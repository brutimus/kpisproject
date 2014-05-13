from django.db import models

BN = {'blank': True, 'null': True}
URLS = {
    'ocr': {
        'view': 'http://www.ocregister.com/articles/-%s--.html',
        'edit': 'http://admin.onset.freedom.com/modules/articles/edit.php?id=%s'
    }
}

class Site(models.Model):
    name = models.CharField(max_length=100)
    edit_url = models.CharField(max_length=200)
    view_url = models.CharField(max_length=200)
    ga_table = models.CharField(max_length=50)
    dma = models.CharField(max_length=100)


class Stats(models.Model):
    timestamp = models.DateTimeField()
    visits = models.IntegerField(**BN)
    pageviews = models.IntegerField(**BN)
    time_on_page = models.IntegerField(**BN)


class Article(models.Model):
    id = models.IntegerField(primary_key=True)
    url = models.URLField()
    headline = models.CharField(max_length=500)
    date = models.DateTimeField()
    site = models.ForeignKey(Site)

    # Relationships
    bylines = models.ManyToManyField('Byline')
    category = models.ForeignKey('Category', **BN)
    status = models.ForeignKey('Status')

    # Raw fields to store original data in case we need to re-parse
    raw_byline_text = models.CharField(max_length=200, **BN)
    raw_category_text = models.CharField(max_length=200, **BN)
    raw_status_text = models.CharField(max_length=200, **BN)

    stats_day = models.OneToOneField(Stats,
        related_name='stats_day', **BN)
    stats_day_local = models.OneToOneField(Stats,
        related_name='stats_day_local', **BN)
    stats_total = models.OneToOneField(Stats,
        related_name='stats_total', **BN)
    stats_total_local = models.OneToOneField(Stats,
        related_name='stats_total_local', **BN)

    # Tracking
    record_updated = models.DateTimeField(**BN)

    def __unicode__(self):
        return self.headline

    def view_url(self):
        return self.site.view_url % self.id

    def edit_url(self):
        return self.site.edit_url % self.id


class Category(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __unicode__(self):
        return self.name

class Byline(models.Model):
    id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=500)
    last_name = models.CharField(max_length=500)
    editor = models.ManyToManyField('Byline')

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Status(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __unicode__(self):
        return self.name