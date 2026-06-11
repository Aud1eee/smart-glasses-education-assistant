import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.state_interpreter import StateInterpreter
from core.state_transition_manager import StateTransitionManager


def _frame_only_snapshot(**overrides):
    snapshot = {
        "task_mode": "reading",
        "state_hint": "stable",
        "load_level": "low",
        "focus_score": 82,
        "behavioral_alignment": 80,
        "cognitive_load": 24,
        "fatigue_risk": 12,
        "uncertainty_score": 18,
        "switching_index": 12,
        "drift_trend": 2,
        "combined_drift": 6,
        "movement_intensity": 16,
        "stability": 78,
        "scene_content_score": 74,
        "scene_text_score": 66,
        "scene_stability_score": 72,
        "scene_switch_rate": 14,
        "study_surface_score": 76,
        "scene_lock_score": 78,
        "blur_score": 58,
        "brightness_score": 52,
        "tracking_confidence": 0.86,
        "tracking_uncertainty": 14,
        "tracking_state": "scene_locked",
        "source_mode": "frame_only",
        "motion_source": "scene-derived",
        "pose_source": "scene-proxy",
        "has_pose": False,
        "has_imu": False,
        "pose_reliability": "scene_proxy",
        "valid_frame_streak": 1,
        "valid_frame_seconds": 0.0,
        "missing_signals": ["pose", "imu", "motion"],
        "rokid_compatible_mode": True,
    }
    snapshot.update(overrides)
    return snapshot


class RokidCompatibleStateModeSmokeTests(unittest.TestCase):
    def setUp(self):
        self.interpreter = StateInterpreter()

    def test_single_frame_only_snapshot_stays_conservative(self):
        result = self.interpreter.interpret(_frame_only_snapshot())
        self.assertIn(result["label"], {"scene_snapshot", "signal_uncertain"})
        self.assertNotEqual(result["label"], "stable_focus")
        self.assertLessEqual(result["confidence"], 0.62)
        self.assertTrue(result["auxiliary_flags"]["frame_only_guard_active"])

    def test_first_frame_does_not_initialize_stable_focus(self):
        interpreted = self.interpreter.interpret(_frame_only_snapshot())
        manager = StateTransitionManager()
        transition = manager.update(interpreted, now=1000.0)
        self.assertIn(transition["stable_label"], {"scene_snapshot", "signal_uncertain"})
        self.assertNotEqual(transition["stable_label"], "stable_focus")

    def test_valid_frame_run_can_emit_conservative_proxy_state(self):
        result = self.interpreter.interpret(_frame_only_snapshot(
            state_hint="load_rising",
            load_level="medium",
            focus_score=66,
            behavioral_alignment=64,
            cognitive_load=63,
            fatigue_risk=34,
            switching_index=28,
            drift_trend=9,
            combined_drift=11,
            movement_intensity=18,
            stability=64,
            scene_switch_rate=36,
            valid_frame_streak=5,
            valid_frame_seconds=4.0,
        ))
        self.assertEqual(result["label"], "load_rising_proxy")
        self.assertLessEqual(result["confidence"], 0.62)

    def test_frame_only_does_not_force_fatigue_risk(self):
        result = self.interpreter.interpret(_frame_only_snapshot(
            state_hint="fatigue_risk",
            load_level="high",
            focus_score=42,
            behavioral_alignment=40,
            cognitive_load=72,
            fatigue_risk=88,
            switching_index=36,
            drift_trend=12,
            combined_drift=18,
            movement_intensity=8,
            stability=30,
            valid_frame_streak=6,
            valid_frame_seconds=5.0,
        ))
        self.assertNotEqual(result["label"], "fatigue_risk")
        self.assertEqual(result["label"], "load_rising_proxy")

    def test_missing_imu_caps_confidence_even_for_stable_scene_proxy(self):
        result = self.interpreter.interpret(_frame_only_snapshot(
            valid_frame_streak=6,
            valid_frame_seconds=5.0,
        ))
        self.assertEqual(result["label"], "stable_focus")
        self.assertLessEqual(result["confidence"], 0.62)

    def test_signal_uncertain_fallback_for_unstable_tracking(self):
        result = self.interpreter.interpret(_frame_only_snapshot(
            state_hint="off_task_risk",
            focus_score=28,
            behavioral_alignment=22,
            cognitive_load=76,
            fatigue_risk=84,
            uncertainty_score=74,
            switching_index=70,
            drift_trend=11,
            combined_drift=18,
            movement_intensity=10,
            stability=24,
            scene_content_score=12,
            scene_text_score=8,
            scene_stability_score=18,
            scene_switch_rate=74,
            study_surface_score=14,
            scene_lock_score=10,
            blur_score=8,
            brightness_score=93,
            tracking_confidence=0.18,
            tracking_uncertainty=82,
            tracking_state="blurred",
        ))
        self.assertEqual(result["label"], "signal_uncertain")


if __name__ == "__main__":
    unittest.main()
