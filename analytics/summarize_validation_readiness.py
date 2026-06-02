from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

import pandas as pd

from core.state_classifier import LABELS, sklearn_status


DEFAULT_FEATURES_PATH = ROOT / "data" / "state_window_features.csv"
DEFAULT_LABELS_PATH = ROOT / "data" / "state_labels.csv"
DEFAULT_OUTPUT_PATH = ROOT / "exports" / "validation_readiness.md"


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    return frame if not frame.empty else pd.DataFrame(columns=frame.columns.tolist())


def _valid_label_frame(labels_frame: pd.DataFrame) -> pd.DataFrame:
    if labels_frame.empty or "label" not in labels_frame.columns:
        return pd.DataFrame(columns=labels_frame.columns.tolist())
    frame = labels_frame.copy()
    frame["label"] = frame["label"].fillna("").astype(str).str.strip()
    return frame[frame["label"].isin(LABELS)].reset_index(drop=True)


def _readiness_payload(
    features_path: Path,
    labels_path: Path,
) -> dict[str, Any]:
    features_frame = _load_csv(features_path)
    labels_frame = _load_csv(labels_path)
    valid_labels = _valid_label_frame(labels_frame)

    label_counts = {label: 0 for label in LABELS}
    if not valid_labels.empty:
        for label, count in valid_labels["label"].value_counts().items():
            label_counts[str(label)] = int(count)

    usable_label_rows = int(len(valid_labels.index))
    total_label_rows = int(len(labels_frame.index))
    threshold_status = {
        20: usable_label_rows >= 20,
        50: usable_label_rows >= 50,
        100: usable_label_rows >= 100,
    }
    sklearn_env = sklearn_status()
    label_diversity = int(valid_labels["label"].nunique()) if not valid_labels.empty else 0

    blockers = []
    if usable_label_rows < 20:
        blockers.append("at least 20 usable labeled windows are recommended before sklearn baseline training")
    if label_diversity < 2:
        blockers.append("at least 2 label classes are needed for sklearn baseline training")
    if not sklearn_env.get("sklearn_available", False):
        blockers.append(f"sklearn is unavailable in the current environment: {sklearn_env.get('sklearn_error', '')}".strip())

    feature_sessions = 0
    if not features_frame.empty and "session_id" in features_frame.columns:
        feature_sessions = int(
            features_frame["session_id"].astype(str).str.strip().replace("", pd.NA).dropna().nunique()
        )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features_path": _relative_path(features_path),
        "labels_path": _relative_path(labels_path),
        "feature_windows": int(len(features_frame.index)),
        "feature_sessions": feature_sessions,
        "labels_file_present": bool(labels_path.exists() and labels_path.stat().st_size > 0),
        "total_label_rows": total_label_rows,
        "usable_label_rows": usable_label_rows,
        "label_diversity": label_diversity,
        "label_counts": label_counts,
        "threshold_status": threshold_status,
        "sklearn_environment": sklearn_env,
        "sklearn_baseline_ready": usable_label_rows >= 20 and label_diversity >= 2 and bool(sklearn_env.get("sklearn_available", False)),
        "sklearn_blockers": blockers,
    }


def _build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Validation Readiness",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Window features: `{payload['features_path']}`",
        f"- Labels: `{payload['labels_path']}`",
        "",
        "## Current Counts",
        "",
        f"- Window feature rows: {payload['feature_windows']}",
        f"- Sessions with extracted windows: {payload['feature_sessions']}",
        f"- Total label rows in file: {payload['total_label_rows']}",
        f"- Usable labeled windows: {payload['usable_label_rows']}",
        f"- Label diversity: {payload['label_diversity']}",
        "",
        "## Per-Label Counts",
        "",
        "| Label | Count |",
        "| --- | ---: |",
    ]
    for label in LABELS:
        lines.append(f"| {label} | {payload['label_counts'].get(label, 0)} |")

    lines.extend([
        "",
        "## Thresholds",
        "",
        f"- 20 labeled windows: {'ready' if payload['threshold_status'][20] else 'not yet'}",
        f"- 50 labeled windows: {'ready' if payload['threshold_status'][50] else 'not yet'}",
        f"- 100 labeled windows: {'ready' if payload['threshold_status'][100] else 'not yet'}",
        "",
        "## Sklearn Baseline Readiness",
        "",
        f"- sklearn installed: {payload['sklearn_environment'].get('sklearn_available', False)}",
        f"- sklearn baseline ready: {payload['sklearn_baseline_ready']}",
    ])

    if payload["sklearn_blockers"]:
        lines.append("- blockers:")
        for blocker in payload["sklearn_blockers"]:
            lines.append(f"  - {blocker}")
    else:
        lines.append("- blockers: none")

    lines.extend([
        "",
        "## Next Step",
        "",
    ])
    if payload["feature_windows"] <= 0:
        lines.append("- Generate `data/state_window_features.csv` first with `python analytics/validate_learning_state.py` or `python core/state_feature_extractor.py`.")
    elif payload["usable_label_rows"] <= 0:
        lines.append("- Build `data/state_labels_draft.csv` with `python analytics/build_labeling_sheet.py`, then curate rows into `data/state_labels.csv`.")
    elif not payload["threshold_status"][20]:
        lines.append("- Keep labeling until at least 20 usable windows are available so the validation workflow can be demonstrated end to end.")
    elif not payload["threshold_status"][50]:
        lines.append("- You can already run rule-baseline validation; keep labeling toward 50 windows for a more credible first demo.")
    elif not payload["threshold_status"][100]:
        lines.append("- You have enough data for an early demo. Push toward 100 windows before comparing rule and sklearn baselines more seriously.")
    elif not payload["sklearn_baseline_ready"]:
        lines.append("- Label volume is strong enough, but the sklearn runtime is still blocked by environment availability or class diversity.")
    else:
        lines.append("- Label volume and runtime look ready for rule-baseline evaluation plus an sklearn baseline comparison.")

    lines.append("")
    return "\n".join(lines)


def summarize_validation_readiness(
    features_path: str | Path = DEFAULT_FEATURES_PATH,
    labels_path: str | Path = DEFAULT_LABELS_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    features_path = Path(features_path)
    labels_path = Path(labels_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = _readiness_payload(features_path=features_path, labels_path=labels_path)
    output_path.write_text(_build_markdown(payload), encoding="utf-8")
    payload["output_path"] = _relative_path(output_path)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize whether the current validation dataset is ready for baseline comparison.")
    parser.add_argument("--features", default=str(DEFAULT_FEATURES_PATH), help="Input state window feature CSV.")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS_PATH), help="Input state label CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output readiness markdown path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = summarize_validation_readiness(
        features_path=args.features,
        labels_path=args.labels,
        output_path=args.output,
    )
    print("\nValidation readiness")
    print(f"- Features: {summary['features_path']}")
    print(f"- Labels: {summary['labels_path']}")
    print(f"- Window feature rows: {summary['feature_windows']}")
    print(f"- Usable labeled windows: {summary['usable_label_rows']}")
    print(f"- Sklearn baseline ready: {summary['sklearn_baseline_ready']}")
    print(f"- Report: {summary['output_path']}")


if __name__ == "__main__":
    main()
