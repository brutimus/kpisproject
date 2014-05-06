from django.db import models

# Create your models here.

class Article(models.Model):
    id = models.IntegerField(primary_key=True)
    url = models.URLField()
    headline = models.CharField(max_length=500)
    date = models.DateTimeField()
    category = models.ForeignKey('Category', blank=True, null=True)
    status = models.ForeignKey('Status')
    bylines = models.ManyToManyField('Byline')
    visits = models.IntegerField(blank=True, null=True)
    pageviews = models.IntegerField(blank=True, null=True)
    time_on_page = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.headline


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