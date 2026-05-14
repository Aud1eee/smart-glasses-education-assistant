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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/v1/posture", methods=["POST"])
def handle_posture():
    global pending_card, latest_session, latest_difficulty, sample_counter
    data = request.json or {}
    sample_counter += 1
    timestamp_text = datetime.now().strftime("%H:%M:%S")
    res = posture.process(data.get("pitch", 0))
    latest_session = focus_session.update(res)
    latest_difficulty = difficulty_marker.update(
        res,
        latest_session,
        timestamp_text=timestamp_text,
        sample_index=sample_counter,
    )
    logger.log_study(
        res["relative_pitch"],
        res["is_alert"],
        res["focus_score"],
        res["stability"],
        res["cognitive_load"],
        res["load_level"],
        latest_session["guidance"],
        latest_session["phase"],
        latest_session["elapsed_seconds"],
        latest_session["cycle_index"],
        timestamp_text=timestamp_text,
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
    global pending_card, latest_session, latest_difficulty
    latest_session = focus_session.update({
        "cognitive_load": posture.cognitive_load,
        "load_level": posture.load_level,
        "focus_score": posture.focus_score,
    })
    data = {
        "rel_pitch": round(abs(posture.smooth_pitch - posture.base_pitch), 1),
        "stability": posture.current_stability,
        "is_alert": posture.is_alert,
        "focus_score": posture.focus_score,
        "cognitive_load": posture.cognitive_load,
        "load_level": posture.load_level,
        "load_reason": posture.load_reason,
        "session": latest_session,
        "difficulty": {
            "active_event": latest_difficulty.get("active_event"),
            "last_event": latest_difficulty.get("last_event"),
            "event_count": latest_difficulty.get("event_count", 0),
        },
        "flashcard": pending_card,
    }
    pending_card = {"word": "", "trans": "", "type": ""}
    return jsonify(data)


@app.route("/calibrate")
def calibrate():
    posture.calibrate()
    difficulty_marker.reset()
    return "ok"


@app.route("/reset_session")
def reset_session():
    global latest_session, latest_difficulty
    focus_session.reset()
    difficulty_marker.reset()
    latest_session = focus_session.update({
        "cognitive_load": posture.cognitive_load,
        "load_level": posture.load_level,
        "focus_score": 100,
    })
    latest_difficulty = {
        "active_event": None,
        "completed_event": None,
        "last_event": difficulty_marker.last_completed_event,
        "event_count": difficulty_marker.event_counter,
    }
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
