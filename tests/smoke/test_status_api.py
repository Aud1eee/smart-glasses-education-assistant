import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from app import app


class StatusApiSmokeTests(unittest.TestCase):
    def test_status_and_demo_review_routes(self):
        with app.test_client() as client:
            status_response = client.get("/status")
            review_response = client.get("/api/review_summary?dataset=demo")

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(review_response.status_code, 200)

        status_payload = status_response.get_json() or {}
        review_payload = review_response.get_json() or {}

        self.assertIn("state_hint", status_payload)
        self.assertIn("session", status_payload)
        self.assertIn("interpreted_state", status_payload)
        self.assertIn("summary", review_payload)


if __name__ == "__main__":
    unittest.main()
