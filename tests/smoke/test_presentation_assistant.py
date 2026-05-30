import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.presentation_assistant import PresentationAssistant
from core.reflection_coach import ReflectionCoach
from utils.storage import DataLogger


class PresentationAssistantSmokeTests(unittest.TestCase):
    def test_summary_payload_shape(self):
        logger = DataLogger()
        coach = ReflectionCoach(logger)
        assistant = PresentationAssistant(logger, coach)
        payload = assistant.build_summary_payload(dataset="demo")
        self.assertEqual(payload.get("status"), "ok")
        self.assertIn("project_positioning", payload)
        self.assertIn("demo_script_3min", payload)
        self.assertIn("demo_script_5min", payload)
        self.assertIn("defense_qa", payload)
        self.assertIn("limitations", payload)
        self.assertIn("template-based", payload.get("module_boundary", "").lower())


if __name__ == "__main__":
    unittest.main()
