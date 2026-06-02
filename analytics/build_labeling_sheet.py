from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

import pandas as pd

from core.state_classifier import rule_baseline


DEFAULT_FEATURES_PATH = ROOT / "data" / "state_window_features.csv"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "state_labels_draft.csv"

AUTO_COLUMNS = [
    "session_id",
    "start_sample",
    "end_sample",
    "predicted_label",
    "confidence",
    "evidence_summary",
    "cognitive_load_mean",
    "behavioral_alignment_mean",
    "fatigue_risk_mean",
    "scene_lock_score_mean",
    "scene_switch_rate_mean",
    "study_surface_score_mean",
]

MANUAL_COLUMNS = [
    "label",
    "self_report_load",
    "self_report_attention",
    "self_report_fatigue",
    "task_difficulty",
    "quiz_score",
    "notes",
]

DRAFT_COLUMNS = AUTO_COLUMNS + MANUAL_COLUMNS


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def _safe_float(value: Any) -> float | str:
    try:
        if pd.isna(value):
            return ""
        return round(float(value), 4)
    except Exception:
        return ""


def _safe_int(value: Any) -> int | str:
    try:
        if pd.isna(value):
            return ""
        return int(float(value))
    except Exception:
        return ""


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    return frame if not frame.empty else pd.DataFrame(columns=frame.columns.tolist())


def _row_key(row: dict[str, Any] | pd.Series) -> tuple[str, str, str]:
    return (
        str(row.get("session_id", "")).strip(),
        str(_safe_int(row.get("start_sample"))),
        str(_safe_int(row.get("end_sample"))),
    )


def _existing_manual_values(draft_frame: pd.DataFrame) -> dict[tuple[str, str, str], dict[str, Any]]:
    if draft_frame.empty:
        return {}
    values: dict[tuple[str, str, str], dict[str, Any]] = {}
    for _, row in draft_frame.iterrows():
        values[_row_key(row)] = {column: row.get(column, "") for column in MANUAL_COLUMNS}
    return values


def _draft_row(row: pd.Series, preserved_manual: dict[str, Any] | None = None) -> dict[str, Any]:
    prediction = rule_baseline(row)
    payload = {
        "session_id": str(row.get("session_id", "")).strip(),
        "start_sample": _safe_int(row.get("start_sample")),
        "end_sample": _safe_int(row.get("end_sample")),
        "predicted_label": prediction["label"],
        "confidence": prediction["confidence"],
        "evidence_summary": " | ".join(prediction["evidence"]),
        "cognitive_load_mean": _safe_float(row.get("cognitive_load_mean")),
        "behavioral_alignment_mean": _safe_float(row.get("behavioral_alignment_mean")),
        "fatigue_risk_mean": _safe_float(row.get("fatigue_risk_mean")),
        "scene_lock_score_mean": _safe_float(row.get("scene_lock_score_mean")),
        "scene_switch_rate_mean": _safe_float(row.get("scene_switch_rate_mean")),
        "study_surface_score_mean": _safe_float(row.get("study_surface_score_mean")),
    }
    preserved_manual = preserved_manual or {}
    for column in MANUAL_COLUMNS:
        payload[column] = preserved_manual.get(column, "")
    return payload


def build_labeling_sheet(
    features_path: str | Path = DEFAULT_FEATURES_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    features_path = Path(features_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    features_frame = _load_csv(features_path)
    existing_draft = _load_csv(output_path)
    preserved_manual = _existing_manual_values(existing_draft)

    if features_frame.empty:
        pd.DataFrame(columns=DRAFT_COLUMNS).to_csv(output_path, index=False)
        return {
            "features_found": False,
            "windows": 0,
            "sessions": 0,
            "output_path": _relative_path(output_path),
            "features_path": _relative_path(features_path),
            "manual_rows_preserved": 0,
        }

    draft_rows: list[dict[str, Any]] = []
    preserved_count = 0
    for _, row in features_frame.iterrows():
        row_manual = preserved_manual.get(_row_key(row), {})
        if row_manual:
            preserved_count += 1
        draft_rows.append(_draft_row(row, preserved_manual=row_manual))

    draft_frame = pd.DataFrame(draft_rows, columns=DRAFT_COLUMNS)
    session_count = 0
    if not draft_frame.empty and "session_id" in draft_frame.columns:
        session_count = int(
            draft_frame["session_id"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()
        )
    draft_frame.to_csv(output_path, index=False)
    return {
        "features_found": True,
        "windows": int(len(draft_frame.index)),
        "sessions": session_count,
        "output_path": _relative_path(output_path),
        "features_path": _relative_path(features_path),
        "manual_rows_preserved": preserved_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a draft labeling sheet from state window features.")
    parser.add_argument("--features", default=str(DEFAULT_FEATURES_PATH), help="Input state window feature CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output draft labeling CSV.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_labeling_sheet(features_path=args.features, output_path=args.output)
    print("\nLabeling sheet draft")
    print(f"- Features: {summary['features_path']}")
    print(f"- Draft: {summary['output_path']}")
    print(f"- Windows: {summary['windows']}")
    print(f"- Sessions: {summary['sessions']}")
    if summary["manual_rows_preserved"]:
        print(f"- Preserved manual rows: {summary['manual_rows_preserved']}")
    if not summary["features_found"]:
        print("- No state window features were found. Run analytics/validate_learning_state.py first, or generate data/state_window_features.csv before labeling.")


if __name__ == "__main__":
    main()
