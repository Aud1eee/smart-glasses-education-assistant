import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from core.difficulty_marker import DifficultyEventMarker
from core.edu import EduEngine
from core.focus_session import FocusSessionEngine
from core.posture import PostureEngine
from core.vision import VisionEngine
from utils.storage import DataLogger


load_dotenv()

app = Flask(__name__, template_folder="web", static_folder="web")
CORS(app)

logger = DataLogger()
posture = PostureEngine()
vision = VisionEngine()
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


def _start_new_session(reset_posture=False):
    global latest_session, latest_difficulty, sample_counter, last_posture_at, current_session_id
    if reset_posture:
        posture.calibrate()
    focus_session.reset()
    difficulty_marker.reset()
    current_session_id = _build_session_id()
    latest_session = focus_session.snapshot()
    latest_difficulty = _new_difficulty_snapshot()
    sample_counter = 0
    last_posture_at = None
    return current_session_id


current_session_id = _build_session_id()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/v1/posture", methods=["POST"])
def handle_posture():
    global pending_card, latest_session, latest_difficulty, sample_counter, last_posture_at
    data = request.json or {}
    sample_counter += 1
    last_posture_at = datetime.now()
    timestamp_text = datetime.now().strftime("%H:%M:%S")
    res = posture.process(data.get("pitch", 0))
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
        stability=res["stability"],
        cognitive_load=res["cognitive_load"],
        load_level=res["load_level"],
        task_mode=res["task_mode"],
        behavioral_alignment=res["behavioral_alignment"],
        behavioral_level=res["behavioral_level"],
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
    if latest_difficulty["completed_event"]:
        logger.log_difficulty_event(latest_difficulty["completed_event"])

    if auto_recall_enabled and not pending_card.get("word"):
        quiz = edu.check_active_recall()
        if quiz:
            pending_card = quiz
            print(f"[EDU] Active recall triggered: {quiz['word']}")

    return jsonify({"status": "ok"})


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
    global pending_card, latest_session, latest_difficulty, last_posture_at
    latest_session = focus_session.snapshot()
    data = {
        "rel_pitch": round(abs(posture.smooth_pitch - posture.base_pitch), 1),
        "stability": posture.current_stability,
        "is_alert": posture.is_alert,
        "focus_score": posture.focus_score,
        "cognitive_load": posture.cognitive_load,
        "load_level": posture.load_level,
        "load_reason": posture.load_reason,
        "task_mode": posture.task_mode,
        "behavioral_alignment": posture.behavioral_alignment,
        "behavioral_level": posture.behavioral_level,
        "fatigue_risk": posture.fatigue_risk,
        "fatigue_level": posture.fatigue_level,
        "uncertainty_score": posture.uncertainty_score,
        "confidence_level": posture.confidence_level,
        "session": latest_session,
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
