import csv
import os
from datetime import datetime

import pandas as pd


class DataLogger:
    REPORT_FIELDS = [
        "Session_ID",
        "Timestamp",
        "Relative_Pitch",
        "Task_Mode",
        "Stability",
        "Is_Alert",
        "Focus_Score",
        "Cognitive_Load",
        "Load_Level",
        "Behavioral_Alignment",
        "Behavioral_Level",
        "Fatigue_Risk",
        "Fatigue_Level",
        "Uncertainty_Score",
        "Confidence_Level",
        "Guidance",
        "Phase",
        "Elapsed_Seconds",
        "Cycle_Index",
    ]
    DIFFICULTY_FIELDS = [
        "Session_ID",
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
        self.demo_report_path = os.path.join(self.root, "demo_study_report.csv")
        self.demo_difficulty_path = os.path.join(self.root, "demo_difficulty_events.csv")
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
        else:
            self._migrate_difficulty_schema()

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
                "Session_ID": row.get("Session_ID", "") or "legacy-session-1",
                "Timestamp": row.get("Timestamp", ""),
                "Relative_Pitch": row.get("Relative_Pitch", ""),
                "Task_Mode": row.get("Task_Mode", "") or "reading",
                "Stability": row.get("Stability", ""),
                "Is_Alert": row.get("Is_Alert", ""),
                "Focus_Score": row.get("Focus_Score", ""),
                "Cognitive_Load": row.get("Cognitive_Load", ""),
                "Load_Level": row.get("Load_Level", ""),
                "Behavioral_Alignment": row.get("Behavioral_Alignment", "") or row.get("Focus_Score", ""),
                "Behavioral_Level": row.get("Behavioral_Level", "") or "aligned",
                "Fatigue_Risk": row.get("Fatigue_Risk", "") or "0",
                "Fatigue_Level": row.get("Fatigue_Level", "") or "low",
                "Uncertainty_Score": row.get("Uncertainty_Score", "") or "35",
                "Confidence_Level": row.get("Confidence_Level", "") or "medium",
                "Guidance": row.get("Guidance", ""),
                "Phase": row.get("Phase", ""),
                "Elapsed_Seconds": row.get("Elapsed_Seconds", ""),
                "Cycle_Index": row.get("Cycle_Index", ""),
            })

        with open(self.report_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.REPORT_FIELDS)
            writer.writeheader()
            writer.writerows(migrated)

    def _migrate_difficulty_schema(self):
        with open(self.difficulty_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            current_fields = reader.fieldnames or []

        if current_fields == self.DIFFICULTY_FIELDS:
            return

        migrated = []
        for row in rows:
            migrated.append({
                "Session_ID": row.get("Session_ID", "") or "legacy-session-1",
                "Event_ID": row.get("Event_ID", ""),
                "Start_Timestamp": row.get("Start_Timestamp", ""),
                "End_Timestamp": row.get("End_Timestamp", ""),
                "Start_Sample": row.get("Start_Sample", ""),
                "End_Sample": row.get("End_Sample", ""),
                "Duration_Seconds": row.get("Duration_Seconds", ""),
                "Severity": row.get("Severity", ""),
                "Peak_Load": row.get("Peak_Load", ""),
                "Min_Focus": row.get("Min_Focus", ""),
                "Peak_Pitch": row.get("Peak_Pitch", ""),
                "Lowest_Stability": row.get("Lowest_Stability", ""),
                "Primary_Label": row.get("Primary_Label", ""),
                "Trigger_Reason": row.get("Trigger_Reason", ""),
                "Guidance": row.get("Guidance", ""),
                "Review_Note": row.get("Review_Note", ""),
                "Sample_Count": row.get("Sample_Count", ""),
            })

        with open(self.difficulty_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.DIFFICULTY_FIELDS)
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
        task_mode="reading",
        behavioral_alignment=100,
        behavioral_level="aligned",
        fatigue_risk=0,
        fatigue_level="low",
        uncertainty_score=35,
        confidence_level="medium",
        guidance="Keep learning steadily.",
        phase="focus",
        elapsed_seconds=0,
        cycle_index=1,
        timestamp_text=None,
        session_id="",
    ):
        timestamp_text = timestamp_text or datetime.now().strftime("%H:%M:%S")
        with open(self.report_path, "a", newline="") as f:
            csv.writer(f).writerow([
                session_id or "session-unknown",
                timestamp_text,
                round(pitch, 2),
                task_mode,
                int(stability),
                is_alert,
                round(score, 1),
                round(cognitive_load, 1),
                load_level,
                round(behavioral_alignment, 1),
                behavioral_level,
                round(fatigue_risk, 1),
                fatigue_level,
                round(uncertainty_score, 1),
                confidence_level,
                guidance,
                phase,
                int(elapsed_seconds),
                int(cycle_index),
            ])

    def log_difficulty_event(self, event):
        with open(self.difficulty_path, "a", newline="") as f:
            csv.writer(f).writerow([
                event.get("session_id", "session-unknown"),
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

    def build_review_payload(self, session_id=None, dataset="live"):
        report_path, difficulty_path = self._resolve_review_paths(dataset)
        report_df = self._read_optional_csv(report_path)
        difficulty_df = self._read_optional_csv(difficulty_path)

        if report_df.empty and difficulty_df.empty:
            return {
                "dataset": dataset,
                "session_id": session_id or "",
                "session_options": [],
                "summary": self._empty_review_summary(),
                "events": [],
                "next_actions": [{
                    "title": "No session data yet",
                    "detail": "Run a study session or generate demo assets before opening the review page.",
                }],
                "empty": True,
            }

        resolved_session_id = session_id or self._latest_session_id(report_df, difficulty_df)
        session_report = self._filter_session(report_df, resolved_session_id)
        session_events = self._filter_session(difficulty_df, resolved_session_id)

        summary = self._build_review_summary(resolved_session_id, session_report, session_events)
        events = self._build_review_events(session_report, session_events)
        next_actions = self._build_next_actions(summary, events)

        return {
            "dataset": dataset,
            "session_id": resolved_session_id,
            "session_options": self._build_session_options(report_df, difficulty_df),
            "summary": summary,
            "events": events,
            "timeline": self._build_timeline(summary, session_report, events),
            "next_actions": next_actions,
            "empty": False,
        }

    def _resolve_review_paths(self, dataset):
        if str(dataset).lower() == "demo":
            return self.demo_report_path, self.demo_difficulty_path
        return self.report_path, self.difficulty_path

    def _read_optional_csv(self, path):
        if not os.path.exists(path) or os.stat(path).st_size < 10:
            return pd.DataFrame()
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()

    def _latest_session_id(self, report_df, difficulty_df):
        for frame in (report_df, difficulty_df):
            if not frame.empty and "Session_ID" in frame.columns:
                values = [str(value) for value in frame["Session_ID"].dropna().tolist() if str(value).strip()]
                if values:
                    return values[-1]
        return "session-unknown"

    def _filter_session(self, frame, session_id):
        if frame.empty or "Session_ID" not in frame.columns:
            return pd.DataFrame()
        return frame[frame["Session_ID"].astype(str) == str(session_id)].copy()

    def _build_session_options(self, report_df, difficulty_df):
        ordered = []
        for frame in (report_df, difficulty_df):
            if frame.empty or "Session_ID" not in frame.columns:
                continue
            for value in frame["Session_ID"].dropna().tolist():
                session_text = str(value).strip()
                if session_text:
                    ordered.append(session_text)

        unique = list(dict.fromkeys(ordered))
        return [{"session_id": session_id} for session_id in reversed(unique[-12:])]

    def _empty_review_summary(self):
        return {
            "samples": 0,
            "duration_seconds": 0,
            "duration_label": "00:00",
            "primary_task_mode": "unknown",
            "avg_alignment": 0.0,
            "avg_load": 0.0,
            "avg_fatigue": 0.0,
            "high_load_ratio": 0.0,
            "low_confidence_ratio": 0.0,
            "difficulty_count": 0,
            "review_priority": "clear",
        }

    def _build_review_summary(self, session_id, session_report, session_events):
        if session_report.empty:
            summary = self._empty_review_summary()
            summary["session_id"] = session_id
            summary["difficulty_count"] = int(len(session_events.index))
            return summary

        duration_seconds = self._safe_int(session_report["Elapsed_Seconds"].max())
        primary_mode = self._mode_or_default(session_report.get("Task_Mode"), "reading")
        high_load_ratio = self._ratio((session_report.get("Load_Level") == "high").sum(), len(session_report.index))
        low_confidence_ratio = self._ratio((session_report.get("Confidence_Level") == "low").sum(), len(session_report.index))
        severity_values = [str(value).lower() for value in session_events.get("Severity", pd.Series(dtype=str)).tolist()]
        review_priority = "high" if "high" in severity_values else "medium" if len(severity_values) else "clear"

        return {
            "session_id": session_id,
            "samples": int(len(session_report.index)),
            "duration_seconds": duration_seconds,
            "duration_label": self._format_mmss(duration_seconds),
            "primary_task_mode": primary_mode,
            "avg_alignment": round(self._safe_float(session_report["Behavioral_Alignment"].mean()), 1),
            "avg_load": round(self._safe_float(session_report["Cognitive_Load"].mean()), 1),
            "avg_fatigue": round(self._safe_float(session_report["Fatigue_Risk"].mean()), 1),
            "high_load_ratio": high_load_ratio,
            "low_confidence_ratio": low_confidence_ratio,
            "difficulty_count": int(len(session_events.index)),
            "review_priority": review_priority,
        }

    def _build_review_events(self, session_report, session_events):
        if session_events.empty:
            return []

        ordered = session_events.copy()
        ordered["Event_ID"] = pd.to_numeric(ordered["Event_ID"], errors="coerce").fillna(0).astype(int)
        ordered = ordered.sort_values(["Event_ID", "Start_Sample"], ascending=[True, True])

        events = []
        for _, row in ordered.iterrows():
            start_sample = max(1, self._safe_int(row.get("Start_Sample", 1)))
            end_sample = max(start_sample, self._safe_int(row.get("End_Sample", start_sample)))
            segment = session_report.iloc[start_sample - 1:end_sample] if not session_report.empty else pd.DataFrame()
            severity = str(row.get("Severity", "medium")).lower()
            primary_mode = self._mode_or_default(segment.get("Task_Mode"), self._mode_or_default(session_report.get("Task_Mode"), "reading"))
            phase = self._mode_or_default(segment.get("Phase"), "focus")
            avg_alignment = round(self._safe_float(segment.get("Behavioral_Alignment", pd.Series(dtype=float)).mean()), 1) if not segment.empty else 0.0
            avg_load = round(self._safe_float(segment.get("Cognitive_Load", pd.Series(dtype=float)).mean()), 1) if not segment.empty else 0.0
            avg_fatigue = round(self._safe_float(segment.get("Fatigue_Risk", pd.Series(dtype=float)).mean()), 1) if not segment.empty else 0.0
            low_conf_ratio = self._ratio((segment.get("Confidence_Level") == "low").sum(), len(segment.index)) if not segment.empty else 0.0
            missed_risk = self._missed_content_risk(severity, avg_load, low_conf_ratio)

            review_note = str(row.get("Review_Note", "")).strip() or self._review_action(severity, primary_mode, avg_fatigue)
            events.append({
                "event_id": self._safe_int(row.get("Event_ID", 0)),
                "severity": severity,
                "severity_label": severity.upper(),
                "time_window": f"{row.get('Start_Timestamp', '--')} - {row.get('End_Timestamp', '--')}",
                "duration_seconds": round(self._safe_float(row.get("Duration_Seconds", 0)), 1),
                "start_sample": start_sample,
                "end_sample": end_sample,
                "sample_window": f"{start_sample}-{end_sample}",
                "task_mode": primary_mode,
                "phase": phase,
                "peak_load": round(self._safe_float(row.get("Peak_Load", 0)), 1),
                "min_focus": round(self._safe_float(row.get("Min_Focus", 0)), 1),
                "avg_alignment": avg_alignment,
                "avg_load": avg_load,
                "avg_fatigue": avg_fatigue,
                "missed_content_risk": missed_risk,
                "trigger_label": str(row.get("Primary_Label", "")).strip() or "Load rising",
                "trigger_reason": str(row.get("Trigger_Reason", "")).strip() or "State change detected",
                "guidance": str(row.get("Guidance", "")).strip() or "Review this segment carefully.",
                "review_note": review_note,
                "catch_up_action": self._catch_up_action(severity, primary_mode, avg_fatigue, missed_risk),
            })

        return events

    def _build_timeline(self, summary, session_report, events):
        sample_count = int(summary.get("samples", 0))
        if session_report.empty or sample_count <= 0:
            return {
                "samples": sample_count,
                "duration_label": summary.get("duration_label", "00:00"),
                "events": [],
                "risk_segments": {
                    "high_load": [],
                    "low_confidence": [],
                    "fatigue": [],
                },
            }

        load_levels = session_report.get("Load_Level", pd.Series(dtype=str)).fillna("").astype(str).str.lower()
        confidence_levels = session_report.get("Confidence_Level", pd.Series(dtype=str)).fillna("").astype(str).str.lower()
        fatigue_risk = pd.to_numeric(session_report.get("Fatigue_Risk", pd.Series(dtype=float)), errors="coerce").fillna(0)

        return {
            "samples": sample_count,
            "duration_label": summary.get("duration_label", "00:00"),
            "events": [
                {
                    "event_id": int(event["event_id"]),
                    "severity": event["severity"],
                    "start_sample": int(event["start_sample"]),
                    "end_sample": int(event["end_sample"]),
                    "task_mode": event["task_mode"],
                }
                for event in events
            ],
            "risk_segments": {
                "high_load": self._mask_segments(load_levels.eq("high")),
                "low_confidence": self._mask_segments(confidence_levels.eq("low")),
                "fatigue": self._mask_segments(fatigue_risk >= 55),
            },
        }

    def _build_next_actions(self, summary, events):
        if not events:
            return [{
                "title": "No flagged difficulty segment",
                "detail": "This session has no sustained medium/high difficulty event. Keep the heatmap as a general reflection aid.",
            }]

        top_event = sorted(events, key=lambda item: (0 if item["severity"] == "high" else 1, -item["peak_load"], -item["duration_seconds"]))[0]
        actions = [{
            "title": f"Review D{top_event['event_id']} first",
            "detail": f"{top_event['time_window']} in {top_event['task_mode']} mode was the strongest difficulty segment. {top_event['catch_up_action']}",
        }]

        if summary.get("avg_fatigue", 0) >= 40:
            actions.append({
                "title": "Reduce fatigue before retrying",
                "detail": "Fatigue stayed elevated in this session. Take a short break before replaying the flagged section.",
            })

        if summary.get("low_confidence_ratio", 0) >= 18:
            actions.append({
                "title": "Recalibrate and replay",
                "detail": "Signal confidence dropped multiple times. Recalibrate posture baseline before the next run.",
            })
        else:
            actions.append({
                "title": "Use the event list as a replay map",
                "detail": "Revisit the flagged sections in order and compare them with your notes or source material.",
            })

        return actions[:3]

    def _missed_content_risk(self, severity, avg_load, low_conf_ratio):
        if severity == "high" or avg_load >= 70 or low_conf_ratio >= 25:
            return "high"
        if avg_load >= 50 or low_conf_ratio >= 10:
            return "medium"
        return "low"

    def _review_action(self, severity, task_mode, avg_fatigue):
        if severity == "high" and avg_fatigue >= 45:
            return "Pause first, then replay this segment slowly with a fresh posture baseline."
        if task_mode == "note-taking":
            return "Compare this segment with your notes and check whether a step or definition was skipped."
        if task_mode == "review":
            return "Reopen the source material and verify the exact point that caused the load rise."
        if severity == "high":
            return "Replay this segment first and reduce the pace while following the same material."
        return "Review this segment once more and confirm the main idea before moving on."

    def _catch_up_action(self, severity, task_mode, avg_fatigue, missed_risk):
        if severity == "high" and missed_risk == "high":
            return "Replay the whole segment from the start and rebuild the missing context before continuing."
        if avg_fatigue >= 45:
            return "Take a short reset, then revisit this segment with a slower pace."
        if task_mode == "note-taking":
            return "Check your notes line by line and rewrite the missing step or keyword."
        if task_mode == "lecture":
            return "Replay the explanation and pause on the point where the load started to rise."
        return "Revisit this segment once and verify the key concept before continuing."

    def _mask_segments(self, mask):
        segments = []
        start_index = None
        bool_values = [bool(value) for value in list(mask)]
        for index, active in enumerate(bool_values, start=1):
            if active and start_index is None:
                start_index = index
            if start_index is not None and (not active or index == len(bool_values)):
                end_index = index if active and index == len(bool_values) else index - 1
                segments.append({
                    "start_sample": start_index,
                    "end_sample": end_index,
                })
                start_index = None
        return segments

    def _mode_or_default(self, series, default):
        if series is None:
            return default
        values = [str(value).strip() for value in series.dropna().tolist() if str(value).strip()]
        if not values:
            return default
        return pd.Series(values).mode().iloc[0]

    def _format_mmss(self, seconds):
        total = max(0, self._safe_int(seconds))
        minutes = total // 60
        remain = total % 60
        return f"{minutes:02d}:{remain:02d}"

    def _ratio(self, count, total):
        if not total:
            return 0.0
        return round((float(count) / float(total)) * 100, 1)

    def _safe_float(self, value):
        try:
            if pd.isna(value):
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def _safe_int(self, value):
        try:
            if pd.isna(value):
                return 0
            return int(float(value))
        except Exception:
            return 0
