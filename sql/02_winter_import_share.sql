-- Q2: How dependent is Switzerland on imports each winter (Oct-Mar), and is it changing?
-- Only complete winters (all six months in the data) are kept.
WITH winters AS (
    SELECT
        winter,
        count(DISTINCT month)  AS n_months,
        sum(production_kwh)    AS production_kwh,
        sum(consumption_kwh)   AS consumption_kwh,
        sum(net_import_kwh)    AS net_import_kwh
    FROM grid
    WHERE half_year = 'winter'
    GROUP BY winter
)
SELECT
    winter,
    round(production_kwh  / 1e9, 2)                    AS production_twh,
    round(consumption_kwh / 1e9, 2)                    AS consumption_twh,
    round(net_import_kwh  / 1e9, 2)                    AS net_import_twh,
    round(100 * net_import_kwh / consumption_kwh, 1)  AS import_share_pct,
    -- change vs previous winter, in percentage points
    round(100 * net_import_kwh / consumption_kwh
          - LAG(100 * net_import_kwh / consumption_kwh) OVER (ORDER BY winter), 1) AS change_pp
FROM winters
WHERE n_months = 6
ORDER BY winter;
