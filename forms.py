import os.path
from itertools import count, islice

from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django import forms
from django.core.urlresolvers import resolve, reverse, Resolver404
from django.template.defaultfilters import slugify
from django.core.mail import mail_admins
import urlparse
import cgi
from tinymce.widgets import TinyMCE
import logging
from textwrap import dedent

from util import *

from text_html_text_moin_wiki import convert as html2wiki
import common
import views
import render
from models import PageVersion, Attachment
from util.files import normalize_extension
from www.common.templatetags.static import reverse_static_url
from www.common.context import get_request
from www.common.models import MAX_PHOTO_CAPTION_LENGTH
from common import settings
from django.conf import settings as django_settings

try:
    import tidy
except OSError:
    class FakeTidyLib(object):
        def parseString(s, **opts):
            print >>sys.stderr, ('**You do not seem to have tidy lib '
                                 'installed on your system. That could be bad.**')
            return s

    tidy = FakeTidyLib()

log = logging.getLogger(__name__)

class WikiNameField(forms.CharField):
    def clean(self, value):
        value = super(WikiNameField, self).clean(value)

        try:
            # Just to make sure that we can get a valid wiki word out
            # of it.
            common.title_to_wikiword(value)
            return value
        except sym.invalid_title.exc:
            raise forms.ValidationError('Cannot convert title to wiki word')


class NewPageForm(forms.Form):
    name = WikiNameField(max_length=100)

_pageversion_body_attrs = dict(rows=30, cols=70)

class PageVersionForm(ModelForm, common.HiddenFormMixin):
    form_type = 'rich-text'
    workarounds = settings.TINYMCE_WORKAROUNDS

    @staticmethod
    def get_type(POST):
        if PageVersionPlaintextForm.ident_attr in POST:
            return PageVersionPlaintextForm
        else:
            return PageVersionForm


    @staticmethod
    def get(POST, instance=None):
        return PageVersionForm.get_type(POST)(POST, instance=instance)


    @staticmethod
    def coerce(POST, which, instance=None):
        klass = PageVersionForm.get_type(POST)
        form = klass(POST, instance=instance)
        if klass != which and form.is_valid():
            form.save(commit=False)
            return which(instance=form.instance)
        else:
            return form


    def __init__(self, *args, **kwargs):
        super(PageVersionForm, self).__init__(*args, **kwargs)

        # This is a hack? maybe.
        if self.instance:
            self.initial['body'] = render.render_page_for_edit(self.instance)
            if self.instance.category is not None:
                # `category' isn't a proper model field, so we have to
                # help it along..
                self.initial['category'] = self.instance.category


    def save(self, *args, **kwargs):
        # Help `category' along again.
        instance = super(PageVersionForm, self).save(*args, **kwargs)
        if self.cleaned_data['category']:
            instance.category = self.cleaned_data['category']

    _buttons1 = dedent('''
    formatselect,separator,wiki_b,wiki_i,wiki_u,separator,
    wiki_listnum,wiki_list,wiki_indent,wiki_outdent,separator,
    wiki_link,wiki_img,wiki_hr,wiki_switch''')

    body = forms.CharField(required=False, widget=TinyMCE(
        mce_attrs=dict(
            plugins='wiki,safari',
            mode='textareas',
            theme='advanced',
            skin='wiki',
            width='600',
            height='400',
            body_class='wiki',
            content_css = ','.join(map(lambda x: reverse_static_url(x), (
                    'js/tiny_mce/themes/advanced/skins/wiki/content.css',
                    'css/wiki.css'))),
            extended_valid_elements=('img[class|src|border=0|alt|'
                    '_wiki_img_args|title|width|height],'
                    'div[class|style]'),
            relative_url=False,
            # Don't strip <br /> tags at the end of <li> blocks
            remove_redundant_brs=False,
            remove_script_host=False,
            document_base_url='/',
            # this couples the form with the view a little too tightly
            # in my mind.
            init_instance_callback='init_tinymce',
            theme_advanced_toolbar_align='left',
            theme_advanced_toolbar_location='top',
            theme_advanced_disable='html,help',
            theme_advanced_layout_manager='SimpleLayout',
            theme_advanced_buttons1=_buttons1,
            theme_advanced_buttons2='',
            theme_advanced_buttons3='',
            theme_advanced_link_targets='',
            theme_advanced_blockformats='p,pre,h1,h2,h3',
            wiki_img='wiki_insert_image',
            wiki_link='wiki_insert_link',
            wiki_switch='wiki_switch_editor')))

    title = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'wiki_edit_title mixertwiddle_select',
        'title': 'Enter a Title'}))

    cat_choices = [(cat['id'], cat['title']) 
                    for cat in settings.CATEGORIES.values() 
                    if cat['id'] != '__none__']
    cat_choices = sorted(cat_choices, key=lambda x: x[1])
    category = forms.CharField(
        required=False,
        max_length=max(map(len, settings.CATEGORIES.keys())),
        widget=forms.Select(
            choices=[('', 'Please select a category')] \
                        + cat_choices
        )
    )

    def clean_body(self):
        html = self.cleaned_data['body']

        if not self.instance:
            raise sym.need_instance.exc()

        # TODO(marius): Move this stuff out to a separate module --
        # derender -- and have it deal with the entire HTML<->wiki
        # conversion path. It's kind of ugly to have it in the form.
        def try_resolve(base, path):
            from .widget import WikiWidget
            joined = urlparse.urljoin(base, path)
            try:
                view, _, d = resolve(joined)
                if view == views.widget:
                    w = WikiWidget(d['wiki_slug'], d['slug'])
                    d_ = d
                    view, _, d_ = w.resolve(d['rest'])

                    if view == w.handle_root:
                        return sym.page, d['wiki_slug'], d['slug']
                    elif view == w.image:
                        return (sym.image, d['wiki_slug'],
                                d['slug'], d_['photo_slug'])

                # it resolved, so it's valid, we'll just return the
                # absolute url
                return joined
            except Resolver404:
                # TODO(marius): robustness -- log these?
                return joined

        def resolve_url(url):
            u = urlparse.urlparse(url)
            if not u.netloc or u.netloc == get_request().get_host():
                return try_resolve('/', u.path)
            else:
                return url

        try:
            # First try to tidy things up.
#             html = str(tidy.parseString(
#                 str(html),
#                 output_xhtml=False, add_xml_decl=False,
#                 indent=False, tidy_mark=False,
#                 show_body_only=True))

            # Preserve line feeds intentionally added by user.
            html = html.replace('<p>&nbsp;</p>', '<p>\\\\</p>').replace(
                    '<br />', '\\\\')
            wiki = html2wiki('Name', html, resolve_url)
            if settings.VERIFY_RENDER_BEFORE_SAVE:
                try:
                    render.render_wiki_markup(self.instance.page, wiki)
                except Exception, e:
                    print e
                    # This sucks, but probably less than failing to
                    # render it serve-time :-/
                    mail_admins(
                        'Render failure',
                        'The following page failed to render: %d [%s]\n%s' % (
                            self.instance.page.pk, e, wiki
                        ),
                        fail_silently=True
                    )
                    raise forms.ValidationError(
                        'Failed to convert to wiki markup. '
                        'The townme development team has been notified'
                    )

            return wiki
        except Exception, e:
            log.error('Invalid HTML output: %s', e)
            if django_settings.DEBUG:
                raise
            raise forms.ValidationError('Invalid HTML output.')

    def clean_title(self):
        title = self.cleaned_data['title']

        if not self.instance:
            raise sym.need_instance.exc()

        if self.instance.page.is_ephemeral:
            try:
                # Just to make sure that we can get a valid wiki word out
                # of it.
                common.title_to_wikiword(title)
                return title
            except sym.invalid_title.exc:
                raise forms.ValidationError('Cannot convert title to a wiki word')
        else:
            return title

    def clean_category(self):
        category = self.cleaned_data['category']
        if category and category not in settings.CATEGORIES:
            raise forms.ValidationError('Invalid category')

        return category

    class Meta:
        model = PageVersion
        fields = ['title', 'body']


class PageVersionPlaintextForm(PageVersionForm):
    form_type = 'plain-text'
    ident_attr = 'is_pageversionplaintextform'

    def __init__(self, *args, **kwargs):
        super(PageVersionForm, self).__init__(*args, **kwargs)

        if not self.ident_attr in self.data:
            self.data[self.ident_attr] = '1'

        self.initial[self.ident_attr] = '1'

        # This is a hack? Yes.
        if self.instance:
            self.initial['body'] = self.instance.body

    def clean_body(self):
        return self.cleaned_data['body']

    body = forms.CharField(required=False, widget=forms.widgets.Textarea())
    is_pageversionplaintextform = forms.IntegerField(widget=forms.HiddenInput())

    title = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'wiki_edit_title mixertwiddle_select',
        'title': 'Enter a Title'}))

class AttachmentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        try:
            self.page = kwargs.pop('page')
        except KeyError:
            self.page = None

        super(AttachmentForm, self).__init__(*args, **kwargs)

        if self.page:
            self.instance.page = self.page

    def save(self):
        # Create a name.
        self.instance.file_normalized_extension = normalize_extension(
            self.files['attachment'].name)
        self.instance.file_name = self.files['attachment'].name

        super(AttachmentForm, self).save(commit=False)

        inst = self.instance

        def candidates():
            base, _ = os.path.splitext(os.path.basename(inst.file_name))
            yield base
            yield base.lower()
            for i in islice(count(), 100):
                yield slugify('%s-%d' % (base, i))

        for c in candidates():
            try:
                inst.name = c
                inst.save()
                break
            except IntegrityError:
                pass
        else:
            raise ValidationError(
                'Failed to find a unique name for image %s' % i.file_name)

    class Meta:
        model = Attachment
        fields = ['attachment', 'caption']

class ConfigPhotoForm(forms.Form):

    caption = forms.CharField(required=False,
                              max_length=MAX_PHOTO_CAPTION_LENGTH,
                              widget=forms.TextInput(attrs={
                                            'class': 'mixertwiddle_select',
                                            'title': 'e.g. A Beautiful Lake'}))
    size = forms.ChoiceField(initial='150',
                        choices=(('600', 'large'), ('300', 'medium'),
                                 ('150', 'small')),
                        widget=forms.RadioSelect())
    align = forms.ChoiceField(initial='right',
                         choices=(('left', 'left'), ('center', 'center'),
                                  ('right', 'right')),
                         widget=forms.RadioSelect())

    def __init__(self, photo, *args, **kwargs):
        super(ConfigPhotoForm, self).__init__(*args, **kwargs)
        self.photo = photo
