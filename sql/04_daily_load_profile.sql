-- Q4: What does a typical day look like? Average end-user demand (MW) by hour,
-- for winter vs summer and weekdays vs weekends.
-- kWh per 15 min * 4 = average kW over the interval; / 1000 -> MW.
SELECT
    half_year,
    day_type,
    hour,
    round(avg(consumption_end_users_kwh) * 4 / 1000) AS avg_demand_mw
FROM grid
GROUP BY half_year, day_type, hour
ORDER BY half_year, day_type, hour;
