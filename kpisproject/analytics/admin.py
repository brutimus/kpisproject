from django.contrib import admin
from kpisproject.analytics.models import Article, Category, Byline, Status

# Register your models here.


admin.site.register(Article)
admin.site.register(Category)
admin.site.register(Byline)
admin.site.register(Status)
