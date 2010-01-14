from models import Page, PageVersion, Wiki
from django.contrib import admin

class PageVersionInline(admin.StackedInline):
    model = PageVersion
    max_num = 3

    fieldsets = (
        (None, {
            'fields': ('title', 'body', 'edit_user', 'edit_ip_address')
        }),
    )


class PageAdmin(admin.ModelAdmin):
    inlines = [
        PageVersionInline,
    ]

    list_display = ('full_name',)
    search_fields = ('slug',)
    list_filter = ('created_at',)

    fieldsets = (
        (None, {
            'fields': ('wiki', 'slug',)
        }),
    )

class PageInline(admin.StackedInline):
    model = Page
    max_num = 5

class WikiAdmin(admin.ModelAdmin):
    inlines = [
        PageInline,
    ]

    list_display = ('slug',)
    search_fields = ('slug',)

    fieldsets = (
        (None, {
            'fields': ('slug',)
        }),
    )

admin.site.register(Page, PageAdmin)
admin.site.register(Wiki, WikiAdmin)

