daily_rollup = """
    SELECT
        EXTRACT(EPOCH from date_trunc('day', date)) as ts,
        COUNT(*) AS count,
        SUM(visits) AS v,
        SUM(pageviews) AS pv,
        SUM(all_visits) AS t_v,
        SUM(all_pageviews) AS t_pv
    FROM
        analytics_article
    LEFT OUTER JOIN analytics_article_bylines ON (
        analytics_article.id = analytics_article_bylines.article_id)
    WHERE
        %s
    GROUP BY
        ts;
"""

weekly_rollup = """
    SELECT
        DATE_TRUNC('week', date) AS week_start,
        DATE_TRUNC('week', date) + interval '6 days' AS week_end,
        COUNT(*) AS count,
        SUM(visits) AS v,
        SUM(pageviews) AS pv,
        SUM(all_visits) AS t_v,
        SUM(all_pageviews) AS t_pv,
        SUM(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / SUM(visits) AS avg_top
    FROM
        analytics_article
    LEFT OUTER JOIN analytics_article_bylines ON (
        analytics_article.id = analytics_article_bylines.article_id)
    WHERE
        %s
    GROUP BY
        week_start,
        week_end
    ORDER BY
        week_start DESC;
"""

monthly_rollup = """
    SELECT
        DATE_TRUNC('month', date) AS month,
        COUNT(*) AS count,
        SUM(visits) AS v,
        SUM(pageviews) AS pv,
        SUM(all_visits) AS t_v,
        SUM(all_pageviews) AS t_pv,
        SUM(COALESCE(visits, 0) * COALESCE(time_on_page, 0)) / SUM(visits) AS avg_top
    FROM
        analytics_article
    LEFT OUTER JOIN analytics_article_bylines ON (
        analytics_article.id = analytics_article_bylines.article_id)
    WHERE
        %s
    GROUP BY
        month
    ORDER BY
        month DESC;
"""