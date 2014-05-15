sums_query = """
    SET timezone = "US/Pacific";
    SELECT
        %(select)s
        COUNT(*) AS count,
        SUM(d.visits) AS v,
        SUM(d.pageviews) AS pv,
        SUM(COALESCE(d.visits, 0) * COALESCE(d.time_on_page, 0))::real / SUM(d.visits) AS avg_top,
        SUM(dl.visits) AS l_v,
        SUM(dl.pageviews) AS l_pv,
        SUM(COALESCE(dl.visits, 0) * COALESCE(dl.time_on_page, 0))::real / SUM(dl.visits) AS avg_l_top,
        SUM(t.visits) AS t_v,
        SUM(t.pageviews) AS t_pv,
        SUM(COALESCE(t.visits, 0) * COALESCE(t.time_on_page, 0))::real / SUM(t.visits) AS avg_t_top,
        SUM(tl.visits) AS t_l_v,
        SUM(tl.pageviews) AS t_l_pv,
        SUM(COALESCE(tl.visits, 0) * COALESCE(tl.time_on_page, 0))::real / SUM(tl.visits) AS avg_t_l_top
    FROM
        analytics_article
        %(from)s
    LEFT OUTER JOIN analytics_stats AS d ON (
        analytics_article.stats_day_id = d.id)
    LEFT OUTER JOIN analytics_stats AS dl ON (
        analytics_article.stats_day_local_id = dl.id)
    LEFT OUTER JOIN analytics_stats AS t ON (
        analytics_article.stats_total_id = t.id)
    LEFT OUTER JOIN analytics_stats AS tl ON (
        analytics_article.stats_total_local_id = tl.id)
    %(where)s
    %(group_by)s
    ORDER BY 1 DESC;
"""