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

### 1. Extract and Build Pageviews

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

### 2. Categorise Pages

To apply the categorisation rules and map each unique page to its respective category:

First, aggregate unique pages across all daily files to get their views and QIDs:

```bash
.venv/bin/python scripts/aggregate_pages.py
```

Build the subclass hierarchy graph from `data/categorisation/p279.csv`:

```bash
.venv/bin/python scripts/categorisation/build_p279_graph.py
```

Initialise page-class assignments using `data/categorisation/p31.csv` and the built graph:

```bash
.venv/bin/python scripts/categorisation/init_assignments.py
```

Apply the categorisation rules from `data/categorisation/rules.csv`:

```bash
.venv/bin/python scripts/categorisation/apply_rules.py
```

Produce the intermediate categorised pages CSV file:

```bash
.venv/bin/python scripts/categorisation/produce_final_csv.py
```

Apply aggregation and label rules to simplify categories and produce the final category distribution table:

```bash
.venv/bin/python scripts/categorisation/aggregate.py
```

### 3. Sub-categorise Event Pages

To apply the event-specific sub-categorisation rules to pages categorised as `Events` at the first step, run:

Initialise assignments specifically for Event pages:

```bash
.venv/bin/python scripts/categorisation/init_assignments.py --filter-category Events
```

Apply the sub-categorisation rules:

```bash
.venv/bin/python scripts/categorisation/apply_rules.py --filter-category Events
```

Produce the intermediate categorised event pages CSV file:

```bash
.venv/bin/python scripts/categorisation/produce_final_csv.py --filter-category Events
```

Apply event-specific aggregation and label rules to simplify event sub-categories and produce the event category distribution table:

```bash
.venv/bin/python scripts/categorisation/aggregate.py --filter-category Events
```

### 4. Adjust Non-Events

To finalise the distributions by removing "Non-Events" sub-categories from the event table and moving their counts and views to their appropriate main categories in the main category distribution table, run:

```bash
.venv/bin/python scripts/categorisation/adjust_non_events.py
```

### 5. Build Category Plots

To generate the category distribution treemap plots (standalone non-event categories, event categories, and combined category plots) from the final tables, run:

```bash
.venv/bin/python scripts/categorisation/build_plots.py
```

### 6. Plot Event Timelines

Each event category is defined by a page list in
`data/poi/{bushfires,cyclones,earthquakes,climate}.csv`, giving each page's
`page_id` and display `name`. Build the per-event daily-view CSVs by scanning
the Australia-only pageview TSVs and summing the views of the listed page IDs.
Matching on the page ID captures a page's full history even across renames:

```bash
.venv/bin/python scripts/build_event_views.py
```

Then generate the per-event pageview timeline figures (bushfire, cyclone and
earthquake small-multiple grids, plus the standalone climate-change timeline):

```bash
.venv/bin/python scripts/plot_event_timelines.py
```

## Outputs

- `data/interim/australia/pageviews/`: Australia-only daily pageview TSVs.
- `data/processed/australia_daily_views.csv`: daily total views.
- `data/processed/australia_daily_views_manifest.json`: dataset build metadata.
- `data/processed/project_stats.json`: project-specific page and view statistics.
- `data/processed/views.csv`: aggregated unique pages with views and QIDs.
- `data/interim/class_graph.pkl`: precomputed subclass hierarchy graph.
- `data/interim/assignments.csv`: intermediate state of page-category assignments.
- `outputs/figures/australia_daily_views.png`: rendered figure.
- `outputs/figures/non_event_categories.png` / `outputs/figures/non_event_categories.pdf`: standalone non-event categories treemap.
- `outputs/figures/event_categories.png` / `outputs/figures/event_categories.pdf`: standalone event categories treemap.
- `outputs/figures/combined_categories.png` / `outputs/figures/combined_categories.pdf`: combined category distribution treemap with connection lines.
- `data/interim/categorised_pages.csv`: intermediate categorised pages mapping.
- `data/interim/categorised_pages_labelled.csv`: final categorised pages with aggregation and label rules applied.
- `data/interim/assignments_events.csv`: intermediate state of event page assignments.
- `data/interim/categorised_event_pages.csv`: intermediate categorised event pages mapping.
- `data/interim/categorised_event_pages_labelled.csv`: final categorised event pages with event-specific aggregation and label rules applied.
- `outputs/tables/category_distribution.csv`: final category distribution table (CSV format).
- `outputs/tables/event_category_distribution.csv`: final event category distribution table (CSV format).
- `data/poi/{bushfires,cyclones,earthquakes,climate}.csv`: page lists (`page_id`, `name`) that define each event category.
- `data/processed/event_views/{bushfires,cyclones,earthquakes,climate}.csv`: daily views for the selected event pages, built from the Australia TSVs by matching page IDs.
- `outputs/figures/bushfire.png` / `.pdf`: bushfire event pageview timelines (small-multiple grid).
- `outputs/figures/cyclone.png` / `.pdf`: cyclone event pageview timelines (small-multiple grid).
- `outputs/figures/earthquake.png` / `.pdf`: earthquake event pageview timelines (small-multiple grid).
- `outputs/figures/climate.png` / `.pdf`: standalone climate-change pageview timeline.
