from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class IMUSignals:
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    accel_magnitude: Optional[float] = None
    gyro_magnitude: Optional[float] = None


@dataclass
class FaceSignals:
    face_present: bool = False
    face_confidence: Optional[float] = None
    gaze_target: str = "unknown"
    gaze_confidence: Optional[float] = None
    eye_openness_left: Optional[float] = None
    eye_openness_right: Optional[float] = None
    blink_rate: Optional[float] = None
    blink_duration_ms: Optional[float] = None
    perclos: Optional[float] = None
    pupil_feature: Optional[float] = None


@dataclass
class MultimodalPacket:
    session_id: str = ""
    timestamp: str = ""
    task_mode: str = "reading"
    imu: IMUSignals = field(default_factory=IMUSignals)
    face: FaceSignals = field(default_factory=FaceSignals)


def build_multimodal_blueprint():
    """Describe the planned multimodal learning-state architecture.

    This is intentionally lightweight: it gives the current system a concrete
    extension contract without forcing unfinished device-side work into the
    active scoring path.
    """

    packet = MultimodalPacket()
    return {
        "current_stage": "phase-1 rokid posture proxy",
        "current_active_signals": [
            "pitch",
            "yaw",
            "roll",
            "movement_intensity",
            "task_mode",
            "stability",
            "behavioral_alignment",
            "cognitive_load",
            "fatigue_risk",
            "uncertainty_score",
        ],
        "fusion_branches": [
            {
                "name": "behavioral_alignment",
                "status": "active",
                "current_signals": ["pitch", "yaw", "roll", "variance", "stability", "task_mode"],
                "future_signals": ["scene_target_proxy", "capture_intent", "device_mode"],
            },
            {
                "name": "cognitive_effort",
                "status": "proxy-active",
                "current_signals": ["drift", "variance", "alignment_cost", "switching_index", "drift_trend"],
                "future_signals": ["scene_change_rate", "revisit_pattern", "manual_checkpoint"],
            },
            {
                "name": "fatigue_risk",
                "status": "active",
                "current_signals": ["passive_drift", "low_motion_window", "sustained_slump", "movement_intensity"],
                "future_signals": ["optional_eye_openness", "optional_blink_proxy", "session_break_context"],
            },
            {
                "name": "confidence",
                "status": "active",
                "current_signals": ["warmup_window", "variance_spike", "mode_transition"],
                "future_signals": ["tracking_quality", "adapter_timestamp_skew", "imu_packet_health"],
            },
        ],
        "planned_modalities": {
            "imu": asdict(packet.imu),
            "vision_context": {
                "scene_change_rate": None,
                "capture_intent": False,
                "device_mode": "reading",
                "manual_checkpoint": False,
            },
        },
        "future_states": [
            "Deep Focus",
            "Productive Struggle",
            "Off-Task Risk",
            "Fatigue Risk",
            "Uncertain",
        ],
        "device_readiness": {
            "simulator": "active",
            "rokid_adapter": "active",
            "rokid_video_frame_adapter": "active",
            "face_landmarker": "optional-future",
            "eye_features": "planned",
        },
        "rokid_constraints": [
            "active logic assumes Rokid-realistic head pose and IMU signals first",
            "precise gaze target, pupil dilation, and PERCLOS are not required in the current design",
            "task mode and app-side context remain first-class inputs because device-side eye tracking may be unavailable",
        ],
        "recommended_rollout": [
            "phase-1: head pose and movement proxy with task-mode awareness",
            "phase-2: Rokid frame adapter + scene/context hooks from app-side camera or UI events",
            "phase-3: optional vision-assisted features only if device access is available and stable",
        ],
    }
