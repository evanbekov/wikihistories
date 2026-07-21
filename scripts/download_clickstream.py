#!/usr/bin/env python3
"""Download monthly Wikipedia clickstream dumps and filter them to climate pages.

Fetches each ``clickstream-enwiki-YYYY-MM.tsv.gz`` from dumps.wikimedia.org,
keeps only the rows whose destination page relates to climate change, and
writes ``data/clicks/YYYY-MM.csv``. This is the raw entry point of the
clickstream pipeline; run it before building the panel.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from wikihistories.clickstream_impact import (
    CLICKS_DIR,
    FIRST_MONTH,
    LAST_MONTH,
    RAW_CLICKSTREAM_DIR,
    download_clicks,
    month_range,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=FIRST_MONTH, help="first month (YYYY-MM)")
    parser.add_argument("--end", default=LAST_MONTH, help="last month (YYYY-MM)")
    parser.add_argument("--clicks-dir", type=Path, default=CLICKS_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_CLICKSTREAM_DIR)
    parser.add_argument(
        "--keep-archives",
        action="store_true",
        help="keep the downloaded .tsv.gz dumps instead of deleting them",
    )
    args = parser.parse_args()

    written = download_clicks(
        month_range(args.start, args.end),
        clicks_dir=args.clicks_dir,
        raw_dir=args.raw_dir,
        keep_archive=args.keep_archives,
    )
    print(f"Clicks available for {len(written)} months in {args.clicks_dir}")


if __name__ == "__main__":
    main()
