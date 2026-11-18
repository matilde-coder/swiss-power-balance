-- Q1: How do production, consumption and net imports evolve month by month?
-- Positive net_import_gwh = Switzerland imported more than it exported.
SELECT
    year,
    month,
    round(sum(production_kwh)  / 1e6, 1) AS production_gwh,
    round(sum(consumption_kwh) / 1e6, 1) AS consumption_gwh,
    round(sum(net_import_kwh)  / 1e6, 1) AS net_import_gwh
FROM grid
GROUP BY year, month
ORDER BY year, month;
