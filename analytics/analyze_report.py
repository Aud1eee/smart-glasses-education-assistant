import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def analyze(
    input_path=None,
    heatmap_path=None,
    legacy_output_path=None,
    events_path=None,
    title_prefix="Attention Heatmap Review",
):
    root = Path(__file__).resolve().parents[1]
    input_path = Path(input_path) if input_path else root / "data" / "study_report.csv"
    heatmap_path = Path(heatmap_path) if heatmap_path else root / "exports" / "attention_heatmap.png"
    legacy_output_path = Path(legacy_output_path) if legacy_output_path else root / "exports" / "study_analysis.png"
    events_path = Path(events_path) if events_path else None

    if not input_path.exists() or input_path.stat().st_size < 50:
        print(">>> Not enough learning-state data to analyze.")
        return

    df = pd.read_csv(input_path)
    df = df[df["Relative_Pitch"] != "Relative_Pitch"].copy()
    if df.empty:
        print(">>> No valid learning-state rows found.")
        return

    df["Relative_Pitch"] = pd.to_numeric(df["Relative_Pitch"], errors="coerce").fillna(0)
    df["Focus_Score"] = pd.to_numeric(df["Focus_Score"], errors="coerce").fillna(0)

    if "Cognitive_Load" not in df.columns:
        df["Cognitive_Load"] = np.nan
    df["Cognitive_Load"] = pd.to_numeric(df["Cognitive_Load"], errors="coerce")
    df["Cognitive_Load"] = df["Cognitive_Load"].fillna(100 - df["Focus_Score"]).clip(0, 100)

    if "Stability" not in df.columns:
        df["Stability"] = np.nan
    df["Stability"] = pd.to_numeric(df["Stability"], errors="coerce").fillna(100 - df["Relative_Pitch"]).clip(0, 100)

    alert = df["Is_Alert"].astype(str).str.lower().eq("true")
    high_load = (df["Cognitive_Load"] >= 70) | alert
    medium_load = (df["Cognitive_Load"] >= 45) & ~high_load

    avg_focus = df["Focus_Score"].mean()
    avg_load = df["Cognitive_Load"].mean()
    high_load_ratio = high_load.mean() * 100
    events_df = _load_events(events_path)
    event_count = 0 if events_df is None else len(events_df)

    print("\nLearning State Review")
    print(f"- Samples: {len(df)}")
    print(f"- Average focus score: {avg_focus:.1f}/100")
    print(f"- Average cognitive load: {avg_load:.1f}/100")
    print(f"- High-load ratio: {high_load_ratio:.1f}%")
    if event_count:
        print(f"- Difficulty events: {event_count}")

    x = np.arange(len(df))
    heat = np.tile(df["Cognitive_Load"].to_numpy(), (18, 1))

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(13, 7), constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[1.4, 0.55, 1], hspace=0.28)

    ax1 = fig.add_subplot(gs[0])
    ax1.plot(x, df["Focus_Score"], color="#00ff9d", linewidth=1.8, label="Focus score")
    ax1.plot(x, 100 - df["Cognitive_Load"], color="#ffcc00", linewidth=1.2, alpha=0.8, label="Load comfort")
    ax1.fill_between(x, 0, df["Focus_Score"], color="#00ff9d", alpha=0.12)
    for start, end in _segments(high_load):
        ax1.axvspan(start, end, color="#ff3158", alpha=0.18)
    _draw_event_overlays(ax1, events_df)
    ax1.set_ylim(0, 105)
    ax1.set_ylabel("Score")
    ax1.set_title(
        f"{title_prefix} | Focus {avg_focus:.1f} | Load {avg_load:.1f} | High-load {high_load_ratio:.1f}% | Events {event_count}"
    )
    ax1.legend(loc="upper right")
    ax1.grid(axis="y", linestyle="--", alpha=0.18)

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.imshow(heat, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)
    ax2.set_yticks([])
    ax2.set_ylabel("Load")
    ax2.set_title("Cognitive Load Heatmap", loc="left", fontsize=10, color="#d8fff0")

    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(x, df["Relative_Pitch"], color="#8fd3ff", linewidth=1.4, label="Pitch delta")
    ax3.plot(x, df["Stability"], color="#d8fff0", linewidth=1.2, alpha=0.75, label="Stability")
    ax3.scatter(x[medium_load], df.loc[medium_load, "Relative_Pitch"], color="#ffcc00", s=12, label="Medium load")
    ax3.scatter(x[high_load], df.loc[high_load, "Relative_Pitch"], color="#ff3158", s=16, label="High load")
    _draw_event_overlays(ax3, events_df, show_labels=False)
    ax3.set_ylabel("Motion")
    ax3.set_xlabel("Timeline samples")
    ax3.legend(loc="upper right")
    ax3.grid(axis="y", linestyle="--", alpha=0.18)

    heatmap_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(heatmap_path, dpi=150)
    if legacy_output_path:
        fig.savefig(legacy_output_path, dpi=150)
    plt.close(fig)
    print(f">>> Saved attention heatmap to {heatmap_path}")
    return {
        "samples": len(df),
        "avg_focus": round(avg_focus, 1),
        "avg_load": round(avg_load, 1),
        "high_load_ratio": round(high_load_ratio, 1),
        "difficulty_event_count": event_count,
    }


def _segments(mask):
    starts = []
    start = None
    values = list(mask)
    for idx, active in enumerate(values):
        if active and start is None:
            start = idx
        if start is not None and (not active or idx == len(values) - 1):
            end = idx if active and idx == len(values) - 1 else idx - 1
            starts.append((start, end))
            start = None
    return starts


def _load_events(events_path):
    if not events_path or not events_path.exists() or events_path.stat().st_size < 20:
        return None

    events_df = pd.read_csv(events_path)
    if events_df.empty:
        return None

    for column in ["Start_Sample", "End_Sample", "Event_ID"]:
        if column in events_df.columns:
            events_df[column] = pd.to_numeric(events_df[column], errors="coerce").fillna(0).astype(int)
    return events_df


def _draw_event_overlays(axis, events_df, show_labels=True):
    if events_df is None:
        return

    for _, event in events_df.iterrows():
        start = max(0, int(event.get("Start_Sample", 0)) - 1)
        end = max(start, int(event.get("End_Sample", 0)) - 1)
        severity = str(event.get("Severity", "medium")).lower()
        color = "#66d6ff" if severity == "medium" else "#7c8dff"
        axis.axvspan(start, end, color=color, alpha=0.08)
        if show_labels:
            axis.text(
                (start + end) / 2,
                101,
                f"D{int(event.get('Event_ID', 0))}",
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
            )


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a learning-state heatmap from a CSV report.")
    parser.add_argument("--input", default=None, help="Path to the CSV report file.")
    parser.add_argument("--heatmap-output", default=None, help="Path for the main heatmap PNG.")
    parser.add_argument("--legacy-output", default=None, help="Optional secondary PNG output path.")
    parser.add_argument("--events-input", default=None, help="Optional difficulty-events CSV path.")
    parser.add_argument("--title-prefix", default="Attention Heatmap Review", help="Chart title prefix.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analyze(
        input_path=args.input,
        heatmap_path=args.heatmap_output,
        legacy_output_path=args.legacy_output,
        events_path=args.events_input,
        title_prefix=args.title_prefix,
    )
