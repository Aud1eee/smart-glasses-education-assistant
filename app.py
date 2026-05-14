import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

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
auto_recall_enabled = os.getenv("ENABLE_AUTO_RECALL", "0").lower() in {"1", "true", "yes", "on"}

pending_card = {"word": "", "trans": "", "type": ""}
latest_session = focus_session.update({
    "cognitive_load": 0,
    "load_level": "low",
    "focus_score": 100,
})


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/v1/posture", methods=["POST"])
def handle_posture():
    global pending_card, latest_session
    data = request.json or {}
    res = posture.process(data.get("pitch", 0))
    latest_session = focus_session.update(res)
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
    )

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
    global pending_card, latest_session
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
        "flashcard": pending_card,
    }
    pending_card = {"word": "", "trans": "", "type": ""}
    return jsonify(data)


@app.route("/calibrate")
def calibrate():
    posture.calibrate()
    return "ok"


@app.route("/reset_session")
def reset_session():
    global latest_session
    focus_session.reset()
    latest_session = focus_session.update({
        "cognitive_load": posture.cognitive_load,
        "load_level": posture.load_level,
        "focus_score": 100,
    })
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
