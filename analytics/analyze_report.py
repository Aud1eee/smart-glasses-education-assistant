import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


TASK_MODE_COLORS = {
    "lecture": "#1e90ff",
    "reading": "#00b894",
    "note-taking": "#ff9f1c",
    "review": "#8e7dff",
}


def analyze(
    input_path=None,
    heatmap_path=None,
    legacy_output_path=None,
    events_path=None,
    title_prefix="Learning State Review",
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

    df = _normalize_schema(df)

    alert = df["Is_Alert"].astype(str).str.lower().eq("true")
    high_load = (df["Cognitive_Load"] >= 70) | alert
    medium_load = (df["Cognitive_Load"] >= 45) & ~high_load
    fatigue_high = df["Fatigue_Risk"] >= 60
    low_confidence = (df["Uncertainty_Score"] >= 55) | df["Confidence_Level"].isin(["low", "warming_up"])
    drift_risk = (
        (df["Behavioral_Alignment"] < 72)
        | df["Behavioral_Level"].isin(["drifting", "misaligned"])
    )

    avg_alignment = df["Behavioral_Alignment"].mean()
    avg_focus = df["Focus_Score"].mean()
    avg_load = df["Cognitive_Load"].mean()
    avg_fatigue = df["Fatigue_Risk"].mean()
    high_load_ratio = high_load.mean() * 100
    low_conf_ratio = low_confidence.mean() * 100
    drift_ratio = drift_risk.mean() * 100
    session_offsets = _build_session_offsets(df)
    events_df = _load_events(events_path, session_offsets)
    event_count = 0 if events_df is None else len(events_df)
    task_modes = " / ".join(dict.fromkeys(df["Task_Mode"].tolist()))

    print("\nLearning State Review")
    print(f"- Samples: {len(df)}")
    print(f"- Average behavioral alignment: {avg_alignment:.1f}/100")
    print(f"- Average focus proxy: {avg_focus:.1f}/100")
    print(f"- Average cognitive load: {avg_load:.1f}/100")
    print(f"- Average fatigue risk: {avg_fatigue:.1f}/100")
    print(f"- Drift-risk ratio: {drift_ratio:.1f}%")
    print(f"- High-load ratio: {high_load_ratio:.1f}%")
    print(f"- Low-confidence ratio: {low_conf_ratio:.1f}%")
    print(f"- Task modes present: {task_modes}")
    if event_count:
        print(f"- Difficulty events: {event_count}")

    x = np.arange(len(df))
    risk_matrix = np.vstack([
        100 - df["Behavioral_Alignment"].to_numpy(),
        df["Cognitive_Load"].to_numpy(),
        df["Fatigue_Risk"].to_numpy(),
    ])

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    gs = fig.add_gridspec(4, 1, height_ratios=[1.45, 0.72, 0.95, 1.05], hspace=0.26)

    ax1 = fig.add_subplot(gs[0])
    ax1.plot(x, df["Behavioral_Alignment"], color="#00ff9d", linewidth=1.9, label="Behavioral alignment")
    ax1.plot(x, 100 - df["Cognitive_Load"], color="#ffcc00", linewidth=1.3, alpha=0.95, label="Load comfort")
    ax1.plot(x, 100 - df["Fatigue_Risk"], color="#53b3ff", linewidth=1.15, alpha=0.9, label="Fatigue comfort")
    ax1.fill_between(x, 0, df["Behavioral_Alignment"], color="#00ff9d", alpha=0.10)
    _shade_segments(ax1, high_load, color="#ff3158", alpha=0.14)
    _shade_segments(ax1, low_confidence, color="#8a8f9d", alpha=0.12)
    _draw_event_overlays(ax1, events_df)
    ax1.set_ylim(0, 105)
    ax1.set_ylabel("Score")
    ax1.set_title(
        f"{title_prefix} | Align {avg_alignment:.1f} | Load {avg_load:.1f} | "
        f"Fatigue {avg_fatigue:.1f} | Low-conf {low_conf_ratio:.1f}% | Events {event_count}"
    )
    ax1.legend(loc="upper right")
    ax1.grid(axis="y", linestyle="--", alpha=0.18)

    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.imshow(risk_matrix, aspect="auto", cmap="RdYlGn_r", vmin=0, vmax=100)
    ax2.set_yticks([0, 1, 2])
    ax2.set_yticklabels(["Align risk", "Load", "Fatigue"])
    ax2.set_title("Risk Heat Bands", loc="left", fontsize=10, color="#d8fff0")
    _shade_segments(ax2, low_confidence, color="#8a8f9d", alpha=0.10)

    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.plot(x, df["Uncertainty_Score"], color="#d28cff", linewidth=1.45, label="Uncertainty score")
    ax3.plot(x, df["Stability"], color="#d8fff0", linewidth=1.15, alpha=0.82, label="Stability")
    _shade_segments(ax3, low_confidence, color="#8a8f9d", alpha=0.12)
    _draw_mode_spans(ax3, df["Task_Mode"].tolist())
    ax3.set_ylim(0, 105)
    ax3.set_ylabel("Signal")
    ax3.set_title("Confidence and Task Mode Context", loc="left", fontsize=10, color="#d8fff0")
    ax3.legend(loc="upper right")
    ax3.grid(axis="y", linestyle="--", alpha=0.16)

    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    ax4.plot(x, df["Relative_Pitch"], color="#8fd3ff", linewidth=1.35, label="Pitch delta")
    ax4.plot(x, df["Stability"], color="#8ef6d4", linewidth=1.0, alpha=0.55, label="Stability")
    ax4.scatter(x[medium_load], df.loc[medium_load, "Relative_Pitch"], color="#ffcc00", s=12, label="Medium load")
    ax4.scatter(x[high_load], df.loc[high_load, "Relative_Pitch"], color="#ff3158", s=16, label="High load")
    ax4.scatter(x[fatigue_high], df.loc[fatigue_high, "Relative_Pitch"], color="#53b3ff", s=20, marker="x", label="Fatigue risk")
    _draw_event_overlays(ax4, events_df, show_labels=False)
    ax4.set_ylabel("Motion")
    ax4.set_xlabel("Timeline samples")
    ax4.legend(loc="upper right")
    ax4.grid(axis="y", linestyle="--", alpha=0.18)

    heatmap_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(heatmap_path, dpi=150)
    if legacy_output_path:
        fig.savefig(legacy_output_path, dpi=150)
    plt.close(fig)
    print(f">>> Saved attention heatmap to {heatmap_path}")
    return {
        "samples": len(df),
        "avg_alignment": round(avg_alignment, 1),
        "avg_focus": round(avg_focus, 1),
        "avg_load": round(avg_load, 1),
        "avg_fatigue": round(avg_fatigue, 1),
        "drift_ratio": round(drift_ratio, 1),
        "high_load_ratio": round(high_load_ratio, 1),
        "low_conf_ratio": round(low_conf_ratio, 1),
        "difficulty_event_count": event_count,
    }


def _normalize_schema(df):
    if "Session_ID" not in df.columns:
        df["Session_ID"] = "legacy-session-1"
    df["Session_ID"] = df["Session_ID"].fillna("").replace("", "legacy-session-1")

    defaults = {
        "Focus_Score": 0,
        "Cognitive_Load": np.nan,
        "Stability": np.nan,
        "Task_Mode": "reading",
        "Behavioral_Alignment": np.nan,
        "Behavioral_Level": "aligned",
        "Fatigue_Risk": 0,
        "Fatigue_Level": "low",
        "Uncertainty_Score": 35,
        "Confidence_Level": "medium",
    }

    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default

    df["Relative_Pitch"] = pd.to_numeric(df["Relative_Pitch"], errors="coerce").fillna(0)
    df["Focus_Score"] = pd.to_numeric(df["Focus_Score"], errors="coerce").fillna(0)
    df["Cognitive_Load"] = pd.to_numeric(df["Cognitive_Load"], errors="coerce")
    df["Cognitive_Load"] = df["Cognitive_Load"].fillna(100 - df["Focus_Score"]).clip(0, 100)
    df["Stability"] = pd.to_numeric(df["Stability"], errors="coerce").fillna(100 - df["Relative_Pitch"]).clip(0, 100)
    df["Behavioral_Alignment"] = pd.to_numeric(df["Behavioral_Alignment"], errors="coerce")
    df["Behavioral_Alignment"] = df["Behavioral_Alignment"].fillna(df["Focus_Score"]).clip(0, 100)
    df["Fatigue_Risk"] = pd.to_numeric(df["Fatigue_Risk"], errors="coerce").fillna(0).clip(0, 100)
    df["Uncertainty_Score"] = pd.to_numeric(df["Uncertainty_Score"], errors="coerce").fillna(35).clip(0, 100)
    df["Task_Mode"] = df["Task_Mode"].fillna("reading").astype(str).str.strip().str.lower()
    df["Behavioral_Level"] = df["Behavioral_Level"].fillna("aligned").astype(str).str.strip().str.lower()
    df["Confidence_Level"] = df["Confidence_Level"].fillna("medium").astype(str).str.strip().str.lower()
    return df


def _shade_segments(axis, mask, color, alpha):
    for start, end in _segments(mask):
        axis.axvspan(start, end, color=color, alpha=alpha)


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


def _load_events(events_path, session_offsets):
    if not events_path or not events_path.exists() or events_path.stat().st_size < 20:
        return None

    events_df = pd.read_csv(events_path)
    if events_df.empty:
        return None

    if "Session_ID" not in events_df.columns:
        events_df["Session_ID"] = "legacy-session-1"
    events_df["Session_ID"] = events_df["Session_ID"].fillna("").replace("", "legacy-session-1")

    for column in ["Start_Sample", "End_Sample", "Event_ID"]:
        if column in events_df.columns:
            events_df[column] = pd.to_numeric(events_df[column], errors="coerce").fillna(0).astype(int)
    events_df["_absolute_start"] = events_df.apply(
        lambda row: max(0, session_offsets.get(row["Session_ID"], 0) + int(row.get("Start_Sample", 0)) - 1),
        axis=1,
    )
    events_df["_absolute_end"] = events_df.apply(
        lambda row: max(
            int(row["_absolute_start"]),
            session_offsets.get(row["Session_ID"], 0) + int(row.get("End_Sample", 0)) - 1,
        ),
        axis=1,
    )
    return events_df


def _build_session_offsets(df):
    offsets = {}
    start = 0
    for session_id, session_rows in df.groupby("Session_ID", sort=False):
        offsets[session_id] = start
        start += len(session_rows)
    return offsets


def _draw_event_overlays(axis, events_df, show_labels=True):
    if events_df is None:
        return

    top_y = axis.get_ylim()[1] - ((axis.get_ylim()[1] - axis.get_ylim()[0]) * 0.04)
    for _, event in events_df.iterrows():
        start = int(event.get("_absolute_start", 0))
        end = int(event.get("_absolute_end", start))
        severity = str(event.get("Severity", "medium")).lower()
        color = "#66d6ff" if severity == "medium" else "#7c8dff"
        axis.axvspan(start, end, color=color, alpha=0.08)
        if show_labels:
            axis.text(
                (start + end) / 2,
                top_y,
                f"D{int(event.get('Event_ID', 0))}",
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
            )


def _draw_mode_spans(axis, modes):
    start = 0
    current = modes[0] if modes else "reading"
    segments = []
    for idx, mode in enumerate(modes):
        if mode != current:
            segments.append((start, idx - 1, current))
            start = idx
            current = mode
    if modes:
        segments.append((start, len(modes) - 1, current))

    y_top = axis.get_ylim()[1] - 5
    for start, end, mode in segments:
        color = TASK_MODE_COLORS.get(mode, "#4f6bed")
        axis.axvspan(start, end, color=color, alpha=0.06)
        axis.text(
            (start + end) / 2,
            y_top,
            mode,
            color=color,
            fontsize=8,
            ha="center",
            va="top",
        )


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a learning-state heatmap from a CSV report.")
    parser.add_argument("--input", default=None, help="Path to the CSV report file.")
    parser.add_argument("--heatmap-output", default=None, help="Path for the main heatmap PNG.")
    parser.add_argument("--legacy-output", default=None, help="Optional secondary PNG output path.")
    parser.add_argument("--events-input", default=None, help="Optional difficulty-events CSV path.")
    parser.add_argument("--title-prefix", default="Learning State Review", help="Chart title prefix.")
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
