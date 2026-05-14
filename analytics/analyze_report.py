import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def analyze():
    path = "../data/study_report.csv"
    if not os.path.exists(path) or os.stat(path).st_size < 50:
        print(">>> Not enough learning-state data to analyze.")
        return

    df = pd.read_csv(path)
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

    print("\nLearning State Review")
    print(f"- Samples: {len(df)}")
    print(f"- Average focus score: {avg_focus:.1f}/100")
    print(f"- Average cognitive load: {avg_load:.1f}/100")
    print(f"- High-load ratio: {high_load_ratio:.1f}%")

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
    ax1.set_ylim(0, 105)
    ax1.set_ylabel("Score")
    ax1.set_title(
        f"Attention Heatmap Review | Focus {avg_focus:.1f} | Load {avg_load:.1f} | High-load {high_load_ratio:.1f}%"
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
    ax3.set_ylabel("Motion")
    ax3.set_xlabel("Timeline samples")
    ax3.legend(loc="upper right")
    ax3.grid(axis="y", linestyle="--", alpha=0.18)

    os.makedirs("../exports", exist_ok=True)
    fig.savefig("../exports/attention_heatmap.png", dpi=150)
    fig.savefig("../exports/study_analysis.png", dpi=150)
    print(">>> Saved attention heatmap to ../exports/attention_heatmap.png")


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


if __name__ == "__main__":
    analyze()
