import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.demo_storyboard import build_demo_storyboard
from core.reflection_coach import ReflectionCoach
from utils.storage import DataLogger


class DemoStoryboardSmokeTests(unittest.TestCase):
    def test_storyboard_payload_shape(self):
        logger = DataLogger()
        coach = ReflectionCoach(logger)
        payload = build_demo_storyboard(logger=logger, reflection_coach=coach, dataset="demo")
        self.assertEqual(payload.get("status"), "ok")
        self.assertIn("story_summary", payload)
        self.assertIn("stages", payload)
        self.assertEqual(len(payload.get("stages", [])), 5)
        self.assertIn("learning-state pro", payload.get("module_boundary", "").lower())


if __name__ == "__main__":
    unittest.main()
