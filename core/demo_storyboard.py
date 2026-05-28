from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.state_classifier import rule_baseline


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_FEATURES_PATH = DATA_DIR / "state_window_features.csv"

STAGE_ORDER = [
    "stable_focus",
    "load_rising",
    "productive_struggle",
    "off_task_risk",
    "recovery",
]

STAGE_TITLES = {
    "stable_focus": "Stage 1 | Stable Focus",
    "load_rising": "Stage 2 | Load Rising",
    "productive_struggle": "Stage 3 | Productive Struggle Proxy",
    "off_task_risk": "Stage 4 | Off-Task Risk",
    "recovery": "Stage 5 | Recovery",
}

TRANSITIONS = {
    "stable_focus": "The first transition happens when calm study rhythm starts to show rising load and drift pressure.",
    "load_rising": "The next question is whether the learner can still hold the challenge, or whether drift takes over completely.",
    "productive_struggle": "This is the point where a replay or tutor intervention still has leverage before the session becomes mostly reactive.",
    "off_task_risk": "After the most fragmented stretch, the key demo question becomes whether the learner can rebuild a steadier pattern.",
    "recovery": "Close by showing that the system can narrate recovery and next-step coaching, not only breakdown.",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    return frame if not frame.empty else pd.DataFrame(columns=frame.columns.tolist())


def _resolve_paths(dataset: str) -> tuple[Path, Path]:
    normalized = str(dataset or "demo").strip().lower()
    if normalized == "live":
        return DATA_DIR / "study_report.csv", DATA_DIR / "difficulty_events.csv"
    return DATA_DIR / "demo_study_report.csv", DATA_DIR / "demo_difficulty_events.csv"


def _normalize_state(series: pd.Series | None) -> pd.Series:
    if series is None:
        return pd.Series(dtype=str)
    return series.fillna("").astype(str).str.strip().str.lower()


def _prepare_report_frame(frame: pd.DataFrame, session_id: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    if "Session_ID" in frame.columns and session_id:
        frame = frame[frame["Session_ID"].astype(str).str.strip() == str(session_id).strip()].copy()
    if frame.empty:
        return pd.DataFrame()
    working = frame.reset_index(drop=True).copy()
    working["__sample"] = [index + 1 for index in range(len(working.index))]
    return working


def _prepare_events_frame(frame: pd.DataFrame, session_id: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    if "Session_ID" in frame.columns and session_id:
        frame = frame[frame["Session_ID"].astype(str).str.strip() == str(session_id).strip()].copy()
    if frame.empty:
        return pd.DataFrame()
    return frame.reset_index(drop=True).copy()


def _window_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> int:
    return max(0, min(end_a, end_b) - max(start_a, start_b) + 1)


def _contiguous_segments(frame: pd.DataFrame, mask: pd.Series) -> list[dict[str, Any]]:
    if frame.empty or mask.empty:
        return []
    values = mask.fillna(False).astype(bool).tolist()
    segments: list[dict[str, Any]] = []
    start_index: int | None = None
    for index, matched in enumerate(values):
        if matched and start_index is None:
            start_index = index
        elif not matched and start_index is not None:
            rows = frame.iloc[start_index:index].copy()
            if not rows.empty:
                segments.append(_segment_from_rows(rows, source="contiguous"))
            start_index = None
    if start_index is not None:
        rows = frame.iloc[start_index:].copy()
        if not rows.empty:
            segments.append(_segment_from_rows(rows, source="contiguous"))
    return segments


def _segment_from_rows(rows: pd.DataFrame, source: str) -> dict[str, Any]:
    first = rows.iloc[0]
    last = rows.iloc[-1]
    return {
        "source": source,
        "start_sample": _safe_int(first.get("__sample"), default=1),
        "end_sample": _safe_int(last.get("__sample"), default=1),
        "start_timestamp": str(first.get("Timestamp", "--")).strip() or "--",
        "end_timestamp": str(last.get("Timestamp", "--")).strip() or "--",
        "rows": rows,
    }


def _slice_segment(frame: pd.DataFrame, start_sample: int, end_sample: int, source: str) -> dict[str, Any] | None:
    if frame.empty:
        return None
    rows = frame[(frame["__sample"] >= int(start_sample)) & (frame["__sample"] <= int(end_sample))].copy()
    if rows.empty:
        return None
    return _segment_from_rows(rows, source=source)


def _event_lookup(review_payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    events = review_payload.get("events", []) if isinstance(review_payload, dict) else []
    valid_events = [event for event in events if isinstance(event, dict)]
    highlight = review_payload.get("highlight_event") if isinstance(review_payload, dict) else None
    return valid_events, highlight if isinstance(highlight, dict) else None


def _select_stable_segment(frame: pd.DataFrame) -> dict[str, Any] | None:
    if frame.empty:
        return None
    hints = _normalize_state(frame.get("State_Hint"))
    end_index = 0
    while end_index < len(frame.index) and hints.iloc[end_index] == "stable":
        end_index += 1
    if end_index >= 8:
        return _segment_from_rows(frame.iloc[:end_index].copy(), source="leading_stable")
    stable_mask = (
        hints.eq("stable")
        & (pd.to_numeric(frame.get("Focus_Score"), errors="coerce").fillna(0) >= 75)
        & (pd.to_numeric(frame.get("Behavioral_Alignment"), errors="coerce").fillna(0) >= 75)
    )
    segments = _contiguous_segments(frame, stable_mask)
    if segments:
        return max(segments, key=lambda segment: segment["end_sample"] - segment["start_sample"])
    return _slice_segment(frame, 1, min(24, len(frame.index)), source="stable_fallback")


def _select_load_rising_segment(frame: pd.DataFrame, start_after: int, hint_anchor: int | None = None) -> dict[str, Any] | None:
    if frame.empty:
        return None
    anchor = int(hint_anchor or start_after)
    search_start = max(1, anchor - 8)
    search_end = min(_safe_int(frame["__sample"].max(), default=0), anchor + 36)
    candidates: list[tuple[float, dict[str, Any]]] = []
    broad_candidates: list[tuple[float, dict[str, Any]]] = []
    for start_sample in range(search_start, max(search_start + 1, search_end - 10)):
        segment = _slice_segment(frame, start_sample, min(start_sample + 14, search_end), source="load_rising_window")
        if not segment:
            continue
        rows = segment["rows"]
        load_values = pd.to_numeric(rows.get("Cognitive_Load"), errors="coerce").fillna(0)
        align_values = pd.to_numeric(rows.get("Behavioral_Alignment"), errors="coerce").fillna(0)
        focus_values = pd.to_numeric(rows.get("Focus_Score"), errors="coerce").fillna(0)
        switch_values = pd.to_numeric(rows.get("Switching_Index"), errors="coerce").fillna(0)
        load_gain = float(load_values.iloc[-1] - load_values.iloc[0])
        align_drop = float(align_values.iloc[0] - align_values.iloc[-1])
        focus_drop = float(focus_values.iloc[0] - focus_values.iloc[-1])
        load_mean = float(load_values.mean())
        align_mean = float(align_values.mean())
        focus_mean = float(focus_values.mean())
        switch_mean = float(switch_values.mean())
        score = (
            max(0.0, 42.0 - abs(load_mean - 52.0)) * 1.3
            + max(0.0, 28.0 - abs(align_mean - 54.0))
            + max(0.0, 28.0 - abs(focus_mean - 52.0))
            + (load_gain * 1.2)
            + (align_drop * 0.4)
            + (focus_drop * 0.4)
            - (switch_mean * 0.18)
        )
        broad_candidates.append((score, segment))
        if 30.0 <= load_mean <= 78.0 and align_mean >= 35.0 and focus_mean >= 35.0:
            candidates.append((score, segment))
    if candidates:
        return max(candidates, key=lambda item: item[0])[1]
    if broad_candidates:
        return max(broad_candidates, key=lambda item: item[0])[1]
    return _slice_segment(frame, max(1, anchor - 6), min(anchor + 8, len(frame.index)), source="load_rising_fallback")


def _first_long_off_task_start(frame: pd.DataFrame, start_after: int) -> int | None:
    hints = _normalize_state(frame.get("State_Hint"))
    segments = _contiguous_segments(
        frame,
        hints.eq("off_task_risk") & (frame["__sample"] >= int(start_after)),
    )
    qualified = [segment for segment in segments if (segment["end_sample"] - segment["start_sample"] + 1) >= 12]
    if qualified:
        return min(segment["start_sample"] for segment in qualified)
    return None


def _select_productive_segment(frame: pd.DataFrame, start_after: int, stop_before: int | None = None) -> dict[str, Any] | None:
    if frame.empty:
        return None
    start_sample = max(1, int(start_after))
    end_limit = min(
        _safe_int(frame["__sample"].max(), default=0),
        (int(stop_before) - 1) if stop_before else _safe_int(frame["__sample"].max(), default=0),
        start_sample + 84,
    )
    if end_limit <= start_sample:
        end_limit = min(_safe_int(frame["__sample"].max(), default=0), start_sample + 20)
    best_segment = None
    best_score = float("-inf")
    for candidate_start in range(start_sample, max(start_sample + 1, end_limit - 10)):
        segment = _slice_segment(frame, candidate_start, min(candidate_start + 14, end_limit), source="productive_window")
        if not segment:
            continue
        rows = segment["rows"]
        load_mean = float(pd.to_numeric(rows.get("Cognitive_Load"), errors="coerce").fillna(0).mean())
        align_mean = float(pd.to_numeric(rows.get("Behavioral_Alignment"), errors="coerce").fillna(0).mean())
        focus_mean = float(pd.to_numeric(rows.get("Focus_Score"), errors="coerce").fillna(0).mean())
        switch_mean = float(pd.to_numeric(rows.get("Switching_Index"), errors="coerce").fillna(0).mean())
        fatigue_mean = float(pd.to_numeric(rows.get("Fatigue_Risk"), errors="coerce").fillna(0).mean())
        stability_mean = float(pd.to_numeric(rows.get("Stability"), errors="coerce").fillna(0).mean())
        score = (
            max(0.0, 40.0 - abs(load_mean - 60.0))
            + max(0.0, 35.0 - abs(align_mean - 55.0))
            + max(0.0, 25.0 - abs(focus_mean - 45.0))
            + (stability_mean * 0.12)
            - (switch_mean * 0.45)
            - (fatigue_mean * 0.18)
        )
        if load_mean >= 45 and align_mean >= 40 and focus_mean >= 35 and score > best_score:
            best_score = score
            best_segment = segment
    return best_segment


def _select_off_task_segment(frame: pd.DataFrame, start_after: int, fallback_event: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if frame.empty:
        return None
    hints = _normalize_state(frame.get("State_Hint"))
    segments = _contiguous_segments(
        frame,
        hints.eq("off_task_risk") & (frame["__sample"] >= int(start_after)),
    )
    if segments:
        def score(segment: dict[str, Any]) -> float:
            rows = segment["rows"]
            focus_mean = float(pd.to_numeric(rows.get("Focus_Score"), errors="coerce").fillna(0).mean())
            load_mean = float(pd.to_numeric(rows.get("Cognitive_Load"), errors="coerce").fillna(0).mean())
            switch_mean = float(pd.to_numeric(rows.get("Switching_Index"), errors="coerce").fillna(0).mean())
            length = segment["end_sample"] - segment["start_sample"] + 1
            return (length * 0.5) + load_mean + switch_mean - (focus_mean * 0.4)
        return max(segments, key=score)
    if isinstance(fallback_event, dict):
        return _slice_segment(
            frame,
            _safe_int(fallback_event.get("start_sample"), default=1),
            _safe_int(fallback_event.get("end_sample"), default=1),
            source="difficulty_event_fallback",
        )
    return None


def _select_recovery_segment(frame: pd.DataFrame, start_after: int) -> dict[str, Any] | None:
    if frame.empty:
        return None
    hints = _normalize_state(frame.get("State_Hint"))
    guidance = _normalize_state(frame.get("Guidance"))
    stable_mask = hints.eq("stable") & (frame["__sample"] >= int(start_after))
    segments = _contiguous_segments(frame, stable_mask)
    if segments:
        def score(segment: dict[str, Any]) -> float:
            rows = segment["rows"]
            focus_mean = float(pd.to_numeric(rows.get("Focus_Score"), errors="coerce").fillna(0).mean())
            align_mean = float(pd.to_numeric(rows.get("Behavioral_Alignment"), errors="coerce").fillna(0).mean())
            stability_mean = float(pd.to_numeric(rows.get("Stability"), errors="coerce").fillna(0).mean())
            load_mean = float(pd.to_numeric(rows.get("Cognitive_Load"), errors="coerce").fillna(0).mean())
            switch_mean = float(pd.to_numeric(rows.get("Switching_Index"), errors="coerce").fillna(0).mean())
            rows_guidance = _normalize_state(rows.get("Guidance"))
            recovery_bonus = 18.0 if rows_guidance.str.contains("recovery", regex=False).any() else 0.0
            return focus_mean + align_mean + (stability_mean * 0.35) - load_mean - (switch_mean * 0.5) + recovery_bonus
        return max(segments, key=score)
    recovery_mask = guidance.str.contains("recovery", regex=False) & (frame["__sample"] >= int(start_after))
    recovery_segments = _contiguous_segments(frame, recovery_mask)
    if recovery_segments:
        return max(recovery_segments, key=lambda segment: segment["end_sample"] - segment["start_sample"])
    return _slice_segment(frame, max(start_after, _safe_int(frame["__sample"].max(), default=1) - 24), _safe_int(frame["__sample"].max(), default=1), source="recovery_fallback")


def _load_validation_frame(features_path: Path, session_id: str) -> pd.DataFrame:
    frame = _read_csv(features_path)
    if frame.empty:
        return pd.DataFrame()
    filtered = frame[
        frame.get("session_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip() == str(session_id).strip()
    ].copy()
    if filtered.empty:
        return pd.DataFrame()
    return filtered.sort_values(["start_sample", "end_sample"], kind="stable").reset_index(drop=True)


def _validation_window_for_segment(features_frame: pd.DataFrame, start_sample: int, end_sample: int) -> dict[str, Any] | None:
    if features_frame.empty:
        return None
    best_row = None
    best_overlap = 0
    for _, row in features_frame.iterrows():
        overlap = _window_overlap(
            _safe_int(row.get("start_sample"), default=0),
            _safe_int(row.get("end_sample"), default=0),
            int(start_sample),
            int(end_sample),
        )
        if overlap > best_overlap:
            best_overlap = overlap
            best_row = row
    if best_row is None or best_overlap <= 0:
        return None
    prediction = rule_baseline(best_row)
    return {
        "start_sample": _safe_int(best_row.get("start_sample"), default=0),
        "end_sample": _safe_int(best_row.get("end_sample"), default=0),
        "predicted_label": prediction["label"],
        "confidence": prediction["confidence"],
        "evidence": prediction["evidence"],
        "uncertainty_reason": prediction["uncertainty_reason"],
    }


def _segment_metrics(rows: pd.DataFrame) -> dict[str, Any]:
    hints = _normalize_state(rows.get("State_Hint"))
    guidance = rows.get("Guidance", pd.Series(dtype=str)).fillna("").astype(str).str.strip()
    metrics = {
        "samples": int(len(rows.index)),
        "avg_load": round(_safe_float(pd.to_numeric(rows.get("Cognitive_Load"), errors="coerce").mean()), 1),
        "avg_focus": round(_safe_float(pd.to_numeric(rows.get("Focus_Score"), errors="coerce").mean()), 1),
        "avg_alignment": round(_safe_float(pd.to_numeric(rows.get("Behavioral_Alignment"), errors="coerce").mean()), 1),
        "avg_switching": round(_safe_float(pd.to_numeric(rows.get("Switching_Index"), errors="coerce").mean()), 1),
        "avg_fatigue": round(_safe_float(pd.to_numeric(rows.get("Fatigue_Risk"), errors="coerce").mean()), 1),
        "avg_stability": round(_safe_float(pd.to_numeric(rows.get("Stability"), errors="coerce").mean()), 1),
        "dominant_state_hint": hints.mode().iloc[0] if not hints.mode().empty else "",
        "dominant_guidance": guidance.mode().iloc[0] if not guidance.mode().empty else "",
    }
    return metrics


def _overlapping_events(events: list[dict[str, Any]], start_sample: int, end_sample: int) -> list[dict[str, Any]]:
    overlaps = []
    for event in events:
        if not isinstance(event, dict):
            continue
        overlap = _window_overlap(
            _safe_int(event.get("start_sample"), default=0),
            _safe_int(event.get("end_sample"), default=0),
            int(start_sample),
            int(end_sample),
        )
        if overlap > 0:
            overlaps.append(event)
    return overlaps


def _time_range(segment: dict[str, Any]) -> str:
    return (
        f"{segment.get('start_timestamp', '--')} - {segment.get('end_timestamp', '--')} "
        f"(samples {segment.get('start_sample', '--')}-{segment.get('end_sample', '--')})"
    )


def _what_user_sees(stage_key: str, metrics: dict[str, Any]) -> str:
    if stage_key == "stable_focus":
        return "The HUD looks calm: focus and alignment stay high, switching stays low, and the guidance remains steady."
    if stage_key == "load_rising":
        return "The on-screen guidance starts warning about drift while load climbs and focus begins to fall."
    if stage_key == "productive_struggle":
        return "The work still looks hard, but the learner has not fully disengaged yet. This is the best replay window for a concept explanation."
    if stage_key == "off_task_risk":
        return "The session looks fragmented: focus and alignment are suppressed while switching and strain dominate the window."
    return "The later samples show the pattern settling down again, with steadier guidance and a more review-ready rhythm."


def _what_system_infers(stage_key: str, metrics: dict[str, Any], validation_window: dict[str, Any] | None) -> str:
    validation_phrase = ""
    if isinstance(validation_window, dict):
        validation_phrase = (
            f" Optional state-window evidence overlaps this segment and reads as "
            f"{str(validation_window.get('predicted_label', 'stable_focus')).replace('_', ' ')} "
            f"at about {int(round(_safe_float(validation_window.get('confidence', 0.0)) * 100))}% confidence."
        )
    if stage_key == "stable_focus":
        return (
            "The learning-state proxy suggests a relatively settled baseline: low load, high alignment, and one stable target."
            + validation_phrase
        )
    if stage_key == "load_rising":
        return (
            "The proxy suggests regulation pressure is increasing. This should be described as rising load and drift risk, not as precise attention detection."
            + validation_phrase
        )
    if stage_key == "productive_struggle":
        return (
            "This window only briefly resembles productive struggle: challenge is elevated, but enough alignment remains to justify a replay-focused explanation."
            + validation_phrase
        )
    if stage_key == "off_task_risk":
        return (
            "The proxy suggests the task is no longer well held. Off-task risk and overload dominate this stage of the narrative."
            + validation_phrase
        )
    return (
        "The proxy suggests recovery is underway and the study pattern is becoming easier to review and coach."
        + validation_phrase
    )


def _speaker_notes(stage_key: str, metrics: dict[str, Any], reflection_summary: dict[str, Any]) -> str:
    encouragement = str(reflection_summary.get("encouragement", "")).strip()
    if stage_key == "stable_focus":
        return "Open the demo here to establish the baseline. Emphasize that the system first looks for a stable learning-state proxy before it interprets difficulty."
    if stage_key == "load_rising":
        return "Explain that the system is now flagging a rising-load pattern. Use conservative wording: the module sees proxy evidence of drift pressure, not hidden mental state."
    if stage_key == "productive_struggle":
        return "This is the teaching moment. Show that the system can separate a hard-but-still-held segment from a purely fragmented one."
    if stage_key == "off_task_risk":
        return "Use this stage to justify the difficulty marker and the review page. This is where replay, heatmap review, and catch-up guidance become easy to explain."
    closing = "Close on recovery so the story is not only about failure. The system should look like a coach for adjustment, not only a detector for mistakes."
    if encouragement:
        return f"{closing} {encouragement}"
    return closing


def _build_evidence_lines(
    stage_key: str,
    segment: dict[str, Any],
    metrics: dict[str, Any],
    events: list[dict[str, Any]],
    validation_window: dict[str, Any] | None,
) -> list[str]:
    lines = [
        f"Time range: {_time_range(segment)}.",
        (
            f"Key metrics: load {metrics['avg_load']}, focus {metrics['avg_focus']}, alignment {metrics['avg_alignment']}, "
            f"switching {metrics['avg_switching']}, fatigue {metrics['avg_fatigue']}, stability {metrics['avg_stability']}."
        ),
    ]
    if metrics.get("dominant_state_hint"):
        lines.append(f"Dominant proxy hint: {str(metrics['dominant_state_hint']).replace('_', ' ')}.")
    if metrics.get("dominant_guidance"):
        lines.append(f"Observed guidance: {metrics['dominant_guidance']}")
    overlaps = _overlapping_events(events, segment["start_sample"], segment["end_sample"])
    if overlaps:
        labels = ", ".join(f"D{_safe_int(event.get('event_id'), default=0)} ({event.get('severity', 'medium')})" for event in overlaps)
        lines.append(f"Overlaps difficulty markers: {labels}.")
    if isinstance(validation_window, dict):
        evidence = validation_window.get("evidence", [])
        evidence_text = "; ".join(str(item).strip() for item in evidence if str(item).strip()) if isinstance(evidence, list) else ""
        lines.append(
            f"Optional validation window: {str(validation_window.get('predicted_label', '')).replace('_', ' ')} "
            f"at about {int(round(_safe_float(validation_window.get('confidence', 0.0)) * 100))}% confidence."
        )
        if evidence_text:
            lines.append(f"Validation evidence: {evidence_text}.")
    else:
        lines.append("No matching state-window validation segment was available for this stage, so the narrative falls back to review and raw session cues.")
    return lines


def _stage_payload(
    stage_key: str,
    segment: dict[str, Any] | None,
    events: list[dict[str, Any]],
    reflection_summary: dict[str, Any],
    validation_frame: pd.DataFrame,
) -> dict[str, Any]:
    if not segment:
        return {
            "stage_key": stage_key,
            "stage_title": STAGE_TITLES[stage_key],
            "time_range": "Unavailable",
            "start_sample": None,
            "end_sample": None,
            "key_metrics": {},
            "what_user_sees": "No matching segment was available for this stage in the current dataset.",
            "what_system_infers": "No proxy inference is available for this stage because the dataset does not include a matching segment.",
            "speaker_notes": "If this stage is missing during a live demo, explain that the storyboard is conservative and only narrates segments that the current session actually contains.",
            "evidence": ["Stage unavailable in current dataset."],
            "transition_to_next_stage": TRANSITIONS[stage_key],
        }
    rows = segment["rows"]
    metrics = _segment_metrics(rows)
    validation_window = _validation_window_for_segment(validation_frame, segment["start_sample"], segment["end_sample"])
    return {
        "stage_key": stage_key,
        "stage_title": STAGE_TITLES[stage_key],
        "time_range": _time_range(segment),
        "start_sample": segment["start_sample"],
        "end_sample": segment["end_sample"],
        "key_metrics": metrics,
        "what_user_sees": _what_user_sees(stage_key, metrics),
        "what_system_infers": _what_system_infers(stage_key, metrics, validation_window),
        "speaker_notes": _speaker_notes(stage_key, metrics, reflection_summary),
        "evidence": _build_evidence_lines(stage_key, segment, metrics, events, validation_window),
        "transition_to_next_stage": TRANSITIONS[stage_key],
    }


def _empty_storyboard_payload(dataset: str, session_id: str = "") -> dict[str, Any]:
    return {
        "status": "ok",
        "empty": True,
        "dataset": dataset,
        "session_id": session_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "title": "Learning State Guardian Demo Storyboard",
        "story_summary": "No demo session data is available yet. Generate demo assets or run a local session first, then rebuild the storyboard.",
        "module_boundary": (
            "This storyboard uses conservative learning-state proxy framing. It does not claim precise attention detection or psychological diagnosis."
        ),
        "reflection_summary": {},
        "assets": {},
        "stages": [
            _stage_payload(stage_key, None, [], {}, pd.DataFrame())
            for stage_key in STAGE_ORDER
        ],
    }


def build_demo_storyboard(
    logger,
    reflection_coach,
    dataset: str = "demo",
    session_id: str | None = None,
    features_path: Path | str | None = None,
) -> dict[str, Any]:
    dataset_name = str(dataset or "demo").strip().lower() or "demo"
    review_payload = logger.build_review_payload(session_id=session_id, dataset=dataset_name)
    report_path, difficulty_path = _resolve_paths(dataset_name)
    report_frame = _prepare_report_frame(_read_csv(report_path), str(review_payload.get("session_id", session_id or "")).strip())
    difficulty_frame = _prepare_events_frame(_read_csv(difficulty_path), str(review_payload.get("session_id", session_id or "")).strip())
    if report_frame.empty and difficulty_frame.empty:
        return _empty_storyboard_payload(dataset_name, str(review_payload.get("session_id", session_id or "")).strip())

    events, highlight_event = _event_lookup(review_payload)
    validation_frame = _load_validation_frame(Path(features_path or DEFAULT_FEATURES_PATH), str(review_payload.get("session_id", session_id or "")).strip())
    validation_summary = {
        "status": "ok",
        "features_available": bool(not validation_frame.empty),
    }
    reflection_summary = reflection_coach.build_review_summary_payload(
        review_payload=review_payload,
        difficulty_events=events,
        validation_summary=validation_summary,
        session_id=review_payload.get("session_id") or session_id,
        dataset=dataset_name,
        event_id=highlight_event.get("event_id") if isinstance(highlight_event, dict) else None,
    )

    stable_segment = _select_stable_segment(report_frame)
    first_load_hint = None
    hints = _normalize_state(report_frame.get("State_Hint"))
    load_hint_rows = report_frame[hints.eq("load_rising")]
    if not load_hint_rows.empty:
        first_load_hint = _safe_int(load_hint_rows.iloc[0].get("__sample"), default=0)
    load_segment = _select_load_rising_segment(
        report_frame,
        start_after=(stable_segment["end_sample"] + 1) if stable_segment else 1,
        hint_anchor=first_load_hint or (_safe_int(highlight_event.get("start_sample"), default=0) if isinstance(highlight_event, dict) else None),
    )
    if stable_segment and load_segment and load_segment["start_sample"] <= stable_segment["end_sample"]:
        trimmed_stable = _slice_segment(
            report_frame,
            stable_segment["start_sample"],
            max(stable_segment["start_sample"], load_segment["start_sample"] - 1),
            source="stable_trimmed_for_transition",
        )
        if trimmed_stable and (trimmed_stable["end_sample"] - trimmed_stable["start_sample"] + 1) >= 12:
            stable_segment = trimmed_stable
    off_task_anchor = _first_long_off_task_start(report_frame, (load_segment["end_sample"] + 1) if load_segment else 1)
    productive_segment = _select_productive_segment(
        report_frame,
        start_after=(load_segment["end_sample"] + 1) if load_segment else 1,
        stop_before=off_task_anchor,
    )
    off_task_segment = _select_off_task_segment(
        report_frame,
        start_after=(productive_segment["end_sample"] + 1) if productive_segment else ((load_segment["end_sample"] + 1) if load_segment else 1),
        fallback_event=highlight_event,
    )
    recovery_segment = _select_recovery_segment(
        report_frame,
        start_after=(off_task_segment["end_sample"] + 1) if off_task_segment else max(1, _safe_int(report_frame["__sample"].max(), default=1) - 30),
    )

    segments = {
        "stable_focus": stable_segment,
        "load_rising": load_segment,
        "productive_struggle": productive_segment,
        "off_task_risk": off_task_segment,
        "recovery": recovery_segment,
    }

    story_summary = str(reflection_summary.get("session_summary", "")).strip() or (
        "This storyboard follows a conservative learning-state proxy narrative from stable setup, through difficulty, into recovery."
    )
    return {
        "status": "ok",
        "empty": False,
        "dataset": dataset_name,
        "session_id": str(review_payload.get("session_id", session_id or "")).strip(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "title": "Learning State Guardian Demo Storyboard",
        "story_summary": story_summary,
        "module_boundary": (
            "This storyboard is a conservative explanation layer built from learning-state proxies, difficulty markers, review cues, and optional validation evidence. "
            "It should not be described as precise attention detection."
        ),
        "reflection_summary": {
            "session_summary": reflection_summary.get("session_summary"),
            "encouragement": reflection_summary.get("encouragement"),
        },
        "assets": review_payload.get("assets", {}),
        "stages": [
            _stage_payload(stage_key, segments.get(stage_key), events, reflection_summary, validation_frame)
            for stage_key in STAGE_ORDER
        ],
    }


def build_demo_storyboard_markdown(payload: dict[str, Any], report_source: str) -> str:
    lines = [
        "# Demo Storyboard",
        "",
        f"- Generated at: {payload.get('generated_at', datetime.now().isoformat(timespec='seconds'))}",
        f"- Dataset: {payload.get('dataset', 'demo')}",
        f"- Session ID: {payload.get('session_id', '--') or '--'}",
        f"- Source report: {report_source}",
        "",
        f"> {payload.get('module_boundary', 'This storyboard uses conservative learning-state proxy framing.')}",
        "",
        "## Story Summary",
        "",
        str(payload.get("story_summary", "No storyboard summary is available yet.")).strip() or "No storyboard summary is available yet.",
        "",
    ]
    for stage in payload.get("stages", []):
        lines.append(f"## {stage.get('stage_title', 'Storyboard Stage')}")
        lines.append("")
        lines.append(f"- Time range: {stage.get('time_range', 'Unavailable')}")
        lines.append(f"- What user sees: {stage.get('what_user_sees', 'No detail available.')}")
        lines.append(f"- What system infers: {stage.get('what_system_infers', 'No detail available.')}")
        lines.append(f"- Speaker notes: {stage.get('speaker_notes', 'No speaker note available.')}")
        metrics = stage.get("key_metrics", {})
        if isinstance(metrics, dict) and metrics:
            lines.append("- Key metrics:")
            lines.append(f"  - Avg load: {metrics.get('avg_load', '--')}")
            lines.append(f"  - Avg focus: {metrics.get('avg_focus', '--')}")
            lines.append(f"  - Avg alignment: {metrics.get('avg_alignment', '--')}")
            lines.append(f"  - Avg switching: {metrics.get('avg_switching', '--')}")
            lines.append(f"  - Avg fatigue: {metrics.get('avg_fatigue', '--')}")
            lines.append(f"  - Avg stability: {metrics.get('avg_stability', '--')}")
            lines.append(f"  - Dominant proxy hint: {metrics.get('dominant_state_hint', '--')}")
        evidence = stage.get("evidence", [])
        lines.append("- Evidence:")
        if isinstance(evidence, list) and evidence:
            for item in evidence:
                lines.append(f"  - {str(item).strip()}")
        else:
            lines.append("  - No stage evidence was available.")
        lines.append(f"- Transition to next stage: {stage.get('transition_to_next_stage', '')}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"
