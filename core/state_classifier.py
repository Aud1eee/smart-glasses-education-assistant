from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


LABELS = [
    "stable_focus",
    "load_rising",
    "productive_struggle",
    "off_task_risk",
    "fatigue_risk",
    "signal_uncertain",
]

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC

    SKLEARN_AVAILABLE = True
    SKLEARN_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - availability is environment-specific
    RandomForestClassifier = None
    LogisticRegression = None
    SVC = None
    SKLEARN_AVAILABLE = False
    SKLEARN_IMPORT_ERROR = str(exc)

try:
    import joblib

    JOBLIB_AVAILABLE = True
    JOBLIB_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - availability is environment-specific
    joblib = None
    JOBLIB_AVAILABLE = False
    JOBLIB_IMPORT_ERROR = str(exc)


def _safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _value(row: dict[str, Any] | pd.Series, key: str) -> float | None:
    if isinstance(row, pd.Series):
        value = row.get(key)
    else:
        value = row.get(key)
    return _safe_float(value)


def _closeness(value: float | None, center: float, spread: float) -> float:
    if value is None or spread <= 0:
        return 0.0
    distance = abs(value - center)
    return max(0.0, 1.0 - min(1.0, distance / spread))


def _confidence_from_scores(scores: dict[str, float], coverage_ratio: float) -> float:
    ordered = sorted(scores.values(), reverse=True)
    top = ordered[0] if ordered else 0.0
    second = ordered[1] if len(ordered) > 1 else 0.0
    margin = max(0.0, top - second)
    confidence = 0.42 + min(0.42, margin / 22.0)
    confidence *= max(0.35, min(1.0, coverage_ratio))
    return round(max(0.08, min(0.96, confidence)), 3)


def _top_evidence(items: list[tuple[float, str]]) -> list[str]:
    evidence: list[str] = []
    for _, text in sorted(items, key=lambda item: item[0], reverse=True):
        if text and text not in evidence:
            evidence.append(text)
        if len(evidence) >= 3:
            break
    return evidence


def _uncertainty_reason(row: dict[str, Any] | pd.Series) -> str:
    uncertainty = _value(row, "uncertainty_score_mean")
    blur = _value(row, "blur_score_mean")
    brightness = _value(row, "brightness_score_mean")
    scene_content = _value(row, "scene_content_score_mean")
    if uncertainty is not None and uncertainty >= 60:
        if blur is not None and blur < 10:
            return "blur_score stayed low, so the scene signal remained uncertain."
        if brightness is not None and (brightness < 12 or brightness > 88):
            return "brightness looked abnormal, so the first-person scene proxy stayed uncertain."
        if scene_content is not None and scene_content < 18:
            return "scene content stayed sparse, so the proxy estimate should be treated conservatively."
        return "uncertainty stayed elevated across the window, so this remains a learning-state proxy estimate."
    return "No dominant uncertainty warning was found in this window."


def rule_baseline(row: dict[str, Any] | pd.Series) -> dict[str, Any]:
    alignment_mean = _value(row, "behavioral_alignment_mean")
    load_mean = _value(row, "cognitive_load_mean")
    scene_lock_mean = _value(row, "scene_lock_score_mean")
    uncertainty_mean = _value(row, "uncertainty_score_mean")
    load_slope = _value(row, "cognitive_load_slope")
    alignment_slope = _value(row, "behavioral_alignment_slope")
    focus_slope = _value(row, "focus_score_slope")
    scene_switch_mean = _value(row, "scene_switch_rate_mean")
    study_surface_mean = _value(row, "study_surface_score_mean")
    switching_mean = _value(row, "switching_index_mean")
    fatigue_mean = _value(row, "fatigue_risk_mean")
    stability_slope = _value(row, "stability_slope")
    motion_mean = _value(row, "motion_intensity_mean")
    drift_mean = _value(row, "combined_drift_mean")
    blur_mean = _value(row, "blur_score_mean")
    brightness_mean = _value(row, "brightness_score_mean")
    scene_content_mean = _value(row, "scene_content_score_mean")

    available_checks = [
        alignment_mean,
        load_mean,
        scene_lock_mean,
        uncertainty_mean,
        load_slope,
        alignment_slope,
        focus_slope,
        scene_switch_mean,
        study_surface_mean,
        switching_mean,
        fatigue_mean,
        stability_slope,
        motion_mean,
        drift_mean,
        blur_mean,
        brightness_mean,
        scene_content_mean,
    ]
    coverage_ratio = sum(value is not None for value in available_checks) / max(1, len(available_checks))

    stable_evidence = [
        ((alignment_mean or 0.0) * 0.34, "behavioral_alignment stayed high across the window"),
        ((max(0.0, 100.0 - (load_mean or 100.0))) * 0.20, "cognitive_load stayed low"),
        ((scene_lock_mean or 0.0) * 0.18, "scene_lock_score stayed relatively steady"),
        ((max(0.0, 100.0 - (uncertainty_mean or 100.0))) * 0.16, "uncertainty remained low"),
    ]
    stable_score = sum(weight for weight, _ in stable_evidence)

    load_rising_evidence = [
        ((max(0.0, load_slope or 0.0)) * 16.0, "cognitive_load increased over the window"),
        ((max(0.0, -(alignment_slope or 0.0))) * 14.0, "behavioral_alignment decreased"),
        ((max(0.0, -(focus_slope or 0.0))) * 12.0, "focus_score decreased"),
        (((load_mean or 0.0) * 0.18), "cognitive_load stayed above a steady baseline"),
    ]
    load_rising_score = sum(weight for weight, _ in load_rising_evidence)

    productive_evidence = [
        ((_closeness(load_mean, center=58.0, spread=22.0) * 24.0), "cognitive_load stayed in a mid-high challenge range"),
        (((alignment_mean or 0.0) * 0.28), "behavioral_alignment stayed relatively high"),
        (((scene_lock_mean or 0.0) * 0.18), "scene_lock_score stayed supportive"),
        ((max(0.0, 100.0 - (switching_mean or 100.0)) * 0.10), "switching stayed controlled despite the higher load"),
    ]
    productive_score = sum(weight for weight, _ in productive_evidence)

    off_task_evidence = [
        (((scene_switch_mean or 0.0) * 0.22), "scene_switch_rate stayed high"),
        ((max(0.0, 100.0 - (scene_lock_mean or 100.0)) * 0.18), "scene_lock_score remained low"),
        ((max(0.0, 100.0 - (study_surface_mean or 100.0)) * 0.16), "study_surface_score remained low"),
        (((switching_mean or 0.0) * 0.18), "switching_index stayed elevated"),
    ]
    off_task_score = sum(weight for weight, _ in off_task_evidence)

    fatigue_evidence = [
        (((fatigue_mean or 0.0) * 0.28), "fatigue_risk stayed elevated"),
        ((max(0.0, -(stability_slope or 0.0)) * 18.0), "stability trended downward"),
        ((max(0.0, 30.0 - (motion_mean or 30.0)) * 0.22), "motion_intensity stayed relatively low"),
        (((drift_mean or 0.0) * 0.10), "drift stayed present while fatigue remained elevated"),
    ]
    fatigue_score = sum(weight for weight, _ in fatigue_evidence)

    signal_evidence = [
        (((uncertainty_mean or 0.0) * 0.28), "uncertainty_score stayed high"),
        ((max(0.0, 15.0 - (blur_mean or 15.0)) * 0.90), "blur_score remained low"),
        ((max(0.0, 18.0 - (scene_content_mean or 18.0)) * 0.90), "scene_content_score stayed low"),
        (((max(0.0, 12.0 - (brightness_mean or 12.0)) + max(0.0, (brightness_mean or 0.0) - 88.0)) * 0.65), "brightness looked abnormal for part of the window"),
    ]
    signal_score = sum(weight for weight, _ in signal_evidence)

    scores = {
        "stable_focus": round(stable_score - max(0.0, signal_score * 0.25), 4),
        "load_rising": round(load_rising_score - max(0.0, signal_score * 0.12), 4),
        "productive_struggle": round(productive_score - max(0.0, off_task_score * 0.10), 4),
        "off_task_risk": round(off_task_score, 4),
        "fatigue_risk": round(fatigue_score, 4),
        "signal_uncertain": round(signal_score, 4),
    }

    label = max(scores, key=scores.get) if scores else "stable_focus"
    evidence_map = {
        "stable_focus": stable_evidence,
        "load_rising": load_rising_evidence,
        "productive_struggle": productive_evidence,
        "off_task_risk": off_task_evidence,
        "fatigue_risk": fatigue_evidence,
        "signal_uncertain": signal_evidence,
    }
    confidence = _confidence_from_scores(scores, coverage_ratio)
    return {
        "label": label,
        "confidence": confidence,
        "evidence": _top_evidence(evidence_map.get(label, [])),
        "uncertainty_reason": _uncertainty_reason(row),
        "model": "rule_baseline",
        "predicted_load_proxy": round(load_mean if load_mean is not None else 0.0, 4),
    }


def sklearn_status() -> dict[str, Any]:
    return {
        "sklearn_available": SKLEARN_AVAILABLE,
        "joblib_available": JOBLIB_AVAILABLE,
        "sklearn_error": SKLEARN_IMPORT_ERROR,
        "joblib_error": JOBLIB_IMPORT_ERROR,
    }


def _build_estimator(model_name: str):
    normalized = str(model_name or "LogisticRegression").strip().lower()
    if normalized in {"logisticregression", "logistic_regression", "logistic"}:
        return LogisticRegression(max_iter=2000, class_weight="balanced", random_state=7)
    if normalized in {"randomforestclassifier", "random_forest", "randomforest"}:
        return RandomForestClassifier(n_estimators=160, max_depth=8, random_state=7, class_weight="balanced")
    if normalized in {"svc", "svm"}:
        return SVC(probability=True, class_weight="balanced", random_state=7)
    raise ValueError(f"Unsupported sklearn baseline model: {model_name}")


def _feature_columns(frame: pd.DataFrame, label_column: str = "label") -> list[str]:
    ignore = {
        label_column,
        "session_id",
        "start_sample",
        "end_sample",
        "start_timestamp",
        "end_timestamp",
        "task_mode_majority",
        "state_hint_majority",
        "load_level_majority",
        "self_report_load",
        "self_report_attention",
        "self_report_fatigue",
        "task_difficulty",
        "quiz_score",
        "notes",
        "matched_overlap",
        "predicted_label",
        "predicted_confidence",
    }
    feature_names: list[str] = []
    for column in frame.columns:
        if column in ignore:
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            feature_names.append(column)
    return feature_names


def train_sklearn_baseline(
    frame: pd.DataFrame,
    label_column: str = "label",
    model_name: str = "LogisticRegression",
    model_path: str | Path = "exports/state_classifier_model.joblib",
) -> dict[str, Any]:
    if not SKLEARN_AVAILABLE:
        return {
            "status": "skipped",
            "reason": f"sklearn unavailable: {SKLEARN_IMPORT_ERROR}",
            "model_name": model_name,
        }

    if frame is None or frame.empty or label_column not in frame.columns:
        return {
            "status": "skipped",
            "reason": "No labeled training frame was provided.",
            "model_name": model_name,
        }

    labeled = frame.copy()
    labeled[label_column] = labeled[label_column].fillna("").astype(str).str.strip()
    labeled = labeled[labeled[label_column] != ""]
    if len(labeled.index) < 20 or labeled[label_column].nunique() < 2:
        return {
            "status": "skipped",
            "reason": "Not enough label diversity for sklearn training.",
            "model_name": model_name,
        }

    feature_names = _feature_columns(labeled, label_column=label_column)
    if not feature_names:
        return {
            "status": "skipped",
            "reason": "No numeric feature columns were available for sklearn training.",
            "model_name": model_name,
        }

    estimator = _build_estimator(model_name)
    X = labeled[feature_names].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    y = labeled[label_column].astype(str)
    estimator.fit(X, y)

    bundle = {
        "status": "trained",
        "model_name": type(estimator).__name__,
        "feature_names": feature_names,
        "labels": sorted(y.unique().tolist()),
        "estimator": estimator,
        "model_path": str(model_path),
    }

    if JOBLIB_AVAILABLE:
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model_name": bundle["model_name"],
            "feature_names": feature_names,
            "labels": bundle["labels"],
            "estimator": estimator,
        }, model_path)
    else:
        bundle["save_warning"] = f"joblib unavailable: {JOBLIB_IMPORT_ERROR}"

    return bundle


def predict_sklearn_baseline(model_bundle: dict[str, Any], frame: pd.DataFrame) -> list[dict[str, Any]]:
    if not model_bundle or model_bundle.get("status") != "trained":
        return []
    if frame is None or frame.empty:
        return []

    estimator = model_bundle["estimator"]
    feature_names = model_bundle.get("feature_names", [])
    if not feature_names:
        return []

    input_frame = frame.copy()
    for feature_name in feature_names:
        if feature_name not in input_frame.columns:
            input_frame[feature_name] = 0.0

    X = input_frame[feature_names].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    predictions = estimator.predict(X)
    if hasattr(estimator, "predict_proba"):
        probabilities = estimator.predict_proba(X)
        confidences = probabilities.max(axis=1).tolist()
    else:  # pragma: no cover - all configured models expose predict_proba
        confidences = [0.0] * len(predictions)

    output: list[dict[str, Any]] = []
    for label, confidence in zip(predictions.tolist(), confidences):
        output.append({
            "label": str(label),
            "confidence": round(float(confidence), 3),
            "evidence": [],
            "model": "sklearn_baseline",
        })
    return output
