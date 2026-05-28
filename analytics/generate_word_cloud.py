import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import bootstrap_windows_runtime  # noqa: F401

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_ERROR = None
except Exception as exc:
    plt = None
    MATPLOTLIB_ERROR = exc


def plot_vocab_analysis():
    if plt is None:
        print(f">>> Matplotlib unavailable in the current Windows runtime bridge: {MATPLOTLIB_ERROR}")
        print(">>> Vocabulary chart export is skipped in this runtime.")
        return

    # Keep relative paths aligned with the Windows launcher flow.
    input_file = "../data/my_vocabulary.csv"
    output_dir = "../exports"

    if not os.path.exists(input_file):
        print(">>> Vocabulary data was not found. Capture some words first.")
        return

    try:
        df = pd.read_csv(input_file)
        if df.empty:
            print(">>> The vocabulary list is currently empty.")
            return

        # Keep only the most frequently queried words so the chart stays readable.
        df = df.sort_values("Count", ascending=False).head(15)

        # Match the darker HUD-oriented visual style used elsewhere in the project.
        plt.style.use("dark_background")
        plt.figure(figsize=(12, 6))

        colors = plt.cm.viridis(df["Count"] / df["Count"].max())
        bars = plt.bar(df["Word"], df["Count"], color=colors, edgecolor="#00ff9d", linewidth=1)

        # Add value labels above each bar.
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width() / 2, yval + 0.5, yval, ha="center", color="#00ff9d")

        plt.title("Vocab Mastery & Difficulty Analysis", fontsize=15, color="#00ff9d", pad=20)
        plt.ylabel("Inquiry Frequency (Difficulty)", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        plt.grid(axis="y", linestyle="--", alpha=0.3)

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "vocab_intensity.png")
        plt.tight_layout()
        plt.savefig(output_path)
        print(f"\nVocabulary visualization completed. Chart saved to: {output_path}")

    except Exception as exc:
        print(f">>> Vocabulary visualization failed: {exc}")


if __name__ == "__main__":
    plot_vocab_analysis()
