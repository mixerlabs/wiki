"""A widget for wiki viewing & editing."""
from __future__ import absolute_import

import re
import urllib
import mimetypes
from itertools import ifilter, islice

from django.core.urlresolvers       import reverse, NoReverseMatch
from django.core.paginator          import Paginator, InvalidPage
from django.views.generic.simple    import redirect_to
from django.http                    import (Http404, HttpResponse,
                                            HttpResponseNotFound)
from django.shortcuts               import (render_to_response
                                            as django_render_to_response)
from django.conf                    import settings as django_settings
from django.contrib.gis.geos        import Point
from django.template.defaultfilters import escapejs
from django.shortcuts               import get_object_or_404
from django.db                      import transaction

import www.reviews.views
import www.common.tabs
from environment              import env
from util                     import mixlog
from util.url                 import merge_cgi_params
from www.common               import render_to_string, render_to_response
from www.common.media_storage import media_file_storage
from www.common.forms         import UploadPhotoForm
from www.common.context       import get_ip
from www.registration.captcha import is_captcha_needed
from www.widgets              import Widget, view, ajax

from .       import common
from .       import guid
from .forms  import (PageVersionForm, PageVersionPlaintextForm,
                     ConfigPhotoForm, NewPageForm)
from .models import Wiki, Page, PageVersion
from .render import (wiki_img_clean_caption, wiki_img_args_to_html,
                    default_thumb_width)

class WikiWidget(Widget):
    """The wiki widget is a widget that hosts a wiki. We do not use
    the widget to maintain state, as we have our own versioning via
    PageVersion."""
    class WikiHttpResponseNotFound(HttpResponseNotFound): pass

    @classmethod
    def of_page(cls, page):
        """Create a widget for the given page."""
        return cls(page.wiki.slug, page.slug)

    def __init__(self, wiki_slug, page_slug):
        super(WikiWidget, self).__init__()

        self.page      = None
        self.wiki_slug = wiki_slug
        self.page_slug = page_slug

    def get_page(self):
        return Page.all_objects.get(
            wiki__slug=self.wiki_slug, slug=self.page_slug)

    @transaction.commit_on_success
    def __call__(self, request, path):
        view, args, kwargs = self.resolve(path)
        if view != self.edit:
            try:
                self.page = self.get_page()
            except Page.DoesNotExist:
                # We have a special 404 for wikis, to enable users to
                # create the page in question.
                return self.WikiHttpResponseNotFound(
                    render_to_string(
                        'wiki/page_404.html', {
                            'slug'  : self.page_slug,
                            'title' : common.wikiword_to_title(self.page_slug),
                            'wiki_slug' : self.wiki_slug,
                    })
                )

        return view(request, *args, **kwargs)

    def handle_root(self, request):
        context = {
            'page'    : self.page,
            'related' : islice(self.page.each_related_page(), 5)
        }

        www.reviews.views.process_reviews_django(
            request, context,
            '/' + self.page.wiki.slug + '/' + self.page.slug,
            comments_only=True)

        return render_to_response(
            'wiki/page.html', context,
            uri_ctx_override={'cc_license':True},
            base_opts={'tab': www.common.tabs.PAGES})

    @view(r'^edit$', 'edit')
    def edit(self, request):
        from . import views

        # Special: for edits, we'll create the page for you. We're
        # nice like that.
        if self.page is None:
            try:
                self.page = self.get_page()
            except Page.DoesNotExist:
                wiki, _ = Wiki.objects.get_or_create(
                    slug=self.wiki_slug, host=guid.host())
                self.page, _ = Page.all_objects.get_or_create(
                    wiki=wiki, slug=self.page_slug)

        if 'plaintext' in request.REQUEST:
            do_coerce = PageVersionPlaintextForm
        elif 'richtext' in request.REQUEST:
            do_coerce = PageVersionForm
        else:
            do_coerce = False

        if do_coerce:
            formklass = do_coerce
        else:
            # Rich text is default
            formklass = PageVersionForm

        context = {}

        if request.method == 'GET':
            if self.page.current_version:
                vsn = self.page.current_version
            else:
                vsn = PageVersion(page=self.page)
            if not vsn.title:
                if 'title' in request.REQUEST:
                    vsn.title = common.wikiword_to_title(
                        request.REQUEST['title'])
                elif not self.page.is_ephemeral:
                    vsn.title = common.wikiword_to_title(self.page.slug)
                if request.REQUEST.get('category') in common.settings.CATEGORIES:
                    vsn.category = request.REQUEST.get('category') 
            form = formklass(instance=vsn)
        elif request.method == 'POST':
            vsn = PageVersion(page=self.page)
            if do_coerce:
                form = PageVersionForm.coerce(
                    request.POST, formklass, instance=vsn)
            else:
                form = PageVersionForm.get(request.POST, instance=vsn)

            if form.is_valid():
                form.save(commit=False)
                if 'preview' in request.REQUEST:
                    context['preview'] = form.instance
                if 'publish' in request.REQUEST:
                    if views._publish_page(request, self.page, vsn, context):
                        # The last thing to do whe a submit succeeds is propagate
                        # the post_auth action to the session.
                        post_auth_action = request.POST.get('post_auth_action')
                        if post_auth_action:
                            request.session['post_auth_action'] = post_auth_action
                        return redirect_to(request, vsn.page.get_absolute_url())

        # Hide titles and categories for embedded pages.
        if vsn.page.is_embedded():
            form.fields['title'].widget = form.fields['title'].hidden_widget()
            form.fields['category'].widget = \
                form.fields['category'].hidden_widget()

        pre_auth = None
        if env.recaptcha.enable_pre:
            if request.user.is_anonymous():
                pre_auth = 'login'
            elif is_captcha_needed(request):
                pre_auth = 'captcha'

        context.update({
            'form'        : form,
            'vsn'         : vsn,
            'admin_view'  : request.user.is_staff,
            'pre_auth'    : pre_auth,
        })

        return render_to_response('wiki/edit.html', context,
                                  uri_ctx_override={'cc_license': True},
                                  base_opts={'tab': www.common.tabs.PAGES})

    @view(r'^history$', 'history')
    def history(self, request):
        # show the last five entries
        history = self.page.pageversion_set.all().order_by('-created_at')
        try:
            paginator = Paginator(history, 10).page(request.GET.get('page', 1))
        except InvalidPage:
            raise Http404

        context = {
            'page'      : self.page,
            'paginator' : paginator,
            'widget'    : self,
        }

        return render_to_response('wiki/history.html', context, 
                                  base_opts={'tab': www.common.tabs.PAGES})

    @ajax('resolvediffurl')
    def resolvediffurl(self, fromvsn, tovsn):
        return self.reverse('diff', fromvsn, tovsn)

    @view(r'^diff/(?P<fromvsn>[^,]+),(?P<tovsn>[^,]+)$', 'diff')
    def diff(self, request, fromvsn, tovsn):
        context = {
            'fromvsn' : get_object_or_404(
                          PageVersion, page=self.page, version=fromvsn),
            'tovsn'   : get_object_or_404(
                          PageVersion, page=self.page, version=tovsn),
            'page'    : self.page,
        }

        return render_to_response('wiki/diff.html', context,
                                  uri_ctx_override={'cc_license':True},
                                  base_opts={'tab': www.common.tabs.PAGES})


    @view(r'^upload_photo_dialog$', 'upload_photo_dialog')
    def upload_photo_dialog(self, request):
        context = {
            'flickr_api_key':  django_settings.FLICKR_API_KEY,
            'page': request.REQUEST.get('page', '1'),
            'query': request.REQUEST.get('query', ''),
        }

        user = request.user
        ip_address = get_ip(request)
        if not user.is_authenticated():
            user = None
        if request.method == 'GET':
            context['geo_check'] = request.GET.get('geo_check', '')
            context['form'] = UploadPhotoForm(self.page, user, ip_address)
        elif request.method == 'POST':
            context['geo_check'] = request.POST.get('geo_check', '')
            form = UploadPhotoForm(self.page, user, ip_address, request.POST,
                    request.FILES)
            if form.is_valid():
                form.save()
                back = merge_cgi_params(request.get_full_path(), {
                        'page': context['page'], 'query': context['query'], 
                        'geo_check': context['geo_check'] })
                return redirect_to(request,
                    self.page.get_config_photo_dialog_url(form.instance.slug) +
                    '?back=%(back)s', back=urllib.quote(back))
            else:
                context['form'] = form
        if 'current_town' in request.ctx:
            town = request.ctx['current_town'].census_sf1_city
            context['geo_pt'] = Point(x=float(town['INTPTLON']),
                                      y=float(town['INTPTLAT']))
        context['default_search_terms'] = ' '.join(self.page.wiki.get_keywords())
        return django_render_to_response(
            'common/upload_photo_dialog.html', context)

    @view(r'^config_photo_dialog/(?P<photo_slug>[^/]+)$', 'config_photo_dialog')
    def config_photo_dialog(self, request, photo_slug):
        photo = self.page.photos.get(slug=photo_slug)
        context = {
            'photo' : photo,
            'back'  : request.REQUEST.get('back', None)
        }

        if request.method == 'GET':
            context['form'] = ConfigPhotoForm(photo)
        elif request.method == 'POST':
            form = ConfigPhotoForm(photo, request.POST, request.FILES)
            if form.is_valid():
                caption = form.cleaned_data.get('caption', None)
                if caption:
                    # Saving this will rebase the slug on the caption
                    photo.caption = caption
                    photo.save()
                img_args_list = [ photo.slug, 'thumb' ]
                try:
                    width = int(form.cleaned_data.get('size', ''))
                    if width > 0 and width != default_thumb_width:
                        img_args_list.append(str(min(600, width)) + 'px')
                except ValueError:
                    pass
                align = form.cleaned_data.get('align', None)
                # Don't specify 'right' since that is the default for thumb
                if align in ('left', 'center'):
                    img_args_list.append(align)
                if caption:
                    img_args_list.append(wiki_img_clean_caption(caption))
                img_args = '|'.join(img_args_list)
                markup = '<<img %s>>' % img_args
                html = wiki_img_args_to_html(self.page, True, img_args)
                context['script'] = 'parent.done_uploading("%s", "%s");' % (
                    escapejs(markup), escapejs(html))
                return django_render_to_response(
                    'common/run_script.html', context)
            else:
                context['form'] = form
        return django_render_to_response(
            'common/config_photo_dialog.html', context)

    @view(r'^image_(?P<media_hash>[^/]+)/(?P<photo_slug>[^./]+)(?P<ext>\.[^.]+)',
          'image')
    def image(self, request, media_hash, photo_slug, ext):
        # Apache should intercept urls of this form:
        # image_hhhhh/my-dog-spot.jpg and locally serve as if the url
        # was /media/hhhhh.jpg Warn if this function does not get
        # bypassed!
        mixlog().warning('www.wiki.views.image called. Apache failed to '
                         'intercept %s' % request.path)
        file_name = media_hash + ext
        mimetype = mimetypes.guess_type(file_name)[0]
        if not mimetype:
            raise Exception, "Image mime type undetermined"
        file = media_file_storage.open(file_name)    
        return HttpResponse(file.read(), mimetype=mimetype)

    @view(r'^add_link_inline$', 'add_link_inline')
    def add_link_inline(self, request):
        from . import views
        recent = ifilter(lambda p: p != self.page,
                         self.page.wiki.each_recent_page())

        # TODO(marius): The listifying here may not scale -- might
        # need to come up with a generator wrapper for this, or do
        # some more denormalization the models so that we don't rely
        # on foreign field orderings.
        recent = list(recent)

        try:
            paginator = Paginator(recent, 5).page(request.GET.get('page', 1))
        except InvalidPage:
            raise Http404

        context = {
            'page'      : self.page,
            'paginator' : paginator,
        }

        if request.method == 'GET':
            form = None
            selection = request.GET.get('selection', None)
            if selection is not None and len(selection) > 0:
                m = re.match(
                    (r'(http://)?(?P<url>[a-z]+\.[a-z]+'
                     r'\.[a-z]{2,3}(\.[a-z]{2})?)'), selection)
                if m is not None:
                    context['link_url'] = m.groupdict()['url']
                else:
                    form = NewPageForm({'name': selection})
            if form is None:
                form = NewPageForm()                

        elif request.method == 'POST':
            form = NewPageForm(request.POST)
            if form.is_valid():
                context['form_title'] = form.cleaned_data['name']
                context['form_slug'] = \
                    common.title_to_wikiword(form.cleaned_data['name'])
                context['form_href'] = reverse(
                    'wiki_page',
                    kwargs={'wiki_slug' : self.page.wiki.slug,
                            'slug'      : context['form_slug']})

                # Actually create the page here, so that we can store
                # the unadulterated title (and I guess this is the
                # intent anyway).
                page_, created = Page.objects.get_or_create(
                    wiki=self.page.wiki, slug=context['form_slug'])
                if created:
                    pv = PageVersion(page=page_)
                    pv.title = context['form_title']
                    pv.body = common.settings.DEFAULT_STUB_CONTENT

                    views._save_page_version(pv, request)

        context['form'] = form

        return django_render_to_response('wiki/add_link_inline.html', context)

    @view(r'^version/(?P<version>[^/]+)$', 'version')
    def version(self, request, version):
        vsn = get_object_or_404(PageVersion, page=self.page, version=version)

        return render_to_response(
            'wiki/version.html', {
                'page' : vsn.page,
                'vsn'  : vsn,
            }
        )

    def reverse(self, name, *args, **kwargs):
        if self.parent:
            return super(WikiWidget, self).reverse(name, *args, **kwargs)
        else:
            return reverse('wiki_page_', kwargs={
                'wiki_slug' : self.wiki_slug,
                'slug'      : self.page_slug,
                'rest': super(WikiWidget, self).reverse(name, *args, **kwargs)
            })
