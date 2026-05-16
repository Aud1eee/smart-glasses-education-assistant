import os
from datetime import datetime

import bootstrap_windows_runtime  # noqa: F401
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
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
    "motion_source": "default",
    "pose_source": "simulator",
    "frame_source": "simulator",
    "timestamp_ms": None,
}


def _build_session_id(now=None):
    now = now or datetime.now()
    return now.strftime("session-%Y%m%d-%H%M%S-%f")


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
        "motion_source": packet.motion_source,
        "pose_source": packet.pose_source,
        "frame_source": packet.frame_source,
        "timestamp_ms": packet.timestamp_ms,
    }


def _start_new_session(reset_posture=False):
    global latest_session, latest_difficulty, latest_input, sample_counter, last_posture_at, current_session_id
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
        message = "Frame adapter scaffold is active, but the current runtime does not provide OpenCV face detection support."
    elif packet.tracking_state == "face_missing":
        message = "Frame received, but no stable face box was detected; the session will bias toward signal-check behavior."
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
