class StateInterpreter:
    """Interpret current learning-state proxies into a more explainable snapshot.

    This layer does not claim to detect attention precisely. It reorganizes
    existing posture, scene, and session signals into conservative proxy labels,
    scores, and evidence that are easier to stabilize and calibrate later.
    """

    LABEL_DISPLAY = {
        "stable_focus": "Stable focus",
        "scene_snapshot": "Scene snapshot",
        "load_rising": "Load rising",
        "load_rising_proxy": "Load rising proxy",
        "productive_struggle": "Productive struggle",
        "off_task_risk": "Off-task risk",
        "off_task_risk_proxy": "Off-task risk proxy",
        "fatigue_risk": "Fatigue risk",
        "signal_uncertain": "Signal uncertain",
    }

    DEFAULT_THRESHOLDS = {
        "signal_uncertain_floor": 40.0,
        "signal_caution_floor": 55.0,
        "productive_load_floor": 60.0,
        "productive_engagement_floor": 60.0,
        "off_task_switch_floor": 56.0,
        "off_task_engagement_ceiling": 48.0,
        "signal_guard_floor": 48.0,
        "fatigue_floor": 65.0,
        "fatigue_stability_ceiling": 46.0,
        "fatigue_motion_ceiling": 22.0,
        "stable_engagement_floor": 72.0,
        "stable_load_ceiling": 48.0,
        "stable_fatigue_ceiling": 40.0,
        "load_rising_floor": 50.0,
        "load_rising_engagement_ceiling": 72.0,
        "frame_ready_streak": 4.0,
        "frame_ready_seconds": 3.0,
        "frame_only_confidence_cap": 62.0,
    }

    def __init__(self, thresholds=None):
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        if isinstance(thresholds, dict):
            for key, value in thresholds.items():
                try:
                    self.thresholds[key] = float(value)
                except Exception:
                    continue

    def interpret(self, snapshot):
        metrics = self._normalize(snapshot or {})
        axes = self._compute_axes(metrics)
        auxiliary_flags = self._compute_auxiliary_flags(metrics, axes)
        label = self._select_label(metrics, axes, auxiliary_flags)
        evidence = self._build_evidence(label, metrics, axes, auxiliary_flags)
        uncertainty_reason = self._uncertainty_reason(label, metrics, axes, auxiliary_flags)
        confidence = self._confidence(label, metrics, axes, auxiliary_flags, uncertainty_reason)

        return {
            "label": label,
            "display_label": self.display_label(label),
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "uncertainty_reason": uncertainty_reason,
            "axes": {
                "engagement_score": round(axes["engagement_score"], 1),
                "cognitive_load_score": round(axes["cognitive_load_score"], 1),
                "fatigue_score": round(axes["fatigue_score"], 1),
                "signal_quality_score": round(axes["signal_quality_score"], 1),
            },
            "auxiliary_flags": auxiliary_flags,
        }

    @classmethod
    def display_label(cls, label):
        normalized = str(label or "").strip().lower()
        return cls.LABEL_DISPLAY.get(normalized, "Stable focus")

    def _normalize(self, snapshot):
        return {
            "task_mode": self._text(snapshot, "task_mode", default="reading"),
            "state_hint": self._text(snapshot, "state_hint", default="stable"),
            "session_state_label": self._text(snapshot, "session_state_label", default=""),
            "load_level": self._text(snapshot, "load_level", default="low"),
            "focus_score": self._number(snapshot, "focus_score", default=0.0),
            "behavioral_alignment": self._number(snapshot, "behavioral_alignment", default=0.0),
            "cognitive_load": self._number(snapshot, "cognitive_load", default=0.0),
            "fatigue_risk": self._number(snapshot, "fatigue_risk", default=0.0),
            "uncertainty_score": self._number(snapshot, "uncertainty_score", default=0.0),
            "switching_index": self._number(snapshot, "switching_index", default=0.0),
            "drift_trend": self._number(snapshot, "drift_trend", default=0.0),
            "combined_drift": self._number(snapshot, "combined_drift", default=0.0),
            "movement_intensity": self._number(snapshot, "movement_intensity", "motion_intensity", default=0.0),
            "stability": self._number(snapshot, "stability", default=0.0),
            "scene_content_score": self._number(snapshot, "scene_content_score", default=0.0),
            "scene_text_score": self._number(snapshot, "scene_text_score", default=0.0),
            "scene_stability_score": self._number(snapshot, "scene_stability_score", default=0.0),
            "scene_switch_rate": self._number(snapshot, "scene_switch_rate", default=0.0),
            "study_surface_score": self._number(snapshot, "study_surface_score", default=0.0),
            "scene_lock_score": self._number(snapshot, "scene_lock_score", default=0.0),
            "blur_score": self._number(snapshot, "blur_score", default=0.0),
            "brightness_score": self._number(snapshot, "brightness_score", default=0.0),
            "tracking_confidence": self._number(snapshot, "tracking_confidence", default=0.0),
            "tracking_uncertainty": self._number(snapshot, "tracking_uncertainty", default=0.0),
            "tracking_state": self._text(snapshot, "tracking_state", default="warmup"),
            "source_mode": self._text(snapshot, "source_mode", default="imu_only"),
            "motion_source": self._text(snapshot, "motion_source", default="default"),
            "pose_source": self._text(snapshot, "pose_source", default="telemetry"),
            "has_pose": self._bool(snapshot.get("has_pose")),
            "has_imu": self._bool(snapshot.get("has_imu")),
            "pose_reliability": self._text(snapshot, "pose_reliability", default="measured"),
            "valid_frame_streak": self._number(snapshot, "valid_frame_streak", default=0.0),
            "valid_frame_seconds": self._number(snapshot, "valid_frame_seconds", default=0.0),
            "missing_signals": self._list(snapshot.get("missing_signals")),
            "rokid_compatible_mode": self._bool(snapshot.get("rokid_compatible_mode")),
        }

    def _compute_axes(self, metrics):
        engagement_score = self._clamp(
            (metrics["behavioral_alignment"] * 0.42)
            + (metrics["focus_score"] * 0.20)
            + (metrics["scene_lock_score"] * 0.14)
            + (metrics["study_surface_score"] * 0.10)
            + (metrics["scene_stability_score"] * 0.08)
            + (metrics["scene_content_score"] * 0.06)
            - (metrics["switching_index"] * 0.16)
            - (metrics["scene_switch_rate"] * 0.10)
        )
        cognitive_load_score = self._clamp(
            (metrics["cognitive_load"] * 0.82)
            + (max(0.0, metrics["drift_trend"]) * 1.45)
            + (max(0.0, 55.0 - metrics["behavioral_alignment"]) * 0.22)
            + (8.0 if metrics["load_level"] == "high" else 3.0 if metrics["load_level"] == "medium" else 0.0)
        )
        fatigue_score = self._clamp(
            (metrics["fatigue_risk"] * 0.80)
            + (max(0.0, 55.0 - metrics["stability"]) * 0.20)
            + (max(0.0, 22.0 - metrics["movement_intensity"]) * 0.55)
            + (max(0.0, metrics["combined_drift"] - 14.0) * 0.45)
        )
        brightness_quality = 100.0 - min(abs(metrics["brightness_score"] - 52.0) * 1.35, 100.0)
        uncertainty_inverse = 100.0 - max(metrics["uncertainty_score"], metrics["tracking_uncertainty"])
        signal_quality_score = self._clamp(
            (metrics["tracking_confidence"] * 100.0 * 0.24)
            + (metrics["scene_stability_score"] * 0.20)
            + (metrics["scene_lock_score"] * 0.16)
            + (metrics["scene_content_score"] * 0.12)
            + (metrics["blur_score"] * 0.12)
            + (brightness_quality * 0.10)
            + (uncertainty_inverse * 0.06)
        )
        return {
            "engagement_score": engagement_score,
            "cognitive_load_score": cognitive_load_score,
            "fatigue_score": fatigue_score,
            "signal_quality_score": signal_quality_score,
        }

    def _compute_auxiliary_flags(self, metrics, axes):
        note_like_mode = metrics["task_mode"] in {"note-taking", "review"}
        risk_signal_strong_enough = bool(
            axes["signal_quality_score"] >= self.thresholds["signal_guard_floor"]
        )
        valid_learning_switch = bool(
            metrics["switching_index"] >= 40.0
            and metrics["switching_index"] <= 76.0
            and axes["engagement_score"] >= 58.0
            and metrics["study_surface_score"] >= 38.0
            and (
                note_like_mode
                or metrics["scene_lock_score"] >= 34.0
                or metrics["state_hint"] == "productive_struggle"
            )
        )
        off_task_switch_floor = self.thresholds["off_task_switch_floor"] + (6.0 if note_like_mode else 0.0)
        off_task_engagement_ceiling = self.thresholds["off_task_engagement_ceiling"] - (6.0 if note_like_mode else 0.0)
        off_task_scene_lock_ceiling = 34.0 if note_like_mode else 40.0
        off_task_surface_ceiling = 38.0 if note_like_mode else 44.0
        off_task_switch = bool(
            metrics["switching_index"] >= off_task_switch_floor
            and axes["engagement_score"] <= off_task_engagement_ceiling
            and metrics["scene_lock_score"] <= off_task_scene_lock_ceiling
            and metrics["study_surface_score"] <= off_task_surface_ceiling
            and (risk_signal_strong_enough or metrics["state_hint"] == "off_task_risk")
            and not valid_learning_switch
        )
        productive_struggle_candidate = bool(
            axes["cognitive_load_score"] >= self.thresholds["productive_load_floor"]
            and axes["engagement_score"] >= self.thresholds["productive_engagement_floor"]
            and axes["fatigue_score"] < 68.0
            and axes["signal_quality_score"] >= 45.0
        )
        fatigue_candidate = bool(
            axes["fatigue_score"] >= self.thresholds["fatigue_floor"]
            and (
                metrics["stability"] <= self.thresholds["fatigue_stability_ceiling"]
                or metrics["movement_intensity"] <= self.thresholds["fatigue_motion_ceiling"]
                or metrics["state_hint"] == "fatigue_risk"
            )
            and (risk_signal_strong_enough or metrics["state_hint"] == "fatigue_risk")
        )
        signal_uncertain_candidate = bool(
            axes["signal_quality_score"] <= self.thresholds["signal_uncertain_floor"]
            or metrics["uncertainty_score"] >= 60.0
            or metrics["tracking_state"] in {"warmup", "frame_unavailable", "blurred", "low_visibility", "content_sparse"}
        )
        frame_only_guard_active = self._is_frame_only_guard(metrics)
        frame_temporal_ready = bool(
            metrics["valid_frame_streak"] >= self.thresholds["frame_ready_streak"]
            and metrics["valid_frame_seconds"] >= self.thresholds["frame_ready_seconds"]
        )
        frame_scene_snapshot_ready = bool(
            metrics["tracking_state"] in {"scene_tracking", "scene_locked"}
            and (
                metrics["scene_content_score"] >= 18.0
                or metrics["study_surface_score"] >= 22.0
                or metrics["scene_lock_score"] >= 22.0
            )
        )
        return {
            "valid_learning_switch": valid_learning_switch,
            "off_task_switch": off_task_switch,
            "productive_struggle_candidate": productive_struggle_candidate,
            "fatigue_candidate": fatigue_candidate,
            "signal_uncertain_candidate": signal_uncertain_candidate,
            "frame_only_guard_active": frame_only_guard_active,
            "frame_temporal_ready": frame_temporal_ready,
            "frame_scene_snapshot_ready": frame_scene_snapshot_ready,
        }

    def _select_label(self, metrics, axes, auxiliary_flags):
        if auxiliary_flags["frame_only_guard_active"]:
            warmup_label = self._frame_only_guard_label(metrics, axes, auxiliary_flags)
            if warmup_label:
                return warmup_label

        label = self._select_standard_label(metrics, axes, auxiliary_flags)
        if not auxiliary_flags["frame_only_guard_active"]:
            return label
        return self._frame_only_remap_label(label, metrics, auxiliary_flags)

    def _select_standard_label(self, metrics, axes, auxiliary_flags):
        if auxiliary_flags["signal_uncertain_candidate"]:
            return "signal_uncertain"
        if auxiliary_flags["fatigue_candidate"]:
            return "fatigue_risk"
        if auxiliary_flags["productive_struggle_candidate"]:
            return "productive_struggle"
        if auxiliary_flags["off_task_switch"] and not auxiliary_flags["valid_learning_switch"]:
            return "off_task_risk"
        if (
            metrics["state_hint"] == "load_rising"
            or axes["cognitive_load_score"] >= self.thresholds["load_rising_floor"]
            or metrics["load_level"] == "medium"
        ) and axes["engagement_score"] <= self.thresholds["load_rising_engagement_ceiling"]:
            return "load_rising"
        return "stable_focus"

    def _frame_only_guard_label(self, metrics, axes, auxiliary_flags):
        if auxiliary_flags["signal_uncertain_candidate"]:
            return "signal_uncertain"
        if metrics["tracking_state"] not in {"scene_tracking", "scene_locked"}:
            return "signal_uncertain"
        if axes["signal_quality_score"] < self.thresholds["signal_guard_floor"]:
            return "signal_uncertain"
        if not auxiliary_flags["frame_temporal_ready"]:
            if auxiliary_flags["frame_scene_snapshot_ready"]:
                return "scene_snapshot"
            return "signal_uncertain"
        return None

    def _frame_only_remap_label(self, label, metrics, auxiliary_flags):
        if label == "fatigue_risk":
            return "load_rising_proxy" if auxiliary_flags["frame_temporal_ready"] else "signal_uncertain"
        if label in {"productive_struggle", "load_rising"}:
            return "load_rising_proxy"
        if label == "off_task_risk":
            return "off_task_risk_proxy"
        if label == "stable_focus" and metrics["scene_lock_score"] < 38.0:
            return "scene_snapshot"
        return label

    def _build_evidence(self, label, metrics, axes, auxiliary_flags):
        evidence = []
        frame_only_guard = auxiliary_flags["frame_only_guard_active"]

        if label == "stable_focus":
            if frame_only_guard:
                evidence.append("scene-driven proxy kept a relatively steady study-surface lock")
                if metrics["scene_lock_score"] >= 50.0 or metrics["study_surface_score"] >= 50.0:
                    evidence.append("first-person scene stayed anchored on learning material")
                if axes["signal_quality_score"] >= 60.0:
                    evidence.append("signal quality stayed stable enough for a cautious proxy interpretation")
            else:
                if axes["engagement_score"] >= self.thresholds["stable_engagement_floor"]:
                    evidence.append("behavioral alignment and focus cues stayed relatively steady")
                if axes["cognitive_load_score"] <= self.thresholds["stable_load_ceiling"]:
                    evidence.append("cognitive-load proxy stayed in a lower band")
                if metrics["scene_lock_score"] >= 50.0 or metrics["study_surface_score"] >= 50.0:
                    evidence.append("first-person scene stayed anchored on a study surface")
                if axes["signal_quality_score"] >= 60.0:
                    evidence.append("signal quality was stable enough for a cautious proxy interpretation")
        elif label == "scene_snapshot":
            evidence.append("scene-driven proxy has only a short continuous frame window so far")
            if metrics["scene_lock_score"] >= 28.0 or metrics["study_surface_score"] >= 28.0:
                evidence.append("the current frame still looks anchored on a study surface")
            evidence.append("the system stays at scene-snapshot strength until more valid frames arrive")
        elif label == "load_rising":
            if axes["cognitive_load_score"] >= self.thresholds["load_rising_floor"]:
                evidence.append("cognitive-load proxy rose into a medium or higher band")
            if axes["engagement_score"] < self.thresholds["stable_engagement_floor"]:
                evidence.append("engagement cues softened compared with a stable segment")
            if metrics["switching_index"] >= 34.0 or metrics["drift_trend"] >= 5.0:
                evidence.append("switching or drift trend increased across the current snapshot")
            if metrics["state_hint"] == "load_rising":
                evidence.append("legacy state hint also points to load rising")
        elif label == "load_rising_proxy":
            evidence.append("scene-driven proxy suggests learning pressure or challenge is rising")
            if metrics["scene_switch_rate"] >= 34.0 or metrics["drift_trend"] >= 5.0:
                evidence.append("scene-switch proxy or drift trend increased")
            if metrics["scene_lock_score"] >= 34.0 or metrics["study_surface_score"] >= 34.0:
                evidence.append("study-surface lock still looks partially intact")
            evidence.append("without measured pose or IMU, this stays a conservative load proxy rather than a stronger fatigue or struggle claim")
        elif label == "productive_struggle":
            if axes["cognitive_load_score"] >= self.thresholds["productive_load_floor"]:
                evidence.append("cognitive-load proxy is elevated")
            if axes["engagement_score"] >= self.thresholds["productive_engagement_floor"]:
                evidence.append("behavioral alignment remains relatively high despite the challenge")
            if metrics["scene_lock_score"] >= 42.0 or metrics["study_surface_score"] >= 42.0:
                evidence.append("first-person scene still looks anchored on learning material")
            if auxiliary_flags["valid_learning_switch"]:
                evidence.append("switching pattern still looks compatible with valid learning transitions")
        elif label == "off_task_risk":
            if metrics["switching_index"] >= self.thresholds["off_task_switch_floor"]:
                evidence.append("switching index stayed elevated")
            if metrics["scene_switch_rate"] >= 52.0:
                evidence.append("first-person scene changed rapidly")
            if metrics["scene_lock_score"] <= 40.0 or metrics["study_surface_score"] <= 44.0:
                evidence.append("study-surface lock weakened during the current snapshot")
            if axes["engagement_score"] <= self.thresholds["off_task_engagement_ceiling"]:
                evidence.append("engagement cues dropped while switching pressure increased")
        elif label == "off_task_risk_proxy":
            evidence.append("scene-switch proxy rose while study-surface lock weakened")
            if metrics["scene_switch_rate"] >= 45.0:
                evidence.append("first-person scene changed more often than a settled study view")
            if metrics["scene_lock_score"] <= 40.0 or metrics["study_surface_score"] <= 44.0:
                evidence.append("study-surface lock softened during the current frame window")
            evidence.append("this remains a scene-driven learning-state proxy with conservative certainty")
        elif label == "fatigue_risk":
            if axes["fatigue_score"] >= self.thresholds["fatigue_floor"]:
                evidence.append("fatigue proxy stayed elevated")
            if metrics["stability"] <= self.thresholds["fatigue_stability_ceiling"]:
                evidence.append("stability softened during the current snapshot")
            if metrics["movement_intensity"] <= self.thresholds["fatigue_motion_ceiling"] and metrics["combined_drift"] >= 10.0:
                evidence.append("low movement with persistent drift can match a fatigue-like slump")
            if metrics["state_hint"] == "fatigue_risk":
                evidence.append("legacy state hint also points to fatigue risk")
        elif label == "signal_uncertain":
            if axes["signal_quality_score"] <= self.thresholds["signal_uncertain_floor"]:
                evidence.append("signal quality is too weak for a stronger learning-state proxy claim")
            if metrics["tracking_state"] in {"warmup", "frame_unavailable", "blurred", "low_visibility", "content_sparse"}:
                evidence.append(f"tracking state is currently `{metrics['tracking_state']}`")
            if metrics["blur_score"] < 22.0:
                evidence.append("frame clarity looks limited")
            if metrics["brightness_score"] < 14.0 or metrics["brightness_score"] > 88.0:
                evidence.append("brightness looks atypical for a stable scene proxy")
            if frame_only_guard and metrics["missing_signals"]:
                evidence.append("measured pose or IMU signals are missing, so the system stays conservative")

        if not evidence:
            evidence.append("current proxy signals are mixed, so the interpretation stays conservative")
        return evidence[:4]

    def _uncertainty_reason(self, label, metrics, axes, auxiliary_flags):
        if auxiliary_flags["frame_only_guard_active"] and not auxiliary_flags["frame_temporal_ready"]:
            if metrics["tracking_state"] not in {"scene_tracking", "scene_locked"}:
                return "Frame-only mode has not reached a stable scene window yet, so the learning-state proxy stays uncertain."
            return (
                f"Only {int(round(metrics['valid_frame_streak']))} valid frame(s) and "
                f"{metrics['valid_frame_seconds']:.1f}s of continuous scene evidence are available, "
                "so the system stays at scene-snapshot strength."
            )
        if auxiliary_flags["signal_uncertain_candidate"]:
            if metrics["tracking_state"] in {"frame_unavailable", "warmup"}:
                return "Scene and posture signals are still warming up, so the learning-state proxy should be treated cautiously."
            if metrics["blur_score"] < 22.0:
                return "Frame clarity is limited, which reduces confidence in the current learning-state proxy."
            if metrics["brightness_score"] < 14.0 or metrics["brightness_score"] > 88.0:
                return "Lighting conditions look atypical, so the scene proxy is less reliable."
            return "Signal quality is currently weak, so this should be read as a cautious learning-state proxy."
        if auxiliary_flags["frame_only_guard_active"] and metrics["missing_signals"]:
            return "Frame-only mode is using a scene-driven proxy without measured pose or IMU, so confidence is intentionally capped."
        if axes["signal_quality_score"] < self.thresholds["signal_caution_floor"]:
            return "Signal quality is moderate rather than strong, so the learning-state proxy may drift slightly."
        return ""

    def _confidence(self, label, metrics, axes, auxiliary_flags, uncertainty_reason):
        signal = axes["signal_quality_score"] / 100.0
        engagement = axes["engagement_score"] / 100.0
        load = axes["cognitive_load_score"] / 100.0
        fatigue = axes["fatigue_score"] / 100.0
        base = 0.42 + (signal * 0.26)

        if label == "stable_focus":
            support = min(1.0, (engagement * 0.52) + ((1.0 - load) * 0.28) + ((1.0 - fatigue) * 0.20))
        elif label == "scene_snapshot":
            surface = self._clamp(metrics["study_surface_score"]) / 100.0
            lock = self._clamp(metrics["scene_lock_score"]) / 100.0
            support = min(1.0, (signal * 0.42) + (surface * 0.32) + (lock * 0.18) + 0.08)
        elif label == "load_rising":
            support = min(1.0, (load * 0.50) + ((1.0 - engagement) * 0.30) + (signal * 0.20))
        elif label == "load_rising_proxy":
            switching = self._clamp(metrics["scene_switch_rate"] * 0.55 + metrics["drift_trend"] * 0.30) / 100.0
            support = min(1.0, (load * 0.32) + (switching * 0.28) + (signal * 0.25) + 0.15)
        elif label == "productive_struggle":
            support = min(1.0, (load * 0.38) + (engagement * 0.42) + (signal * 0.20))
        elif label == "off_task_risk":
            switching_support = self._clamp(metrics["switching_index"] * 0.9 + metrics["scene_switch_rate"] * 0.5) / 100.0
            support = min(1.0, (switching_support * 0.42) + ((1.0 - engagement) * 0.33) + ((1.0 - signal) * 0.05) + 0.20)
        elif label == "off_task_risk_proxy":
            switching_support = self._clamp(metrics["scene_switch_rate"] * 0.78 + (100.0 - metrics["scene_lock_score"]) * 0.38) / 100.0
            support = min(1.0, (switching_support * 0.42) + ((1.0 - engagement) * 0.20) + (signal * 0.12) + 0.16)
        elif label == "fatigue_risk":
            support = min(1.0, (fatigue * 0.54) + ((1.0 - engagement) * 0.16) + ((1.0 - load) * 0.08) + 0.22)
        else:
            support = min(1.0, ((1.0 - signal) * 0.58) + 0.28)

        if auxiliary_flags["valid_learning_switch"] and label == "productive_struggle":
            support += 0.05
        if auxiliary_flags["signal_uncertain_candidate"] and label != "signal_uncertain":
            support -= 0.08
        if uncertainty_reason:
            support -= 0.04

        confidence = base + (support * 0.24)
        if label == "signal_uncertain":
            confidence = 0.34 + ((1.0 - signal) * 0.32)

        if auxiliary_flags["frame_only_guard_active"]:
            missing_penalty = min(0.16, len(metrics["missing_signals"]) * 0.04)
            confidence -= missing_penalty
            if not auxiliary_flags["frame_temporal_ready"]:
                confidence = min(confidence, 0.48 if label == "scene_snapshot" else 0.44)
            confidence = min(confidence, self.thresholds["frame_only_confidence_cap"] / 100.0)

        return self._clamp(confidence, low=0.32, high=0.92)

    def _is_frame_only_guard(self, metrics):
        return bool(metrics["rokid_compatible_mode"] and metrics["source_mode"] == "frame_only")

    def _number(self, payload, *keys, default=0.0):
        for key in keys:
            if key not in payload:
                continue
            try:
                value = payload.get(key)
                if value is None:
                    continue
                return float(value)
            except Exception:
                continue
        return float(default)

    def _text(self, payload, key, default=""):
        value = payload.get(key, default)
        return str(value if value is not None else default).strip().lower()

    def _bool(self, value):
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        text = str(value).strip().lower()
        return text in {"1", "true", "yes", "on"}

    def _list(self, value):
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        if value is None:
            return []
        text = str(value).strip()
        return [text.lower()] if text else []

    def _clamp(self, value, low=0.0, high=100.0):
        try:
            numeric = float(value)
        except Exception:
            numeric = low
        return max(low, min(high, numeric))
