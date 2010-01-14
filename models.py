from __future__ import absolute_import

import os.path
import datetime
import itertools
import posixpath
import re

from django.conf                 import settings as all_settings
from django.contrib.auth.models  import User
from django.db                   import models
from django.core.urlresolvers    import reverse
from django.template.loader      import render_to_string
from django.contrib.contenttypes import generic
from tagging.models              import Tag, TaggedItem

from util.cache                     import cache_key_, invalidate_cache_key
from util.django_models             import get_or_none
from util.functional                import pick
from util                           import cache
from guid                           import resolve_guid
from www.guid.resolver              import resolve_url_to_ctx
from www.common.media_storage       import media_file_storage
from www.common.fields              import PyObjectField
from www.common.templatetags.static import reverse_static_url
from www.common.models              import Photo
from www.feedback.models            import Feedback

from .common import settings


# ~ CATEGORIES
#
#   The following deal with converting categories to tags and vice
#   versa. We create a separate tag namespace for categories for
#   future flexibility.
def category_of_tag(tag):
    """Return the category (a string) from a tag (also a string)."""
    label, category = tag.split(':', 1)
    assert label == 'category'
    return category

def tag_of_category(category):
    """Return the tag of the given category -- inverse of
    ``category_of_tag()''"""
    return 'category:%s' % category

def title_of_category(category):
    return settings.CATEGORIES[category]['title']

def category_of_object(obj):
    """Return the category of the given object according to
    django-tagging. If it does not have one, return the default as
    defined in settings."""
    tags = Tag.objects.get_for_object(obj)
    return category_of_tag(tags[0].name) if len(tags) > 0 else None

class WikiHost(models.Model):
    """A WikiHost deals with providing certain functionality for a
    group of wikis hosted under the same ``category'' -- eg. looking up
    related wikis, interpreting slugs, dealing with extra templating and
    so on."""
    name = models.SlugField(max_length=50, unique=True)
    cls = PyObjectField()

# Cache WikiHosts by ID.  There's only a few and they don't change.
host_cache = {}

class Wiki(models.Model):
    # As of 2008/03/19, the largest guid is 184 characters.
    #
    #     mysql> select max(length(id)) from guid;
    #     +-----------------+
    #     | max(length(id)) |
    #     +-----------------+
    #     |             184 | 
    #     +-----------------+
    #
    # TODO(marius): drop the slug as the primary key and instead use
    # something else, otherwise these foreign keys become big.

    slug = models.SlugField(max_length=200, unique=True, primary_key=True)
    host = models.ForeignKey(WikiHost)

    @property
    def all_pages(self):
        """Return a query set for visible pages in this
        wiki. (`page_set' will return *all* pages, we actually want to
        filter out invisible ones). TODO(Django1.1): supports the
        notion of an auto manager, and so with it, we can have
        `page_set' do the right thing."""
        # Include current_version because that's usually accessed next.
        return self.page_set.filter(is_ephemeral=False, is_deleted=False)\
            .exclude(current_version=None).select_related('current_version')

    def each_page(self):
        """Iterate over all visible pages in this wiki."""
        for page in self.all_pages:
            # set page.wiki to potentially save a DB query
            page.wiki = self
            yield page

    def each_recent_page(self):
        '''Iterate over recent pages in this wiki.'''
        for page in self.all_pages\
                .filter(modified_on__gte=settings.WIKI_BIRTHDAY)\
                .order_by('-modified_on'):
            # set page.wiki to potentially save a DB query
            page.wiki = self
            yield page

    def pages_of_category(self, category):
        """Return query set for Pages in category (string)"""
        if category is None:
            category = '__none__'
        
        if category not in settings.CATEGORIES:
            raise ValueError, 'Invalid category %s' % category

        if category == '__none__':
            cats = map(tag_of_category, settings.CATEGORIES.keys())
            qs = TaggedItem.objects.get_by_model(Page, cats)
            qs = self.all_pages.exclude(id__in=pick('id', qs.values('id')))
        else:
            qs = TaggedItem.objects.get_by_model(Page, 
                                                 [tag_of_category(category)])
            qs = qs.filter(wiki=self, is_ephemeral=False, is_deleted=False)
        return qs
        
    def get_categories(self):
        """Return categories for a wiki. Results are cached for an hour.
        When changing categories of pages, on should call 
        'refresh_categories' to invalidate the cache."""
        return cache_key_('wiki_categories', 60*60, lambda: self.slug,
                          self._get_categories)

    def refresh_categories(self):
        invalidate_cache_key('wiki_categories', self.slug)

    def _get_categories(self):        
        def cat_cmp(x, y):
            score = lambda c: c['id'] == '__none__' and -1 or c['count']
            return cmp(score(x), score(y))
        categories = settings.CATEGORIES.copy()
        for category in categories.values():
            category['count'] = self.pages_of_category(category['id']).count()
        categories = sorted(categories.values(), cmp=cat_cmp, reverse=True)
        return categories

    def get_new_url(self):
        return reverse('wiki_new_page', kwargs=dict(wiki_slug=self.slug))

    def get_keywords(self):
        words = self.slug.split('-')
        # Quick and dirty keywords for flickr photo searches
        # TODO: Make this smarter?
        if len(words) < 2:
            # Only 1 word or less, wiki is probably a profile
            return []        
        if len(words[-1]) == 2:
            # Ends in a 2 letter word, wiki is a city, strip off state abbrev.
            return words [:-1]        
        if len(words[-1]) == 5:
            # Ends in a 5 character word (zip code), strip last two
            # words (state and zip code).
            return words [:-2]

    def __repr__(self):
        return '<Wiki: %s>' % self.slug

    def __unicode__(self):
        return self.slug

class VisiblePagesManager(models.Manager):
    def get_query_set(self):
        qs = super(VisiblePagesManager, self).get_query_set()
        qs = qs.filter(is_ephemeral=False, is_deleted=False)
        qs = qs.select_related('current_version', 'wiki')
        return qs

class Page(models.Model):
    all_objects = models.Manager()
    objects = VisiblePagesManager()

    wiki = models.ForeignKey(Wiki)

    slug = models.SlugField(max_length=settings.MAX_WIKIWORD_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now_add=True)

    photos = generic.GenericRelation(Photo)

    is_ephemeral = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    current_version = models.OneToOneField('PageVersion', null=True,
                                           related_name='unused')
    first_version = models.OneToOneField('PageVersion', null=True,
                                           related_name='unused2')

    default_cached_35px_thumb_url = \
        lambda: reverse_static_url('img/placeholder35x.png')

    @property
    def category(self):
        return category_of_object(self)

    @property
    def category_title(self):
        return title_of_category(self.category)

    @property
    def widget(self):
        from .widget import WikiWidget
        return WikiWidget.of_page(self)

    class Meta:
        unique_together = (('wiki', 'slug'))

    def host(self):
        # Cache host instances.  There's only a few and they're immutable.
        if self.wiki.host_id not in host_cache:
            host_cache[self.wiki.host_id] = self.wiki.host.cls.obj()
        return host_cache[self.wiki.host_id]

    def get_absolute_url(self):
        if self.is_ephemeral:
            return reverse('wiki_new_page',
                           kwargs={'wiki_slug': self.wiki.slug})
        else:
            return self.host().reverse_page(self.wiki.slug, self.slug)

    def get_edit_url(self):
        return self.widget.reverse('edit')

    def has_history(self):
        return self.current_version is not None

    def get_history_url(self):
        return self.widget.reverse('history')

    def get_config_photo_dialog_url(self, photo_slug):
        return self.widget.reverse('config_photo_dialog', photo_slug)

    def full_name(self):
        return '%s/%s' % (self.wiki.slug, self.slug)

    def __repr__(self):
        return '<Page: %s>' % self.slug

    def __unicode__(self):
        return self.slug

    def has_version(self):
        return (self.id is not None) and (self.current_version is not None)

    def is_embedded(self):
        return self.host().is_embedded_page(self)

    def title(self):
        if self.is_embedded():
            return None
        elif self.has_version():
            return self.current_version.title
        else:
            return self.slug

    def get_title_for_follower(self, follower=None):
        try:
            _, ctx = resolve_url_to_ctx(self.wiki.slug)
            guid_title = ctx.get('guid_title', self.wiki.slug)
        except:
            # Don't kill the thread because we can't get the fancy title
            guid_title = self.wiki.slug            
        if self.is_embedded():
            return guid_title
        else:
            return '%s (%s)' % (self.title(), guid_title)

    def get_photo(self):
        if self.has_version():
            return self.current_version.get_photo()
        else:
            return None

    @cache.cache_key('wiki_cached_35px_thumb', settings.THUMB_CACHE_TIMEOUT,
                 lambda self: '%d' % self.id)
    def get_cached_35px_thumb_url(self):
        photo = self.get_photo()
        if photo is None:
            return Page.default_cached_35px_thumb_url()
        return photo.get_thumb(width=35, height=35, aspect='crop'
                ).get_absolute_url()

    def invalidate_cached_35px_thumb(self):
        cache.invalidate_cache_key('wiki_cached_35px_thumb', '%d' % self.id)

    # TODO(marius): These are temporary hacks to that go away
    # absolutely when all things are django-templated! It's nasty to
    # mix presentation and bidness logic like this.
    def render_section(self, about, city_layout=False):
        guid = resolve_guid(self.wiki.slug)
        return render_to_string('wiki/_section.html', {
            'page': self,
            'about': about,
            'has_history': self.has_history(),
            'city_layout': city_layout,
            'guid_type': guid['type'] if guid is not None else None
        })

    def get_absolute_photo_or_thumb_url(self, photo_or_thumb):
        base, ext = os.path.splitext(photo_or_thumb.get_file_name())
        return self.widget.reverse(
            'image', media_hash=base,
            photo_slug=photo_or_thumb.get_slug(), ext=ext)

    def get_fb_type(self):
        return 'wiki'
        
    def each_link(self):
        # Circular dependency
        from www.wiki.linkgraph import each_link
        from www.wiki.render import render_page_to_stream
        return each_link(render_page_to_stream(self.current_version)) 
            
    def get_fb_as_json(self):
        return Feedback.objects.get_traits_for_current_user_as_json(self)

    def version_post_save(self, version):
        '''Update Page with new PageVersion after save.'''
        # Update fields in Page
        save_page = False

        # Update page.first_version
        if version.version == 1:
            self.first_version = version
            save_page = True

        # Update page.current_version
        if self.current_version:
            if self.current_version != version:
                if self.current_version.version < version.version:
                    self.current_version = version
                    save_page = True
        else:
            self.current_version = version
            save_page = True

        # Update page.modified_on
        if self.current_version == version:
            self.modified_on = version.created_at
            save_page = True

        # Update page.is_deleted
        is_deleted = self.current_version.body.strip() == ''
        if self.is_deleted != is_deleted:
            self.is_deleted = is_deleted
            save_page = True

        if save_page:
            self.save()
            self.invalidate_cached_35px_thumb()

    def each_related_page(self):
        from . import linkgraph         # circular.

        related_ids = [self.id]
        related = itertools.chain(linkgraph.each_related_page(self),
                                  self.wiki.pages_of_category(self.category))
        for page in related:
            if page.id not in related_ids:
                related_ids.append(page.id)
                yield page


_editable_fields = set([
    'title',
    'body'
])

photo_slug_re = re.compile(r'<<img ([\w-]+)')

class PageVersion(models.Model):
    def __init__(self, *args, **kwargs):
        super(PageVersion, self).__init__(*args, **kwargs)
        self._new_category = None

    page = models.ForeignKey(Page)

    title = models.CharField(max_length=settings.MAX_WIKIWORD_LENGTH)
    body = models.TextField()

    version = models.IntegerField(default=1)

    # Data integrity stuff.
    previous = models.ForeignKey('self', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    edit_user = models.ForeignKey(User, null=True)
    edit_ip_address = models.IPAddressField(default='0.0.0.0')

    # True for changes maked as bad, and Lil'b's revert
    is_hidden_change = models.BooleanField(default=False)

    def dup(self):
        """Return a fresh duplicate of this version. Good for creating
        new versions. Doesn't include edit-specific things like user &
        IP."""
        new       = PageVersion(page=self.page)
        new.title = self.title
        new.body  = self.body

        return new

    def category_fget(self):
        """The *category* of the wiki, is one of the strings in the
        CATEGORIES setting."""
        if self._new_category is not None:
            return self._new_category
        else:
            return category_of_object(self)

    def category_fset(self, value):
        """Set the category for this page, we check that the string is
        a member of the CATEGORIES setting."""
        if value not in settings.CATEGORIES:
            raise ValueError, \
                'Category must be one of %r' % settings.CATEGORIES.keys()

        self._new_category = value

    category = property(category_fget, category_fset)

    def __unicode__(self):
        return '%s: %s' % (self.page.slug, self.created_at)

    if not all_settings.WIDGETS_DEFAULT:
        class ChangesMeta:
            change_type = 'page'
            time_field = 'created_at'
            timeval_field = 'created_at'
            user_field = 'edit_user'
            user_ip_field = 'edit_ip_address'
    
            @staticmethod
            def verb(vsn):
                return 'deleted' if vsn.body.strip() == '' else 'edited'
    
            # NOTE: Not stricly accurate since this only gets pages that
            # are rooted under the town, but not pages that are rooted
            # under entities that are contained in that town. But there
            # are extremely few such pages anyway, and we might even phase
            # those out, so for an emergency fix this works OK.
            town_guid_field = 'page__wiki__slug'
    
            @staticmethod
            def title(vsn):
                return vsn.page.get_title_for_follower()
    
            @staticmethod
            def get_url(vsn):
                """Return the URL of the parent page."""
                return vsn.page.get_absolute_url()
    
            @staticmethod
            def get_no_follow(vsn):
                """Return whether the links to the change should be no-follow."""
                return vsn.page.is_deleted
    
            @staticmethod
            def get_is_hidden(vsn):
                return vsn.is_hidden_change

    class Meta:
        # TODO: should this just use the pk instead?
        get_latest_by = "created_at"
        ordering = ("-created_at",)
        unique_together = (('page', 'version'))

    def get_absolute_url(self):
        return self.page.widget.reverse('version', self.version)

    def get_user_and_ip(self):
        return self.edit_user, self.edit_ip_address
    
    def get_photo(self):
        match = photo_slug_re.search(self.body)
        if not match:
            return None
        return get_or_none(self.page.photos, slug=match.group(1))

    def get_cached_35px_thumb_url(self):
        return self.page.get_cached_35px_thumb_url()

    def save(self, force_insert=False, force_update=False):
        # Force page save since self references.
        if self.page.pk is None:
            self.page.save()

        # On first save, set previous and version based on newest version
        if self.pk is None:
            try:
                self.previous = self.page.pageversion_set.latest('version')
                self.version  = self.previous.version + 1
            except PageVersion.DoesNotExist:
                self.previous = None
                self.version  = 1

        super(PageVersion, self).save(force_insert, force_update)

        # After save, we update the category, since it needs a saved
        # object (pk) and invalidate the category cache for the wiki.
        if self._new_category is not None:
            tag = tag_of_category(self._new_category)
            Tag.objects.update_tags(self, tag)
            Tag.objects.update_tags(self.page, tag)
            self.page.wiki.refresh_categories()

        self.page.version_post_save(self)

        # Send the notifications after any de-normalization
        self.notify_followers_post_save()

    def notify_followers_post_save(self):
        if self.page.is_ephemeral or self.is_hidden_change:
            return
        prev = self.previous
        if prev and ((self.edit_user and
                      prev.edit_user == self.edit_user) or
                     (not self.edit_user and not prev.edit_user and
                      prev.edit_ip_address == self.edit_ip_address)) and (
                self.created_at - prev.created_at <
                datetime.timedelta(minutes=30)):
            # Don't notify adjacent edits from the same user or anon ip within
            # 30 minutes of each other
            return        
        from www.notify.actions import (follow_url_on_first_user_action,
                email_edit_to_other_followers)
        if prev or self.page.is_embedded():
            mode = 'E'
        else:
            mode = 'C'
        follow_url_on_first_user_action(self.page.get_absolute_url(),
                self.edit_user, mode)
        email_edit_to_other_followers(self.page, self.get_user_and_ip())

    def has_changed(self):
        if self._new_category is not None:
            return True

        try:
            old = self.page.pageversion_set.latest()

            old_fields = [getattr(old, f, None) for f in _editable_fields]
            new_fields = [getattr(self, f, None) for f in _editable_fields]

            return old_fields != new_fields

        except PageVersion.DoesNotExist:
            return True

    def possum_eat(self):
        """ Rather than deleting the page version, mark it as hidden.  If it's
        the latest version, create a version from lilb that reverts it. """
        self.is_hidden_change = True
        self.save()
        if self.page.current_version != self:
            return
        # Create a followup version as lilb that duplicates the latest
        # non-hidden version, or empty (delete) if they are all hidden
        last_good_vsn = self
        while last_good_vsn and last_good_vsn.is_hidden_change:
            last_good_vsn = last_good_vsn.previous
        if last_good_vsn:
            revert_vsn = last_good_vsn.dup()
        else:
            revert_vsn = PageVersion(page=self.page, title=self.title, body='')
        revert_vsn.edit_user = User.objects.get(username='lilb')
        revert_vsn.is_hidden_change = True
        revert_vsn.save()


def attachment_upload_to(instance, filename):
    # Strip the initial '/'
    return posixpath.join(instance.page.get_absolute_url(), instance.name)[1:]

class Attachment(models.Model):
    page = models.ForeignKey(Page)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    attachment = models.FileField(upload_to='n/a',
                                  max_length=200,
                                  storage=media_file_storage)

    file_name = models.CharField(max_length=100)
    file_content_type = models.CharField(max_length=100)
    file_normalized_extension = models.CharField(max_length=6)

    name = models.SlugField(max_length=50)

    caption = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return '%s, %s, %s' % (self.name, self.file_name, self.file_content_type)

    class Meta:
        unique_together = (('page', 'name'))

    def get_absolute_url(self):
        return reverse('wiki_attachments',
                       kwargs=dict(wiki_slug=self.page.wiki.slug,
                                   slug=self.page.slug,
                                   attachment_slug=self.name,
                                   ext=self.file_normalized_extension))
