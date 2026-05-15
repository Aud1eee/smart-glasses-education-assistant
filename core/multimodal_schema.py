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
        "current_stage": "phase-1 posture proxy",
        "current_active_signals": [
            "pitch",
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
                "current_signals": ["pitch", "variance", "stability", "task_mode"],
                "future_signals": ["yaw", "roll", "gaze_target", "face_presence"],
            },
            {
                "name": "cognitive_effort",
                "status": "proxy-active",
                "current_signals": ["drift", "variance", "alignment_cost"],
                "future_signals": ["pupil_feature", "blink_rate", "fixation_dwell", "reread_pattern"],
            },
            {
                "name": "fatigue_risk",
                "status": "active",
                "current_signals": ["passive_drift", "low_motion_window", "sustained_slump"],
                "future_signals": ["eye_openness", "blink_duration_ms", "perclos"],
            },
            {
                "name": "confidence",
                "status": "active",
                "current_signals": ["warmup_window", "variance_spike", "mode_transition"],
                "future_signals": ["face_confidence", "gaze_confidence", "tracking_quality"],
            },
        ],
        "planned_modalities": {
            "imu": asdict(packet.imu),
            "face": asdict(packet.face),
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
            "rokid_adapter": "planned",
            "face_landmarker": "planned",
            "eye_features": "planned",
        },
        "recommended_rollout": [
            "phase-1: posture proxy with task-mode awareness",
            "phase-2: face presence, gaze proxy, eye openness hooks",
            "phase-3: pupil feature, blink and perclos-supported fusion",
        ],
    }
