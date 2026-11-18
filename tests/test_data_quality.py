"""Data-quality checks on the built database. Skipped if `make load` has not run."""

from pathlib import Path

import duckdb
import pytest

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "swiss_power.duckdb"
pytestmark = pytest.mark.skipif(not DB_PATH.exists(), reason="database not built")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(DB_PATH), read_only=True)
    yield c
    c.close()


def test_every_year_is_complete(con):
    rows = con.execute("""
        SELECT year(ts_local) AS y, count(*) AS n,
               (date_diff('day', make_date(y, 1, 1), make_date(y + 1, 1, 1))) * 96 AS expected
        FROM grid_15min GROUP BY y
    """).fetchall()
    assert rows and all(n == expected for _, n, expected in rows)


def test_timestamps_are_unique_and_gap_free(con):
    gaps = con.execute("""
        SELECT count(*) FROM (
            SELECT ts_utc - lag(ts_utc) OVER (ORDER BY ts_utc) AS step FROM grid_15min
        ) WHERE step IS NOT NULL AND step <> INTERVAL 15 MINUTE
    """).fetchone()[0]
    assert gaps == 0


def test_no_missing_or_negative_energy_values(con):
    cols = [c for (c,) in con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'grid_15min' AND column_name LIKE '%_kwh'").fetchall()]
    checks = " + ".join(f"count(*) FILTER (WHERE {c} IS NULL OR {c} < 0)" for c in cols)
    assert con.execute(f"SELECT {checks} FROM grid_15min").fetchone()[0] == 0


def test_energy_balance_closes(con):
    """Production + net imports should match consumption within 1% every year."""
    ratios = con.execute("""
        SELECT year, sum(production_kwh + net_import_kwh) / sum(consumption_kwh)
        FROM grid GROUP BY year
    """).fetchall()
    assert all(abs(r - 1) < 0.01 for _, r in ratios), ratios


def test_canton_table_has_one_row_per_region_and_interval(con):
    n_grid = con.execute("SELECT count(*) FROM grid_15min").fetchone()[0]
    n_regions, n_rows = con.execute(
        "SELECT count(DISTINCT region), count(*) FROM canton_15min").fetchone()
    assert n_regions == 18
    assert n_rows == n_grid * n_regions


def test_flows_long_matches_wide_table(con):
    wide = con.execute("SELECT sum(net_import_kwh) FROM grid").fetchone()[0]
    long = con.execute(
        "SELECT sum(CASE WHEN direction = 'import' THEN kwh ELSE -kwh END) FROM flows_long").fetchone()[0]
    assert abs(wide - long) < 1
