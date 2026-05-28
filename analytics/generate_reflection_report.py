from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

import pandas as pd

from core.reflection_coach import ReflectionCoach
from core.state_classifier import rule_baseline
from utils.storage import DataLogger


DEFAULT_FEATURES_PATH = ROOT / "data" / "state_window_features.csv"
DEFAULT_OUTPUT_PATH = ROOT / "exports" / "reflection_report.md"
DEFAULT_LIVE_REPORT_PATH = ROOT / "data" / "study_report.csv"
DEFAULT_DEMO_REPORT_PATH = ROOT / "data" / "demo_study_report.csv"


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


def _window_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> int:
    return max(0, min(end_a, end_b) - max(start_a, start_b) + 1)


def _title_case_label(value: Any) -> str:
    return " ".join(
        part.capitalize()
        for part in str(value or "").replace("-", "_").split("_")
        if part
    )


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    return frame if not frame.empty else pd.DataFrame(columns=frame.columns.tolist())


def _serialize_validation_window(row: pd.Series) -> dict[str, Any]:
    prediction = rule_baseline(row)
    return {
        "session_id": str(row.get("session_id", "")).strip(),
        "start_sample": _safe_int(row.get("start_sample"), default=0),
        "end_sample": _safe_int(row.get("end_sample"), default=0),
        "task_mode_majority": str(row.get("task_mode_majority", "")).strip(),
        "predicted_label": prediction["label"],
        "confidence": prediction["confidence"],
        "evidence": prediction["evidence"],
        "uncertainty_reason": prediction["uncertainty_reason"],
        "model": prediction["model"],
    }


def _pick_selected_event(review_payload: dict[str, Any], event_id: str | None = None) -> dict[str, Any] | None:
    requested = _safe_int(event_id, default=0)
    events = review_payload.get("events", []) if isinstance(review_payload, dict) else []
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            if requested and _safe_int(event.get("event_id"), default=0) == requested:
                return event
    highlight_event = review_payload.get("highlight_event") if isinstance(review_payload, dict) else None
    if isinstance(highlight_event, dict) and highlight_event:
        return highlight_event
    if isinstance(events, list):
        for event in events:
            if isinstance(event, dict):
                return event
    return None


def _load_validation_summary(
    features_path: Path,
    session_id: str | None = None,
    start_sample: int | None = None,
    end_sample: int | None = None,
    limit: int = 6,
) -> dict[str, Any]:
    frame = _load_csv(features_path)
    if frame.empty:
        return {
            "status": "ok",
            "features_available": False,
            "selected_window": None,
            "recent_windows": [],
            "features_path": str(features_path.relative_to(ROOT)),
        }

    if session_id:
        frame = frame[
            frame.get("session_id", pd.Series(dtype=str)).fillna("").astype(str).str.strip() == str(session_id).strip()
        ].copy()
    if frame.empty:
        return {
            "status": "ok",
            "features_available": False,
            "selected_window": None,
            "recent_windows": [],
            "features_path": str(features_path.relative_to(ROOT)),
        }

    frame = frame.sort_values(["session_id", "start_sample", "end_sample"], kind="stable").reset_index(drop=True)
    selected_row = None
    if start_sample is not None and end_sample is not None:
        best_overlap = 0
        for _, row in frame.iterrows():
            overlap = _window_overlap(
                _safe_int(row.get("start_sample"), default=0),
                _safe_int(row.get("end_sample"), default=0),
                _safe_int(start_sample, default=0),
                _safe_int(end_sample, default=0),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                selected_row = row
    if selected_row is None:
        selected_row = frame.iloc[-1]

    recent_windows = [
        _serialize_validation_window(row)
        for _, row in frame.tail(max(1, min(int(limit or 6), 12))).iterrows()
    ]
    return {
        "status": "ok",
        "features_available": True,
        "selected_window": _serialize_validation_window(selected_row),
        "recent_windows": recent_windows,
        "features_path": str(features_path.relative_to(ROOT)),
    }


def _resolve_dataset(dataset_arg: str) -> str:
    normalized = str(dataset_arg or "auto").strip().lower()
    if normalized in {"live", "demo"}:
        return normalized
    if DEFAULT_LIVE_REPORT_PATH.exists() and DEFAULT_LIVE_REPORT_PATH.stat().st_size > 10:
        return "live"
    if DEFAULT_DEMO_REPORT_PATH.exists() and DEFAULT_DEMO_REPORT_PATH.stat().st_size > 10:
        return "demo"
    return "live"


def _format_markdown(
    payload: dict[str, Any],
    dataset: str,
    report_source: str,
    selected_event: dict[str, Any] | None,
    validation_summary: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("# Reflection Coach Report")
    lines.append("")
    lines.append(f"- Generated at: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Dataset: {dataset}")
    lines.append(f"- Source report: {report_source}")
    lines.append(f"- Session ID: {payload.get('session_id') or '--'}")
    lines.append(f"- Selected event: D{_safe_int(selected_event.get('event_id'), default=0)}" if isinstance(selected_event, dict) else "- Selected event: none")
    lines.append(f"- State window features: {'available' if validation_summary.get('features_available') else 'not available'}")
    lines.append("")
    lines.append("> This reflection summary is based on learning-state proxies, difficulty events, and study context. It should not be read as precise attention detection or psychological diagnosis.")
    lines.append("")
    lines.append("## Session Summary")
    lines.append("")
    lines.append(payload.get("session_summary", "No session summary is available yet."))
    lines.append("")
    lines.append("## Key Moments")
    lines.append("")
    key_moments = payload.get("key_moments", [])
    if key_moments:
        for index, moment in enumerate(key_moments[:3], start=1):
            title = str(moment.get("title", f"Moment {index}")).strip() or f"Moment {index}"
            source = str(moment.get("source", "session_summary")).strip() or "session_summary"
            window = str(moment.get("window", "session-wide")).strip() or "session-wide"
            lines.append(f"{index}. **{title}** (`{source}`, `{window}`)")
            lines.append(f"   {str(moment.get('detail', '')).strip() or 'No extra detail available.'}")
    else:
        lines.append("1. No key moment was generated yet. Run a live or demo session first.")
    lines.append("")
    lines.append("## Reflection Questions")
    lines.append("")
    questions = payload.get("reflection_questions", [])
    if questions:
        for question in questions[:3]:
            lines.append(f"- {str(question).strip()}")
    else:
        lines.append("- No reflection questions are available yet because the session evidence is still missing.")
    lines.append("")
    lines.append("## Next Actions")
    lines.append("")
    actions = payload.get("next_actions", [])
    if actions:
        for action in actions[:3]:
            title = str(action.get("title", "Next action")).strip() or "Next action"
            detail = str(action.get("detail", "")).strip() or "No action detail is available yet."
            success_marker = str(action.get("success_marker", "")).strip()
            lines.append(f"- **{title}**: {detail}")
            if success_marker:
                lines.append(f"  Success marker: {success_marker}")
    else:
        lines.append("- No next action is available yet.")
    lines.append("")
    lines.append("## Encouragement")
    lines.append("")
    lines.append(payload.get("encouragement", "Use the next session as a comparison point rather than treating one report as a final verdict."))
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(f"- Module boundary: {payload.get('module_boundary', 'Reflection Coach is a lightweight post-session reflection aid.')}")
    if not validation_summary.get("features_available"):
        lines.append("- State-window evidence was unavailable for this run, so the report fell back to review summary and difficulty-event cues only.")
    if not isinstance(selected_event, dict):
        lines.append("- No sustained difficulty event was available, so the report emphasized session-wide rhythm, guidance, and proxy signals.")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local Reflection Coach markdown report.")
    parser.add_argument("--dataset", default="auto", choices=["auto", "live", "demo"], help="Pick the live or demo study report source.")
    parser.add_argument("--session-id", default="", help="Optional session ID override.")
    parser.add_argument("--event-id", default="", help="Optional difficulty event ID override.")
    parser.add_argument("--features", default=str(DEFAULT_FEATURES_PATH), help="Path to state window features CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Path to the markdown report output.")
    args = parser.parse_args()

    dataset = _resolve_dataset(args.dataset)
    output_path = Path(args.output)
    features_path = Path(args.features)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger = DataLogger()
    coach = ReflectionCoach(logger)
    review_payload = logger.build_review_payload(session_id=args.session_id or None, dataset=dataset)
    selected_event = _pick_selected_event(review_payload, event_id=args.event_id or None)
    validation_summary = _load_validation_summary(
        features_path=features_path,
        session_id=review_payload.get("session_id") or args.session_id or None,
        start_sample=_safe_int(selected_event.get("start_sample"), default=0) if isinstance(selected_event, dict) else None,
        end_sample=_safe_int(selected_event.get("end_sample"), default=0) if isinstance(selected_event, dict) else None,
        limit=6,
    )
    reflection_summary = coach.build_review_summary_payload(
        review_payload=review_payload,
        difficulty_events=review_payload.get("events", []),
        validation_summary=validation_summary,
        session_id=review_payload.get("session_id") or args.session_id or None,
        dataset=dataset,
        event_id=args.event_id or None,
    )

    report_source = "data/demo_study_report.csv" if dataset == "demo" else "data/study_report.csv"
    markdown = _format_markdown(
        reflection_summary,
        dataset=dataset,
        report_source=report_source,
        selected_event=selected_event,
        validation_summary=validation_summary,
    )
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Reflection report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
