-- Q5: When are the top 1% demand quarter-hours each year, and how much of the
-- demand is covered by imports at those moments compared with the rest of the year?
WITH ranked AS (
    SELECT
        *,
        PERCENT_RANK() OVER (PARTITION BY year ORDER BY consumption_end_users_kwh) AS pct_rank
    FROM grid
),
labelled AS (
    SELECT *, CASE WHEN pct_rank >= 0.99 THEN 'peak' ELSE 'other' END AS segment
    FROM ranked
)
SELECT
    year,
    round(min(consumption_end_users_kwh) FILTER (WHERE segment = 'peak') * 4 / 1000)   AS peak_threshold_mw,
    round(100 * avg(CASE WHEN month IN (12, 1, 2) THEN 1 ELSE 0 END) FILTER (WHERE segment = 'peak')) AS peaks_in_dec_feb_pct,
    round(100 * avg(CASE WHEN day_type = 'weekday' AND hour BETWEEN 7 AND 12 THEN 1 ELSE 0 END)
          FILTER (WHERE segment = 'peak'))                                              AS peaks_weekday_7_to_13h_pct,
    round(100 * avg(net_import_kwh / consumption_kwh) FILTER (WHERE segment = 'peak'), 1)  AS import_share_peak_pct,
    round(100 * avg(net_import_kwh / consumption_kwh) FILTER (WHERE segment = 'other'), 1) AS import_share_other_pct
FROM labelled
GROUP BY year
ORDER BY year;
