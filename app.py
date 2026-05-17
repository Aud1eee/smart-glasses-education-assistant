import json
import os
import re
from datetime import datetime

import bootstrap_windows_runtime  # noqa: F401
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory, Response
from flask_cors import CORS

from core.difficulty_marker import DifficultyEventMarker
from core.edu import EduEngine
from core.focus_session import FocusSessionEngine
from core.multimodal_schema import build_multimodal_blueprint
from core.posture import PostureEngine
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
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROKID_PROFILE_STORE_PATH = os.path.join(PROJECT_ROOT, "data", "rokid_scene_profiles.json")

logger = DataLogger()
posture = PostureEngine()
vision = VisionEngine()
rokid_frame_adapter = RokidFrameAdapter()
edu = EduEngine(logger.vocab_path)
focus_session = FocusSessionEngine()
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
