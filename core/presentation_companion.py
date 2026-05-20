import json
import os
import re
from datetime import datetime

import requests

from utils.presentation_storage import PresentationStore


class PresentationCompanion:
    MODEL_PROVIDERS = {"ollama", "remote", "openai"}
    ALL_PROVIDERS = {"auto", "heuristic", "ollama", "remote", "openai"}
    WORDS_PER_SECOND = 2.35
    STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "because", "but", "by", "for", "from",
        "have", "if", "in", "into", "is", "it", "of", "on", "or", "our", "so", "that",
        "the", "their", "them", "there", "they", "this", "to", "we", "with", "you", "your",
        "can", "will", "just", "about", "then", "than", "also", "very", "really", "like",
    }

    def __init__(self, root_dir="data"):
        self.store = PresentationStore(root_dir=root_dir)

    def list_missions(self):
        return [self._mission_payload(item, summary_only=True) for item in self.store.list_missions()]

    def get_mission_bundle(self, mission_id):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        rehearsals = self.store.list_rehearsals(mission_id=mission_id)
        return {
            "mission": self._mission_payload(mission),
            "rehearsals": [self._rehearsal_payload(item, mission=mission, summary_only=True) for item in rehearsals],
        }

    def save_mission(self, payload):
        payload = payload or {}
        existing = None
        mission_id = self._clean_text(payload.get("mission_id", ""), max_length=80)
        if mission_id:
            existing = self.store.get_mission(mission_id)
        mission_id = mission_id or self._build_id("mission")

        sections_input = payload.get("script_sections")
        if isinstance(sections_input, list) and sections_input:
            script_sections = self._sanitize_sections(sections_input)
        elif existing and isinstance(existing.get("script_sections"), list) and existing.get("script_sections"):
            script_sections = self._sanitize_sections(existing.get("script_sections"))
        else:
            script_sections = self._build_default_sections(
                target_minutes=self._safe_float(payload.get("target_duration_minutes"), default=0),
                deliverable_type=payload.get("deliverable_type", ""),
            )
        presentation_state = self._normalize_presentation_state(
            sections=script_sections,
            incoming=payload.get("presentation_state"),
            existing=(existing or {}).get("presentation_state"),
        )
        companion_sync = self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            incoming=payload.get("companion_sync"),
            existing=(existing or {}).get("companion_sync"),
        )

        now = datetime.now().isoformat(timespec="seconds")
        mission = {
            "mission_id": mission_id,
            "title": self._clean_text(payload.get("title", ""), max_length=180) or self._clean_text((existing or {}).get("title", ""), max_length=180),
            "course": self._clean_text(payload.get("course", ""), max_length=180) or self._clean_text((existing or {}).get("course", ""), max_length=180),
            "deadline": self._clean_text(payload.get("deadline", ""), max_length=180) or self._clean_text((existing or {}).get("deadline", ""), max_length=180),
            "deliverable_type": self._clean_text(payload.get("deliverable_type", ""), max_length=120) or self._clean_text((existing or {}).get("deliverable_type", ""), max_length=120) or "presentation",
            "target_duration_minutes": round(self._safe_float(payload.get("target_duration_minutes"), default=self._safe_float((existing or {}).get("target_duration_minutes"), default=0)), 1),
            "audience": self._clean_text(payload.get("audience", ""), max_length=240) or self._clean_text((existing or {}).get("audience", ""), max_length=240),
            "teacher_requirements": self._clean_text(payload.get("teacher_requirements", ""), max_length=2400, preserve_lines=True) or self._clean_text((existing or {}).get("teacher_requirements", ""), max_length=2400, preserve_lines=True),
            "task_description": self._clean_text(payload.get("task_description", ""), max_length=6000, preserve_lines=True) or self._clean_text((existing or {}).get("task_description", ""), max_length=6000, preserve_lines=True),
            "intake_task_text": self._clean_text(payload.get("intake_task_text", ""), max_length=6000, preserve_lines=True) or self._clean_text((existing or {}).get("intake_task_text", ""), max_length=6000, preserve_lines=True),
            "script_sections": script_sections,
            "presentation_state": presentation_state,
            "companion_sync": companion_sync,
            "created_at": (existing or {}).get("created_at", now),
            "updated_at": now,
        }
        self.store.upsert_mission(mission)
        return self.get_mission_bundle(mission_id)

    def save_script(self, mission_id, sections):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        mission["script_sections"] = self._sanitize_sections(sections or mission.get("script_sections", []))
        mission["presentation_state"] = self._normalize_presentation_state(
            sections=mission.get("script_sections", []),
            existing=mission.get("presentation_state"),
        )
        mission["companion_sync"] = self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=mission.get("presentation_state", {}),
            existing=mission.get("companion_sync"),
        )
        mission["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.store.upsert_mission(mission)
        return self.get_mission_bundle(mission_id)

    def get_presentation_state(self, mission_id):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        sections = self._sanitize_sections(mission.get("script_sections", []))
        state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        mission["presentation_state"] = state
        mission["companion_sync"] = self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=state,
            existing=mission.get("companion_sync"),
        )
        self.store.upsert_mission(mission)
        return {
            "mission_id": mission_id,
            "presentation_state": self._presentation_state_payload(state, sections),
            "companion_sync": self._companion_sync_payload(
                mission_id=mission_id,
                sync_state=mission.get("companion_sync", {}),
                presentation_state=state,
            ),
            "live_hud": self._build_live_hud_payload(mission, latest_rehearsal=self._latest_rehearsal_for_mission(mission_id)),
        }

    def update_presentation_state(self, mission_id, payload):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        sections = self._sanitize_sections(mission.get("script_sections", []))
        mission["presentation_state"] = self._normalize_presentation_state(
            sections=sections,
            incoming=payload,
            existing=mission.get("presentation_state"),
        )
        mission["companion_sync"] = self._touch_companion_sync(
            mission_id=mission_id,
            presentation_state=mission.get("presentation_state", {}),
            existing=mission.get("companion_sync"),
            payload={
                "surface": self._normalize_sync_surface(
                    payload.get("surface") or self._control_source_surface(payload.get("control_source", "phone"))
                ),
                "event": "presentation_state_update",
            },
        )
        mission["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.store.upsert_mission(mission)
        return {
            "mission_id": mission_id,
            "presentation_state": self._presentation_state_payload(mission["presentation_state"], sections),
            "companion_sync": self._companion_sync_payload(
                mission_id=mission_id,
                sync_state=mission.get("companion_sync", {}),
                presentation_state=mission.get("presentation_state", {}),
            ),
            "live_hud": self._build_live_hud_payload(mission, latest_rehearsal=self._latest_rehearsal_for_mission(mission_id)),
        }

    def apply_presentation_control(self, mission_id, payload):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        payload = payload or {}
        sections = self._sanitize_sections(mission.get("script_sections", []))
        state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        section_ids = [item.get("section_id", "") for item in sections if item.get("section_id", "")]
        active_section_id = state.get("active_section_id", section_ids[0] if section_ids else "")
        current_index = section_ids.index(active_section_id) if active_section_id in section_ids else 0
        action = self._clean_text(payload.get("action", ""), max_length=40).lower()
        control_source = self._normalize_control_source(payload.get("control_source", state.get("control_source", "")))

        if action == "next":
            current_index = min(len(section_ids) - 1, current_index + 1) if section_ids else 0
            state["active_section_id"] = section_ids[current_index] if section_ids else ""
        elif action == "previous":
            current_index = max(0, current_index - 1)
            state["active_section_id"] = section_ids[current_index] if section_ids else ""
        elif action == "jump":
            requested_section_id = self._clean_text(payload.get("section_id", ""), max_length=80)
            requested_slide_index = self._safe_int(payload.get("slide_index"), default=0)
            if requested_section_id and requested_section_id in section_ids:
                state["active_section_id"] = requested_section_id
            elif requested_slide_index > 0:
                matched = next((item.get("section_id", "") for item in sections if self._safe_int(item.get("slide_index"), default=0) == requested_slide_index), "")
                if matched:
                    state["active_section_id"] = matched
        elif action == "toggle_cue":
            state["cue_view"] = "hidden" if state.get("cue_view") == "visible" else "visible"
        elif action == "set_mode":
            state["presentation_mode"] = self._normalize_presentation_mode(payload.get("presentation_mode", state.get("presentation_mode", "")))

        state["control_source"] = control_source
        state["last_control_source"] = control_source
        state["last_action"] = action or "sync"
        state["last_control_at"] = datetime.now().isoformat(timespec="seconds")
        mission["presentation_state"] = self._normalize_presentation_state(
            sections=sections,
            existing=state,
        )
        mission["companion_sync"] = self._touch_companion_sync(
            mission_id=mission_id,
            presentation_state=mission.get("presentation_state", {}),
            existing=mission.get("companion_sync"),
            payload={
                "surface": self._control_source_surface(control_source),
                "event": f"control:{action or 'sync'}",
            },
        )
        mission["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.store.upsert_mission(mission)
        return {
            "mission_id": mission_id,
            "presentation_state": self._presentation_state_payload(mission["presentation_state"], sections),
            "companion_sync": self._companion_sync_payload(
                mission_id=mission_id,
                sync_state=mission.get("companion_sync", {}),
                presentation_state=mission.get("presentation_state", {}),
            ),
            "live_hud": self._build_live_hud_payload(mission, latest_rehearsal=self._latest_rehearsal_for_mission(mission_id)),
        }

    def extract_intake(self, payload):
        payload = payload or {}
        task_text = self._clean_text(payload.get("task_text", ""), max_length=6000, preserve_lines=True)
        if not task_text:
            return {
                "status": "error",
                "message": "Paste the assignment text first.",
            }

        use_llm = self._as_bool(payload.get("use_llm", True))
        provider_override = self._clean_text(payload.get("provider_override", "auto"), max_length=24).lower() or "auto"
        model_override = self._clean_model_name(payload.get("model_override", ""))
        requested_provider, configured_provider, effective_provider = self._resolve_provider_request(provider_override)

        heuristic = self._heuristic_intake_candidates(task_text)
        candidates = heuristic["candidates"]
        suggested_sections = self._sanitize_sections(heuristic["suggested_sections"])
        generation = self._generation_meta(
            mode="heuristic",
            requested_provider=requested_provider,
            resolved_provider="heuristic",
            configured_provider=configured_provider,
            provider_available=self._provider_is_configured(effective_provider),
            note="Heuristic intake extraction is active. Provider-backed extraction can refine the field guesses when available.",
            model_override=model_override,
        )

        if use_llm:
            request_bundle = self._build_intake_request_bundle(task_text, candidates, suggested_sections)
            llm_payload, generation = self._maybe_generate_model_layer(
                request_bundle=request_bundle,
                requested_provider=requested_provider,
                configured_provider=configured_provider,
                effective_provider=effective_provider,
                model_override=model_override,
            )
            if llm_payload:
                candidates = self._merge_intake_candidates(candidates, llm_payload)
                llm_sections = self._normalize_llm_sections(llm_payload.get("suggested_sections", []), candidates.get("target_duration_minutes", 0))
                if llm_sections:
                    suggested_sections = llm_sections

        return {
            "status": "ok",
            "task_text": task_text,
            "candidates": candidates,
            "suggested_sections": suggested_sections,
            "notes": heuristic["notes"],
            "generation": generation,
        }

    def create_rehearsal(self, payload, audio_bytes=None, audio_filename="", audio_content_type=""):
        payload = payload or {}
        mission_id = self._clean_text(payload.get("mission_id", ""), max_length=80)
        mission = self.store.get_mission(mission_id)
        if not mission:
            return {
                "status": "error",
                "message": "Select a mission before saving a rehearsal run.",
            }

        rehearsal_id = self._clean_text(payload.get("rehearsal_id", ""), max_length=80) or self._build_id("rehearsal")
        total_duration_seconds = round(self._safe_float(payload.get("total_duration_seconds"), default=0), 1)
        section_timings = self._normalize_section_timings(
            mission_sections=mission.get("script_sections", []),
            section_timings=payload.get("section_timings", []),
            total_duration_seconds=total_duration_seconds,
        )
        if total_duration_seconds <= 0:
            total_duration_seconds = round(sum(item.get("actual_seconds", 0) for item in section_timings), 1)

        existing = self.store.get_rehearsal(rehearsal_id) or {}
        transcript_text = self._clean_text(payload.get("transcript_text", existing.get("transcript_text", "")), max_length=12000, preserve_lines=True)
        transcript_source = self._normalize_transcript_source(payload.get("transcript_source", existing.get("transcript_source", "")), has_text=bool(transcript_text))
        audio_source = self._normalize_audio_source(payload.get("audio_source", existing.get("audio_source", "")))
        audio_meta = existing.get("audio", {}) or {}
        if audio_bytes:
            audio_meta = self.store.save_audio_blob(
                rehearsal_id=rehearsal_id,
                audio_bytes=audio_bytes,
                filename=audio_filename,
                content_type=audio_content_type,
            )

        now = datetime.now().isoformat(timespec="seconds")
        rehearsal = {
            "rehearsal_id": rehearsal_id,
            "mission_id": mission_id,
            "audio_source": audio_source,
            "audio": audio_meta,
            "total_duration_seconds": total_duration_seconds,
            "section_timings": section_timings,
            "transcript_text": transcript_text,
            "transcript_source": transcript_source,
            "self_rating": self._safe_int(payload.get("self_rating"), default=0),
            "notes": self._clean_text(payload.get("notes", existing.get("notes", "")), max_length=2400, preserve_lines=True),
            "created_at": existing.get("created_at", now),
            "updated_at": now,
            "analysis": existing.get("analysis", {}),
        }
        self.store.upsert_rehearsal(rehearsal)
        return {
            "status": "ok",
            "rehearsal": self._rehearsal_payload(rehearsal, mission=mission),
        }

    def get_rehearsal_bundle(self, rehearsal_id):
        rehearsal = self.store.get_rehearsal(rehearsal_id)
        if not rehearsal:
            return None
        mission = self.store.get_mission(rehearsal.get("mission_id"))
        return {
            "status": "ok",
            "rehearsal": self._rehearsal_payload(rehearsal, mission=mission),
        }

    def analyze_rehearsal(self, rehearsal_id, payload):
        rehearsal = self.store.get_rehearsal(rehearsal_id)
        if not rehearsal:
            return {
                "status": "error",
                "message": "Rehearsal run not found.",
            }
        mission = self.store.get_mission(rehearsal.get("mission_id"))
        if not mission:
            return {
                "status": "error",
                "message": "Mission context is missing for this rehearsal.",
            }

        payload = payload or {}
        if "total_duration_seconds" in payload:
            rehearsal["total_duration_seconds"] = round(self._safe_float(payload.get("total_duration_seconds"), default=rehearsal.get("total_duration_seconds", 0)), 1)
        if "section_timings" in payload:
            rehearsal["section_timings"] = self._normalize_section_timings(
                mission_sections=mission.get("script_sections", []),
                section_timings=payload.get("section_timings", []),
                total_duration_seconds=rehearsal.get("total_duration_seconds", 0),
            )
        if "transcript_text" in payload:
            rehearsal["transcript_text"] = self._clean_text(payload.get("transcript_text", ""), max_length=12000, preserve_lines=True)
        if "transcript_source" in payload:
            rehearsal["transcript_source"] = self._normalize_transcript_source(
                payload.get("transcript_source", rehearsal.get("transcript_source", "")),
                has_text=bool(rehearsal.get("transcript_text", "")),
            )
        if "self_rating" in payload:
            rehearsal["self_rating"] = self._safe_int(payload.get("self_rating"), default=rehearsal.get("self_rating", 0))
        if "notes" in payload:
            rehearsal["notes"] = self._clean_text(payload.get("notes", ""), max_length=2400, preserve_lines=True)

        use_llm = self._as_bool(payload.get("use_llm", True))
        provider_override = self._clean_text(payload.get("provider_override", "auto"), max_length=24).lower() or "auto"
        model_override = self._clean_model_name(payload.get("model_override", ""))
        requested_provider, configured_provider, effective_provider = self._resolve_provider_request(provider_override)

        transcript = self._build_transcript_object(rehearsal)
        feedback = self._heuristic_feedback(mission, rehearsal, transcript)
        generation = self._generation_meta(
            mode="heuristic",
            requested_provider=requested_provider,
            resolved_provider="heuristic",
            configured_provider=configured_provider,
            provider_available=self._provider_is_configured(effective_provider),
            note="Rule-based rehearsal feedback is active. Provider-backed feedback can rewrite the analysis without generating a script.",
            model_override=model_override,
        )

        if use_llm:
            request_bundle = self._build_analysis_request_bundle(mission, rehearsal, transcript, feedback)
            llm_payload, generation = self._maybe_generate_model_layer(
                request_bundle=request_bundle,
                requested_provider=requested_provider,
                configured_provider=configured_provider,
                effective_provider=effective_provider,
                model_override=model_override,
            )
            if llm_payload:
                feedback = self._merge_feedback(feedback, llm_payload)

        hud_summary = self._build_hud_summary(
            mission=mission,
            rehearsal=rehearsal,
            transcript=transcript,
            feedback=feedback,
        )

        rehearsal["analysis"] = {
            "transcript": transcript,
            "feedback": feedback,
            "hud_summary": hud_summary,
            "generation": generation,
            "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        }
        rehearsal["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.store.upsert_rehearsal(rehearsal)
        return self.get_rehearsal_bundle(rehearsal_id)

    def get_hud_summary(self, rehearsal_id):
        rehearsal = self.store.get_rehearsal(rehearsal_id)
        if not rehearsal:
            return None
        mission = self.store.get_mission(rehearsal.get("mission_id"))
        analysis = rehearsal.get("analysis", {}) or {}
        hud_summary = analysis.get("hud_summary")
        if hud_summary:
            return hud_summary
        transcript = self._build_transcript_object(rehearsal)
        feedback = self._heuristic_feedback(mission or {}, rehearsal, transcript)
        return self._build_hud_summary(
            mission=mission or {},
            rehearsal=rehearsal,
            transcript=transcript,
            feedback=feedback,
        )

    def get_companion_sync_bundle(self, mission_id):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        sections = self._sanitize_sections(mission.get("script_sections", []))
        presentation_state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        companion_sync = self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            existing=mission.get("companion_sync"),
        )
        mission["presentation_state"] = presentation_state
        mission["companion_sync"] = companion_sync
        self.store.upsert_mission(mission)
        latest_rehearsal = self._latest_rehearsal_for_mission(mission_id)
        return {
            "mission_id": mission_id,
            "presentation_state": self._presentation_state_payload(presentation_state, sections),
            "companion_sync": self._companion_sync_payload(mission_id, companion_sync, presentation_state),
            "live_hud": self._build_live_hud_payload(mission, latest_rehearsal=latest_rehearsal),
        }

    def update_companion_sync(self, mission_id, payload):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        payload = payload or {}
        sections = self._sanitize_sections(mission.get("script_sections", []))
        presentation_state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        mission["presentation_state"] = presentation_state
        mission["companion_sync"] = self._touch_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            existing=mission.get("companion_sync"),
            payload=payload,
        )
        self.store.upsert_mission(mission)
        latest_rehearsal = self._latest_rehearsal_for_mission(mission_id)
        return {
            "mission_id": mission_id,
            "presentation_state": self._presentation_state_payload(presentation_state, sections),
            "companion_sync": self._companion_sync_payload(mission_id, mission.get("companion_sync", {}), presentation_state),
            "live_hud": self._build_live_hud_payload(mission, latest_rehearsal=latest_rehearsal),
        }

    def apply_rokid_event(self, mission_id, payload):
        payload = payload or {}
        button_event = self._normalize_rokid_button_event(payload.get("button_event", ""))
        if not button_event:
            return {
                "status": "error",
                "message": "Provide a Rokid button event such as single_press, double_press, or long_press.",
            }
        mapping = self._control_hints_payload().get("rokid_button", {}).get("button_map", {})
        mapped_action = self._clean_text(mapping.get(button_event, ""), max_length=40).lower()
        if not mapped_action:
            return {
                "status": "error",
                "message": f"No presentation action is mapped to {button_event}.",
            }
        control_result = self.apply_presentation_control(
            mission_id,
            {
                "action": mapped_action,
                "control_source": "rokid_button",
                "presentation_mode": payload.get("presentation_mode", ""),
            },
        )
        if not control_result:
            return None
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        sections = self._sanitize_sections(mission.get("script_sections", []))
        presentation_state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        mission["presentation_state"] = presentation_state
        mission["companion_sync"] = self._touch_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            existing=mission.get("companion_sync"),
            payload={
                "surface": "rokid_hud",
                "event": f"rokid:{button_event}",
                "button_event": button_event,
            },
        )
        self.store.upsert_mission(mission)
        latest_rehearsal = self._latest_rehearsal_for_mission(mission_id)
        return {
            "mission_id": mission_id,
            "rokid_event": {
                "button_event": button_event,
                "mapped_action": mapped_action,
            },
            "presentation_state": self._presentation_state_payload(presentation_state, sections),
            "companion_sync": self._companion_sync_payload(mission_id, mission.get("companion_sync", {}), presentation_state),
            "live_hud": self._build_live_hud_payload(mission, latest_rehearsal=latest_rehearsal),
        }

    def get_live_hud(self, mission_id, surface="rokid_hud"):
        mission = self.store.get_mission(mission_id)
        if not mission:
            return None
        sections = self._sanitize_sections(mission.get("script_sections", []))
        presentation_state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        mission["presentation_state"] = presentation_state
        mission["companion_sync"] = self._touch_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            existing=mission.get("companion_sync"),
            payload={
                "surface": self._normalize_sync_surface(surface or "rokid_hud"),
                "event": "live_hud_pull",
            },
        )
        self.store.upsert_mission(mission)
        latest_rehearsal = self._latest_rehearsal_for_mission(mission_id)
        return {
            "mission_id": mission_id,
            "live_hud": self._build_live_hud_payload(mission, latest_rehearsal=latest_rehearsal),
            "companion_sync": self._companion_sync_payload(mission_id, mission.get("companion_sync", {}), presentation_state),
        }

    def _mission_payload(self, mission, summary_only=False):
        mission = mission or {}
        sections = self._sanitize_sections(mission.get("script_sections", []))
        presentation_state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        companion_sync = self._normalize_companion_sync(
            mission_id=mission.get("mission_id", ""),
            presentation_state=presentation_state,
            existing=mission.get("companion_sync"),
        )
        summary = self._build_script_summary(
            sections=sections,
            target_minutes=self._safe_float(mission.get("target_duration_minutes"), default=0),
        )
        payload = {
            "mission_id": mission.get("mission_id", ""),
            "title": mission.get("title", "") or "Untitled mission",
            "course": mission.get("course", ""),
            "deadline": mission.get("deadline", ""),
            "deliverable_type": mission.get("deliverable_type", "") or "presentation",
            "target_duration_minutes": round(self._safe_float(mission.get("target_duration_minutes"), default=0), 1),
            "target_duration_seconds": summary["target_total_seconds"],
            "audience": mission.get("audience", ""),
            "teacher_requirements": mission.get("teacher_requirements", ""),
            "task_description": mission.get("task_description", ""),
            "intake_task_text": mission.get("intake_task_text", ""),
            "created_at": mission.get("created_at", ""),
            "updated_at": mission.get("updated_at", ""),
            "script_summary": summary,
            "presentation_state": self._presentation_state_payload(presentation_state, sections),
            "companion_sync": self._companion_sync_payload(
                mission_id=mission.get("mission_id", ""),
                sync_state=companion_sync,
                presentation_state=presentation_state,
            ),
        }
        if summary_only:
            return payload
        payload["script_sections"] = sections
        return payload

    def _rehearsal_payload(self, rehearsal, mission=None, summary_only=False):
        rehearsal = rehearsal or {}
        mission = mission or self.store.get_mission(rehearsal.get("mission_id"))
        transcript = rehearsal.get("analysis", {}).get("transcript") or self._build_transcript_object(rehearsal)
        payload = {
            "rehearsal_id": rehearsal.get("rehearsal_id", ""),
            "mission_id": rehearsal.get("mission_id", ""),
            "audio_source": rehearsal.get("audio_source", ""),
            "audio": rehearsal.get("audio", {}) or {},
            "total_duration_seconds": round(self._safe_float(rehearsal.get("total_duration_seconds"), default=0), 1),
            "total_duration_label": self._format_mmss(rehearsal.get("total_duration_seconds", 0)),
            "section_timings": rehearsal.get("section_timings", []) or [],
            "transcript_text": rehearsal.get("transcript_text", ""),
            "transcript_source": rehearsal.get("transcript_source", ""),
            "transcript_status": transcript.get("status", "missing"),
            "self_rating": self._safe_int(rehearsal.get("self_rating"), default=0),
            "notes": rehearsal.get("notes", ""),
            "created_at": rehearsal.get("created_at", ""),
            "updated_at": rehearsal.get("updated_at", ""),
            "analysis": rehearsal.get("analysis", {}) or {},
            "mission_title": (mission or {}).get("title", ""),
            "mission_presentation_state": self._presentation_state_payload(
                self._normalize_presentation_state(
                    sections=(mission or {}).get("script_sections", []),
                    existing=(mission or {}).get("presentation_state"),
                ),
                self._sanitize_sections((mission or {}).get("script_sections", [])),
            ) if mission else {},
        }
        if summary_only:
            payload.pop("analysis", None)
            payload.pop("section_timings", None)
            payload.pop("notes", None)
            payload.pop("transcript_text", None)
            return payload
        return payload

    def _build_default_sections(self, target_minutes=0, deliverable_type=""):
        target_seconds = max(120, int(round(self._safe_float(target_minutes, default=5) * 60))) if self._safe_float(target_minutes, default=0) > 0 else 300
        deliverable = self._clean_text(deliverable_type, max_length=120).lower()
        if "poster" in deliverable or "pitch" in deliverable:
            skeleton = [
                ("Opening Hook", "Slide 1", "Open with the core problem and why it matters.", 0.18),
                ("Core Claim", "Slide 2", "State the main idea in one plain sentence.", 0.28),
                ("Evidence", "Slide 3", "Point the audience to the strongest proof or example.", 0.30),
                ("Takeaway", "Slide 4", "Close with the result and invite one short question.", 0.24),
            ]
        elif target_seconds <= 240:
            skeleton = [
                ("Opening", "Slide 1", "Frame the task and preview the structure.", 0.20),
                ("Main Point", "Slide 2", "Explain the key idea without reading full sentences.", 0.32),
                ("Example", "Slide 3", "Slow down and make one example easy to follow.", 0.28),
                ("Conclusion", "Slide 4", "Land the takeaway and pause for audience reaction.", 0.20),
            ]
        elif target_seconds <= 420:
            skeleton = [
                ("Opening", "Slide 1", "Set the topic, goal, and route for the audience.", 0.16),
                ("Background", "Slide 2", "Explain what the audience needs before the main point.", 0.18),
                ("Core Idea", "Slide 3", "State the main argument or method clearly.", 0.24),
                ("Evidence or Example", "Slide 4", "Use one clear example and signpost the transition.", 0.24),
                ("Conclusion", "Slide 5", "Summarize the takeaway and invite one question.", 0.18),
            ]
        else:
            skeleton = [
                ("Opening", "Slide 1", "Give the audience the roadmap and timing expectation.", 0.14),
                ("Context", "Slide 2", "Define the problem or assignment frame.", 0.16),
                ("Point One", "Slide 3", "Teach the first key point with a clean transition.", 0.20),
                ("Point Two", "Slide 4", "Extend the argument with one comparison or detail.", 0.20),
                ("Example", "Slide 5", "Use one concrete example and face the audience at the end.", 0.16),
                ("Conclusion", "Slide 6", "Finish with the takeaway, significance, and question cue.", 0.14),
            ]

        sections = []
        remaining = target_seconds
        for index, (name, slide_anchor, interaction_goal, weight) in enumerate(skeleton, start=1):
            if index == len(skeleton):
                target = max(15, remaining)
            else:
                target = max(15, int(round(target_seconds * weight)))
                remaining -= target
            sections.append({
                "section_id": self._build_id(f"section-{index}"),
                "name": name,
                "slide_index": index,
                "slide_title": name,
                "slide_anchor": slide_anchor,
                "interaction_goal": interaction_goal,
                "target_seconds": target,
                "outline": "",
                "speaker_notes": "",
                "cue_cards": "",
            })
        return sections

    def _sanitize_sections(self, sections):
        normalized = []
        seen_ids = set()
        for index, section in enumerate(sections or [], start=1):
            if not isinstance(section, dict):
                continue
            section_id = self._clean_text(section.get("section_id", ""), max_length=80) or self._build_id(f"section-{index}")
            while section_id in seen_ids:
                section_id = self._build_id(f"section-{index}")
            seen_ids.add(section_id)
            slide_index = max(1, self._safe_int(section.get("slide_index"), default=index))
            slide_title = self._clean_text(section.get("slide_title", ""), max_length=120) or self._clean_text(section.get("name", ""), max_length=120) or f"Slide {slide_index}"
            normalized.append({
                "section_id": section_id,
                "name": self._clean_text(section.get("name", ""), max_length=120) or f"Section {index}",
                "slide_index": slide_index,
                "slide_title": slide_title,
                "slide_anchor": self._clean_text(section.get("slide_anchor", ""), max_length=120),
                "interaction_goal": self._clean_text(section.get("interaction_goal", ""), max_length=240),
                "target_seconds": max(10, self._safe_int(section.get("target_seconds"), default=45)),
                "outline": self._clean_text(section.get("outline", ""), max_length=2400, preserve_lines=True),
                "speaker_notes": self._clean_text(section.get("speaker_notes", ""), max_length=3600, preserve_lines=True),
                "cue_cards": self._clean_text(section.get("cue_cards", ""), max_length=1800, preserve_lines=True),
            })
        if not normalized:
            return self._build_default_sections()
        normalized.sort(key=lambda item: (self._safe_int(item.get("slide_index"), default=0), item.get("section_id", "")))
        return normalized

    def _build_script_summary(self, sections, target_minutes=0):
        target_total_seconds = sum(max(0, self._safe_int(item.get("target_seconds"), default=0)) for item in sections)
        if target_total_seconds <= 0 and self._safe_float(target_minutes, default=0) > 0:
            target_total_seconds = int(round(self._safe_float(target_minutes, default=0) * 60))

        estimated_total_seconds = 0
        completed_sections = 0
        interaction_sections = 0
        section_metrics = []
        for section in sections:
            estimated_seconds = self._estimate_section_seconds(section)
            estimated_total_seconds += estimated_seconds
            has_core_content = any(section.get(field, "").strip() for field in ("outline", "speaker_notes", "cue_cards"))
            if has_core_content:
                completed_sections += 1
            if section.get("interaction_goal", "").strip():
                interaction_sections += 1
            hint = self._section_duration_hint(estimated_seconds, section.get("target_seconds", 0))
            section_metrics.append({
                "section_id": section.get("section_id", ""),
                "slide_index": self._safe_int(section.get("slide_index"), default=0),
                "slide_title": section.get("slide_title", ""),
                "estimated_seconds": estimated_seconds,
                "estimated_label": self._format_mmss(estimated_seconds),
                "target_label": self._format_mmss(section.get("target_seconds", 0)),
                "duration_hint": hint["status"],
                "duration_note": hint["note"],
                "estimated_words": self._estimated_script_words(section),
                "content_status": "ready" if has_core_content else "empty",
            })

        overall_hint = self._section_duration_hint(estimated_total_seconds, target_total_seconds)
        return {
            "section_count": len(sections),
            "slide_card_count": len(sections),
            "completed_sections": completed_sections,
            "interaction_sections": interaction_sections,
            "target_total_seconds": target_total_seconds,
            "target_total_label": self._format_mmss(target_total_seconds),
            "estimated_total_seconds": estimated_total_seconds,
            "estimated_total_label": self._format_mmss(estimated_total_seconds),
            "duration_hint": overall_hint["status"],
            "duration_note": overall_hint["note"],
            "section_metrics": section_metrics,
        }

    def _estimated_script_words(self, section):
        outline_words = self._word_count(section.get("outline", ""))
        notes_words = self._word_count(section.get("speaker_notes", ""))
        cue_words = self._word_count(section.get("cue_cards", ""))
        return int(round(outline_words * 0.45 + notes_words + cue_words * 0.7))

    def _estimate_section_seconds(self, section):
        weighted_words = self._estimated_script_words(section)
        if weighted_words <= 0:
            return 0
        return max(10, int(round(weighted_words / self.WORDS_PER_SECOND)))

    def _section_duration_hint(self, estimated_seconds, target_seconds):
        target_seconds = max(0, self._safe_int(target_seconds, default=0))
        estimated_seconds = max(0, self._safe_int(estimated_seconds, default=0))
        if target_seconds <= 0:
            return {
                "status": "unknown",
                "note": "Set a target time for a clearer section pacing check.",
            }
        if estimated_seconds <= 0:
            return {
                "status": "empty",
                "note": "This section still needs your own outline or notes.",
            }
        ratio = estimated_seconds / max(target_seconds, 1)
        if ratio >= 1.2:
            return {
                "status": "long",
                "note": f"Estimated at {self._format_mmss(estimated_seconds)}, which looks longer than the target window.",
            }
        if ratio <= 0.7:
            return {
                "status": "short",
                "note": f"Estimated at {self._format_mmss(estimated_seconds)}, which may be too short for the target window.",
            }
        return {
            "status": "balanced",
            "note": f"Estimated at {self._format_mmss(estimated_seconds)} and roughly aligned with the target window.",
        }

    def _heuristic_intake_candidates(self, task_text):
        lines = [line.strip(" -*\t") for line in task_text.splitlines() if line.strip()]
        lowered = task_text.lower()
        deliverable_type = self._detect_deliverable_type(lowered)
        duration_minutes = self._extract_duration_minutes(task_text)
        title = self._extract_title(task_text, lines) or "Academic Presentation"
        course = self._extract_labeled_value(task_text, ("course", "class", "module", "subject"))
        deadline = self._extract_deadline(task_text)
        audience = self._detect_audience(lowered)
        teacher_requirements = self._extract_teacher_requirements(task_text)
        suggested_sections = self._build_default_sections(duration_minutes or 5, deliverable_type)
        notes = [
            "The fallback extractor looked for explicit duration, deliverable, audience, and requirement cues.",
            "All extracted fields stay editable before you save the mission.",
        ]
        return {
            "candidates": {
                "title": title,
                "course": course,
                "deadline": deadline,
                "deliverable_type": deliverable_type or "presentation",
                "target_duration_minutes": duration_minutes or 0,
                "audience": audience,
                "teacher_requirements": teacher_requirements,
                "task_description": task_text,
            },
            "suggested_sections": suggested_sections,
            "notes": notes,
        }

    def _detect_deliverable_type(self, lowered_text):
        mapping = [
            ("poster presentation", "poster presentation"),
            ("oral presentation", "oral presentation"),
            ("group presentation", "group presentation"),
            ("seminar", "seminar presentation"),
            ("pitch", "pitch presentation"),
            ("defense", "presentation defense"),
            ("slides", "slide presentation"),
            ("presentation", "presentation"),
            ("present", "presentation"),
        ]
        for needle, label in mapping:
            if needle in lowered_text:
                return label
        return ""

    def _extract_duration_minutes(self, text):
        patterns = [
            re.compile(r"(\d+)\s*(?:-|to)\s*(\d+)\s*(minutes|minute|min|mins)\b", re.I),
            re.compile(r"(\d+(?:\.\d+)?)\s*(minutes|minute|min|mins)\b", re.I),
        ]
        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue
            try:
                if len(match.groups()) >= 3 and match.group(2) and match.group(2).isdigit():
                    return round((float(match.group(1)) + float(match.group(2))) / 2.0, 1)
            except Exception:
                pass
            try:
                return round(float(match.group(1)), 1)
            except Exception:
                continue
        return 0

    def _extract_title(self, text, lines):
        labeled = self._extract_labeled_value(text, ("title", "topic", "presentation title"))
        if labeled:
            return labeled
        quoted = re.search(r"\"([^\"]{4,120})\"", text)
        if quoted:
            return self._clean_text(quoted.group(1), max_length=120)
        first_line = lines[0] if lines else ""
        if 4 <= len(first_line) <= 90 and ":" not in first_line:
            return self._clean_text(first_line, max_length=120)
        return ""

    def _extract_labeled_value(self, text, labels):
        for label in labels:
            match = re.search(rf"{re.escape(label)}\s*[:\-]\s*(.+)", text, re.I)
            if match:
                value = match.group(1).strip()
                value = value.splitlines()[0].strip()
                return self._clean_text(value, max_length=180)
        return ""

    def _extract_deadline(self, text):
        patterns = [
            re.compile(r"(?:deadline|due(?: date)?|presentation date|present on)\s*[:\-]?\s*([^\n\.]{4,80})", re.I),
            re.compile(r"\b(on\s+[A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)", re.I),
            re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
        ]
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return self._clean_text(match.group(1), max_length=80)
        return ""

    def _detect_audience(self, lowered_text):
        if "classmates" in lowered_text or "class" in lowered_text:
            return "Classmates and teacher"
        if "teacher" in lowered_text and "class" not in lowered_text:
            return "Teacher"
        if "panel" in lowered_text or "jury" in lowered_text:
            return "Panel"
        if "audience" in lowered_text:
            return "General audience"
        return ""

    def _extract_teacher_requirements(self, text):
        requirement_lines = []
        for raw_line in text.splitlines():
            line = raw_line.strip(" -*\t")
            lowered = line.lower()
            if not line:
                continue
            if any(token in lowered for token in ("must", "should", "need to", "required", "include", "at least", "cite", "reference", "submit")):
                requirement_lines.append(line)
        if not requirement_lines:
            sentences = re.split(r"(?<=[\.\?!])\s+", text.strip())
            for sentence in sentences:
                lowered = sentence.lower()
                if any(token in lowered for token in ("must", "need to", "required", "include", "at least", "cite", "reference")):
                    requirement_lines.append(sentence.strip())
        if not requirement_lines:
            return ""
        cleaned = [self._clean_text(line, max_length=280) for line in requirement_lines[:5] if self._clean_text(line, max_length=280)]
        if not cleaned:
            return ""
        return "\n".join(f"- {item}" for item in cleaned)

    def _merge_intake_candidates(self, heuristic_candidates, llm_payload):
        merged = dict(heuristic_candidates or {})
        for key, limit in (
            ("title", 180),
            ("course", 180),
            ("deadline", 180),
            ("deliverable_type", 120),
            ("audience", 240),
            ("teacher_requirements", 2400),
        ):
            value = self._clean_text(llm_payload.get(key, ""), max_length=limit, preserve_lines=(key == "teacher_requirements"))
            if value:
                merged[key] = value
        duration = self._safe_float(llm_payload.get("target_duration_minutes"), default=0)
        if duration > 0:
            merged["target_duration_minutes"] = round(duration, 1)
        merged["task_description"] = heuristic_candidates.get("task_description", "")
        return merged

    def _normalize_llm_sections(self, items, target_minutes):
        if not isinstance(items, list) or not items:
            return []
        target_seconds = max(120, int(round(self._safe_float(target_minutes, default=5) * 60))) if self._safe_float(target_minutes, default=0) > 0 else 300
        normalized = []
        for index, item in enumerate(items[:6], start=1):
            if not isinstance(item, dict):
                continue
            normalized.append({
                "section_id": self._build_id(f"section-llm-{index}"),
                "name": self._clean_text(item.get("name", ""), max_length=120) or f"Section {index}",
                "slide_index": max(1, self._safe_int(item.get("slide_index"), default=index)),
                "slide_title": self._clean_text(item.get("slide_title", ""), max_length=120) or self._clean_text(item.get("name", ""), max_length=120) or f"Slide {index}",
                "slide_anchor": self._clean_text(item.get("slide_anchor", ""), max_length=120),
                "interaction_goal": self._clean_text(item.get("interaction_goal", ""), max_length=240),
                "target_seconds": max(10, self._safe_int(item.get("target_seconds"), default=max(15, int(round(target_seconds / max(len(items), 1)))))),
                "outline": "",
                "speaker_notes": "",
                "cue_cards": "",
            })
        return self._sanitize_sections(normalized) if normalized else []

    def _normalize_section_timings(self, mission_sections, section_timings, total_duration_seconds):
        mission_sections = self._sanitize_sections(mission_sections)
        provided_map = {}
        if isinstance(section_timings, list):
            for item in section_timings:
                if not isinstance(item, dict):
                    continue
                key = self._clean_text(item.get("section_id", ""), max_length=80) or self._clean_text(item.get("name", ""), max_length=120)
                if key:
                    provided_map[key] = item

        resolved = []
        total_target = sum(max(0, self._safe_int(section.get("target_seconds"), default=0)) for section in mission_sections)
        actual_sum = 0
        for section in mission_sections:
            key_candidates = [section.get("section_id", ""), section.get("name", "")]
            candidate = None
            for key in key_candidates:
                if key and key in provided_map:
                    candidate = provided_map[key]
                    break
            target_seconds = max(10, self._safe_int(section.get("target_seconds"), default=45))
            actual_seconds = self._safe_float((candidate or {}).get("actual_seconds"), default=0)
            if actual_seconds <= 0 and self._safe_float(total_duration_seconds, default=0) > 0 and total_target > 0:
                actual_seconds = round(self._safe_float(total_duration_seconds, default=0) * (target_seconds / total_target), 1)
            if actual_seconds <= 0:
                actual_seconds = float(target_seconds)
            actual_sum += actual_seconds
            resolved.append({
                "section_id": section.get("section_id", ""),
                "name": section.get("name", ""),
                "slide_index": self._safe_int(section.get("slide_index"), default=0),
                "slide_title": section.get("slide_title", ""),
                "target_seconds": target_seconds,
                "actual_seconds": round(actual_seconds, 1),
            })

        if self._safe_float(total_duration_seconds, default=0) > 0 and actual_sum > 0:
            ratio = self._safe_float(total_duration_seconds, default=0) / actual_sum
            if 0.65 <= ratio <= 1.35:
                for item in resolved:
                    item["actual_seconds"] = round(item["actual_seconds"] * ratio, 1)

        for item in resolved:
            delta = round(self._safe_float(item.get("actual_seconds"), default=0) - self._safe_float(item.get("target_seconds"), default=0), 1)
            item["delta_seconds"] = delta
            item["delta_label"] = self._format_signed_mmss(delta)
            item["pace_status"] = self._section_pace_status(item.get("actual_seconds"), item.get("target_seconds"))
        return resolved

    def _normalize_presentation_state(self, sections, incoming=None, existing=None):
        sections = self._sanitize_sections(sections)
        incoming = incoming or {}
        existing = existing or {}
        section_ids = [item.get("section_id", "") for item in sections if item.get("section_id", "")]
        default_section_id = section_ids[0] if section_ids else ""
        active_section_id = self._clean_text(
            incoming.get("active_section_id", existing.get("active_section_id", default_section_id)),
            max_length=80,
        )
        if active_section_id not in section_ids:
            requested_slide_index = self._safe_int(incoming.get("active_slide_index", existing.get("active_slide_index", 0)), default=0)
            matched = next((item.get("section_id", "") for item in sections if self._safe_int(item.get("slide_index"), default=0) == requested_slide_index), "")
            active_section_id = matched or default_section_id
        active_section = next((item for item in sections if item.get("section_id", "") == active_section_id), sections[0] if sections else {})
        return {
            "presentation_mode": self._normalize_presentation_mode(incoming.get("presentation_mode", existing.get("presentation_mode", "rehearse"))),
            "control_source": self._normalize_control_source(incoming.get("control_source", existing.get("control_source", "phone"))),
            "last_control_source": self._normalize_control_source(incoming.get("last_control_source", existing.get("last_control_source", "phone"))),
            "active_section_id": active_section_id,
            "active_slide_index": self._safe_int(active_section.get("slide_index"), default=0),
            "cue_view": self._normalize_cue_view(incoming.get("cue_view", existing.get("cue_view", "visible"))),
            "last_action": self._clean_text(incoming.get("last_action", existing.get("last_action", "sync")), max_length=40).lower() or "sync",
            "last_control_at": self._clean_text(incoming.get("last_control_at", existing.get("last_control_at", "")), max_length=40),
        }

    def _normalize_companion_sync(self, mission_id, presentation_state, incoming=None, existing=None):
        incoming = incoming or {}
        existing = existing or {}
        mission_id = self._clean_text(mission_id, max_length=80)
        sync_status = self._normalize_sync_status(
            incoming.get("sync_status", existing.get("sync_status", "")),
            presentation_mode=(presentation_state or {}).get("presentation_mode", "rehearse"),
        )
        active_surface = self._normalize_sync_surface(incoming.get("active_surface", existing.get("active_surface", "web")))
        return {
            "session_id": self._clean_text(
                incoming.get("session_id", existing.get("session_id", "")),
                max_length=80,
            ) or self._build_id(f"{mission_id or 'presentation'}-sync"),
            "sync_status": sync_status,
            "active_surface": active_surface,
            "controller_surface": self._normalize_sync_surface(incoming.get("controller_surface", existing.get("controller_surface", "phone"))),
            "hud_surface": self._normalize_sync_surface(incoming.get("hud_surface", existing.get("hud_surface", "rokid_hud"))),
            "sync_revision": max(1, self._safe_int(incoming.get("sync_revision", existing.get("sync_revision", 1)), default=1)),
            "last_event": self._clean_text(incoming.get("last_event", existing.get("last_event", "initialized")), max_length=80) or "initialized",
            "last_button_event": self._normalize_rokid_button_event(incoming.get("last_button_event", existing.get("last_button_event", ""))),
            "last_sync_at": self._clean_text(incoming.get("last_sync_at", existing.get("last_sync_at", "")), max_length=40),
            "last_phone_seen_at": self._clean_text(incoming.get("last_phone_seen_at", existing.get("last_phone_seen_at", "")), max_length=40),
            "last_web_seen_at": self._clean_text(incoming.get("last_web_seen_at", existing.get("last_web_seen_at", "")), max_length=40),
            "last_hud_seen_at": self._clean_text(incoming.get("last_hud_seen_at", existing.get("last_hud_seen_at", "")), max_length=40),
            "last_rokid_event_at": self._clean_text(incoming.get("last_rokid_event_at", existing.get("last_rokid_event_at", "")), max_length=40),
        }

    def _touch_companion_sync(self, mission_id, presentation_state, existing=None, payload=None):
        payload = payload or {}
        current = self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            existing=existing,
        )
        surface = self._normalize_sync_surface(payload.get("surface", current.get("active_surface", "web")))
        event = self._clean_text(payload.get("event", "heartbeat"), max_length=80) or "heartbeat"
        button_event = self._normalize_rokid_button_event(payload.get("button_event", current.get("last_button_event", "")))
        now = datetime.now().isoformat(timespec="seconds")
        presentation_mode = (presentation_state or {}).get("presentation_mode", "rehearse")
        requested_sync_status = self._clean_text(payload.get("sync_status", ""), max_length=20).lower()
        if requested_sync_status:
            sync_status = self._normalize_sync_status(
                requested_sync_status,
                presentation_mode=presentation_mode,
            )
        elif self._normalize_presentation_mode(presentation_mode) == "present":
            sync_status = "live"
        else:
            sync_status = self._normalize_sync_status(
                current.get("sync_status", ""),
                presentation_mode=presentation_mode,
            )
        touched = {
            **current,
            "active_surface": surface,
            "sync_status": sync_status,
            "sync_revision": max(1, self._safe_int(current.get("sync_revision"), default=1)) + 1,
            "last_event": event,
            "last_button_event": button_event,
            "last_sync_at": now,
        }
        if surface == "phone":
            touched["controller_surface"] = "phone"
            touched["last_phone_seen_at"] = now
        elif surface == "web":
            touched["last_web_seen_at"] = now
        elif surface == "rokid_hud":
            touched["hud_surface"] = "rokid_hud"
            touched["last_hud_seen_at"] = now
        if button_event:
            touched["last_rokid_event_at"] = now
            touched["hud_surface"] = "rokid_hud"
        return self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            incoming=touched,
            existing=current,
        )

    def _presentation_state_payload(self, state, sections):
        sections = self._sanitize_sections(sections)
        state = self._normalize_presentation_state(sections, existing=state)
        active_card = self._find_active_card(sections, state)
        return {
            **state,
            "active_card": active_card,
            "next_card": self._next_card_brief(sections, state),
            "available_cards": [self._card_brief_payload(item) for item in sections],
            "control_hints": self._control_hints_payload(),
        }

    def _find_active_card(self, sections, state):
        sections = self._sanitize_sections(sections)
        target_id = self._clean_text((state or {}).get("active_section_id", ""), max_length=80)
        for item in sections:
            if item.get("section_id", "") == target_id:
                return self._card_payload(item, presentation_mode=(state or {}).get("presentation_mode", "rehearse"), cue_view=(state or {}).get("cue_view", "visible"))
        return self._card_payload(sections[0], presentation_mode=(state or {}).get("presentation_mode", "rehearse"), cue_view=(state or {}).get("cue_view", "visible")) if sections else {}

    def _next_card_brief(self, sections, state):
        sections = self._sanitize_sections(sections)
        target_id = self._clean_text((state or {}).get("active_section_id", ""), max_length=80)
        for index, item in enumerate(sections):
            if item.get("section_id", "") == target_id:
                if index + 1 < len(sections):
                    return self._card_brief_payload(sections[index + 1])
                return {}
        return self._card_brief_payload(sections[1]) if len(sections) > 1 else {}

    def _card_brief_payload(self, section):
        return {
            "section_id": section.get("section_id", ""),
            "name": section.get("name", ""),
            "slide_index": self._safe_int(section.get("slide_index"), default=0),
            "slide_title": section.get("slide_title", ""),
            "slide_anchor": section.get("slide_anchor", ""),
            "interaction_goal": section.get("interaction_goal", ""),
            "target_seconds": self._safe_int(section.get("target_seconds"), default=0),
            "target_label": self._format_mmss(section.get("target_seconds", 0)),
        }

    def _card_payload(self, section, presentation_mode="rehearse", cue_view="visible"):
        if not section:
            return {}
        payload = {
            "section_id": section.get("section_id", ""),
            "name": section.get("name", ""),
            "slide_index": self._safe_int(section.get("slide_index"), default=0),
            "slide_title": section.get("slide_title", ""),
            "slide_anchor": section.get("slide_anchor", ""),
            "interaction_goal": section.get("interaction_goal", ""),
            "target_seconds": self._safe_int(section.get("target_seconds"), default=0),
            "target_label": self._format_mmss(section.get("target_seconds", 0)),
            "outline": section.get("outline", ""),
            "speaker_notes": section.get("speaker_notes", ""),
            "cue_cards": section.get("cue_cards", ""),
            "presentation_mode": self._normalize_presentation_mode(presentation_mode),
            "cue_view": self._normalize_cue_view(cue_view),
        }
        if payload["presentation_mode"] == "present":
            payload["speaker_notes"] = ""
            if payload["cue_view"] == "hidden":
                payload["cue_cards"] = ""
        elif payload["cue_view"] == "hidden":
            payload["cue_cards"] = ""
        return payload

    def _normalize_presentation_mode(self, value):
        normalized = str(value or "").strip().lower()
        if normalized not in {"edit", "rehearse", "present"}:
            return "rehearse"
        return normalized

    def _normalize_control_source(self, value):
        normalized = str(value or "").strip().lower()
        if normalized not in {"phone", "rokid_button"}:
            return "phone"
        return normalized

    def _control_source_surface(self, value):
        normalized = self._normalize_control_source(value)
        if normalized == "rokid_button":
            return "rokid_hud"
        return "phone"

    def _normalize_sync_surface(self, value):
        normalized = str(value or "").strip().lower()
        if normalized not in {"web", "phone", "rokid_hud"}:
            return "web"
        return normalized

    def _normalize_sync_status(self, value, presentation_mode="rehearse"):
        normalized = str(value or "").strip().lower()
        if normalized in {"idle", "ready", "live"}:
            return normalized
        return "live" if self._normalize_presentation_mode(presentation_mode) == "present" else "ready"

    def _normalize_rokid_button_event(self, value):
        normalized = str(value or "").strip().lower()
        if normalized not in {"single_press", "double_press", "long_press"}:
            return ""
        return normalized

    def _normalize_cue_view(self, value):
        normalized = str(value or "").strip().lower()
        if normalized not in {"visible", "hidden"}:
            return "visible"
        return normalized

    def _companion_sync_payload(self, mission_id, sync_state, presentation_state):
        sync_state = self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            existing=sync_state,
        )
        return {
            **sync_state,
            "controller_path": f"/presentation/controller?mission_id={mission_id}",
            "workspace_path": f"/presentation?mission_id={mission_id}",
            "sync_api_path": f"/api/presentation_missions/{mission_id}/companion_sync",
            "rokid_event_api_path": f"/api/presentation_missions/{mission_id}/rokid_event",
            "live_hud_api_path": f"/api/presentation_missions/{mission_id}/live_hud",
            "surface_status": {
                "web": self._surface_status_payload(sync_state.get("last_web_seen_at", "")),
                "phone": self._surface_status_payload(sync_state.get("last_phone_seen_at", "")),
                "rokid_hud": self._surface_status_payload(sync_state.get("last_hud_seen_at", "")),
            },
            "presentation_mode": self._normalize_presentation_mode((presentation_state or {}).get("presentation_mode", "rehearse")),
            "active_slide_index": self._safe_int((presentation_state or {}).get("active_slide_index"), default=0),
            "cue_view": self._normalize_cue_view((presentation_state or {}).get("cue_view", "visible")),
        }

    def _surface_status_payload(self, iso_value):
        last_seen_at = self._clean_text(iso_value, max_length=40)
        status = self._connection_status(last_seen_at)
        return {
            "last_seen_at": last_seen_at,
            "status": status,
        }

    def _connection_status(self, iso_value):
        age_seconds = self._seconds_since_iso(iso_value)
        if age_seconds is None:
            return "offline"
        if age_seconds <= 20:
            return "active"
        if age_seconds <= 180:
            return "idle"
        return "offline"

    def _seconds_since_iso(self, iso_value):
        cleaned = self._clean_text(iso_value, max_length=40)
        if not cleaned:
            return None
        try:
            parsed = datetime.fromisoformat(cleaned)
        except Exception:
            return None
        try:
            return max(0, int((datetime.now() - parsed).total_seconds()))
        except Exception:
            return None

    def _latest_rehearsal_for_mission(self, mission_id):
        if not mission_id:
            return None
        rehearsals = self.store.list_rehearsals(mission_id=mission_id)
        return rehearsals[0] if rehearsals else None

    def _control_hints_payload(self):
        return {
            "phone": {
                "role": "Main controller",
                "note": "Use the phone for full slide switching, jump, and mode changes.",
                "actions": ["previous", "next", "jump", "toggle_cue", "set_mode"],
            },
            "rokid_button": {
                "role": "Quick remote",
                "note": "Keep glasses-side control lightweight so the presenter does not need complex input during delivery.",
                "button_map": {
                    "single_press": "next",
                    "double_press": "previous",
                    "long_press": "toggle_cue",
                },
            },
        }

    def _build_transcript_object(self, rehearsal):
        rehearsal = rehearsal or {}
        transcript_text = self._clean_text(rehearsal.get("transcript_text", ""), max_length=12000, preserve_lines=True)
        total_seconds = self._safe_float(rehearsal.get("total_duration_seconds"), default=0)
        word_count = self._word_count(transcript_text)
        words_per_minute = round(word_count / max(total_seconds / 60.0, 1 / 60.0), 1) if transcript_text and total_seconds >= 10 else None
        audio = rehearsal.get("audio", {}) or {}
        if transcript_text:
            status = "available"
            note = "Transcript text is available for rehearsal analysis."
        elif audio.get("relative_path"):
            status = "unavailable"
            note = "Audio was saved, but no transcript text was captured yet. Add browser speech text or a manual transcript for richer feedback."
        else:
            status = "missing"
            note = "No transcript text was provided. Timing-based feedback is still available."
        return {
            "text": transcript_text,
            "source": rehearsal.get("transcript_source", "") or ("manual" if transcript_text else ""),
            "status": status,
            "note": note,
            "word_count": word_count,
            "words_per_minute": words_per_minute,
        }

    def _heuristic_feedback(self, mission, rehearsal, transcript):
        mission = mission or {}
        sections = self._sanitize_sections(mission.get("script_sections", []))
        section_timings = rehearsal.get("section_timings", []) or self._normalize_section_timings(sections, [], rehearsal.get("total_duration_seconds", 0))
        target_seconds = self._mission_target_seconds(mission, sections)
        actual_seconds = self._safe_float(rehearsal.get("total_duration_seconds"), default=sum(self._safe_float(item.get("actual_seconds"), default=0) for item in section_timings))
        delta_seconds = round(actual_seconds - target_seconds, 1)
        pace_status = self._overall_pace_status(actual_seconds, target_seconds)
        wpm = transcript.get("words_per_minute")
        tempo_status = self._tempo_status(wpm)
        strongest = self._pick_strongest_section(sections, section_timings)
        weakest = self._pick_weakest_section(sections, section_timings)
        interaction_coverage = sum(1 for section in sections if section.get("interaction_goal", "").strip())
        repetitive_phrase = self._repetitive_phrase(transcript.get("text", ""))
        opening_timing = section_timings[0] if section_timings else {}
        closing_timing = section_timings[-1] if section_timings else {}

        overall_pacing = self._overall_pacing_text(target_seconds, actual_seconds, pace_status, tempo_status, wpm)
        main_issue = ""
        next_action = ""
        if pace_status == "too_long":
            main_issue = f"The full run is too long for the target window, with most pressure building in {weakest.get('name', 'the longest section')}."
            next_action = f"Cut one idea or example from {weakest.get('name', 'the longest section')} and rehearse again inside the target window."
        elif pace_status == "too_short":
            main_issue = "The run finishes too early, so at least one section still feels under-developed."
            next_action = f"Add one clearer example or explanation beat to {weakest.get('name', 'the weakest section')} before the next run."
        elif tempo_status == "fast":
            main_issue = "The transcript pace reads fast, which may make the delivery hard to follow even if the total duration is close."
            next_action = "Add two pause cues in your opening and one pause before the conclusion, then rehearse at a calmer speaking speed."
        elif tempo_status == "slow":
            main_issue = "The speaking pace reads slow, so the presentation may lose energy before the key point lands."
            next_action = f"Tighten the wording in {weakest.get('name', 'the softest section')} and keep only the sentence you truly need to say out loud."
        elif closing_timing and closing_timing.get("pace_status") == "short":
            main_issue = "The conclusion ends too quickly, so the takeaway may not stay with the audience."
            next_action = "Write one final cue-card line for the takeaway and one line for the closing pause, then rerun the ending."
        elif opening_timing and opening_timing.get("pace_status") == "long":
            main_issue = "The opening is running long, which delays the main point."
            next_action = "Trim the opening to a short frame-setting move and reach the core idea sooner."
        elif interaction_coverage <= max(1, len(sections) // 3):
            main_issue = "Interaction cues are still thin, so the delivery may feel like reading instead of presenting."
            next_action = "Add one audience-facing cue or pause goal to each major section before the next rehearsal."
        elif transcript.get("status") != "available":
            main_issue = "Timing is available, but transcript detail is still missing for a stronger wording-level review."
            next_action = "Turn on browser speech capture or paste a short transcript next time so the feedback can inspect phrasing and pace more precisely."
        elif repetitive_phrase:
            main_issue = f"Repeated phrasing around '{repetitive_phrase}' may be making the middle of the talk sound circular."
            next_action = "Swap the repeated phrase for a shorter cue card and vary the transition sentence once."
        else:
            main_issue = f"{weakest.get('name', 'One section')} is the least controlled section right now and still needs a cleaner time budget."
            next_action = f"Rehearse {weakest.get('name', 'that section')} once by itself with the target time on screen."

        if pace_status == "on_target":
            main_strength = "The full run stays close to the planned duration, which is a strong base for polishing delivery."
        elif strongest.get("name"):
            main_strength = f"{strongest['name']} already has the clearest time-to-content balance in this run."
        elif interaction_coverage >= max(2, len(sections) - 1):
            main_strength = "The script is already mapped to audience and slide cues instead of acting like a flat transcript."
        else:
            main_strength = "The section structure is clear enough to support another focused rehearsal pass."

        suggestions = self._build_section_suggestions(sections, section_timings)
        strongest_name = strongest.get("name", "Full run")
        weakest_name = weakest.get("name", "Full run")

        return {
            "overall_pacing": overall_pacing,
            "pace_status": pace_status,
            "duration_delta_seconds": delta_seconds,
            "duration_delta_label": self._format_signed_mmss(delta_seconds),
            "words_per_minute": wpm,
            "strongest_section": strongest_name,
            "strongest_section_note": strongest.get("note", ""),
            "weakest_section": weakest_name,
            "weakest_section_note": weakest.get("note", ""),
            "one_main_issue": main_issue,
            "one_main_strength": main_strength,
            "one_next_action": next_action,
            "section_suggestions": suggestions,
        }

    def _mission_target_seconds(self, mission, sections):
        explicit = int(round(self._safe_float((mission or {}).get("target_duration_minutes"), default=0) * 60))
        section_total = sum(max(0, self._safe_int(item.get("target_seconds"), default=0)) for item in sections or [])
        return explicit if explicit > 0 else section_total

    def _overall_pace_status(self, actual_seconds, target_seconds):
        actual_seconds = self._safe_float(actual_seconds, default=0)
        target_seconds = self._safe_float(target_seconds, default=0)
        if target_seconds <= 0 or actual_seconds <= 0:
            return "unknown"
        ratio = actual_seconds / target_seconds
        if ratio >= 1.22:
            return "too_long"
        if ratio >= 1.08:
            return "slightly_long"
        if ratio <= 0.78:
            return "too_short"
        if ratio <= 0.92:
            return "slightly_short"
        return "on_target"

    def _tempo_status(self, words_per_minute):
        speed = self._safe_float(words_per_minute, default=0)
        if speed <= 0:
            return "unknown"
        if speed >= 172:
            return "fast"
        if speed <= 95:
            return "slow"
        return "comfortable"

    def _overall_pacing_text(self, target_seconds, actual_seconds, pace_status, tempo_status, words_per_minute):
        target_label = self._format_mmss(target_seconds)
        actual_label = self._format_mmss(actual_seconds)
        if pace_status == "too_long":
            text = f"The rehearsal ran {actual_label} against a {target_label} target, so it currently feels too long for the assignment."
        elif pace_status == "too_short":
            text = f"The rehearsal finished at {actual_label} against a {target_label} target, so at least one section still needs more substance."
        elif pace_status == "slightly_long":
            text = f"The rehearsal is only a little over target at {actual_label}, but one section still needs tightening."
        elif pace_status == "slightly_short":
            text = f"The rehearsal is slightly short at {actual_label}, so one section can carry a bit more explanation."
        elif pace_status == "on_target":
            text = f"The rehearsal landed near the target window at {actual_label} for a planned {target_label} run."
        else:
            text = "A clear target duration was not available, so pacing is being judged from section balance only."

        if tempo_status == "fast" and words_per_minute:
            text += f" The transcript pace still reads fast at about {int(round(words_per_minute))} words per minute."
        elif tempo_status == "slow" and words_per_minute:
            text += f" The transcript pace reads slow at about {int(round(words_per_minute))} words per minute."
        elif tempo_status == "comfortable" and words_per_minute:
            text += f" The transcript pace looks workable at about {int(round(words_per_minute))} words per minute."
        return text

    def _pick_strongest_section(self, sections, section_timings):
        if not section_timings:
            return {"name": "Full run", "note": "No section timing map was available."}
        section_lookup = {item.get("section_id", ""): item for item in sections}
        best = None
        best_score = None
        for timing in section_timings:
            section = section_lookup.get(timing.get("section_id", ""), {})
            target = max(1, self._safe_float(timing.get("target_seconds"), default=0))
            delta_ratio = abs(self._safe_float(timing.get("delta_seconds"), default=0)) / target
            content_score = sum(1 for field in ("outline", "speaker_notes", "cue_cards") if section.get(field, "").strip())
            interaction_score = 1 if section.get("interaction_goal", "").strip() else 0
            score = (1 - min(delta_ratio, 1.0)) * 100 + content_score * 10 + interaction_score * 6
            if best is None or score > best_score:
                best = {
                    "name": timing.get("name", "Section"),
                    "note": f"This section is closest to its time target and already has the cleanest content scaffold.",
                }
                best_score = score
        return best or {"name": "Full run", "note": ""}

    def _pick_weakest_section(self, sections, section_timings):
        if not section_timings:
            return {"name": "Full run", "note": "No section timing map was available."}
        section_lookup = {item.get("section_id", ""): item for item in sections}
        worst = None
        worst_score = None
        for timing in section_timings:
            section = section_lookup.get(timing.get("section_id", ""), {})
            target = max(1, self._safe_float(timing.get("target_seconds"), default=0))
            delta_ratio = abs(self._safe_float(timing.get("delta_seconds"), default=0)) / target
            content_penalty = 0 if any(section.get(field, "").strip() for field in ("outline", "speaker_notes", "cue_cards")) else 0.5
            interaction_penalty = 0 if section.get("interaction_goal", "").strip() else 0.15
            score = delta_ratio + content_penalty + interaction_penalty
            if worst is None or score > worst_score:
                worst = {
                    "name": timing.get("name", "Section"),
                    "note": f"This section is furthest from its target timing or still missing enough delivery cues.",
                }
                worst_score = score
        return worst or {"name": "Full run", "note": ""}

    def _build_section_suggestions(self, sections, section_timings):
        section_lookup = {item.get("section_id", ""): item for item in sections}
        suggestions = []
        for timing in section_timings:
            section = section_lookup.get(timing.get("section_id", ""), {})
            pace_status = timing.get("pace_status", "balanced")
            if pace_status == "long":
                message = "Trim one supporting idea or compress the example so this section reaches the audience faster."
            elif pace_status == "short":
                message = "Add one clearer explanation beat or example so this section feels complete."
            elif not section.get("interaction_goal", "").strip():
                message = "Add one audience-facing cue, pause goal, or transition line so the section feels live."
            elif not any(section.get(field, "").strip() for field in ("outline", "speaker_notes", "cue_cards")):
                message = "Write your own outline or notes here before the next rehearsal."
            else:
                continue
            suggestions.append({
                "section_name": timing.get("name", "Section"),
                "status": pace_status,
                "suggestion": message,
            })
        return suggestions[:3]

    def _section_pace_status(self, actual_seconds, target_seconds):
        actual = self._safe_float(actual_seconds, default=0)
        target = self._safe_float(target_seconds, default=0)
        if actual <= 0 or target <= 0:
            return "unknown"
        ratio = actual / target
        if ratio >= 1.22:
            return "long"
        if ratio <= 0.78:
            return "short"
        return "balanced"

    def _repetitive_phrase(self, text):
        tokens = [
            token.lower()
            for token in re.findall(r"[A-Za-z']+", text or "")
            if len(token) > 3 and token.lower() not in self.STOPWORDS
        ]
        if len(tokens) < 24:
            return ""
        counts = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        phrase, count = max(counts.items(), key=lambda item: item[1], default=("", 0))
        if count >= 5 and count / max(len(tokens), 1) >= 0.09:
            return phrase
        return ""

    def _merge_feedback(self, heuristic_feedback, llm_payload):
        merged = dict(heuristic_feedback or {})
        for key, limit in (
            ("overall_pacing", 1200),
            ("strongest_section", 180),
            ("strongest_section_note", 600),
            ("weakest_section", 180),
            ("weakest_section_note", 600),
            ("one_main_issue", 1200),
            ("one_main_strength", 1200),
            ("one_next_action", 1200),
        ):
            value = self._clean_text(llm_payload.get(key, ""), max_length=limit)
            if value:
                merged[key] = value
        suggestions = self._normalize_section_suggestions(llm_payload.get("section_suggestions"))
        if suggestions:
            merged["section_suggestions"] = suggestions
        return merged

    def _normalize_section_suggestions(self, items):
        if not isinstance(items, list):
            return []
        normalized = []
        for item in items[:3]:
            if isinstance(item, dict):
                section_name = self._clean_text(item.get("section_name", ""), max_length=180)
                suggestion = self._clean_text(item.get("suggestion", ""), max_length=800)
                status = self._clean_text(item.get("status", ""), max_length=40).lower()
                if section_name and suggestion:
                    normalized.append({
                        "section_name": section_name,
                        "status": status or "note",
                        "suggestion": suggestion,
                    })
            elif isinstance(item, str):
                suggestion = self._clean_text(item, max_length=800)
                if suggestion:
                    normalized.append({
                        "section_name": "Section",
                        "status": "note",
                        "suggestion": suggestion,
                    })
        return normalized

    def _build_hud_summary(self, mission, rehearsal, transcript, feedback):
        sections = self._sanitize_sections((mission or {}).get("script_sections", []))
        presentation_state = self._normalize_presentation_state(
            sections=sections,
            existing=(mission or {}).get("presentation_state"),
        )
        active_card = self._find_active_card(sections, presentation_state)
        next_card = self._next_card_brief(sections, presentation_state)
        target_seconds = self._mission_target_seconds(mission or {}, sections)
        actual_seconds = self._safe_float(rehearsal.get("total_duration_seconds"), default=0)
        pace_status = feedback.get("pace_status", "unknown")
        if pace_status == "on_target":
            final_status = "On target"
        elif pace_status in {"too_long", "slightly_long"}:
            final_status = "Running long"
        elif pace_status in {"too_short", "slightly_short"}:
            final_status = "Running short"
        elif transcript.get("words_per_minute") and transcript.get("words_per_minute") >= 172:
            final_status = "Speaking fast"
        else:
            final_status = "Rehearse again"
        return {
            "mode": "rehearse_summary",
            "target_duration_seconds": target_seconds,
            "actual_duration_seconds": round(actual_seconds, 1),
            "elapsed_vs_target": self._format_signed_mmss(round(actual_seconds - target_seconds, 1)),
            "pace_status": pace_status,
            "current_or_final_status": final_status,
            "strength": self._shorten_line(feedback.get("one_main_strength", ""), 92),
            "issue": self._shorten_line(feedback.get("one_main_issue", ""), 92),
            "next_action": self._shorten_line(feedback.get("one_next_action", ""), 92),
            "active_slide_index": active_card.get("slide_index", 0),
            "active_slide_title": active_card.get("slide_title", ""),
            "active_slide_anchor": active_card.get("slide_anchor", ""),
            "presentation_mode": presentation_state.get("presentation_mode", "rehearse"),
            "cue_view": presentation_state.get("cue_view", "visible"),
            "control_source": presentation_state.get("control_source", "phone"),
            "next_slide_index": next_card.get("slide_index", 0),
            "next_slide_title": next_card.get("slide_title", ""),
            "transcript_status": transcript.get("status", "missing"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _build_live_hud_payload(self, mission, latest_rehearsal=None):
        mission = mission or {}
        mission_id = self._clean_text(mission.get("mission_id", ""), max_length=80)
        sections = self._sanitize_sections(mission.get("script_sections", []))
        presentation_state = self._normalize_presentation_state(
            sections=sections,
            existing=mission.get("presentation_state"),
        )
        companion_sync = self._normalize_companion_sync(
            mission_id=mission_id,
            presentation_state=presentation_state,
            existing=mission.get("companion_sync"),
        )
        active_card = self._find_active_card(sections, presentation_state)
        next_card = self._next_card_brief(sections, presentation_state)
        latest_rehearsal = latest_rehearsal or self._latest_rehearsal_for_mission(mission_id)
        latest_feedback = {}
        latest_hud = {}
        if latest_rehearsal:
            latest_hud = self.get_hud_summary(latest_rehearsal.get("rehearsal_id", "")) or {}
            latest_feedback = (latest_rehearsal.get("analysis", {}) or {}).get("feedback", {}) or {}
        section_hint = self._section_duration_hint(
            self._estimate_section_seconds(active_card or {}),
            (active_card or {}).get("target_seconds", 0),
        )
        if latest_hud.get("current_or_final_status"):
            status_line = latest_hud.get("current_or_final_status", "")
        elif section_hint.get("status") == "long":
            status_line = "Current slide looks dense"
        elif section_hint.get("status") == "short":
            status_line = "Current slide may need one more beat"
        else:
            status_line = "Current slide ready"
        cue_source = ""
        if presentation_state.get("cue_view") == "visible":
            cue_source = (active_card or {}).get("cue_cards") or (active_card or {}).get("outline") or (active_card or {}).get("slide_anchor")
        issue_line = latest_hud.get("issue") or latest_feedback.get("one_main_issue", "")
        next_action_line = latest_hud.get("next_action") or latest_feedback.get("one_next_action", "")
        return {
            "mode": "presentation_live",
            "mission_id": mission_id,
            "session_id": companion_sync.get("session_id", ""),
            "sync_status": companion_sync.get("sync_status", "ready"),
            "sync_revision": self._safe_int(companion_sync.get("sync_revision"), default=1),
            "control_source": presentation_state.get("control_source", "phone"),
            "presentation_mode": presentation_state.get("presentation_mode", "rehearse"),
            "cue_view": presentation_state.get("cue_view", "visible"),
            "active_slide_index": active_card.get("slide_index", 0),
            "active_slide_title": active_card.get("slide_title", ""),
            "active_slide_anchor": active_card.get("slide_anchor", ""),
            "status_line": self._shorten_line(status_line, 84),
            "cue_line": self._shorten_line(cue_source, 96),
            "interaction_hint": self._shorten_line((active_card or {}).get("interaction_goal", ""), 84),
            "next_slide_index": next_card.get("slide_index", 0),
            "next_slide_title": next_card.get("slide_title", ""),
            "issue_line": self._shorten_line(issue_line, 84),
            "next_action_line": self._shorten_line(next_action_line, 84),
            "target_seconds": self._safe_int((active_card or {}).get("target_seconds"), default=0),
            "target_label": self._format_mmss((active_card or {}).get("target_seconds", 0)),
            "surface_status": {
                "web": self._connection_status(companion_sync.get("last_web_seen_at", "")),
                "phone": self._connection_status(companion_sync.get("last_phone_seen_at", "")),
                "rokid_hud": self._connection_status(companion_sync.get("last_hud_seen_at", "")),
            },
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _build_intake_request_bundle(self, task_text, draft_candidates, draft_sections):
        schema = self._intake_schema()
        instruction = (
            "You are supporting an academic presentation preparation workflow. "
            "Extract assignment fields only. Do not write a script, do not invent missing facts, "
            "and do not become a tutor. You may suggest section names, slide anchors, and interaction goals, "
            "but never generate the student's final content. Return strict JSON only."
        )
        prompt_payload = {
            "task_text": task_text,
            "draft_candidates": draft_candidates,
            "draft_sections": draft_sections,
            "schema": schema,
        }
        return {
            "instruction": instruction,
            "prompt": json.dumps(prompt_payload, ensure_ascii=False),
            "schema": schema,
            "context": {"task_text": task_text},
            "draft": {"candidates": draft_candidates, "sections": draft_sections},
        }

    def _build_analysis_request_bundle(self, mission, rehearsal, transcript, feedback):
        schema = self._analysis_schema()
        instruction = (
            "You are analyzing a student's presentation rehearsal. "
            "Do not generate a script, do not teach the subject content, and do not write answers for the student. "
            "You may only refine the rehearsal feedback about pacing, section balance, audience interaction, "
            "and the next revision action. Return strict JSON only."
        )
        prompt_payload = {
            "mission": {
                "title": mission.get("title", ""),
                "course": mission.get("course", ""),
                "deliverable_type": mission.get("deliverable_type", ""),
                "target_duration_minutes": mission.get("target_duration_minutes", 0),
                "audience": mission.get("audience", ""),
                "teacher_requirements": mission.get("teacher_requirements", ""),
            },
            "sections": [
                {
                    "name": section.get("name", ""),
                    "slide_index": section.get("slide_index", 0),
                    "slide_title": section.get("slide_title", ""),
                    "slide_anchor": section.get("slide_anchor", ""),
                    "interaction_goal": section.get("interaction_goal", ""),
                    "target_seconds": section.get("target_seconds", 0),
                }
                for section in self._sanitize_sections(mission.get("script_sections", []))
            ],
            "rehearsal": {
                "audio_source": rehearsal.get("audio_source", ""),
                "total_duration_seconds": rehearsal.get("total_duration_seconds", 0),
                "section_timings": rehearsal.get("section_timings", []),
                "self_rating": rehearsal.get("self_rating", 0),
                "notes": rehearsal.get("notes", ""),
            },
            "transcript": {
                "status": transcript.get("status", "missing"),
                "word_count": transcript.get("word_count", 0),
                "words_per_minute": transcript.get("words_per_minute"),
                "excerpt": self._clean_text(transcript.get("text", ""), max_length=2600, preserve_lines=True),
            },
            "draft_feedback": feedback,
            "schema": schema,
        }
        return {
            "instruction": instruction,
            "prompt": json.dumps(prompt_payload, ensure_ascii=False),
            "schema": schema,
            "context": prompt_payload,
            "draft": feedback,
        }

    def _intake_schema(self):
        return {
            "title": "string",
            "course": "string",
            "deadline": "string",
            "deliverable_type": "string",
            "target_duration_minutes": "number",
            "audience": "string",
            "teacher_requirements": "string",
            "suggested_sections": [
                {
                    "name": "string",
                    "slide_index": "number",
                    "slide_title": "string",
                    "slide_anchor": "string",
                    "interaction_goal": "string",
                    "target_seconds": "number",
                }
            ],
        }

    def _analysis_schema(self):
        return {
            "overall_pacing": "string",
            "strongest_section": "string",
            "strongest_section_note": "string",
            "weakest_section": "string",
            "weakest_section_note": "string",
            "one_main_issue": "string",
            "one_main_strength": "string",
            "one_next_action": "string",
            "section_suggestions": [
                {
                    "section_name": "string",
                    "status": "string",
                    "suggestion": "string",
                }
            ],
        }

    def _maybe_generate_model_layer(
        self,
        request_bundle,
        requested_provider,
        configured_provider,
        effective_provider,
        model_override="",
    ):
        if effective_provider == "heuristic":
            return None, self._generation_meta(
                mode="heuristic",
                requested_provider=requested_provider,
                resolved_provider="heuristic",
                configured_provider=configured_provider,
                provider_available=True,
                note="Heuristic mode was selected explicitly, so no model provider was used.",
                model_override=model_override,
            )

        if not self._provider_is_configured(effective_provider):
            return None, self._generation_meta(
                mode="heuristic",
                requested_provider=requested_provider,
                resolved_provider="heuristic",
                configured_provider=configured_provider,
                provider_available=False,
                note=f"{self._provider_label(effective_provider)} is not configured, so the module stayed in heuristic mode.",
                model_override=model_override,
            )

        if effective_provider == "ollama":
            llm_payload, note = self._generate_with_ollama(request_bundle, model_override=model_override)
            model_name = self._ollama_model(model_override=model_override)
        elif effective_provider == "remote":
            llm_payload, note = self._generate_with_remote(request_bundle)
            model_name = self._provider_model_name("remote")
        elif effective_provider == "openai":
            llm_payload, note = self._generate_with_openai(request_bundle)
            model_name = self._provider_model_name("openai")
        else:
            llm_payload, note = None, f"Unknown provider `{effective_provider}`, so heuristic mode stayed active."
            model_name = ""

        if not llm_payload:
            return None, self._generation_meta(
                mode="heuristic",
                requested_provider=requested_provider,
                resolved_provider="heuristic",
                configured_provider=configured_provider,
                provider_available=True,
                model=model_name,
                note=note,
                model_override=model_override,
            )

        return llm_payload, self._generation_meta(
            mode=effective_provider,
            requested_provider=requested_provider,
            resolved_provider=effective_provider,
            configured_provider=configured_provider,
            provider_available=True,
            model=model_name,
            note=note,
            model_override=model_override,
        )

    def _generate_with_ollama(self, request_bundle, model_override=""):
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api").rstrip("/")
        model = self._ollama_model(model_override=model_override)
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": request_bundle["instruction"]},
                        {"role": "user", "content": request_bundle["prompt"]},
                    ],
                    "options": {"temperature": 0.2},
                },
                timeout=self._provider_timeout("ollama", default=120),
            )
            response.raise_for_status()
            raw = response.json()
            content = raw.get("message", {}).get("content", "")
            parsed = self._parse_model_json(content)
            if not parsed:
                return None, f"Ollama returned no valid JSON for `{model}`, so heuristic mode stayed active."
            return parsed, f"Presentation companion wording refined locally with Ollama `{model}`."
        except Exception as exc:
            return None, f"Ollama refinement failed ({exc}), so heuristic mode stayed active."

    def _generate_with_remote(self, request_bundle):
        url = self._remote_url()
        token = os.getenv("PRESENTATION_REMOTE_AUTH_TOKEN", "").strip() or os.getenv("REFLECTION_REMOTE_AUTH_TOKEN", "").strip()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = requests.post(
                url,
                headers=headers,
                json={
                    "instruction": request_bundle["instruction"],
                    "prompt": request_bundle["prompt"],
                    "schema": request_bundle["schema"],
                    "context": request_bundle["context"],
                    "draft": request_bundle["draft"],
                },
                timeout=self._provider_timeout("remote", default=45),
            )
            response.raise_for_status()
            raw = response.json()
            parsed = self._parse_remote_payload(raw)
            if not parsed:
                return None, "The remote presentation provider returned no valid JSON, so heuristic mode stayed active."
            return parsed, "Presentation wording refined through the configured remote provider."
        except Exception as exc:
            return None, f"Remote presentation provider failed ({exc}), so heuristic mode stayed active."

    def _generate_with_openai(self, request_bundle):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = self._provider_model_name("openai")
        request_payload = {
            "model": model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": request_bundle["instruction"]}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": request_bundle["prompt"]}],
                },
            ],
            "text": {"format": {"type": "json_object"}},
            "max_output_tokens": 1200,
        }
        try:
            response = requests.post(
                f"{base_url}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=request_payload,
                timeout=self._provider_timeout("openai", default=45),
            )
            response.raise_for_status()
            raw = response.json()
            output_text = self._extract_openai_output_text(raw)
            parsed = self._parse_model_json(output_text)
            if not parsed:
                return None, f"OpenAI returned no valid JSON for `{model}`, so heuristic mode stayed active."
            return parsed, f"Presentation wording refined with OpenAI `{model}`."
        except Exception as exc:
            return None, f"OpenAI refinement failed ({exc}), so heuristic mode stayed active."

    def _parse_remote_payload(self, payload):
        if isinstance(payload, dict):
            normalized = self._extract_model_patch(payload)
            if normalized:
                return normalized
            for key in ("result", "output", "data"):
                candidate = payload.get(key)
                if isinstance(candidate, dict):
                    normalized = self._extract_model_patch(candidate)
                    if normalized:
                        return normalized
                if isinstance(candidate, str):
                    parsed = self._parse_model_json(candidate)
                    if parsed:
                        return parsed
        return None

    def _parse_model_json(self, text):
        if isinstance(text, dict):
            return self._extract_model_patch(text)
        if not isinstance(text, str) or not text.strip():
            return None
        candidate = re.sub(r"^```(?:json)?\s*", "", text.strip())
        candidate = re.sub(r"\s*```$", "", candidate)
        try:
            parsed = json.loads(candidate)
            return self._extract_model_patch(parsed)
        except Exception:
            return None

    def _extract_model_patch(self, payload):
        if not isinstance(payload, dict):
            return None
        candidates = [payload]
        for key in ("json", "schema", "result", "output", "data"):
            value = payload.get(key)
            if isinstance(value, dict):
                candidates.append(value)
        for candidate in candidates:
            normalized = self._normalize_model_candidate(candidate)
            if normalized:
                return normalized
        for value in payload.values():
            if isinstance(value, dict):
                normalized = self._extract_model_patch(value)
                if normalized:
                    return normalized
        return None

    def _normalize_model_candidate(self, candidate):
        if not isinstance(candidate, dict):
            return None
        normalized = {}
        for key, limit in (
            ("title", 180),
            ("course", 180),
            ("deadline", 180),
            ("deliverable_type", 120),
            ("audience", 240),
            ("teacher_requirements", 2400),
            ("overall_pacing", 1200),
            ("strongest_section", 180),
            ("strongest_section_note", 600),
            ("weakest_section", 180),
            ("weakest_section_note", 600),
            ("one_main_issue", 1200),
            ("one_main_strength", 1200),
            ("one_next_action", 1200),
        ):
            value = self._clean_text(candidate.get(key, ""), max_length=limit, preserve_lines=(key == "teacher_requirements"))
            if value:
                normalized[key] = value
        duration = self._safe_float(candidate.get("target_duration_minutes"), default=0)
        if duration > 0:
            normalized["target_duration_minutes"] = round(duration, 1)
        sections = self._normalize_llm_sections(candidate.get("suggested_sections", []), duration or 5)
        if sections:
            normalized["suggested_sections"] = sections
        section_suggestions = self._normalize_section_suggestions(candidate.get("section_suggestions"))
        if section_suggestions:
            normalized["section_suggestions"] = section_suggestions
        return normalized or None

    def _extract_openai_output_text(self, payload):
        if isinstance(payload.get("output_text"), str) and payload.get("output_text").strip():
            return payload["output_text"].strip()
        parts = []
        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
        return "".join(parts).strip()

    def _resolve_provider_request(self, provider_override):
        requested = self._normalize_provider(provider_override or "auto")
        configured = self._configured_provider()
        effective = configured if requested == "auto" else requested
        if effective not in self.ALL_PROVIDERS:
            effective = "heuristic"
        return requested, configured, effective

    def _normalize_provider(self, value):
        normalized = str(value or "").strip().lower()
        if normalized not in self.ALL_PROVIDERS:
            return "auto"
        return normalized

    def _configured_provider(self):
        provider = self._normalize_provider(
            os.getenv("PRESENTATION_LLM_PROVIDER", "").strip() or os.getenv("LLM_PROVIDER", "ollama")
        )
        if provider == "auto":
            return "ollama"
        return provider

    def _provider_is_configured(self, provider):
        provider = self._normalize_provider(provider)
        if provider in {"auto", "heuristic"}:
            return True
        if provider == "ollama":
            return bool(self._ollama_model()) and bool(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api").strip())
        if provider == "remote":
            return bool(self._remote_url())
        if provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY", "").strip())
        return False

    def _provider_label(self, provider):
        return {
            "auto": "Default Provider",
            "heuristic": "Heuristic",
            "ollama": "Ollama Local",
            "remote": "Remote API",
            "openai": "OpenAI",
        }.get(str(provider or "").strip().lower(), "Heuristic")

    def _provider_model_name(self, provider):
        provider = self._normalize_provider(provider)
        if provider == "ollama":
            return self._ollama_model()
        if provider == "remote":
            return os.getenv("PRESENTATION_REMOTE_LABEL", "").strip() or os.getenv("REFLECTION_REMOTE_LABEL", "remote-presentation-service").strip() or "remote-presentation-service"
        if provider == "openai":
            return os.getenv("OPENAI_PRESENTATION_MODEL", "").strip() or os.getenv("OPENAI_REFLECTION_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
        return ""

    def _ollama_model(self, model_override=""):
        cleaned_override = self._clean_model_name(model_override)
        if cleaned_override:
            return cleaned_override
        return os.getenv("PRESENTATION_OLLAMA_MODEL", "").strip() or os.getenv("OLLAMA_MODEL", "qwen3:4b").strip() or "qwen3:4b"

    def _remote_url(self):
        return os.getenv("PRESENTATION_REMOTE_URL", "").strip() or os.getenv("REFLECTION_REMOTE_URL", "").strip()

    def _provider_timeout(self, provider, default=45):
        specific_key = f"{str(provider or '').strip().upper()}_TIMEOUT_SECONDS"
        for key in (specific_key, "PRESENTATION_PROVIDER_TIMEOUT_SECONDS", "REFLECTION_PROVIDER_TIMEOUT_SECONDS"):
            raw = os.getenv(key, "").strip()
            if not raw:
                continue
            try:
                value = int(float(raw))
                if value > 0:
                    return value
            except Exception:
                continue
        return default

    def _generation_meta(
        self,
        mode="heuristic",
        requested_provider="auto",
        resolved_provider="heuristic",
        configured_provider="ollama",
        provider_available=False,
        model="",
        note="",
        model_override="",
    ):
        return {
            "mode": mode,
            "used_llm": mode != "heuristic",
            "requested_provider": requested_provider,
            "resolved_provider": resolved_provider,
            "configured_provider": configured_provider,
            "provider_available": bool(provider_available),
            "provider_label": self._provider_label(resolved_provider),
            "configured_label": self._provider_label(configured_provider),
            "model": model or self._provider_model_name(resolved_provider),
            "configured_model": self._provider_model_name(configured_provider),
            "model_override": self._clean_model_name(model_override),
            "note": note,
        }

    def _normalize_audio_source(self, value):
        normalized = str(value or "").strip().lower()
        if normalized in {"browser_mic", "phone_mic", "rokid_mic"}:
            return normalized
        return "browser_mic"

    def _normalize_transcript_source(self, value, has_text=False):
        normalized = str(value or "").strip().lower()
        if normalized in {"browser_speech", "manual", "phone_app", "rokid_companion"}:
            return normalized
        return "manual" if has_text else ""

    def _build_id(self, prefix):
        return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"

    def _word_count(self, text):
        return len(re.findall(r"[A-Za-z0-9']+", str(text or "")))

    def _format_mmss(self, seconds):
        total_seconds = max(0, int(round(self._safe_float(seconds, default=0))))
        minutes = total_seconds // 60
        remainder = total_seconds % 60
        return f"{minutes:02d}:{remainder:02d}"

    def _format_signed_mmss(self, seconds):
        value = self._safe_float(seconds, default=0)
        sign = "+" if value >= 0 else "-"
        return f"{sign}{self._format_mmss(abs(value))}"

    def _shorten_line(self, text, limit):
        cleaned = self._clean_text(text, max_length=limit)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: max(0, limit - 3)].rstrip() + "..."

    def _safe_float(self, value, default=0):
        try:
            if value in {"", None}:
                return default
            return float(value)
        except Exception:
            return default

    def _safe_int(self, value, default=0):
        try:
            if value in {"", None}:
                return default
            return int(round(float(value)))
        except Exception:
            return default

    def _as_bool(self, value):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _clean_model_name(self, value):
        value = self._clean_text(value, max_length=120)
        if not value:
            return ""
        return re.sub(r"[^A-Za-z0-9:_\.\-]", "", value)

    def _clean_text(self, value, max_length=400, preserve_lines=False):
        if value is None:
            return ""
        text = str(value).replace("\r\n", "\n").replace("\r", "\n")
        if preserve_lines:
            lines = [" ".join(line.split()) for line in text.split("\n")]
            text = "\n".join(line for line in lines if line)
        else:
            text = " ".join(text.split())
        return text[:max_length].strip()
