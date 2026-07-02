# Reproducing The Australia Pageviews Result

## Setup

Create an environment and install the project:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

Download the daily Wikimedia country-project-page TSV files from the
[historical release](https://analytics.wikimedia.org/published/datasets/country_project_page_historical/)
and the
[current release](https://analytics.wikimedia.org/published/datasets/country_project_page/).
Place the files for 2017-02-09 through 2026-02-28 in:

```text
data/raw/pageviews/
```

## Run

Extract the Australia-only pageview files:

```bash
.venv/bin/python scripts/extract_australia_pageviews.py
```

Build the daily totals:

```bash
.venv/bin/python scripts/build_australia_daily_views.py
```

Compute project-specific statistics:

```bash
.venv/bin/python scripts/compute_project_stats.py
```

Create the figure:

```bash
.venv/bin/python scripts/plot_australia_daily_views.py
```

## Outputs

- `data/interim/australia/pageviews/`: Australia-only daily pageview TSVs.
- `data/processed/australia_daily_views.csv`: daily total views.
- `data/processed/australia_daily_views_manifest.json`: dataset build metadata.
- `data/processed/project_stats.json`: project-specific page and view statistics.
- `outputs/figures/australia_daily_views.png`: rendered figure.
