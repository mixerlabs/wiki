from itertools import islice, ifilterfalse
import re

from difflib import HtmlDiff
from ext.diff.diff_match_patch import diff_match_patch
import genshi.core

from django import template
from django.utils.html import conditional_escape
from django.core.urlresolvers import reverse
import ext.diff.intra_region_diff as intra_region_diff

from www.common import render_to_response, context as ctx
from www.wiki.common import settings
from www.common.templatetags.goodtimes import goodtimes
from www.profiles.utils import screen_name_from_user
from www.wiki.models import Attachment, Wiki
from www.wiki import render


register = template.Library()

@register.simple_tag
def context_title():
    return render.render_page(vsn)

@register.simple_tag
def wiki_body(vsn):
    if not vsn:
        return ''
    return render.render_page(vsn)

@register.simple_tag
def wiki_title(vsn):
    if not vsn:
        out = ''
    elif vsn.title:
        out = vsn.title
    elif vsn.page.is_ephemeral:
        out = 'New page'
    else:
        out = vsn.page.slug

    return conditional_escape(out)

@register.simple_tag
def wiki_snippet(vsn, max_length=80):
    text = render.render_page(vsn, method='text')
    text = unicode(text, 'utf8').strip()
    if len(text) <= max_length:
        return text
    snippet = text[:max_length-3]
    index = snippet.rfind(' ')
    if index >= 0:
        snippet = snippet[:index].rstrip(' .')
    snippet = snippet + '...'
    return snippet
    
@register.simple_tag
def wiki_render_section(page, about):
    return page.render_section(about)

@register.simple_tag
def wiki_url(which, page):
    # The wiki host may override the page URLs, so we need to special
    # case that here since it may be embedded. TODO: think of a better
    # way to do this. At least by using only wiki_url, we can control
    # it...
    if which == 'page':
        if page.is_ephemeral:
            return '/'
        else:
            return page.get_absolute_url()
    else:
        return page.widget.reverse(which)

@register.simple_tag
def wiki_new_page_url(wiki_slug, category):
    url = reverse('wiki_new_page', kwargs=dict(wiki_slug=wiki_slug))
    if category in settings.CATEGORIES and category != '__none__':
        url = '%s?category=%s' % (url, category)
    return url

@register.simple_tag
def wiki_link(page):
    if not page.current_version:
        return ''
    return '<a href="%s">%s</a>' % (wiki_url('page', page), 
                wiki_title(page.current_version))

@register.simple_tag
def wiki_last_edit_user_time(page):
    vsn = page.current_version
    if not vsn:
        return ''

    if vsn.edit_user is None:
        user_str = vsn.edit_ip_address
    else:
        user_str = '<a href=%s>%s</a>' % (
            reverse('view_profile', args=[vsn.edit_user.username]),
            screen_name_from_user(vsn.edit_user)
        )

    return '%s by %s' % (
        goodtimes(page.current_version.created_at, '1week'),
        user_str
    )

@register.simple_tag
def wiki_linked_user(page, utype):
    if utype == 'creator':
        vsn = page.first_version
    else:
        vsn = page.current_version
    if not vsn:
        return ''

    user = vsn.edit_user

    if vsn.edit_user is None:
        return vsn.edit_ip_address
    else:
        return '<a href="%s">%s</a>' % (
            reverse('view_profile', args=[user.username]), 
                    screen_name_from_user(user))
                
@register.simple_tag
def wiki_directory_url(wiki_slug):
    return reverse('wiki_directory',
                  kwargs={'wiki_slug': wiki_slug})

@register.simple_tag
def wiki_category_url(wiki_slug, category):
    assert category in settings.CATEGORIES
    return reverse('wiki_category_directory',
                   kwargs={'wiki_slug': wiki_slug,
                           'category': category})

@register.simple_tag
def wiki_linked_category(wiki_slug, category, extra=''):
    assert category in settings.CATEGORIES
    name = settings.CATEGORIES[category]['title']
    url = wiki_category_url(wiki_slug, category)
    return '<a href="%s">%s</a>' % (url, name)

@register.simple_tag
def wiki_attachment(page, attachment):
    return reverse('wiki_attachments',
                   kwargs=dict(wiki_slug=page.wiki.slug,
                               slug=page.slug,
                               attachment_slug=attachment))
                               
@register.simple_tag
def wiki_diff(fromvsn, tovsn):
    differ = diff_match_patch()
    return differ.diff_prettyHtml(differ.diff_main(fromvsn.body, tovsn.body))

@register.simple_tag
def wiki_tablediff(fromvsn, tovsn):
    diff_params = intra_region_diff.GetDiffParams(dbg=False)
    return intra_region_diff.IntraRegionDiff(
        fromvsn.body.splitlines(1),
        tovsn.body.splitlines(1),
        diff_params)

@register.inclusion_tag('wiki/_page_group.html')
def wiki_page_group(page_set, order):
    show_last_edit_time = order=='recent'
    show_last_edit_user = order in ('title', 'recent')
    
    return {'page_set': page_set,
            'show_last_edit_time': show_last_edit_time,
            'show_last_edit_user': show_last_edit_user,
           }

@register.inclusion_tag('wiki/_recent.html')
def wiki_recent_pages(slug, title, num=5, exclude=['Home']):
    try:
        wiki = Wiki.objects.get(slug=slug)
    except Wiki.DoesNotExist:
        return {}
    recent = list(islice(ifilterfalse(lambda p: p.slug in exclude,
            wiki.each_recent_page()), num))
    return {'recent': recent, 'title': title}

@register.inclusion_tag('wiki/_section.html')
def wiki_section(page):
    return {'page': page}

@register.inclusion_tag('wiki/_buttons.html')
def wiki_buttons(page, which):
    which = which.lower().split(',')

    urls = dict(view=page.get_absolute_url(),
                edit=page.get_edit_url(),
                history=page.get_history_url(),
                new=page.wiki.get_new_url())

    titles = dict(
        view='view page',
        edit='edit page',
        history='page history',
        new='create new page')

    default = which[0]

    return dict(buttons=[(b, titles[b], urls[b], 'button-default' if b == default else 'button')
                         for b in which])

