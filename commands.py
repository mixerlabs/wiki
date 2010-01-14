import sys

class Commands(object):
    descr = 'Wiki'

    def cmd_pack(self, wiki_slug, page_slug, path):
        """Pack the addressed wiki page to `path'"""
        import conf; conf.configure_django('www.settings')
        from www.wiki.models import Page
        from www.wiki.pack   import pack

        page = Page.objects.get(wiki__slug=wiki_slug, slug=page_slug)
        pack(page, path)

    def cmd_unpack(self, path, wiki_slug=None, page_slug=None, force=False):
        """Unpack the page at `path' onto this system"""
        import conf; conf.configure_django('www.settings')
        from www.wiki.pack import unpack
        unpack(path, wiki_slug=wiki_slug, page_slug=page_slug, force=force)

COMMANDS = Commands()
