from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import squarify
from matplotlib.patches import ConnectionPatch


PLOT_DPI = int(os.environ.get("PLOT_DPI", "300"))

COMBINED_ORDER = ["People", "Entertainment", "Events", "Meta", "Places", "Other"]
EVENT_ORDER = [
    "Sporting Events",
    "Other",
    "Crimes",
    "Wars and Conflicts",
    "Political Events",
    "Cultural Events",
    "Natural Disasters",
]

BLUE = "#4281a4" #"#364757"
ORANGE = "#d95b20"
YELLOW = "#c9b220" #"#F9B438" # "#fac23e" #e5aa3e
GREEN = "#054a29"
LIGHT = "#F4EFE4" #"#e5e5e3" #efdfbb
PURPLE = "#3e2f5b"
RED = "#ce3d30" #be290d

COLORS_MAIN = [
    (BLUE,LIGHT),
    (PURPLE,LIGHT),    
    (LIGHT,GREEN),
    (ORANGE,LIGHT),
    (YELLOW,GREEN),
    (GREEN,LIGHT),
]

COLORS_EVENTS = [
    (BLUE,LIGHT),
    (LIGHT,GREEN),
    (PURPLE,LIGHT),    
    (ORANGE,LIGHT),
    (YELLOW,GREEN),
    (GREEN,LIGHT),
    (RED,LIGHT),
]

"""
COLORS_MAIN = [
    "#780000",
    "#dc2f02",
    "#1b4332",
    "#c3891e",
    "#91480d",
    "#003049",
]
COLORS_EVENTS = [
    "#780000",
    "#91480d",
    "#dc2f02",
    "#c3891e",
    "#1b4332",
    "#003049",
    "#5f0f40",
]
"""

def ensure_directories() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)


def ordered_categories(df: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    df = df.copy()
    df["Category"] = pd.Categorical(df["Category"], order, ordered=True)
    return df.sort_values("Category")


def label_for(name: str, views: int, total: int) -> str:
    return f"{name}\n{views / total:.1%}"


def draw_squarify_treemap(
    ax,
    categories: pd.DataFrame,
    colors: list[tuple[str, str]],
    fontsize: int,
    callout_names: set[str] | None = None,
) -> tuple[pd.DataFrame, list[dict]]:
    callout_names = callout_names or set()
    plot_df = categories.sort_values("Views", ascending=False).copy()
    if "Events" in plot_df["Category"].values and "Other" in plot_df["Category"].values:
        pos_events = list(plot_df["Category"]).index("Events")
        pos_other = list(plot_df["Category"]).index("Other")
        idx_order = list(range(len(plot_df)))
        idx_order[pos_events], idx_order[pos_other] = idx_order[pos_other], idx_order[pos_events]
        plot_df = plot_df.iloc[idx_order].copy()

    total = plot_df["Views"].sum()
    labels = [
        "" if name in callout_names else label_for(name, views, total)
        for name, views in zip(plot_df["Category"], plot_df["Views"])
    ]
    rects = squarify.squarify(
        squarify.normalize_sizes(plot_df["Views"].tolist(), 100, 100),
        0,
        0,
        100,
        100,
    )
    for index, (label, rect) in enumerate(zip(labels, rects)):
        color_pair = colors[index % len(colors)]
        bg_color, text_color = color_pair[0], color_pair[1]

        ax.bar(
            rect["x"],
            rect["dy"],
            width=rect["dx"],
            bottom=rect["y"],
            color=bg_color,
            align="edge",
            alpha=0.85,
        )
        if label:
            # Dynamically determine the label's font size based on category name and rect height
            name = label.split("\n")[0]
            if name in ["Meta", "Places"]:
                label_fontsize = min(fontsize, max(12, rect["dy"] * 0.98))
            elif name == "Wars and Conflicts":
                label_fontsize = min(fontsize - 4, max(8, rect["dy"] * 0.65))
            else:
                label_fontsize = min(fontsize, max(8, rect["dy"] * 0.75))

            ax.text(
                rect["x"] + rect["dx"] / 2,
                rect["y"] + rect["dy"] / 2,
                label,
                ha="center",
                va="center",
                fontsize=label_fontsize,
                color=text_color,
                fontweight="bold",
            )

    label_y_max = 100
    for index, (name, views) in enumerate(zip(plot_df["Category"], plot_df["Views"])):
        if name not in callout_names:
            continue
        rect = rects[index]
        pct = views / total
        ax.bar(
            rect["x"],
            rect["dy"],
            width=rect["dx"],
            bottom=rect["y"],
            fill=False,
            edgecolor="white",
            linewidth=3,
            align="edge",
            zorder=5,
        )
        anchor_x = rect["x"] + rect["dx"] / 2
        anchor_y = rect["y"] + rect["dy"]
        text_x = rect["x"] - 6
        text_y = anchor_y + 9
        label_fontsize = max(12, fontsize + 4)
        label_y_max = max(label_y_max, text_y + label_fontsize * 0.35)
        ax.annotate(
            f"{name}, {pct:.1%}",
            xy=(anchor_x, anchor_y),
            xytext=(text_x, text_y),
            xycoords="data",
            textcoords="data",
            ha="right",
            va="bottom",
            fontsize=label_fontsize,
            fontweight="bold",
            color=GREEN,
            arrowprops=dict(
                arrowstyle="-",
                color="#888888",
                lw=1.5,
                shrinkA=2,
                shrinkB=2,
            ),
        )

    ax.set_xlim(0, 100)
    ax.set_ylim(0, label_y_max)
    ax.axis("off")
    return plot_df, rects


def save_figure(fig: plt.Figure, stem: str) -> None:
    for extension in ["png", "pdf"]:
        fig.savefig(
            FIGURE_DIR / f"{stem}.{extension}",
            dpi=PLOT_DPI,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(fig)


def plot_single(categories: pd.DataFrame, stem: str, colors: list[tuple[str, str]], callout_names: set[str] | None = None) -> None:
    fig, ax = plt.subplots(figsize=(10, 6), facecolor="white")
    draw_squarify_treemap(ax, categories, colors, fontsize=20, callout_names=callout_names)
    save_figure(fig, stem)


def plot_combined(combined_categories: pd.DataFrame, event_categories: pd.DataFrame) -> None:
    fig = plt.figure(figsize=(16, 9), facecolor="white")
    ax_main = fig.add_axes([0.05, 0.06, 0.50, 0.58])
    ax_inset = fig.add_axes([0.62, 0.48, 0.36, 0.46])

    plot_df, rects = draw_squarify_treemap(ax_main, combined_categories, COLORS_MAIN, fontsize=22)
    draw_squarify_treemap(
        ax_inset,
        event_categories,
        COLORS_EVENTS,
        fontsize=18,
        callout_names={"Natural Disasters"},
    )

    events_idx = list(plot_df["Category"]).index("Events")
    rect_events = rects[events_idx]
    ex = rect_events["x"]
    ey = rect_events["y"]
    ew = rect_events["dx"]
    eh = rect_events["dy"]

    ax_main.bar(
        ex,
        eh,
        width=ew,
        bottom=ey,
        fill=False,
        edgecolor="white",
        linewidth=3,
        align="edge",
        zorder=5,
    )

    connector_style = dict(
        arrowstyle="-",
        mutation_scale=14,
        lw=4.0,
        color="#888888",
        alpha=0.9,
        connectionstyle="arc3,rad=0.08",
    )
    for source, target in zip(
        [(ex + ew, ey + eh), (ex + ew, ey)],
        [(0.0, 100.0), (0.0, 0.0)],
    ):
        fig.add_artist(
            ConnectionPatch(
                xyA=source,
                coordsA=ax_main.transData,
                xyB=target,
                coordsB=ax_inset.transData,
                **connector_style,
            )
        )

    save_figure(fig, "combined_categories")


def main() -> None:
    ensure_directories()

    category_dist_path = TABLE_DIR / "category_distribution.csv"
    event_category_dist_path = TABLE_DIR / "event_category_distribution.csv"

    if not category_dist_path.exists():
        raise FileNotFoundError(f"Missing input table: {category_dist_path}")
    if not event_category_dist_path.exists():
        raise FileNotFoundError(f"Missing input table: {event_category_dist_path}")

    combined_df = pd.read_csv(category_dist_path)
    event_df = pd.read_csv(event_category_dist_path)

    # Filter out "Uncategorised" and "Total Categorised"
    combined_df = combined_df[~combined_df["Category"].isin(["Uncategorised", "Total Categorised"])].copy()
    event_df = event_df[~event_df["Category"].isin(["Uncategorised", "Total Categorised"])].copy()

    combined_df["Views"] = pd.to_numeric(combined_df["Views"])
    event_df["Views"] = pd.to_numeric(event_df["Views"])

    # Reorder according to preferred category orders
    combined_categories = ordered_categories(combined_df, COMBINED_ORDER)
    event_categories = ordered_categories(event_df, EVENT_ORDER)

    plot_single(combined_categories, "non_event_categories", COLORS_MAIN)
    plot_single(
        event_categories,
        "event_categories",
        COLORS_EVENTS,
        callout_names={"Natural Disasters"},
    )
    plot_combined(combined_categories, event_categories)

    print(f"Wrote figures to {FIGURE_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
