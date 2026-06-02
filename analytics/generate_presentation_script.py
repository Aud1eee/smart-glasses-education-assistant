from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from core.presentation_assistant import PresentationAssistant
from core.reflection_coach import ReflectionCoach
from utils.storage import DataLogger


DEFAULT_OUTPUT_DIR = ROOT / "exports"
DEFAULT_SCRIPT_3MIN_PATH = DEFAULT_OUTPUT_DIR / "presentation_script_3min.md"
DEFAULT_SCRIPT_5MIN_PATH = DEFAULT_OUTPUT_DIR / "presentation_script_5min.md"
DEFAULT_DEFENSE_QA_PATH = DEFAULT_OUTPUT_DIR / "defense_qa.md"


def _render_positioning(positioning: dict) -> list[str]:
    return [
        "## Project Positioning",
        "",
        f"- Headline: {positioning.get('headline', '--')}",
        f"- One-liner: {positioning.get('one_liner', '--')}",
        f"- Problem statement: {positioning.get('problem_statement', '--')}",
        f"- Project claim: {positioning.get('project_claim', '--')}",
        f"- Guardrail: {positioning.get('guardrail', '--')}",
        f"- Validation status: {positioning.get('validation_status', '--')}",
        "",
    ]


def _render_script(title: str, payload: dict, sections: list[dict]) -> str:
    lines = [
        f"# {title}",
        "",
        f"- Generated at: {payload.get('generated_at', '--')}",
        f"- Dataset: {payload.get('dataset', 'demo')}",
        f"- Session ID: {payload.get('session_id', '--') or '--'}",
        "",
        f"> {payload.get('module_boundary', 'Presentation Assistant is a template-based presentation layer.')}",
        "",
    ]
    lines.extend(_render_positioning(payload.get("project_positioning", {})))
    lines.append("## Talk Track")
    lines.append("")
    for index, section in enumerate(sections, start=1):
        lines.append(f"### {index}. {section.get('section', 'Presentation Section')}")
        lines.append("")
        lines.append(f"- Target seconds: {section.get('target_seconds', '--')}")
        lines.append(f"- Talk track: {section.get('talk_track', '--')}")
        lines.append("")
    lines.append("## Limitations To Say Out Loud")
    lines.append("")
    for item in payload.get("limitations", []):
        lines.append(f"- **{item.get('title', 'Limitation')}**: {item.get('detail', '--')}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_defense_qa(payload: dict) -> str:
    lines = [
        "# Defense Q&A",
        "",
        f"- Generated at: {payload.get('generated_at', '--')}",
        f"- Dataset: {payload.get('dataset', 'demo')}",
        "",
        f"> {payload.get('module_boundary', 'Presentation Assistant is a template-based presentation layer.')}",
        "",
    ]
    lines.extend(_render_positioning(payload.get("project_positioning", {})))
    lines.append("## Common Questions")
    lines.append("")
    for index, item in enumerate(payload.get("defense_qa", []), start=1):
        lines.append(f"### Q{index}. {item.get('question', 'Question')}")
        lines.append("")
        lines.append(item.get("answer", "--"))
        lines.append("")
    lines.append("## Metric Explanations")
    lines.append("")
    for item in payload.get("metric_explanations", []):
        lines.append(f"- **{item.get('metric', 'Metric')}**: {item.get('explanation', '--')}")
        lines.append(f"  Current context: {item.get('current_context', '--')}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate template-based presentation and defense markdown files.")
    parser.add_argument("--dataset", default="demo", choices=["demo", "live"], help="Choose demo or live data for the presentation summary.")
    parser.add_argument("--session-id", default="", help="Optional session ID override.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for generated markdown files.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = DataLogger()
    reflection_coach = ReflectionCoach(logger)
    assistant = PresentationAssistant(logger, reflection_coach)
    payload = assistant.build_summary_payload(dataset=args.dataset, session_id=args.session_id or None)

    script_3min_path = output_dir / "presentation_script_3min.md"
    script_5min_path = output_dir / "presentation_script_5min.md"
    defense_qa_path = output_dir / "defense_qa.md"

    script_3min_path.write_text(_render_script("Presentation Script (3 min)", payload, payload.get("demo_script_3min", [])), encoding="utf-8")
    script_5min_path.write_text(_render_script("Presentation Script (5 min)", payload, payload.get("demo_script_5min", [])), encoding="utf-8")
    defense_qa_path.write_text(_render_defense_qa(payload), encoding="utf-8")

    print(f"Wrote {script_3min_path}")
    print(f"Wrote {script_5min_path}")
    print(f"Wrote {defense_qa_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
