"""A utility to pack a wiki page into a completely self-contained
format (which includes pictures, etc, too.)"""
from __future__ import absolute_import

import sys
import os.path
import zipfile
import simplejson
import StringIO

from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.models   import User

from www.common.models         import Photo
from www.common.temporary_file import TemporaryFile

from www.wiki.models import Wiki, Page, PageVersion

class JSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, User):
            return o.username
        else:
            return super(JSONEncoder, self).default(o)

def user_or_default(username, default):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return User.objects.get(username=default)

def dict_to_attrs(obj, dict):
    for k, v in dict.items():
        setattr(obj, k, v)

def attrs_to_dict(obj, attrs):
    return dict((attr, getattr(obj, attr))
                for attr in attrs
                if getattr(obj, attr) is not None)

PAGE_ATTRS    = ['slug', 'created_at']
PHOTO_ATTRS   = ['user', 'ip_address', 'width', 'height', 'size',
                 'uploaded_at', 'caption', 'slug', 'attributes']
VERSION_ATTRS = ['title', 'body', 'version', 'created_at', 'edit_user',
                 'edit_ip_address', 'is_hidden_change', 'category']

def pack(page, path):
    """Pack the wiki page object `page' to the given (filesystem)
    path."""

    if os.path.exists(path):
        raise ValueError, '%s already exists!' % path

    meta = {
        'wiki_slug' : page.wiki.slug,
        'page'      : attrs_to_dict(page, PAGE_ATTRS),
        'photos'    : dict((p.image.name, attrs_to_dict(p, PHOTO_ATTRS))
                           for p in page.photos.all()),
        'versions'  : [attrs_to_dict(v, VERSION_ATTRS)
                       for v in page.pageversion_set.all()]
    }

    z = zipfile.ZipFile(path, 'w')
    z.writestr('meta.json', simplejson.dumps(meta, cls=JSONEncoder))
    for photo in page.photos.all():
        z.writestr(photo.image.name, photo.image.read())
    z.close()

def unpack(path, default_user='mixerlabs',
           wiki_slug=None, page_slug=None,
           force=False):
    """Unpack the packed page at `path', assigning user to the named
    default user if the given user does not exist on the target
    system. If wiki and/or page slugs are specified, these are
    overriden."""
    meta = unpack_raw(path)

    wiki_slug = wiki_slug or meta['wiki_slug']
    page_slug = page_slug or meta['page']['slug']

    import www.wiki.views  # Circular.
    wiki = www.wiki.views._get_wiki_or_create(wiki_slug)

    if force:
        try:
            page = Page.objects.get(wiki=wiki, slug=page_slug)
            page.photos.all().delete()
            page.delete()
        except Page.DoesNotExist:
            pass

    page = Page(wiki=wiki)
    dict_to_attrs(page, meta['page'])
    page.slug = page_slug
    page.save()

    # Fix up created at since it's an auto_now_add field.
    page.created_at = meta['page']['created_at']

    for v in sorted(meta['versions'], key=lambda v: v['version']):
        version = PageVersion()
        v['edit_user'] = user_or_default(v['edit_user'], default_user)
        dict_to_attrs(version, v)
        version.is_hidden_change = True
        version.page = page
        version.save()
        # Fix up created at since it's an auto_now_add field.
        version.created_at = v['created_at']
        version.save()

    for name, p in meta['photos'].items():
        photo = Photo()
        file = p.pop('file')
        p['user'] = user_or_default(p['user'], default_user)
        dict_to_attrs(photo, p)

        # We need to create a temporary file because of .chunks()
        tempfile = TemporaryFile(file.name)
        tempfile.write(file.read())
        tempfile.seek(0)
        photo.image.save(file.name, tempfile, False)
        tempfile.close_and_delete_if_not_moved()
        page.photos.add(photo)
        photo.save()

    page.save()
    return meta

def unpack_raw(path):
    """Unpack the packed page at `path' into a "raw" state -- that is,
    we give you the meta dictionary with merged photo file
    objects."""
    z = zipfile.ZipFile(path, 'r')
    meta = simplejson.loads(z.read('meta.json'))
    for photo in meta['photos']:
        meta['photos'][photo]['file'] = StringIO.StringIO(z.read(photo))

    return meta
