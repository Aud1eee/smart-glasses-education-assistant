from datetime import datetime
import time


class DifficultyEventMarker:
    def __init__(self, medium_trigger_seconds=3.0, high_trigger_seconds=1.5, resolve_seconds=3.0):
        self.medium_trigger_seconds = medium_trigger_seconds
        self.high_trigger_seconds = high_trigger_seconds
        self.resolve_seconds = resolve_seconds
        self.event_counter = 0
        self.reset()

    def reset(self):
        self.candidate_start = None
        self.candidate_rank = 0
        self.candidate_label = ""
        self.candidate_reason = ""
        self.candidate_start_sample = None
        self.active_event = None
        self.resolve_start = None
        self.last_completed_event = None

    def update(self, posture_state, session_state, now=None, timestamp_text=None, sample_index=None):
        now = time.time() if now is None else now
        timestamp_text = timestamp_text or self._format_timestamp(now)
        rank, severity, label, reason = self._classify(posture_state, session_state)

        completed_event = None
        if self.active_event is None:
            completed_event = self._handle_candidate(
                rank,
                severity,
                label,
                reason,
                posture_state,
                session_state,
                now,
                timestamp_text,
                sample_index,
            )
        else:
            completed_event = self._update_active_event(
                rank,
                severity,
                label,
                reason,
                posture_state,
                session_state,
                now,
                timestamp_text,
                sample_index,
            )

        return {
            "active_event": self._public_event(self.active_event),
            "completed_event": completed_event,
            "last_event": self.last_completed_event,
            "event_count": self.event_counter,
        }

    def flush(self, now=None, timestamp_text=None, sample_index=None):
        if self.active_event is None:
            return None
        now = time.time() if now is None else now
        timestamp_text = timestamp_text or self._format_timestamp(now)
        return self._close_event(now, timestamp_text, sample_index)

    def _handle_candidate(
        self,
        rank,
        severity,
        label,
        reason,
        posture_state,
        session_state,
        now,
        timestamp_text,
        sample_index,
    ):
        if rank == 0:
            self._clear_candidate()
            return None

        if self.candidate_start is None:
            self.candidate_start = now
            self.candidate_rank = rank
            self.candidate_label = label
            self.candidate_reason = reason
            self.candidate_start_sample = sample_index
        else:
            if rank > self.candidate_rank:
                self.candidate_rank = rank
                self.candidate_label = label
            if reason:
                self.candidate_reason = reason

        trigger_seconds = self.high_trigger_seconds if self.candidate_rank == 2 else self.medium_trigger_seconds
        if now - self.candidate_start < trigger_seconds:
            return None

        self.event_counter += 1
        self.active_event = {
            "event_id": self.event_counter,
            "severity": "high" if self.candidate_rank == 2 else "medium",
            "start_time": self.candidate_start,
            "start_timestamp": timestamp_text,
            "start_sample": self.candidate_start_sample or sample_index or 0,
            "end_time": now,
            "end_timestamp": timestamp_text,
            "end_sample": sample_index or 0,
            "peak_load": float(posture_state.get("cognitive_load", 0)),
            "min_focus": float(posture_state.get("focus_score", 100)),
            "peak_pitch": float(posture_state.get("relative_pitch", 0)),
            "lowest_stability": float(posture_state.get("stability", 100)),
            "primary_label": self.candidate_label or label,
            "trigger_reason": self.candidate_reason or reason,
            "guidance": session_state.get("guidance", ""),
            "sample_count": 1,
        }
        self.resolve_start = None
        self._clear_candidate()
        return None

    def _update_active_event(
        self,
        rank,
        severity,
        label,
        reason,
        posture_state,
        session_state,
        now,
        timestamp_text,
        sample_index,
    ):
        event = self.active_event
        event["end_time"] = now
        event["end_timestamp"] = timestamp_text
        event["end_sample"] = sample_index or event["end_sample"]
        event["sample_count"] += 1
        event["peak_load"] = max(event["peak_load"], float(posture_state.get("cognitive_load", 0)))
        event["min_focus"] = min(event["min_focus"], float(posture_state.get("focus_score", 100)))
        event["peak_pitch"] = max(event["peak_pitch"], float(posture_state.get("relative_pitch", 0)))
        event["lowest_stability"] = min(event["lowest_stability"], float(posture_state.get("stability", 100)))
        if rank >= 2:
            event["severity"] = "high"
        if rank > 0 and label and label not in {"Focus settling", "Recovery"}:
            event["primary_label"] = label
        if rank > 0 and reason and reason != "Stable learning state":
            event["trigger_reason"] = reason
        if rank > 0 and session_state.get("guidance"):
            event["guidance"] = session_state["guidance"]

        if rank == 0:
            if self.resolve_start is None:
                self.resolve_start = now
            elif now - self.resolve_start >= self.resolve_seconds:
                return self._close_event(now, timestamp_text, sample_index)
        else:
            self.resolve_start = None

        return None

    def _close_event(self, now, timestamp_text, sample_index):
        event = self.active_event
        if event is None:
            return None

        event["end_time"] = now
        event["end_timestamp"] = timestamp_text
        event["end_sample"] = sample_index or event["end_sample"]
        event["duration_seconds"] = round(max(0.0, now - event["start_time"]), 1)
        event["review_note"] = self._build_review_note(event)

        public_event = self._public_event(event, resolved=True)
        self.last_completed_event = public_event
        self.active_event = None
        self.resolve_start = None
        self._clear_candidate()
        return public_event

    def _classify(self, posture_state, session_state):
        level = posture_state.get("load_level", "low")
        action = session_state.get("action", "")
        label = session_state.get("state_label") or posture_state.get("load_reason", "")
        reason = posture_state.get("load_reason", "")

        if level == "high" or action in {"slow_down", "micro_break"}:
            return 2, "high", label or "High load", reason
        if level == "medium" or action == "regulate":
            return 1, "medium", label or "Load rising", reason
        return 0, "low", label or "Stable focus", reason

    def _build_review_note(self, event):
        if event["severity"] == "high":
            return "Review this segment first: load rose and reached a high-load state."
        return "Review this segment: sustained rising load suggests a possible difficulty point."

    def _public_event(self, event, resolved=False):
        if event is None:
            return None
        return {
            "event_id": int(event["event_id"]),
            "status": "resolved" if resolved else "active",
            "severity": event["severity"],
            "start_timestamp": event["start_timestamp"],
            "end_timestamp": event["end_timestamp"],
            "start_sample": int(event["start_sample"]),
            "end_sample": int(event["end_sample"]),
            "duration_seconds": round(max(0.0, event.get("duration_seconds", event["end_time"] - event["start_time"])), 1),
            "peak_load": round(event["peak_load"], 1),
            "min_focus": round(event["min_focus"], 1),
            "peak_pitch": round(event["peak_pitch"], 1),
            "lowest_stability": round(event["lowest_stability"], 1),
            "primary_label": event["primary_label"],
            "trigger_reason": event["trigger_reason"],
            "guidance": event["guidance"],
            "sample_count": int(event["sample_count"]),
            "review_note": event.get("review_note") or self._build_review_note(event),
        }

    def _clear_candidate(self):
        self.candidate_start = None
        self.candidate_rank = 0
        self.candidate_label = ""
        self.candidate_reason = ""
        self.candidate_start_sample = None

    def _format_timestamp(self, now):
        if isinstance(now, (int, float)) and now > 100000:
            return datetime.fromtimestamp(now).strftime("%H:%M:%S")
        minutes = int(now // 60)
        seconds = int(now % 60)
        centiseconds = int((now % 1) * 100)
        return f"{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
