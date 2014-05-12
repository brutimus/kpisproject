import json, datetime, time
from operator import itemgetter, methodcaller, attrgetter
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.db import connections, connection
from django.db.models import Sum, Avg, Count
from django.shortcuts import render_to_response
from django.views.decorators.cache import cache_page
from django.views.generic.dates import DayArchiveView
from django.views.generic.list import ListView
from kpisproject.analytics.models import Article, Byline, Category, Status
from kpisproject.analytics import sql


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
    totals = Article.objects.extra(
        select={
            'count': 'count(*)',
            # Day of
            'top': 'sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits)',
            'v': 'sum(visits)',
            'pv': 'sum(pageviews)',
            'avg_v': '(select sum(visits)/count(*) from analytics_article where visits > 0)',
            'avg_pv': '(select sum(pageviews)/count(*) from analytics_article where pageviews > 0)',
            'avg_p_lv': 'SUM(visits_local)::real / SUM(visits)::real * 100',
            # All time
            't_top': 'sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits)',
            't_v': 'sum(all_visits)',
            't_pv': 'sum(all_pageviews)',
            'avg_t_v': '(select sum(all_visits)/count(*) from analytics_article where all_visits > 0)',
            'avg_t_pv': '(select sum(all_pageviews)/count(*) from analytics_article where all_pageviews > 0)',
            'avg_p_t_lv': 'SUM(all_visits_local)::real / SUM(all_visits)::real * 100',
        }
    ).values(
        'count',
        'top',
        'v',
        't_v',
        'pv',
        't_pv',
        't_top',
        'avg_v',
        'avg_t_v',
        'avg_pv',
        'avg_t_pv',
        'avg_p_lv',
        'avg_p_t_lv'
    )

    # Daily Rollup
    cursor.execute(sql.daily_rollup % '0 = 0')
    by_day = dictfetchall(cursor)

    # Weekly Rollup
    cursor.execute(sql.weekly_rollup % '0 = 0')
    by_week = dictfetchall(cursor)

    # Monthly Rollup
    cursor.execute(sql.monthly_rollup % '0 = 0')
    by_month = dictfetchall(cursor)

    return render_to_response('analytics/story_overview.html', {
        'totals': totals.get(),
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
    cursor = connection.cursor()

    site_totals = Article.objects.extra(
        select={
            'count': 'count(*)',
            # Day of
            'top': 'sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits)',
            'v': 'sum(visits)',
            'pv': 'sum(pageviews)',
            'avg_v': '(select sum(visits)/count(*) from analytics_article where visits > 0)',
            'avg_pv': '(select sum(pageviews)/count(*) from analytics_article where pageviews > 0)',
            # All time
            't_top': 'sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits)',
            't_v': 'sum(all_visits)',
            't_pv': 'sum(all_pageviews)',
            'avg_t_v': '(select sum(all_visits)/count(*) from analytics_article where all_visits > 0)',
            'avg_t_pv': '(select sum(all_pageviews)/count(*) from analytics_article where all_pageviews > 0)'
        }
    ).values(
        'count',
        'top',
        'v',
        't_v',
        'pv',
        't_pv',
        'avg_v',
        'avg_t_v',
        'avg_pv',
        'avg_t_pv'
    )

    base_article_list = Article.objects.filter(
        bylines__id=byline_id
    )

    # Sums ##########################################################
    sums = base_article_list.extra(
        select={
            # Totals
            'count': 'count(*)',
            'v': 'sum(visits)',
            'pv': 'sum(pageviews)',
            't_v': 'sum(all_visits)',
            't_pv': 'sum(all_pageviews)'
        }
    ).values(
        'count',
        'v',
        't_v',
        'pv',
        't_pv',
    )

    # Averages ######################################################
    averages_day_extra = {
        'avg_v': 'sum(visits)/count(*)',
        'avg_pv': 'sum(pageviews)/count(*)',
        'avg_top': 'sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits)',
        'avg_p_lv': 'SUM(visits_local)::real / SUM(visits)::real * 100',

        'r_avg_v': """(
            (sum(visits)/count(*))::real - (
                select sum(visits)/count(*) from analytics_article where visits > 0)
        ) / (select sum(visits)/count(*) from analytics_article where visits > 0) * 100""",

        'r_avg_pv': """(
            (sum(pageviews)/count(*))::real - (
                select sum(pageviews)/count(*) from analytics_article where pageviews > 0)
        ) / (select sum(pageviews)/count(*) from analytics_article where pageviews > 0) * 100""",

        'r_avg_top': """(
            (sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits))::real - (
                select sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits) from analytics_article)
        ) / (select sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits) from analytics_article) * 100""",

        'r_avg_p_lv': """(
            (SUM(visits_local)::real / SUM(visits)::real) - (
                SELECT SUM(visits_local)::real / SUM(visits)::real from analytics_article where visits_local > 0 AND visits > 0)
        ) / (SELECT SUM(visits_local)::real / SUM(visits)::real from analytics_article where visits_local > 0 AND visits > 0) * 100"""        
    }
    averages_day = base_article_list.filter(
        visits__isnull=False,
        pageviews__isnull=False
    ).extra(
        select=averages_day_extra
    ).values(*averages_day_extra.keys())

    averages_total_extra = {
        'avg_t_v': 'sum(all_visits)/count(*)',
        'avg_t_pv': 'sum(all_pageviews)/count(*)',
        'avg_t_top': 'sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits)',
        'avg_p_t_lv': 'SUM(all_visits_local)::real / SUM(all_visits)::real * 100',

        'r_avg_t_v': """(
            (sum(all_visits)/count(*))::real - (
                select sum(all_visits)/count(*) from analytics_article where all_visits > 0)
        ) / (select sum(all_visits)/count(*) from analytics_article where all_visits > 0) * 100""",

        'r_avg_t_pv': """(
            (sum(all_pageviews)/count(*))::real - (
                select sum(all_pageviews)/count(*) from analytics_article where all_pageviews > 0)
        ) / (select sum(all_pageviews)/count(*) from analytics_article where all_pageviews > 0) * 100""",

        'r_avg_t_top': """(
            (sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits))::real - (
                select sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits) from analytics_article)
        ) / (select sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits) from analytics_article) * 100""",

        'r_avg_p_t_lv': """(
            (SUM(all_visits_local)::real / SUM(all_visits)::real) - (
                SELECT SUM(all_visits_local)::real / SUM(all_visits)::real from analytics_article where all_visits_local > 0 AND all_visits > 0)
        ) / (SELECT SUM(all_visits_local)::real / SUM(all_visits)::real from analytics_article where all_visits_local > 0 AND all_visits > 0) * 100"""
    }
    averages_total = base_article_list.filter(
        all_visits__isnull=False,
        all_pageviews__isnull=False
    ).extra(
        select=averages_total_extra
    ).values(*averages_total_extra.keys())

    cursor.execute("""
    SELECT
        SUM(all_visits)/COUNT(*) AS avg_t_v,
        SUM(all_pageviews)/COUNT(*) AS avg_t_pv,
        SUM(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0))
            / SUM(all_visits) AS avg_t_top,
        SUM(all_visits_local)::real / SUM(all_visits)::real * 100 AS avg_p_t_lv,
        ((SUM(all_visits) / COUNT(*))::real - (
            SELECT
                SUM(all_visits) / COUNT(*)
            FROM analytics_article
            WHERE all_visits > 0
        )::real) / (
            SELECT
                SUM(all_visits) / COUNT(*)
                FROM analytics_article
                WHERE all_visits > 0
        )::real * 100 AS r_avg_t_v,
        ((SUM(all_pageviews) / COUNT(*))::real - (
            SELECT
                SUM(all_pageviews) / COUNT(*)
            FROM analytics_article
            WHERE all_pageviews > 0
        )::real) / (
            SELECT
                SUM(all_pageviews) / COUNT(*)
            FROM analytics_article
            WHERE all_pageviews > 0
        )::real * 100 AS r_avg_t_pv,
        ((SUM(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / SUM(all_visits))::real - (
            SELECT
                SUM(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / SUM(all_visits)
            FROM analytics_article
        )) / (
            SELECT
                SUM(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / SUM(all_visits)
            FROM analytics_article
        ) * 100 AS r_avg_t_top,
        ((SUM(all_visits_local)::real / SUM(all_visits)::real) - (
            SELECT
                SUM(all_visits_local)::real / SUM(all_visits)::real
            FROM analytics_article
            WHERE all_visits_local > 0 AND all_visits > 0
        )::real) / (
            SELECT
                SUM(all_visits_local)::real / SUM(all_visits)::real
            FROM analytics_article
            WHERE all_visits_local > 0 AND all_visits > 0
        ) * 100 AS r_avg_p_t_lv
    FROM
        analytics_article,
        analytics_article_bylines
    WHERE
        analytics_article.id = analytics_article_bylines.article_id
        AND analytics_article_bylines.byline_id = %s
        AND all_visits IS NOT NULL
        AND all_pageviews IS NOT NULL;
    """, [int(byline_id)])


    rollup_days = (30, 60, 90, 180, 365)
    rollups = []
    for delta in rollup_days:
        f = {'date__gte': datetime.date.today() - datetime.timedelta(days=delta)}
        rollups.append({
            'delta': delta,
            'sums': sums.filter(**f).get(),
            'averages_day': averages_day.filter(**f).get(),
            'averages_total': averages_total.filter(**f).get()
        })


    # Daily Rollup
    
    cursor.execute(sql.daily_rollup % (
        "analytics_article_bylines.byline_id = %s" % int(byline_id),
    ))
    by_day = dictfetchall(cursor)

    # Weekly Rollup
    cursor.execute(sql.weekly_rollup % (
        "analytics_article_bylines.byline_id = %s" % int(byline_id),
    ))
    by_week = dictfetchall(cursor)

    # Monthly Rollup
    cursor.execute(sql.monthly_rollup % (
        "analytics_article_bylines.byline_id = %s" % int(byline_id),
    ))
    by_month = dictfetchall(cursor)


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
        'site_totals': site_totals.get(),
        'totals': {
            'sums': sums.get(),
            'averages_day': averages_day.get(),
            'averages_total': averages_total.get()
        },
        'rollups': rollups
    })
