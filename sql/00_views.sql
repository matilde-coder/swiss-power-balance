-- Reusable views on top of the raw 15-minute tables.
-- Energy columns are kWh per 15-minute interval. Calendar fields use Swiss local time.

-- National series + calendar attributes + net imports
CREATE OR REPLACE VIEW grid AS
SELECT
    *,
    year(ts_local)                                   AS year,
    month(ts_local)                                  AS month,
    hour(ts_local)                                   AS hour,
    CASE WHEN isodow(ts_local) >= 6 THEN 'weekend' ELSE 'weekday' END AS day_type,
    -- Swiss energy statistics split the year into a winter (Oct-Mar) and summer (Apr-Sep) half
    CASE WHEN month(ts_local) IN (10, 11, 12, 1, 2, 3) THEN 'winter' ELSE 'summer' END AS half_year,
    -- A winter is labelled by the year it starts in: Oct 2022 - Mar 2023 -> '2022/23'
    CASE
        WHEN month(ts_local) >= 10 THEN year(ts_local) || '/' || right(CAST(year(ts_local) + 1 AS VARCHAR), 2)
        WHEN month(ts_local) <= 3  THEN year(ts_local) - 1 || '/' || right(CAST(year(ts_local) AS VARCHAR), 2)
    END                                              AS winter,
    (at_to_ch_kwh + de_to_ch_kwh + fr_to_ch_kwh + it_to_ch_kwh)
      - (ch_to_at_kwh + ch_to_de_kwh + ch_to_fr_kwh + ch_to_it_kwh) AS net_import_kwh
FROM grid_15min;

-- Cross-border flows in long format: one row per interval, neighbour and direction
CREATE OR REPLACE VIEW flows_long AS
WITH unpivoted AS (
    UNPIVOT (
        SELECT ts_utc, ts_local,
               at_to_ch_kwh, de_to_ch_kwh, fr_to_ch_kwh, it_to_ch_kwh,
               ch_to_at_kwh, ch_to_de_kwh, ch_to_fr_kwh, ch_to_it_kwh
        FROM grid_15min
    )
    ON COLUMNS('_to_')
    INTO NAME flow VALUE kwh
)
SELECT
    ts_utc,
    ts_local,
    CASE WHEN flow LIKE 'ch_to_%' THEN upper(substr(flow, 7, 2)) ELSE upper(substr(flow, 1, 2)) END AS country,
    CASE WHEN flow LIKE 'ch_to_%' THEN 'export' ELSE 'import' END AS direction,
    kwh
FROM unpivoted;
