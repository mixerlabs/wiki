"""Settings for the wiki app.

Note that these may be overriden by the same names, prefixed by
'WIKI_' in the root django config.

ie. if we define here:

  SETTING = 'foo'

and in the main django settings module:

  WIKI_SETTING = 'bar'

it overrides the former."""

# TODO: Once all traffic is migrated to widgets, move settings over to the 
# widgets app.

from textwrap import dedent
from datetime import datetime, timedelta
import yaml

from util.files import mixer_open
from www.common.templatetags.static import reverse_static_url

# The wiki word definition. Always start with a capital letter, after
# that any alphanumeric will do (including '_')
WIKIWORD_RE = r'[A-Z0-9][a-zA-Z0-9-]+'
ATTACHMENT_BUCKET = 'wiki.mixerlabs.com'

# GUID stuff
GUID_NUM_RECENT_WIKIS = 5

# NOTE! changing most likely requires database migrations.
MAX_WIKIWORD_LENGTH = 100

DEFAULT_STUB_CONTENT = dedent('''
This page is a "stub page". Click edit and write something!
Be the first to make it a real page!''')

# The name of the "home" page for wikis hosted by GUIDs.
GUID_HOME_PAGE_NAME = 'Home'

# Other special slugs
GUID_TWITTER_PAGE_SLUG = 'Twitter-directory'
GUID_BIRTHDAY_PAGE_SLUG = 'Free-birthday-stuff-deals-and-freebies'

EPHEMERAL_PAGE_EXPIRY = timedelta(days=1)

TINYMCE_WORKAROUNDS = {
    'list_item_linking': True,
}

# Note that the categories have pretty strick type checking on them,
# so if we ever remove categories, we'll need to alter the
# typechecking.
CATEGORIES = yaml.load(mixer_open('www/wiki/etc/categories.yaml').read())
for k,v in CATEGORIES.items():
    v['id'] = k
    v['icon_url'] = reverse_static_url('img/wikicat-%s25x2.png' % \
                                       v['icon'])

# Set this to true to verify that a page renders sucesfully before
# allowing it to be saved.
VERIFY_RENDER_BEFORE_SAVE = True

# Domains for which we don't add nofollow links
FOLLOW_DOMAINS = ['www.townme.com', 'townme.com']

# Cache page thumbnail urls for 1 week
THUMB_CACHE_TIMEOUT = 3600 * 24 * 7

# Pages created before the wiki's birthday are system pages and are
# excluded from each_recent_page.
WIKI_BIRTHDAY = datetime(2009, 2, 2)
