import csv
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analytics.analyze_report import analyze
from core.difficulty_marker import DifficultyEventMarker
from core.focus_session import FocusSessionEngine
from core.posture import PostureEngine
from simulate_motion import PRESENTATION_SEQUENCE, SCENARIOS
from utils.storage import DataLogger


DEMO_REPORT_PATH = ROOT / "data" / "demo_study_report.csv"
DEMO_DIFFICULTY_PATH = ROOT / "data" / "demo_difficulty_events.csv"
DEMO_HEATMAP_PATH = ROOT / "exports" / "demo_attention_heatmap.png"


def format_timestamp(seconds):
    minutes = int(seconds // 60)
    whole_seconds = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def generate_demo_report(
    output_path=DEMO_REPORT_PATH,
    difficulty_output_path=DEMO_DIFFICULTY_PATH,
    seed=7,
    interval=0.12,
    session_id="demo-session-1",
):
    random.seed(seed)
    posture = PostureEngine()
    session = FocusSessionEngine()
    difficulty_marker = DifficultyEventMarker()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    difficulty_output_path.parent.mkdir(parents=True, exist_ok=True)

    now = 0.0
    with (
        open(output_path, "w", newline="", encoding="utf-8") as handle,
        open(difficulty_output_path, "w", newline="", encoding="utf-8") as difficulty_handle,
    ):
        writer = csv.writer(handle)
        difficulty_writer = csv.writer(difficulty_handle)
        writer.writerow(DataLogger.REPORT_FIELDS)
        difficulty_writer.writerow(DataLogger.DIFFICULTY_FIELDS)

        for _ in range(20):
            posture.process(8.0, now=now)
            now += 0.05

        posture.calibrate()
        session.reset(now=now)
        difficulty_marker.reset()
        sample_index = 0

        for mode, seconds in PRESENTATION_SEQUENCE:
            config = SCENARIOS[mode]
            samples = max(1, int(seconds / interval))
            for step in range(samples):
                sample_index += 1
                pitch = config["center"] + math.sin(step * config["speed"]) * config["swing"]
                pitch += random.uniform(-config["noise"], config["noise"])
                result = posture.process(pitch, now=now)
                session_result = session.update(result, now=now)
                timestamp_text = format_timestamp(now)
                difficulty_result = difficulty_marker.update(
                    result,
                    session_result,
                    now=now,
                    timestamp_text=timestamp_text,
                    sample_index=sample_index,
                    session_id=session_id,
                )
                writer.writerow([
                    session_id,
                    timestamp_text,
                    round(result["relative_pitch"], 2),
                    result["task_mode"],
                    int(result["stability"]),
                    result["is_alert"],
                    round(result["focus_score"], 1),
                    round(result["cognitive_load"], 1),
                    result["load_level"],
                    round(result["behavioral_alignment"], 1),
                    result["behavioral_level"],
                    round(result["fatigue_risk"], 1),
                    result["fatigue_level"],
                    round(result["uncertainty_score"], 1),
                    result["confidence_level"],
                    session_result["guidance"],
                    session_result["phase"],
                    int(session_result["elapsed_seconds"]),
                    int(session_result["cycle_index"]),
                ])
                if difficulty_result["completed_event"]:
                    event = difficulty_result["completed_event"]
                    difficulty_writer.writerow([
                        event["session_id"],
                        int(event["event_id"]),
                        event["start_timestamp"],
                        event["end_timestamp"],
                        int(event["start_sample"]),
                        int(event["end_sample"]),
                        round(event["duration_seconds"], 1),
                        event["severity"],
                        round(event["peak_load"], 1),
                        round(event["min_focus"], 1),
                        round(event["peak_pitch"], 1),
                        round(event["lowest_stability"], 1),
                        event["primary_label"],
                        event["trigger_reason"],
                        event["guidance"],
                        event["review_note"],
                        int(event["sample_count"]),
                    ])
                now += interval

        final_event = difficulty_marker.flush(
            now=now,
            timestamp_text=format_timestamp(now),
            sample_index=sample_index,
            session_id=session_id,
        )
        if final_event:
            difficulty_writer.writerow([
                final_event["session_id"],
                int(final_event["event_id"]),
                final_event["start_timestamp"],
                final_event["end_timestamp"],
                int(final_event["start_sample"]),
                int(final_event["end_sample"]),
                round(final_event["duration_seconds"], 1),
                final_event["severity"],
                round(final_event["peak_load"], 1),
                round(final_event["min_focus"], 1),
                round(final_event["peak_pitch"], 1),
                round(final_event["lowest_stability"], 1),
                final_event["primary_label"],
                final_event["trigger_reason"],
                final_event["guidance"],
                final_event["review_note"],
                int(final_event["sample_count"]),
            ])

    return output_path, difficulty_output_path


def main():
    report_path, difficulty_path = generate_demo_report()
    summary = analyze(
        input_path=report_path,
        heatmap_path=DEMO_HEATMAP_PATH,
        legacy_output_path=None,
        events_path=difficulty_path,
        title_prefix="Demo Attention Heatmap Review",
    )

    print("\nDemo assets generated")
    print(f"- CSV: {report_path}")
    print(f"- Difficulty events: {difficulty_path}")
    print(f"- Heatmap: {DEMO_HEATMAP_PATH}")
    if summary:
        print(
            f"- Summary: {summary['samples']} samples | "
            f"focus {summary['avg_focus']} | load {summary['avg_load']} | "
            f"high-load {summary['high_load_ratio']}%"
        )


if __name__ == "__main__":
    main()
