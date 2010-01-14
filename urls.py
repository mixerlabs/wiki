from __future__ import absolute_import

from django.conf.urls.defaults import url, patterns

from . import common
from . import views

urlpatterns = patterns('',
    # | Widget.
    #
    # We're hosting a widget, so first route the root so we don't need
    # a trailing slash.
    url(r'^(?P<slug>' + common.settings.WIKIWORD_RE + r')$',
        views.widget, name='wiki_page', kwargs={'rest': ''}),
    # Then once for the sub paths to be routed.
    url(r'^(?P<slug>' + common.settings.WIKIWORD_RE + r')/(?P<rest>.*)$',
        views.widget, name='wiki_page_'),

    # | Other toplevels.
    url(r'^directory$', views.directory, name='wiki_directory'),
    url(r'^directory/best_ofs$', views.directory, 
        name='wiki_directory_best_of', kwargs={'best_ofs': True}),
    url(r'^directory/(?P<category>[\w-]+)$',
        views.directory,
        name='wiki_category_directory'),
    url(r'^directory/(?P<category>[\w-]+)/best_ofs$',
        views.directory,
        name='wiki_category_directory_best_of', kwargs={'best_ofs': True}),

    url(r'^new-page$', views.new_page, name='wiki_new_page'),
)
