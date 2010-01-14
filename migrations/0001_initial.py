
from south.db import db
from django.db import models
from www.wiki.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'WikiHost'
        db.create_table('wiki_wikihost', (
            ('cls', PyObjectField()),
            ('id', models.AutoField(primary_key=True)),
            ('name', models.SlugField(unique=True, max_length=50)),
        ))
        db.send_create_signal('wiki', ['WikiHost'])
        
        # Adding model 'Attachment'
        db.create_table('wiki_attachment', (
            ('file_normalized_extension', models.CharField(max_length=6)),
            ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ('name', models.SlugField(max_length=50)),
            ('file_name', models.CharField(max_length=100)),
            ('file_content_type', models.CharField(max_length=100)),
            ('page', models.ForeignKey(orm.Page)),
            ('caption', models.TextField(null=True, blank=True)),
            ('attachment', models.FileField(storage=media_file_storage, max_length=media_file_storage.MAX_NAME_LEN, upload_to='n/a')),
            ('id', models.AutoField(primary_key=True)),
        ))
        db.send_create_signal('wiki', ['Attachment'])
        
        # Adding model 'PageVersion'
        db.create_table('wiki_pageversion', (
            ('body', models.TextField()),
            ('comment', models.CharField(max_length=200, blank=True)),
            ('edit_user', models.ForeignKey(orm['auth.User'], null=True)),
            ('title', models.CharField(max_length=settings.MAX_WIKIWORD_LENGTH)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('page', models.ForeignKey(orm.Page)),
            ('version', models.IntegerField(default=1)),
            ('id', models.AutoField(primary_key=True)),
            ('edit_ip_address', models.IPAddressField(default='0.0.0.0')),
            ('previous', models.ForeignKey(orm.PageVersion, null=True, blank=True)),
        ))
        db.send_create_signal('wiki', ['PageVersion'])
        
        # Adding model 'Page'
        db.create_table('wiki_page', (
            ('wiki', models.ForeignKey(orm.Wiki)),
            ('is_ephemeral', models.BooleanField(default=False)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('id', models.AutoField(primary_key=True)),
            ('slug', models.SlugField(max_length=settings.MAX_WIKIWORD_LENGTH)),
        ))
        db.send_create_signal('wiki', ['Page'])
        
        # Adding model 'Wiki'
        db.create_table('wiki_wiki', (
            ('host', models.ForeignKey(orm.WikiHost)),
            ('slug', models.SlugField(unique=True, max_length=200, primary_key=True)),
        ))
        db.send_create_signal('wiki', ['Wiki'])
        
        # Creating unique_together for [wiki, slug] on Page.
        db.create_unique('wiki_page', ['wiki_id', 'slug'])
        
        # Creating unique_together for [page, version] on PageVersion.
        db.create_unique('wiki_pageversion', ['page_id', 'version'])
        
        # Creating unique_together for [page, name] on Attachment.
        db.create_unique('wiki_attachment', ['page_id', 'name'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'WikiHost'
        db.delete_table('wiki_wikihost')
        
        # Deleting model 'Attachment'
        db.delete_table('wiki_attachment')
        
        # Deleting model 'PageVersion'
        db.delete_table('wiki_pageversion')
        
        # Deleting model 'Page'
        db.delete_table('wiki_page')
        
        # Deleting model 'Wiki'
        db.delete_table('wiki_wiki')
        
        # Deleting unique_together for [wiki, slug] on Page.
        db.delete_unique('wiki_page', ['wiki_id', 'slug'])
        
        # Deleting unique_together for [page, version] on PageVersion.
        db.delete_unique('wiki_pageversion', ['page_id', 'version'])
        
        # Deleting unique_together for [page, name] on Attachment.
        db.delete_unique('wiki_attachment', ['page_id', 'name'])
        
    
    
    models = {
        'wiki.pageversion': {
            'Meta': {'ordering': '("-created_at"),', 'unique_together': "(('page','version'))", 'get_latest_by': '"created_at"'},
            'body': ('models.TextField', [], {}),
            'comment': ('models.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'created_at': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'edit_ip_address': ('models.IPAddressField', [], {'default': "'0.0.0.0'"}),
            'edit_user': ('models.ForeignKey', ['User'], {'null': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'page': ('models.ForeignKey', ['Page'], {}),
            'previous': ('models.ForeignKey', ["'self'"], {'null': 'True', 'blank': 'True'}),
            'title': ('models.CharField', [], {'max_length': 'settings.MAX_WIKIWORD_LENGTH'}),
            'version': ('models.IntegerField', [], {'default': '1'})
        },
        'wiki.page': {
            'Meta': {'unique_together': "(('wiki','slug'))"},
            'created_at': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'is_ephemeral': ('models.BooleanField', [], {'default': 'False'}),
            'slug': ('models.SlugField', [], {'max_length': 'settings.MAX_WIKIWORD_LENGTH'}),
            'wiki': ('models.ForeignKey', ['Wiki'], {})
        },
        'auth.user': {
            '_stub': True,
            'id': ('models.AutoField', [], {'primary_key': 'True'})
        },
        'wiki.wikihost': {
            'cls': ('PyObjectField', [], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'name': ('models.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        'wiki.attachment': {
            'Meta': {'unique_together': "(('page','name'))"},
            'attachment': ('models.FileField', [], {'storage': 'media_file_storage', 'max_length': 'media_file_storage.MAX_NAME_LEN', 'upload_to': "'n/a'"}),
            'caption': ('models.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file_content_type': ('models.CharField', [], {'max_length': '100'}),
            'file_name': ('models.CharField', [], {'max_length': '100'}),
            'file_normalized_extension': ('models.CharField', [], {'max_length': '6'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'name': ('models.SlugField', [], {'max_length': '50'}),
            'page': ('models.ForeignKey', ['Page'], {}),
            'uploaded_at': ('models.DateTimeField', [], {'auto_now_add': 'True'})
        },
        'wiki.wiki': {
            'host': ('models.ForeignKey', ['WikiHost'], {}),
            'slug': ('models.SlugField', [], {'unique': 'True', 'max_length': '200', 'primary_key': 'True'})
        }
    }
    
    complete_apps = ['wiki']
