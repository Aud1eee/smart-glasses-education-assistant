import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from analytics.analyze_report import analyze
from analytics.generate_demo_assets import (
    DEMO_DIFFICULTY_PATH,
    DEMO_HEATMAP_PATH,
    DEMO_REPORT_PATH,
    generate_demo_report,
)
from analytics.verify_demo_states import evaluate_scenario


VALIDATION_JSON_PATH = ROOT / "exports" / "validation_summary.json"
VALIDATION_MD_PATH = ROOT / "exports" / "validation_summary.md"


SCENARIO_RULES = {
    "stable": {
        "label": "Stable focus",
        "checks": [
            ("tail_dominant_state", "in", {"Stable focus", "Focus settling"}),
            ("final_state", "in", {"Stable focus"}),
            ("avg_load", "max", 15),
            ("avg_focus", "min", 90),
        ],
    },
    "rising": {
        "label": "Rising cognitive load",
        "checks": [
            ("state_counts", "contains", "Load rising"),
            ("tail_dominant_state", "in", {"Load rising", "Fatigue risk", "Regulate now"}),
            ("final_state", "in", {"Load rising", "Fatigue risk", "Regulate now"}),
            ("avg_load", "between", (40, 70)),
            ("avg_focus", "max", 65),
        ],
    },
    "overload": {
        "label": "High-load regulation",
        "checks": [
            ("tail_dominant_state", "in", {"Fatigue risk", "Regulate now", "High load"}),
            ("final_state", "in", {"Fatigue risk", "Regulate now", "High load"}),
            ("avg_load", "min", 75),
            ("avg_focus", "max", 40),
            ("high_load_ratio", "min", 60),
        ],
    },
    "recovery": {
        "label": "Recovery state",
        "checks": [
            ("tail_dominant_state", "in", {"Stable focus", "Focus settling"}),
            ("final_state", "in", {"Stable focus"}),
            ("avg_load", "max", 15),
            ("avg_focus", "min", 85),
        ],
    },
}


PIPELINE_RULES = [
    ("samples", "min", 300, "Demo run should contain enough samples for a meaningful timeline."),
    ("avg_alignment", "between", (55, 75), "Average behavioral alignment should stay in a realistic mid-high range."),
    ("avg_load", "between", (30, 55), "Average load should show both stable and stressed segments."),
    ("avg_fatigue", "between", (20, 40), "Average fatigue should remain noticeable but not dominant across the full demo."),
    ("drift_ratio", "between", (40, 70), "Drift-risk ratio should reflect a mixed session rather than a perfectly stable trace."),
    ("high_load_ratio", "between", (25, 55), "High-load ratio should stay concentrated instead of filling the whole session."),
    ("low_conf_ratio", "max", 5, "Low-confidence ratio should stay low in the deterministic demo run."),
    ("difficulty_event_count", "min", 1, "At least one difficulty event should be captured in the presentation sequence."),
]


def _to_json_safe(value):
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _check_rule(metric_name, op, expected, observed):
    if op == "min":
        return observed >= expected, f">= {expected}"
    if op == "max":
        return observed <= expected, f"<= {expected}"
    if op == "between":
        low, high = expected
        return low <= observed <= high, f"{low} - {high}"
    if op == "in":
        return observed in expected, " / ".join(sorted(expected))
    if op == "contains":
        return expected in observed, expected
    raise ValueError(f"Unsupported operator: {op}")


def _evaluate_scenario_rules(name, result):
    checks = []
    for metric_name, op, expected in SCENARIO_RULES[name]["checks"]:
        observed = result[metric_name]
        passed, expected_text = _check_rule(metric_name, op, expected, observed)
        if metric_name == "state_counts":
            observed_text = ", ".join(sorted(observed.keys()))
        else:
            observed_text = observed
        checks.append({
            "metric": metric_name,
            "expected": expected_text,
            "observed": observed_text,
            "passed": passed,
        })
    return checks


def _evaluate_pipeline_rules(summary):
    checks = []
    for metric_name, op, expected, note in PIPELINE_RULES:
        observed = summary.get(metric_name, 0)
        passed, expected_text = _check_rule(metric_name, op, expected, observed)
        checks.append({
            "metric": metric_name,
            "expected": expected_text,
            "observed": observed,
            "passed": passed,
            "note": note,
        })
    return checks


def _build_markdown(payload):
    scenario_rows = []
    for item in payload["scenario_results"]:
        scenario_rows.append(
            "| {label} | {tail} | {final} | {load} | {focus} | {status} |".format(
                label=item["label"],
                tail=item["tail_dominant_state"],
                final=item["final_state"],
                load=item["avg_load"],
                focus=item["avg_focus"],
                status="PASS" if item["passed"] else "REVIEW",
            )
        )

    scenario_check_rows = []
    for item in payload["scenario_results"]:
        for check in item["checks"]:
            scenario_check_rows.append(
                "| {label} | {metric} | {expected} | {observed} | {status} |".format(
                    label=item["label"],
                    metric=check["metric"],
                    expected=check["expected"],
                    observed=check["observed"],
                    status="PASS" if check["passed"] else "REVIEW",
                )
            )

    pipeline_rows = []
    for check in payload["pipeline_checks"]:
        pipeline_rows.append(
            "| {metric} | {expected} | {observed} | {note} | {status} |".format(
                metric=check["metric"],
                expected=check["expected"],
                observed=check["observed"],
                note=check["note"],
                status="PASS" if check["passed"] else "REVIEW",
            )
        )

    notes = []
    if not payload["demo_summary"].get("heatmap_saved", False):
        notes.append(
            "- Heatmap export was skipped in the current Windows runtime bridge because `matplotlib` is not available in a compatible binary form. This does not affect the scenario checks or summary metrics."
        )

    notes.append(
        "- The scenario validation uses deterministic simulated motion, so it is intended to verify algorithm behavior and demo consistency, not real-world educational validity."
    )
    notes.append(
        "- `Stable` and `recovery` scenarios currently allow `Focus settling` as an acceptable tail-dominant state because the session engine intentionally uses a conservative settling phase before fully stabilizing."
    )
    notes.append(
        "- This validation layer is best paired with manual observation, task performance, and future Rokid-device input tests."
    )

    return "\n".join([
        "# Learning State Validation Summary",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Overall status: **{'PASS' if payload['overall_passed'] else 'REVIEW'}**",
        "",
        "## Validation Scope",
        "",
        "- Scenario-level checks for `stable`, `rising`, `overload`, and `recovery` traces",
        "- End-to-end demo pipeline checks using `demo_study_report.csv` and `demo_difficulty_events.csv`",
        "",
        "## Scenario Overview",
        "",
        "| Scenario | Tail dominant | Final state | Avg load | Avg focus | Result |",
        "| --- | --- | --- | ---: | ---: | --- |",
        *scenario_rows,
        "",
        "## Scenario Check Details",
        "",
        "| Scenario | Metric | Expected | Observed | Result |",
        "| --- | --- | --- | --- | --- |",
        *scenario_check_rows,
        "",
        "## End-to-End Demo Checks",
        "",
        "| Metric | Expected | Observed | Rationale | Result |",
        "| --- | --- | --- | --- | --- |",
        *pipeline_rows,
        "",
        "## Notes",
        "",
        *notes,
        "",
    ])


def main():
    scenario_results = []
    for scenario_name in ["stable", "rising", "overload", "recovery"]:
        result = evaluate_scenario(scenario_name)
        checks = _evaluate_scenario_rules(scenario_name, result)
        result["checks"] = checks
        result["passed"] = all(item["passed"] for item in checks)
        scenario_results.append(result)

    generate_demo_report(
        output_path=DEMO_REPORT_PATH,
        difficulty_output_path=DEMO_DIFFICULTY_PATH,
        session_id="demo-session-1",
    )
    demo_summary = analyze(
        input_path=DEMO_REPORT_PATH,
        heatmap_path=DEMO_HEATMAP_PATH,
        legacy_output_path=None,
        events_path=DEMO_DIFFICULTY_PATH,
        title_prefix="Demo Attention Heatmap Review",
    )
    pipeline_checks = _evaluate_pipeline_rules(demo_summary)
    pipeline_passed = all(item["passed"] for item in pipeline_checks)
    scenarios_passed = all(item["passed"] for item in scenario_results)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_passed": scenarios_passed and pipeline_passed,
        "scenario_results": scenario_results,
        "demo_summary": demo_summary,
        "pipeline_checks": pipeline_checks,
    }
    payload = _to_json_safe(payload)

    VALIDATION_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    VALIDATION_MD_PATH.write_text(_build_markdown(payload), encoding="utf-8")

    print("\nLearning-state validation")
    print(f"- Scenario checks: {sum(item['passed'] for item in scenario_results)}/{len(scenario_results)} passed")
    print(f"- Pipeline checks: {sum(item['passed'] for item in pipeline_checks)}/{len(pipeline_checks)} passed")
    print(f"- Overall status: {'PASS' if payload['overall_passed'] else 'REVIEW'}")
    print(f"- JSON: {VALIDATION_JSON_PATH}")
    print(f"- Markdown: {VALIDATION_MD_PATH}")
    if not demo_summary.get("heatmap_saved", False):
        print("- Heatmap export: skipped in the current Windows runtime bridge")


if __name__ == "__main__":
    main()
