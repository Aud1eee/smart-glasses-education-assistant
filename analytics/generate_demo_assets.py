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
from simulate_motion import PRESENTATION_SEQUENCE, SCENARIOS, scenario_pose
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
            posture.process(8.0, raw_yaw=1.0, raw_roll=0.8, motion_intensity=10.0, now=now)
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
                pose = scenario_pose(config, step)
                pose["pitch"] += random.uniform(-config["noise"] * 0.2, config["noise"] * 0.2)
                result = posture.process(
                    pose["pitch"],
                    raw_yaw=pose["yaw"],
                    raw_roll=pose["roll"],
                    motion_intensity=pose["motion_intensity"],
                    now=now,
                )
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
                row = {
                    "Session_ID": session_id,
                    "Timestamp": timestamp_text,
                    "Relative_Pitch": round(result["relative_pitch"], 2),
                    "Relative_Yaw": round(result.get("relative_yaw", 0), 2),
                    "Relative_Roll": round(result.get("relative_roll", 0), 2),
                    "Combined_Drift": round(result.get("combined_drift", result["relative_pitch"]), 2),
                    "Orientation_Drift": round(result.get("orientation_drift", 0), 1),
                    "Movement_Intensity": round(result.get("movement_intensity", 0), 2),
                    "Task_Mode": result["task_mode"],
                    "Input_Source": "simulator",
                    "Stability": int(result["stability"]),
                    "Is_Alert": result["is_alert"],
                    "Focus_Score": round(result["focus_score"], 1),
                    "Cognitive_Load": round(result["cognitive_load"], 1),
                    "Load_Level": result["load_level"],
                    "Behavioral_Alignment": round(result["behavioral_alignment"], 1),
                    "Behavioral_Level": result["behavioral_level"],
                    "Drift_Trend": round(result.get("drift_trend", 0), 1),
                    "Switching_Index": round(result.get("switching_index", 0), 1),
                    "State_Hint": result.get("state_hint", "stable"),
                    "Fatigue_Risk": round(result["fatigue_risk"], 1),
                    "Fatigue_Level": result["fatigue_level"],
                    "Uncertainty_Score": round(result["uncertainty_score"], 1),
                    "Confidence_Level": result["confidence_level"],
                    "Guidance": session_result["guidance"],
                    "Phase": session_result["phase"],
                    "Elapsed_Seconds": int(session_result["elapsed_seconds"]),
                    "Cycle_Index": int(session_result["cycle_index"]),
                }
                writer.writerow([row[field] for field in DataLogger.REPORT_FIELDS])
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
    if summary:
        if summary.get("heatmap_saved"):
            print(f"- Heatmap: {DEMO_HEATMAP_PATH}")
        else:
            print("- Heatmap: skipped in the current Windows runtime bridge")
        print(
            f"- Summary: {summary['samples']} samples | "
            f"align {summary['avg_alignment']} | load {summary['avg_load']} | "
            f"fatigue {summary['avg_fatigue']} | low-conf {summary['low_conf_ratio']}%"
        )


if __name__ == "__main__":
    main()
