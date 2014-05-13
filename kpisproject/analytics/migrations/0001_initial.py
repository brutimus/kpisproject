# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Site'
        db.create_table(u'analytics_site', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('edit_url', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('view_url', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('ga_table', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('dma', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal(u'analytics', ['Site'])

        # Adding model 'Stats'
        db.create_table(u'analytics_stats', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('visits', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('pageviews', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('time_on_page', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'analytics', ['Stats'])

        # Adding model 'Article'
        db.create_table(u'analytics_article', (
            ('id', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('headline', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['analytics.Site'])),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['analytics.Category'], null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['analytics.Status'])),
            ('raw_byline_text', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('raw_category_text', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('raw_status_text', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
            ('stats_day', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='stats_day', unique=True, null=True, to=orm['analytics.Stats'])),
            ('stats_day_local', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='stats_day_local', unique=True, null=True, to=orm['analytics.Stats'])),
            ('stats_total', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='stats_total', unique=True, null=True, to=orm['analytics.Stats'])),
            ('stats_total_local', self.gf('django.db.models.fields.related.OneToOneField')(blank=True, related_name='stats_total_local', unique=True, null=True, to=orm['analytics.Stats'])),
            ('record_updated', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'analytics', ['Article'])

        # Adding M2M table for field bylines on 'Article'
        m2m_table_name = db.shorten_name(u'analytics_article_bylines')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('article', models.ForeignKey(orm[u'analytics.article'], null=False)),
            ('byline', models.ForeignKey(orm[u'analytics.byline'], null=False))
        ))
        db.create_unique(m2m_table_name, ['article_id', 'byline_id'])

        # Adding model 'Category'
        db.create_table(u'analytics_category', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=500)),
        ))
        db.send_create_signal(u'analytics', ['Category'])

        # Adding model 'Byline'
        db.create_table(u'analytics_byline', (
            ('id', self.gf('django.db.models.fields.IntegerField')(primary_key=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=500)),
        ))
        db.send_create_signal(u'analytics', ['Byline'])

        # Adding M2M table for field editor on 'Byline'
        m2m_table_name = db.shorten_name(u'analytics_byline_editor')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_byline', models.ForeignKey(orm[u'analytics.byline'], null=False)),
            ('to_byline', models.ForeignKey(orm[u'analytics.byline'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_byline_id', 'to_byline_id'])

        # Adding model 'Status'
        db.create_table(u'analytics_status', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=500)),
        ))
        db.send_create_signal(u'analytics', ['Status'])


    def backwards(self, orm):
        # Deleting model 'Site'
        db.delete_table(u'analytics_site')

        # Deleting model 'Stats'
        db.delete_table(u'analytics_stats')

        # Deleting model 'Article'
        db.delete_table(u'analytics_article')

        # Removing M2M table for field bylines on 'Article'
        db.delete_table(db.shorten_name(u'analytics_article_bylines'))

        # Deleting model 'Category'
        db.delete_table(u'analytics_category')

        # Deleting model 'Byline'
        db.delete_table(u'analytics_byline')

        # Removing M2M table for field editor on 'Byline'
        db.delete_table(db.shorten_name(u'analytics_byline_editor'))

        # Deleting model 'Status'
        db.delete_table(u'analytics_status')


    models = {
        u'analytics.article': {
            'Meta': {'object_name': 'Article'},
            'bylines': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['analytics.Byline']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['analytics.Category']", 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'headline': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'raw_byline_text': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'raw_category_text': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'raw_status_text': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'record_updated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['analytics.Site']"}),
            'stats_day': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'stats_day'", 'unique': 'True', 'null': 'True', 'to': u"orm['analytics.Stats']"}),
            'stats_day_local': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'stats_day_local'", 'unique': 'True', 'null': 'True', 'to': u"orm['analytics.Stats']"}),
            'stats_total': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'stats_total'", 'unique': 'True', 'null': 'True', 'to': u"orm['analytics.Stats']"}),
            'stats_total_local': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'stats_total_local'", 'unique': 'True', 'null': 'True', 'to': u"orm['analytics.Stats']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['analytics.Status']"}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'analytics.byline': {
            'Meta': {'object_name': 'Byline'},
            'editor': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['analytics.Byline']", 'symmetrical': 'False'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'id': ('django.db.models.fields.IntegerField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '500'})
        },
        u'analytics.category': {
            'Meta': {'object_name': 'Category'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'})
        },
        u'analytics.site': {
            'Meta': {'object_name': 'Site'},
            'dma': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'edit_url': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'ga_table': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'view_url': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        u'analytics.stats': {
            'Meta': {'object_name': 'Stats'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pageviews': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'time_on_page': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'visits': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'analytics.status': {
            'Meta': {'object_name': 'Status'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '500'})
        }
    }

    complete_apps = ['analytics']