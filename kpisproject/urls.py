import django_databrowse
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic.list import ListView

from django.contrib import admin
admin.autodiscover()

from kpisproject.analytics.models import Article, Byline, Status, Category

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'kpis.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^grappelli/', include('grappelli.urls')), # grappelli URLS
    url(r'^django_databrowse/(.*)', django_databrowse.site.root),
    url(r'^stories/$', 'kpisproject.analytics.views.story_overview'),
    url(
    	r'^stories/(?P<year>\d{4})/(?P<month>\d+)/(?P<day>\d+)/$',
    	'kpisproject.analytics.views.story_day'),
    url(r'^bylines/$', 'kpisproject.analytics.views.byline_overview'),
    url(r'^bylines/(\d+)/$', 'kpisproject.analytics.views.byline_detail')
)

# django_databrowse.site.register(Article, Byline, Status, Category)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )