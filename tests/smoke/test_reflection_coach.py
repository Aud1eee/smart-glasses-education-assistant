import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.reflection_coach import ReflectionCoach
from utils.storage import DataLogger


class ReflectionCoachSmokeTests(unittest.TestCase):
    def test_review_summary_payload_shape(self):
        logger = DataLogger()
        coach = ReflectionCoach(logger)
        review_payload = logger.build_review_payload(dataset="demo")
        payload = coach.build_review_summary_payload(
            review_payload=review_payload,
            difficulty_events=review_payload.get("events", []),
            validation_summary={"status": "ok", "features_available": False},
            session_id=review_payload.get("session_id"),
            dataset="demo",
        )
        self.assertEqual(payload.get("status"), "ok")
        self.assertIn("session_summary", payload)
        self.assertIn("key_moments", payload)
        self.assertIn("reflection_questions", payload)
        self.assertIn("next_actions", payload)
        self.assertIn("learning-state proxies", payload.get("module_boundary", "").lower())


if __name__ == "__main__":
    unittest.main()
