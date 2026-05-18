import os

import bootstrap_windows_runtime  # noqa: F401
from flask import Flask, jsonify, request


app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "provider": "mock-reflection-provider",
        "service": "reflection-remote-mock",
    })


@app.post("/reflect")
def reflect():
    payload = request.get_json(silent=True) or {}
    draft = payload.get("draft") or {}
    coach_summary = draft.get("coach_summary") or {}
    questions = draft.get("reflection_questions") or []
    experiments = draft.get("next_session_experiments") or []
    learner_note = str(payload.get("learner_note", "")).strip()
    next_goal = str(payload.get("next_goal", "")).strip()

    headline = coach_summary.get("headline") or "Mock reflection provider summary"
    overview = coach_summary.get("overview") or "No overview was supplied by the draft payload."
    why_it_matters = coach_summary.get("why_it_matters") or "No explanation was supplied by the draft payload."
    next_boundary = coach_summary.get("next_boundary") or "No next-session boundary was supplied by the draft payload."
    coach_memo = draft.get("coach_memo") or "No coach memo was supplied by the draft payload."

    if learner_note:
        overview = f"{overview} Learner note acknowledged: {learner_note}"
    if next_goal:
        next_boundary = f"{next_boundary} Remote provider goal focus: {next_goal}"

    return jsonify({
        "headline": headline,
        "overview": overview,
        "why_it_matters": why_it_matters,
        "next_boundary": next_boundary,
        "coach_memo": f"{coach_memo} [Remote mock provider]",
        "reflection_questions": questions[:3] if len(questions) >= 3 else [
            {"question": "What part of this session should be replayed first?"},
            {"question": "What process cue changed before the session became harder to regulate?"},
            {"question": "What one boundary should stay tighter next time?"},
        ],
        "next_session_experiments": experiments[:3] if len(experiments) >= 3 else [
            {
                "title": "Replay one target",
                "detail": "Replay the strongest segment while keeping one source stable.",
                "success_marker": "The next session shows less switching pressure.",
            },
            {
                "title": "Shorter retry",
                "detail": "Shorten the replay block and inspect the hardest moment first.",
                "success_marker": "The next review starts cleaner and stays more focused.",
            },
            {
                "title": "Boundary note",
                "detail": "Write down one concrete regulation boundary before restarting.",
                "success_marker": "The next session begins with a clearer self-coaching rule.",
            },
        ],
        "provider": "mock-reflection-provider",
    })


if __name__ == "__main__":
    host = os.getenv("REFLECTION_REMOTE_HOST", "127.0.0.1")
    port = int(os.getenv("REFLECTION_REMOTE_PORT", "5051"))
    app.run(host=host, port=port, debug=False)
