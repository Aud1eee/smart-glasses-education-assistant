import json
import os
import re
import sys
from datetime import datetime
from html import escape as html_escape
import time

import bootstrap_windows_runtime  # noqa: F401
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory, Response
from flask_cors import CORS

from core.difficulty_marker import DifficultyEventMarker
from core.edu import EduEngine
from core.focus_session import FocusSessionEngine
from core.multimodal_schema import build_multimodal_blueprint
from core.posture import PostureEngine
from core.presentation_companion import PresentationCompanion
from core.reflection_coach import ReflectionCoach
from core.rokid_adapter import (
    build_rokid_adapter_blueprint,
    build_rokid_packet,
    build_simulator_packet,
)
from core.rokid_frame_adapter import RokidFrameAdapter
from core.vision import VisionEngine
from utils.storage import DataLogger


load_dotenv()

app = Flask(__name__, template_folder="web", static_folder="web")
CORS(app)
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
REFLECTION_SNAPSHOT_DIR = os.path.join(EXPORT_DIR, "reflection_snapshots")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROKID_PROFILE_STORE_PATH = os.path.join(PROJECT_ROOT, "data", "rokid_scene_profiles.json")
REFLECTION_RUNTIME_VERSION = "reflection-runtime-info-2026-05-19-v1"
REFLECTION_SNAPSHOT_EXPORTER_VERSION = "reflection-html-card-2026-05-19-v1"
APP_BOOTED_AT = datetime.now().isoformat(timespec="seconds")

logger = DataLogger()
posture = PostureEngine()
vision = VisionEngine()
rokid_frame_adapter = RokidFrameAdapter()
edu = EduEngine(logger.vocab_path)
focus_session = FocusSessionEngine()
reflection_coach = ReflectionCoach(logger)
presentation_companion = PresentationCompanion()
difficulty_marker = DifficultyEventMarker()
auto_recall_enabled = os.getenv("ENABLE_AUTO_RECALL", "0").lower() in {"1", "true", "yes", "on"}
sample_counter = 0
last_posture_at = None

pending_card = {"word": "", "trans": "", "type": ""}
latest_session = focus_session.update({
    "cognitive_load": 0,
    "load_level": "low",
    "focus_score": 100,
})
latest_difficulty = {
    "active_event": None,
    "completed_event": None,
    "last_event": None,
    "event_count": 0,
}
latest_input = {
    "source": "simulator",
    "device_profile": "simulator-rokid-proxy",
    "tracking_state": "warmup",
    "tracking_confidence": None,
    "tracking_uncertainty": 0.0,
    "face_present": None,
    "scene_content_score": 0.0,
    "scene_text_score": 0.0,
    "scene_stability_score": 0.0,
    "scene_switch_rate": 0.0,
    "study_surface_score": 0.0,
    "scene_lock_score": 0.0,
    "blur_score": 0.0,
    "brightness_score": 0.0,
    "motion_source": "default",
    "pose_source": "simulator",
    "frame_source": "simulator",
    "timestamp_ms": None,
}

ROKID_SCENE_PRESETS = {
    "balanced-reading": {
        "label": "Balanced Reading",
        "summary": "General first-person reading baseline for books, slides, and mixed text surfaces.",
        "posture": {
            "content_expectation_bias": 0.0,
            "surface_expectation_bias": 2.0,
            "signal_uncertainty_floor": 54.0,
            "off_task_switch_floor": 52.0,
            "productive_alignment_floor": 76.0,
            "productive_lock_floor": 34.0,
        },
        "frame_adapter": {
            "content_sparse_floor": 18.0,
            "scene_locked_surface_floor": 54.0,
            "scene_locked_lock_floor": 58.0,
            "lock_switch_ceiling": 36.0,
        },
    },
    "screen-lecture": {
        "label": "Screen Lecture",
        "summary": "For PPT or teacher-screen viewing where content is stable but less text-dense than books.",
        "posture": {
            "content_expectation_bias": -4.0,
            "surface_expectation_bias": 0.0,
            "signal_uncertainty_floor": 58.0,
            "off_task_switch_floor": 48.0,
            "productive_alignment_floor": 72.0,
            "productive_lock_floor": 28.0,
        },
        "frame_adapter": {
            "content_sparse_floor": 14.0,
            "scene_locked_surface_floor": 48.0,
            "scene_locked_lock_floor": 52.0,
            "lock_switch_ceiling": 40.0,
        },
    },
    "notes-switching": {
        "label": "Notes Switching",
        "summary": "For note-taking with frequent book-screen or page-note switching; reduces false off-task triggers.",
        "posture": {
            "content_expectation_bias": -2.0,
            "surface_expectation_bias": -2.0,
            "signal_uncertainty_floor": 60.0,
            "off_task_switch_floor": 62.0,
            "productive_alignment_floor": 70.0,
            "productive_lock_floor": 24.0,
        },
        "frame_adapter": {
            "content_sparse_floor": 12.0,
            "scene_locked_surface_floor": 44.0,
            "scene_locked_lock_floor": 46.0,
            "lock_switch_ceiling": 48.0,
        },
    },
    "strict-review": {
        "label": "Strict Review",
        "summary": "For focused revision demos where scene lock is expected and drift should surface quickly.",
        "posture": {
            "content_expectation_bias": 4.0,
            "surface_expectation_bias": 6.0,
            "signal_uncertainty_floor": 50.0,
            "off_task_switch_floor": 46.0,
            "productive_alignment_floor": 80.0,
            "productive_lock_floor": 40.0,
        },
        "frame_adapter": {
            "content_sparse_floor": 22.0,
            "scene_locked_surface_floor": 60.0,
            "scene_locked_lock_floor": 64.0,
            "lock_switch_ceiling": 30.0,
        },
    },
}


def _build_session_id(now=None):
    now = now or datetime.now()
    return now.strftime("session-%Y%m%d-%H%M%S-%f")


def _active_scene_metrics():
    return {
        "tracking_state": latest_input.get("tracking_state", "warmup"),
        "tracking_confidence": latest_input.get("tracking_confidence"),
        "tracking_uncertainty": latest_input.get("tracking_uncertainty", 0.0),
        "scene_content_score": posture.scene_content_score,
        "scene_text_score": posture.scene_text_score,
        "scene_stability_score": posture.scene_stability_score,
        "scene_switch_rate": posture.scene_switch_rate,
        "study_surface_score": posture.study_surface_score,
        "scene_lock_score": posture.scene_lock_score,
        "blur_score": posture.blur_score,
        "brightness_score": posture.brightness_score,
        "behavioral_alignment": posture.behavioral_alignment,
        "cognitive_load": posture.cognitive_load,
        "fatigue_risk": posture.fatigue_risk,
        "uncertainty_score": posture.uncertainty_score,
        "state_hint": posture.state_hint,
        "task_mode": posture.task_mode,
    }


def _build_scene_calibration_diagnosis():
    metrics = _active_scene_metrics()
    posture_tuning = posture.get_scene_tuning()
    frame_tuning = rokid_frame_adapter.get_scene_tuning()
    diagnosis = []
    suggested_preset = "balanced-reading"

    if metrics["tracking_state"] in {"frame_unavailable", "low_visibility", "blurred"}:
        diagnosis.append({
            "severity": "high",
            "title": "Scene signal is not stable enough yet",
            "reason": "The first-person frame currently looks too dim, too blurred, or unavailable for scene-based learning inference.",
            "recommended_actions": [
                "Improve lighting or hold the glasses more steadily for a few seconds.",
                f"If this scene is usually usable, try lowering `blurred_floor` below {frame_tuning['blurred_floor']:.1f}.",
                f"If dark textbook scenes are common, lower `low_visibility_floor` or raise `low_visibility_ceiling` from {frame_tuning['low_visibility_ceiling']:.1f}.",
            ],
            "target_fields": ["blurred_floor", "low_visibility_floor", "low_visibility_ceiling"],
        })

    if metrics["scene_content_score"] < frame_tuning["content_sparse_floor"] and metrics["study_surface_score"] < frame_tuning["scene_locked_surface_floor"]:
        diagnosis.append({
            "severity": "medium",
            "title": "Study surface looks too sparse for the current thresholds",
            "reason": "The scene appears weakly text-anchored or lacks a strong reading surface under the active rules.",
            "recommended_actions": [
                "If this is a screen or low-text slide, try the `Screen Lecture` preset.",
                f"Otherwise reduce `content_sparse_floor` below {frame_tuning['content_sparse_floor']:.1f}.",
                f"You can also lower `surface_expectation_bias` from {posture_tuning['surface_expectation_bias']:.1f} for mixed-content scenes.",
            ],
            "target_fields": ["content_sparse_floor", "surface_expectation_bias"],
        })
        suggested_preset = "screen-lecture"

    if metrics["scene_content_score"] >= 45 and metrics["study_surface_score"] >= 45 and metrics["scene_lock_score"] < frame_tuning["scene_locked_lock_floor"]:
        diagnosis.append({
            "severity": "medium",
            "title": "The scene has content, but the lock requirement may be too strict",
            "reason": "Book or screen content is visible, yet the adapter still struggles to call the view scene-locked.",
            "recommended_actions": [
                f"Lower `scene_locked_lock_floor` from {frame_tuning['scene_locked_lock_floor']:.1f}.",
                f"Lower `scene_locked_surface_floor` from {frame_tuning['scene_locked_surface_floor']:.1f} if the material is visually lighter.",
                "Use the `Balanced Reading` preset as a safer baseline before fine-grained tuning.",
            ],
            "target_fields": ["scene_locked_lock_floor", "scene_locked_surface_floor"],
        })

    if metrics["scene_switch_rate"] >= posture_tuning["off_task_switch_floor"] and metrics["task_mode"] in {"reading", "note-taking"}:
        diagnosis.append({
            "severity": "medium",
            "title": "Switching sensitivity is high for the current study rhythm",
            "reason": "The model sees frequent target switching, which may be valid note-taking rather than true off-task drift.",
            "recommended_actions": [
                "If you are intentionally moving between notes and screen, try the `Notes Switching` preset.",
                f"Raise `off_task_switch_floor` above {posture_tuning['off_task_switch_floor']:.1f} to tolerate valid switching.",
                f"Raise `lock_switch_ceiling` above {frame_tuning['lock_switch_ceiling']:.1f} if scene lock drops too easily during note-taking.",
            ],
            "target_fields": ["off_task_switch_floor", "lock_switch_ceiling"],
        })
        suggested_preset = "notes-switching"

    if metrics["behavioral_alignment"] >= posture_tuning["productive_alignment_floor"] and metrics["scene_lock_score"] >= posture_tuning["productive_lock_floor"] and metrics["state_hint"] in {"stable", "productive_struggle"}:
        diagnosis.append({
            "severity": "good",
            "title": "Current thresholds are aligned with a focused first-person study scene",
            "reason": "The scene is sufficiently content-rich and locked for the model to distinguish stable study from productive struggle.",
            "recommended_actions": [
                "Keep this threshold set as a local baseline snapshot.",
                "Only tighten it if off-task drift is being missed during demos.",
            ],
            "target_fields": [],
        })

    if not diagnosis:
        diagnosis.append({
            "severity": "signal",
            "title": "Warm up with a stable textbook or screen frame",
            "reason": "The system needs a few consistent first-person frames before the scene thresholds become informative.",
            "recommended_actions": [
                "Send a short burst of similar frames from a book, note page, or screen.",
                "Then compare `scene_content`, `study_surface`, and `scene_lock` before changing thresholds.",
            ],
            "target_fields": [],
        })

    headline = diagnosis[0]["title"]
    return {
        "headline": headline,
        "suggested_preset": suggested_preset,
        "items": diagnosis,
        "metrics": metrics,
    }


def _scene_preset_payload(preset_id):
    preset = ROKID_SCENE_PRESETS.get(preset_id)
    if not preset:
        return None
    return {
        "preset_id": preset_id,
        "label": preset["label"],
        "summary": preset["summary"],
        "posture": dict(preset["posture"]),
        "frame_adapter": dict(preset["frame_adapter"]),
    }


def _default_scene_profile_store():
    return {
        "version": 1,
        "profiles": [],
    }


def _load_scene_profile_store():
    if not os.path.exists(ROKID_PROFILE_STORE_PATH):
        return _default_scene_profile_store()
    try:
        with open(ROKID_PROFILE_STORE_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return _default_scene_profile_store()
    if not isinstance(data, dict):
        return _default_scene_profile_store()
    data.setdefault("version", 1)
    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        data["profiles"] = []
    return data


def _save_scene_profile_store(store):
    os.makedirs(os.path.dirname(ROKID_PROFILE_STORE_PATH), exist_ok=True)
    with open(ROKID_PROFILE_STORE_PATH, "w", encoding="utf-8") as handle:
        json.dump(store, handle, indent=2, ensure_ascii=False)


def _slugify_profile_name(name):
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", str(name or "").strip().lower())
    normalized = normalized.strip("-")
    return normalized or "scene-profile"


def _slugify_reflection_name(name, fallback="reflection"):
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", str(name or "").strip().lower())
    normalized = normalized.strip("-")
    return normalized or fallback


def _clean_model_override_name(value):
    return " ".join(str(value or "").strip().split())[:160].strip()


def _clean_compare_models(raw_models):
    if not isinstance(raw_models, list):
        return []
    models = []
    seen = set()
    for item in raw_models:
        model_name = _clean_model_override_name(item)
        if not model_name or model_name in seen:
            continue
        models.append(model_name)
        seen.add(model_name)
    return models


def _reflection_markdown_lines(items, prefix):
    lines = []
    for index, item in enumerate(items or [], start=1):
        if isinstance(item, dict):
            text = item.get("question") or item.get("title") or ""
        else:
            text = str(item or "")
        text = str(text).strip()
        if text:
            lines.append(f"{prefix}{index}. {text}")
    return lines or [f"{prefix}None"]


def _reflection_experiment_lines(items):
    lines = []
    for index, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip() or f"Experiment {index}"
        detail = str(item.get("detail", "")).strip()
        success_marker = str(item.get("success_marker", "")).strip()
        combined = title
        if detail:
            combined += f": {detail}"
        if success_marker:
            combined += f" Success marker: {success_marker}"
        lines.append(f"- {combined}")
    return lines or ["- None"]


def _snapshot_display_label(value, fallback="--"):
    text = str(value or "").strip()
    if not text:
        return fallback
    normalized = re.sub(r"[_-]+", " ", text)
    normalized = " ".join(normalized.split())
    return normalized.title() if normalized else fallback


def _snapshot_metric(value, suffix=""):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return f"--{suffix}"
    return f"{int(round(numeric))}{suffix}"


def _snapshot_plain_text(value, fallback="--"):
    text = str(value or "").strip()
    return text or fallback


def _snapshot_html_text(value, fallback="--"):
    return html_escape(_snapshot_plain_text(value, fallback))


def _snapshot_html_paragraph(value, fallback="--"):
    return _snapshot_html_text(value, fallback).replace("\n", "<br>")


def _runtime_info_payload():
    return {
        "status": "ok",
        "service": "focus-project-reflection",
        "backend_version": REFLECTION_RUNTIME_VERSION,
        "snapshot_exporter_version": REFLECTION_SNAPSHOT_EXPORTER_VERSION,
        "booted_at": APP_BOOTED_AT,
        "pid": os.getpid(),
        "python_version": sys.version.split()[0],
        "python_executable": os.path.basename(sys.executable or "python"),
        "feature_flags": {
            "runtime_info_endpoint": True,
            "snapshot_html_card_export": True,
            "compare_html_card_export": True,
        },
    }


def _reflection_anchor_reason(payload, event):
    event = event or {}
    requested_event_id = str(payload.get("requested_event_id", "") or "").strip()
    selected_event_id = str(payload.get("selected_event_id", "") or event.get("event_id", "") or "").strip()
    if not event:
        return "No specific difficulty event was available, so the coach read the overall session rhythm."
    if requested_event_id and requested_event_id == selected_event_id:
        return f"This reflection inherited D{selected_event_id} from the review selection."
    if requested_event_id and requested_event_id != selected_event_id:
        return (
            f"Requested D{requested_event_id} was unavailable in this session, "
            f"so the coach fell back to D{selected_event_id}, the strongest recorded difficulty segment."
        )
    return f"No explicit event was passed in, so the coach anchored itself to D{selected_event_id}, the strongest difficulty segment in this session."


def _reflection_anchor_markdown_lines(payload, heading="## Evidence Anchor"):
    payload = payload if isinstance(payload, dict) else {}
    event = payload.get("highlight_event") or {}
    if not event:
        return [
            heading,
            "",
            "- Anchor reason: No event-specific replay anchor was available for this session.",
        ]

    severity_label = str(event.get("severity_label", "")).strip() or _snapshot_display_label(event.get("severity"), "Clear")
    state_label = str(event.get("state_hint_label", "")).strip() or _snapshot_display_label(event.get("state_hint"), "Stable")
    lines = [
        heading,
        "",
        f"- Anchor reason: {_reflection_anchor_reason(payload, event)}",
        f"- Event: D{event.get('event_id')}",
        f"- Window: {event.get('time_window', '--')}",
        f"- Severity: {severity_label}",
        f"- State hint: {state_label}",
        f"- Task mode: {_snapshot_display_label(event.get('task_mode'), '--')}",
        f"- Load / Fatigue / Switching: {_snapshot_metric(event.get('avg_load'))} / {_snapshot_metric(event.get('avg_fatigue'))} / {_snapshot_metric(event.get('avg_switching'))}",
        f"- Trigger: {event.get('trigger_label') or '--'}",
        f"- Trigger reason: {event.get('trigger_reason') or '--'}",
        f"- Review note: {event.get('review_note') or '--'}",
        f"- Catch-up action: {event.get('catch_up_action') or '--'}",
    ]
    return lines


def _build_single_reflection_snapshot_markdown(bundle):
    payload = bundle.get("payload", {}) or {}
    summary = payload.get("summary", {}) or {}
    generation = payload.get("generation", {}) or {}
    coach_summary = payload.get("coach_summary", {}) or {}
    signature = payload.get("signature", {}) or {}
    lines = [
        "# Reflection Snapshot",
        "",
        f"- Saved at: {bundle.get('saved_at', '')}",
        f"- Session ID: {bundle.get('session_id', '') or '--'}",
        f"- Dataset: {bundle.get('dataset', '') or '--'}",
        f"- Provider: {generation.get('provider_label', 'Heuristic')}",
        f"- Model: {generation.get('model', '') or '--'}",
        f"- Primary task mode: {summary.get('primary_task_mode', '--')}",
        "",
        "## Signature",
        "",
        f"**{signature.get('label', '--')}**",
        "",
        signature.get("detail", "No signature detail."),
        "",
        "## Summary",
        "",
        f"- Headline: {coach_summary.get('headline', '--')}",
        f"- Overview: {coach_summary.get('overview', '--')}",
        f"- Why it matters: {coach_summary.get('why_it_matters', '--')}",
        f"- Next boundary: {coach_summary.get('next_boundary', '--')}",
        "",
    ]
    lines.extend(_reflection_anchor_markdown_lines(payload))
    lines.extend([
        "",
        "## Coach Memo",
        "",
        payload.get("coach_memo", "No coach memo."),
        "",
        "## Reflection Questions",
        "",
    ])
    lines.extend(_reflection_markdown_lines(payload.get("reflection_questions", []), ""))
    lines.extend([
        "",
        "## Next-Session Experiments",
        "",
    ])
    lines.extend(_reflection_experiment_lines(payload.get("next_session_experiments", [])))
    return "\n".join(lines).strip() + "\n"


def _build_compare_reflection_snapshot_markdown(bundle):
    payload = bundle.get("payload", {}) or {}
    variants = payload.get("variants", []) or []
    anchor_payload = {}
    for variant in variants:
        candidate = variant.get("payload")
        if isinstance(candidate, dict) and candidate:
            anchor_payload = candidate
            break
    lines = [
        "# Reflection Compare Snapshot",
        "",
        f"- Saved at: {bundle.get('saved_at', '')}",
        f"- Session ID: {bundle.get('session_id', '') or '--'}",
        f"- Dataset: {bundle.get('dataset', '') or '--'}",
        f"- Compared at: {payload.get('compared_at', '') or '--'}",
        f"- Provider: {payload.get('request', {}).get('provider', 'ollama')}",
        "",
    ]
    lines.extend(_reflection_anchor_markdown_lines(anchor_payload, heading="## Shared Evidence Anchor"))
    lines.append("")
    for variant in variants:
        generation = variant.get("generation", {}) or {}
        coach_summary = variant.get("coach_summary", {}) or {}
        lines.extend([
            f"## {variant.get('model', '--')}",
            "",
            f"- Duration: {variant.get('duration_ms', 0)} ms",
            f"- Active mode: {generation.get('mode', 'heuristic')}",
            f"- Provider note: {generation.get('note', '--')}",
            "",
            f"Headline: {coach_summary.get('headline', '--')}",
            "",
            f"Overview: {coach_summary.get('overview', '--')}",
            "",
            "Coach memo:",
            "",
            variant.get("coach_memo", "No coach memo."),
            "",
            "Reflection questions:",
            "",
        ])
        lines.extend(_reflection_markdown_lines(variant.get("reflection_questions", []), ""))
        lines.extend([
            "",
            "Next-Session Experiments:",
            "",
        ])
        lines.extend(_reflection_experiment_lines(variant.get("next_session_experiments", [])))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _reflection_card_question_items(items):
    rows = []
    for index, item in enumerate(items or [], start=1):
        if isinstance(item, dict):
            text = item.get("question") or item.get("title") or ""
        else:
            text = str(item or "")
        text = str(text).strip()
        if not text:
            continue
        rows.append(
            f"<li><strong>Q{index}.</strong> <span>{_snapshot_html_paragraph(text)}</span></li>"
        )
    return "".join(rows) or "<li class=\"empty\">No reflection questions were generated.</li>"


def _reflection_card_experiment_items(items):
    rows = []
    for index, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        title = _snapshot_plain_text(item.get("title"), f"Experiment {index}")
        detail = _snapshot_plain_text(item.get("detail"), "")
        success_marker = _snapshot_plain_text(item.get("success_marker"), "")
        body = [
            f"<strong>{_snapshot_html_text(title)}</strong>",
        ]
        if detail:
            body.append(f"<p>{_snapshot_html_paragraph(detail)}</p>")
        if success_marker:
            body.append(
                f"<p><span class=\"metric-label\">Success marker</span> {_snapshot_html_paragraph(success_marker)}</p>"
            )
        rows.append(f"<li>{''.join(body)}</li>")
    return "".join(rows) or "<li class=\"empty\">No next-session experiments were generated.</li>"


def _reflection_card_anchor_html(payload):
    payload = payload if isinstance(payload, dict) else {}
    event = payload.get("highlight_event") or {}
    anchor_reason = _reflection_anchor_reason(payload, event)
    if not event:
        return f"""
        <article class="anchor-card anchor-empty">
            <div class="section-eyebrow">Evidence Anchor</div>
            <h2>Session-wide reading</h2>
            <p>{_snapshot_html_paragraph(anchor_reason)}</p>
        </article>
        """

    severity_label = str(event.get("severity_label", "")).strip() or _snapshot_display_label(event.get("severity"), "Clear")
    state_label = str(event.get("state_hint_label", "")).strip() or _snapshot_display_label(event.get("state_hint"), "Stable")
    requested_event_id = str(payload.get("requested_event_id", "") or "").strip()
    selected_event_id = str(payload.get("selected_event_id", "") or event.get("event_id", "") or "").strip()
    anchor_meta = "Auto-selected strongest event"
    if requested_event_id:
        anchor_meta = "Inherited from review selection" if requested_event_id == selected_event_id else f"Fallback from requested D{requested_event_id}"

    return f"""
    <article class="anchor-card">
        <div class="section-eyebrow">Evidence Anchor</div>
        <div class="anchor-topline">
            <span class="anchor-meta">{_snapshot_html_text(anchor_meta)}</span>
            <span class="anchor-event">D{_snapshot_html_text(event.get('event_id'), '--')} | {_snapshot_html_text(event.get('time_window'), '--')}</span>
        </div>
        <p class="anchor-reason">{_snapshot_html_paragraph(anchor_reason)}</p>
        <div class="metric-grid">
            <div class="metric-chip"><span class="metric-label">Severity</span><strong>{_snapshot_html_text(severity_label)}</strong></div>
            <div class="metric-chip"><span class="metric-label">State</span><strong>{_snapshot_html_text(state_label)}</strong></div>
            <div class="metric-chip"><span class="metric-label">Mode</span><strong>{_snapshot_html_text(_snapshot_display_label(event.get('task_mode'), '--'))}</strong></div>
            <div class="metric-chip"><span class="metric-label">Load</span><strong>{_snapshot_html_text(_snapshot_metric(event.get('avg_load')))}</strong></div>
            <div class="metric-chip"><span class="metric-label">Fatigue</span><strong>{_snapshot_html_text(_snapshot_metric(event.get('avg_fatigue')))}</strong></div>
            <div class="metric-chip"><span class="metric-label">Switching</span><strong>{_snapshot_html_text(_snapshot_metric(event.get('avg_switching')))}</strong></div>
        </div>
        <div class="anchor-details">
            <div>
                <span class="metric-label">Trigger</span>
                <p>{_snapshot_html_paragraph(event.get('trigger_label'), '--')}</p>
            </div>
            <div>
                <span class="metric-label">Trigger reason</span>
                <p>{_snapshot_html_paragraph(event.get('trigger_reason'), '--')}</p>
            </div>
            <div>
                <span class="metric-label">Review note</span>
                <p>{_snapshot_html_paragraph(event.get('review_note'), '--')}</p>
            </div>
            <div>
                <span class="metric-label">Catch-up action</span>
                <p>{_snapshot_html_paragraph(event.get('catch_up_action'), '--')}</p>
            </div>
        </div>
    </article>
    """


def _reflection_card_shell(title, subtitle, body_html):
    title = _snapshot_html_text(title, "Reflection Snapshot Card")
    subtitle = _snapshot_html_paragraph(subtitle, "Reflection summary")
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
        :root {{
            color-scheme: light;
            --paper: #f7f3ea;
            --panel: #fffaf3;
            --line: #d8c9af;
            --text: #1f2430;
            --muted: #576172;
            --accent: #a84f2f;
            --accent-soft: #efe0d1;
            --ink-soft: #e8f0ec;
            --ink-strong: #27594a;
            --warn-soft: #f6ead5;
            --shadow: 0 20px 48px rgba(31, 36, 48, 0.08);
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: "Segoe UI", "Noto Sans SC", sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at top left, rgba(168, 79, 47, 0.12), transparent 34%),
                radial-gradient(circle at top right, rgba(39, 89, 74, 0.14), transparent 28%),
                var(--paper);
        }}
        main {{
            max-width: 1120px;
            margin: 0 auto;
            padding: 32px 24px 48px;
        }}
        .hero {{
            display: grid;
            gap: 18px;
            padding: 28px;
            border: 1px solid var(--line);
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(255, 250, 243, 0.98), rgba(247, 243, 234, 0.96));
            box-shadow: var(--shadow);
        }}
        .hero-eyebrow, .section-eyebrow {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--accent);
        }}
        h1, h2, h3, p {{ margin: 0; }}
        h1 {{
            font-size: clamp(30px, 4vw, 48px);
            line-height: 1.02;
            letter-spacing: -0.04em;
        }}
        .hero-subtitle {{
            max-width: 760px;
            font-size: 16px;
            line-height: 1.65;
            color: var(--muted);
        }}
        .meta-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
        }}
        .meta-card, .panel {{
            border: 1px solid var(--line);
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.82);
            box-shadow: var(--shadow);
        }}
        .meta-card {{
            padding: 16px 18px;
        }}
        .meta-card span, .metric-label {{
            display: block;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--muted);
            margin-bottom: 8px;
        }}
        .meta-card strong {{
            font-size: 16px;
            line-height: 1.35;
        }}
        .content-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
            gap: 18px;
            margin-top: 18px;
        }}
        .panel {{
            padding: 22px;
        }}
        .signature-panel {{
            background: linear-gradient(160deg, rgba(239, 224, 209, 0.9), rgba(255, 250, 243, 0.94));
        }}
        .signature-panel h2 {{
            margin-top: 12px;
            font-size: 28px;
            line-height: 1.15;
        }}
        .signature-detail {{
            margin-top: 12px;
            line-height: 1.7;
            color: var(--muted);
        }}
        .summary-stack, .anchor-details, .variant-stack {{
            display: grid;
            gap: 12px;
        }}
        .summary-item {{
            padding: 14px 16px;
            border-radius: 16px;
            background: rgba(39, 89, 74, 0.07);
        }}
        .summary-item:nth-child(2n) {{
            background: rgba(168, 79, 47, 0.08);
        }}
        .summary-item p {{
            margin-top: 6px;
            line-height: 1.6;
            color: var(--muted);
        }}
        .anchor-card {{
            grid-column: 1 / -1;
            padding: 22px;
            border: 1px solid var(--line);
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(255, 250, 243, 0.96), rgba(246, 234, 213, 0.78));
            box-shadow: var(--shadow);
        }}
        .anchor-topline {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            gap: 10px;
            margin-top: 14px;
        }}
        .anchor-meta {{
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent);
        }}
        .anchor-event {{
            font-weight: 700;
            font-size: 18px;
        }}
        .anchor-reason {{
            margin-top: 12px;
            line-height: 1.7;
            color: var(--muted);
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
            margin-top: 16px;
        }}
        .metric-chip {{
            padding: 12px 14px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(216, 201, 175, 0.75);
        }}
        .metric-chip strong {{
            font-size: 17px;
        }}
        .anchor-details {{
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            margin-top: 16px;
        }}
        .anchor-details div {{
            padding: 14px 16px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.68);
        }}
        .anchor-details p, .memo-body, .list-card li, .variant-block p {{
            line-height: 1.7;
            color: var(--muted);
        }}
        .lists-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px;
            margin-top: 18px;
        }}
        .list-card ul {{
            margin: 16px 0 0;
            padding-left: 20px;
        }}
        .list-card li {{
            margin-bottom: 14px;
        }}
        .list-card li.empty {{
            list-style: none;
            margin-left: -20px;
        }}
        .memo-panel {{
            margin-top: 18px;
            background: linear-gradient(180deg, rgba(232, 240, 236, 0.86), rgba(255, 255, 255, 0.9));
        }}
        .memo-body {{
            margin-top: 14px;
            font-size: 15px;
        }}
        .footer-note {{
            margin-top: 18px;
            font-size: 13px;
            line-height: 1.7;
            color: var(--muted);
        }}
        .compare-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 18px;
            margin-top: 18px;
        }}
        .variant-panel {{
            background: rgba(255, 255, 255, 0.86);
        }}
        .variant-topline {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: baseline;
            margin-top: 12px;
        }}
        .variant-badge {{
            padding: 8px 12px;
            border-radius: 999px;
            background: var(--ink-soft);
            color: var(--ink-strong);
            font-weight: 700;
            font-size: 12px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }}
        .variant-block {{
            margin-top: 14px;
            padding-top: 14px;
            border-top: 1px solid rgba(216, 201, 175, 0.78);
        }}
        @media (max-width: 900px) {{
            .content-grid,
            .lists-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        @media print {{
            body {{ background: #fff; }}
            main {{ max-width: none; padding: 0; }}
            .hero, .panel, .anchor-card, .meta-card {{
                box-shadow: none;
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <main>
        <section class="hero">
            <div class="hero-eyebrow">Learning Reflection Coach</div>
            <h1>{title}</h1>
            <p class="hero-subtitle">{subtitle}</p>
        </section>
        {body_html}
        <p class="footer-note">
            This reflection card stays process-focused. It summarizes how the learning session unfolded and what to try next, without reteaching the study content itself.
        </p>
    </main>
</body>
</html>
"""


def _build_single_reflection_snapshot_html(bundle):
    payload = bundle.get("payload", {}) or {}
    summary = payload.get("summary", {}) or {}
    generation = payload.get("generation", {}) or {}
    coach_summary = payload.get("coach_summary", {}) or {}
    signature = payload.get("signature", {}) or {}
    body_html = f"""
    <div class="meta-row" style="margin-top: 18px;">
        <article class="meta-card"><span>Session</span><strong>{_snapshot_html_text(bundle.get('session_id'), '--')}</strong></article>
        <article class="meta-card"><span>Dataset</span><strong>{_snapshot_html_text(bundle.get('dataset'), '--')}</strong></article>
        <article class="meta-card"><span>Provider</span><strong>{_snapshot_html_text(generation.get('provider_label'), 'Heuristic')}</strong></article>
        <article class="meta-card"><span>Model</span><strong>{_snapshot_html_text(generation.get('model'), '--')}</strong></article>
        <article class="meta-card"><span>Saved At</span><strong>{_snapshot_html_text(bundle.get('saved_at'), '--')}</strong></article>
        <article class="meta-card"><span>Primary Mode</span><strong>{_snapshot_html_text(summary.get('primary_task_mode'), '--')}</strong></article>
    </div>
    <div class="content-grid">
        <article class="panel signature-panel">
            <div class="section-eyebrow">Session Signature</div>
            <h2>{_snapshot_html_text(signature.get('label'), '--')}</h2>
            <p class="signature-detail">{_snapshot_html_paragraph(signature.get('detail'), 'No signature detail.')}</p>
        </article>
        <article class="panel">
            <div class="section-eyebrow">Coach Summary</div>
            <div class="summary-stack" style="margin-top: 12px;">
                <div class="summary-item"><span class="metric-label">Headline</span><p>{_snapshot_html_paragraph(coach_summary.get('headline'), '--')}</p></div>
                <div class="summary-item"><span class="metric-label">Overview</span><p>{_snapshot_html_paragraph(coach_summary.get('overview'), '--')}</p></div>
                <div class="summary-item"><span class="metric-label">Why It Matters</span><p>{_snapshot_html_paragraph(coach_summary.get('why_it_matters'), '--')}</p></div>
                <div class="summary-item"><span class="metric-label">Next Boundary</span><p>{_snapshot_html_paragraph(coach_summary.get('next_boundary'), '--')}</p></div>
            </div>
        </article>
    </div>
    {_reflection_card_anchor_html(payload)}
    <div class="lists-grid">
        <article class="panel list-card">
            <div class="section-eyebrow">Reflection Questions</div>
            <ul>{_reflection_card_question_items(payload.get('reflection_questions', []))}</ul>
        </article>
        <article class="panel list-card">
            <div class="section-eyebrow">Next-Session Experiments</div>
            <ul>{_reflection_card_experiment_items(payload.get('next_session_experiments', []))}</ul>
        </article>
    </div>
    <article class="panel memo-panel">
        <div class="section-eyebrow">Coach Memo</div>
        <p class="memo-body">{_snapshot_html_paragraph(payload.get('coach_memo'), 'No coach memo.')}</p>
    </article>
    """
    title = signature.get("label") or "Reflection Snapshot Card"
    subtitle = coach_summary.get("headline") or "A one-page summary of the session signature, anchor event, and next-session experiments."
    return _reflection_card_shell(title, subtitle, body_html)


def _build_compare_reflection_snapshot_html(bundle):
    payload = bundle.get("payload", {}) or {}
    variants = payload.get("variants", []) or []
    anchor_payload = {}
    for variant in variants:
        candidate = variant.get("payload")
        if isinstance(candidate, dict) and candidate:
            anchor_payload = candidate
            break

    variant_html = []
    for variant in variants:
        generation = variant.get("generation", {}) or {}
        coach_summary = variant.get("coach_summary", {}) or {}
        variant_html.append(f"""
        <article class="panel variant-panel">
            <div class="section-eyebrow">Model Variant</div>
            <div class="variant-topline">
                <h2>{_snapshot_html_text(variant.get('model') or generation.get('model'), '--')}</h2>
                <span class="variant-badge">{_snapshot_html_text(generation.get('mode'), 'heuristic')} | {_snapshot_html_text(variant.get('duration_ms'), '0')} ms</span>
            </div>
            <div class="variant-stack">
                <div class="variant-block">
                    <span class="metric-label">Headline</span>
                    <p>{_snapshot_html_paragraph(coach_summary.get('headline'), '--')}</p>
                </div>
                <div class="variant-block">
                    <span class="metric-label">Coach Memo</span>
                    <p>{_snapshot_html_paragraph(variant.get('coach_memo'), 'No coach memo.')}</p>
                </div>
                <div class="variant-block">
                    <span class="metric-label">Reflection Questions</span>
                    <ul>{_reflection_card_question_items(variant.get('reflection_questions', []))}</ul>
                </div>
                <div class="variant-block">
                    <span class="metric-label">Next-Session Experiments</span>
                    <ul>{_reflection_card_experiment_items(variant.get('next_session_experiments', []))}</ul>
                </div>
            </div>
        </article>
        """)

    body_html = f"""
    <div class="meta-row" style="margin-top: 18px;">
        <article class="meta-card"><span>Session</span><strong>{_snapshot_html_text(bundle.get('session_id'), '--')}</strong></article>
        <article class="meta-card"><span>Dataset</span><strong>{_snapshot_html_text(bundle.get('dataset'), '--')}</strong></article>
        <article class="meta-card"><span>Provider</span><strong>{_snapshot_html_text((payload.get('request', {}) or {}).get('provider'), 'ollama')}</strong></article>
        <article class="meta-card"><span>Compared At</span><strong>{_snapshot_html_text(payload.get('compared_at'), '--')}</strong></article>
        <article class="meta-card"><span>Variant Count</span><strong>{_snapshot_html_text(len(variants), '0')}</strong></article>
    </div>
    {_reflection_card_anchor_html(anchor_payload)}
    <div class="compare-grid">
        {''.join(variant_html) or '<article class="panel variant-panel"><p class="memo-body">No compare variants were generated.</p></article>'}
    </div>
    """
    title = "Reflection Compare Card"
    subtitle = "A one-page contrast of local model outputs on the same evidence anchor."
    return _reflection_card_shell(title, subtitle, body_html)


def _build_reflection_snapshot_html(bundle):
    if bundle.get("kind") == "compare":
        return _build_compare_reflection_snapshot_html(bundle)
    return _build_single_reflection_snapshot_html(bundle)


def _build_reflection_snapshot_markdown(bundle):
    if bundle.get("kind") == "compare":
        return _build_compare_reflection_snapshot_markdown(bundle)
    return _build_single_reflection_snapshot_markdown(bundle)


def _build_reflection_snapshot_bundle(kind, payload):
    saved_at = datetime.now().isoformat(timespec="seconds")
    payload = payload if isinstance(payload, dict) else {}
    session_id = str(payload.get("session_id", "")).strip()
    dataset = str(payload.get("dataset", "")).strip().lower() or "live"
    anchor_payload = payload

    if kind == "compare":
        variants = payload.get("variants", []) or []
        if not session_id and variants:
            session_id = str((variants[0].get("payload", {}) or {}).get("session_id", "")).strip()
        if not payload.get("dataset") and variants:
            dataset = str((variants[0].get("payload", {}) or {}).get("dataset", dataset)).strip().lower() or dataset
        for variant in variants:
            candidate = variant.get("payload")
            if isinstance(candidate, dict) and candidate:
                anchor_payload = candidate
                break

    return {
        "kind": kind,
        "saved_at": saved_at,
        "session_id": session_id,
        "dataset": dataset,
        "requested_event_id": (anchor_payload or {}).get("requested_event_id"),
        "selected_event_id": (anchor_payload or {}).get("selected_event_id"),
        "payload": payload,
    }


def _save_reflection_snapshot(kind, payload):
    bundle = _build_reflection_snapshot_bundle(kind, payload)
    os.makedirs(REFLECTION_SNAPSHOT_DIR, exist_ok=True)
    session_slug = _slugify_reflection_name(bundle.get("session_id") or f"{bundle.get('dataset', 'live')}-session", fallback="session")
    basename = f"{session_slug}-reflection-{kind}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    json_path = os.path.join(REFLECTION_SNAPSHOT_DIR, f"{basename}.json")
    md_path = os.path.join(REFLECTION_SNAPSHOT_DIR, f"{basename}.md")
    html_path = os.path.join(REFLECTION_SNAPSHOT_DIR, f"{basename}.html")

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(bundle, handle, indent=2, ensure_ascii=False)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(_build_reflection_snapshot_markdown(bundle))
    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(_build_reflection_snapshot_html(bundle))

    return {
        "status": "ok",
        "kind": kind,
        "snapshot_id": basename,
        "saved_at": bundle["saved_at"],
        "snapshot_exporter_version": REFLECTION_SNAPSHOT_EXPORTER_VERSION,
        "supports_html_card_export": True,
        "json_url": f"/exports/reflection_snapshots/{basename}.json",
        "md_url": f"/exports/reflection_snapshots/{basename}.md",
        "card_url": f"/exports/reflection_snapshots/{basename}.html",
        "json_path": json_path,
        "md_path": md_path,
        "card_path": html_path,
    }


def _build_reflection_compare_variant(dataset, session_id, event_id, learner_note, next_goal, model_name):
    started_at = time.perf_counter()
    payload = reflection_coach.build_payload(
        session_id=session_id,
        dataset=dataset,
        event_id=event_id,
        learner_note=learner_note,
        next_goal=next_goal,
        use_llm=True,
        provider_override="ollama",
        model_override=model_name,
    )
    duration_ms = int(round((time.perf_counter() - started_at) * 1000))
    generation = payload.get("generation", {}) or {}
    return {
        "model": generation.get("model") or model_name,
        "duration_ms": duration_ms,
        "generation": generation,
        "signature": payload.get("signature", {}),
        "coach_summary": payload.get("coach_summary", {}),
        "coach_memo": payload.get("coach_memo", ""),
        "reflection_questions": payload.get("reflection_questions", []),
        "next_session_experiments": payload.get("next_session_experiments", []),
        "payload": payload,
    }


def _build_scene_profile_payload(profile_name, task_mode=None, notes="", source_preset=""):
    timestamp = datetime.now()
    slug = _slugify_profile_name(profile_name)
    profile_id = f"{slug}-{timestamp.strftime('%Y%m%d-%H%M%S')}"
    task_mode = str(task_mode or posture.task_mode or "reading").strip().lower()
    return {
        "profile_id": profile_id,
        "profile_name": str(profile_name or "").strip() or "Scene calibration",
        "task_mode": task_mode,
        "notes": str(notes or "").strip(),
        "source_preset": str(source_preset or "").strip(),
        "saved_at": timestamp.isoformat(timespec="seconds"),
        "posture": posture.get_scene_tuning(),
        "frame_adapter": rokid_frame_adapter.get_scene_tuning(),
        "snapshot": _active_scene_metrics(),
    }


def _find_scene_profile(profile_id):
    store = _load_scene_profile_store()
    for profile in store.get("profiles", []):
        if profile.get("profile_id") == profile_id:
            return store, profile
    return store, None


def _new_difficulty_snapshot():
    return {
        "active_event": None,
        "completed_event": None,
        "last_event": None,
        "event_count": difficulty_marker.event_counter,
    }


def _input_snapshot(packet=None):
    if packet is None:
        return {
            "source": "simulator",
            "device_profile": "simulator-rokid-proxy",
            "tracking_state": "warmup",
            "tracking_confidence": None,
            "tracking_uncertainty": 0.0,
            "face_present": None,
            "scene_content_score": 0.0,
            "scene_text_score": 0.0,
            "scene_stability_score": 0.0,
            "scene_switch_rate": 0.0,
            "study_surface_score": 0.0,
            "scene_lock_score": 0.0,
            "blur_score": 0.0,
            "brightness_score": 0.0,
            "motion_source": "default",
            "pose_source": "simulator",
            "frame_source": "simulator",
            "timestamp_ms": None,
        }
    return {
        "source": packet.source,
        "device_profile": packet.device_profile,
        "tracking_state": packet.tracking_state,
        "tracking_confidence": packet.tracking_confidence,
        "tracking_uncertainty": packet.tracking_uncertainty,
        "face_present": packet.face_present,
        "scene_content_score": packet.scene_content_score,
        "scene_text_score": packet.scene_text_score,
        "scene_stability_score": packet.scene_stability_score,
        "scene_switch_rate": packet.scene_switch_rate,
        "study_surface_score": packet.study_surface_score,
        "scene_lock_score": packet.scene_lock_score,
        "blur_score": packet.blur_score,
        "brightness_score": packet.brightness_score,
        "motion_source": packet.motion_source,
        "pose_source": packet.pose_source,
        "frame_source": packet.frame_source,
        "timestamp_ms": packet.timestamp_ms,
    }


def _start_new_session(reset_posture=False):
    global latest_session, latest_difficulty, latest_input, sample_counter, last_posture_at, current_session_id
    rokid_frame_adapter.reset_scene_memory()
    if reset_posture:
        posture.calibrate()
    else:
        posture.reset_tracking(preserve_baseline=True)
    focus_session.reset()
    difficulty_marker.reset()
    current_session_id = _build_session_id()
    latest_session = focus_session.snapshot()
    latest_difficulty = _new_difficulty_snapshot()
    latest_input = _input_snapshot()
    sample_counter = 0
    last_posture_at = None
    return current_session_id


current_session_id = _build_session_id()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/review")
def review_page():
    return render_template("review.html")


@app.route("/reflection")
def reflection_page():
    return render_template("reflection.html")


@app.route("/presentation")
@app.route("/presentations")
def presentation_page():
    return render_template("presentation.html")


@app.route("/rokid_debug")
def rokid_debug_page():
    return render_template("rokid_debug.html")


@app.route("/exports/<path:filename>")
def export_asset(filename):
    return send_from_directory(EXPORT_DIR, filename)


@app.route("/api/v1/posture", methods=["POST"])
def handle_posture():
    packet = build_simulator_packet(request.json or {}, default_task_mode=posture.task_mode)
    _ingest_packet(packet)
    return jsonify({"status": "ok", "source": packet.source, "session_id": current_session_id})


@app.route("/api/v1/rokid/head-pose", methods=["POST"])
def handle_rokid_head_pose():
    packet = build_rokid_packet(request.json or {}, default_task_mode=posture.task_mode)
    _ingest_packet(packet)
    return jsonify({"status": "ok", "source": packet.source, "session_id": current_session_id})


@app.route("/api/v1/rokid/frame", methods=["POST"])
def handle_rokid_frame():
    if request.files:
        payload = request.form.to_dict()
        image_bytes = request.files.get("frame").read() if request.files.get("frame") else None
    else:
        payload = request.json or {}
        image_bytes = None

    if not rokid_frame_adapter.has_frame_payload(payload, image_bytes=image_bytes):
        return jsonify({
            "status": "error",
            "message": "Provide `frame` upload, `image_base64`, or `image_path` for the Rokid video-frame adapter.",
        }), 400

    packet = rokid_frame_adapter.build_packet(payload, image_bytes=image_bytes, default_task_mode=posture.task_mode)
    _ingest_packet(packet)
    message = "Frame packet ingested."
    if packet.frame_source == "opencv-unavailable":
        message = "Frame adapter scaffold is active, but the current runtime does not provide OpenCV scene-analysis support."
    elif packet.tracking_state in {"content_sparse", "low_visibility", "blurred", "scene_unstable"}:
        message = "Frame received, but the study scene was not stable enough; the session will bias toward signal-check behavior."
    elif packet.tracking_state == "frame_unavailable":
        message = "Frame input was not decoded successfully."
    return jsonify({
        "status": "ok",
        "source": packet.source,
        "tracking_state": packet.tracking_state,
        "tracking_confidence": packet.tracking_confidence,
        "message": message,
        "session_id": current_session_id,
    })


def _ingest_packet(packet):
    global pending_card, latest_session, latest_difficulty, latest_input, sample_counter, last_posture_at
    sample_counter += 1
    last_posture_at = datetime.now()
    timestamp_text = packet.timestamp_text or datetime.now().strftime("%H:%M:%S")
    if packet.task_mode and packet.task_mode != posture.task_mode:
        posture.set_task_mode(packet.task_mode)
    res = posture.process(
        packet.pitch or 0,
        raw_yaw=packet.yaw or 0,
        raw_roll=packet.roll or 0,
        motion_intensity=packet.motion_intensity,
        external_uncertainty=packet.tracking_uncertainty,
        scene_features={
            "scene_content_score": packet.scene_content_score,
            "scene_text_score": packet.scene_text_score,
            "scene_stability_score": packet.scene_stability_score,
            "scene_switch_rate": packet.scene_switch_rate,
            "study_surface_score": packet.study_surface_score,
            "scene_lock_score": packet.scene_lock_score,
            "blur_score": packet.blur_score,
            "brightness_score": packet.brightness_score,
        },
    )
    latest_session = focus_session.update(res)
    latest_difficulty = difficulty_marker.update(
        res,
        latest_session,
        timestamp_text=timestamp_text,
        sample_index=sample_counter,
        session_id=current_session_id,
    )
    logger.log_study(
        pitch=res["relative_pitch"],
        is_alert=res["is_alert"],
        score=res["focus_score"],
        relative_yaw=res.get("relative_yaw", 0),
        relative_roll=res.get("relative_roll", 0),
        combined_drift=res.get("combined_drift", res["relative_pitch"]),
        orientation_drift=res.get("orientation_drift", 0),
        movement_intensity=res.get("movement_intensity", 0),
        stability=res["stability"],
        cognitive_load=res["cognitive_load"],
        load_level=res["load_level"],
        task_mode=res["task_mode"],
        input_source=packet.source,
        behavioral_alignment=res["behavioral_alignment"],
        behavioral_level=res["behavioral_level"],
        drift_trend=res.get("drift_trend", 0),
        switching_index=res.get("switching_index", 0),
        state_hint=res.get("state_hint", "stable"),
        fatigue_risk=res["fatigue_risk"],
        fatigue_level=res["fatigue_level"],
        uncertainty_score=res["uncertainty_score"],
        confidence_level=res["confidence_level"],
        guidance=latest_session["guidance"],
        phase=latest_session["phase"],
        elapsed_seconds=latest_session["elapsed_seconds"],
        cycle_index=latest_session["cycle_index"],
        timestamp_text=timestamp_text,
        session_id=current_session_id,
    )
    latest_input = _input_snapshot(packet)
    if latest_difficulty["completed_event"]:
        logger.log_difficulty_event(latest_difficulty["completed_event"])

    if auto_recall_enabled and not pending_card.get("word"):
        quiz = edu.check_active_recall()
        if quiz:
            pending_card = quiz
            print(f"[EDU] Active recall triggered: {quiz['word']}")


@app.route("/capture")
def handle_capture():
    global pending_card
    res = vision.ocr_and_translate("images/demo.jpg")
    if res:
        logger.save_word(res["word"], res["trans"])
        pending_card = {"word": res["word"], "trans": res["trans"], "type": "ocr"}
    return "ok"


@app.route("/collect")
def handle_collect():
    global pending_card
    res = vision.process_engineering_buffer("images/demo.jpg")
    if res:
        pending_card = {"word": f"{res['type']} SAVED", "trans": "Synced to notes.md", "type": "collect"}
    return "ok"


@app.route("/status")
def get_status():
    global pending_card, latest_session, latest_difficulty, latest_input, last_posture_at
    latest_session = focus_session.snapshot()
    data = {
        "rel_pitch": round(abs(posture.smooth_pitch - posture.base_pitch), 1),
        "signed_pitch_delta": round(posture.smooth_pitch - posture.base_pitch, 1),
        "rel_yaw": round(abs(posture.smooth_yaw - posture.base_yaw), 1),
        "signed_yaw_delta": round(posture.smooth_yaw - posture.base_yaw, 1),
        "rel_roll": round(abs(posture.smooth_roll - posture.base_roll), 1),
        "signed_roll_delta": round(posture.smooth_roll - posture.base_roll, 1),
        "combined_drift": round(posture.combined_drift, 1),
        "orientation_drift": posture.orientation_drift,
        "movement_intensity": posture.movement_intensity,
        "stability": posture.current_stability,
        "is_alert": posture.is_alert,
        "focus_score": posture.focus_score,
        "cognitive_load": posture.cognitive_load,
        "load_level": posture.load_level,
        "load_reason": posture.load_reason,
        "task_mode": posture.task_mode,
        "behavioral_alignment": posture.behavioral_alignment,
        "behavioral_level": posture.behavioral_level,
        "drift_trend": posture.drift_trend,
        "switching_index": posture.switching_index,
        "state_hint": posture.state_hint,
        "fatigue_risk": posture.fatigue_risk,
        "fatigue_level": posture.fatigue_level,
        "uncertainty_score": posture.uncertainty_score,
        "confidence_level": posture.confidence_level,
        "scene_content_score": posture.scene_content_score,
        "scene_text_score": posture.scene_text_score,
        "scene_stability_score": posture.scene_stability_score,
        "scene_switch_rate": posture.scene_switch_rate,
        "study_surface_score": posture.study_surface_score,
        "scene_lock_score": posture.scene_lock_score,
        "blur_score": posture.blur_score,
        "brightness_score": posture.brightness_score,
        "session": latest_session,
        "input": latest_input,
        "difficulty": {
            "active_event": latest_difficulty.get("active_event"),
            "last_event": latest_difficulty.get("last_event"),
            "event_count": latest_difficulty.get("event_count", 0),
        },
        "session_id": current_session_id,
        "last_posture_age_seconds": None if last_posture_at is None else round((datetime.now() - last_posture_at).total_seconds(), 1),
        "flashcard": pending_card,
    }
    pending_card = {"word": "", "trans": "", "type": ""}
    return jsonify(data)


@app.route("/api/review_summary")
def review_summary():
    dataset = request.args.get("dataset", "live")
    session_id = request.args.get("session_id") or None
    payload = logger.build_review_payload(session_id=session_id, dataset=dataset)
    return jsonify(payload)


@app.route("/api/reflection_coach", methods=["GET", "POST"])
def reflection_coach_summary():
    payload = (request.get_json(silent=True) or {}) if request.method == "POST" else request.args.to_dict()
    dataset = str(payload.get("dataset", "live")).strip().lower() or "live"
    session_id = str(payload.get("session_id", "")).strip() or None
    event_id = str(payload.get("event_id", "")).strip() or None
    learner_note = payload.get("learner_note", "")
    next_goal = payload.get("next_goal", "")
    use_llm = str(payload.get("use_llm", payload.get("use_model", "0"))).strip().lower() in {"1", "true", "yes", "on"}
    provider_override = str(payload.get("provider_override", "auto")).strip() or "auto"
    model_override = str(payload.get("model_override", "")).strip()
    return jsonify(
        reflection_coach.build_payload(
            session_id=session_id,
            dataset=dataset,
            event_id=event_id,
            learner_note=learner_note,
            next_goal=next_goal,
            use_llm=use_llm,
            provider_override=provider_override,
            model_override=model_override,
        )
    )


@app.route("/api/runtime_info")
def runtime_info():
    return jsonify(_runtime_info_payload())


@app.route("/api/reflection_provider_status")
def reflection_provider_status():
    provider_override = str(request.args.get("provider_override", "auto")).strip() or "auto"
    model_override = str(request.args.get("model_override", "")).strip()
    return jsonify(reflection_coach.provider_status(provider_override=provider_override, model_override=model_override))


@app.route("/api/reflection_compare", methods=["POST"])
def reflection_compare():
    payload = request.get_json(silent=True) or {}
    dataset = str(payload.get("dataset", "live")).strip().lower() or "live"
    session_id = str(payload.get("session_id", "")).strip() or None
    event_id = str(payload.get("event_id", "")).strip() or None
    learner_note = payload.get("learner_note", "")
    next_goal = payload.get("next_goal", "")
    requested_models = _clean_compare_models(payload.get("models", []))

    if len(requested_models) < 2:
        status = reflection_coach.provider_status(provider_override="ollama")
        fallback_models = [
            str(item.get("name", "")).strip()
            for item in (status.get("ollama", {}) or {}).get("available_models", [])
            if str(item.get("name", "")).strip()
        ]
        requested_models = _clean_compare_models(fallback_models[:2])

    if len(requested_models) < 2:
        return jsonify({
            "status": "error",
            "message": "At least two local Ollama models are required for comparison.",
        }), 400

    variants = [
        _build_reflection_compare_variant(dataset, session_id, event_id, learner_note, next_goal, model_name)
        for model_name in requested_models[:2]
    ]
    resolved_session_id = str((variants[0].get("payload", {}) or {}).get("session_id", session_id or "")).strip()
    resolved_dataset = str((variants[0].get("payload", {}) or {}).get("dataset", dataset)).strip().lower() or dataset
    return jsonify({
        "status": "ok",
        "dataset": resolved_dataset,
        "session_id": resolved_session_id,
        "compared_at": datetime.now().isoformat(timespec="seconds"),
        "request": {
            "provider": "ollama",
            "models": [variant.get("model", "") for variant in variants],
        },
        "variants": variants,
    })


@app.route("/api/reflection_snapshot", methods=["POST"])
def reflection_snapshot():
    payload = request.get_json(silent=True) or {}
    kind = str(payload.get("kind", "single")).strip().lower()
    snapshot_payload = payload.get("payload", {})
    if kind not in {"single", "compare"}:
        return jsonify({
            "status": "error",
            "message": f"Unsupported snapshot kind: {kind}",
        }), 400
    if not isinstance(snapshot_payload, dict) or not snapshot_payload:
        return jsonify({
            "status": "error",
            "message": "Snapshot payload is required.",
        }), 400
    return jsonify(_save_reflection_snapshot(kind, snapshot_payload))


@app.route("/api/presentation_missions", methods=["GET", "POST"])
def presentation_missions():
    if request.method == "GET":
        return jsonify({
            "status": "ok",
            "missions": presentation_companion.list_missions(),
        })

    payload = request.get_json(silent=True) or {}
    result = presentation_companion.save_mission(payload)
    return jsonify({
        "status": "ok",
        **result,
    })


@app.route("/api/presentation_missions/intake_extract", methods=["POST"])
def presentation_intake_extract():
    payload = request.get_json(silent=True) or {}
    result = presentation_companion.extract_intake(payload)
    status_code = 400 if result.get("status") == "error" else 200
    return jsonify(result), status_code


@app.route("/api/presentation_missions/<mission_id>")
def presentation_mission_detail(mission_id):
    result = presentation_companion.get_mission_bundle(mission_id)
    if not result:
        return jsonify({
            "status": "error",
            "message": "Presentation mission not found.",
        }), 404
    return jsonify({
        "status": "ok",
        **result,
    })


@app.route("/api/presentation_missions/<mission_id>/script", methods=["POST"])
def presentation_script_save(mission_id):
    payload = request.get_json(silent=True) or {}
    result = presentation_companion.save_script(mission_id, payload.get("script_sections", []))
    if not result:
        return jsonify({
            "status": "error",
            "message": "Presentation mission not found.",
        }), 404
    return jsonify({
        "status": "ok",
        **result,
    })


@app.route("/api/presentation_rehearsals", methods=["POST"])
def presentation_rehearsals():
    if request.files:
        audio_file = request.files.get("audio")
        try:
            payload = json.loads(request.form.get("payload", "{}") or "{}")
        except Exception:
            payload = {}
        audio_bytes = audio_file.read() if audio_file else None
        audio_name = audio_file.filename if audio_file else ""
        audio_type = audio_file.content_type if audio_file else ""
    else:
        payload = request.get_json(silent=True) or {}
        audio_bytes = None
        audio_name = ""
        audio_type = ""

    result = presentation_companion.create_rehearsal(
        payload=payload,
        audio_bytes=audio_bytes,
        audio_filename=audio_name,
        audio_content_type=audio_type,
    )
    status_code = 400 if result.get("status") == "error" else 200
    return jsonify(result), status_code


@app.route("/api/presentation_rehearsals/<rehearsal_id>")
def presentation_rehearsal_detail(rehearsal_id):
    result = presentation_companion.get_rehearsal_bundle(rehearsal_id)
    if not result:
        return jsonify({
            "status": "error",
            "message": "Presentation rehearsal not found.",
        }), 404
    return jsonify(result)


@app.route("/api/presentation_rehearsals/<rehearsal_id>/analyze", methods=["POST"])
def presentation_rehearsal_analyze(rehearsal_id):
    payload = request.get_json(silent=True) or {}
    result = presentation_companion.analyze_rehearsal(rehearsal_id, payload)
    status_code = 400 if result.get("status") == "error" else 200
    return jsonify(result), status_code


@app.route("/api/presentation_rehearsals/<rehearsal_id>/hud_summary")
def presentation_hud_summary(rehearsal_id):
    hud_summary = presentation_companion.get_hud_summary(rehearsal_id)
    if not hud_summary:
        return jsonify({
            "status": "error",
            "message": "Presentation rehearsal not found.",
        }), 404
    return jsonify({
        "status": "ok",
        "hud_summary": hud_summary,
    })


@app.route("/api/multimodal_blueprint")
def multimodal_blueprint():
    return jsonify(build_multimodal_blueprint())


@app.route("/api/rokid_adapter_blueprint")
def rokid_adapter_blueprint():
    return jsonify(build_rokid_adapter_blueprint())


@app.route("/api/rokid_frame_adapter_blueprint")
def rokid_frame_adapter_blueprint():
    return jsonify(rokid_frame_adapter.blueprint())


@app.route("/api/rokid_scene_tuning", methods=["GET", "POST"])
def rokid_scene_tuning():
    if request.method == "GET":
        return jsonify({
            "posture": posture.get_scene_tuning(),
            "frame_adapter": rokid_frame_adapter.get_scene_tuning(),
        })

    payload = request.json or {}
    posture_config = posture.update_scene_tuning(payload.get("posture", {}))
    frame_config = rokid_frame_adapter.update_scene_tuning(payload.get("frame_adapter", {}))
    return jsonify({
        "status": "ok",
        "posture": posture_config,
        "frame_adapter": frame_config,
    })


@app.route("/api/rokid_scene_tuning/preset", methods=["POST"])
def rokid_scene_tuning_preset():
    payload = request.json or {}
    preset_id = str(payload.get("preset_id", "")).strip().lower()
    preset = _scene_preset_payload(preset_id)
    if not preset:
        return jsonify({
            "status": "error",
            "message": f"Unknown preset: {preset_id or 'missing'}",
        }), 400

    posture.reset_scene_tuning()
    rokid_frame_adapter.reset_scene_tuning()
    posture_config = posture.update_scene_tuning(preset["posture"])
    frame_config = rokid_frame_adapter.update_scene_tuning(preset["frame_adapter"])
    return jsonify({
        "status": "ok",
        "preset": {
            "preset_id": preset["preset_id"],
            "label": preset["label"],
            "summary": preset["summary"],
        },
        "posture": posture_config,
        "frame_adapter": frame_config,
    })


@app.route("/api/rokid_scene_tuning/reset", methods=["POST"])
def rokid_scene_tuning_reset():
    return jsonify({
        "status": "ok",
        "posture": posture.reset_scene_tuning(),
        "frame_adapter": rokid_frame_adapter.reset_scene_tuning(),
    })


@app.route("/api/rokid_scene_calibration")
def rokid_scene_calibration():
    return jsonify({
        "presets": [_scene_preset_payload(preset_id) for preset_id in ROKID_SCENE_PRESETS.keys()],
        "active_tuning": {
            "posture": posture.get_scene_tuning(),
            "frame_adapter": rokid_frame_adapter.get_scene_tuning(),
        },
        "diagnosis": _build_scene_calibration_diagnosis(),
    })


@app.route("/api/rokid_scene_profiles")
def rokid_scene_profiles():
    store = _load_scene_profile_store()
    profiles = list(store.get("profiles", []))
    profiles.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
    return jsonify({
        "status": "ok",
        "store_path": ROKID_PROFILE_STORE_PATH,
        "profiles": profiles,
    })


@app.route("/api/rokid_scene_profiles/save", methods=["POST"])
def save_rokid_scene_profile():
    payload = request.json or {}
    profile_name = str(payload.get("profile_name", "")).strip()
    if not profile_name:
        return jsonify({
            "status": "error",
            "message": "Provide `profile_name` before saving a Rokid scene calibration profile.",
        }), 400

    store = _load_scene_profile_store()
    profile = _build_scene_profile_payload(
        profile_name=profile_name,
        task_mode=payload.get("task_mode") or posture.task_mode,
        notes=payload.get("notes", ""),
        source_preset=payload.get("source_preset", ""),
    )
    store["profiles"] = [item for item in store.get("profiles", []) if item.get("profile_id") != profile["profile_id"]]
    store["profiles"].append(profile)
    _save_scene_profile_store(store)
    return jsonify({
        "status": "ok",
        "saved_profile": profile,
        "profile_count": len(store["profiles"]),
    })


@app.route("/api/rokid_scene_profiles/load", methods=["POST"])
def load_rokid_scene_profile():
    payload = request.json or {}
    profile_id = str(payload.get("profile_id", "")).strip()
    if not profile_id:
        return jsonify({
            "status": "error",
            "message": "Provide `profile_id` before loading a Rokid scene calibration profile.",
        }), 400

    store, profile = _find_scene_profile(profile_id)
    if not profile:
        return jsonify({
            "status": "error",
            "message": f"Profile not found: {profile_id}",
        }), 404

    posture.reset_scene_tuning()
    rokid_frame_adapter.reset_scene_tuning()
    posture_config = posture.update_scene_tuning(profile.get("posture", {}))
    frame_config = rokid_frame_adapter.update_scene_tuning(profile.get("frame_adapter", {}))
    if profile.get("task_mode"):
        posture.set_task_mode(profile.get("task_mode"))
    return jsonify({
        "status": "ok",
        "loaded_profile": profile,
        "posture": posture_config,
        "frame_adapter": frame_config,
    })


@app.route("/api/rokid_scene_profiles/export")
def export_rokid_scene_profile():
    profile_id = str(request.args.get("profile_id", "")).strip()
    store = _load_scene_profile_store()
    payload = store
    filename = "rokid_scene_profiles.json"
    if profile_id:
        _, profile = _find_scene_profile(profile_id)
        if not profile:
            return jsonify({
                "status": "error",
                "message": f"Profile not found: {profile_id}",
            }), 404
        payload = profile
        filename = f"{profile_id}.json"

    response = Response(
        json.dumps(payload, indent=2, ensure_ascii=False),
        mimetype="application/json",
    )
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@app.route("/calibrate")
def calibrate():
    session_id = _start_new_session(reset_posture=True)
    return jsonify({"status": "ok", "session_id": session_id})


@app.route("/reset_session")
def reset_session():
    session_id = _start_new_session(reset_posture=False)
    return jsonify({"status": "ok", "session_id": session_id})


@app.route("/task_mode", methods=["POST"])
def set_task_mode():
    data = request.json or {}
    mode = posture.set_task_mode(data.get("task_mode", "reading"))
    return jsonify({
        "status": "ok",
        "task_mode": mode,
        "message": f"Task mode switched to {mode}. Hold steady or recalibrate if posture changed.",
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
