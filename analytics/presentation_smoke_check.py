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
    assert mission["presentation_state"]["active_slide_index"] >= 1, "Missing initial active slide."
    assert mission["presentation_state"]["control_source"] == "phone", "Phone should be the default controller."

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
    updated_mission = script_response.get_json()["mission"]
    section_ids = [section["section_id"] for section in updated_mission["script_sections"]]
    assert len(section_ids) >= 2, "Need at least two slide cards for presentation control checks."

    state_response = client.get(f"/api/presentation_missions/{mission_id}/presentation_state")
    assert state_response.status_code == 200, state_response.get_data(as_text=True)
    state_payload = state_response.get_json()["presentation_state"]
    assert state_payload["active_slide_index"] == 1, "Expected the first slide to be active."

    mode_response = client.post(
        f"/api/presentation_missions/{mission_id}/presentation_state",
        json={
            "presentation_mode": "present",
            "control_source": "phone",
            "active_section_id": section_ids[0],
        },
    )
    assert mode_response.status_code == 200, mode_response.get_data(as_text=True)
    mode_payload = mode_response.get_json()["presentation_state"]
    assert mode_payload["presentation_mode"] == "present", "Presentation mode did not update."

    next_response = client.post(
        f"/api/presentation_missions/{mission_id}/presentation_control",
        json={
            "action": "next",
            "control_source": "rokid_button",
        },
    )
    assert next_response.status_code == 200, next_response.get_data(as_text=True)
    next_payload = next_response.get_json()["presentation_state"]
    assert next_payload["active_section_id"] == section_ids[1], "Next control did not advance to the second card."
    assert next_payload["last_control_source"] == "rokid_button", "Expected the last control source to be rokid_button."

    cue_response = client.post(
        f"/api/presentation_missions/{mission_id}/presentation_control",
        json={
            "action": "toggle_cue",
            "control_source": "rokid_button",
        },
    )
    assert cue_response.status_code == 200, cue_response.get_data(as_text=True)
    cue_payload = cue_response.get_json()["presentation_state"]
    assert cue_payload["cue_view"] == "hidden", "Cue toggle did not hide the cue view."

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
    assert analysis["hud_summary"]["active_slide_index"] >= 1, "HUD summary should expose the active slide index."
    assert analysis["hud_summary"]["control_source"] in {"phone", "rokid_button"}, "HUD summary should expose the control source."

    hud_response = client.get(f"/api/presentation_rehearsals/{rehearsal_id}/hud_summary")
    assert hud_response.status_code == 200, hud_response.get_data(as_text=True)
    hud_payload = hud_response.get_json()
    assert hud_payload["hud_summary"]["pace_status"], "Missing HUD pace status."
    assert hud_payload["hud_summary"]["active_slide_title"], "Missing HUD active slide title."

    print(json.dumps({
        "mission_id": mission_id,
        "rehearsal_id": rehearsal_id,
        "active_slide_index": hud_payload["hud_summary"]["active_slide_index"],
        "control_source": hud_payload["hud_summary"]["control_source"],
        "pace_status": analysis["feedback"]["pace_status"],
        "hud_status": hud_payload["hud_summary"]["current_or_final_status"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
