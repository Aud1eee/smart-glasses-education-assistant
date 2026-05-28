from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

import pandas as pd

from core.state_classifier import LABELS, predict_sklearn_baseline, rule_baseline, sklearn_status, train_sklearn_baseline
from core.state_feature_extractor import DEFAULT_INPUT_PATH, extract_state_window_features

try:  # pragma: no cover - availability is environment-specific
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
    MATPLOTLIB_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - availability is environment-specific
    plt = None
    MATPLOTLIB_AVAILABLE = False
    MATPLOTLIB_IMPORT_ERROR = str(exc)


DEFAULT_FEATURES_PATH = ROOT / "data" / "state_window_features.csv"
DEFAULT_LABELS_TEMPLATE_PATH = ROOT / "data" / "state_labels_template.csv"
DEFAULT_LABELS_PATH = ROOT / "data" / "state_labels.csv"
DEFAULT_OUTPUT_DIR = ROOT / "exports"
DEFAULT_REPORT_PATH = DEFAULT_OUTPUT_DIR / "state_validation_report.md"
DEFAULT_METRICS_PATH = DEFAULT_OUTPUT_DIR / "state_validation_metrics.json"
DEFAULT_CONFUSION_PATH = DEFAULT_OUTPUT_DIR / "state_confusion_matrix.png"
DEFAULT_MODEL_PATH = DEFAULT_OUTPUT_DIR / "state_classifier_model.joblib"

LABEL_TEMPLATE_COLUMNS = [
    "session_id",
    "start_sample",
    "end_sample",
    "label",
    "self_report_load",
    "self_report_attention",
    "self_report_fatigue",
    "task_difficulty",
    "quiz_score",
    "notes",
]


def _safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def _ensure_label_template(template_path: Path) -> None:
    template_path.parent.mkdir(parents=True, exist_ok=True)
    if template_path.exists() and template_path.stat().st_size > 0:
        return
    pd.DataFrame(columns=LABEL_TEMPLATE_COLUMNS).to_csv(template_path, index=False)


def _ensure_labels_file(template_path: Path, labels_path: Path) -> None:
    _ensure_label_template(template_path)
    if labels_path.exists() and labels_path.stat().st_size > 0:
        return
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path, labels_path)


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size <= 0:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    return frame if not frame.empty else pd.DataFrame(columns=frame.columns.tolist())


def _extract_or_load_features(
    features_path: Path,
    source_path: Path,
    window_seconds: float,
    step_seconds: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    extraction_summary: dict[str, Any] | None = None
    if not features_path.exists() or features_path.stat().st_size <= 0:
        extraction_summary = extract_state_window_features(
            input_path=source_path,
            output_path=features_path,
            window_seconds=window_seconds,
            step_seconds=step_seconds,
        )
    features_frame = _load_csv(features_path)
    if extraction_summary is None:
        source_header = []
        if source_path.exists() and source_path.stat().st_size > 0:
            try:
                source_header = pd.read_csv(source_path, nrows=0).columns.tolist()
            except Exception:
                source_header = []
        missing_fields = [
            field for field in (
                "Session_ID",
                "Timestamp",
                "Sample_Index",
                "Task_Mode",
                "Relative_Pitch",
                "Relative_Yaw",
                "Relative_Roll",
                "Combined_Drift",
                "Motion_Intensity",
                "Stability",
                "Focus_Score",
                "Cognitive_Load",
                "Behavioral_Alignment",
                "Fatigue_Risk",
                "Uncertainty_Score",
                "Switching_Index",
                "Scene_Content_Score",
                "Scene_Text_Score",
                "Scene_Stability_Score",
                "Scene_Switch_Rate",
                "Study_Surface_Score",
                "Scene_Lock_Score",
                "Blur_Score",
                "Brightness_Score",
                "State_Hint",
                "Load_Level",
            )
            if field not in source_header
        ]
        extraction_summary = {
            "output_path": str(features_path),
            "rows": int(len(features_frame.index)),
            "sessions": int(features_frame["session_id"].nunique()) if "session_id" in features_frame.columns else 0,
            "missing_fields": missing_fields,
            "window_seconds": float(window_seconds),
            "step_seconds": float(step_seconds),
        }
    return features_frame, extraction_summary


def _normalize_labels(labels_frame: pd.DataFrame) -> pd.DataFrame:
    if labels_frame.empty:
        return pd.DataFrame(columns=LABEL_TEMPLATE_COLUMNS)
    normalized = labels_frame.copy()
    for column in LABEL_TEMPLATE_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = ""
    normalized["session_id"] = normalized["session_id"].fillna("").astype(str).str.strip()
    normalized["start_sample"] = normalized["start_sample"].apply(lambda value: _safe_int(value, default=0))
    normalized["end_sample"] = normalized["end_sample"].apply(lambda value: _safe_int(value, default=0))
    normalized["label"] = normalized["label"].fillna("").astype(str).str.strip()
    return normalized


def _window_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> int:
    return max(0, min(end_a, end_b) - max(start_a, start_b) + 1)


def _align_labels_to_windows(features_frame: pd.DataFrame, labels_frame: pd.DataFrame) -> pd.DataFrame:
    aligned = features_frame.copy()
    if aligned.empty:
        for column in LABEL_TEMPLATE_COLUMNS + ["matched_overlap"]:
            if column not in aligned.columns:
                aligned[column] = ""
        return aligned

    for column in LABEL_TEMPLATE_COLUMNS:
        if column not in aligned.columns:
            aligned[column] = ""
    aligned["matched_overlap"] = 0

    if labels_frame.empty:
        return aligned

    labels_by_session = {
        session_id: session_group.reset_index(drop=True)
        for session_id, session_group in labels_frame.groupby("session_id", sort=False)
    }
    resolved_rows: list[dict[str, Any]] = []
    for _, row in aligned.iterrows():
        session_id = str(row.get("session_id", "")).strip()
        start_sample = _safe_int(row.get("start_sample", 0), default=0)
        end_sample = _safe_int(row.get("end_sample", 0), default=start_sample)
        matched = None
        best_overlap = 0
        for _, label_row in labels_by_session.get(session_id, pd.DataFrame()).iterrows():
            overlap = _window_overlap(
                start_sample,
                end_sample,
                _safe_int(label_row.get("start_sample", 0), default=0),
                _safe_int(label_row.get("end_sample", 0), default=0),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                matched = label_row
        payload = row.to_dict()
        payload["matched_overlap"] = int(best_overlap)
        if matched is not None:
            for column in LABEL_TEMPLATE_COLUMNS:
                payload[column] = matched.get(column, "")
        resolved_rows.append(payload)
    return pd.DataFrame(resolved_rows)


def _apply_rule_baseline(aligned_frame: pd.DataFrame) -> pd.DataFrame:
    if aligned_frame.empty:
        return aligned_frame.copy()
    predicted_rows: list[dict[str, Any]] = []
    for _, row in aligned_frame.iterrows():
        prediction = rule_baseline(row)
        payload = row.to_dict()
        payload["predicted_label"] = prediction["label"]
        payload["predicted_confidence"] = prediction["confidence"]
        payload["predicted_evidence"] = json.dumps(prediction["evidence"], ensure_ascii=False)
        payload["predicted_model"] = prediction["model"]
        payload["predicted_load_proxy"] = prediction["predicted_load_proxy"]
        payload["uncertainty_reason"] = prediction["uncertainty_reason"]
        predicted_rows.append(payload)
    return pd.DataFrame(predicted_rows)


def _labeled_windows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "label" not in frame.columns:
        return pd.DataFrame(columns=frame.columns.tolist())
    labeled = frame.copy()
    labeled["label"] = labeled["label"].fillna("").astype(str).str.strip()
    labeled = labeled[labeled["label"].isin(LABELS)]
    return labeled.reset_index(drop=True)


def _split_train_test(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if frame.empty:
        return frame.copy(), frame.copy()
    train_parts = []
    test_parts = []
    for _, group in frame.groupby("label", sort=False):
        group = group.reset_index(drop=True)
        if len(group.index) < 4:
            train_parts.append(group)
            continue
        test_mask = [index % 5 == 0 for index in range(len(group.index))]
        test_group = group[test_mask]
        train_group = group[[not flag for flag in test_mask]]
        if test_group.empty:
            train_parts.append(group)
        else:
            train_parts.append(train_group)
            test_parts.append(test_group)
    train_frame = pd.concat(train_parts, ignore_index=True) if train_parts else pd.DataFrame(columns=frame.columns.tolist())
    test_frame = pd.concat(test_parts, ignore_index=True) if test_parts else pd.DataFrame(columns=frame.columns.tolist())
    return train_frame, test_frame


def _classification_metrics(true_labels: list[str], predicted_labels: list[str]) -> dict[str, Any]:
    if not true_labels:
        return {
            "accuracy": None,
            "macro_f1": None,
            "per_class_precision": {},
            "per_class_recall": {},
            "confusion_matrix": {},
            "label_count": 0,
        }

    label_order = [label for label in LABELS if label in set(true_labels) | set(predicted_labels)]
    confusion = {
        true_label: {pred_label: 0 for pred_label in label_order}
        for true_label in label_order
    }
    correct = 0
    for true_label, predicted_label in zip(true_labels, predicted_labels):
        if true_label == predicted_label:
            correct += 1
        if true_label not in confusion:
            confusion[true_label] = {pred_label: 0 for pred_label in label_order}
        if predicted_label not in confusion[true_label]:
            for row_label in confusion:
                confusion[row_label].setdefault(predicted_label, 0)
            if predicted_label not in label_order:
                label_order.append(predicted_label)
        confusion[true_label][predicted_label] += 1

    per_class_precision: dict[str, float] = {}
    per_class_recall: dict[str, float] = {}
    f1_scores: list[float] = []
    for label in label_order:
        tp = confusion.get(label, {}).get(label, 0)
        fp = sum(confusion.get(other_label, {}).get(label, 0) for other_label in label_order if other_label != label)
        fn = sum(confusion.get(label, {}).get(other_label, 0) for other_label in label_order if other_label != label)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class_precision[label] = round(precision, 4)
        per_class_recall[label] = round(recall, 4)
        f1_scores.append(f1)

    return {
        "accuracy": round(correct / len(true_labels), 4),
        "macro_f1": round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0.0,
        "per_class_precision": per_class_precision,
        "per_class_recall": per_class_recall,
        "confusion_matrix": confusion,
        "label_count": len(true_labels),
    }


def _pearson_correlation(values_a: list[float], values_b: list[float]) -> float | None:
    paired = [
        (float(a), float(b))
        for a, b in zip(values_a, values_b)
        if a is not None and b is not None and not math.isnan(float(a)) and not math.isnan(float(b))
    ]
    if len(paired) < 2:
        return None
    left = [pair[0] for pair in paired]
    right = [pair[1] for pair in paired]
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in paired)
    left_denom = math.sqrt(sum((a - left_mean) ** 2 for a in left))
    right_denom = math.sqrt(sum((b - right_mean) ** 2 for b in right))
    if left_denom <= 0 or right_denom <= 0:
        return None
    return round(numerator / (left_denom * right_denom), 4)


def _label_level_summary(predicted_frame: pd.DataFrame, labels_frame: pd.DataFrame) -> pd.DataFrame:
    if predicted_frame.empty or labels_frame.empty:
        return pd.DataFrame(columns=LABEL_TEMPLATE_COLUMNS)
    summaries: list[dict[str, Any]] = []
    for _, label_row in labels_frame.iterrows():
        session_id = str(label_row.get("session_id", "")).strip()
        label_start = _safe_int(label_row.get("start_sample", 0), default=0)
        label_end = _safe_int(label_row.get("end_sample", 0), default=0)
        session_windows = predicted_frame[predicted_frame["session_id"].astype(str) == session_id]
        if session_windows.empty:
            continue
        overlaps = session_windows.apply(
            lambda row: _window_overlap(
                _safe_int(row.get("start_sample", 0), default=0),
                _safe_int(row.get("end_sample", 0), default=0),
                label_start,
                label_end,
            ),
            axis=1,
        )
        matched = session_windows[overlaps > 0]
        if matched.empty:
            continue
        predicted_label = matched["predicted_label"].mode().iloc[0] if "predicted_label" in matched.columns and not matched["predicted_label"].mode().empty else ""
        summaries.append({
            "session_id": session_id,
            "label": str(label_row.get("label", "")).strip(),
            "predicted_label": predicted_label,
            "predicted_load_proxy": pd.to_numeric(matched.get("predicted_load_proxy"), errors="coerce").fillna(0).mean(),
            "focus_score_mean": pd.to_numeric(matched.get("focus_score_mean"), errors="coerce").fillna(0).mean(),
            "self_report_load": _safe_float(label_row.get("self_report_load")),
            "self_report_attention": _safe_float(label_row.get("self_report_attention")),
            "self_report_fatigue": _safe_float(label_row.get("self_report_fatigue")),
            "task_difficulty": _safe_float(label_row.get("task_difficulty")),
            "quiz_score": _safe_float(label_row.get("quiz_score")),
        })
    return pd.DataFrame(summaries)


def _recent_window_preview(predicted_frame: pd.DataFrame, limit: int = 8) -> list[dict[str, Any]]:
    if predicted_frame.empty:
        return []
    preview: list[dict[str, Any]] = []
    for _, row in predicted_frame.tail(limit).iterrows():
        preview.append({
            "session_id": str(row.get("session_id", "")),
            "start_sample": _safe_int(row.get("start_sample", 0), default=0),
            "end_sample": _safe_int(row.get("end_sample", 0), default=0),
            "predicted_label": str(row.get("predicted_label", "")),
            "confidence": round(_safe_float(row.get("predicted_confidence")) or 0.0, 3),
            "evidence": _safe_json_list(row.get("predicted_evidence")),
            "uncertainty_reason": str(row.get("uncertainty_reason", "")).strip(),
            "metrics": {
                "cognitive_load_mean": _safe_float(row.get("cognitive_load_mean")),
                "behavioral_alignment_mean": _safe_float(row.get("behavioral_alignment_mean")),
                "fatigue_risk_mean": _safe_float(row.get("fatigue_risk_mean")),
                "scene_lock_score_mean": _safe_float(row.get("scene_lock_score_mean")),
                "scene_switch_rate_mean": _safe_float(row.get("scene_switch_rate_mean")),
                "study_surface_score_mean": _safe_float(row.get("study_surface_score_mean")),
            },
        })
    return preview


def _safe_json_list(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return [text]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _render_confusion_matrix(confusion: dict[str, dict[str, int]], output_path: Path) -> str | None:
    if not MATPLOTLIB_AVAILABLE:
        return None
    labels = [label for label in LABELS if label in confusion]
    if not labels:
        return None
    matrix = []
    for true_label in labels:
        matrix.append([confusion.get(true_label, {}).get(pred_label, 0) for pred_label in labels])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted label")
    ax.set_ylabel("True label")
    ax.set_title("Learning-state proxy confusion matrix")

    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            ax.text(col_index, row_index, str(value), ha="center", va="center", color="#1f2937", fontsize=9)

    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return str(output_path)


def _build_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Learning-State Proxy Validation",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Features: `{payload['features_path']}`",
        f"- Labels: `{payload['labels_path']}`",
        f"- Windows: {payload['feature_rows']}",
        f"- Missing source fields: {', '.join(payload.get('missing_fields', [])) if payload.get('missing_fields') else 'none'}",
        "",
        "This report evaluates **learning-state proxy estimation**. It does not claim precise attention detection.",
        "",
        "## Rule Baseline",
        "",
    ]

    rule_metrics = payload.get("rule_baseline", {})
    if rule_metrics.get("accuracy") is None:
        lines.extend([
            "- No usable labels were aligned to the extracted windows yet.",
            "- Fill `data/state_labels.csv` to unlock accuracy, macro F1, and confusion-matrix outputs.",
            "",
        ])
    else:
        lines.extend([
            f"- Accuracy: `{rule_metrics.get('accuracy')}`",
            f"- Macro F1: `{rule_metrics.get('macro_f1')}`",
            "",
            "| Label | Precision | Recall |",
            "| --- | ---: | ---: |",
        ])
        for label in LABELS:
            if label not in rule_metrics.get("per_class_precision", {}):
                continue
            lines.append(
                f"| {label} | {rule_metrics['per_class_precision'][label]} | {rule_metrics['per_class_recall'][label]} |"
            )
        lines.append("")

    sklearn_metrics = payload.get("sklearn_baseline", {})
    lines.extend([
        "## Sklearn Baseline",
        "",
    ])
    if sklearn_metrics.get("status") != "trained":
        lines.append(f"- Status: `{sklearn_metrics.get('status', 'skipped')}`")
        lines.append(f"- Reason: {sklearn_metrics.get('reason', 'No additional detail provided.')}")
        lines.append("")
    else:
        lines.append(f"- Model: `{sklearn_metrics.get('model_name')}`")
        lines.append(f"- Accuracy: `{sklearn_metrics.get('accuracy')}`")
        lines.append(f"- Macro F1: `{sklearn_metrics.get('macro_f1')}`")
        if sklearn_metrics.get("model_path"):
            lines.append(f"- Saved model: `{sklearn_metrics.get('model_path')}`")
        lines.append("")

    correlations = payload.get("correlations", {})
    lines.extend([
        "## Self-Report Correlations",
        "",
        f"- predicted load proxy vs self_report_load: `{correlations.get('correlation_between_predicted_load_and_self_report_load')}`",
        f"- focus_score_mean vs self_report_attention: `{correlations.get('correlation_between_focus_score_and_self_report_attention')}`",
        "",
        "## Recent Window Preview",
        "",
    ])
    for item in payload.get("recent_rule_windows", []):
        lines.append(
            f"- {item['session_id']} samples {item['start_sample']}-{item['end_sample']}: "
            f"`{item['predicted_label']}` @ `{item['confidence']}`"
        )
        for evidence in item.get("evidence", []):
            lines.append(f"  - {evidence}")
    lines.append("")
    lines.extend([
        "## Notes",
        "",
        "- Missing source fields do not crash the pipeline; the extractor skips them and the classifier lowers confidence when key signals are unavailable.",
        "- Self-report labels are subjective and should be interpreted as supportive evidence, not ground truth in a strict biometric sense.",
        "- Without gaze, blink, or fixation signals, the current system remains a posture + first-person scene **proxy** estimator.",
    ])
    if not MATPLOTLIB_AVAILABLE:
        lines.append(f"- Confusion matrix image was skipped because matplotlib is unavailable: {MATPLOTLIB_IMPORT_ERROR}")
    if payload.get("labels_created"):
        lines.append("- `data/state_labels.csv` was created from the template because it did not exist before this run.")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate learning-state proxy windows against manual/self-report labels.")
    parser.add_argument("--features", default=str(DEFAULT_FEATURES_PATH), help="Window feature CSV path.")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS_PATH), help="State label CSV path.")
    parser.add_argument("--source", default=str(DEFAULT_INPUT_PATH), help="Source study report CSV path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for reports and confusion matrix outputs.")
    parser.add_argument("--window-seconds", type=float, default=10.0, help="Window size for auto extraction.")
    parser.add_argument("--step-seconds", type=float, default=5.0, help="Step size for auto extraction.")
    parser.add_argument("--sklearn-model", default="LogisticRegression", choices=["LogisticRegression", "RandomForestClassifier", "SVC"], help="Sklearn baseline model.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features_path = Path(args.features)
    labels_path = Path(args.labels)
    source_path = Path(args.source)
    output_dir = Path(args.output_dir)
    report_path = output_dir / DEFAULT_REPORT_PATH.name
    metrics_path = output_dir / DEFAULT_METRICS_PATH.name
    confusion_path = output_dir / DEFAULT_CONFUSION_PATH.name
    model_path = output_dir / DEFAULT_MODEL_PATH.name

    _ensure_label_template(DEFAULT_LABELS_TEMPLATE_PATH)
    labels_preexisting = labels_path.exists() and labels_path.stat().st_size > 0
    _ensure_labels_file(DEFAULT_LABELS_TEMPLATE_PATH, labels_path)

    features_frame, extraction_summary = _extract_or_load_features(
        features_path=features_path,
        source_path=source_path,
        window_seconds=args.window_seconds,
        step_seconds=args.step_seconds,
    )
    labels_frame = _normalize_labels(_load_csv(labels_path))
    aligned_frame = _align_labels_to_windows(features_frame, labels_frame)
    predicted_frame = _apply_rule_baseline(aligned_frame)
    labeled_windows = _labeled_windows(predicted_frame)

    rule_metrics = _classification_metrics(
        labeled_windows["label"].tolist() if not labeled_windows.empty else [],
        labeled_windows["predicted_label"].tolist() if not labeled_windows.empty else [],
    )

    train_frame, test_frame = _split_train_test(labeled_windows)
    sklearn_bundle = train_sklearn_baseline(
        train_frame,
        label_column="label",
        model_name=args.sklearn_model,
        model_path=model_path,
    ) if len(labeled_windows.index) >= 20 else {
        "status": "skipped",
        "reason": "Not enough labeled windows for sklearn training (need at least 20).",
        "model_name": args.sklearn_model,
    }
    sklearn_metrics = dict(sklearn_bundle)
    if sklearn_bundle.get("status") == "trained" and not test_frame.empty:
        sklearn_predictions = predict_sklearn_baseline(sklearn_bundle, test_frame)
        sklearn_metrics.update(
            _classification_metrics(
                test_frame["label"].tolist(),
                [item["label"] for item in sklearn_predictions],
            )
        )
    elif sklearn_bundle.get("status") == "trained" and test_frame.empty:
        sklearn_metrics.update({
            "status": "skipped",
            "reason": "No deterministic holdout set remained after the class-wise split.",
        })

    label_level_frame = _label_level_summary(predicted_frame, labels_frame)
    correlations = {
        "correlation_between_predicted_load_and_self_report_load": _pearson_correlation(
            label_level_frame["predicted_load_proxy"].tolist() if "predicted_load_proxy" in label_level_frame.columns else [],
            label_level_frame["self_report_load"].tolist() if "self_report_load" in label_level_frame.columns else [],
        ),
        "correlation_between_focus_score_and_self_report_attention": _pearson_correlation(
            label_level_frame["focus_score_mean"].tolist() if "focus_score_mean" in label_level_frame.columns else [],
            label_level_frame["self_report_attention"].tolist() if "self_report_attention" in label_level_frame.columns else [],
        ),
    }

    confusion_matrix_path = None
    if rule_metrics.get("confusion_matrix"):
        confusion_matrix_path = _render_confusion_matrix(rule_metrics["confusion_matrix"], confusion_path)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "features_path": str(features_path),
        "labels_path": str(labels_path),
        "feature_rows": int(len(features_frame.index)),
        "labeled_window_rows": int(len(labeled_windows.index)),
        "missing_fields": extraction_summary.get("missing_fields", []),
        "window_seconds": extraction_summary.get("window_seconds", args.window_seconds),
        "step_seconds": extraction_summary.get("step_seconds", args.step_seconds),
        "labels_created": not labels_preexisting,
        "rule_baseline": rule_metrics,
        "sklearn_baseline": sklearn_metrics,
        "correlations": correlations,
        "recent_rule_windows": _recent_window_preview(predicted_frame),
        "sklearn_environment": sklearn_status(),
        "matplotlib_available": MATPLOTLIB_AVAILABLE,
        "matplotlib_error": MATPLOTLIB_IMPORT_ERROR,
        "confusion_matrix_path": confusion_matrix_path or "",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_build_markdown_report(payload), encoding="utf-8")
    metrics_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nLearning-state proxy validation")
    print(f"- Features: {features_path}")
    print(f"- Labels: {labels_path}")
    print(f"- Feature windows: {len(features_frame.index)}")
    print(f"- Labeled windows: {len(labeled_windows.index)}")
    print(f"- Report: {report_path}")
    print(f"- Metrics: {metrics_path}")
    if confusion_matrix_path:
        print(f"- Confusion matrix: {confusion_matrix_path}")
    elif not MATPLOTLIB_AVAILABLE:
        print(f"- Confusion matrix skipped: matplotlib unavailable ({MATPLOTLIB_IMPORT_ERROR})")
    else:
        print("- Confusion matrix skipped: no labeled confusion data yet")


if __name__ == "__main__":
    main()
