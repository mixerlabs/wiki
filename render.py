"""utilities used to render wiki pages"""

import re

from ext.creoleparser.core import Parser as creole_Parser
from ext.creoleparser.dialects import dialect_base as creole_dialect_base
from ext.creoleparser.elements import WikiLink as creole_WikiLink
from django.core.urlresolvers import reverse, NoReverseMatch
from functools import partial
from models import Attachment
import genshi.builder as bldr
import genshi.core
from genshi import escape
from genshi.filters.transform import Transformer
from util import *
from www.common.models import Photo
import os.path
from util.rect import scale_dimensions
import urllib
import urlparse

log = mixlog()

# Our thumb size defaults to 150px, 1/4 the page width (wikipedia uses 180)
default_thumb_width = 150

max_image_width = 600

_size_width_re = re.compile(r'(\d+)px$')
_size_width_and_height_re = re.compile(r'(\d+)x(\d+)px$')
_alt_re = re.compile(r'alt=(.*)$')
_align_re = re.compile(r'(left|center|right|none)$')
_type_re = re.compile(r'(frame|thumb|thumbnail|border)$')

def parse_img_attributes(photo, arglist):
    """ Parses the attributes for the wiki macro <<img image|arg1|arg2|...>>
    and returns a storage dict of values.  Syntax of args mirrors wikipedia
    as close as possible: http://en.wikipedia.org/wiki/Image_markup
    Values are cleaned to handle various edge cases; "size" value is always set
    to the computed display size.  "photo" is the photo object already resovled
    by the caller. "arglist" is a list of attributes already split on '|'. """
    attrs = storage()

    def align(match):
        # With align, first one wins (verified using wikipedia's sandbox)
        try:
            return attrs.align
        except AttributeError:
            return match.group(1)

    def img_type(match):
        # With type, there is a priority system (like Wikipedia)
        old = attrs.get('type', None)
        new = match.group(1)
        for value in ('frame', 'thumb', 'thumbnail', 'border'):
            if old == value or new == value:
                return value
        raise sym.wtf_XXX.exc()
        
    attr_rules = (
        (
            _size_width_re, 'size', lambda match:
                    photo.get_scaled_dimensions(int(match.group(1)))
        ), (
            _size_width_and_height_re, 'size', lambda match:
                    (int(match.group(1)), int(match.group(2)))
        ), (
            _alt_re, 'alt', lambda match: match.group(1)
        ), (
            _align_re, 'align', align
        ), (
            _type_re, 'type', img_type
        )
    )
    
    # Skip arg 0, it is the slug of the photo.
    for arg in arglist[1:]:
        for rule in attr_rules:
            match = rule[0].match(arg)
            if (match):
                attrs[rule[1]] = rule[2](match)
                break
        else:
            # Unrecognized arguments become the caption; last one wins.
            attrs.caption = arg.strip()

    type = attrs.get('type', None)
    if type == 'frame' and 'size' in attrs:
        # Frame not allowed to specify size
        del attrs.size
    if type in ('thumb', 'thumbnail'):
        if 'size' not in attrs:
            attrs.size = photo.get_scaled_dimensions(default_thumb_width)
    if type in ('thumb', 'thumbnail', 'frame') and 'align' not in attrs:
        # Thumb and frame alignment default to right.
        attrs.align = 'right'
    if 'size' not in attrs:
        # Always define a size for html; default to full.
        attrs.size = (photo.width, photo.height)
    if attrs.size[0] > max_image_width:
        # Anything wider than the screen will be scaled down
        attrs.size = scale_dimensions((max_image_width, None), attrs.size)
    return attrs


def wiki_img_clean_caption(caption):
    caption = caption.replace('\n', ' ').replace('|', ':').replace(
            '>>', '>').strip()
    if re.match(r'left|right|center|frame|thumb|thumbnail|border|none|'
            '(\d+x)?\d+px', caption):
        caption = "- %s" % caption
    return caption


def wiki_img_args_to_html(page, editing, args):
    """ Returns the html rendering of a wiki image given a page object and
    the args string from the <<img args>> wiki macro.  If editing is true,
    the html is customized for use inside the tinymce editor. """
    arglist = args.strip().split('|')
    # Arg 0 is the slug of the photo
    photo = page.photos.get(slug=arglist[0])
    attrs = parse_img_attributes(photo, arglist)
    try:
        thumb = photo.get_thumb(attrs.size[0], attrs.size[1], 'Stretch')
    except IOError, e:
        # If an image is missing from the media folder, don't kill the page
        log.warn('Cannot render photo %s for %s %s' % (arglist[0],
                page.get_absolute_url(), e))
        thumb = None

    align = attrs.get('align', None)
    caption = None
    if 'caption' in attrs:
        caption = escape(attrs.caption)
    type = attrs.get('type', None)
    alt_text = escape(attrs.alt) if 'alt' in attrs else caption    
    has_frame = type in ('thumb', 'thumbnail', 'frame')
    table_frame = has_frame and caption and not editing
    img_frame = has_frame and not table_frame

    # Build the image element first.
    img_src = thumb.get_absolute_url() if thumb is not None else ''
    if editing:
        # Save the original args in the url as a dummy query string.
        # In google chrome and windows safari, only the src attribute
        # of a dragged image survives. 
        img_src += '?wiki_img_args=' + urllib.quote(args.strip())        
    img_attrs = [
        'src="%s"' % escape(img_src),
        'width="%d"' % attrs.size[0],
        'height="%d"' % attrs.size[1]
    ]
    if editing and caption:
        img_attrs.append('title="%s"' % caption)
    if alt_text:
        img_attrs.append('alt="%s"' % alt_text)
    img_classes = []
    if align and not table_frame:
        img_classes.append('wiki_img_%s' % align)
    if type == 'border':
        img_classes.append('wiki_img_border')
    if img_frame:
        img_classes.append('wiki_img_frame')
        if caption:
            img_classes.append('wiki_img_fake_caption')        
    if img_classes:
        img_attrs.append('class="%s"' % ' '.join(img_classes))
    html = '<img %s />' % ' '.join(img_attrs)

    # Wrap the image in a link when not in the editor.        
    if not editing:
        link_title = caption
        if not link_title:
            base, ext = os.path.splitext(photo.get_file_name())
            link_title = escape(photo.get_slug() + ext)
        html = '<a class="wiki_img_link" href="%s" title="%s">%s</a>' % (
                escape(photo.get_attribution_url()), link_title, html)

    # Create a frame around the image with a caption using a table
    # to force the width of the caption to match the contained image.
    if table_frame:
        html = ('<table class="wiki_img_frame"><tr><td>'
                '<div class="wiki_img_frame">%s'
                '<div class="wiki_img_caption">%s</div></div>'
                '</td></tr></table>') % (html, caption)
        # Wrap the frame with an alignment div.
        if align:
            html = '<div class="wiki_img_%s">%s</div>' % (align, html)        
        
    return html

    
    
def _macro(page, editing, method, name, args, body, is_block, creole_page):
    if method == 'text':
        return ''
    if name == 'img':
        try:
            return genshi.core.Markup(wiki_img_args_to_html(page, editing, args))
        except Photo.DoesNotExist:
            # TODO: Deprecate images as attachments soon
            name = args.split()[0]
            try:
                a = page.attachment_set.get(name=name)
                return genshi.core.Markup(
                    '<img src="%s" />' % a.get_absolute_url())
            except (Attachment.DoesNotExist, NoReverseMatch):
                return '##Error! No such image %s##' % name
    else:
        return None

def make_creole_dialect(page, editing, method):
    def link(ref):
        # First see if it's an interwiki link.
        res = ref.split(':', 1)
        if len(res) == 1:
            wiki_slug = page.wiki.slug
            page_slug = res[0]
        else:
            wiki_slug = res[0]
            page_slug = res[1]

        try:
            linked = reverse('wiki_page', kwargs=dict(wiki_slug=wiki_slug, slug=page_slug))
        except NoReverseMatch:
            # TODO(marius): Robust? I think we should log this.
            linked = ref

        return linked

    # TODO(marius): fix this up so that we can pass in the page on
    # class instantiation instead of definition. Can we use the page
    # kwarg to do that?
    Base = creole_dialect_base(
        use_additions=True,
        no_wiki_monospace=True,
        wiki_links_base_url='',
        wiki_links_path_func=link,
        macro_func=partial(_macro, page, editing, method))

    class WikiMarkup(Base):
        # We do our own interwiki parsing so that we don't have to
        # jigger up the creole library.
        interwiki_link = Base.wiki_link
        
    return WikiMarkup()


def render_page_to_stream(version, editing=False, method='xhtml'):
    """Render the PageVersion `version' to a Genshi stream."""
    if version is None:
        return ''
    return render_wiki_to_stream(version.page, version.body,
                                 editing, method)

def render_wiki_to_stream(page, body, editing=False, method='xhtml'):
    dialect = make_creole_dialect(page, editing, method)
    creole = creole_Parser(dialect=dialect, method=method)
    return creole.generate(body)

def render_page(version, editing=False, method='xhtml'):
    """Render the PageVersion `version' to HTML."""
    if version is None:
        return ''
    return render_wiki_markup(version.page, version.body, editing, method)

def render_page_for_edit(version):
    return render_page(version, True)

def render_wiki_markup(page, body, editing=False, method='xhtml'):
    """Render the marked up text in `body' for the given `page'."""
    # Circular import
    from . import settings    
    html = render_wiki_to_stream(page, body, editing, method)

    def set_nofollow(name, event):
        if len(event) < 2 or len(event[1]) < 2:
            return None
        href = event[1][1].get('href')
        if href:
            _, host, _, _, _, _ = urlparse.urlparse(href)
            if host and host not in settings.FOLLOW_DOMAINS:
                return 'nofollow'
        return None

    html = html | Transformer('a').attr('rel', set_nofollow)
    return html.render(method=method)
