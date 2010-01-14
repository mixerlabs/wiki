"""Utilities for wiki."""

import re
import random
import uuid
from string import Template
from itertools import islice, chain

from django.conf import settings as dsettings
from django.forms.forms import BoundField
from django.utils.safestring import mark_safe

from util import *
from util.functional import memoize
from util.files import mixer_open
from environment import env

from ext.plone_normalizer.base import baseNormalize as normalize_to_ascii

import settings as wsettings

class WikiSettings(object):
    """Get a wiki setting -- first try in the main django settings,
    and if that doesn't exist, try wiki.settings."""

    def __getattr__(self, key):
        try:
            return getattr(dsettings, 'WIKI_%s' % key)
        except AttributeError:
            return getattr(wsettings, key)

settings = WikiSettings()

def wikiword_to_title(wikiword, separator='-'):
    return ' '.join(wikiword.split(separator))


_valid_char_ranges = (('A', 'Z'),
                      ('a', 'z'),
                      ('0', '9'),
                      ('-', '-'))

_valid_chars = set(
    map(chr, chain(*[range(ord(start), ord(end)+1) for start, end in _valid_char_ranges])))

def title_to_wikiword(title, separator='-'):
    """Provides a default suggestion for a valid wiki word given a
    title. Raises sym.invalid_title if we cannot convert the title
    successfully."""
    words = map(normalize_to_ascii, title.split())

    wikiword = separator.join(words)

    # Truncate if necessary.
    wikiword = wikiword[:settings.MAX_WIKIWORD_LENGTH]
    # Strip invalid chars
    wikiword = filter(_valid_chars.__contains__, wikiword)
    # Make sure we're capitalized
    wikiword = wikiword.capitalize()

    if re.search(r'^%s$' % settings.WIKIWORD_RE, wikiword):
        return wikiword
    else:
        raise sym.invalid_title.exc(wikiword)

def random_wikiword():
    return title_to_wikiword(str(uuid.uuid1()))

# Modified from http://www.djangosnippets.org/snippets/316/
class HiddenFormMixin(object):
    def as_hidden(self):
        """Returns this form rendered entirely as hidden fields."""
        output = []
        for name, field in self.fields.items():
            bf = BoundField(self, field, name)
            output.append(bf.as_hidden())

        return mark_safe(u'\n'.join(output))
