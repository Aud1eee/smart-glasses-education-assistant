import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.state_interpreter import StateInterpreter


class StateInterpreterSmokeTests(unittest.TestCase):
    def setUp(self):
        self.interpreter = StateInterpreter()

    def test_signal_uncertain_overrides_other_risk_like_patterns(self):
        result = self.interpreter.interpret({
            "task_mode": "reading",
            "state_hint": "off_task_risk",
            "focus_score": 32,
            "behavioral_alignment": 34,
            "cognitive_load": 58,
            "fatigue_risk": 71,
            "uncertainty_score": 75,
            "switching_index": 74,
            "drift_trend": 9,
            "combined_drift": 18,
            "movement_intensity": 10,
            "stability": 28,
            "scene_content_score": 10,
            "scene_text_score": 8,
            "scene_stability_score": 20,
            "scene_switch_rate": 70,
            "study_surface_score": 18,
            "scene_lock_score": 12,
            "blur_score": 10,
            "brightness_score": 93,
            "tracking_confidence": 0.18,
            "tracking_uncertainty": 80,
            "tracking_state": "blurred",
        })
        self.assertEqual(result["label"], "signal_uncertain")
        self.assertTrue(result["auxiliary_flags"]["signal_uncertain_candidate"])

    def test_note_taking_switch_can_stay_productive(self):
        result = self.interpreter.interpret({
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
        })
        self.assertEqual(result["label"], "productive_struggle")
        self.assertTrue(result["auxiliary_flags"]["valid_learning_switch"])
        self.assertFalse(result["auxiliary_flags"]["off_task_switch"])


if __name__ == "__main__":
    unittest.main()
