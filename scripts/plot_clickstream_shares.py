#!/usr/bin/env python3
"""Plot the daily Australian click-share small multiples for Climate change.

Reads data/processed/climate_au_daily.csv and writes the figure
outputs/figures/clickstream_climate_shares.{png,pdf}, the ranked source table
outputs/tables/clickstream_top_sources.csv, the top-3 shares into report.json,
and re-renders README.md from the template.
"""
from __future__ import annotations

from wikihistories.clickstream_shares import RANKING_CSV, build_all
from wikihistories.project_summary import render_readme


def main() -> None:
    figure = build_all()
    readme = render_readme()
    print(f"Wrote {figure}")
    print(f"Wrote {RANKING_CSV}")
    print(f"Updated report.json and {readme}")


if __name__ == "__main__":
    main()
