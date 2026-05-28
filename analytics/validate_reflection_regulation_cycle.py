import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.reflection_coach import ReflectionCoach


class DummyLogger:
    def build_reflection_context(self, session_id=None, dataset="live", event_id=None):
        return {
            "dataset": dataset,
            "session_id": session_id or "closure-session-1",
            "requested_event_id": event_id,
            "selected_event_id": 3,
            "session_options": [{"session_id": session_id or "closure-session-1", "label": "Closure Session"}],
            "summary": {
                "duration_label": "08:40",
                "avg_load": 56.0,
                "avg_fatigue": 34.0,
                "avg_switching": 41.0,
                "productive_struggle_ratio": 12.0,
                "off_task_ratio": 28.0,
                "low_confidence_ratio": 8.0,
                "difficulty_count": 1,
                "primary_task_mode": "reading",
                "samples": 120,
            },
            "highlight_event": {
                "event_id": 3,
                "time_window": "04:12-05:06",
                "task_mode": "reading",
                "severity": "high",
                "severity_label": "HIGH",
                "state_hint": "off_task_risk",
                "state_hint_label": "Off-task risk",
                "trigger_reason": "Switching pressure rose faster than comprehension stabilized.",
                "review_note": "Replay this window after reducing source switching.",
                "catch_up_action": "Lock onto one source before replaying the segment.",
                "guidance": "Reduce switching and keep one target.",
            },
            "events": [],
            "timeline": {},
            "assets": {},
            "distributions": {},
            "anchors": {
                "closing_state": {
                    "state_hint": "off_task_risk",
                    "guidance": "Reduce switching and keep one target.",
                    "task_mode": "reading",
                }
            },
            "empty": False,
        }


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def run_active_cycle(coach):
    payload = coach.build_payload(
        session_id="closure-session-1",
        dataset="live",
        learner_note="I kept bouncing between slides and my notes.",
        next_goal="hold one source steady for the first two minutes",
        provider_override="heuristic",
        live_guardian_state={
            "task_mode": "reading",
            "state_hint": "off_task_risk",
            "focus_score": 39.0,
            "cognitive_load": 62.0,
            "load_level": "high",
            "load_reason": "Switching stayed high and the target never settled.",
            "fatigue_risk": 28.0,
            "uncertainty_score": 21.0,
            "switching_index": 57.0,
        },
        live_session_state={
            "guidance": "Lock one source and slow down.",
            "action": "regulate",
            "state_label": "Off-task risk",
        },
        live_difficulty_state={
            "active_event": {
                "event_id": 7,
                "status": "active",
                "severity": "high",
                "trigger_reason": "Switching pressure stayed high across the block.",
                "guidance": "Reduce switching and keep one target.",
                "review_note": "Replay only after stabilizing one source.",
                "time_window": "06:10-06:58",
            },
            "last_event": None,
            "event_count": 1,
        },
    )
    cycle = payload.get("regulation_cycle") or {}
    assert_true(cycle.get("status") == "active", "active regulation cycle should be marked active")
    assert_true("Source-lock reset" in (cycle.get("recommended_next_action", {}) or {}).get("title", ""), "off-task cycle should recommend a source-lock action")
    assert_true(payload.get("reflection_questions", [{}])[0].get("question") == cycle.get("reflection_question"), "cycle question should lead the reflection question list")
    assert_true(payload.get("next_session_experiments", [{}])[0].get("title") == (cycle.get("recommended_experiment", {}) or {}).get("title"), "cycle experiment should lead the experiment list")
    print("PASS regulation_cycle_active")


def run_recovery_cycle(coach):
    payload = coach.build_payload(
        session_id="closure-session-1",
        dataset="live",
        learner_note="I locked onto one source on the replay.",
        next_goal="keep the opening stable before adding notes",
        provider_override="heuristic",
        live_guardian_state={
            "task_mode": "reading",
            "state_hint": "stable",
            "focus_score": 78.0,
            "cognitive_load": 33.0,
            "load_level": "low",
            "load_reason": "The current block is comparatively stable.",
            "fatigue_risk": 24.0,
            "uncertainty_score": 16.0,
            "switching_index": 14.0,
        },
        live_session_state={
            "guidance": "Recovery is working. Rebuild a steady rhythm.",
            "action": "recover_focus",
            "state_label": "Recovery",
        },
        live_difficulty_state={
            "active_event": None,
            "last_event": {
                "event_id": 7,
                "status": "resolved",
                "severity": "high",
                "trigger_reason": "Switching pressure stayed high across the block.",
                "guidance": "Reduce switching and keep one target.",
                "review_note": "Replay only after stabilizing one source.",
                "time_window": "06:10-06:58",
            },
            "event_count": 1,
        },
    )
    cycle = payload.get("regulation_cycle") or {}
    outcome = cycle.get("outcome_review") or {}
    assert_true(cycle.get("status") == "improved", "stable follow-up should look improved")
    assert_true(outcome.get("label") == "Recovery looks credible", "recovery cycle should explain that recovery is credible")
    assert_true(bool(payload.get("coach_summary", {}).get("regulation_focus")), "coach summary should expose regulation focus text")
    assert_true("Regulation loop:" in (payload.get("coach_memo") or ""), "coach memo should mention the regulation loop")
    print("PASS regulation_cycle_recovery")


def main():
    coach = ReflectionCoach(DummyLogger())
    run_active_cycle(coach)
    run_recovery_cycle(coach)
    print("ALL REFLECTION REGULATION CYCLE TESTS PASSED")


if __name__ == "__main__":
    main()
