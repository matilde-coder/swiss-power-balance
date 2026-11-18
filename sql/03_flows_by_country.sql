-- Q3: Which neighbours supply Switzerland in winter, and which ones buy its power?
-- Net flow per neighbour and complete winter; positive = net import into Switzerland.
WITH complete_winters AS (
    SELECT winter FROM grid
    WHERE half_year = 'winter'
    GROUP BY winter
    HAVING count(DISTINCT month) = 6
),
net_by_country AS (
    SELECT
        g.winter,
        f.country,
        sum(CASE WHEN f.direction = 'import' THEN f.kwh ELSE -f.kwh END) AS net_import_kwh
    FROM flows_long f
    JOIN grid g USING (ts_utc)
    WHERE g.winter IN (SELECT winter FROM complete_winters)
    GROUP BY g.winter, f.country
)
SELECT
    winter,
    country,
    round(net_import_kwh / 1e9, 2) AS net_import_twh,
    RANK() OVER (PARTITION BY winter ORDER BY net_import_kwh DESC) AS supplier_rank
FROM net_by_country
ORDER BY winter, supplier_rank;
