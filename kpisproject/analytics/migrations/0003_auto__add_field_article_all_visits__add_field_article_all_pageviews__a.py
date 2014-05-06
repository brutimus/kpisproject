# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Article.all_visits'
        db.add_column(u'analytics_article', 'all_visits',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Article.all_pageviews'
        db.add_column(u'analytics_article', 'all_pageviews',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Article.all_time_on_page'
        db.add_column(u'analytics_article', 'all_time_on_page',
                      self.gf('django.db.models.fields.IntegerField')(null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Article.all_visits'
        db.delete_column(u'analytics_article', 'all_visits')

        # Deleting field 'Article.all_pageviews'
        db.delete_column(u'analytics_article', 'all_pageviews')

        # Deleting field 'Article.all_time_on_page'
        db.delete_column(u'analytics_article', 'all_time_on_page')


    models = {
        u'analytics.article': {
            'Meta': {'object_name': 'Article'},
            'all_pageviews': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'all_time_on_page': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'all_visits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
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