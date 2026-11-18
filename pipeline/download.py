"""Download Swissgrid's yearly "Energy Overview Switzerland" files.

Source: https://www.swissgrid.ch/en/home/operation/grid-data/generation.html
One Excel file per year with 15-minute time series for the Swiss control block.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import requests

URL = "https://www.swissgrid.ch/dam/dataimport/energy-statistic/EnergieUebersichtCH-{year}.xlsx"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
DEFAULT_YEARS = range(2020, 2026)


def download(year: int, force: bool = False) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    target = RAW_DIR / f"EnergieUebersichtCH-{year}.xlsx"
    if target.exists() and not force:
        print(f"[skip] {target.name} already downloaded")
        return target

    resp = requests.get(URL.format(year=year), timeout=120)
    resp.raise_for_status()
    # .xlsx files are zip archives: a missing year returns an HTML page instead.
    if not resp.content.startswith(b"PK"):
        raise ValueError(f"{year}: response is not an .xlsx file")
    target.write_bytes(resp.content)
    print(f"[ok]   {target.name} ({len(resp.content) / 1e6:.1f} MB)")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("years", nargs="*", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()
    for year in args.years:
        download(year, force=args.force)


if __name__ == "__main__":
    main()
