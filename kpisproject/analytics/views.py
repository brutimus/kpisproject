import json, datetime, time, re, operator
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
from kpisproject.analytics import process


base.tag_re = (re.compile('(%s.*?%s|%s.*?%s|%s.*?%s)' %
  (re.escape(base.BLOCK_TAG_START), re.escape(base.BLOCK_TAG_END),
   re.escape(base.VARIABLE_TAG_START), re.escape(base.VARIABLE_TAG_END),
   re.escape(base.COMMENT_TAG_START), re.escape(base.COMMENT_TAG_END)), re.DOTALL))


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
    totals = process.dictfetchall(cursor)
    (
        averages_day,
        averages_day_local,
        averages_total,
        averages_total_local) = process.get_averages()

    # Daily Rollup
    cursor.execute(sql.sums_query % {
        'select': "EXTRACT(EPOCH FROM DATE_TRUNC('day', date)) AS ts,",
        'from': '',
        'where': '',
        'group_by': "GROUP BY ts"
    })
    by_day = process.dictfetchall(cursor)

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
    by_week = process.dictfetchall(cursor)

    # Monthly Rollup
    cursor.execute(sql.sums_query % {
        'select': "DATE_TRUNC('month', date) AS month,",
        'from': '',
        'where': '',
        'group_by': "GROUP BY month"
    })
    by_month = process.dictfetchall(cursor)

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
    base_article_list = Article.objects.filter(
        date__year=year,
        date__month=month,
        date__day=day
    ).select_related(
        'status',
        'category',
        'stats_day',
        'stats_day_local',
        'stats_total',
        'stats_total_local',
        'site'
    ).prefetch_related(
        'bylines'
    ).order_by('date')
    if base_article_list.count() == 0:
        return render_to_response('analytics/story_day_empty.html', {
            'today': today
        })

    base_byline_list = Byline.objects.filter(
        article__date__year=year,
        article__date__month=month,
        article__date__day=day
    ).order_by('first_name', 'last_name').distinct()

    cursor = connection.cursor()
    cursor.execute(sql.sums_query % {
        'select': '',
        'from': '',
        'where': 'WHERE date BETWEEN %s AND %s',
        'group_by': ''
    }, [today, today + datetime.timedelta(days=1)])
    sums = process.dictfetchall(cursor)[0]

    (
        site_averages_day,
        site_averages_day_local,
        site_averages_total,
        site_averages_total_local) = process.get_averages()

    (
        averages_day,
        averages_day_local,
        averages_total,
        averages_total_local) = process.get_averages(date=today)

    (
        byline_averages_day,
        byline_averages_day_local,
        byline_averages_total,
        byline_averages_total_local) = process.get_averages(
            date=today,
            byline_group=True)

    dictify = lambda y: {x['byline_id']: x for x in y}

    byline_averages_day = dictify(byline_averages_day)
    byline_averages_day_local = dictify(byline_averages_day_local)
    byline_averages_total = dictify(byline_averages_total)
    byline_averages_total_local = dictify(byline_averages_total_local)


    def summertime(data, field):
        s = lambda y:reduce(
            operator.add,
            map(
                operator.attrgetter('%s.%s' % (field, y)),
                filter(operator.attrgetter(field), data)),
            0)
        avg = lambda x:(s(x) / len(filter(
            operator.attrgetter(field),
            data))) if len(filter(
                operator.attrgetter(field),
                data)) > 0 else 0
        return {
            'count': len(data),
            'v': s('visits'),
            'avg_v': avg('visits'),
            'pv': s('pageviews'),
            'avg_pv': avg('pageviews'),
            'avg_top': (reduce(
                operator.add,
                map(
                    lambda x:reduce(
                        operator.mul,
                        operator.attrgetter(
                            '%s.visits' % field,
                            '%s.time_on_page' % field)(x)),
                    filter(
                        operator.attrgetter(field),
                        data)),
                0) / s('visits')) if s('visits') > 0 else 0
        }


    # PROCESS BYLINES
    byline_context = {
        'count': len(base_byline_list),
        'list': []
    }

    # Byline(): [Article(), ... ]
    byline_groups = {}
    for article in base_article_list:
        for byline in article.bylines.all():
            byline_groups[byline] = byline_groups.get(byline, [])
            byline_groups[byline].append(article)

    # byline_sums = summarize_groups(byline_groups)
    byline_sums = []
    for key, articles in byline_groups.items():
        byline_sums.append({
            'byline': key,
            'totals': {
                'count': len(articles),
                'day': summertime(articles, 'stats_day'),
                'day_local': summertime(articles, 'stats_day_local'),
                'total': summertime(articles, 'stats_total'),
                'total_local': summertime(articles, 'stats_total_local'),
            },
            'ratios': process.calc_ratios(
                byline_averages_day.get(key.id),
                byline_averages_day_local.get(key.id),
                site_averages_day,
                site_averages_day_local,
                byline_averages_total.get(key.id),
                byline_averages_total_local.get(key.id),
                site_averages_total,
                site_averages_total_local
            ),
            'group': articles
        })
    # ammend_sums(byline_sums)
    byline_context['list'] = sorted(
        byline_sums,
        key=lambda x:x['totals']['day'].get('v', 0),
        reverse=True)

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
    section_sums = []
    for key, articles in category_groups.items():
        section_sums.append({
            'category': articles[0].category,
            'totals': {
                'count': len(articles),
                'day': summertime(articles, 'stats_day'),
                'day_local': summertime(articles, 'stats_day_local'),
                'total': summertime(articles, 'stats_total'),
                'total_local': summertime(articles, 'stats_total_local'),
            },
            # 'ratios': process.calc_ratios(
            #     byline_averages_day.get(key.id),
            #     byline_averages_day_local.get(key.id),
            #     site_averages_day,
            #     site_averages_day_local,
            #     byline_averages_total.get(key.id),
            #     byline_averages_total_local.get(key.id),
            #     site_averages_total,
            #     site_averages_total_local
            # ),
            'group': articles
        })
    section_context['list'] = sorted(
        section_sums,
        key=lambda x:x['totals']['day'].get('v', 0),
        reverse=True)

    context = {
        'totals': {
            'sums': sums,
            'day': averages_day,
            'day_local': averages_day_local,
            'total': averages_total,
            'total_local': averages_total_local
        },
        'articles': base_article_list,
        'bylines': byline_context,
        'sections': section_context,
        'unused': base_article_list.filter(stats_day__isnull=True),
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
    base_article_list = Article.objects.filter(
        bylines__id=byline_id
    )

    cursor.execute(sql.sums_query % {
        'select': '',
        'from': '',
        'where': '',
        'group_by': ''
    })
    site_totals = process.dictfetchall(cursor)[0]

    (
        site_averages_day,
        site_averages_day_local,
        site_averages_total,
        site_averages_total_local) = process.get_averages()

    (
        averages_day,
        averages_day_local,
        averages_total,
        averages_total_local) = process.get_averages(byline_id=byline_id)

    # Sums ##########################################################
    cursor.execute(sql.sums_query % {
        'select': '',
        'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
        'where': """WHERE analytics_article.id = analytics_article_bylines.article_id
            AND analytics_article_bylines.byline_id = %s""" % int(byline_id),
        'group_by': ''
    })
    sums = process.dictfetchall(cursor)[0]

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
        sums = process.dictfetchall(cursor)[0]

        (
            roll_averages_day,
            roll_averages_day_local,
            roll_averages_total,
            roll_averages_total_local) = process.get_averages(
                byline_id=byline_id,
                start_date=d)
        

        rollups.append({
            'delta': delta,
            'sums': sums,
            'day': roll_averages_day,
            'day_local': roll_averages_day_local,
            'total': roll_averages_total,
            'total_local': roll_averages_total_local
        })


    # Daily Rollup
    cursor.execute(sql.sums_query % {
        'select': "EXTRACT(EPOCH FROM DATE_TRUNC('day', date)) AS ts,",
        'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
        'where': """WHERE analytics_article_bylines.byline_id = %s""" % int(byline_id),
        'group_by': "GROUP BY ts"
    })
    by_day = process.dictfetchall(cursor)

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
    by_week = process.dictfetchall(cursor)

    # Monthly Rollup
    cursor.execute(sql.sums_query % {
        'select': "DATE_TRUNC('month', date) AS month,",
        'from': """JOIN analytics_article_bylines ON (
            analytics_article.id = analytics_article_bylines.article_id)""",
        'where': """WHERE analytics_article_bylines.byline_id = %s""" % int(byline_id),
        'group_by': "GROUP BY month"
    })
    by_month = process.dictfetchall(cursor)

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
        'ratios': process.calc_ratios(
            averages_day,
            averages_day_local,
            site_averages_day,
            site_averages_day_local,
            averages_total,
            averages_total_local,
            site_averages_total,
            site_averages_total_local
        ),
        'rollups': rollups
    })
