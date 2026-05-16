import argparse
import time
from collections import Counter
from pathlib import Path

import bootstrap_windows_runtime  # noqa: F401
import cv2
import requests


DEFAULT_BASE_URL = "http://127.0.0.1:5000"
FRAME_ENDPOINT = "/api/v1/rokid/frame"
STATUS_ENDPOINT = "/status"
RESET_ENDPOINT = "/reset_session"
CALIBRATE_ENDPOINT = "/calibrate"
TASK_MODES = ("lecture", "reading", "note-taking", "review")


class FrameSource:
    def __init__(self, kind, image_path=None, video_path=None, camera_index=0, loop_video=False):
        self.kind = kind
        self.image_path = str(image_path) if image_path else None
        self.video_path = str(video_path) if video_path else None
        self.camera_index = int(camera_index)
        self.loop_video = bool(loop_video)
        self.frame = None
        self.capture = None
        self.label = ""
        self._open()

    def _open_capture(self, target, camera=False):
        attempts = []
        if camera and hasattr(cv2, "CAP_DSHOW"):
            attempts.append(cv2.VideoCapture(target, cv2.CAP_DSHOW))
        attempts.append(cv2.VideoCapture(target))
        for cap in attempts:
            if cap is not None and cap.isOpened():
                return cap
            if cap is not None:
                cap.release()
        return None

    def _open(self):
        self.close()
        if self.kind == "image":
            self.frame = cv2.imread(self.image_path)
            if self.frame is None:
                raise RuntimeError(f"Unable to load image: {self.image_path}")
            self.label = f"image:{Path(self.image_path).name}"
            return

        if self.kind == "video":
            self.capture = self._open_capture(self.video_path, camera=False)
            if self.capture is None:
                raise RuntimeError(f"Unable to open video file: {self.video_path}")
            self.label = f"video:{Path(self.video_path).name}"
            return

        if self.kind == "camera":
            self.capture = self._open_capture(self.camera_index, camera=True)
            if self.capture is None:
                raise RuntimeError(f"Unable to open camera index {self.camera_index}")
            self.label = f"camera:{self.camera_index}"
            return

        raise RuntimeError(f"Unsupported frame source: {self.kind}")

    def can_reopen(self):
        return self.kind in {"video", "image"}

    def reopen(self):
        self._open()

    def read(self):
        if self.kind == "image":
            return None if self.frame is None else self.frame.copy()

        if self.capture is None:
            return None
        ok, frame = self.capture.read()
        if ok and frame is not None:
            return frame

        if self.kind == "video" and self.loop_video:
            self.reopen()
            if self.capture is None:
                return None
            ok, frame = self.capture.read()
            if ok and frame is not None:
                return frame

        return None

    def close(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None


def build_parser():
    parser = argparse.ArgumentParser(
        description="Continuously stream frames into the Rokid video-frame adapter."
    )
    parser.add_argument(
        "--source",
        choices=("image", "video", "camera"),
        default="image",
        help="Frame source for the local Rokid test chain.",
    )
    parser.add_argument("--image-path", default="images/demo.jpg", help="Image path when --source image is used.")
    parser.add_argument("--video-path", default="", help="Video path when --source video is used.")
    parser.add_argument("--camera-index", type=int, default=0, help="Camera index when --source camera is used.")
    parser.add_argument(
        "--task-mode",
        choices=TASK_MODES,
        default="reading",
        help="Task mode attached to each streamed frame.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the local Flask backend.")
    parser.add_argument("--interval", type=float, default=0.2, help="Seconds between frame posts.")
    parser.add_argument("--duration", type=float, default=None, help="Optional total runtime in seconds.")
    parser.add_argument("--max-frames", type=int, default=0, help="Optional frame cap. 0 means unlimited.")
    parser.add_argument("--warmup-frames", type=int, default=8, help="Frames used for reset/calibrate preparation.")
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=84,
        help="JPEG quality used for multipart uploads.",
    )
    parser.add_argument(
        "--loop-video",
        action="store_true",
        help="Loop the video file when the end is reached.",
    )
    parser.add_argument(
        "--no-prepare-session",
        action="store_true",
        help="Skip reset/warmup/calibrate before streaming.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=5.0,
        help="HTTP timeout in seconds for each backend request.",
    )
    return parser


def request_json(method, url, timeout, **kwargs):
    response = requests.request(method, url, timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


def encode_frame(frame, jpeg_quality):
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG.")
    return encoded.tobytes()


def send_frame(frame, args):
    image_bytes = encode_frame(frame, args.jpeg_quality)
    data = {
        "task_mode": args.task_mode,
        "timestamp_ms": str(int(time.time() * 1000)),
    }
    files = {
        "frame": ("rokid-frame.jpg", image_bytes, "image/jpeg"),
    }
    response = request_json(
        "POST",
        f"{args.base_url}{FRAME_ENDPOINT}",
        timeout=args.request_timeout,
        data=data,
        files=files,
    )
    status = request_json("GET", f"{args.base_url}{STATUS_ENDPOINT}", timeout=args.request_timeout)
    return response, status


def prepare_session(source, args):
    if args.no_prepare_session:
        return

    print("Preparing local session baseline...")
    request_json("GET", f"{args.base_url}{RESET_ENDPOINT}", timeout=args.request_timeout)

    warmed = 0
    for _ in range(max(0, args.warmup_frames)):
        frame = source.read()
        if frame is None:
            break
        send_frame(frame, args)
        warmed += 1
        time.sleep(min(args.interval, 0.12))

    if warmed == 0:
        print("Warmup skipped because no readable frame was available yet.")
        return

    request_json("GET", f"{args.base_url}{CALIBRATE_ENDPOINT}", timeout=args.request_timeout)
    request_json("GET", f"{args.base_url}{RESET_ENDPOINT}", timeout=args.request_timeout)
    if source.can_reopen():
        source.reopen()
    print(f"Warmup complete: {warmed} frame(s), baseline recalibrated.")


def print_frame_line(frame_index, source_label, adapter_response, status):
    tracking = adapter_response.get("tracking_state", "unknown")
    track_conf = adapter_response.get("tracking_confidence", 0)
    hint = status.get("state_hint", "stable")
    alignment = round(float(status.get("behavioral_alignment", 0) or 0))
    load = round(float(status.get("cognitive_load", 0) or 0))
    fatigue = round(float(status.get("fatigue_risk", 0) or 0))
    surface = round(float(status.get("study_surface_score", 0) or 0))
    lock_score = round(float(status.get("scene_lock_score", 0) or 0))
    confidence = status.get("confidence_level", "unknown")
    mode = status.get("task_mode", "reading")
    print(
        f"[{frame_index:04d}] {source_label:<20} "
        f"| track {tracking:<14} conf {float(track_conf):.2f} "
        f"| hint {hint:<20} "
        f"| align {alignment:>3} load {load:>3} fatigue {fatigue:>3} "
        f"| surface {surface:>3} lock {lock_score:>3} "
        f"| confidence {confidence:<10} mode {mode}"
    )


def print_summary(frame_count, source, stats):
    print("\nStreaming summary")
    print(f"- Source: {source.label}")
    print(f"- Frames sent: {frame_count}")
    print(f"- Tracking states: {dict(stats['tracking'])}")
    print(f"- State hints: {dict(stats['hint'])}")
    print(f"- Confidence levels: {dict(stats['confidence'])}")
    if frame_count > 0:
        print(f"- Average tracking confidence: {stats['tracking_conf_sum'] / frame_count:.2f}")
        print(f"- Average study surface score: {stats['surface_sum'] / frame_count:.1f}")
        print(f"- Average scene lock score: {stats['lock_sum'] / frame_count:.1f}")
        print(f"- Average scene switch rate: {stats['switch_sum'] / frame_count:.1f}")


def build_source(args):
    if args.source == "image":
        return FrameSource("image", image_path=args.image_path)
    if args.source == "video":
        if not args.video_path:
            raise RuntimeError("Provide --video-path when using --source video.")
        return FrameSource("video", video_path=args.video_path, loop_video=args.loop_video)
    return FrameSource("camera", camera_index=args.camera_index)


def main():
    args = build_parser().parse_args()
    source = build_source(args)
    stats = {
        "tracking": Counter(),
        "hint": Counter(),
        "confidence": Counter(),
        "tracking_conf_sum": 0.0,
        "surface_sum": 0.0,
        "lock_sum": 0.0,
        "switch_sum": 0.0,
    }
    frame_count = 0
    started_at = time.time()

    try:
        prepare_session(source, args)
        print(f"Streaming Rokid frame path from {source.label} ... Press Ctrl+C to stop.")
        while True:
            if args.duration is not None and (time.time() - started_at) >= args.duration:
                break
            if args.max_frames and frame_count >= args.max_frames:
                break

            frame = source.read()
            if frame is None:
                print("Frame source ended or became unreadable.")
                break

            adapter_response, status = send_frame(frame, args)
            frame_count += 1
            stats["tracking"][adapter_response.get("tracking_state", "unknown")] += 1
            stats["hint"][status.get("state_hint", "stable")] += 1
            stats["confidence"][status.get("confidence_level", "unknown")] += 1
            stats["tracking_conf_sum"] += float(adapter_response.get("tracking_confidence", 0) or 0.0)
            stats["surface_sum"] += float(status.get("study_surface_score", 0) or 0.0)
            stats["lock_sum"] += float(status.get("scene_lock_score", 0) or 0.0)
            stats["switch_sum"] += float(status.get("scene_switch_rate", 0) or 0.0)
            print_frame_line(frame_count, source.label, adapter_response, status)
            time.sleep(max(0.01, args.interval))
    except KeyboardInterrupt:
        print("\nFrame stream stopped by user.")
    finally:
        source.close()
        print_summary(frame_count, source, stats)


if __name__ == "__main__":
    main()
