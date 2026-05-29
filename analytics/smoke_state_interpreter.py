import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.state_interpreter import StateInterpreter  # noqa: E402


def build_snapshots():
    return {
        "stable_focus": {
            "task_mode": "reading",
            "state_hint": "stable",
            "focus_score": 84,
            "behavioral_alignment": 88,
            "cognitive_load": 34,
            "load_level": "low",
            "fatigue_risk": 24,
            "uncertainty_score": 18,
            "switching_index": 14,
            "drift_trend": 1,
            "combined_drift": 6,
            "movement_intensity": 16,
            "stability": 82,
            "scene_content_score": 74,
            "scene_text_score": 71,
            "scene_stability_score": 80,
            "scene_switch_rate": 18,
            "study_surface_score": 76,
            "scene_lock_score": 79,
            "blur_score": 60,
            "brightness_score": 53,
            "tracking_confidence": 0.92,
            "tracking_uncertainty": 12,
            "tracking_state": "scene_locked",
        },
        "productive_struggle": {
            "task_mode": "reading",
            "state_hint": "productive_struggle",
            "focus_score": 63,
            "behavioral_alignment": 74,
            "cognitive_load": 68,
            "load_level": "medium",
            "fatigue_risk": 36,
            "uncertainty_score": 24,
            "switching_index": 28,
            "drift_trend": 7,
            "combined_drift": 14,
            "movement_intensity": 24,
            "stability": 61,
            "scene_content_score": 70,
            "scene_text_score": 68,
            "scene_stability_score": 66,
            "scene_switch_rate": 28,
            "study_surface_score": 64,
            "scene_lock_score": 58,
            "blur_score": 56,
            "brightness_score": 50,
            "tracking_confidence": 0.86,
            "tracking_uncertainty": 18,
            "tracking_state": "tracked",
        },
        "off_task_risk": {
            "task_mode": "reading",
            "state_hint": "off_task_risk",
            "focus_score": 33,
            "behavioral_alignment": 36,
            "cognitive_load": 58,
            "load_level": "medium",
            "fatigue_risk": 29,
            "uncertainty_score": 28,
            "switching_index": 73,
            "drift_trend": 10,
            "combined_drift": 18,
            "movement_intensity": 42,
            "stability": 38,
            "scene_content_score": 28,
            "scene_text_score": 20,
            "scene_stability_score": 32,
            "scene_switch_rate": 66,
            "study_surface_score": 30,
            "scene_lock_score": 24,
            "blur_score": 42,
            "brightness_score": 47,
            "tracking_confidence": 0.58,
            "tracking_uncertainty": 36,
            "tracking_state": "tracked",
        },
        "fatigue_risk": {
            "task_mode": "reading",
            "state_hint": "fatigue_risk",
            "focus_score": 39,
            "behavioral_alignment": 44,
            "cognitive_load": 46,
            "load_level": "medium",
            "fatigue_risk": 76,
            "uncertainty_score": 34,
            "switching_index": 26,
            "drift_trend": 5,
            "combined_drift": 16,
            "movement_intensity": 12,
            "stability": 36,
            "scene_content_score": 54,
            "scene_text_score": 48,
            "scene_stability_score": 42,
            "scene_switch_rate": 24,
            "study_surface_score": 58,
            "scene_lock_score": 51,
            "blur_score": 50,
            "brightness_score": 49,
            "tracking_confidence": 0.74,
            "tracking_uncertainty": 24,
            "tracking_state": "tracked",
        },
        "signal_uncertain": {
            "task_mode": "reading",
            "state_hint": "stable",
            "focus_score": 41,
            "behavioral_alignment": 46,
            "cognitive_load": 40,
            "load_level": "low",
            "fatigue_risk": 31,
            "uncertainty_score": 72,
            "switching_index": 18,
            "drift_trend": 2,
            "combined_drift": 8,
            "movement_intensity": 10,
            "stability": 30,
            "scene_content_score": 12,
            "scene_text_score": 9,
            "scene_stability_score": 20,
            "scene_switch_rate": 34,
            "study_surface_score": 16,
            "scene_lock_score": 10,
            "blur_score": 11,
            "brightness_score": 93,
            "tracking_confidence": 0.19,
            "tracking_uncertainty": 78,
            "tracking_state": "blurred",
        },
        "note_taking_valid_switch": {
            "task_mode": "note-taking",
            "state_hint": "productive_struggle",
            "focus_score": 75,
            "behavioral_alignment": 88,
            "cognitive_load": 64,
            "load_level": "medium",
            "fatigue_risk": 33,
            "uncertainty_score": 23,
            "switching_index": 54,
            "drift_trend": 6,
            "combined_drift": 12,
            "movement_intensity": 28,
            "stability": 61,
            "scene_content_score": 66,
            "scene_text_score": 61,
            "scene_stability_score": 63,
            "scene_switch_rate": 44,
            "study_surface_score": 63,
            "scene_lock_score": 49,
            "blur_score": 54,
            "brightness_score": 51,
            "tracking_confidence": 0.82,
            "tracking_uncertainty": 20,
            "tracking_state": "tracked",
        },
    }


def main():
    interpreter = StateInterpreter()
    print("State interpreter smoke test")
    print("=" * 72)
    for name, snapshot in build_snapshots().items():
        result = interpreter.interpret(snapshot)
        print(f"\n[{name}]")
        print(f"interpreted_state: {result['label']}")
        print(f"display_label:     {result['display_label']}")
        print(f"confidence:        {result['confidence']}")
        print(f"uncertainty:       {result['uncertainty_reason'] or '--'}")
        print("axes:")
        print(json.dumps(result["axes"], ensure_ascii=True, indent=2))
        print("auxiliary_flags:")
        print(json.dumps(result["auxiliary_flags"], ensure_ascii=True, indent=2))
        print("evidence:")
        for item in result["evidence"]:
            print(f"- {item}")


if __name__ == "__main__":
    main()
