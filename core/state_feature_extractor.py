from __future__ import annotations

import argparse
import math
from pathlib import Path
from collections.abc import Iterable
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = ROOT / "data" / "study_report.csv"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "state_window_features.csv"

EXPECTED_SOURCE_FIELDS = [
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
]

NUMERIC_FIELD_CANDIDATES = {
    "relative_pitch": ["Relative_Pitch", "relative_pitch"],
    "relative_yaw": ["Relative_Yaw", "relative_yaw"],
    "relative_roll": ["Relative_Roll", "relative_roll"],
    "combined_drift": ["Combined_Drift", "combined_drift"],
    "motion_intensity": ["Motion_Intensity", "Movement_Intensity", "motion_intensity", "movement_intensity"],
    "stability": ["Stability", "stability"],
    "focus_score": ["Focus_Score", "focus_score"],
    "cognitive_load": ["Cognitive_Load", "cognitive_load"],
    "behavioral_alignment": ["Behavioral_Alignment", "behavioral_alignment"],
    "fatigue_risk": ["Fatigue_Risk", "fatigue_risk"],
    "uncertainty_score": ["Uncertainty_Score", "uncertainty_score"],
    "switching_index": ["Switching_Index", "switching_index"],
    "scene_content_score": ["Scene_Content_Score", "scene_content_score"],
    "scene_text_score": ["Scene_Text_Score", "scene_text_score"],
    "scene_stability_score": ["Scene_Stability_Score", "scene_stability_score"],
    "scene_switch_rate": ["Scene_Switch_Rate", "scene_switch_rate"],
    "study_surface_score": ["Study_Surface_Score", "study_surface_score"],
    "scene_lock_score": ["Scene_Lock_Score", "scene_lock_score"],
    "blur_score": ["Blur_Score", "blur_score"],
    "brightness_score": ["Brightness_Score", "brightness_score"],
}

CATEGORICAL_FIELD_CANDIDATES = {
    "session_id": ["Session_ID", "session_id"],
    "timestamp": ["Timestamp", "timestamp"],
    "sample_index": ["Sample_Index", "sample_index"],
    "task_mode": ["Task_Mode", "task_mode"],
    "state_hint": ["State_Hint", "state_hint"],
    "load_level": ["Load_Level", "load_level"],
    "elapsed_seconds": ["Elapsed_Seconds", "elapsed_seconds"],
}

AGGREGATE_SUFFIXES = ("mean", "std", "min", "max", "range", "slope")


def _safe_float(value: Any) -> float | None:
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _parse_timestamp_to_seconds(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None

    numeric = _safe_float(text)
    if numeric is not None:
        return float(numeric)

    parts = text.split(":")
    if len(parts) == 3:
        hours = _safe_float(parts[0])
        minutes = _safe_float(parts[1])
        seconds = _safe_float(parts[2])
        if hours is None or minutes is None or seconds is None:
            return None
        return (hours * 3600.0) + (minutes * 60.0) + seconds
    if len(parts) == 2:
        minutes = _safe_float(parts[0])
        seconds = _safe_float(parts[1])
        if minutes is None or seconds is None:
            return None
        return (minutes * 60.0) + seconds
    return None


def _majority_value(series: pd.Series, default: str = "") -> str:
    if series is None:
        return default
    values = series.fillna("").astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return default
    modes = values.mode()
    if modes.empty:
        return default
    return str(modes.iloc[0])


def _ratio(values: Iterable[Any] | pd.Series | None, predicate) -> float:
    if values is None:
        return 0.0
    if isinstance(values, pd.Series):
        materialized = values.tolist()
    else:
        materialized = list(values)
    if not materialized:
        return 0.0
    total = len(materialized)
    if not total:
        return 0.0
    matches = sum(1 for value in materialized if predicate(value))
    return round(matches / total, 4)


def _series_stats(values: list[float], time_axis: list[float]) -> dict[str, float | str]:
    clean_pairs = [
        (time_axis[index], value)
        for index, value in enumerate(values)
        if value is not None and not math.isnan(value)
    ]
    if not clean_pairs:
        return {
            "mean": "",
            "std": "",
            "min": "",
            "max": "",
            "range": "",
            "slope": "",
        }

    clean_times = [pair[0] for pair in clean_pairs]
    clean_values = [pair[1] for pair in clean_pairs]
    count = len(clean_values)
    mean_value = sum(clean_values) / count
    variance = 0.0 if count <= 1 else sum((value - mean_value) ** 2 for value in clean_values) / count
    min_value = min(clean_values)
    max_value = max(clean_values)
    slope = _series_slope(clean_times, clean_values)
    return {
        "mean": round(mean_value, 4),
        "std": round(math.sqrt(max(0.0, variance)), 4),
        "min": round(min_value, 4),
        "max": round(max_value, 4),
        "range": round(max_value - min_value, 4),
        "slope": round(slope, 6),
    }


def _series_slope(time_axis: list[float], values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0

    first_time = time_axis[0]
    shifted = [time_value - first_time for time_value in time_axis]
    if max(shifted) == min(shifted):
        shifted = [float(index) for index, _ in enumerate(values)]

    x_mean = sum(shifted) / len(shifted)
    y_mean = sum(values) / len(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(shifted, values))
    denominator = sum((x - x_mean) ** 2 for x in shifted)
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _resolve_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    return None


def _load_source_frame(input_path: Path) -> pd.DataFrame:
    if not input_path.exists() or input_path.stat().st_size <= 0:
        return pd.DataFrame()
    try:
        frame = pd.read_csv(input_path)
    except Exception:
        return pd.DataFrame()
    return frame if not frame.empty else pd.DataFrame()


def _prepare_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    prepared = frame.copy()
    missing_fields: list[str] = []

    session_column = _resolve_column(prepared, CATEGORICAL_FIELD_CANDIDATES["session_id"])
    if session_column is None:
        prepared["Session_ID"] = "session-unknown"
        session_column = "Session_ID"
        missing_fields.append("Session_ID")
    prepared["__session_id"] = prepared[session_column].fillna("session-unknown").astype(str).str.strip().replace("", "session-unknown")

    sample_column = _resolve_column(prepared, CATEGORICAL_FIELD_CANDIDATES["sample_index"])
    if sample_column is None:
        prepared["__sample_index"] = prepared.groupby("__session_id").cumcount() + 1
        missing_fields.append("Sample_Index")
    else:
        numeric_sample = pd.to_numeric(prepared[sample_column], errors="coerce")
        if numeric_sample.isna().all():
            prepared["__sample_index"] = prepared.groupby("__session_id").cumcount() + 1
        else:
            fallback = prepared.groupby("__session_id").cumcount() + 1
            prepared["__sample_index"] = numeric_sample.fillna(fallback).astype(int)

    timestamp_column = _resolve_column(prepared, CATEGORICAL_FIELD_CANDIDATES["timestamp"])
    if timestamp_column is None:
        prepared["__timestamp_text"] = ""
        missing_fields.append("Timestamp")
    else:
        prepared["__timestamp_text"] = prepared[timestamp_column].fillna("").astype(str)

    elapsed_column = _resolve_column(prepared, CATEGORICAL_FIELD_CANDIDATES["elapsed_seconds"])
    if elapsed_column is not None:
        elapsed_numeric = pd.to_numeric(prepared[elapsed_column], errors="coerce")
    else:
        elapsed_numeric = pd.Series([None] * len(prepared.index))

    parsed_timestamp = prepared["__timestamp_text"].map(_parse_timestamp_to_seconds)
    time_axis = elapsed_numeric.where(~elapsed_numeric.isna(), parsed_timestamp)
    if time_axis.isna().all():
        time_axis = prepared["__sample_index"].astype(float) - 1.0
    prepared["__time_seconds"] = time_axis

    for canonical_name, candidates in NUMERIC_FIELD_CANDIDATES.items():
        column = _resolve_column(prepared, candidates)
        if column is None:
            prepared[f"__{canonical_name}"] = pd.Series([math.nan] * len(prepared.index))
            missing_fields.append(_preferred_field_name(candidates))
        else:
            prepared[f"__{canonical_name}"] = pd.to_numeric(prepared[column], errors="coerce")

    for canonical_name in ("task_mode", "state_hint", "load_level"):
        column = _resolve_column(prepared, CATEGORICAL_FIELD_CANDIDATES[canonical_name])
        if column is None:
            prepared[f"__{canonical_name}"] = ""
            missing_fields.append(_preferred_field_name(CATEGORICAL_FIELD_CANDIDATES[canonical_name]))
        else:
            prepared[f"__{canonical_name}"] = prepared[column].fillna("").astype(str).str.strip()

    return prepared, sorted(set(missing_fields))


def _preferred_field_name(candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate and candidate[0].isupper():
            return candidate
    return candidates[0]


def _build_window_record(session_frame: pd.DataFrame, window_frame: pd.DataFrame) -> dict[str, Any]:
    start_row = window_frame.iloc[0]
    end_row = window_frame.iloc[-1]
    time_axis = window_frame["__time_seconds"].ffill().bfill().fillna(0).astype(float).tolist()
    record: dict[str, Any] = {
        "session_id": str(start_row["__session_id"]),
        "start_sample": int(start_row["__sample_index"]),
        "end_sample": int(end_row["__sample_index"]),
        "start_timestamp": str(start_row["__timestamp_text"] or ""),
        "end_timestamp": str(end_row["__timestamp_text"] or ""),
        "task_mode_majority": _majority_value(window_frame["__task_mode"], default=""),
        "state_hint_majority": _majority_value(window_frame["__state_hint"], default=""),
        "load_level_majority": _majority_value(window_frame["__load_level"], default=""),
    }

    for canonical_name in NUMERIC_FIELD_CANDIDATES:
        values = window_frame[f"__{canonical_name}"].astype(float).tolist()
        stats = _series_stats(values, time_axis)
        for suffix in AGGREGATE_SUFFIXES:
            record[f"{canonical_name}_{suffix}"] = stats[suffix]

    load_level_series = window_frame["__load_level"].fillna("").astype(str).str.strip().str.lower()
    focus_series = window_frame["__focus_score"]
    state_hint_series = window_frame["__state_hint"].fillna("").astype(str).str.strip().str.lower()
    scene_lock_series = window_frame["__scene_lock_score"]
    scene_stability_series = window_frame["__scene_stability_score"]
    scene_switch_series = window_frame["__scene_switch_rate"]
    blur_series = window_frame["__blur_score"]
    brightness_series = window_frame["__brightness_score"]
    scene_content_series = window_frame["__scene_content_score"]
    motion_series = window_frame["__motion_intensity"]

    if (load_level_series != "").any():
        record["high_load_ratio"] = _ratio(load_level_series, lambda value: value == "high")
    else:
        record["high_load_ratio"] = _ratio(
            window_frame["__cognitive_load"],
            lambda value: _is_valid_number(value) and float(value) >= 70.0,
        )
    record["low_focus_ratio"] = _ratio(
        focus_series,
        lambda value: value is not None and not math.isnan(value) and value < 45.0,
    )
    record["off_task_hint_ratio"] = _ratio(state_hint_series, lambda value: value == "off_task_risk")
    record["productive_struggle_ratio"] = _ratio(state_hint_series, lambda value: value == "productive_struggle")
    record["signal_check_ratio"] = _ratio(
        state_hint_series,
        lambda value: value in {"signal_check", "signal_uncertain"},
    )
    record["scene_locked_ratio"] = _ratio(
        range(len(window_frame.index)),
        lambda index: (
            _is_valid_number(scene_lock_series.iloc[index]) and scene_lock_series.iloc[index] >= 60.0
            and _is_valid_number(scene_stability_series.iloc[index]) and scene_stability_series.iloc[index] >= 45.0
            and _is_valid_number(scene_switch_series.iloc[index]) and scene_switch_series.iloc[index] <= 35.0
        ),
    )
    record["unstable_scene_ratio"] = _ratio(
        range(len(window_frame.index)),
        lambda index: (
            (_is_valid_number(scene_stability_series.iloc[index]) and scene_stability_series.iloc[index] < 35.0)
            or (_is_valid_number(blur_series.iloc[index]) and blur_series.iloc[index] < 10.0)
            or (_is_valid_number(brightness_series.iloc[index]) and (brightness_series.iloc[index] < 12.0 or brightness_series.iloc[index] > 88.0))
            or (_is_valid_number(scene_content_series.iloc[index]) and scene_content_series.iloc[index] < 18.0)
            or (_is_valid_number(motion_series.iloc[index]) and motion_series.iloc[index] > 65.0)
        ),
    )
    return record


def _is_valid_number(value: Any) -> bool:
    try:
        return value is not None and not math.isnan(float(value))
    except Exception:
        return False


def _generate_session_windows(
    session_frame: pd.DataFrame,
    window_seconds: float,
    step_seconds: float,
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    if session_frame.empty:
        return windows

    time_min = float(session_frame["__time_seconds"].min())
    time_max = float(session_frame["__time_seconds"].max())
    start_time = time_min
    end_limit = max(time_min, time_max)
    epsilon = 1e-9

    while start_time <= end_limit + epsilon:
        end_time = start_time + window_seconds
        mask = (
            (session_frame["__time_seconds"] >= start_time)
            & (session_frame["__time_seconds"] <= end_time)
        )
        window_frame = session_frame.loc[mask]
        if not window_frame.empty:
            windows.append(_build_window_record(session_frame, window_frame))
        start_time += step_seconds

    if not windows:
        windows.append(_build_window_record(session_frame, session_frame))
    return windows


def extract_state_window_features(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    window_seconds: float = 10.0,
    step_seconds: float = 5.0,
) -> dict[str, Any]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_frame = _load_source_frame(input_path)
    if source_frame.empty:
        empty_columns = [
            "session_id",
            "start_sample",
            "end_sample",
            "start_timestamp",
            "end_timestamp",
            "task_mode_majority",
            "state_hint_majority",
            "load_level_majority",
        ]
        for canonical_name in NUMERIC_FIELD_CANDIDATES:
            for suffix in AGGREGATE_SUFFIXES:
                empty_columns.append(f"{canonical_name}_{suffix}")
        empty_columns.extend([
            "high_load_ratio",
            "low_focus_ratio",
            "off_task_hint_ratio",
            "productive_struggle_ratio",
            "signal_check_ratio",
            "scene_locked_ratio",
            "unstable_scene_ratio",
        ])
        pd.DataFrame(columns=empty_columns).to_csv(output_path, index=False)
        return {
            "output_path": str(output_path),
            "rows": 0,
            "sessions": 0,
            "missing_fields": EXPECTED_SOURCE_FIELDS[:],
            "window_seconds": float(window_seconds),
            "step_seconds": float(step_seconds),
        }

    prepared, missing_fields = _prepare_frame(source_frame)
    records: list[dict[str, Any]] = []
    for _, session_frame in prepared.groupby("__session_id", sort=False):
        session_frame = session_frame.sort_values(["__time_seconds", "__sample_index"], kind="stable").reset_index(drop=True)
        records.extend(_generate_session_windows(session_frame, window_seconds=window_seconds, step_seconds=step_seconds))

    features_frame = pd.DataFrame(records)
    features_frame.to_csv(output_path, index=False)
    return {
        "output_path": str(output_path),
        "rows": int(len(features_frame.index)),
        "sessions": int(prepared["__session_id"].nunique()),
        "missing_fields": missing_fields,
        "window_seconds": float(window_seconds),
        "step_seconds": float(step_seconds),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract 5s/10s-style learning-state proxy window features from study_report.csv.",
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Path to source study report CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Path for extracted window feature CSV.")
    parser.add_argument("--window-seconds", type=float, default=10.0, help="Sliding window size in seconds.")
    parser.add_argument("--step-seconds", type=float, default=5.0, help="Sliding step size in seconds.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = extract_state_window_features(
        input_path=args.input,
        output_path=args.output,
        window_seconds=args.window_seconds,
        step_seconds=args.step_seconds,
    )
    print("\nState window feature extraction")
    print(f"- Output: {summary['output_path']}")
    print(f"- Sessions: {summary['sessions']}")
    print(f"- Windows: {summary['rows']}")
    print(f"- Window / step: {summary['window_seconds']}s / {summary['step_seconds']}s")
    if summary["missing_fields"]:
        print(f"- Missing source fields: {', '.join(summary['missing_fields'])}")
    else:
        print("- Missing source fields: none")


if __name__ == "__main__":
    main()
