"""Contains GUID integration for Wikis. Most of the other stuff here
is entirely separable from GUID stuff, so let's try to keep the
integration code here."""

from itertools import islice, ifilter

import views
from django.conf              import settings as all_settings
from django.core.urlresolvers import reverse

from util.seq import Deferred
from www.guid.urlresolver import reverse_guid

import www.common.context
from common import settings
from models import Wiki, Page
from models import WikiHost as models_WikiHost

def recent_wikis_context(context):
    if not 'base_wiki_guid' in context:
        return

    guid = context['base_wiki_guid']
    ctx = context.setdefault('wiki', {})

    ctx['new_page_url'] = reverse('wiki_new_page', kwargs=dict(wiki_slug=guid))
    ctx['directory_url'] = reverse('wiki_directory',
                                   kwargs=dict(wiki_slug=guid))
    # TODO - only set the changes url if the slug is a town?
    ctx['changes_url'] = reverse('changes', kwargs=dict(town=guid))
    ctx['recent'] = []
    try:
        wiki = Wiki.objects.get(pk=guid)
    except Wiki.DoesNotExist:
        return

    ctx['recent'] = Deferred(islice(ifilter(lambda p: p.slug != 'Home',
            wiki.each_recent_page()), settings.GUID_NUM_RECENT_WIKIS))


def home_wiki_context(context):
    """If it exists, add the home wiki to the context, otherwise set
    it to None."""
    if not 'id' in context:
        return

    ctx = context.setdefault('wiki', {})
    guid = context['id']

    try:
        ctx['wiki'] = Wiki.objects.get(pk=guid)
    except Wiki.DoesNotExist:
        ctx['wiki'] = Wiki(slug=guid, host=host())

    try:
        ctx['home'] = ctx['wiki'].page_set.get(slug='Home')
    except (Wiki.DoesNotExist, Page.DoesNotExist):
        # Create a fake, empty one.
        ctx['home'] = Page(slug='Home', wiki=ctx['wiki'])

def host():
    try:
        return models_WikiHost.objects.get(name='guid')
    except models_WikiHost.DoesNotExist:
        host = models_WikiHost(name='guid', cls='www.wiki.guid.WikiHost')
        host.save()
        return host

class WikiHost(object):
    @staticmethod
    def reverse_page(wiki_slug, page_slug):
        if page_slug == settings.GUID_HOME_PAGE_NAME:
            return reverse_guid(wiki_slug)
        elif page_slug == settings.GUID_TWITTER_PAGE_SLUG:
            from www.twitter.views import _slug_home
            return _slug_home(wiki_slug, True)
        else:
            return reverse('wiki_page', kwargs={
                'wiki_slug': wiki_slug,
                'slug': page_slug})

    @staticmethod
    def is_embedded_page(page):
        return page.slug == settings.GUID_HOME_PAGE_NAME

if all_settings.WIKI_ENABLED:
    www.common.context.pre_processors.add(home_wiki_context)
    www.common.context.post_processors.add(recent_wikis_context)
