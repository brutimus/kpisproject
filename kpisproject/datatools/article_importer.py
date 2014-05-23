import datetime, os, shelve, sys
from collections import OrderedDict

sys.path.append('/Users/brutimus/Code/kpisproject')
os.environ['DJANGO_SETTINGS_MODULE'] = 'kpisproject.settings'

from dateutil.parser import parse as parse_date
import psycopg2
from psycopg2.extras import DictCursor
from petl.fluent import *

from kpisproject.analytics.models import (
    Article,
    Byline,
    Category,
    Status,
    Stats,
    Site
)

from kpisproject.datatools.ga import (
    initialize_service,
    get_api_query,
    get_api_query_for_ids,
    dict_ga
)

DB = os.environ.get('DATABASE_URL')

REPORTERS_QUERY = """
    SELECT
        *
    FROM
        analytics_byline;
"""

ARTICLES_QUERY = """
    SELECT
        id,
        headline,
        date,
        raw_byline_text,
        raw_category_text,
        raw_status_text
    FROM
        analytics_article;
"""

REPORTERS_CSV = "reporters.csv"
ARTICLES_CSV = "articles.csv"


class SiteProcessor(object):

    SITE_LOOKUP = {
        'ocr': 'Orange County Register',
        'lar': 'Los Angeles Register'
    }

    def __init__(self, field):
        self.field = field
        self.cache = {}

    def __call__(self, item):
        skey = item[self.field]
        site = self.cache.get(skey)
        if not site:
            print "=== Site not cached, fetching: %s" % skey
            site = self.cache[skey] = Site.objects.get(
                name=self.SITE_LOOKUP[skey])
        return site


class StatusProcessor(object):

    def __init__(self, field):
        self.field = field
        self.cache = {}

    def __call__(self, item):
        skey = item[self.field]
        status = self.cache.get(skey)
        if not status:
            print "=== Status not cached, fetching: %s" % skey
            status = self.cache[skey] = Status.objects.get_or_create(
                name=skey)[0]
        return status


class CategoryProcessor(object):

    def __init__(self, field):
        self.field = field
        self.cache = {}

    def __call__(self, item):
        skey = item[self.field]
        category = self.cache.get(skey)
        if not category:
            print "=== Category not cached, fetching: %s" % skey
            category = self.cache[skey] = Category.objects.get_or_create(
                name=skey)[0]
        return category


class BylineProcessor(object):

    def __init__(self, field):
        self.field = field
        self.byline_lookup = [(x.first_name.lower(), x.last_name.lower(), x)
            for x in Byline.objects.all()]

    def __call__(self, item):
        text_byline = item[self.field]
        if not text_byline:
            return []
        text_byline = text_byline.lower()
        bl = []
        for first_name, last_name, byline in self.byline_lookup:
            if first_name.strip('. ') in text_byline:
                if last_name in text_byline:
                    bl.append(byline)
        return bl


class GoogleAnalytics(object):

    reports = {}
    local_reports = {}
    GA_CACHE_FILE = 'ga_cache'

    def __init__(self, site_field):
        self.site_field = site_field
        self.ga_service = initialize_service()
        self.shelve_reports = shelve.open(self.GA_CACHE_FILE)
        self.shelve_local_reports = shelve.open(self.GA_CACHE_FILE + '_local')
        self.reports = {}
        self.local_reports = {}

    def _fetch_report(self, ga_table, date, local=False):
        day = date.date()
        shelve_report_cache = self.shelve_local_reports if local else self.shelve_reports
        report_cache = self.local_reports if local else self.reports
        cache_key = str(day.toordinal())
        if report_cache.has_key(cache_key):
            return report_cache[cache_key]
        elif shelve_report_cache.has_key(cache_key):
            print "=== Pulling from%s shelve: %s" % (
                ' local' if local else '', cache_key)
            report = report_cache[cache_key] = dict_ga(
                shelve_report_cache[cache_key]['rows'])
            return report
        print 'Fetching%s GA report for: %s' % (' local' if local else '', day)
        report = self.ga_service.data().ga().get(
            ids=ga_table,
            start_date=day.strftime('%Y-%m-%d'),
            end_date=day.strftime('%Y-%m-%d'),
            metrics='ga:uniquePageviews,ga:pageviews,ga:avgTimeOnPage',
            dimensions='ga:pagePath',
            sort='-ga:uniquePageviews',
            segment='sessions::condition::ga:metro=@Angeles' if local else None,
            start_index='1',
            max_results='10000').execute()
        shelve_report_cache[cache_key] = report
        report = report_cache[cache_key] = dict_ga(report['rows'])
        return report

    def __call__(self, item):
        stats = {'day': None, 'day_local': None}
        report = self._fetch_report(
            item[self.site_field].ga_table,
            item['date'])
        ga_item = report.get(item['id'])
        if ga_item:
            # print 'Google Analytics for item: %s' % str(item)
            # print 'DATA: %s' % str(ga_item)
            stats['day'] = Stats(
                timestamp=datetime.datetime.now(),
                visits=ga_item[0],
                pageviews=ga_item[1],
                time_on_page=ga_item[2])

        # Local analytics
        report = self._fetch_report(
            item[self.site_field].ga_table,
            item['date'],
            local=True)
        ga_item = report.get(item['id'])
        if ga_item:
            # print 'Google Analytics for item: %s' % str(item)
            # print 'DATA: %s' % str(ga_item)
            stats['day_local'] = Stats(
                timestamp=datetime.datetime.now(),
                visits=ga_item[0],
                pageviews=ga_item[1],
                time_on_page=ga_item[2])

        return stats


def main():
    connection = psycopg2.connect(DB)
    DICT_CURSOR = lambda: connection.cursor(cursor_factory=DictCursor)

    # fromdb(DICT_CURSOR, REPORTERS_QUERY).progress().tocsv(REPORTERS_CSV)

    fieldmapping = OrderedDict()
    fieldmapping['id'] = 'id'
    fieldmapping['headline'] = 'headline'
    fieldmapping['date'] = 'date'
    fieldmapping['raw_byline_text'] = 'raw_byline_text'
    fieldmapping['raw_category_text'] = 'raw_category_text'
    fieldmapping['raw_status_text'] = 'raw_status_text'
    fieldmapping['site'] = lambda x:'ocr'

    existing_ids = Article.objects.all().values_list('id', flat=True)

    for x in fromucsv(
        'april.csv'
    ).fieldmap(
        fieldmapping
    ).rename(
        'site',
        'raw_site_text'
    ).convert(
        'id',
        parsenumber
    ).selectnotin(
        'id',
        existing_ids
    ).convert(
        'date',
        parse_date
    ).addfield(
        'site',
        SiteProcessor('raw_site_text')
    ).addfield(
        'status',
        StatusProcessor('raw_status_text')
    ).addfield(
        'bylines',
        BylineProcessor('raw_byline_text')
    ).addfield(
        'category',
        CategoryProcessor('raw_category_text')
    ).addfield(
        'stats',
        GoogleAnalytics('site') # Depends on SiteProcessor result
    ).iterdicts():
        sd = x['stats']['day']
        sdl = x['stats']['day_local']
        bylines = x['bylines']
        if sd:
            sd.save()
        if sdl:
            sdl.save()
        a = Article(
            id=x['id'],
            headline=x['headline'],
            date=x['date'],
            stats_day=sd,
            stats_day_local=sdl,
            site=x['site'],
            category=x['category'],
            status=x['status'],
            raw_byline_text=x['raw_byline_text'],
            raw_status_text=x['raw_status_text'],
            raw_category_text=x['raw_category_text'],
            record_updated=datetime.datetime.now()
        )
        a.save()
        a.bylines = bylines

        print a

if __name__ == '__main__':
    main()
