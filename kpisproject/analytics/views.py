import json, datetime, time
from operator import itemgetter, methodcaller, attrgetter
from itertools import groupby

from django.db import connections
from django.db.models import Sum, Avg, Count
from django.shortcuts import render_to_response
from django.views.decorators.cache import cache_page
from django.views.generic.dates import DayArchiveView
from django.views.generic.list import ListView
from kpisproject.analytics.models import Article, Byline, Category, Status


EDIT_URL = "http://admin.onset.freedom.com/modules/articles/edit.php?id="
VIEW_URL = "%s"

@cache_page(60 * 15)
def story_overview(request):
    by_day = Article.objects.extra(
        select={
            # Don't know why I need the +1 days, but it works.
            # This code requires my custom django patch.
            'ts': "EXTRACT(EPOCH from date_trunc('day', date))"
            # 'ts': "strftime('%%s', date, 'start of day', '+1 days')"
        }
    ).values('ts').annotate(
        dcount=Count('id'),
        dv=Sum('visits'),
        dpv=Sum('pageviews')
    )
    
    by_week = Article.objects.extra(
        select={
            # Again, not totally sure on the date math here, but it works.
            # I think I'm just confused about 0-indexed weeks.
            'week': "date_trunc('week', date)",
            'week_start': "DATE_TRUNC('week', date)",
            'week_end': "DATE_TRUNC('week', date) + interval '6 days'"
            # 'week_start': "strftime('%%s', date, 'start of day', 'weekday 0', '-5 days')",
            # 'week_end': "strftime('%%s', date, 'start of day', 'weekday 0', '+1 day')"
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

    base_article_list = Article.objects.filter(
        date__year=year,
        date__month=month,
        date__day=day
    ).extra(
        select={'expanded_avg': 'COALESCE(visits, 0) * COALESCE(time_on_page, 0)'}
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
    total_v = sum(map(lambda x:x.visits or 0, base_article_list))
    total_pv = sum(map(lambda x:x.pageviews or 0, base_article_list))
    total_avg_time_on_page = (
        sum(map(attrgetter('expanded_avg'), base_article_list)) / total_v
    ) if total_v > 0 else None
    # PROCESS BYLINES
    byline_context = {
        'count': 0,
        'list': []
    }

    byline_context['count'] = len(base_byline_list)

    # Byline(): [Article(), ... ]
    byline_groups = {}
    for article in base_article_list:
        for byline in article.bylines.all():
            byline_groups[byline] = byline_groups.get(byline, [])
            byline_groups[byline].append(article)

    for byline, article_list in byline_groups.items():
        byline_total_v = sum(map(lambda x:x.visits or 0, article_list))
        byline_total_pv = sum(map(lambda x:x.pageviews or 0, article_list))
        byline_context['list'].append({
            'byline': byline,
            'count': len(article_list),
            'list': article_list,
            'total_visits': byline_total_v,
            'total_pageviews': byline_total_pv,
            'avg_time_on_page': (
                sum(map(
                    attrgetter('expanded_avg'), article_list
                )) / byline_total_v
            ) if byline_total_v > 0 else None,
            'percent_total_visits': (
                float(byline_total_v) / float(total_v)) * 100,
            'percent_total_pageviews': (
                float(byline_total_pv) / float(total_pv)) * 100
        })

    # PROCESS SECTIONS
    section_context = {
        'count': 0,
        'list': []
    }
    key = lambda x:x.category.name if x.category else None
    category_group = [
        (key, list(group)) for key, group in
        groupby(sorted(base_article_list, key=key), key=key)]
    section_context['count'] = len(category_group)
    for category, article_list in category_group:
        article_list = list(article_list)
        section_total_v = sum(map(lambda x:x.visits or 0, article_list))
        section_total_pv = sum(map(lambda x:x.pageviews or 0, article_list))
        section_context['list'].append({
            'section': category,
            'count': len(article_list),
            'list': article_list,
            'total_visits': section_total_v,
            'total_pageviews': section_total_pv,
            'avg_time_on_page': (
                sum(map(
                    attrgetter('expanded_avg'), article_list
                )) / section_total_v
            ) if section_total_v > 0 else None,
            'percent_total_visits': (
                float(section_total_v) / float(total_v)) * 100,
            'percent_total_pageviews': (
                float(section_total_pv) / float(total_pv)) * 100
        })

    context = {
        'totals': {
            'visits__sum': total_v,
            'pageviews__sum': total_pv,
            'time_on_page__avg': total_avg_time_on_page
        },
        'articles': base_article_list,
        'bylines': byline_context,
        'sections': section_context,
        'unused': Article.objects.filter(
            date__year=year,
            date__month=month,
            date__day=day,
            visits__isnull=True
        ).order_by('date').select_related('status', 'category'),
        'EDIT_URL': EDIT_URL,
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
    base_article_list = Article.objects.filter(
        bylines__id=byline_id
    )

    # Overall totals
    totals = base_article_list.extra(
        select={
            'dcount': 'count(*)',
            'dtop': 'sum(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / sum(visits)',
            'dv': 'sum(visits)',
            'dpv': 'sum(pageviews)',
            'avg_v': 'sum(visits)/count(*)',
            'avg_pv': 'sum(pageviews)/count(*)'
        }
    ).values('dcount', 'dtop', 'dv', 'dpv', 'avg_v', 'avg_pv')

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

    # Daily Rollup
    by_day = base_article_list.extra(
        select={
            # Don't know why I need the +1 days, but it works.
            # This code requires my custom django patch.
            # 'ts': "strftime('%%s', date, 'start of day', '+1 days')"
            'ts': "EXTRACT(EPOCH from date_trunc('day', date))"
        }
    ).values('ts').annotate(
        dcount=Count('id'),
        dv=Sum('visits'),
        dpv=Sum('pageviews')
    )

    # Weekly Rollup
    by_week = base_article_list.extra(
        select={
            # Again, not totally sure on the date math here, but it works.
            # I think I'm just confused about 0-indexed weeks.
            'week': "date_trunc('week', date)",
            'week_start': "DATE_TRUNC('week', date)",
            'week_end': "DATE_TRUNC('week', date) + interval '6 days'"
        }
    ).values('week', 'week_start', 'week_end').annotate(
        dcount=Count('id'), 
        dv=Sum('visits'),
        dpv=Sum('pageviews')
    ).order_by('-week')

    # Monthly Rollup
    by_month = base_article_list.extra(
        select={
            'month': "DATE_TRUNC('month', date)"
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

    return render_to_response('analytics/byline.html', {
        'byline': Byline.objects.get(id=byline_id),
        'articles': base_article_list.order_by('-date').select_related('status'),
        'histograms': {
            'count': {int(x['ts']): x['dcount'] for x in by_day},
            'v': {int(x['ts']): x['dv'] for x in by_day},
            'pv': {int(x['ts']): x['dpv'] for x in by_day}
        },
        'by_week': by_week,
        'by_month': by_month,
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
        },),
        'EDIT_URL': EDIT_URL
        })
