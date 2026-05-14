import csv
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.analyze_report import analyze
from core.focus_session import FocusSessionEngine
from core.posture import PostureEngine
from simulate_motion import PRESENTATION_SEQUENCE, SCENARIOS
from utils.storage import DataLogger


DEMO_REPORT_PATH = ROOT / "data" / "demo_study_report.csv"
DEMO_HEATMAP_PATH = ROOT / "exports" / "demo_attention_heatmap.png"


def format_timestamp(seconds):
    minutes = int(seconds // 60)
    whole_seconds = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def generate_demo_report(output_path=DEMO_REPORT_PATH, seed=7, interval=0.12):
    random.seed(seed)
    posture = PostureEngine()
    session = FocusSessionEngine()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    now = 0.0
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(DataLogger.REPORT_FIELDS)

        for _ in range(20):
            posture.process(8.0, now=now)
            now += 0.05

        posture.calibrate()
        session.reset(now=now)

        for mode, seconds in PRESENTATION_SEQUENCE:
            config = SCENARIOS[mode]
            samples = max(1, int(seconds / interval))
            for step in range(samples):
                pitch = config["center"] + math.sin(step * config["speed"]) * config["swing"]
                pitch += random.uniform(-config["noise"], config["noise"])
                result = posture.process(pitch, now=now)
                session_result = session.update(result, now=now)
                writer.writerow([
                    format_timestamp(now),
                    round(result["relative_pitch"], 2),
                    int(result["stability"]),
                    result["is_alert"],
                    round(result["focus_score"], 1),
                    round(result["cognitive_load"], 1),
                    result["load_level"],
                    session_result["guidance"],
                    session_result["phase"],
                    int(session_result["elapsed_seconds"]),
                    int(session_result["cycle_index"]),
                ])
                now += interval

    return output_path


def main():
    report_path = generate_demo_report()
    summary = analyze(
        input_path=report_path,
        heatmap_path=DEMO_HEATMAP_PATH,
        legacy_output_path=None,
        title_prefix="Demo Attention Heatmap Review",
    )

    print("\nDemo assets generated")
    print(f"- CSV: {report_path}")
    print(f"- Heatmap: {DEMO_HEATMAP_PATH}")
    if summary:
        print(
            f"- Summary: {summary['samples']} samples | "
            f"focus {summary['avg_focus']} | load {summary['avg_load']} | "
            f"high-load {summary['high_load_ratio']}%"
        )


if __name__ == "__main__":
    main()
