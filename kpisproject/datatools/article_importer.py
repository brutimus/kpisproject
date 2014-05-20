import datetime, os, shelve, sys

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

"""('id',
 'headline',
 'date',
 'raw_byline_text',
 'raw_category_text',
 'raw_status_text')"""

class SiteProcessor(object):

    SITE_LOOKUP = {
        'ocr': 'Orange County Register',
        'lar': 'Los Angeles Register'
    }

    def __init__(self):
        self.cache = {}

    def __call__(self, skey):
        site = self.cache.get(skey)
        if not site:
            site = self.cache[skey] = Site.objects.get(
                name=self.SITE_LOOKUP[skey])
        return site


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

    # reports format -> {datetime.day: report, ... }
    reports = {}
    local_reports = {}
    GA_CACHE_FILE = 'ga_cache'

    def __init__(self, site_field):
        self.site_field = site_field
        self.ga_service = initialize_service()
        self.reports = shelve.open(self.GA_CACHE_FILE)
        self.local_reports = shelve.open(self.GA_CACHE_FILE + '_local')

    def _fetch_report(self, ga_table, date, local=False):
        day = date.date()
        report_cache = self.local_reports if local else self.reports
        if report_cache.has_key(str(day.toordinal())):
            return report_cache[str(day.toordinal())]
        print 'Fetching%s GA report for: %s' % (' local' if local else '', day)
        report = dict_ga(self.ga_service.data().ga().get(
          ids=ga_table,
          start_date=day.strftime('%Y-%m-%d'),
          end_date=day.strftime('%Y-%m-%d'),
          metrics='ga:uniquePageviews,ga:pageviews,ga:avgTimeOnPage',
          dimensions='ga:pagePath',
          sort='-ga:uniquePageviews',
          segment='sessions::condition::ga:metro=@Angeles' if local else None,
          start_index='1',
          max_results='10000').execute().get('rows'))
        report_cache[str(day.toordinal())] = report
        return report

    def __call__(self, item):
        report = self._fetch_report(
            item[self.site_field].ga_table,
            item['date'])
        ga_item = report.get(item['id'])
        # stats = {
        #     'visits': None,
        #     'views': None,
        #     'time_on_page': None,
        #     'visits_local': None,
        #     'views_local': None,
        #     'time_on_page_local': None
        # }
        stats = {'day': None, 'day_local': None}
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

    # Need to lookup site from the csv then pull appropriate ga table info

    print fromucsv(
        ARTICLES_CSV
    ).head().convert(
        'id',
        parsenumber
    ).convert(
        'date',
        parse_date
    ).convert(
        'site',
        SiteProcessor()
    ).addfield(
        'byline_ids',
        BylineProcessor('raw_byline_text')
    ).addfield(
        'stats',
        GoogleAnalytics('site') # Depends on SiteProcessor result
    ).look()

    # use .iterdata() to start iterating over the rows

if __name__ == '__main__':
    main()
