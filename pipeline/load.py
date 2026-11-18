"""Clean the Swissgrid Excel files and load them into a DuckDB database.

Creates two tables:
  grid_15min    one row per 15-minute interval, national totals + cross-border flows
  canton_15min  one row per interval and canton group (production / consumption)

Timestamps: Swissgrid labels intervals in Swiss local time, and the convention
changed in 2025 (interval *end* until 2024, interval *start* from 2025). Local
time also has a repeated hour in October. Instead of parsing the labels, we use
the fact that every file is a complete, gap-free 15-minute series for one
calendar year: row i starts at (1 Jan 00:00 local) + i * 15 min. The labels are
then used only as a cross-check.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "swiss_power.duckdb"
SHEET = "Zeitreihen0h15"
TZ = "Europe/Zurich"

# English header text (second line of each Swissgrid header) -> column name
NATIONAL_COLUMNS = {
    "Total energy consumed by end users in the Swiss controlblock": "consumption_end_users_kwh",
    "Total energy production Swiss controlblock": "production_kwh",
    "Total energy consumption Swiss controlblock": "consumption_kwh",
    "Cross Border Exchange CH->AT": "ch_to_at_kwh",
    "Cross Border Exchange AT->CH": "at_to_ch_kwh",
    "Cross Border Exchange CH->DE": "ch_to_de_kwh",
    "Cross Border Exchange DE->CH": "de_to_ch_kwh",
    "Cross Border Exchange CH->FR": "ch_to_fr_kwh",
    "Cross Border Exchange FR->CH": "fr_to_ch_kwh",
    "Cross Border Exchange CH->IT": "ch_to_it_kwh",
    "Cross Border Exchange IT->CH": "it_to_ch_kwh",
    "Transit": "transit_kwh",
}


def interval_starts(year: int, n_rows: int) -> pd.DatetimeIndex:
    """UTC start time of each 15-minute interval of a calendar year."""
    first = pd.Timestamp(f"{year}-01-01 00:00", tz=TZ).tz_convert("UTC")
    starts = pd.date_range(first, periods=n_rows, freq="15min")
    expected_end = pd.Timestamp(f"{year + 1}-01-01 00:00", tz=TZ).tz_convert("UTC")
    if starts[-1] + pd.Timedelta("15min") != expected_end:
        raise ValueError(f"{year}: {n_rows} rows do not cover exactly one calendar year")
    return starts


def check_labels(year: int, labels: pd.Series, starts: pd.DatetimeIndex) -> None:
    """Cross-check Swissgrid's local-time labels against the derived timestamps."""
    # Older files store real Excel dates, newer ones strings like "31.12.2024 23:45"
    parsed = pd.Series([
        pd.Timestamp(v) if not isinstance(v, str) else pd.to_datetime(v, format="%d.%m.%Y %H:%M")
        for v in labels
    ])
    local_start = starts.tz_convert(TZ).tz_localize(None)
    offset = parsed.iloc[0] - local_start[0]  # 0 (start labels) or 15 min (end labels)
    if offset not in (pd.Timedelta(0), pd.Timedelta("15min")):
        raise ValueError(f"{year}: unexpected first label {labels.iloc[0]!r}")
    # Labels around the DST switches are ambiguous, so require ~all others to match.
    match = ((parsed.to_numpy() - offset.to_numpy()) == local_start.to_numpy()).mean()
    if match < 0.999:
        raise ValueError(f"{year}: only {match:.2%} of labels match the derived timestamps")


def read_year(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    year = int(path.stem.split("-")[-1])
    sheet = pd.read_excel(path, sheet_name=SHEET, header=None, engine="calamine")
    headers = [str(h).split("\n")[-1].strip() for h in sheet.iloc[0]]
    data = sheet.iloc[2:].reset_index(drop=True)
    data.columns = headers

    starts = interval_starts(year, len(data))
    check_labels(year, data.iloc[:, 0], starts)
    ts = pd.DataFrame({
        "ts_utc": starts.tz_localize(None),
        "ts_local": starts.tz_convert(TZ).tz_localize(None),
    })

    missing = set(NATIONAL_COLUMNS) - set(headers)
    if missing:
        raise ValueError(f"{year}: missing columns {sorted(missing)}")
    national = pd.concat(
        [ts, data[list(NATIONAL_COLUMNS)].rename(columns=NATIONAL_COLUMNS).astype(float)],
        axis=1,
    )

    # Canton columns come in pairs: "Production Canton(s) X" / "Consumption Canton(s) X"
    canton_frames = []
    for col in headers:
        if col.startswith("Production Canton"):
            region = col.split(" ", 2)[2].strip()  # e.g. "VS" or "GE, VD"
            cons_col = col.replace("Production", "Consumption", 1)
            canton_frames.append(pd.DataFrame({
                "ts_utc": ts["ts_utc"],
                "region": region,
                "production_kwh": data[col].astype(float),
                "consumption_kwh": data[cons_col].astype(float),
            }))
    cantons = pd.concat(canton_frames, ignore_index=True)
    print(f"[ok] {path.name}: {len(national):,} intervals, {cantons['region'].nunique()} canton groups")
    return national, cantons


def main() -> None:
    files = sorted(RAW_DIR.glob("EnergieUebersichtCH-*.xlsx"))
    if not files:
        raise SystemExit("No raw files found. Run `python -m pipeline.download` first.")

    parts = [read_year(f) for f in files]
    national = pd.concat([p[0] for p in parts], ignore_index=True)
    cantons = pd.concat([p[1] for p in parts], ignore_index=True)

    DB_PATH.unlink(missing_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("CREATE TABLE grid_15min AS SELECT * FROM national ORDER BY ts_utc")
    con.execute("CREATE TABLE canton_15min AS SELECT * FROM cantons ORDER BY ts_utc, region")
    con.execute((ROOT / "sql" / "00_views.sql").read_text())
    n = con.execute("SELECT count(*) FROM grid_15min").fetchone()[0]
    con.close()
    print(f"[done] {n:,} rows in grid_15min -> {DB_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
