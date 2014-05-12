from django.db import models

BN = {'blank': True, 'null': True}
URLS = {
    'ocr': {
        'view': 'http://www.ocregister.com/articles/-%s--.html',
        'edit': 'http://admin.onset.freedom.com/modules/articles/edit.php?id=%s'
    }
}

# class Site(models.Model):
#     name = models.CharField(max_length=100)
#     edit_url = models.CharField(max_length=200)
#     view_url = models.CharField(max_length=200)
#     ga_table = models.CharField(max_length=50)
#     dma = models.CharField(max_length=100)



class Article(models.Model):
    id = models.IntegerField(primary_key=True)
    url = models.URLField()
    headline = models.CharField(max_length=500)
    date = models.DateTimeField()

    # Relationships
    bylines = models.ManyToManyField('Byline')
    category = models.ForeignKey('Category', **BN)
    status = models.ForeignKey('Status')

    # Raw fields to store original data in case we need to re-parse
    raw_byline_text = models.CharField(max_length=200, **BN)
    raw_category_text = models.CharField(max_length=200, **BN)
    raw_status_text = models.CharField(max_length=200, **BN)

    # Used for day-of-publish analytics stats
    visits = models.IntegerField(**BN)
    visits_local = models.IntegerField(**BN)
    pageviews = models.IntegerField(**BN)
    time_on_page = models.IntegerField(**BN)

    # all_ fields used for overall analytics stats
    all_visits = models.IntegerField(**BN)
    all_visits_local = models.IntegerField(**BN)
    all_pageviews = models.IntegerField(**BN)
    all_time_on_page = models.IntegerField(**BN)

    # Tracking
    record_updated = models.DateTimeField(**BN)

    def __unicode__(self):
        return self.headline

    def view_url(self):
        return URLS['ocr']['view'] % self.id

    def edit_url(self):
        return URLS['ocr']['edit'] % self.id


class Category(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __unicode__(self):
        return self.name

class Byline(models.Model):
    first_name = models.CharField(max_length=500)
    last_name = models.CharField(max_length=500)
    editor = models.ManyToManyField('Byline')

    def __unicode__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Status(models.Model):
    name = models.CharField(max_length=500, unique=True)

    def __unicode__(self):
        return self.name