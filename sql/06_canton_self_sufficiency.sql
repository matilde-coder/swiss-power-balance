-- Q6: Which canton groups produce more electricity than they consume, in summer vs winter?
-- Ratio > 1 = net producer. Uses the most recent complete calendar year in the data.
-- Note: plants connected across cantonal borders are reported separately by Swissgrid
-- ("across Cantons") and are not included here.
WITH latest AS (
    SELECT year
    FROM grid
    GROUP BY year
    HAVING count(DISTINCT month) = 12
    ORDER BY year DESC
    LIMIT 1
),
by_region AS (
    SELECT
        c.region,
        g.half_year,
        sum(c.production_kwh)  AS production_kwh,
        sum(c.consumption_kwh) AS consumption_kwh
    FROM canton_15min c
    JOIN grid g USING (ts_utc)
    WHERE g.year = (SELECT year FROM latest)
    GROUP BY c.region, g.half_year
)
PIVOT (
    SELECT region, half_year, round(production_kwh / consumption_kwh, 2) AS ratio
    FROM by_region
)
ON half_year USING first(ratio)
ORDER BY winter DESC;
