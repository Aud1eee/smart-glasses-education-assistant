import csv
import os
from datetime import datetime

import pandas as pd


class DataLogger:
    REPORT_FIELDS = [
        "Timestamp",
        "Relative_Pitch",
        "Stability",
        "Is_Alert",
        "Focus_Score",
        "Cognitive_Load",
        "Load_Level",
        "Guidance",
        "Phase",
        "Elapsed_Seconds",
        "Cycle_Index",
    ]
    DIFFICULTY_FIELDS = [
        "Event_ID",
        "Start_Timestamp",
        "End_Timestamp",
        "Start_Sample",
        "End_Sample",
        "Duration_Seconds",
        "Severity",
        "Peak_Load",
        "Min_Focus",
        "Peak_Pitch",
        "Lowest_Stability",
        "Primary_Label",
        "Trigger_Reason",
        "Guidance",
        "Review_Note",
        "Sample_Count",
    ]

    def __init__(self, root_dir="data"):
        self.root = root_dir
        os.makedirs(self.root, exist_ok=True)
        self.report_path = os.path.join(self.root, "study_report.csv")
        self.difficulty_path = os.path.join(self.root, "difficulty_events.csv")
        self.vocab_path = os.path.join(self.root, "my_vocabulary.csv")
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.report_path) or os.stat(self.report_path).st_size < 10:
            with open(self.report_path, "w", newline="") as f:
                csv.writer(f).writerow(self.REPORT_FIELDS)
        else:
            self._migrate_report_schema()

        if not os.path.exists(self.vocab_path) or os.stat(self.vocab_path).st_size < 10:
            with open(self.vocab_path, "w", newline="") as f:
                csv.writer(f).writerow(["Word", "Translation", "Count", "Last_Seen"])

        if not os.path.exists(self.difficulty_path) or os.stat(self.difficulty_path).st_size < 10:
            with open(self.difficulty_path, "w", newline="") as f:
                csv.writer(f).writerow(self.DIFFICULTY_FIELDS)

    def _migrate_report_schema(self):
        with open(self.report_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            current_fields = reader.fieldnames or []

        if current_fields == self.REPORT_FIELDS:
            return

        migrated = []
        for row in rows:
            migrated.append({
                "Timestamp": row.get("Timestamp", ""),
                "Relative_Pitch": row.get("Relative_Pitch", ""),
                "Stability": row.get("Stability", ""),
                "Is_Alert": row.get("Is_Alert", ""),
                "Focus_Score": row.get("Focus_Score", ""),
                "Cognitive_Load": row.get("Cognitive_Load", ""),
                "Load_Level": row.get("Load_Level", ""),
                "Guidance": row.get("Guidance", ""),
                "Phase": row.get("Phase", ""),
                "Elapsed_Seconds": row.get("Elapsed_Seconds", ""),
                "Cycle_Index": row.get("Cycle_Index", ""),
            })

        with open(self.report_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(migrated)

    def log_study(
        self,
        pitch,
        is_alert,
        score,
        stability=100,
        cognitive_load=0,
        load_level="low",
        guidance="Keep learning steadily.",
        phase="focus",
        elapsed_seconds=0,
        cycle_index=1,
        timestamp_text=None,
    ):
        timestamp_text = timestamp_text or datetime.now().strftime("%H:%M:%S")
        with open(self.report_path, "a", newline="") as f:
            csv.writer(f).writerow([
                timestamp_text,
                round(pitch, 2),
                int(stability),
                is_alert,
                round(score, 1),
                round(cognitive_load, 1),
                load_level,
                guidance,
                phase,
                int(elapsed_seconds),
                int(cycle_index),
            ])

    def log_difficulty_event(self, event):
        with open(self.difficulty_path, "a", newline="") as f:
            csv.writer(f).writerow([
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

    def save_word(self, word, trans):
        df = pd.read_csv(self.vocab_path)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if word in df["Word"].values:
            df.loc[df["Word"] == word, "Count"] += 1
            df.loc[df["Word"] == word, "Last_Seen"] = now_str
        else:
            new_row = pd.DataFrame([{
                "Word": word,
                "Translation": trans,
                "Count": 1,
                "Last_Seen": now_str,
            }])
            df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(self.vocab_path, index=False)

    def get_vocab_count(self):
        try:
            return len(pd.read_csv(self.vocab_path))
        except Exception:
            return 0
