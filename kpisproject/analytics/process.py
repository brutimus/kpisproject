import datetime, pprint
from django.db import connection

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [
        dict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()
    ]

def get_averages(byline_id=None, byline_group=False, start_date=None, date=None):
    cursor = connection.cursor()
    avg_sql = """
        SELECT
            %(sql_select)s
            COUNT(*) AS count,
            SUM(visits) AS v,
            SUM(pageviews) AS pv,
            SUM(visits) / COUNT(*) AS avg_v,
            SUM(pageviews) / COUNT(*) AS avg_pv,
            SUM(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / SUM(visits) AS avg_top
        FROM
            analytics_article,
            %(sql_from)s
            analytics_stats
        WHERE
            visits IS NOT NULL
            %(sql_where)s
            AND analytics_article.%(stats_field)s = analytics_stats.id
            %(sql_date_gt)s
            %(sql_date_eq)s
        %(sql_group_by)s;
    """
    sql_byline_group_select = "byline_id,"
    sql_byline_group = "GROUP BY byline_id"
    sql_byline_group_where = "AND analytics_article.id = analytics_article_bylines.article_id"

    sql_byline_from = "analytics_article_bylines,"
    sql_byline_where = """
        AND analytics_article.id = analytics_article_bylines.article_id
        AND analytics_article_bylines.byline_id = %s"""
    sql_date_gt = "AND date >= TIMESTAMP %s"
    sql_date_eq = "AND date BETWEEN %s AND %s"

    params = []
    if byline_id:
        params.append(byline_id)
    if start_date:
        params.append(start_date)
    if date:
        params.extend([date, date + datetime.timedelta(days=1)])


    def do_query(stats_field, params):
        sub = {
            'sql_select': '',
            'sql_from': '',
            'sql_where': '',
            'sql_group_by': '',
            'sql_date_gt': sql_date_gt if start_date else '',
            'sql_date_eq': sql_date_eq if date else '',
            'stats_field': stats_field
        }
        if byline_group:
            sub.update({
                'sql_select': sql_byline_group_select,
                'sql_from': sql_byline_from,
                'sql_where': sql_byline_group_where,
                'sql_group_by': sql_byline_group
            })
        if byline_id:
            sub.update({
                'sql_from': sql_byline_from,
                'sql_where': sql_byline_where
            })
        cursor.execute(avg_sql % sub, params)
        return dictfetchall(cursor)

    averages_day = do_query('stats_day_id', params)
    averages_day_local = do_query('stats_day_local_id', params)
    averages_total = do_query('stats_total_id', params)
    averages_total_local = do_query('stats_total_local_id', params)
    return (
        averages_day[0] if len(averages_day) == 1 else averages_day,
        averages_day_local[0] if len(averages_day_local) == 1 else averages_day_local,
        averages_total[0] if len(averages_total) == 1 else averages_total,
        averages_total_local[0] if len(averages_total_local) == 1 else averages_total_local
    )

def floatall(d):
    return {k: float(v) for k, v in d.items()}

def calc_ratios(d, dl, sd, sdl, t, tl, st, stl):
    if not all((d, dl, sd, sdl, t, tl, st, stl)):
        return {}
    d = floatall(d)
    dl = floatall(dl)
    sd = floatall(sd)
    sdl = floatall(sdl)
    t = floatall(t)
    tl = floatall(tl)
    st = floatall(st)
    stl = floatall(stl)
    return {
        'day': {
            # Compare day to site avg
            'avg_v': (d['avg_v'] - sd['avg_v']) / sd['avg_v'],
            'avg_pv': (d['avg_pv'] - sd['avg_pv']) / sd['avg_pv'],
            'avg_top': (d['avg_top'] - sd['avg_top']) / sd['avg_top']},
        'day_local': {
            # Compare day local to day (percent local)
            'avg_v': dl['avg_v'] / d['avg_v'],
            'avg_pv': dl['avg_pv'] / d['avg_pv'],
            'avg_top': dl['avg_top'] / d['avg_top'],
            # Compare byline percent local to site percent local
            'r_avg_v': (
                (dl['avg_v'] / d['avg_v']) - (
                sdl['avg_v'] / sd['avg_v'])) / (
                sdl['avg_v'] / sd['avg_v']),
            'r_avg_pv': (
                (dl['avg_pv'] / d['avg_pv']) - (
                sdl['avg_pv'] / sd['avg_pv'])) / (
                sdl['avg_pv'] / sd['avg_pv']),
            'r_avg_top': (
                (dl['avg_top'] / d['avg_top']) - (
                sdl['avg_top'] / sd['avg_top'])) / (
                sdl['avg_top'] / sd['avg_top'])},
        'total': {
            # Compare total to site total
            'avg_v': (t['avg_v'] - st['avg_v']) / st['avg_v'],
            'avg_pv': (t['avg_pv'] - st['avg_pv']) / st['avg_pv'],
            'avg_top': (t['avg_top'] - st['avg_top']) / st['avg_top']},
        'total_local': {
            # Compare total local to total (percent local)
            'avg_v': tl['avg_v'] / t['avg_v'],
            'avg_pv': tl['avg_pv'] / t['avg_pv'],
            'avg_top': tl['avg_top'] / t['avg_top'],
            # Compare byline percent local to site percent local
            'r_avg_v': (
                (tl['avg_v'] / t['avg_v']) - (
                stl['avg_v'] / st['avg_v'])) / (
                stl['avg_v'] / st['avg_v']),
            'r_avg_pv': (
                (tl['avg_pv'] / t['avg_pv']) - (
                stl['avg_pv'] / st['avg_pv'])) / (
                stl['avg_pv'] / st['avg_pv']),
            'r_avg_top': (
                (tl['avg_top'] / t['avg_top']) - (
                stl['avg_top'] / st['avg_top'])) / (
                stl['avg_top'] / st['avg_top'])},
    }