"""Views for wiki. Most of the wiki views are actually defined in the
wiki widget (in ``widget.py''), as the wiki is now hosted in a
widget. The views here bridge the old & new world."""

from __future__ import absolute_import

import functools

from django.conf                import settings as all_settings
from django.core.urlresolvers   import reverse
from django.http                import Http404 
from django.core.paginator      import Paginator, InvalidPage
from django.contrib.auth        import get_user
from django.contrib.auth.models import User
from django.db                  import IntegrityError, transaction
from django.core.exceptions     import ValidationError

from util.seq                 import first
from www.common               import render_to_response, context as ctx
from www.common.tabs          import PAGES
from www.registration.captcha import is_captcha_needed
from www.search.views         import LocationSearch

from .common import settings
from .models import Wiki, Page 
from .widget import WikiWidget
from .       import common
from .       import guid

# | Page extraction, creation & saving.
def _get_wiki_or_create(slug):
    # First of all, does the wiki exist?
    try:
        wiki = Wiki.objects.get(pk=slug)
    except Wiki.DoesNotExist:
        # XXX(marius): fix the hard-coded default here.
        wiki = Wiki(slug=slug, host=guid.host())
        wiki.save()

    return wiki

def _get_page_or_404(slug, wiki_slug):
    wiki = _get_wiki_or_create(wiki_slug)
    try:
        return Page.all_objects.get(wiki=wiki, slug=slug)
    except Page.DoesNotExist:
        raise Http404

def _get_page(slug, wiki_slug):
    assert slug is not None

    wiki = _get_wiki_or_create(wiki_slug)
    try:
        return Page.all_objects.get(wiki=wiki, slug=slug)
    except Page.DoesNotExist:
        return wiki.page_set.create(slug=slug)

def _extract_wiki_args(kwargs):
    return kwargs.pop('slug'), kwargs.pop('wiki_slug')

def _save_page_version(version, request):
    # Try x-forwarded-for first in case the user is behind a proxy.
    version.edit_ip_address = request.META.get(
        'HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    if request.user.is_authenticated():
        version.edit_user = get_user(request)
    version.save()

def _publish_page(request, page, vsn, context):
    # Nothing has changed, bypass the other checks.
    if not vsn.has_changed():
       return True
    if request.user.is_anonymous():
       context['post_auth'] = 'login'
       return False
    elif is_captcha_needed(request, consume=True):
       context['post_auth'] = 'captcha'
       return False
    if page.is_ephemeral:
        # For ephemeral pages, we have a finalized
        # title, so we'll try and convert it. We
        # disambiguate by adding suffixes. In the
        # future, we might want to notify the user
        # that there's another page with the request
        # title, or maybe even do some sort of
        # merging.
        def candidates():
            slug = common.title_to_wikiword(vsn.title)
            yield slug
            start = min(len(slug), settings.MAX_WIKIWORD_LENGTH-3)

            for i in range(1, 99):
                yield slug[:start] + '-%d' % i

        for slug in candidates():
            
            # First try to see if this slug already exists
            # but was deleted. If so, recycle it.
            try:
                vsn.page = Page.all_objects.get(slug=slug, wiki=page.wiki, 
                                                   is_deleted=True)
                break
            except Page.DoesNotExist:
                pass
            
            # If there is not deleted version of the page, 
            # try using the current slug. 
            try:
                page.slug = slug
                page.is_ephemeral = False
                sid = transaction.savepoint()
                page.save()
                break
            except IntegrityError:
                # If there is an IntegrityError, we need to revert (this
                # matters on Postgres). Note that we set a savepoint above
                # so we just revert the attempt to save.
                transaction.savepoint_rollback(sid)
                continue
        else:
            raise ValidationError, 'Could not find a unique slug.'

    _save_page_version(vsn, request)
    return True
    
def get_page_or_404(fun):
    @functools.wraps(fun)
    def wrapper(request, **kwargs):
        page = _get_page_or_404(*_extract_wiki_args(kwargs))
        return fun(request, page, **kwargs)

    return wrapper

# | Toplevel views. Widgets, new page & directory.
@transaction.commit_on_success
def widget(request, wiki_slug, slug, rest):
    """The main entry point for routing wiki requests: we instantiate
    a widget for the wiki & route the remainder of the URL through it."""
    return WikiWidget(wiki_slug, slug)(request, rest)

def new_page(request, wiki_slug):
    # Create an ephermal widget, and edit it.
    wiki, _ = Wiki.objects.get_or_create(slug=wiki_slug, host=guid.host())
    slug    = common.random_wikiword()
    page    = Page.objects.create(wiki=wiki, slug=slug, is_ephemeral=True)

    # Call directly into the editor.
    return WikiWidget(wiki_slug, slug).edit(request)

def _split_best_ofs(page_set):
    try:
        lilb_id = User.objects.get(username='lilb').id
    except User.DoesNotExist:
        lilb_id = -1
    # TODO: In future, may want to promote pages with 
    # significant user contributions
    filter_args = dict(current_version__edit_user__id=lilb_id, 
                       current_version__title__startswith='Best')
    return page_set.exclude(**filter_args), page_set.filter(**filter_args)
    
def directory(request, wiki_slug, category=None, best_ofs=False):
    wiki = _get_wiki_or_create(wiki_slug)
    categories = wiki.get_categories()
    context = {
        'categories'         : categories,
        'guid_title'         : ctx.get_context().get('guid_title', ''),
        'wiki_slug'          : wiki_slug,
        'show_best_ofs'      : best_ofs,
    }
    
    # Top level directory page get special treatment
    if not (category or best_ofs or request.GET.get('order')):
        context['order'] = 'categories'
        pages = wiki.all_pages
        cats = filter(lambda cat: cat['count'] > 0, categories)
        context['category_paginator'] = Paginator(cats, 5)
        context['title'] = 'Pages about %s' % context['guid_title']
    else:
        context['order'] = request.GET.get('order', 'title')
        if category is None:
            pages = wiki.all_pages
        else:
            category = first(filter(lambda x: x['id']==category, categories))
            if not category:
                raise Http404
            pages = wiki.pages_of_category(category['id'])
            context['category'] = category
        
        if context['order'] == 'title':
            # Sort by title
            pages = pages.order_by('current_version__title')
            pages, best = _split_best_ofs(pages)
            # Annonying that can't case-insensitive sort in db, so doing
            # it only for non-best-of pages
            pages = sorted(pages.select_related(), 
                           key=lambda x: (x.title() or x.slug).lower())
        elif context['order'] == 'recent':
            # Sort by modified date
            pages = pages.order_by('-modified_on')
            pages, best = _split_best_ofs(pages)
        
        if best_ofs:
            context['best_of_paginator'] = Paginator(best, 10)        
        else:
            context['page_paginator'] = Paginator(pages, 10)

    # Do the pagination
    for pg_type in ('page', 'best_of', 'category'):
        paginator = context.get('%s_paginator' % pg_type)
        if paginator:
            pg_num = request.GET.get(pg_type, 1)
            try:                
                context['%s_paginator_page' % pg_type] = paginator.page(pg_num)
            except InvalidPage:
                raise Http404
            context['%s_url_template' % pg_type] = '?order=%s&%s=${num}' % \
                                                    (context['order'], pg_type)
            
    # Pull out only pages for current category (on directory home page)
    if 'category_paginator_page' in context:
        for cat in context['category_paginator_page'].object_list:
            cat['pages'] = wiki.pages_of_category(cat['id']
                                                 ).order_by('-modified_on')[:3]
    
    
    # Titles
    if category and best_ofs:
        context['title'] = 'Best %s in %s' % (category['title'], 
                                              context['guid_title'])
    elif category:
        context['title'] = '%s in %s' % (category['title'], 
                                         context['guid_title'])
    elif best_ofs:
        context['title'] = 'Best in %s' % context['guid_title']
    else:
        context['title'] = 'Pages about %s' % context['guid_title']
       
    # Breadcrumbs 
    crumbs = request.ctx.setdefault('crumbs', [])
    if category or best_ofs:
        # If not home page, add crumb to home
        crumbs.append((reverse('wiki_directory', 
                       kwargs=dict(wiki_slug=wiki_slug)), 'Pages'))
    if category and best_ofs:
        # If in category, best ofs, add crumb to category
        crumbs.append((reverse('wiki_category_directory', 
                       kwargs=dict(wiki_slug=wiki_slug, 
                                   category=category['id'])), 
                      category['title']))
    return render_to_response('wiki/directory.html', context, 
                              base_opts={'tab': PAGES})

class WikiLocationSearch(LocationSearch):
  share_title = 'Pages'
  tab = PAGES

  @classmethod
  def url_from_location(cls, location, which=None):
      #TODO (othman): Use 'which' field to choose wiki slugs
      if all_settings.WIDGETS_DEFAULT:
          dir_tag = 'widgets_wiki_directory'
      else:
          dir_tag = 'wiki_directory'
      return reverse(dir_tag, kwargs={'wiki_slug': location.guid})


