"""linkgraph utilities for wiki pages. Provides updating of linkgraph
by wiki pages & computing related pages."""
from __future__ import absolute_import
from __future__ import with_statement

from django.db.models.signals import post_save, post_delete
from django.core.urlresolvers import resolve, Resolver404

from util.db                  import commit_block
from www.linkgraph.models     import Edge

from .models                  import Page

def initialize():
    """Initialize post-{save,delete} hooks for maintaining the wiki
    link graph."""
    post_save.connect(post_save_handler, sender=Page, weak=False)
    post_delete.connect(post_delete_handler, sender=Page, weak=False)

def post_save_handler(sender, **kwargs):
    with commit_block():
        update_linkgraph_for_page(kwargs['instance'])

def post_delete_handler(sender, **kwargs):
    page = kwargs['instance']
    Edge.objects.filter(src=page.get_absolute_url()).delete()

def each_link(stream):
    """An iterator for parsing out links from the given genshi stream."""
    for kind, meta, _ in stream:
        if kind != 'START':
            continue

        qname, attrs = meta
        if qname != 'a':
            continue

        for key, value in attrs:
            if key != 'href':
                continue

            yield value
            break

def each_related_page(page):
    """An iterator of pages related to `page' for the current link
    graph."""
    # Circular dependency
    from . import views
    for edge in Edge.objects.filter(dst=page.get_absolute_url()):
        # Skip external links.
        if not edge.src or edge.src[0] != '/':
            continue

        # This is a bit roundabout. We may improve on this by storing
        # foreignkeys directly into the link graph.
        try:
            view, _, d = resolve(edge.src)
            if view != views.widget:
                continue
        except Resolver404:
            continue

        try:
            yield Page.objects.get(wiki__slug=d['wiki_slug'], slug=d['slug'])
        except Page.DoesNotExist:
            continue

def update_linkgraph_for_page(page):
    """Updates the global link graph for the given (source) page that
    was just edited"""
    # Circular dependency
    from . import render
    if not page.current_version:
        return

    # Oy, this is pretty terrible: creoleparser doesn't give us any
    # access to the creole parsetree (nor does it really have one,
    # only kinda), so the best we can do is read the outgoing genshi
    # stream, and look for links there.
    stream = render.render_page_to_stream(page.current_version)
    src    = page.get_absolute_url()
    dsts   = set(each_link(stream))

    # Now update the link graph so that the current set of destination
    # reflects `dsts'

    # Delete old objects, then find only new links, and insert them.
    Edge.objects.filter(src=src).exclude(dst__in=dsts).delete()

    old = set(e.dst for e in Edge.objects.filter(src=src))
    new = dsts - old
    for dst in new:
        Edge.objects.create_safe(src=src, dst=dst)
