from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class RokidInputPacket:
    source: str
    timestamp_text: str
    timestamp_ms: Optional[int]
    task_mode: str
    pitch: float
    yaw: float
    roll: float
    motion_intensity: float
    accel_magnitude: Optional[float] = None
    gyro_magnitude: Optional[float] = None
    tracking_state: str = "tracked"
    tracking_confidence: Optional[float] = None
    tracking_uncertainty: float = 0.0
    face_present: Optional[bool] = None
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    scene_content_score: Optional[float] = None
    scene_text_score: Optional[float] = None
    scene_stability_score: Optional[float] = None
    scene_switch_rate: Optional[float] = None
    study_surface_score: Optional[float] = None
    scene_lock_score: Optional[float] = None
    blur_score: Optional[float] = None
    brightness_score: Optional[float] = None
    device_profile: str = "rokid-imu-3dof"
    motion_source: str = "explicit"
    pose_source: str = "telemetry"
    frame_source: str = "telemetry"
    source_mode: str = "imu_only"
    has_pose: bool = True
    has_imu: bool = False
    pose_reliability: str = "measured"
    valid_frame_streak: int = 0
    valid_frame_seconds: float = 0.0
    missing_signals: list[str] = field(default_factory=list)
    rokid_compatible_mode: bool = False


def build_simulator_packet(payload: dict[str, Any], default_task_mode: str = "reading") -> RokidInputPacket:
    timestamp = datetime.now()
    explicit_motion = _as_float(payload.get("motion_intensity"))
    accel_mag = _as_float(_pick(payload, "accel_magnitude", "imu.accel_magnitude"))
    gyro_mag = _as_float(_pick(payload, "gyro_magnitude", "imu.gyro_magnitude"))
    motion_intensity, motion_source = _resolve_motion_intensity(explicit_motion, accel_mag, gyro_mag)
    has_imu = accel_mag is not None or gyro_mag is not None
    return RokidInputPacket(
        source="simulator",
        timestamp_text=timestamp.strftime("%H:%M:%S"),
        timestamp_ms=None,
        task_mode=_normalize_task_mode(payload.get("task_mode"), default_task_mode),
        pitch=_as_float(_pick(payload, "pitch", "head_pitch")),
        yaw=_as_float(_pick(payload, "yaw", "head_yaw")),
        roll=_as_float(_pick(payload, "roll", "head_roll")),
        motion_intensity=motion_intensity,
        accel_magnitude=accel_mag,
        gyro_magnitude=gyro_mag,
        tracking_state="simulated",
        tracking_confidence=1.0,
        tracking_uncertainty=0.0,
        face_present=None,
        device_profile="simulator-rokid-proxy",
        motion_source=motion_source,
        pose_source="simulator",
        frame_source="simulator",
        source_mode="hybrid" if has_imu else "imu_only",
        has_pose=True,
        has_imu=has_imu,
        pose_reliability="measured",
        missing_signals=[],
        rokid_compatible_mode=False,
    )


def build_rokid_packet(payload: dict[str, Any], default_task_mode: str = "reading") -> RokidInputPacket:
    timestamp = datetime.now()
    timestamp_ms = _as_int(_pick(payload, "timestamp_ms", "sensor_timestamp_ms", "imu.timestamp_ms"))
    pitch = _as_float(_pick(payload, "pitch", "head_pitch", "imu.pitch", "orientation.pitch"))
    yaw = _as_float(_pick(payload, "yaw", "head_yaw", "imu.yaw", "orientation.yaw"))
    roll = _as_float(_pick(payload, "roll", "head_roll", "imu.roll", "orientation.roll"))
    accel_mag = _as_float(
        _pick(
            payload,
            "accel_magnitude",
            "imu.accel_magnitude",
            "imu.accelMagnitude",
            "motion.accel_magnitude",
        )
    )
    gyro_mag = _as_float(
        _pick(
            payload,
            "gyro_magnitude",
            "imu.gyro_magnitude",
            "imu.gyroMagnitude",
            "motion.gyro_magnitude",
        )
    )
    explicit_motion = _as_float(_pick(payload, "motion_intensity", "motion.movement_intensity"))
    motion_intensity, motion_source = _resolve_motion_intensity(explicit_motion, accel_mag, gyro_mag)
    has_pose = any(value is not None for value in (pitch, yaw, roll))
    has_imu = accel_mag is not None or gyro_mag is not None
    tracking_state = str(
        _pick(payload, "tracking_state", "tracking.mode", "tracking_mode", "tracking_3dof")
        or "tracked"
    ).strip() or "tracked"
    return RokidInputPacket(
        source="rokid_adapter",
        timestamp_text=timestamp.strftime("%H:%M:%S"),
        timestamp_ms=timestamp_ms,
        task_mode=_normalize_task_mode(_pick(payload, "task_mode", "context.task_mode"), default_task_mode),
        pitch=pitch,
        yaw=yaw,
        roll=roll,
        motion_intensity=motion_intensity,
        accel_magnitude=accel_mag,
        gyro_magnitude=gyro_mag,
        tracking_state=tracking_state,
        tracking_confidence=0.92 if tracking_state == "tracked" else 0.45,
        tracking_uncertainty=12.0 if tracking_state == "tracked" else 42.0,
        face_present=None,
        device_profile=str(_pick(payload, "device_profile", "device.model") or "rokid-imu-3dof"),
        motion_source=motion_source,
        pose_source="imu-packet",
        frame_source="telemetry",
        source_mode="hybrid" if has_pose and has_imu else "imu_only",
        has_pose=has_pose,
        has_imu=has_imu,
        pose_reliability="measured" if has_pose else "missing",
        missing_signals=_build_missing_signals(
            has_pose=has_pose,
            has_imu=has_imu,
            motion_source=motion_source,
            pose_reliability="measured" if has_pose else "missing",
        ),
        rokid_compatible_mode=False,
    )


def build_rokid_adapter_blueprint():
    packet = RokidInputPacket(
        source="rokid_adapter",
        timestamp_text="12:00:00",
        timestamp_ms=1730000000000,
        task_mode="reading",
        pitch=0.0,
        yaw=0.0,
        roll=0.0,
        motion_intensity=0.0,
        accel_magnitude=1.0,
        gyro_magnitude=0.0,
    )
    return {
        "adapter_name": "rokid-head-pose-adapter",
        "design_target": "Rokid-style 3DOF / 9-axis IMU learning-state input",
        "active_endpoint": "/api/v1/rokid/head-pose",
        "video_frame_endpoint": "/api/v1/rokid/frame",
        "simulator_endpoint": "/api/v1/posture",
        "required_runtime_signals": ["pitch", "yaw", "roll"],
        "optional_runtime_signals": ["motion_intensity", "accel_magnitude", "gyro_magnitude", "timestamp_ms", "task_mode"],
        "normalized_packet": asdict(packet),
        "field_aliases": {
            "pitch": ["pitch", "head_pitch", "imu.pitch", "orientation.pitch"],
            "yaw": ["yaw", "head_yaw", "imu.yaw", "orientation.yaw"],
            "roll": ["roll", "head_roll", "imu.roll", "orientation.roll"],
            "motion_intensity": ["motion_intensity", "motion.movement_intensity"],
            "accel_magnitude": ["accel_magnitude", "imu.accel_magnitude", "imu.accelMagnitude"],
            "gyro_magnitude": ["gyro_magnitude", "imu.gyro_magnitude", "imu.gyroMagnitude"],
        },
        "design_constraints": [
            "optimized for head pose and IMU signals that are realistic on Rokid-style glasses",
            "does not require gaze target, pupil dilation, or PERCLOS in the active scoring path",
            "keeps task mode as app context instead of assuming rich eye-tracking telemetry",
        ],
    }


def _resolve_motion_intensity(
    explicit_motion: Optional[float],
    accel_magnitude: Optional[float],
    gyro_magnitude: Optional[float],
):
    if explicit_motion is not None:
        return _clamp(explicit_motion), "explicit"

    accel_component = 0.0
    if accel_magnitude is not None:
        gravity_offset = max(0.0, abs(accel_magnitude) - 1.0)
        accel_component = _clamp(gravity_offset * 55.0)

    gyro_component = 0.0
    if gyro_magnitude is not None:
        gyro_component = _clamp(abs(gyro_magnitude) * 1.2)

    if accel_magnitude is None and gyro_magnitude is None:
        return 0.0, "default"
    if accel_magnitude is None:
        return round(gyro_component, 1), "gyro-derived"
    if gyro_magnitude is None:
        return round(accel_component, 1), "accel-derived"
    return round(_clamp((accel_component * 0.42) + (gyro_component * 0.58)), 1), "imu-derived"


def _normalize_task_mode(task_mode: Any, default_task_mode: str) -> str:
    candidate = str(task_mode or "").strip().lower()
    if candidate in {"lecture", "reading", "note-taking", "review"}:
        return candidate
    return default_task_mode


def _pick(payload: dict[str, Any], *paths: str):
    for path in paths:
        current: Any = payload
        found = True
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                found = False
                break
        if found and current is not None:
            return current
    return None


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except Exception:
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _build_missing_signals(
    has_pose: bool,
    has_imu: bool,
    motion_source: str,
    pose_reliability: str,
) -> list[str]:
    missing = []
    if pose_reliability == "missing" or not has_pose:
        missing.append("pose")
    if not has_imu:
        missing.append("imu")
    if motion_source in {"default", "unavailable", "scene-derived"}:
        missing.append("motion")
    return missing
