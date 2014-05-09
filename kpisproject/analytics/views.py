import json, datetime, time
from operator import itemgetter, methodcaller, attrgetter
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.db import connections
from django.db.models import Sum, Avg, Count
from django.shortcuts import render_to_response
from django.views.decorators.cache import cache_page
from django.views.generic.dates import DayArchiveView
from django.views.generic.list import ListView
from kpisproject.analytics.models import Article, Byline, Category, Status


@cache_page(60 * 15)
# @login_required(login_url='/admin/')
def story_overview(request):
    totals = Article.objects.extra(
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

    by_day = Article.objects.extra(
        select={
            'ts': "EXTRACT(EPOCH from date_trunc('day', date))"
        }
    ).values('ts').annotate(
        dcount=Count('id'),
        dv=Sum('visits'),
        dpv=Sum('pageviews')
    )
    
    by_week = Article.objects.extra(
        select={
            'week': "date_trunc('week', date)",
            'week_start': "DATE_TRUNC('week', date)",
            'week_end': "DATE_TRUNC('week', date) + interval '6 days'"
        }
    ).values('week', 'week_start', 'week_end').annotate(
        dcount=Count('id'), 
        dv=Sum('visits'),
        dpv=Sum('pageviews')
    ).order_by('-week')

    by_month = Article.objects.extra(
        select={
            'month': "DATE_TRUNC('month', date)",
        }
    ).values('month').annotate(
        dcount=Count('id'), 
        dv=Sum('visits'),
        dpv=Sum('pageviews')
    ).order_by('-month')

    # Process
    for week in by_week:
        week['week_start'] = week['week_start']
        week['week_end'] = week['week_end']
    for month in by_month:
        month['month_start'] = month['month']
    return render_to_response('analytics/story_overview.html', {
        'totals': totals.get(),
        'histograms': {
            'count': {int(x['ts']): x['dcount'] for x in by_day},
            'v': {int(x['ts']): x['dv'] for x in by_day},
            'pv': {int(x['ts']): x['dpv'] for x in by_day}
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

    # Overall totals
    totals = base_article_list.extra(
        select={
            'count': 'count(*)',
            # Day of
            'top': 'sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits)',
            'v': 'sum(visits)',
            'pv': 'sum(pageviews)',
            'avg_v': 'sum(visits)/count(*)',
            'avg_pv': 'sum(pageviews)/count(*)',
            # All time
            't_top': 'sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits)',
            't_v': 'sum(all_visits)',
            't_pv': 'sum(all_pageviews)',
            'avg_t_v': 'sum(all_visits)/count(*)',
            'avg_t_pv': 'sum(all_pageviews)/count(*)',
            # Ratios day of
            'r_avg_v': '(\
                (sum(visits)/count(*))::real - (\
                    select sum(visits)/count(*) from analytics_article where visits > 0)\
            ) / (select sum(visits)/count(*) from analytics_article where visits > 0) * 100',
            'r_avg_pv': '(\
                (sum(pageviews)/count(*))::real - (\
                    select sum(pageviews)/count(*) from analytics_article where pageviews > 0)\
            ) / (select sum(pageviews)/count(*) from analytics_article where pageviews > 0) * 100',
            'r_top': '(\
                (sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits))::real - (\
                    select sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits) from analytics_article)\
            ) / (select sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits) from analytics_article) * 100',
            # Ratios all time
            'r_avg_t_v': '(\
                (sum(all_visits)/count(*))::real - (\
                    select sum(all_visits)/count(*) from analytics_article where all_visits > 0)\
            ) / (select sum(all_visits)/count(*) from analytics_article where all_visits > 0) * 100',
            'r_avg_t_pv': '(\
                (sum(all_pageviews)/count(*))::real - (\
                    select sum(all_pageviews)/count(*) from analytics_article where all_pageviews > 0)\
            ) / (select sum(all_pageviews)/count(*) from analytics_article where all_pageviews > 0) * 100',
            'r_t_top': '(\
                (sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits))::real - (\
                    select sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits) from analytics_article)\
            ) / (select sum(COALESCE(all_visits, 0) * COALESCE(all_time_on_page, 0)) / sum(all_visits) from analytics_article) * 100'
        }
    ).values(
        'count',
        'top',
        't_top',
        'v',
        't_v',
        'pv',
        't_pv',
        'avg_v',
        'avg_t_v',
        'avg_pv',
        'avg_t_pv',
        'r_avg_v',
        'r_avg_pv',
        'r_top',
        'r_avg_t_v',
        'r_avg_t_pv',
        'r_t_top',
    )

    # Past 30 days
    days_30 = totals.filter(
        date__gte=datetime.date.today() - datetime.timedelta(days=30)
    ).get()
    # Past 60 days
    days_60 = totals.filter(
        date__gte=datetime.date.today() - datetime.timedelta(days=60)
    ).get()
    # Past 90 days
    days_90 = totals.filter(
        date__gte=datetime.date.today() - datetime.timedelta(days=90)
    ).get()
    # Past 180 days
    days_180 = totals.filter(
        date__gte=datetime.date.today() - datetime.timedelta(days=180)
    ).get()
    # Past 12 months
    months_12 = totals.filter(
        date__gte=datetime.date.today() - datetime.timedelta(days=365)
    ).get()
    print days_30, days_60, days_90, days_180

    # Daily Rollup
    by_day = base_article_list.extra(
        select={
            'ts': "EXTRACT(EPOCH from date_trunc('day', date))"
        }
    ).values('ts').annotate(
        dcount=Count('id'),
        dv=Sum('all_visits'),
        dpv=Sum('all_pageviews')
    )

    # Weekly Rollup
    by_week = base_article_list.extra(
        select={
            'week': "date_trunc('week', date)",
            'week_start': "DATE_TRUNC('week', date)",
            'week_end': "DATE_TRUNC('week', date) + interval '6 days'"
        }
    ).values('week', 'week_start', 'week_end').annotate(
        dcount=Count('id'), 
        dv=Sum('all_visits'),
        dpv=Sum('all_pageviews')
    ).order_by('-week')

    # Monthly Rollup
    by_month = base_article_list.extra(
        select={
            'month': "DATE_TRUNC('month', date)"
        }
    ).values('month').annotate(
        dcount=Count('id'), 
        dv=Sum('all_visits'),
        dpv=Sum('all_pageviews')
    ).order_by('-month')

    # Process
    for week in by_week:
        week['week_start'] = week['week_start']
        week['week_end'] = week['week_end']
    for month in by_month:
        month['month_start'] = month['month']

    return render_to_response('analytics/byline.html', {
        'byline': Byline.objects.get(id=int(byline_id)),
        'articles': base_article_list.order_by('-date').select_related('status'),
        'histograms': {
            'count': {int(x['ts']): x['dcount'] for x in by_day},
            'v': {int(x['ts']): x['dv'] for x in by_day},
            'pv': {int(x['ts']): x['dpv'] for x in by_day}
        },
        'by_week': by_week,
        'by_month': by_month,
        'site_totals': site_totals.get(),
        'totals': totals.get(),
        'rollups': ({
            'name': 'Past 30 Days',
            'stats': days_30
        },{
            'name': 'Past 60 Days',
            'stats': days_60
        },{
            'name': 'Past 90 Days',
            'stats': days_90
        },{
            'name': 'Past 180 Days',
            'stats': days_180
        },{
            'name': 'Past 12 Months',
            'stats': months_12
        },)
    })
