import json
import os
import re

import requests


class ReflectionCoach:
    MODEL_PROVIDERS = {"ollama", "remote", "openai"}
    ALL_PROVIDERS = {"auto", "heuristic", "ollama", "remote", "openai"}

    def __init__(self, logger):
        self.logger = logger

    def build_payload(
        self,
        session_id=None,
        dataset="live",
        event_id=None,
        learner_note="",
        next_goal="",
        use_llm=False,
        provider_override="auto",
        model_override="",
    ):
        learner_note = self._clean_text(learner_note, max_length=1200)
        next_goal = self._clean_text(next_goal, max_length=240)
        model_override = self._clean_model_name(model_override)
        requested_event_id = self._safe_int(event_id, default=0) or None
        context = self.logger.build_reflection_context(session_id=session_id, dataset=dataset, event_id=requested_event_id)
        requested_provider, configured_provider, effective_provider = self._resolve_provider_request(provider_override)

        payload = {
            "dataset": context.get("dataset", dataset),
            "session_id": context.get("session_id", session_id or ""),
            "requested_event_id": context.get("requested_event_id", requested_event_id),
            "selected_event_id": context.get("selected_event_id"),
            "session_options": context.get("session_options", []),
            "summary": context.get("summary", {}),
            "highlight_event": context.get("highlight_event"),
            "events": context.get("events", []),
            "timeline": context.get("timeline", {}),
            "assets": context.get("assets", {}),
            "distributions": context.get("distributions", {}),
            "anchors": context.get("anchors", {}),
            "learner_note": learner_note,
            "next_goal": next_goal,
            "module_boundary": (
                "This module coaches reflection on learning process and self-regulation. "
                "It does not teach the content itself, replace tutoring, or overlap with note-taking features."
            ),
            "provider_options": self._provider_options(),
            "configured_provider": configured_provider,
            "empty": bool(context.get("empty", False)),
        }

        if context.get("empty"):
            payload.update({
                "signature": {
                    "key": "no_data",
                    "label": "No Data Yet",
                    "tone": "signal",
                    "title": "Run a session first, then come back for reflection coaching.",
                    "detail": "The coach needs a completed live or demo session before it can read learning patterns.",
                    "next_boundary": "Start the HUD or generate demo assets so this page has evidence to work from.",
                },
                "coach_summary": {
                    "headline": "No session data yet",
                    "overview": "The reflection coach becomes useful after a real or demo study session has generated structured state logs.",
                    "why_it_matters": "Without session evidence, the module would fall back to generic advice instead of process-specific coaching.",
                    "next_boundary": "Run a session, then regenerate this page.",
                },
                "coach_cards": [],
                "reflection_questions": [],
                "next_session_experiments": [],
                "evidence_cards": [],
                "coach_memo": "No reflection memo is available yet because no session data was found.",
                "generation": self._generation_meta(
                    mode="heuristic",
                    requested_provider=requested_provider,
                    resolved_provider="heuristic",
                    configured_provider=configured_provider,
                    provider_available=self._provider_is_configured(effective_provider),
                    note="No session data was found.",
                ),
            })
            return payload

        signature = self._select_signature(context)
        coach_summary = self._build_coach_summary(signature, context, learner_note, next_goal)
        reflection_questions = self._build_reflection_questions(signature, context)
        next_session_experiments = self._build_experiments(signature, context, next_goal)
        evidence_cards = self._build_evidence_cards(signature, context)
        coach_cards = self._build_coach_cards(signature, context, coach_summary)
        coach_memo = self._build_coach_memo(signature, context, coach_summary, learner_note, next_goal)

        payload.update({
            "signature": signature,
            "coach_summary": coach_summary,
            "coach_cards": coach_cards,
            "reflection_questions": reflection_questions,
            "next_session_experiments": next_session_experiments,
            "evidence_cards": evidence_cards,
            "coach_memo": coach_memo,
            "generation": self._generation_meta(
                mode="heuristic",
                requested_provider=requested_provider,
                resolved_provider="heuristic",
                configured_provider=configured_provider,
                provider_available=self._provider_is_configured(effective_provider),
                note=self._default_generation_note(requested_provider, configured_provider, effective_provider),
            ),
        })

        if use_llm:
            llm_payload, generation = self._maybe_generate_model_layer(
                context,
                payload,
                requested_provider,
                configured_provider,
                effective_provider,
                model_override=model_override,
            )
            if llm_payload:
                payload["coach_summary"].update({
                    key: value
                    for key, value in {
                        "headline": llm_payload.get("headline"),
                        "overview": llm_payload.get("overview"),
                        "why_it_matters": llm_payload.get("why_it_matters"),
                        "next_boundary": llm_payload.get("next_boundary"),
                    }.items()
                    if value
                })
                if llm_payload.get("coach_memo"):
                    payload["coach_memo"] = llm_payload["coach_memo"]
                if self._valid_question_list(llm_payload.get("reflection_questions")):
                    payload["reflection_questions"] = llm_payload["reflection_questions"][:3]
                if self._valid_experiment_list(llm_payload.get("next_session_experiments")):
                    payload["next_session_experiments"] = llm_payload["next_session_experiments"][:3]
            payload["generation"] = generation

        return payload

    def provider_status(self, provider_override="auto", model_override=""):
        model_override = self._clean_model_name(model_override)
        requested_provider, configured_provider, effective_provider = self._resolve_provider_request(provider_override)
        ollama_status = self._ollama_status()
        supports_model_override = requested_provider == "ollama" or (requested_provider == "auto" and configured_provider == "ollama")
        provider_available = self._provider_runtime_available(effective_provider, ollama_status=ollama_status)
        configured_model = self._provider_model_name(configured_provider)
        selected_model = self._provider_model_name(effective_provider, model_override=model_override)

        return {
            "requested_provider": requested_provider,
            "configured_provider": configured_provider,
            "configured_label": self._provider_label(configured_provider),
            "effective_provider": effective_provider,
            "effective_label": self._provider_label(effective_provider),
            "provider_available": provider_available,
            "llm_available": self._any_model_provider_configured(),
            "configured_model": configured_model,
            "selected_model": selected_model,
            "model_override": model_override,
            "supports_model_override": supports_model_override,
            "provider_options": self._provider_options(),
            "model_options": self._model_options(
                configured_provider=configured_provider,
                supports_model_override=supports_model_override,
                model_override=model_override,
                ollama_status=ollama_status,
            ),
            "ollama": ollama_status,
            "remote": {
                "configured": self._provider_is_configured("remote"),
                "label": self._provider_label("remote"),
                "model": self._provider_model_name("remote"),
            },
            "openai": {
                "configured": self._provider_is_configured("openai"),
                "label": self._provider_label("openai"),
                "model": self._provider_model_name("openai"),
            },
        }

    def _select_signature(self, context):
        summary = context.get("summary", {})
        top_event = context.get("highlight_event") or {}
        closing_state = context.get("anchors", {}).get("closing_state", {})
        avg_load = self._safe_float(summary.get("avg_load", 0))
        avg_alignment = self._safe_float(summary.get("avg_alignment", 0))
        avg_fatigue = self._safe_float(summary.get("avg_fatigue", 0))
        avg_switching = self._safe_float(summary.get("avg_switching", 0))
        productive_ratio = self._safe_float(summary.get("productive_struggle_ratio", 0))
        off_task_ratio = self._safe_float(summary.get("off_task_ratio", 0))
        low_conf_ratio = self._safe_float(summary.get("low_confidence_ratio", 0))
        difficulty_count = int(summary.get("difficulty_count", 0) or 0)
        top_hint = str(top_event.get("state_hint", "")).strip().lower()
        closing_hint = str(closing_state.get("state_hint", "")).strip().lower()

        if low_conf_ratio >= 22:
            return {
                "key": "signal_check",
                "label": "Signal Check",
                "tone": "signal",
                "title": "This session needs cleaner signal conditions before deep interpretation.",
                "detail": "Low-confidence periods were frequent enough that we should stabilize the setup first, then interpret performance.",
                "next_boundary": "Keep the opening minute visually and physically stable so the next session starts from a cleaner baseline.",
            }

        if top_hint == "fatigue_risk" or closing_hint == "fatigue_risk" or avg_fatigue >= 46:
            return {
                "key": "fatigue_drag",
                "label": "Fatigue Drag",
                "tone": "warn",
                "title": "Fatigue likely became a stronger limiter than the material itself.",
                "detail": "The session carries a sustained fatigue signature, so recovery timing matters as much as review strategy.",
                "next_boundary": "Treat the next replay as a shorter, cleaner attempt instead of pushing through the same pace.",
            }

        if top_hint == "productive_struggle" or (difficulty_count > 0 and productive_ratio >= max(10.0, off_task_ratio + 4.0)):
            return {
                "key": "productive_challenge",
                "label": "Productive Challenge",
                "tone": "cool",
                "title": "This looked more like productive struggle than simple drift.",
                "detail": "Load rose, but the learner stayed comparatively aligned, which points to real conceptual effort rather than random disengagement.",
                "next_boundary": "Protect the exact segment where effort turned heavy, and replay it more slowly without changing targets.",
            }

        if top_hint == "off_task_risk" or off_task_ratio >= max(10.0, productive_ratio + 4.0) or avg_switching >= 38:
            return {
                "key": "switching_drift",
                "label": "Switching Drift",
                "tone": "high",
                "title": "Target switching likely disrupted the learning rhythm.",
                "detail": "The stronger pattern here is drift pressure: the session lost stability because attention kept moving between targets or actions.",
                "next_boundary": "Reduce switching pressure before trying to rescue understanding with more effort.",
            }

        if difficulty_count == 0 and avg_load < 35 and avg_alignment >= 70:
            return {
                "key": "steady_control",
                "label": "Steady Control",
                "tone": "good",
                "title": "The study rhythm stayed controlled and review-ready.",
                "detail": "This session stayed comparatively stable, so the next opportunity is to preserve what worked and add a slightly harder target.",
                "next_boundary": "Keep the same setup and turn one stable block into a deliberate stretch block next time.",
            }

        return {
            "key": "mixed_regulation",
            "label": "Mixed Regulation",
            "tone": "warn",
            "title": "The session showed mixed regulation pressure rather than one clean failure mode.",
            "detail": "Several pressures appeared together, so the best next step is to control one variable tightly instead of changing everything at once.",
            "next_boundary": "Pick one boundary for the next attempt: pace, source switching, or recovery timing.",
        }

    def _build_coach_summary(self, signature, context, learner_note, next_goal):
        summary = context.get("summary", {})
        top_event = context.get("highlight_event") or {}
        primary_mode = str(summary.get("primary_task_mode", "reading")).replace("-", " ").title()
        event_text = "No sustained difficulty event was recorded."
        if top_event:
            event_text = (
                f"The strongest segment was D{top_event.get('event_id', '?')} "
                f"({top_event.get('time_window', '--')}) in {str(top_event.get('task_mode', primary_mode)).replace('-', ' ')} mode."
            )

        note_text = ""
        if learner_note:
            note_text = f' The learner note was: "{learner_note}".'

        goal_text = ""
        if next_goal:
            goal_text = f' The next session goal is "{next_goal}".'

        return {
            "headline": signature["title"],
            "overview": (
                f"This {primary_mode.lower()} session lasted {summary.get('duration_label', '00:00')} "
                f"with average load {int(round(self._safe_float(summary.get('avg_load', 0))))} "
                f"and fatigue {int(round(self._safe_float(summary.get('avg_fatigue', 0))))}. "
                f"{event_text}{note_text}{goal_text}"
            ),
            "why_it_matters": (
                f"{signature['detail']} The current evidence suggests that the review should focus on process regulation "
                f"rather than adding more material immediately."
            ),
            "next_boundary": signature["next_boundary"],
        }

    def _build_coach_cards(self, signature, context, coach_summary):
        top_event = context.get("highlight_event") or {}
        closing_state = context.get("anchors", {}).get("closing_state", {})
        event_title = "No sustained event to replay first"
        event_detail = "Use the evidence cards below as a light reflection map."
        if top_event:
            event_title = f"D{top_event.get('event_id', '?')} is the best replay target"
            event_detail = (
                f"{top_event.get('time_window', '--')} reached {top_event.get('severity_label', 'MEDIUM')} difficulty. "
                f"{top_event.get('catch_up_action', '')}"
            ).strip()

        closing_title = f"Session ended in {closing_state.get('state_hint_label', 'Stable')}"
        closing_detail = closing_state.get("guidance") or "No closing guidance was recorded for this session."

        return [
            {
                "eyebrow": "Session read",
                "title": signature["label"],
                "detail": coach_summary["why_it_matters"],
                "tone": signature["tone"],
            },
            {
                "eyebrow": "Replay point",
                "title": event_title,
                "detail": event_detail,
                "tone": "high" if top_event else "good",
            },
            {
                "eyebrow": "Carry-forward rule",
                "title": closing_title,
                "detail": closing_detail,
                "tone": "signal" if str(closing_state.get("confidence_level", "")).lower() == "low" else "cool",
            },
        ]

    def _build_reflection_questions(self, signature, context):
        top_event = context.get("highlight_event") or {}
        time_window = top_event.get("time_window", "the main difficulty window")
        mode_text = str(top_event.get("task_mode") or context.get("summary", {}).get("primary_task_mode", "reading")).replace("-", " ")
        key = signature["key"]

        if key == "productive_challenge":
            return [
                {"question": f"During {time_window}, what exact step in {mode_text} mode first changed from understandable to effortful?"},
                {"question": "When load rose, were you still following one source consistently, or did you start scanning for rescue elsewhere?"},
                {"question": "If you replay that segment once, what would you slow down without changing the material itself?"},
            ]
        if key == "switching_drift":
            return [
                {"question": f"What triggered the first unnecessary switch before or during {time_window}?"},
                {"question": "Which extra source, window, or action felt helpful in the moment but actually fragmented the task?"},
                {"question": "What single anchor could keep the next attempt on one target for the first two minutes?"},
            ]
        if key == "fatigue_drag":
            return [
                {"question": "At what moment did effort stop feeling purposeful and start feeling heavy or dull?"},
                {"question": "What earlier cue could tell you to pause before fatigue turns into low-quality persistence?"},
                {"question": "How short should the next replay block be if the goal is clarity rather than endurance?"},
            ]
        if key == "signal_check":
            return [
                {"question": "What most likely destabilized the signal: posture baseline, movement, switching, or scene quality?"},
                {"question": "What can you keep physically and visually constant during the first clean minute of the next session?"},
                {"question": "What would count as a trustworthy calibration start before you interpret the coaching output seriously?"},
            ]
        if key == "steady_control":
            return [
                {"question": "Which part of this session felt easiest to sustain, and what behavior helped that stability?"},
                {"question": "What small challenge could you add next time without breaking the current rhythm?"},
                {"question": "What should stay exactly the same because it clearly supported control and clarity?"},
            ]
        return [
            {"question": "What changed first when the session stopped feeling smooth: pace, switching, uncertainty, or fatigue?"},
            {"question": f"Inside {time_window}, was the main issue understanding pressure or regulation pressure?"},
            {"question": "What one variable do you want to control more tightly in the next session so the pattern becomes easier to interpret?"},
        ]

    def _build_experiments(self, signature, context, next_goal):
        key = signature["key"]
        goal_suffix = f" while aiming for {next_goal}" if next_goal else ""

        if key == "productive_challenge":
            return [
                self._experiment(
                    "Slow replay, same target",
                    "Replay the flagged segment once at a slower pace, but keep exactly one source in view instead of searching for help elsewhere.",
                    "Load rises later than before and the difficult step becomes easier to name.",
                ),
                self._experiment(
                    "Confusion timestamp",
                    "The moment effort jumps, mark the exact sentence, diagram, or reasoning step rather than only noting that it felt hard.",
                    "You can point to one concrete trigger instead of describing the whole segment as confusing.",
                ),
                self._experiment(
                    "One-minute rebuild",
                    f"After the replay, spend one minute rebuilding the logic in your own words{goal_suffix}, without opening new materials.",
                    "The concept gap narrows without a big switching spike.",
                ),
            ]
        if key == "switching_drift":
            return [
                self._experiment(
                    "Two-minute source lock",
                    "Choose one source before starting and do not switch windows, pages, or note formats for the first two minutes.",
                    "Switching pressure falls and the session reaches a steadier opening rhythm.",
                ),
                self._experiment(
                    "Switch budget",
                    "Allow yourself only one intentional switch inside the replay block, and decide in advance why that switch is allowed.",
                    "Every switch becomes purposeful instead of reactive.",
                ),
                self._experiment(
                    "Pre-decide the action path",
                    "Before replaying, decide whether this block is for watching, reading, or note-taking instead of blending them on the fly.",
                    "The task mode feels clearer and the guidance stabilizes faster.",
                ),
            ]
        if key == "fatigue_drag":
            return [
                self._experiment(
                    "Break before rescue",
                    "Take a short reset before replaying the flagged segment instead of trying to recover inside the same tired state.",
                    "The second attempt starts with lower fatigue and cleaner alignment.",
                ),
                self._experiment(
                    "Short replay block",
                    "Replay only the highest-value slice of the difficult segment instead of the full long block.",
                    "Clarity improves without the session becoming another endurance test.",
                ),
                self._experiment(
                    "Earlier stop rule",
                    "Define one clear fatigue boundary for the next session, such as posture heaviness or dull rereading, and stop before it deepens.",
                    "You exit earlier but preserve a better-quality review state.",
                ),
            ]
        if key == "signal_check":
            return [
                self._experiment(
                    "Clean calibration minute",
                    "Use the first minute only to stabilize posture, scene, and task mode before doing real study work.",
                    "Low-confidence drops become rarer in the opening phase.",
                ),
                self._experiment(
                    "Stable surface setup",
                    "Keep the book, screen, or page position more constant so the scene lock stays credible.",
                    "The system spends less time in signal-check behavior.",
                ),
                self._experiment(
                    "Single-mode warm start",
                    "Do not mix reading, note-taking, and review during warm-up. Start with one mode and switch later only if needed.",
                    "The next session becomes easier to interpret with higher confidence.",
                ),
            ]
        if key == "steady_control":
            return [
                self._experiment(
                    "Promote one stable block",
                    "Take the steadiest part of this session and turn it into a deliberate stretch block next time.",
                    "You keep control while increasing challenge slightly.",
                ),
                self._experiment(
                    "Thirty-second recap",
                    "After a stable block ends, spend thirty seconds naming what helped the rhythm stay clean.",
                    "Useful study behaviors become easier to repeat on purpose.",
                ),
                self._experiment(
                    "Stretch without clutter",
                    f"Raise difficulty slightly{goal_suffix}, but keep the setup and source strategy unchanged.",
                    "You can test growth without losing the current stability signature.",
                ),
            ]
        return [
            self._experiment(
                "One-variable retry",
                "Keep the same material but change only one factor next time: pace, switching, or break timing.",
                "The next session pattern becomes easier to diagnose.",
            ),
            self._experiment(
                "Replay the strongest segment first",
                "Start the next review with the most difficult window instead of doing a full passive recap.",
                "You learn faster which regulation change actually matters.",
            ),
            self._experiment(
                "End with a boundary note",
                "Write one sentence after the session about where regulation started to slip and what boundary should be held next time.",
                "The next attempt begins with a sharper self-coaching rule.",
            ),
        ]

    def _build_evidence_cards(self, signature, context):
        summary = context.get("summary", {})
        top_event = context.get("highlight_event") or {}
        peak_load = context.get("anchors", {}).get("peak_load", {})
        task_modes = context.get("distributions", {}).get("task_modes", [])
        mode_label = task_modes[0]["label"] if task_modes else str(summary.get("primary_task_mode", "reading")).replace("-", " ").title()
        top_segment = "Clear" if not top_event else f"D{top_event.get('event_id', '?')}"

        return [
            {"label": "Signature", "value": signature["label"], "detail": signature["detail"], "tone": signature["tone"]},
            {
                "label": "Primary mode",
                "value": mode_label,
                "detail": f"{summary.get('duration_label', '00:00')} session, {summary.get('samples', 0)} samples.",
                "tone": "cool",
            },
            {
                "label": "Top segment",
                "value": top_segment,
                "detail": top_event.get("time_window", "No sustained difficulty event"),
                "tone": "high" if top_event else "good",
            },
            {
                "label": "Load / fatigue",
                "value": f"{int(round(self._safe_float(summary.get('avg_load', 0))))} / {int(round(self._safe_float(summary.get('avg_fatigue', 0))))}",
                "detail": "Average pressure and fatigue across the session.",
                "tone": "warn",
            },
            {
                "label": "Aligned effort",
                "value": f"{int(round(self._safe_float(summary.get('productive_struggle_ratio', 0))))}%",
                "detail": "How often the session resembled productive struggle.",
                "tone": "cool",
            },
            {
                "label": "Off-task risk",
                "value": f"{int(round(self._safe_float(summary.get('off_task_ratio', 0))))}%",
                "detail": peak_load.get("guidance") or "How often switching or drift pressure dominated.",
                "tone": "high",
            },
        ]

    def _build_coach_memo(self, signature, context, coach_summary, learner_note, next_goal):
        summary = context.get("summary", {})
        top_event = context.get("highlight_event") or {}
        note_line = f" Learner note: {learner_note}." if learner_note else ""
        goal_line = f" Next goal: {next_goal}." if next_goal else ""
        event_line = (
            f" The strongest replay target is D{top_event.get('event_id', '?')} at {top_event.get('time_window', '--')}."
            if top_event
            else " No sustained difficulty event was captured, so the coach is reading broader rhythm patterns."
        )
        return (
            f"{coach_summary['headline']} "
            f"Average load was {int(round(self._safe_float(summary.get('avg_load', 0))))} with "
            f"{int(round(self._safe_float(summary.get('avg_fatigue', 0))))} fatigue and "
            f"{int(round(self._safe_float(summary.get('low_confidence_ratio', 0))))}% low-confidence exposure."
            f"{event_line} The next coaching boundary is: {signature['next_boundary']}.{note_line}{goal_line}"
        ).strip()

    def _maybe_generate_model_layer(
        self,
        context,
        payload,
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
                note="Heuristic mode was selected explicitly, so no external model provider was used.",
                model_override=model_override,
            )

        if not self._provider_is_configured(effective_provider):
            return None, self._generation_meta(
                mode="heuristic",
                requested_provider=requested_provider,
                resolved_provider="heuristic",
                configured_provider=configured_provider,
                provider_available=False,
                note=f"{self._provider_label(effective_provider)} is not configured, so the coach stayed in heuristic mode.",
                model_override=model_override,
            )

        request_bundle = self._build_generation_request(context, payload)
        if effective_provider == "ollama":
            llm_payload, note = self._generate_with_ollama(request_bundle, model_override=model_override)
            model_name = self._ollama_model(model_override=model_override)
        elif effective_provider == "remote":
            llm_payload, note = self._generate_with_remote(request_bundle)
            model_name = os.getenv("REFLECTION_REMOTE_LABEL", "remote-reflection-service").strip() or "remote-reflection-service"
        elif effective_provider == "openai":
            llm_payload, note = self._generate_with_openai(request_bundle)
            model_name = self._openai_model()
        else:
            llm_payload, note = None, f"Unknown provider `{effective_provider}`, so the coach stayed in heuristic mode."
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
                    "options": {
                        "temperature": 0.2,
                    },
                },
                timeout=self._provider_timeout("ollama", default=120),
            )
            response.raise_for_status()
            raw = response.json()
            content = raw.get("message", {}).get("content", "")
            parsed = self._parse_model_json(content)
            if not parsed:
                return None, f"Ollama returned no valid JSON for `{model}`, so the coach stayed in heuristic mode."
            return parsed, f"Session wording refined locally with Ollama `{model}`."
        except Exception as exc:
            return None, f"Ollama refinement failed ({exc}), so the coach stayed in heuristic mode."

    def _generate_with_remote(self, request_bundle):
        url = os.getenv("REFLECTION_REMOTE_URL", "").strip()
        token = os.getenv("REFLECTION_REMOTE_AUTH_TOKEN", "").strip()
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
                    "learner_note": request_bundle["learner_note"],
                    "next_goal": request_bundle["next_goal"],
                },
                timeout=self._provider_timeout("remote", default=45),
            )
            response.raise_for_status()
            raw = response.json()
            parsed = self._parse_remote_payload(raw)
            if not parsed:
                return None, "The remote reflection provider returned no valid JSON, so the coach stayed in heuristic mode."
            return parsed, "Session wording refined through the configured remote reflection provider."
        except Exception as exc:
            return None, f"Remote reflection provider failed ({exc}), so the coach stayed in heuristic mode."

    def _generate_with_openai(self, request_bundle):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = self._openai_model()

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
            "text": {
                "format": {
                    "type": "json_object",
                }
            },
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
                return None, f"OpenAI returned no valid JSON for `{model}`, so the coach stayed in heuristic mode."
            return parsed, f"Session wording refined with OpenAI `{model}`."
        except Exception as exc:
            return None, f"OpenAI refinement failed ({exc}), so the coach stayed in heuristic mode."

    def _build_generation_request(self, context, payload):
        schema = self._target_schema()
        instruction = (
            "You are a learning reflection coach for a smart-glasses education project. "
            "Interpret learning-state evidence only. Do not explain subject content, do not act as an AI tutor, "
            "do not give writing guidance, language tutoring, note-taking workflows, or open-ended chat. "
            "Your job is to coach self-reflection, regulation, replay strategy, and next-session experiments. "
            "Preserve the evidence-based structure already present in the draft. Return strict JSON only."
        )
        prompt_payload = {
            "context": {
                "summary": context.get("summary", {}),
                "highlight_event": context.get("highlight_event"),
                "distributions": context.get("distributions", {}),
                "anchors": context.get("anchors", {}),
            },
            "draft": {
                "signature": payload.get("signature", {}),
                "coach_summary": payload.get("coach_summary", {}),
                "reflection_questions": payload.get("reflection_questions", []),
                "next_session_experiments": payload.get("next_session_experiments", []),
                "coach_memo": payload.get("coach_memo", ""),
            },
            "learner_note": payload.get("learner_note", ""),
            "next_goal": payload.get("next_goal", ""),
            "schema": schema,
        }
        return {
            "instruction": instruction,
            "prompt": json.dumps(prompt_payload, ensure_ascii=False),
            "schema": schema,
            "context": prompt_payload["context"],
            "draft": prompt_payload["draft"],
            "learner_note": prompt_payload["learner_note"],
            "next_goal": prompt_payload["next_goal"],
        }

    def _target_schema(self):
        return {
            "headline": "string",
            "overview": "string",
            "why_it_matters": "string",
            "next_boundary": "string",
            "coach_memo": "string",
            "reflection_questions": [{"question": "string"}],
            "next_session_experiments": [{"title": "string", "detail": "string", "success_marker": "string"}],
        }

    def _parse_remote_payload(self, payload):
        if isinstance(payload, dict):
            normalized = self._extract_refinement_patch(payload)
            if normalized:
                return normalized
            for key in ("result", "output", "data"):
                candidate = payload.get(key)
                if isinstance(candidate, dict):
                    normalized = self._extract_refinement_patch(candidate)
                    if normalized:
                        return normalized
                if isinstance(candidate, str):
                    parsed = self._parse_model_json(candidate)
                    if parsed:
                        return parsed
        return None

    def _parse_model_json(self, text):
        if isinstance(text, dict):
            return self._extract_refinement_patch(text)
        if not isinstance(text, str) or not text.strip():
            return None

        candidate = text.strip()
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)

        try:
            parsed = json.loads(candidate)
            return self._extract_refinement_patch(parsed)
        except Exception:
            return None

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

    def _valid_refinement_payload(self, payload):
        return bool(self._extract_refinement_patch(payload))

    def _extract_refinement_patch(self, payload):
        if not isinstance(payload, dict):
            return None

        candidates = []
        candidates.append(payload)

        coach_summary = payload.get("coach_summary")
        if isinstance(coach_summary, dict):
            candidates.append({
                "headline": coach_summary.get("headline"),
                "overview": coach_summary.get("overview"),
                "why_it_matters": coach_summary.get("why_it_matters"),
                "next_boundary": coach_summary.get("next_boundary"),
                "coach_memo": payload.get("coach_memo"),
                "reflection_questions": payload.get("reflection_questions"),
                "next_session_experiments": payload.get("next_session_experiments"),
            })

        for key in ("json", "schema", "result", "output", "data"):
            value = payload.get(key)
            if isinstance(value, dict):
                candidates.append(value)

        for candidate in candidates:
            normalized = self._normalize_refinement_candidate(candidate)
            if normalized:
                return normalized

        for value in payload.values():
            if isinstance(value, dict):
                normalized = self._extract_refinement_patch(value)
                if normalized:
                    return normalized

        return None

    def _normalize_refinement_candidate(self, candidate):
        if not isinstance(candidate, dict):
            return None

        questions = self._coerce_question_list(candidate.get("reflection_questions"))
        experiments = self._coerce_experiment_list(candidate.get("next_session_experiments"))

        normalized = {}
        for key, limit in (
            ("headline", 500),
            ("overview", 2400),
            ("why_it_matters", 2400),
            ("next_boundary", 1200),
            ("coach_memo", 3200),
        ):
            value = self._clean_text(candidate.get(key, ""), max_length=limit)
            if value:
                normalized[key] = value

        if len(questions) >= 3:
            normalized["reflection_questions"] = questions[:3]
        if len(experiments) >= 3:
            normalized["next_session_experiments"] = experiments[:3]

        if not normalized:
            return None
        return normalized

    def _coerce_question_list(self, items):
        if not isinstance(items, list):
            return []

        normalized = []
        for item in items:
            if isinstance(item, dict) and item.get("question"):
                question = self._clean_text(item.get("question", ""), max_length=500)
                if question:
                    normalized.append({"question": question})
            elif isinstance(item, str):
                question = self._clean_text(item, max_length=500)
                if question:
                    normalized.append({"question": question})
        return normalized[:3]

    def _coerce_experiment_list(self, items):
        if not isinstance(items, list):
            return []

        normalized = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title", ""), max_length=240)
            detail = self._clean_text(item.get("detail", ""), max_length=1200)
            success_marker = self._clean_text(item.get("success_marker", ""), max_length=800)
            if title and detail and success_marker:
                normalized.append({
                    "title": title,
                    "detail": detail,
                    "success_marker": success_marker,
                })
        return normalized[:3]

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
        provider = self._normalize_provider(os.getenv("LLM_PROVIDER", "ollama"))
        if provider == "auto":
            return "ollama"
        return provider

    def _provider_options(self):
        return [
            {"value": "auto", "label": "Configured Default"},
            {"value": "heuristic", "label": "Heuristic Only"},
            {"value": "ollama", "label": "Ollama Local"},
            {"value": "remote", "label": "Remote API"},
            {"value": "openai", "label": "OpenAI"},
        ]

    def _provider_is_configured(self, provider):
        provider = self._normalize_provider(provider)
        if provider in {"auto", "heuristic"}:
            return True
        if provider == "ollama":
            return bool(self._ollama_model()) and bool(os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api").strip())
        if provider == "remote":
            return bool(os.getenv("REFLECTION_REMOTE_URL", "").strip())
        if provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY", "").strip())
        return False

    def _any_model_provider_configured(self):
        return any(self._provider_is_configured(provider) for provider in self.MODEL_PROVIDERS)

    def _default_generation_note(self, requested_provider, configured_provider, effective_provider):
        if effective_provider == "heuristic":
            return "Heuristic mode is active. Turn on model polish only if you want a provider-backed wording pass."
        return (
            f"Heuristic mode is active. The configured default provider is {self._provider_label(configured_provider)}. "
            f"If that provider is unavailable at runtime, the coach will still fall back safely."
        )

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
        provider_label = self._provider_label(resolved_provider)
        configured_label = self._provider_label(configured_provider)
        model_name = model or self._provider_model_name(resolved_provider, model_override=model_override)
        return {
            "mode": mode,
            "used_llm": mode != "heuristic",
            "llm_available": self._any_model_provider_configured(),
            "requested_provider": requested_provider,
            "resolved_provider": resolved_provider,
            "configured_provider": configured_provider,
            "provider_available": bool(provider_available),
            "provider_label": provider_label,
            "configured_label": configured_label,
            "model": model_name,
            "configured_model": self._provider_model_name(configured_provider),
            "model_override": model_override,
            "note": note,
        }

    def _provider_label(self, provider):
        mapping = {
            "auto": "Configured Default",
            "heuristic": "Heuristic",
            "ollama": "Ollama Local",
            "remote": "Remote API",
            "openai": "OpenAI",
        }
        return mapping.get(str(provider or "").strip().lower(), "Heuristic")

    def _provider_model_name(self, provider, model_override=""):
        provider = self._normalize_provider(provider)
        if provider == "ollama":
            return self._ollama_model(model_override=model_override)
        if provider == "remote":
            return os.getenv("REFLECTION_REMOTE_LABEL", "remote-reflection-service").strip() or "remote-reflection-service"
        if provider == "openai":
            return self._openai_model()
        return ""

    def _ollama_model(self, model_override=""):
        cleaned_override = self._clean_model_name(model_override)
        if cleaned_override:
            return cleaned_override
        return os.getenv("OLLAMA_MODEL", "qwen3:4b").strip() or "qwen3:4b"

    def _provider_runtime_available(self, provider, ollama_status=None):
        provider = self._normalize_provider(provider)
        if provider in {"auto", "heuristic"}:
            return True
        if provider == "ollama":
            if not self._provider_is_configured("ollama"):
                return False
            if ollama_status is None:
                ollama_status = self._ollama_status()
            return bool(ollama_status.get("reachable"))
        return self._provider_is_configured(provider)

    def _model_options(self, configured_provider, supports_model_override, model_override="", ollama_status=None):
        if not supports_model_override:
            return [{"value": "", "label": "Use configured default"}]

        configured_model = self._provider_model_name(configured_provider)
        options = [{"value": "", "label": f"Use configured default ({configured_model or 'none'})"}]
        seen = {""}
        available_models = (ollama_status or {}).get("available_models", [])
        for item in available_models:
            value = str(item.get("name", "")).strip()
            if not value or value in seen:
                continue
            label_bits = [value]
            parameter_size = str(item.get("parameter_size", "")).strip()
            size_label = str(item.get("size_label", "")).strip()
            if parameter_size:
                label_bits.append(parameter_size)
            if size_label:
                label_bits.append(size_label)
            options.append({"value": value, "label": " | ".join(label_bits)})
            seen.add(value)

        cleaned_override = self._clean_model_name(model_override)
        if cleaned_override and cleaned_override not in seen:
            options.append({"value": cleaned_override, "label": f"{cleaned_override} | typed override"})
        return options

    def _ollama_status(self):
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api").rstrip("/")
        status = {
            "configured": self._provider_is_configured("ollama"),
            "reachable": False,
            "base_url": base_url,
            "configured_model": self._ollama_model(),
            "version": "",
            "available_models": [],
            "note": "",
        }
        if not base_url:
            status["note"] = "OLLAMA_BASE_URL is empty, so local model status could not be checked."
            return status

        timeout_seconds = min(self._provider_timeout("ollama", default=120), 8)
        try:
            version_response = requests.get(f"{base_url}/version", timeout=timeout_seconds)
            version_response.raise_for_status()
            status["version"] = str(version_response.json().get("version", "")).strip()
        except Exception:
            status["version"] = ""

        try:
            tags_response = requests.get(f"{base_url}/tags", timeout=timeout_seconds)
            tags_response.raise_for_status()
            raw = tags_response.json()
            models = []
            for item in raw.get("models", []) or []:
                name = str(item.get("name", "")).strip()
                if not name:
                    continue
                size_value = self._safe_float(item.get("size", 0))
                details = item.get("details", {}) or {}
                models.append({
                    "name": name,
                    "size_label": self._format_bytes(size_value),
                    "parameter_size": str(details.get("parameter_size", "")).strip(),
                    "family": str(details.get("family", "")).strip(),
                })
            status["reachable"] = True
            status["available_models"] = models
            status["note"] = (
                f"Local Ollama is reachable with {len(models)} installed model(s)."
                if models
                else "Local Ollama is reachable, but no installed models were reported."
            )
            return status
        except Exception as exc:
            status["note"] = f"Could not reach local Ollama ({exc})."
            return status

    def _format_bytes(self, value):
        size = self._safe_float(value)
        if size <= 0:
            return ""
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.1f} {units[unit_index]}"

    def _provider_timeout(self, provider, default=45):
        specific_key = f"{str(provider or '').strip().upper()}_TIMEOUT_SECONDS"
        for key in (specific_key, "REFLECTION_PROVIDER_TIMEOUT_SECONDS"):
            raw = os.getenv(key, "").strip()
            if raw:
                try:
                    value = int(float(raw))
                    if value > 0:
                        return value
                except Exception:
                    pass
        return default

    def _openai_model(self):
        return os.getenv("OPENAI_REFLECTION_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"

    def _valid_question_list(self, items):
        return isinstance(items, list) and len(items) >= 3 and all(isinstance(item, dict) and item.get("question") for item in items[:3])

    def _valid_experiment_list(self, items):
        return (
            isinstance(items, list)
            and len(items) >= 3
            and all(
                isinstance(item, dict) and item.get("title") and item.get("detail") and item.get("success_marker")
                for item in items[:3]
            )
        )

    def _experiment(self, title, detail, success_marker):
        return {
            "title": title,
            "detail": detail,
            "success_marker": success_marker,
        }

    def _clean_text(self, text, max_length=500):
        clean = " ".join(str(text or "").strip().split())
        if len(clean) <= max_length:
            return clean
        return clean[: max_length - 1].rstrip() + "..."

    def _clean_model_name(self, text, max_length=160):
        clean = " ".join(str(text or "").strip().split())
        if len(clean) <= max_length:
            return clean
        return clean[:max_length].strip()

    def _safe_float(self, value):
        try:
            return float(value)
        except Exception:
            return 0.0

    def _safe_int(self, value, default=0):
        try:
            return int(float(value))
        except Exception:
            return default
