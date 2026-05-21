import json
import os
import sys
import time

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


def build_teleprompter_script(section_name, index):
    return " ".join([
        f"Slide {index} opens by naming {section_name} and telling the audience what decision or takeaway this part supports.",
        f"The student then explains one concrete detail for {section_name} and connects it back to the assignment requirement without reading every bullet.",
        f"Next comes a short example for {section_name} so the speaker can pause, point at the visual, and keep the audience oriented.",
        f"The final sentence for {section_name} sets up the transition into the next slide and gives the speaker a natural breath before moving on.",
        f"One more reminder on slide {index} helps the speaker stress the evidence, slow the pace, and check that the listeners still follow the argument.",
        f"The closing line on slide {index} turns the current idea into a bridge so the next slide starts smoothly instead of feeling like a sudden jump.",
    ])


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
            "teleprompter_script": build_teleprompter_script(section["name"], index),
            "cue_cards": f"Pause before {section['name']}.",
        })

    script_response = client.post(
        f"/api/presentation_missions/{mission_id}/script",
        json={"script_sections": script_sections},
    )
    assert script_response.status_code == 200, script_response.get_data(as_text=True)
    updated_mission = script_response.get_json()["mission"]
    section_ids = [section["section_id"] for section in updated_mission["script_sections"]]
    assert len(section_ids) >= 3, "Need at least three slide cards for teleprompter control checks."

    state_response = client.get(f"/api/presentation_missions/{mission_id}/presentation_state")
    assert state_response.status_code == 200, state_response.get_data(as_text=True)
    state_payload = state_response.get_json()["presentation_state"]
    assert state_payload["active_slide_index"] == 1, "Expected the first slide to be active."
    assert state_payload["next_card"]["slide_index"] >= 2, "Expected a next slide card in the presentation state."
    assert state_payload["active_chunk_count"] >= 2, "Expected teleprompter chunking for the first slide."
    assert state_payload["chunk_progress_label"].startswith("1/"), "Expected the first slide to begin on teleprompter chunk 1."
    assert state_payload["control_hints"]["rokid_button"]["button_map"]["single_press"] == "next_chunk", "Missing Rokid single-press chunk mapping."
    assert state_payload["control_hints"]["rokid_button"]["button_map"]["double_press"] == "previous_chunk", "Missing Rokid double-press chunk mapping."
    assert state_payload["control_hints"]["rokid_button"]["button_map"]["long_press"] == "next_slide", "Missing Rokid long-press slide mapping."

    sync_response = client.get(f"/api/presentation_missions/{mission_id}/companion_sync")
    assert sync_response.status_code == 200, sync_response.get_data(as_text=True)
    sync_payload = sync_response.get_json()
    assert sync_payload["companion_sync"]["controller_path"].endswith(f"mission_id={mission_id}"), "Missing phone controller path."
    assert sync_payload["live_hud"]["mode"] == "presentation_live", "Expected live presentation HUD payload."
    assert sync_payload["companion_sync"]["bridge_state"]["bridge_pin"], "Missing bridge pairing pin."
    assert sync_payload["companion_sync"]["pairing_state"]["pairing_status"] == "inactive", "Pairing should start inactive."

    pairing_state_response = client.get(f"/api/presentation_missions/{mission_id}/pairing_state")
    assert pairing_state_response.status_code == 200, pairing_state_response.get_data(as_text=True)
    pairing_state_payload = pairing_state_response.get_json()
    assert pairing_state_payload["pairing_state"]["pairing_status"] == "inactive", "Pairing state should start inactive."
    assert pairing_state_payload["pairing_state"]["status_label"] == "Pairing inactive", "Expected a readable inactive pairing label."
    assert pairing_state_payload["pairing_state"]["next_step"], "Expected a next-step hint for pairing."

    pairing_start_short_response = client.post(
        f"/api/presentation_missions/{mission_id}/pairing_start",
        json={
            "surface": "phone",
            "window_seconds": 2,
        },
    )
    assert pairing_start_short_response.status_code == 200, pairing_start_short_response.get_data(as_text=True)
    pairing_start_short_payload = pairing_start_short_response.get_json()
    assert pairing_start_short_payload["pairing_state"]["pairing_status"] == "waiting", "Short pairing window should open in waiting mode."
    assert pairing_start_short_payload["pairing_state"]["pairing_code"], "Short pairing window should issue a code."
    assert pairing_start_short_payload["pairing_state"]["join_ready"] is True, "Waiting pairing state should be join-ready."
    assert pairing_start_short_payload["pairing_state"]["countdown_label"], "Waiting pairing state should expose a countdown label."

    time.sleep(3)

    pairing_expired_response = client.get(f"/api/presentation_missions/{mission_id}/pairing_state")
    assert pairing_expired_response.status_code == 200, pairing_expired_response.get_data(as_text=True)
    pairing_expired_payload = pairing_expired_response.get_json()
    assert pairing_expired_payload["pairing_state"]["pairing_status"] == "expired", "Pairing window should expire after the short timeout."
    assert pairing_expired_payload["pairing_state"]["status_label"] == "Pairing code expired", "Expected an expired pairing label."

    pairing_join_expired_response = client.post(
        f"/api/presentation_missions/{mission_id}/pairing_join",
        json={
            "surface": "rokid_hud",
            "device_label": "expired_attempt",
            "pairing_code": pairing_start_short_payload["pairing_state"]["pairing_code"],
        },
    )
    assert pairing_join_expired_response.status_code == 400, pairing_join_expired_response.get_data(as_text=True)

    pairing_start_response = client.post(
        f"/api/presentation_missions/{mission_id}/pairing_start",
        json={
            "surface": "phone",
            "window_seconds": 180,
        },
    )
    assert pairing_start_response.status_code == 200, pairing_start_response.get_data(as_text=True)
    pairing_start_payload = pairing_start_response.get_json()
    pairing_code = pairing_start_payload["pairing_state"]["pairing_code"]
    assert pairing_start_payload["pairing_state"]["pairing_status"] == "waiting", "Expected the second pairing window to open."
    assert pairing_code, "Missing active pairing code."

    pairing_join_response = client.post(
        f"/api/presentation_missions/{mission_id}/pairing_join",
        json={
            "surface": "rokid_hud",
            "device_label": "smoke_rokid_hud",
            "pairing_code": pairing_code,
        },
    )
    assert pairing_join_response.status_code == 200, pairing_join_response.get_data(as_text=True)
    pairing_join_payload = pairing_join_response.get_json()
    assert pairing_join_payload["pairing_state"]["pairing_status"] == "paired", "Expected pairing join to move into paired mode."
    assert pairing_join_payload["pairing_state"]["paired_surface"] == "rokid_hud", "Expected Rokid HUD to be the paired surface."
    assert pairing_join_payload["pairing_state"]["status_label"] == "Companion joined", "Expected a paired pairing label."

    bridge_state_response = client.get(f"/api/presentation_missions/{mission_id}/bridge_state")
    assert bridge_state_response.status_code == 200, bridge_state_response.get_data(as_text=True)
    bridge_state_payload = bridge_state_response.get_json()
    bridge_pin = bridge_state_payload["bridge_state"]["bridge_pin"]
    assert bridge_state_payload["bridge_state"]["bridge_status"] == "waiting", "Expected the bridge to start in waiting mode."

    phone_sync_response = client.post(
        f"/api/presentation_missions/{mission_id}/companion_sync",
        json={
            "surface": "phone",
            "event": "phone_open",
        },
    )
    assert phone_sync_response.status_code == 200, phone_sync_response.get_data(as_text=True)
    phone_sync_payload = phone_sync_response.get_json()
    assert phone_sync_payload["companion_sync"]["surface_status"]["phone"]["status"] in {"active", "idle"}, "Phone surface should be marked as connected."

    bridge_claim_response = client.post(
        f"/api/presentation_missions/{mission_id}/bridge_claim",
        json={
            "surface": "phone",
            "bridge_pin": bridge_pin,
            "device_label": "smoke_phone",
        },
    )
    assert bridge_claim_response.status_code == 200, bridge_claim_response.get_data(as_text=True)
    bridge_claim_payload = bridge_claim_response.get_json()
    assert bridge_claim_payload["bridge_state"]["bridge_status"] == "paired", "Expected the bridge to be paired after phone claim."
    assert bridge_claim_payload["bridge_state"]["claimed_surface"] == "phone", "Expected the phone controller to hold the bridge claim."

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
    assert mode_payload["active_chunk_index"] == 0, "Presentation mode should start at the first teleprompter chunk."

    next_response = client.post(
        f"/api/presentation_missions/{mission_id}/presentation_control",
        json={
            "action": "next",
            "control_source": "rokid_button",
        },
    )
    assert next_response.status_code == 200, next_response.get_data(as_text=True)
    next_payload = next_response.get_json()["presentation_state"]
    assert next_payload["active_section_id"] == section_ids[0], "Step navigation should stay on the current slide while more chunks remain."
    assert next_payload["active_chunk_index"] == 1, "Next control should advance to the second teleprompter chunk."
    assert next_payload["last_control_source"] == "rokid_button", "Expected the last control source to be rokid_button."
    assert next_payload["next_card"]["slide_index"] >= 2, "Expected the next slide card to stay queued while chunking within the active slide."

    next_slide_response = client.post(
        f"/api/presentation_missions/{mission_id}/presentation_control",
        json={
            "action": "next_slide",
            "control_source": "rokid_button",
        },
    )
    assert next_slide_response.status_code == 200, next_slide_response.get_data(as_text=True)
    next_slide_payload = next_slide_response.get_json()["presentation_state"]
    assert next_slide_payload["active_section_id"] == section_ids[1], "Next-slide control did not advance to the second card."
    assert next_slide_payload["active_chunk_index"] == 0, "Next-slide control should reset chunk navigation on the new slide."
    assert next_slide_payload["active_chunk_count"] >= 2, "Expected teleprompter chunking to continue on the second slide."

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

    rokid_event_single_response = client.post(
        f"/api/presentation_missions/{mission_id}/rokid_event",
        json={
            "button_event": "single_press",
            "presentation_mode": "present",
        },
    )
    assert rokid_event_single_response.status_code == 200, rokid_event_single_response.get_data(as_text=True)
    rokid_event_single_payload = rokid_event_single_response.get_json()
    assert rokid_event_single_payload["rokid_event"]["mapped_action"] == "next_chunk", "Expected single_press to map to next_chunk."
    assert rokid_event_single_payload["presentation_state"]["active_section_id"] == section_ids[1], "single_press should stay on the current slide while chunks remain."
    assert rokid_event_single_payload["presentation_state"]["active_chunk_index"] == 1, "single_press should advance to the next teleprompter chunk."
    assert rokid_event_single_payload["companion_sync"]["last_button_event"] == "single_press", "Missing tracked Rokid single_press event."

    rokid_event_long_response = client.post(
        f"/api/presentation_missions/{mission_id}/rokid_event",
        json={
            "button_event": "long_press",
            "presentation_mode": "present",
        },
    )
    assert rokid_event_long_response.status_code == 200, rokid_event_long_response.get_data(as_text=True)
    rokid_event_long_payload = rokid_event_long_response.get_json()
    assert rokid_event_long_payload["rokid_event"]["mapped_action"] == "next_slide", "Expected long_press to map to next_slide."
    assert rokid_event_long_payload["presentation_state"]["active_section_id"] == section_ids[2], "long_press should advance to the third slide."
    assert rokid_event_long_payload["presentation_state"]["active_chunk_index"] == 0, "long_press should reset chunk navigation on the next slide."
    assert rokid_event_long_payload["companion_sync"]["last_button_event"] == "long_press", "Missing tracked Rokid long_press event."

    rokid_event_double_response = client.post(
        f"/api/presentation_missions/{mission_id}/rokid_event",
        json={
            "button_event": "double_press",
            "presentation_mode": "present",
        },
    )
    assert rokid_event_double_response.status_code == 200, rokid_event_double_response.get_data(as_text=True)
    rokid_event_double_payload = rokid_event_double_response.get_json()
    assert rokid_event_double_payload["rokid_event"]["mapped_action"] == "previous_chunk", "Expected double_press to map to previous_chunk."
    assert rokid_event_double_payload["presentation_state"]["active_section_id"] == section_ids[1], "double_press should fall back to the previous slide when the current slide is at chunk 1."
    assert rokid_event_double_payload["presentation_state"]["active_chunk_index"] == rokid_event_double_payload["presentation_state"]["active_chunk_count"] - 1, "double_press should land on the previous slide's final teleprompter chunk."
    assert rokid_event_double_payload["companion_sync"]["last_button_event"] == "double_press", "Missing tracked Rokid double_press event."

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
    assert analysis["hud_summary"]["presentation_mode"] == "present", "HUD summary should reflect the presentation mode."
    assert analysis["hud_summary"]["cue_view"] == "hidden", "HUD summary should reflect the latest cue visibility."
    assert analysis["hud_summary"]["active_chunk_count"] >= 1, "HUD summary should expose teleprompter chunk counts."
    assert analysis["hud_summary"]["chunk_progress_label"], "HUD summary should expose teleprompter chunk progress."

    hud_response = client.get(f"/api/presentation_rehearsals/{rehearsal_id}/hud_summary")
    assert hud_response.status_code == 200, hud_response.get_data(as_text=True)
    hud_payload = hud_response.get_json()
    assert hud_payload["hud_summary"]["pace_status"], "Missing HUD pace status."
    assert hud_payload["hud_summary"]["active_slide_title"], "Missing HUD active slide title."
    assert "next_slide_index" in hud_payload["hud_summary"], "Missing next slide index in HUD summary."

    live_hud_response = client.get(f"/api/presentation_missions/{mission_id}/live_hud")
    assert live_hud_response.status_code == 200, live_hud_response.get_data(as_text=True)
    live_hud_payload = live_hud_response.get_json()
    assert live_hud_payload["live_hud"]["active_slide_index"] >= 1, "Live HUD should expose the active slide index."
    assert live_hud_payload["live_hud"]["surface_status"]["rokid_hud"] in {"active", "idle"}, "Live HUD pull should mark the Rokid HUD surface as seen."
    assert live_hud_payload["live_hud"]["claimed_surface"] == "phone", "Live HUD should reflect the current bridge owner."
    assert live_hud_payload["live_hud"]["pairing_status"] == "paired", "Live HUD should reflect the active paired session."
    assert live_hud_payload["live_hud"]["pairing_status_label"] == "Companion joined", "Live HUD should expose the pairing status label."
    assert live_hud_payload["live_hud"]["paired_surface"] == "rokid_hud", "Live HUD should expose the paired Rokid surface."
    assert live_hud_payload["live_hud"]["owner_surface"] == "phone", "Live HUD should expose the bridge owner surface."
    assert live_hud_payload["live_hud"]["chunk_progress_label"], "Live HUD should expose teleprompter chunk progress."
    assert live_hud_payload["live_hud"]["teleprompter_text"], "Live HUD should expose the current teleprompter chunk."

    bridge_release_response = client.post(
        f"/api/presentation_missions/{mission_id}/bridge_release",
        json={
            "surface": "phone",
            "bridge_pin": bridge_pin,
        },
    )
    assert bridge_release_response.status_code == 200, bridge_release_response.get_data(as_text=True)
    bridge_release_payload = bridge_release_response.get_json()
    assert bridge_release_payload["bridge_state"]["bridge_status"] == "waiting", "Expected bridge release to return to waiting mode."
    assert not bridge_release_payload["bridge_state"]["claimed_surface"], "Expected the bridge claim to clear after release."

    pairing_end_response = client.post(
        f"/api/presentation_missions/{mission_id}/pairing_end",
        json={
            "surface": "phone",
        },
    )
    assert pairing_end_response.status_code == 200, pairing_end_response.get_data(as_text=True)
    pairing_end_payload = pairing_end_response.get_json()
    assert pairing_end_payload["pairing_state"]["pairing_status"] == "inactive", "Expected pairing end to clear the active pairing session."
    assert not pairing_end_payload["pairing_state"]["paired_surface"], "Expected paired surface to clear after ending pairing."

    print(json.dumps({
        "mission_id": mission_id,
        "rehearsal_id": rehearsal_id,
        "active_slide_index": hud_payload["hud_summary"]["active_slide_index"],
        "control_source": hud_payload["hud_summary"]["control_source"],
        "presentation_mode": hud_payload["hud_summary"]["presentation_mode"],
        "sync_status": live_hud_payload["live_hud"]["sync_status"],
        "pairing_status": pairing_join_payload["pairing_state"]["pairing_status"],
        "bridge_status": bridge_claim_payload["bridge_state"]["bridge_status"],
        "chunk_progress_label": live_hud_payload["live_hud"]["chunk_progress_label"],
        "pace_status": analysis["feedback"]["pace_status"],
        "hud_status": hud_payload["hud_summary"]["current_or_final_status"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
