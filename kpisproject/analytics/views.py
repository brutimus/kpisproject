import json, datetime, time, re
from operator import itemgetter, methodcaller, attrgetter
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.db import connections, connection
from django.db.models import Sum, Avg, Count
from django.shortcuts import render_to_response
from django.template import base
from django.views.decorators.cache import cache_page
from django.views.generic.dates import DayArchiveView
from django.views.generic.list import ListView
from kpisproject.analytics.models import Article, Byline, Category, Status
from kpisproject.analytics import sql

base.tag_re = (re.compile('(%s.*?%s|%s.*?%s|%s.*?%s)' %
          (re.escape(base.BLOCK_TAG_START), re.escape(base.BLOCK_TAG_END),
           re.escape(base.VARIABLE_TAG_START), re.escape(base.VARIABLE_TAG_END),
           re.escape(base.COMMENT_TAG_START), re.escape(base.COMMENT_TAG_END)), re.DOTALL))


def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]


@cache_page(60 * 15)
# @login_required(login_url='/admin/')
def story_overview(request):
    cursor = connection.cursor()

    cursor.execute(sql.sums_query % {
        'select': '',
        'from': '',
        'where': '',
        'group_by': ''
    })
    totals = dictfetchall(cursor)

    avg_sql = """
    SELECT
        SUM(visits) / COUNT(*) AS avg_v,
        SUM(pageviews) / COUNT(*) AS avg_pv,
        SUM(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / SUM(visits) AS avg_top
    FROM
        analytics_article
    LEFT OUTER JOIN
        analytics_stats ON (analytics_article.%s = analytics_stats.id)
    WHERE
        visits IS NOT NULL
    """

    cursor.execute(avg_sql % 'stats_day_id')
    averages_day = dictfetchall(cursor)[0]

    cursor.execute(avg_sql % 'stats_day_local_id')
    averages_day_local = dictfetchall(cursor)[0]

    cursor.execute(avg_sql % 'stats_total_id')
    averages_total = dictfetchall(cursor)[0]
    
    cursor.execute(avg_sql % 'stats_total_local_id')
    averages_total_local = dictfetchall(cursor)[0]
    # print averages_day, averages_total, averages_day_local, averages_total_local

    # Daily Rollup
    cursor.execute(sql.sums_query % {
        'select': "EXTRACT(EPOCH FROM DATE_TRUNC('day', date)) AS ts,",
        'from': '',
        'where': '',
        'group_by': "GROUP BY ts"
    })
    by_day = dictfetchall(cursor)

    # Weekly Rollup
    cursor.execute(sql.sums_query % {
        'select': """
            DATE_TRUNC('week', date) AS week_start,
            DATE_TRUNC('week', date) + INTERVAL '6 days' AS week_end,""",
        'from': '',
        'where': '',
        'group_by': """GROUP BY 
            week_start,
            week_end"""
    })
    by_week = dictfetchall(cursor)

    # Monthly Rollup
    cursor.execute(sql.sums_query % {
        'select': "DATE_TRUNC('month', date) AS month,",
        'from': '',
        'where': '',
        'group_by': "GROUP BY month"
    })
    by_month = dictfetchall(cursor)

    return render_to_response('analytics/story_overview.html', {
        'totals': {
            'sums': totals,
            'day': averages_day,
            'day_local': averages_day_local,
            'total': averages_total,
            'total_local': averages_total_local
        },
        'histograms': {
            'count': {int(x['ts']): int(x['count']) for x in by_day},
            'v': {int(x['ts']): int(x['v'] or 0) for x in by_day},
            'pv': {int(x['ts']): int(x['pv'] or 0) for x in by_day}
        },
        'by_week': by_week,
        'by_month': by_month
    })

@cache_page(60 * 15)
def story_day(request, year, month, day):

    today = datetime.date(int(year), int(month), int(day))
    s = lambda z: lambda x, y: (x or 0) + (getattr(y, z) or 0)
    field_fns = {
        'count': lambda x, y: x + 1,
        'v': s('visits'),
        'pv': s('pageviews'),
        't_v': s('all_visits'),
        't_pv': s('all_pageviews'),
        'ea': s('expanded_avg'),
        't_ea': s('expanded_t_avg')
    }

    base_article_list = Article.objects.filter(
        date__year=year,
        date__month=month,
        date__day=day
    ).extra(
        select={
            # 'count': 'count(*)',
            # # Day of
            # 'sigma_v': 'sum(visits)',
            # 'sigma_pv': 'sum(pageviews)',
            # 'sigma_top': 'sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits)',
            # # Overall
            # 'sigma_t_v': 'sum(all_visits)',
            # 'sigma_t_pv': 'sum(all_pageviews)',
            # 'sigma_t_top': 'sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits)',
            # old
            'expanded_avg': 'COALESCE(visits, 0) * COALESCE(time_on_page, 0)',
            'expanded_t_avg': 'COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)'
        }
    ).select_related(
        'status', 'category'
    ).prefetch_related(
        'bylines'
    ).order_by('date')

    base_byline_list = Byline.objects.filter(
        article__date__year=year,
        article__date__month=month,
        article__date__day=day
    ).order_by('first_name', 'last_name').distinct()

    sigma_v = reduce(field_fns['v'], base_article_list, 0)
    sigma_pv = reduce(field_fns['pv'], base_article_list, 0)
    sigma_top = (
        reduce(field_fns['ea'], base_article_list, 0) / sigma_v
    ) if sigma_v > 0 else None
    sigma_t_v = reduce(field_fns['t_v'], base_article_list, 0)
    sigma_t_pv = reduce(field_fns['t_pv'], base_article_list, 0)
    sigma_t_top = (
        reduce(field_fns['t_ea'], base_article_list, 0) / sigma_t_v
    ) if sigma_t_v > 0 else None

    # PROCESS BYLINES
    byline_context = {
        'count': len(base_byline_list),
        'list': []
    }

    
    def summarize_groups(data, fields=field_fns):
        results = {}
        for key, group in data.items():
            results[key] = {'sums': {}, 'group': group}
            for name, fn in fields.items():
                results[key]['sums'][name] = reduce(fn, group, 0)
        return results

    def ammend_sums(data):
        for k, v in data.items():
            v['sums']['top'] = (v['sums']['ea'] / v['sums']['v']) if v['sums']['v'] else 0
            v['sums']['t_top'] = (v['sums']['t_ea'] / v['sums']['t_v']) if v['sums']['t_v'] else 0
            v['sums']['p_t_v'] = float(v['sums']['v']) / float(sigma_v) * 100
            v['sums']['p_t_pv'] = float(v['sums']['pv']) / float(sigma_pv) * 100
            for a in v['group']:
                a.p_t_v = float(a.visits or 0) / float(sigma_v) * 100
                a.p_t_pv = float(a.pageviews or 0) / float(sigma_pv) * 100
        return data



    # Byline(): [Article(), ... ]
    byline_groups = {}
    for article in base_article_list:
        for byline in article.bylines.all():
            byline_groups[byline] = byline_groups.get(byline, [])
            byline_groups[byline].append(article)

    byline_sums = summarize_groups(byline_groups, field_fns)
    ammend_sums(byline_sums)
    byline_context['list'] = byline_sums

    # PROCESS SECTIONS
    section_context = {
        'count': 0,
        'list': []
    }
    key = lambda x:x.category.name if x.category else None
    category_groups = {
        key: list(group) for key, group in
        groupby(sorted(base_article_list, key=key), key=key)}
    section_context['count'] = len(category_groups)


    category_sums = summarize_groups(category_groups, field_fns)
    ammend_sums(category_sums)
    section_context['list'] = category_sums

    context = {
        'totals': {
            'v': sigma_v,
            'pv': sigma_pv,
            'time_on_page__avg': sigma_top
        },
        'articles': base_article_list,
        'bylines': byline_context,
        'sections': section_context,
        'unused': base_article_list.filter(visits__isnull=True),
        'yesterday': today - datetime.timedelta(days=1),
        'today': today,
        'tomorrow': today + datetime.timedelta(days=1)
    }
    return render_to_response('analytics/story_day.html', context)

@cache_page(60 * 15)
def byline_overview(request):
    return render_to_response('analytics/byline_overview.html', {
        'bylines': Byline.objects.all().order_by('first_name', 'last_name')
        })

@cache_page(60 * 15)
def byline_detail(request, byline_id):
    date_min = datetime.date(2000,1,1)
    cursor = connection.cursor()

    cursor.execute(sql.sums_query % {
        'select': '',
        'from': '',
        'where': '',
        'group_by': ''
    })
    site_totals = dictfetchall(cursor)[0]
    site_avg_sql = """
    SELECT
        SUM(visits) / COUNT(*) AS avg_v,
        SUM(pageviews) / COUNT(*) AS avg_pv,
        SUM(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / SUM(visits) AS avg_top
    FROM
        analytics_article
    LEFT OUTER JOIN
        analytics_stats ON (analytics_article.%s = analytics_stats.id)
    WHERE
        visits IS NOT NULL
    """

    cursor.execute(site_avg_sql % 'stats_day_id')
    site_averages_day = dictfetchall(cursor)[0]

    cursor.execute(site_avg_sql % 'stats_day_local_id')
    site_averages_day_local = dictfetchall(cursor)[0]

    cursor.execute(site_avg_sql % 'stats_total_id')
    site_averages_total = dictfetchall(cursor)[0]
    
    cursor.execute(site_avg_sql % 'stats_total_local_id')
    site_averages_total_local = dictfetchall(cursor)[0]

    avg_sql = """
    SELECT
        SUM(visits) / COUNT(*) AS avg_v,
        SUM(pageviews) / COUNT(*) AS avg_pv,
        SUM(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / SUM(visits) AS avg_top
    FROM
        analytics_article,
        analytics_article_bylines,
        analytics_stats
    WHERE
        analytics_article.id = analytics_article_bylines.article_id
        AND analytics_article_bylines.byline_id = %%s
        AND analytics_article.%s = analytics_stats.id
        AND visits IS NOT NULL
        AND date >= TIMESTAMP %%s;
    """

    cursor.execute(avg_sql % 'stats_day_id', [byline_id, date_min])
    averages_day = dictfetchall(cursor)[0]

    cursor.execute(avg_sql % 'stats_day_local_id', [byline_id, date_min])
    averages_day_local = dictfetchall(cursor)[0]

    cursor.execute(avg_sql % 'stats_total_id', [byline_id, date_min])
    averages_total = dictfetchall(cursor)[0]
    
    cursor.execute(avg_sql % 'stats_total_local_id', [byline_id, date_min])
    averages_total_local = dictfetchall(cursor)[0]


    base_article_list = Article.objects.filter(
        bylines__id=byline_id
    )

    # Sums ##########################################################
    cursor.execute(sql.sums_query % {
        'select': '',
        'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
        'where': """WHERE analytics_article.id = analytics_article_bylines.article_id
            AND analytics_article_bylines.byline_id = %s""" % int(byline_id),
        'group_by': ''
    })
    sums = dictfetchall(cursor)[0]

    # Rollups
    rollup_days = (30, 60, 90, 180, 365)
    rollups = []
    for delta in rollup_days:
        d = datetime.date.today() - datetime.timedelta(days=delta)

        cursor.execute(sql.sums_query % {
            'select': '',
            'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
            'where': """WHERE analytics_article_bylines.byline_id = %s
                AND date >= TIMESTAMP '%s'""" % (
                    int(byline_id),
                    d.strftime('%Y-%m-%d')),
            'group_by': ''
        })
        sums = dictfetchall(cursor)[0]

        cursor.execute(avg_sql % 'stats_day_id', [byline_id, d])
        averages_day = dictfetchall(cursor)[0]

        cursor.execute(avg_sql % 'stats_day_local_id', [byline_id, d])
        averages_day_local = dictfetchall(cursor)[0]

        cursor.execute(avg_sql % 'stats_total_id', [byline_id, d])
        averages_total = dictfetchall(cursor)[0]
        
        cursor.execute(avg_sql % 'stats_total_local_id', [byline_id, d])
        averages_total_local = dictfetchall(cursor)[0]
        

        rollups.append({
            'delta': delta,
            'sums': sums,
            'day': averages_day,
            'day_local': averages_day_local,
            'total': averages_total,
            'total_local': averages_total_local
        })


    # Daily Rollup
    cursor.execute(sql.sums_query % {
        'select': "EXTRACT(EPOCH FROM DATE_TRUNC('day', date)) AS ts,",
        'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
        'where': """WHERE analytics_article_bylines.byline_id = %s""" % int(byline_id),
        'group_by': "GROUP BY ts"
    })
    by_day = dictfetchall(cursor)

    # Weekly Rollup
    cursor.execute(sql.sums_query % {
        'select': """
            DATE_TRUNC('week', date) AS week_start,
            DATE_TRUNC('week', date) + INTERVAL '6 days' AS week_end,""",
        'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
        'where': """WHERE analytics_article_bylines.byline_id = %s""" % int(byline_id),
        'group_by': """GROUP BY 
            week_start,
            week_end"""
    })
    by_week = dictfetchall(cursor)

    # Monthly Rollup
    cursor.execute(sql.sums_query % {
        'select': "DATE_TRUNC('month', date) AS month,",
        'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
        'where': """WHERE analytics_article_bylines.byline_id = %s""" % int(byline_id),
        'group_by': "GROUP BY month"
    })
    by_month = dictfetchall(cursor)

    # Process ratios
    def floatall(d):
        return {k: float(v) for k, v in d.items()}
    averages_day = floatall(averages_day)
    averages_day_local = floatall(averages_day_local)
    averages_total = floatall(averages_total)
    averages_total_local = floatall(averages_total_local)
    site_averages_day = floatall(site_averages_day)
    site_averages_day_local = floatall(site_averages_day_local)
    site_averages_total = floatall(site_averages_total)
    site_averages_total_local = floatall(site_averages_total_local)

    ratios = {
        'day': {
            # Compare day to site avg
            'avg_v': averages_day['avg_v'] / site_averages_day['avg_v'],
            'avg_pv': averages_day['avg_pv'] / site_averages_day['avg_pv'],
            'avg_top': averages_day['avg_top'] / site_averages_day['avg_top']},
        'day_local': {
            # Compare day local to day (percent local)
            'avg_v': averages_day_local['avg_v'] / averages_day['avg_v'],
            'avg_pv': averages_day_local['avg_pv'] / averages_day['avg_pv'],
            'avg_top': averages_day_local['avg_top'] / averages_day['avg_top'],
            # Compare byline percent local to site percent local
            'r_avg_v': (
                averages_day_local['avg_v'] / averages_day['avg_v']) / (
                site_averages_day_local['avg_v'] / site_averages_day['avg_v']),
            'r_avg_pv': (
                averages_day_local['avg_pv'] / averages_day['avg_pv']) / (
                site_averages_day_local['avg_pv'] / site_averages_day['avg_pv']),
            'r_avg_top': (
                averages_day_local['avg_top'] / averages_day['avg_top']) / (
                site_averages_day_local['avg_top'] / site_averages_day['avg_top'])},
        'total': {
            # Compare total to site total
            'avg_v': averages_total['avg_v'] / site_averages_total['avg_v'],
            'avg_pv': averages_total['avg_pv'] / site_averages_total['avg_pv'],
            'avg_top': averages_total['avg_top'] / site_averages_total['avg_top']},
        'total_local': {
            # Compare total local to total (percent local)
            'avg_v': averages_total_local['avg_v'] / averages_total['avg_v'],
            'avg_pv': averages_total_local['avg_pv'] / averages_total['avg_pv'],
            'avg_top': averages_total_local['avg_top'] / averages_total['avg_top'],
            # Compare byline percent local to site percent local
            'r_avg_v': (
                averages_total_local['avg_v'] / averages_total['avg_v']) / (
                site_averages_total_local['avg_v'] / site_averages_total['avg_v']),
            'r_avg_pv': (
                averages_total_local['avg_pv'] / averages_total['avg_pv']) / (
                site_averages_total_local['avg_pv'] / site_averages_total['avg_pv']),
            'r_avg_top': (
                averages_total_local['avg_top'] / averages_total['avg_top']) / (
                site_averages_total_local['avg_top'] / site_averages_total['avg_top'])},
    }


    return render_to_response('analytics/byline.html', {
        'byline': Byline.objects.get(id=int(byline_id)),
        'articles': base_article_list.order_by('-date').select_related('status'),
        'histograms': {
            'count': {int(x['ts']): int(x['count']) for x in by_day},
            'v': {int(x['ts']): int(x['v'] or 0) for x in by_day},
            'pv': {int(x['ts']): int(x['pv'] or 0) for x in by_day}
        },
        'by_week': by_week,
        'by_month': by_month,
        'site_totals': {
            'sums': site_totals,
            'day': site_averages_day,
            'day_local': site_averages_day_local,
            'total': site_averages_total,
            'total_local': site_averages_total_local
        },
        'totals': {
            'sums': sums,
            'day': averages_day,
            'day_local': averages_day_local,
            'total': averages_total,
            'total_local': averages_total_local
        },
        'ratios': ratios,
        'rollups': rollups
    })
