-- Left off calculating the ratios of date averages to site averages
-- Also didn't finish doing all the ratios between sums

set timezone = "US/Pacific";
WITH site_sums AS (
	SELECT
		-- Totals
		AVG(d.visits) AS site_avg_v,
		AVG(d.pageviews) AS site_avg_pv,
		SUM(d.visits * d.time_on_page) / SUM(d.visits) AS site_avg_top,
		AVG(dl.visits) AS site_avg_l_v,
		AVG(dl.pageviews) AS site_avg_l_pv,
		SUM(dl.visits * dl.time_on_page) / SUM(dl.visits) AS site_avg_l_top,
		AVG(t.visits) AS site_avg_t_v,
		AVG(t.pageviews) AS site_avg_t_pv,
		SUM(t.visits * t.time_on_page) / SUM(t.visits) AS site_avg_t_top,
		AVG(tl.visits) AS site_avg_t_l_v,
		AVG(tl.pageviews) AS site_avg_t_l_pv,
		SUM(tl.visits * tl.time_on_page) / SUM(tl.visits) AS site_avg_t_l_top
	FROM
		analytics_article AS a
	LEFT OUTER JOIN analytics_stats AS d ON (a.stats_day_id = d.id)
	LEFT OUTER JOIN analytics_stats AS dl ON (a.stats_day_local_id = dl.id)
	LEFT OUTER JOIN analytics_stats AS t ON (a.stats_total_id = t.id)
	LEFT OUTER JOIN analytics_stats AS tl ON (a.stats_total_local_id = tl.id)
)
WITH sums AS (
	SELECT
		-- Totals
		SUM(d.visits) AS all_v,
		AVG(d.visits) AS all_avg_v,
		SUM(d.pageviews) AS all_pv,
		AVG(d.pageviews) AS all_avg_pv,
		SUM(d.visits * d.time_on_page) / SUM(d.visits) AS all_avg_top,
		SUM(dl.visits) AS all_l_v,
		AVG(dl.visits) AS all_avg_l_v,
		SUM(dl.pageviews) AS all_l_pv,
		AVG(dl.pageviews) AS all_avg_l_pv,
		SUM(dl.visits * dl.time_on_page) / SUM(dl.visits) AS all_avg_l_top,
		SUM(t.visits) AS all_t_v,
		AVG(t.visits) AS all_avg_t_v,
		SUM(t.pageviews) AS all_t_pv,
		AVG(t.pageviews) AS all_avg_t_pv,
		SUM(t.visits * t.time_on_page) / SUM(t.visits) AS all_avg_t_top,
		SUM(tl.visits) AS all_t_l_v,
		AVG(tl.visits) AS all_avg_t_l_v,
		SUM(tl.pageviews) AS all_pt_l_v,
		AVG(tl.pageviews) AS all_avg_t_l_pv,
		SUM(tl.visits * tl.time_on_page) / SUM(tl.visits) AS all_avg_t_l_top
	FROM
		site_sums AS ss,
		analytics_article AS a
	LEFT OUTER JOIN analytics_stats AS d ON (a.stats_day_id = d.id)
	LEFT OUTER JOIN analytics_stats AS dl ON (a.stats_day_local_id = dl.id)
	LEFT OUTER JOIN analytics_stats AS t ON (a.stats_total_id = t.id)
	LEFT OUTER JOIN analytics_stats AS tl ON (a.stats_total_local_id = tl.id)
	WHERE
		date BETWEEN '2014-5-13'::timestamp AND '2014-5-14'::timestamp
)
SELECT
	a.id,
	a.headline,
	b.id,
	b.first_name,
	b.last_name,
	c.name,
	d.visits AS v,
	d.pageviews AS pv,
	d.time_on_page AS top,
	dl.visits AS l_v,
	dl.pageviews AS l_pv,
	dl.time_on_page AS l_top,
	t.visits AS t_v,
	t.pageviews AS t_pv,
	t.time_on_page AS t_top,
	tl.visits AS t_l_v,
	tl.pageviews AS t_l_pv,
	tl.time_on_page AS t_l_top,
	-- Sums
	all_v,
	all_avg_v,
	all_pv,
	all_avg_pv,
	all_avg_top,
	all_l_v,
	all_avg_l_v,
	all_l_pv,
	all_avg_l_pv,
	all_avg_l_top,
	all_t_v,
	all_avg_t_v,
	all_t_pv,
	all_avg_t_pv,
	all_avg_t_top,
	all_t_l_v,
	all_avg_t_l_v,
	all_t_l_pv,
	all_avg_t_l_pv,
	all_avg_t_l_top,
	-- Category
	COUNT(*) OVER wc AS category_count,
	---- Day
	SUM(d.visits) OVER wc AS category_v,
	AVG(d.visits) OVER wc AS category_avg_v,
	SUM(d.pageviews) OVER wc AS category_pv,
	AVG(d.pageviews) OVER wc AS category_avg_pv,
	SUM(d.visits * d.time_on_page) OVER wc / SUM(d.visits) OVER wc AS category_avg_top,
	---- Day Local
	SUM(dl.visits) OVER wc AS category_l_v,
	AVG(dl.visits) OVER wc AS category_avg_l_v,
	SUM(dl.pageviews) OVER wc AS category_l_pv,
	AVG(dl.pageviews) OVER wc AS category_avg_l_pv,
	SUM(dl.visits * dl.time_on_page) OVER wc / SUM(dl.visits) OVER wc AS category_avg_l_top,
	---- Total
	SUM(t.visits) OVER wc AS category_t_v,
	AVG(t.visits) OVER wc AS category_avg_t_v,
	SUM(t.pageviews) OVER wc AS category_t_pv,
	AVG(t.pageviews) OVER wc AS category_avg_t_pv,
	SUM(t.visits * t.time_on_page) OVER wc / SUM(t.visits) OVER wc AS category_avg_t_top,
	---- Total Local
	SUM(tl.visits) OVER wc AS category_t_l_v,
	AVG(tl.visits) OVER wc AS category_avg_t_l_v,
	SUM(tl.pageviews) OVER wc AS category_t_l_pv,
	AVG(tl.pageviews) OVER wc AS category_avg_t_l_pv,
	SUM(tl.visits * tl.time_on_page) OVER wc / SUM(tl.visits) OVER wc AS category_avg_t_l_top,
	-- Byline
	COUNT(*) over wb AS byline_count,
	---- Day
		SUM(d.visits) OVER wb AS byline_v,
		AVG(d.visits) OVER wb AS byline_avg_v,
		SUM(d.pageviews) OVER wb AS byline_pv,
		AVG(d.pageviews) OVER wb AS byline_avg_pv,
		SUM(d.visits * d.time_on_page) OVER wb / SUM(d.visits) OVER wb AS byline_avg_top,
		---- Day / Site Day
			SUM(d.visits::numeric) OVER wb / all_v AS byline_r_v,
			SUM(d.pageviews::numeric) OVER wb / all_pv AS byline_r_pv,

	---- Day Local
		SUM(dl.visits) OVER wb AS byline_l_v,
		AVG(dl.visits) OVER wb AS byline_avg_l_v,
		SUM(dl.pageviews) OVER wb AS byline_l_pv,
		AVG(dl.pageviews) OVER wb AS byline_avg_l_pv,
		SUM(dl.visits * dl.time_on_page) OVER wb / SUM(dl.visits) OVER wb AS byline_avg_l_top,
		---- Day Local / Day
		SUM(dl.visits) OVER wb / SUM(d.visits) OVER wb AS byline_r_dl_d_v,
		SUM(dl.pageviews) OVER wb / SUM(d.pageviews) OVER wb AS byline_r_dl_d_pv,

	---- Total
	SUM(t.visits) OVER wb AS byline_t_v,
	AVG(t.visits) OVER wb AS byline_avg_t_v,
	SUM(t.pageviews) OVER wb AS byline_t_pv,
	AVG(t.pageviews) OVER wb AS byline_avg_t_pv,
	SUM(t.visits * t.time_on_page) OVER wb / SUM(t.visits) OVER wb AS byline_avg_t_top,
	---- Total Local
	SUM(tl.visits) OVER wb AS byline_t_l_v,
	AVG(tl.visits) OVER wb AS byline_avg_t_l_v,
	SUM(tl.pageviews) OVER wb AS byline_t_l_pv,
	AVG(tl.pageviews) OVER wb AS byline_avg_t_l_pv,
	SUM(tl.visits * tl.time_on_page) OVER wb / SUM(tl.visits) OVER wb AS byline_avg_t_l_top
FROM
	sums,
	analytics_article AS a
LEFT OUTER JOIN analytics_article_bylines AS ab ON (a.id = ab.article_id)
LEFT OUTER JOIN analytics_byline AS b ON (ab.byline_id = b.id)
LEFT OUTER JOIN analytics_stats AS d ON (a.stats_day_id = d.id)
LEFT OUTER JOIN analytics_stats AS dl ON (a.stats_day_local_id = dl.id)
LEFT OUTER JOIN analytics_stats AS t ON (a.stats_total_id = t.id)
LEFT OUTER JOIN analytics_stats AS tl ON (a.stats_total_local_id = tl.id)
LEFT OUTER JOIN analytics_category AS c ON (a.category_id = c.id)
WHERE
	date BETWEEN '2014-5-13'::timestamp AND '2014-5-14'::timestamp
WINDOW
	wb AS (PARTITION BY b.id),
	wc AS (PARTITION BY c.id)
order by a.id;