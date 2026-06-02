from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.demo_storyboard import DEFAULT_FEATURES_PATH, build_demo_storyboard


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALIDATION_METRICS_PATH = ROOT / "exports" / "state_validation_metrics.json"


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _title_case(value: Any) -> str:
    return " ".join(
        part.capitalize()
        for part in str(value or "").replace("-", "_").split("_")
        if part
    )


class PresentationAssistant:
    def __init__(self, logger, reflection_coach, features_path: str | Path | None = None, validation_metrics_path: str | Path | None = None):
        self.logger = logger
        self.reflection_coach = reflection_coach
        self.features_path = Path(features_path) if features_path else DEFAULT_FEATURES_PATH
        self.validation_metrics_path = Path(validation_metrics_path) if validation_metrics_path else DEFAULT_VALIDATION_METRICS_PATH

    def build_summary_payload(self, dataset: str = "demo", session_id: str | None = None) -> dict[str, Any]:
        dataset_name = str(dataset or "demo").strip().lower() or "demo"
        review_payload = self.logger.build_review_payload(session_id=session_id, dataset=dataset_name)
        storyboard_payload = build_demo_storyboard(
            logger=self.logger,
            reflection_coach=self.reflection_coach,
            dataset=dataset_name,
            session_id=review_payload.get("session_id") or session_id,
            features_path=self.features_path,
        )
        reflection_payload = self.reflection_coach.build_review_summary_payload(
            review_payload=review_payload,
            difficulty_events=review_payload.get("events", []),
            validation_summary={"status": "ok", "features_available": False},
            session_id=review_payload.get("session_id") or session_id,
            dataset=dataset_name,
            event_id=(review_payload.get("highlight_event") or {}).get("event_id"),
        )
        validation_summary = self._load_validation_summary()

        return {
            "status": "ok",
            "empty": bool(review_payload.get("empty", False)) and bool(storyboard_payload.get("empty", False)),
            "dataset": dataset_name,
            "session_id": str(review_payload.get("session_id", session_id or "")).strip(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "module_boundary": (
                "Presentation Assistant is a template-based layer for project demos and defense preparation. "
                "It is not part of the learning-state judgment main loop."
            ),
            "project_positioning": self._project_positioning(review_payload, reflection_payload, validation_summary),
            "module_explanations": self._module_explanations(validation_summary),
            "demo_script_3min": self._demo_script_3min(storyboard_payload, review_payload, reflection_payload, validation_summary),
            "demo_script_5min": self._demo_script_5min(storyboard_payload, review_payload, reflection_payload, validation_summary),
            "metric_explanations": self._metric_explanations(review_payload, validation_summary),
            "defense_qa": self._defense_qa(validation_summary),
            "limitations": self._limitations(validation_summary),
            "storyboard_summary": {
                "title": storyboard_payload.get("title"),
                "story_summary": storyboard_payload.get("story_summary"),
                "stages": [
                    {
                        "stage_key": stage.get("stage_key"),
                        "stage_title": stage.get("stage_title"),
                        "time_range": stage.get("time_range"),
                    }
                    for stage in storyboard_payload.get("stages", [])
                ],
            },
            "reflection_summary": {
                "session_summary": reflection_payload.get("session_summary"),
                "encouragement": reflection_payload.get("encouragement"),
                "reflection_questions": reflection_payload.get("reflection_questions", []),
                "next_actions": reflection_payload.get("next_actions", []),
            },
            "validation_summary": validation_summary,
        }

    def _load_validation_summary(self) -> dict[str, Any]:
        path = self.validation_metrics_path
        if not path.exists() or path.stat().st_size <= 0:
            return {
                "available": False,
                "metrics_path": "exports/state_validation_metrics.json",
                "note": "Validation metrics are optional and were not found for this presentation run.",
            }
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "available": False,
                "metrics_path": "exports/state_validation_metrics.json",
                "note": "Validation metrics exist but could not be parsed, so the presentation assistant stayed in graceful fallback mode.",
            }
        rule = payload.get("rule_baseline", {}) if isinstance(payload, dict) else {}
        correlations = payload.get("correlations", {}) if isinstance(payload, dict) else {}
        sklearn = payload.get("sklearn_baseline", {}) if isinstance(payload, dict) else {}
        return {
            "available": True,
            "metrics_path": "exports/state_validation_metrics.json",
            "generated_at": payload.get("generated_at"),
            "feature_rows": payload.get("feature_rows"),
            "labeled_window_rows": payload.get("labeled_window_rows"),
            "missing_fields": payload.get("missing_fields", []),
            "rule_accuracy": rule.get("accuracy"),
            "rule_macro_f1": rule.get("macro_f1"),
            "rule_label_count": rule.get("label_count"),
            "sklearn_status": sklearn.get("status"),
            "sklearn_reason": sklearn.get("reason"),
            "predicted_load_self_report_correlation": correlations.get("correlation_between_predicted_load_and_self_report_load"),
            "focus_attention_correlation": correlations.get("correlation_between_focus_score_and_self_report_attention"),
        }

    def _project_positioning(self, review_payload: dict[str, Any], reflection_payload: dict[str, Any], validation_summary: dict[str, Any]) -> dict[str, Any]:
        summary = review_payload.get("summary", {}) if isinstance(review_payload, dict) else {}
        duration_label = str(summary.get("duration_label", "00:00")).strip() or "00:00"
        mode = _title_case(summary.get("primary_task_mode", "reading") or "reading")
        validation_line = self._validation_line(validation_summary)
        return {
            "headline": "Learning State Guardian is a conservative study-process coaching system, not a precise attention detector.",
            "one_liner": (
                "The project combines posture, behavior, first-person scene cues, difficulty marking, review replay, "
                "reflection coaching, and optional validation into one learning-state proxy workflow."
            ),
            "problem_statement": (
                "Learners often notice that a study block felt ineffective, but they cannot easily replay when regulation pressure started, "
                "whether the issue looked more like overload or drift, or how to recover in the next attempt."
            ),
            "project_claim": (
                f"In the current {mode.lower()} demo flow, the system narrates a {duration_label} study session as a sequence of observable learning-state proxies, "
                "then turns those proxies into review and reflection support."
            ),
            "guardrail": (
                "All outputs should be presented as proxy-based estimates derived from observable signals. "
                "They should not be described as mind reading or precise attention measurement."
            ),
            "validation_status": validation_line,
            "reflection_anchor": str(reflection_payload.get("session_summary", "")).strip(),
        }

    def _module_explanations(self, validation_summary: dict[str, Any]) -> list[dict[str, Any]]:
        validation_note = self._validation_line(validation_summary)
        return [
            {
                "module": "PostureEngine",
                "purpose": "Produces behavior-facing proxies such as focus score, cognitive load proxy, behavioral alignment, fatigue risk, uncertainty, and switching pressure from time-varying session signals.",
                "boundary": "These are observable-behavior proxies, not direct measurements of hidden attention state.",
            },
            {
                "module": "RokidFrameAdapter",
                "purpose": "Adds first-person scene proxies such as scene content, text density, scene stability, study-surface quality, and scene lock.",
                "boundary": "Scene features help describe context quality and task holding, but they do not guarantee what the learner is actually thinking about.",
            },
            {
                "module": "FocusSessionEngine",
                "purpose": "Turns the live proxy stream into real-time focus and recovery guidance so the HUD can react before a session is fully lost.",
                "boundary": "The guidance is a coaching layer built on proxy changes, not a content tutor or a diagnostic system.",
            },
            {
                "module": "DifficultyEventMarker",
                "purpose": "Captures sustained medium/high-difficulty windows so the learner can replay the most important segment instead of reviewing the full session blindly.",
                "boundary": "A difficulty event marks a proxy-identified strain segment, not proof of exact comprehension failure.",
            },
            {
                "module": "Review Summary + Heatmap",
                "purpose": "Converts raw session traces into a timeline, event list, heatmap asset, and next-action suggestions for post-session analysis.",
                "boundary": "This layer explains where pressure appeared in the session; it does not replace instruction or assessment.",
            },
            {
                "module": "Reflection Coach",
                "purpose": "Generates conservative post-session reflection questions, key moments, and next actions from review cues and learning-state proxies.",
                "boundary": "Reflection Coach supports self-regulation and replay planning. It is not a psychological evaluator.",
            },
            {
                "module": "Learning-State Validation Layer",
                "purpose": "Adds sliding-window features, rule-based classification, label templates, and optional baseline metrics such as accuracy and macro F1.",
                "boundary": validation_note,
            },
            {
                "module": "Demo Storyboard",
                "purpose": "Organizes the same system evidence into a presentation-friendly five-stage narrative from stable focus to recovery.",
                "boundary": "The storyboard is a narrative aid for demos and defense, not a new inference engine.",
            },
            {
                "module": "Presentation Assistant",
                "purpose": "Packages the current project state into project positioning, demo scripts, metric explanations, and defense Q&A.",
                "boundary": "This assistant is a template-based presentation layer and does not participate in the learning-state main loop.",
            },
        ]

    def _demo_script_3min(
        self,
        storyboard_payload: dict[str, Any],
        review_payload: dict[str, Any],
        reflection_payload: dict[str, Any],
        validation_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        stage_lines = self._story_stage_lines(storyboard_payload)
        return [
            {
                "section": "Opening Positioning",
                "target_seconds": 25,
                "talk_track": (
                    "This project is not trying to read hidden attention directly. "
                    "It builds a conservative learning-state proxy from posture, scene context, and study behavior, then turns that proxy into coaching and review support."
                ),
            },
            {
                "section": "Core Architecture",
                "target_seconds": 35,
                "talk_track": (
                    "The live loop combines PostureEngine, RokidFrameAdapter, FocusSessionEngine, and DifficultyEventMarker. "
                    "Those modules feed the HUD and also create the evidence needed for review, reflection, and validation."
                ),
            },
            {
                "section": "Demo Story Arc",
                "target_seconds": 70,
                "talk_track": (
                    "In the demo storyboard, the session first looks stable, then load starts rising, then we isolate a short challenge window that still looks replayable, "
                    "then off-task risk dominates, and finally the system shows recovery. "
                    f"{stage_lines}"
                ),
            },
            {
                "section": "Review And Reflection",
                "target_seconds": 35,
                "talk_track": (
                    "After the live demo, the review page highlights the strongest difficulty event, and Reflection Coach turns that event into reflection questions and next actions. "
                    f"The current reflection summary says: {str(reflection_payload.get('session_summary', '')).strip() or 'the session can be replayed as a proxy-based reflection case.'}"
                ),
            },
            {
                "section": "Validation And Guardrails",
                "target_seconds": 25,
                "talk_track": (
                    f"{self._validation_line(validation_summary)} "
                    "The main guardrail is that every output is framed as a learning-state proxy estimate rather than precise attention detection."
                ),
            },
        ]

    def _demo_script_5min(
        self,
        storyboard_payload: dict[str, Any],
        review_payload: dict[str, Any],
        reflection_payload: dict[str, Any],
        validation_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        summary = review_payload.get("summary", {}) if isinstance(review_payload, dict) else {}
        stage_lines = self._story_stage_lines(storyboard_payload)
        return [
            {
                "section": "Problem And Framing",
                "target_seconds": 35,
                "talk_track": (
                    "The problem is not only whether a learner looks focused in one instant. "
                    "The harder question is how to replay a session, identify where regulation pressure started, and turn that into a better next attempt."
                ),
            },
            {
                "section": "Why Proxy-Based Instead Of Attention Detection",
                "target_seconds": 35,
                "talk_track": (
                    "We use the phrase learning-state proxy because the system estimates study-relevant pressure from observable behavior and scene cues. "
                    "That is more honest and easier to validate than claiming direct attention detection."
                ),
            },
            {
                "section": "System Pipeline",
                "target_seconds": 50,
                "talk_track": (
                    "The pipeline starts with posture and scene features, adds session guidance, flags difficulty events, then exposes the result in the HUD, review page, Reflection Coach, and demo storyboard. "
                    "This keeps live support and post-session explanation in the same project structure."
                ),
            },
            {
                "section": "Walk Through The Demo Storyboard",
                "target_seconds": 90,
                "talk_track": (
                    f"The current session lasted {summary.get('duration_label', '00:00')} and the storyboard explains it in five stages. {stage_lines} "
                    "That sequence is useful in a defense because it shows the system can explain both breakdown and recovery."
                ),
            },
            {
                "section": "Review, Reflection, And Optional Validation",
                "target_seconds": 55,
                "talk_track": (
                    "The review layer highlights the strongest replay target, Reflection Coach converts it into questions and next actions, and the optional validation layer adds windowed features plus baseline metrics when labels exist. "
                    f"{self._validation_line(validation_summary)}"
                ),
            },
            {
                "section": "Limitations And Honest Scope",
                "target_seconds": 35,
                "talk_track": (
                    "The system does not claim precise attention detection, it depends on proxy quality and labeling quality, "
                    "and it still needs richer real-world data such as gaze, blink, fixation, and stronger outcome measures if the project wants deeper validation."
                ),
            },
        ]

    def _metric_explanations(self, review_payload: dict[str, Any], validation_summary: dict[str, Any]) -> list[dict[str, Any]]:
        summary = review_payload.get("summary", {}) if isinstance(review_payload, dict) else {}
        return [
            {
                "metric": "Focus Score",
                "explanation": "A fast proxy of how settled the study behavior currently looks. It should be explained as a behavior-facing score, not as direct attention measurement.",
                "current_context": f"Session average focus-related stability is reflected indirectly through review and storyboard stages, not as a clinical score.",
            },
            {
                "metric": "Cognitive Load Proxy",
                "explanation": "A session-level estimate of how effortful or pressured the current block looks based on observable signals.",
                "current_context": f"Current average load in the selected session is {summary.get('avg_load', '--')}.",
            },
            {
                "metric": "Behavioral Alignment",
                "explanation": "How consistently the learner appears aligned with one study target instead of fragmenting across actions or sources.",
                "current_context": f"Current average alignment is {summary.get('avg_alignment', '--')}.",
            },
            {
                "metric": "Switching Index",
                "explanation": "A proxy for task fragmentation and reactive source switching.",
                "current_context": f"Current session-wide switching average is {summary.get('avg_switching', '--')}.",
            },
            {
                "metric": "Fatigue Risk",
                "explanation": "A recovery-oriented proxy that warns when persistence may be degrading into lower-quality effort.",
                "current_context": f"Current average fatigue proxy is {summary.get('avg_fatigue', '--')}.",
            },
            {
                "metric": "Uncertainty And Confidence",
                "explanation": "These signals describe how much trust the system should place in the current proxy reading. High uncertainty should reduce claims, not increase them.",
                "current_context": "This is the main guardrail against overclaiming from noisy scenes or unstable session conditions.",
            },
            {
                "metric": "Difficulty Event",
                "explanation": "A sustained medium/high-pressure segment worth replaying first during review.",
                "current_context": f"The current review summary reports {summary.get('difficulty_count', 0)} flagged difficulty events.",
            },
            {
                "metric": "Validation Metrics",
                "explanation": "Accuracy, macro F1, confusion matrix, and self-report correlations belong to the optional validation layer, not the real-time coaching loop itself.",
                "current_context": self._validation_line(validation_summary),
            },
        ]

    def _defense_qa(self, validation_summary: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "question": "What is the core contribution of this project?",
                "answer": "The core contribution is not a single score. It is the full workflow: live proxy estimation, difficulty marking, post-session review, reflection support, and optional validation in one integrated study-process system.",
            },
            {
                "question": "Why do you use the phrase learning-state proxy instead of attention detection?",
                "answer": "Because the system estimates study-relevant patterns from observable behavior and scene cues. That is more honest, easier to defend, and easier to validate than claiming direct access to hidden attention state.",
            },
            {
                "question": "What is the difference between load_rising and off_task_risk?",
                "answer": "Load rising means the session still looks engaged but pressure is increasing. Off-task risk means regulation or task-holding is deteriorating enough that switching, drift, or overload dominate the segment.",
            },
            {
                "question": "Why keep DifficultyEventMarker if you already have review and reflection layers?",
                "answer": "DifficultyEventMarker gives the review stack a concrete replay target. Without it, the learner still has to search the full session to find where the important strain began.",
            },
            {
                "question": "How do you validate the system if you do not claim precise attention detection?",
                "answer": f"We validate the proxy layer conservatively with windowed features, manual labels, self-report fields, and baseline metrics. {self._validation_line(validation_summary)}",
            },
            {
                "question": "What happens when the scene quality is poor or the signal is unstable?",
                "answer": "The system should lower confidence, surface uncertainty, and fall back to weaker claims. That is why uncertainty and confidence are first-class outputs instead of being hidden.",
            },
            {
                "question": "Why is Reflection Coach not part of the main judgment loop?",
                "answer": "Reflection Coach is a post-session explanation layer. It is useful for replay planning and self-regulation, but it should not be confused with the underlying live estimation pipeline.",
            },
            {
                "question": "What would strengthen the project next?",
                "answer": "More real Rokid sessions, more manual labels, richer outcome signals such as quiz performance, and extra modalities such as gaze, blink, and fixation would all make the proxy validation stronger.",
            },
        ]

    def _limitations(self, validation_summary: dict[str, Any]) -> list[dict[str, Any]]:
        validation_note = self._validation_line(validation_summary)
        return [
            {
                "title": "Proxy Scope Only",
                "detail": "The system infers study-process proxies from observable signals. It should not be presented as precise attention detection or internal mental-state measurement.",
            },
            {
                "title": "Label Volume Still Matters",
                "detail": validation_note,
            },
            {
                "title": "Scene Quality Can Limit Confidence",
                "detail": "Poor lighting, blur, unstable first-person framing, or weak scene content can reduce the reliability of proxy estimates.",
            },
            {
                "title": "Cross-User Differences Remain",
                "detail": "Different learners may show challenge, fatigue, and recovery in different ways, so calibration and cross-user validation remain important.",
            },
            {
                "title": "No Eye-Tracking Yet",
                "detail": "Without gaze, blink, fixation, or pupil-related signals, the project should stay conservative about what it infers from posture and scene context alone.",
            },
            {
                "title": "Presentation Assistant Is Not The Main Loop",
                "detail": "This module helps explain the project for demos and defense. It does not participate in the runtime learning-state judgment path.",
            },
        ]

    def _story_stage_lines(self, storyboard_payload: dict[str, Any]) -> str:
        stages = storyboard_payload.get("stages", []) if isinstance(storyboard_payload, dict) else []
        snippets = []
        for stage in stages[:5]:
            stage_key = str(stage.get("stage_key", "")).strip()
            if not stage_key:
                continue
            snippets.append(
                f"{_title_case(stage_key)} appears at {stage.get('time_range', 'an unavailable time range')}"
            )
        if not snippets:
            return "The storyboard gracefully falls back when no staged session evidence is available."
        return " ".join(snippets) + "."

    def _validation_line(self, validation_summary: dict[str, Any]) -> str:
        if not isinstance(validation_summary, dict) or not validation_summary.get("available"):
            return "Validation metrics are optional here and were not available for this run, so the presentation should describe the validation layer as prepared but not fully populated."
        accuracy = validation_summary.get("rule_accuracy")
        macro_f1 = validation_summary.get("rule_macro_f1")
        label_count = validation_summary.get("rule_label_count")
        if accuracy is not None and macro_f1 is not None:
            return (
                f"The current rule baseline reports accuracy {accuracy} and macro F1 {macro_f1} "
                f"on {label_count or 0} labeled windows. These numbers belong to the proxy-validation layer, not to the live HUD."
            )
        return (
            f"Validation exports exist, but the current labeled-window count is {label_count or 0}, "
            "so the presentation should describe this layer as an in-progress baseline rather than a finalized benchmark."
        )
