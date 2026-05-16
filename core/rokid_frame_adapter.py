import base64
import os
from dataclasses import asdict
from datetime import datetime
from typing import Any, Optional

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

from core.rokid_adapter import RokidInputPacket


class RokidFrameAdapter:
    """Build Rokid-style learning-state packets from first-person image frames.

    This adapter is intentionally conservative. It does not pretend to recover
    precise head pose or eye tracking from a monocular frame. Instead, it uses:

    - face presence
    - face-box center offsets
    - frame-to-frame displacement
    - scene change between frames

    to produce coarse posture proxies that can feed the existing
    Learning State Guardian pipeline.
    """

    def __init__(self):
        self.face_cascade = self._load_face_cascade()
        self.previous_face_center = None
        self.previous_face_area_ratio = None
        self.previous_preview = None
        self.last_pose = (0.0, 0.0, 0.0)

    def has_frame_payload(self, payload: dict[str, Any], image_bytes: Optional[bytes] = None) -> bool:
        return bool(
            image_bytes
            or payload.get("image_base64")
            or payload.get("frame_base64")
            or payload.get("image_path")
            or payload.get("frame_path")
        )

    def build_packet(
        self,
        payload: dict[str, Any],
        image_bytes: Optional[bytes] = None,
        default_task_mode: str = "reading",
    ) -> RokidInputPacket:
        timestamp = datetime.now()
        task_mode = self._normalize_task_mode(payload.get("task_mode"), default_task_mode)
        frame, frame_source = self._load_frame(payload, image_bytes=image_bytes)
        explicit_motion = self._as_float(payload.get("motion_intensity"))

        if frame is None:
            damped_pitch = self.last_pose[0] * 0.6
            damped_yaw = self.last_pose[1] * 0.6
            damped_roll = self.last_pose[2] * 0.6
            self.last_pose = (damped_pitch, damped_yaw, damped_roll)
            return RokidInputPacket(
                source="rokid_video_adapter",
                timestamp_text=timestamp.strftime("%H:%M:%S"),
                timestamp_ms=self._as_int(payload.get("timestamp_ms")),
                task_mode=task_mode,
                pitch=round(damped_pitch, 2),
                yaw=round(damped_yaw, 2),
                roll=round(damped_roll, 2),
                motion_intensity=explicit_motion or 0.0,
                tracking_state="frame_unavailable",
                tracking_confidence=0.08,
                tracking_uncertainty=76.0,
                face_present=False,
                device_profile="rokid-video-frame-proxy",
                motion_source="explicit" if explicit_motion is not None else "unavailable",
                pose_source="frame-proxy",
                frame_source=frame_source,
            )

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_h, frame_w = gray.shape[:2]
        scene_delta = self._compute_scene_delta(gray)
        face_box = self._detect_primary_face(gray)

        if face_box is None:
            damped_pitch = self.last_pose[0] * 0.72
            damped_yaw = self.last_pose[1] * 0.72
            damped_roll = self.last_pose[2] * 0.72
            motion = explicit_motion if explicit_motion is not None else min(100.0, scene_delta * 2.8)
            self.last_pose = (damped_pitch, damped_yaw, damped_roll)
            return RokidInputPacket(
                source="rokid_video_adapter",
                timestamp_text=timestamp.strftime("%H:%M:%S"),
                timestamp_ms=self._as_int(payload.get("timestamp_ms")),
                task_mode=task_mode,
                pitch=round(damped_pitch, 2),
                yaw=round(damped_yaw, 2),
                roll=round(damped_roll, 2),
                motion_intensity=round(motion, 1),
                tracking_state="face_missing",
                tracking_confidence=0.22,
                tracking_uncertainty=64.0,
                face_present=False,
                frame_width=frame_w,
                frame_height=frame_h,
                device_profile="rokid-video-frame-proxy",
                motion_source="explicit" if explicit_motion is not None else "scene-delta",
                pose_source="frame-proxy",
                frame_source=frame_source,
            )

        x, y, w, h = face_box
        center_x = x + (w / 2.0)
        center_y = y + (h / 2.0)
        normalized_x = ((center_x / max(frame_w, 1)) - 0.5) * 2.0
        normalized_y = ((center_y / max(frame_h, 1)) - 0.5) * 2.0
        face_ratio = (w * h) / max(frame_w * frame_h, 1)
        face_aspect = w / max(h, 1)

        pitch = self._clamp(normalized_y * 24.0, -28.0, 28.0)
        yaw = self._clamp(normalized_x * 18.0, -24.0, 24.0)
        roll = self._clamp((face_aspect - 0.78) * 18.0, -10.0, 10.0)
        motion = explicit_motion if explicit_motion is not None else self._compute_motion_intensity(
            face_center=(center_x, center_y),
            face_area_ratio=face_ratio,
            frame_shape=(frame_w, frame_h),
            scene_delta=scene_delta,
        )

        center_offset = (abs(normalized_x) + abs(normalized_y)) / 2.0
        tracking_confidence = self._clamp(0.94 - (center_offset * 0.38) + min(face_ratio * 2.5, 0.12), 0.35, 0.98)
        tracking_uncertainty = round(self._clamp((1.0 - tracking_confidence) * 55.0, 6.0, 48.0), 1)

        self.previous_face_center = (center_x, center_y)
        self.previous_face_area_ratio = face_ratio
        self.last_pose = (pitch, yaw, roll)

        return RokidInputPacket(
            source="rokid_video_adapter",
            timestamp_text=timestamp.strftime("%H:%M:%S"),
            timestamp_ms=self._as_int(payload.get("timestamp_ms")),
            task_mode=task_mode,
            pitch=round(pitch, 2),
            yaw=round(yaw, 2),
            roll=round(roll, 2),
            motion_intensity=round(float(motion), 1),
            tracking_state="tracked",
            tracking_confidence=round(float(tracking_confidence), 2),
            tracking_uncertainty=tracking_uncertainty,
            face_present=True,
            frame_width=frame_w,
            frame_height=frame_h,
            device_profile="rokid-video-frame-proxy",
            motion_source="explicit" if explicit_motion is not None else "frame-derived",
            pose_source="frame-proxy",
            frame_source=frame_source,
        )

    def blueprint(self):
        sample_packet = RokidInputPacket(
            source="rokid_video_adapter",
            timestamp_text="12:00:00",
            timestamp_ms=1730000000000,
            task_mode="reading",
            pitch=4.8,
            yaw=-2.4,
            roll=0.0,
            motion_intensity=18.0,
            tracking_state="tracked",
            tracking_confidence=0.86,
            tracking_uncertainty=12.0,
            face_present=True,
            frame_width=1280,
            frame_height=720,
            device_profile="rokid-video-frame-proxy",
            motion_source="frame-derived",
            pose_source="frame-proxy",
            frame_source="base64",
        )
        return {
            "adapter_name": "rokid-video-frame-adapter",
            "active_endpoint": "/api/v1/rokid/frame",
            "input_options": ["multipart file `frame`", "JSON `image_base64`", "JSON `image_path`"],
            "derived_signals": [
                "face_present",
                "tracking_confidence",
                "frame-derived pitch proxy",
                "frame-derived yaw proxy",
                "coarse roll proxy",
                "motion_intensity from frame delta",
            ],
            "normalized_packet": asdict(sample_packet),
            "limits": [
                "coarse posture proxy only",
                "not a precise IMU replacement",
                "does not provide precise gaze target or pupil signals",
            ],
        }

    def _load_face_cascade(self):
        if cv2 is None:
            return None
        cascade_path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        if not os.path.exists(cascade_path):
            return None
        classifier = cv2.CascadeClassifier(cascade_path)
        if classifier.empty():
            return None
        return classifier

    def _load_frame(self, payload: dict[str, Any], image_bytes: Optional[bytes] = None):
        if cv2 is None or np is None:
            return None, "opencv-unavailable"

        if image_bytes:
            frame = self._decode_image_bytes(image_bytes)
            return frame, "upload"

        image_base64 = payload.get("image_base64") or payload.get("frame_base64")
        if image_base64:
            frame = self._decode_base64_image(str(image_base64))
            return frame, "base64"

        image_path = payload.get("image_path") or payload.get("frame_path")
        if image_path:
            try:
                frame = cv2.imread(str(image_path))
            except Exception:
                frame = None
            return frame, "path"

        return None, "missing"

    def _detect_primary_face(self, gray):
        if self.face_cascade is None:
            return None
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if faces is None or len(faces) == 0:
            return None
        return max(faces, key=lambda box: box[2] * box[3])

    def _decode_image_bytes(self, image_bytes: bytes):
        if not image_bytes or cv2 is None or np is None:
            return None
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        return cv2.imdecode(array, cv2.IMREAD_COLOR)

    def _decode_base64_image(self, payload_text: str):
        try:
            cleaned = payload_text.split(",", 1)[-1]
            raw = base64.b64decode(cleaned)
        except Exception:
            return None
        return self._decode_image_bytes(raw)

    def _compute_scene_delta(self, gray):
        if cv2 is None:
            return 0.0
        preview = cv2.resize(gray, (160, 90))
        delta = 0.0
        if self.previous_preview is not None:
            diff = cv2.absdiff(preview, self.previous_preview)
            delta = float(np.mean(diff))
        self.previous_preview = preview
        return delta

    def _compute_motion_intensity(self, face_center, face_area_ratio, frame_shape, scene_delta):
        frame_w, frame_h = frame_shape
        center_motion = 0.0
        size_motion = 0.0
        if self.previous_face_center is not None:
            dx = (face_center[0] - self.previous_face_center[0]) / max(frame_w, 1)
            dy = (face_center[1] - self.previous_face_center[1]) / max(frame_h, 1)
            center_motion = min(1.0, (dx * dx + dy * dy) ** 0.5 * 3.6)
        if self.previous_face_area_ratio is not None:
            size_motion = min(1.0, abs(face_area_ratio - self.previous_face_area_ratio) * 24.0)
        scene_component = min(1.0, scene_delta / 34.0)
        return round(self._clamp((center_motion * 46.0) + (size_motion * 24.0) + (scene_component * 18.0)), 1)

    def _normalize_task_mode(self, task_mode: Any, default_task_mode: str) -> str:
        candidate = str(task_mode or "").strip().lower()
        if candidate in {"lecture", "reading", "note-taking", "review"}:
            return candidate
        return default_task_mode

    def _as_float(self, value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except Exception:
            return None

    def _as_int(self, value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(float(value))
        except Exception:
            return None

    def _clamp(self, value: float, low: float = 0.0, high: float = 100.0) -> float:
        return max(low, min(high, float(value)))
