# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding M2M table for field editor on 'Byline'
        m2m_table_name = db.shorten_name(u'analytics_byline_editor')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_byline', models.ForeignKey(orm[u'analytics.byline'], null=False)),
            ('to_byline', models.ForeignKey(orm[u'analytics.byline'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_byline_id', 'to_byline_id'])


    def backwards(self, orm):
        # Removing M2M table for field editor on 'Byline'
        db.delete_table(db.shorten_name(u'analytics_byline_editor'))


    models = {
        u'analytics.article': {
            'Meta': {'object_name': 'Article'},
            'bylines': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['analytics.Byline']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['analytics.Category']", 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'pageviews': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['analytics.Status']"}),
            'time_on_page': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'visits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'analytics.byline': {
            'Meta': {'object_name': 'Byline'},
            'editor': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['analytics.Byline']", 'symmetrical': 'False'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        u'analytics.category': {
            'Meta': {'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'})
        },
        u'analytics.status': {
            'Meta': {'object_name': 'Status'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'})
        }
    }

    complete_apps = ['analytics']