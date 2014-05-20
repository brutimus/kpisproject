import os, sys

sys.path.append('/Users/brutimus/Code/kpisproject')
os.environ['DJANGO_SETTINGS_MODULE'] = 'kpisproject.settings'

import psycopg2
from psycopg2.extras import DictCursor
from petl.fluent import *

from kpisproject.analytics.models import (
    Article,
    Byline,
    Category,
    Status,
    Stats
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


def main():
    connection = psycopg2.connect(DB)
    DICT_CURSOR = lambda: connection.cursor(cursor_factory=DictCursor)

    fromdb(DICT_CURSOR, REPORTERS_QUERY).progress().toucsv(REPORTERS_CSV)

    fromdb(
        DICT_CURSOR,
        ARTICLES_QUERY
    ).progress().toucsv(ARTICLES_CSV)


if __name__ == '__main__':
    main()
