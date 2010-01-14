
from south.db import db
from django.db import models
from www.wiki.models import *

class Migration:
    
    def forwards(self, orm):
        db.add_column('wiki_pageversion', 'is_hidden_change',
            models.BooleanField(default=False))

    def backwards(self, orm):
        db.delete_column('wiki_pageversion', 'is_hidden_change')
    
    
    models = {
        'wiki.pageversion': {
            'Meta': {'ordering': '("-created_at",)', 'unique_together': "(('page','version'))", 'get_latest_by': '"created_at"'},
            'body': ('models.TextField', [], {}),
            'created_at': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'edit_ip_address': ('models.IPAddressField', [], {'default': "'0.0.0.0'"}),
            'edit_user': ('models.ForeignKey', ['User'], {'null': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'is_hidden_change': ('models.BooleanField', [], {'default': 'False'}),
            'page': ('models.ForeignKey', ['Page'], {}),
            'previous': ('models.ForeignKey', ["'self'"], {'null': 'True', 'blank': 'True'}),
            'title': ('models.CharField', [], {'max_length': 'settings.MAX_WIKIWORD_LENGTH'}),
            'version': ('models.IntegerField', [], {'default': '1'})
        },
        'wiki.page': {
            'Meta': {'unique_together': "(('wiki','slug'))"},
            'created_at': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'current_version': ('models.OneToOneField', ["'PageVersion'"], {'related_name': "'unused'", 'null': 'True'}),
            'first_version': ('models.OneToOneField', ["'PageVersion'"], {'related_name': "'unused2'", 'null': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'is_deleted': ('models.BooleanField', [], {'default': 'False'}),
            'is_ephemeral': ('models.BooleanField', [], {'default': 'False'}),
            'modified_on': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            # 'photos': ('generic.GenericRelation', ['Photo'], {}),
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
            'attachment': ('models.FileField', [], {'storage': 'media_file_storage', 'max_length': '200', 'upload_to': "'n/a'"}),
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
