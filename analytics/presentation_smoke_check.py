import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import app


SAMPLE_TASK_TEXT = """
Course: Research Methods
Title: Mini Presentation on Interview Reliability
Deadline: May 28
You need to give a 6 minute class presentation to your classmates and teacher.
Include one example, keep the conclusion short, and show at least one slide with evidence.
"""


def main():
    client = app.test_client()

    page_response = client.get("/presentation")
    assert page_response.status_code == 200, page_response.get_data(as_text=True)

    extract_response = client.post(
        "/api/presentation_missions/intake_extract",
        json={
            "task_text": SAMPLE_TASK_TEXT,
            "use_llm": False,
        },
    )
    assert extract_response.status_code == 200, extract_response.get_data(as_text=True)
    extract_payload = extract_response.get_json()
    candidates = extract_payload["candidates"]
    sections = extract_payload["suggested_sections"]
    assert candidates["title"], "Missing extracted title."
    assert sections, "Missing suggested sections."

    mission_response = client.post(
        "/api/presentation_missions",
        json={
            **candidates,
            "intake_task_text": SAMPLE_TASK_TEXT,
            "script_sections": sections,
        },
    )
    assert mission_response.status_code == 200, mission_response.get_data(as_text=True)
    mission_payload = mission_response.get_json()
    mission = mission_payload["mission"]
    mission_id = mission["mission_id"]
    assert mission_id, "Missing mission id."

    script_sections = []
    for index, section in enumerate(mission["script_sections"], start=1):
        script_sections.append({
            **section,
            "outline": f"Point {index} outline",
            "speaker_notes": f"This is the student written note for {section['name']}.",
            "cue_cards": f"Pause before {section['name']}.",
        })

    script_response = client.post(
        f"/api/presentation_missions/{mission_id}/script",
        json={"script_sections": script_sections},
    )
    assert script_response.status_code == 200, script_response.get_data(as_text=True)

    total_duration_seconds = sum(section["target_seconds"] for section in script_sections) + 18
    rehearsal_response = client.post(
        "/api/presentation_rehearsals",
        json={
            "mission_id": mission_id,
            "audio_source": "browser_mic",
            "total_duration_seconds": total_duration_seconds,
            "section_timings": [
                {
                    "section_id": section["section_id"],
                    "name": section["name"],
                    "target_seconds": section["target_seconds"],
                    "actual_seconds": section["target_seconds"] + (8 if index == 0 else 2),
                }
                for index, section in enumerate(script_sections)
            ],
            "transcript_text": "Today I will explain interview reliability and use one short example before the conclusion.",
            "transcript_source": "manual",
            "self_rating": 3,
            "notes": "Opening still felt a little long.",
        },
    )
    assert rehearsal_response.status_code == 200, rehearsal_response.get_data(as_text=True)
    rehearsal_payload = rehearsal_response.get_json()
    rehearsal = rehearsal_payload["rehearsal"]
    rehearsal_id = rehearsal["rehearsal_id"]
    assert rehearsal_id, "Missing rehearsal id."

    analyze_response = client.post(
        f"/api/presentation_rehearsals/{rehearsal_id}/analyze",
        json={"use_llm": False},
    )
    assert analyze_response.status_code == 200, analyze_response.get_data(as_text=True)
    analyze_payload = analyze_response.get_json()
    analysis = analyze_payload["rehearsal"]["analysis"]
    assert analysis["transcript"]["status"] in {"available", "unavailable", "missing"}
    assert analysis["feedback"]["one_main_issue"], "Missing main issue."
    assert analysis["hud_summary"]["mode"] == "rehearse_summary"

    hud_response = client.get(f"/api/presentation_rehearsals/{rehearsal_id}/hud_summary")
    assert hud_response.status_code == 200, hud_response.get_data(as_text=True)
    hud_payload = hud_response.get_json()
    assert hud_payload["hud_summary"]["pace_status"], "Missing HUD pace status."

    print(json.dumps({
        "mission_id": mission_id,
        "rehearsal_id": rehearsal_id,
        "pace_status": analysis["feedback"]["pace_status"],
        "hud_status": hud_payload["hud_summary"]["current_or_final_status"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
