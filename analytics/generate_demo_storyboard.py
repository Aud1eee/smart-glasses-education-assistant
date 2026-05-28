from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.demo_storyboard import (
    DEFAULT_FEATURES_PATH,
    build_demo_storyboard,
    build_demo_storyboard_markdown,
)
from core.reflection_coach import ReflectionCoach
from utils.storage import DataLogger


DEFAULT_OUTPUT_PATH = ROOT / "exports" / "demo_storyboard.md"
DEFAULT_DEMO_REPORT_PATH = ROOT / "data" / "demo_study_report.csv"
DEFAULT_LIVE_REPORT_PATH = ROOT / "data" / "study_report.csv"


def _resolve_dataset(dataset_arg: str) -> str:
    normalized = str(dataset_arg or "auto").strip().lower()
    if normalized in {"demo", "live"}:
        return normalized
    if DEFAULT_DEMO_REPORT_PATH.exists() and DEFAULT_DEMO_REPORT_PATH.stat().st_size > 10:
        return "demo"
    if DEFAULT_LIVE_REPORT_PATH.exists() and DEFAULT_LIVE_REPORT_PATH.stat().st_size > 10:
        return "live"
    return "demo"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a reproducible demo storyboard markdown report.")
    parser.add_argument("--dataset", default="auto", choices=["auto", "demo", "live"], help="Prefer demo or live session data.")
    parser.add_argument("--session-id", default="", help="Optional session ID override.")
    parser.add_argument("--features", default=str(DEFAULT_FEATURES_PATH), help="Optional state window features CSV path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Markdown output path.")
    args = parser.parse_args()

    dataset = _resolve_dataset(args.dataset)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger = DataLogger()
    reflection_coach = ReflectionCoach(logger)
    payload = build_demo_storyboard(
        logger=logger,
        reflection_coach=reflection_coach,
        dataset=dataset,
        session_id=args.session_id or None,
        features_path=Path(args.features),
    )
    report_source = "data/demo_study_report.csv" if dataset == "demo" else "data/study_report.csv"
    output_path.write_text(build_demo_storyboard_markdown(payload, report_source=report_source), encoding="utf-8")
    print(f"Demo storyboard written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
