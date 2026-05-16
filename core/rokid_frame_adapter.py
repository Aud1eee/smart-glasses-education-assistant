import base64
from dataclasses import asdict
from datetime import datetime
import os
from typing import Any, Optional

try:
    import cv2
    import numpy as np
except Exception:
    cv2 = None
    np = None

from core.rokid_adapter import RokidInputPacket


class RokidFrameAdapter:
    """Build Rokid-style packets from first-person frames using scene cues.

    This adapter is designed for outward-facing smart-glasses video where the
    wearer does not appear in the scene. It therefore relies on:

    - scene motion / frame delta
    - content density and scene-text richness
    - blur and brightness quality
    - anchor stability across frames

    instead of assuming face-based head-pose recovery.
    """

    def __init__(self):
        self.previous_preview = None
        self.previous_hist = None
        self.previous_anchor = None
        self.previous_content_score = None
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
            damped_pitch, damped_yaw, damped_roll = self._decay_last_pose(0.62)
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
                tracking_uncertainty=78.0,
                face_present=None,
                scene_content_score=0.0,
                scene_text_score=0.0,
                scene_stability_score=0.0,
                scene_switch_rate=0.0,
                blur_score=0.0,
                brightness_score=0.0,
                device_profile="rokid-video-scene-proxy",
                motion_source="explicit" if explicit_motion is not None else "unavailable",
                pose_source="scene-proxy",
                frame_source=frame_source,
            )

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_h, frame_w = gray.shape[:2]
        preview = cv2.resize(gray, (160, 90))
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 60, 160)

        blur_score = self._compute_blur_score(gray)
        brightness_score = self._compute_brightness_score(gray)
        contrast_score = self._compute_contrast_score(gray)
        feature_score = self._compute_feature_score(gray)
        text_score = self._compute_text_score(edges, feature_score, contrast_score)
        content_score = self._compute_content_score(text_score, feature_score, blur_score, contrast_score)
        anchor = self._compute_anchor(edges, gray)
        scene_delta = self._compute_scene_delta(preview)
        histogram_delta = self._compute_histogram_delta(gray)
        anchor_shift = self._compute_anchor_shift(anchor, frame_shape=(frame_w, frame_h))
        scene_switch_rate = self._compute_scene_switch_rate(
            anchor_shift=anchor_shift,
            histogram_delta=histogram_delta,
            content_score=content_score,
            text_score=text_score,
        )
        motion = explicit_motion if explicit_motion is not None else self._compute_motion_intensity(
            scene_delta=scene_delta,
            histogram_delta=histogram_delta,
            anchor_shift=anchor_shift,
        )
        scene_stability = self._compute_scene_stability(
            motion=motion,
            scene_switch_rate=scene_switch_rate,
            content_score=content_score,
            blur_score=blur_score,
        )
        tracking_confidence = self._compute_tracking_confidence(
            blur_score=blur_score,
            brightness_score=brightness_score,
            content_score=content_score,
            scene_stability=scene_stability,
        )
        tracking_uncertainty = self._compute_tracking_uncertainty(
            blur_score=blur_score,
            brightness_score=brightness_score,
            content_score=content_score,
            scene_stability=scene_stability,
            scene_switch_rate=scene_switch_rate,
            tracking_confidence=tracking_confidence,
        )

        pitch, yaw, roll = self._derive_scene_pose(
            anchor=anchor,
            frame_shape=(frame_w, frame_h),
            edges=edges,
            scene_stability=scene_stability,
        )
        tracking_state = self._classify_tracking_state(
            blur_score=blur_score,
            brightness_score=brightness_score,
            content_score=content_score,
            scene_stability=scene_stability,
            scene_switch_rate=scene_switch_rate,
        )

        self.previous_preview = preview
        self.previous_hist = self._compute_histogram(gray)
        self.previous_anchor = anchor
        self.previous_content_score = content_score
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
            tracking_state=tracking_state,
            tracking_confidence=round(float(tracking_confidence), 2),
            tracking_uncertainty=round(float(tracking_uncertainty), 1),
            face_present=None,
            frame_width=frame_w,
            frame_height=frame_h,
            scene_content_score=round(float(content_score), 1),
            scene_text_score=round(float(text_score), 1),
            scene_stability_score=round(float(scene_stability), 1),
            scene_switch_rate=round(float(scene_switch_rate), 1),
            blur_score=round(float(blur_score), 1),
            brightness_score=round(float(brightness_score), 1),
            device_profile="rokid-video-scene-proxy",
            motion_source="explicit" if explicit_motion is not None else "scene-derived",
            pose_source="scene-proxy",
            frame_source=frame_source,
        )

    def blueprint(self):
        sample_packet = RokidInputPacket(
            source="rokid_video_adapter",
            timestamp_text="12:00:00",
            timestamp_ms=1730000000000,
            task_mode="reading",
            pitch=3.8,
            yaw=-1.6,
            roll=1.2,
            motion_intensity=14.0,
            tracking_state="scene_locked",
            tracking_confidence=0.84,
            tracking_uncertainty=14.0,
            face_present=None,
            frame_width=1280,
            frame_height=720,
            scene_content_score=72.0,
            scene_text_score=66.0,
            scene_stability_score=74.0,
            scene_switch_rate=18.0,
            blur_score=58.0,
            brightness_score=52.0,
            device_profile="rokid-video-scene-proxy",
            motion_source="scene-derived",
            pose_source="scene-proxy",
            frame_source="base64",
        )
        return {
            "adapter_name": "rokid-video-scene-adapter",
            "active_endpoint": "/api/v1/rokid/frame",
            "input_options": ["multipart file `frame`", "JSON `image_base64`", "JSON `image_path`"],
            "derived_signals": [
                "scene_content_score",
                "scene_text_score",
                "scene_stability_score",
                "scene_switch_rate",
                "blur_score",
                "brightness_score",
                "scene-derived pitch/yaw/roll proxies",
            ],
            "normalized_packet": asdict(sample_packet),
            "limits": [
                "scene-driven proxy only",
                "not a precise IMU or eye-tracking replacement",
                "best for first-person study surfaces such as books, screens, boards, and notes",
            ],
        }

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

    def _compute_blur_score(self, gray):
        variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        return self._clamp((variance / 180.0) * 100.0)

    def _compute_brightness_score(self, gray):
        return self._clamp((float(np.mean(gray)) / 255.0) * 100.0)

    def _compute_contrast_score(self, gray):
        return self._clamp((float(np.std(gray)) / 72.0) * 100.0)

    def _compute_feature_score(self, gray):
        corners = cv2.goodFeaturesToTrack(gray, maxCorners=180, qualityLevel=0.01, minDistance=8)
        count = 0 if corners is None else int(len(corners))
        return self._clamp((count / 160.0) * 100.0)

    def _compute_text_score(self, edges, feature_score, contrast_score):
        edge_density = float(np.mean(edges > 0)) * 100.0
        horizontal_energy = float(np.mean(np.abs(np.diff(edges.astype(np.float32), axis=1)))) / 255.0 * 100.0
        score = (edge_density * 1.7) + (horizontal_energy * 0.55) + (feature_score * 0.35) + (contrast_score * 0.18)
        return self._clamp(score)

    def _compute_content_score(self, text_score, feature_score, blur_score, contrast_score):
        score = (text_score * 0.45) + (feature_score * 0.30) + (blur_score * 0.15) + (contrast_score * 0.10)
        return self._clamp(score)

    def _compute_anchor(self, edges, gray):
        mask = edges > 0
        if not np.any(mask):
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            mask = thresh < np.mean(thresh)
        if not np.any(mask):
            height, width = gray.shape[:2]
            return width / 2.0, height / 2.0
        ys, xs = np.where(mask)
        return float(np.mean(xs)), float(np.mean(ys))

    def _compute_scene_delta(self, preview):
        delta = 0.0
        if self.previous_preview is not None:
            diff = cv2.absdiff(preview, self.previous_preview)
            delta = float(np.mean(diff))
        return delta

    def _compute_histogram(self, gray):
        hist = cv2.calcHist([gray], [0], None, [32], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist

    def _compute_histogram_delta(self, gray):
        current = self._compute_histogram(gray)
        if self.previous_hist is None:
            return 0.0
        return float(cv2.compareHist(self.previous_hist.astype("float32"), current.astype("float32"), cv2.HISTCMP_BHATTACHARYYA))

    def _compute_anchor_shift(self, anchor, frame_shape):
        if self.previous_anchor is None:
            return 0.0
        frame_w, frame_h = frame_shape
        dx = (anchor[0] - self.previous_anchor[0]) / max(frame_w, 1)
        dy = (anchor[1] - self.previous_anchor[1]) / max(frame_h, 1)
        return min(1.0, (dx * dx + dy * dy) ** 0.5 * 3.0)

    def _compute_scene_switch_rate(self, anchor_shift, histogram_delta, content_score, text_score):
        content_drop = 0.0
        if self.previous_content_score is not None and self.previous_content_score > content_score:
            content_drop = min(1.0, (self.previous_content_score - content_score) / 42.0)
        text_drop = 0.0
        if self.previous_content_score is not None and text_score < 28:
            text_drop = min(1.0, (28.0 - text_score) / 28.0)
        score = (anchor_shift * 42.0) + (histogram_delta * 38.0) + (content_drop * 14.0) + (text_drop * 6.0)
        return self._clamp(score)

    def _compute_motion_intensity(self, scene_delta, histogram_delta, anchor_shift):
        scene_component = min(1.0, scene_delta / 34.0)
        histogram_component = min(1.0, histogram_delta * 2.0)
        motion = (scene_component * 48.0) + (histogram_component * 22.0) + (anchor_shift * 30.0)
        return round(self._clamp(motion), 1)

    def _compute_scene_stability(self, motion, scene_switch_rate, content_score, blur_score):
        stability = 100.0 - (motion * 0.52) - (scene_switch_rate * 0.28)
        stability += max(0.0, content_score - 45.0) * 0.10
        stability -= max(0.0, 20.0 - blur_score) * 0.55
        return self._clamp(stability)

    def _compute_tracking_confidence(self, blur_score, brightness_score, content_score, scene_stability):
        brightness_quality = 100.0 - min(abs(brightness_score - 52.0) * 1.3, 100.0)
        quality = (
            (blur_score * 0.30)
            + (brightness_quality * 0.18)
            + (content_score * 0.28)
            + (scene_stability * 0.24)
        )
        confidence = 0.12 + (self._clamp(quality) / 100.0) * 0.84
        return max(0.08, min(0.98, confidence))

    def _compute_tracking_uncertainty(
        self,
        blur_score,
        brightness_score,
        content_score,
        scene_stability,
        scene_switch_rate,
        tracking_confidence,
    ):
        brightness_penalty = 0.0
        if brightness_score < 14.0:
            brightness_penalty = (14.0 - brightness_score) * 1.4
        elif brightness_score > 88.0:
            brightness_penalty = (brightness_score - 88.0) * 1.2
        blur_penalty = max(0.0, 22.0 - blur_score) * 1.5
        sparse_penalty = max(0.0, 24.0 - content_score) * 0.9
        stability_penalty = max(0.0, 34.0 - scene_stability) * 0.8
        base = (1.0 - tracking_confidence) * 52.0
        uncertainty = base + brightness_penalty + blur_penalty + sparse_penalty + stability_penalty + (scene_switch_rate * 0.12)
        return self._clamp(uncertainty)

    def _derive_scene_pose(self, anchor, frame_shape, edges, scene_stability):
        frame_w, frame_h = frame_shape
        normalized_x = ((anchor[0] / max(frame_w, 1)) - 0.5) * 2.0
        normalized_y = ((anchor[1] / max(frame_h, 1)) - 0.5) * 2.0
        pitch_target = self._clamp(normalized_y * 18.0, -22.0, 22.0)
        yaw_target = self._clamp(normalized_x * 16.0, -20.0, 20.0)
        roll_target = self._estimate_roll(edges)
        blend = 0.45 if scene_stability >= 45 else 0.28
        pitch = (pitch_target * blend) + (self.last_pose[0] * (1.0 - blend))
        yaw = (yaw_target * blend) + (self.last_pose[1] * (1.0 - blend))
        roll = (roll_target * blend) + (self.last_pose[2] * (1.0 - blend))
        return (
            round(self._clamp(pitch, -28.0, 28.0), 2),
            round(self._clamp(yaw, -24.0, 24.0), 2),
            round(self._clamp(roll, -12.0, 12.0), 2),
        )

    def _estimate_roll(self, edges):
        ys, xs = np.where(edges > 0)
        if len(xs) < 40:
            return self.last_pose[2] * 0.85
        coords = np.column_stack((xs.astype(np.float32), ys.astype(np.float32)))
        mean, eigenvectors = cv2.PCACompute(coords, mean=None, maxComponents=2)
        _ = mean
        angle = float(np.degrees(np.arctan2(eigenvectors[0, 1], eigenvectors[0, 0])))
        normalized = ((angle + 90.0) % 180.0) - 90.0
        return self._clamp(normalized * 0.18, -10.0, 10.0)

    def _classify_tracking_state(self, blur_score, brightness_score, content_score, scene_stability, scene_switch_rate):
        if blur_score < 10.0:
            return "blurred"
        if brightness_score < 10.0 or brightness_score > 92.0:
            return "low_visibility"
        if content_score < 18.0:
            return "content_sparse"
        if scene_stability < 28.0 and scene_switch_rate >= 48.0:
            return "scene_unstable"
        if content_score >= 50.0 and scene_stability >= 46.0:
            return "scene_locked"
        return "scene_tracking"

    def _decay_last_pose(self, factor):
        damped_pitch = self.last_pose[0] * factor
        damped_yaw = self.last_pose[1] * factor
        damped_roll = self.last_pose[2] * factor
        self.last_pose = (damped_pitch, damped_yaw, damped_roll)
        return damped_pitch, damped_yaw, damped_roll

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
