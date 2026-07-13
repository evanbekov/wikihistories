#!/usr/bin/env python3
"""Compute top 10 most viewed English Wikipedia pages over given date ranges.

Produces one CSV per query in outputs/tables with columns
Rank, Article title, Average daily views, and one daily views-vs-date figure
per query in outputs/figures.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from wikihistories.top_pages import TopPagesSpec, TABLES_DIR, write_top_pages

SPECS = [
    TopPagesSpec(
        country_code="AU",
        start_date=date(2025, 3, 4),
        end_date=date(2025, 3, 9),
        output_csv=TABLES_DIR / "top_pages_australia_2025-03-04_2025-03-09.csv",
        title="Top 10 pages by daily views — Australia, 4–9 Mar 2025",
        figure_stem="top_pages_cyclone",
        highlight_titles=("Cyclone Tracy", "Cyclone Yasi", "Cyclone Alfred (2025)"),
        highlight_cmap="Blues",
        legend_loc="upper center",
    ),
    TopPagesSpec(
        country_code="AU",
        start_date=date(2019, 12, 30),
        end_date=date(2020, 1, 9),
        output_csv=TABLES_DIR / "top_pages_australia_2019-12-30_2020-01-09.csv",
        title="Top 10 pages by daily views — Australia, 30 Dec 2019 – 9 Jan 2020",
        figure_stem="top_pages_bushfire",
        highlight_titles=("Black Saturday bushfires", "Bushfire", "Australia fire"),
        highlight_cmap="Reds",
        legend_loc="upper right",
    ),
    TopPagesSpec(
        country_code="GB",
        start_date=date(2025, 3, 4),
        end_date=date(2025, 3, 9),
        output_csv=TABLES_DIR / "top_pages_uk_2025-03-04_2025-03-09.csv",
        title="Top 10 pages by daily views — UK, 4–9 Mar 2025",
        figure_stem="top_pages_uk",
        legend_loc="upper center",
        legend_bbox=(0.52, 1.0),
    ),
]


def main() -> None:
    for spec in SPECS:
        table = write_top_pages(spec, make_plot=True)
        print(
            f"{spec.country_code} {spec.start_date.isoformat()}..{spec.end_date.isoformat()} "
            f"-> {spec.output_csv}"
        )
        print(table.to_string(index=False))
        print()


if __name__ == "__main__":
    main()
