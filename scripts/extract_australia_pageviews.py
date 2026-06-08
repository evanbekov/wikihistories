#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from wikihistories.australia_daily_views import (
    AUSTRALIA_PAGEVIEWS_DIR,
    END_DATE,
    RAW_PAGEVIEWS_DIR,
    START_DATE,
    iter_dates,
)

def extract_day(source: Path, destination: Path, force: bool = False) -> tuple[int, bool]:
    if destination.exists() and not force:
        return 0, False

    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    rows = 0

    with source.open("r", encoding="utf-8") as infile, tmp.open(
        "w", encoding="utf-8"
    ) as outfile:
        for line in infile:
            if line.startswith("Australia\tAU\t"):
                outfile.write(line)
                rows += 1

    os.replace(tmp, destination)
    return rows, True

def extract_all(source_dir: Path, destination_dir: Path, force: bool = False) -> None:
    missing: list[str] = []
    extracted = 0
    skipped = 0
    rows = 0

    for index, day in enumerate(iter_dates(), start=1):
        name = f"{day.isoformat()}.tsv"
        source = source_dir / name
        destination = destination_dir / name

        if not source.exists():
            missing.append(day.isoformat())
            continue

        day_rows, did_extract = extract_day(source, destination, force=force)
        if did_extract:
            extracted += 1
            rows += day_rows
        else:
            skipped += 1

        if index == 1 or index % 50 == 0:
            print(
                f"{day.isoformat()}: extracted={extracted} "
                f"skipped={skipped} missing={len(missing)} rows={rows}",
                flush=True,
            )

    print(f"Date range: {START_DATE.isoformat()} to {END_DATE.isoformat()}")
    print(f"Extracted {extracted} files to {destination_dir}")
    print(f"Skipped {skipped} existing files")
    print(f"Wrote {rows:,} Australia rows")
    print(f"Missing {len(missing)} source files")
    if missing:
        print("Missing dates: " + ", ".join(missing))

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract Australia rows from raw Wikimedia pageview TSVs."
    )
    parser.add_argument("--source", type=Path, default=RAW_PAGEVIEWS_DIR)
    parser.add_argument("--destination", type=Path, default=AUSTRALIA_PAGEVIEWS_DIR)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    extract_all(args.source, args.destination, force=args.force)

if __name__ == "__main__":
    main()
