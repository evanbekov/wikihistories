#!/usr/bin/env python3
"""Build the daily Australian clickstream-impact panel for Climate change.

Combines the monthly clicks in ``data/clicks`` with the raw daily country
pageviews in ``data/raw/pageviews`` into the single
``data/processed/climate_au_daily.csv`` that the figures read. Run once; the
plotting step then consumes only the CSV.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from wikihistories.clickstream_impact import (
    CLICKS_DIR,
    PANEL_CSV,
    RAW_PAGEVIEWS_DIR,
    build_panel,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clicks-dir", type=Path, default=CLICKS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_PAGEVIEWS_DIR)
    parser.add_argument("--out", type=Path, default=PANEL_CSV)
    args = parser.parse_args()

    panel = build_panel(args.clicks_dir, args.raw_dir, args.out)
    months = panel["date"].str[:7].nunique() if not panel.empty else 0
    print(
        f"Wrote {len(panel):,} rows across {months} months "
        f"({panel['date'].min()} to {panel['date'].max()}) -> {args.out}"
    )


if __name__ == "__main__":
    main()
