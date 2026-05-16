import time

import numpy as np


class PostureEngine:
    TASK_PROFILES = {
        "lecture": {
            "drift_soft": 10.0,
            "drift_hard": 18.0,
            "yaw_soft": 8.0,
            "yaw_hard": 15.0,
            "roll_soft": 7.0,
            "roll_hard": 12.0,
            "variance_soft": 4.5,
            "variance_hard": 9.5,
            "movement_soft": 3.5,
            "movement_hard": 7.0,
            "fatigue_drift": 12.0,
            "fatigue_variance": 3.2,
            "axis_weights": (0.46, 0.34, 0.20),
        },
        "reading": {
            "drift_soft": 13.0,
            "drift_hard": 22.0,
            "yaw_soft": 10.0,
            "yaw_hard": 18.0,
            "roll_soft": 8.0,
            "roll_hard": 14.0,
            "variance_soft": 6.5,
            "variance_hard": 12.5,
            "movement_soft": 4.5,
            "movement_hard": 8.5,
            "fatigue_drift": 14.0,
            "fatigue_variance": 4.0,
            "axis_weights": (0.56, 0.24, 0.20),
        },
        "note-taking": {
            "drift_soft": 17.0,
            "drift_hard": 26.0,
            "yaw_soft": 16.0,
            "yaw_hard": 24.0,
            "roll_soft": 10.0,
            "roll_hard": 17.0,
            "variance_soft": 9.5,
            "variance_hard": 16.5,
            "movement_soft": 6.5,
            "movement_hard": 11.5,
            "fatigue_drift": 18.0,
            "fatigue_variance": 5.0,
            "axis_weights": (0.40, 0.36, 0.24),
        },
        "review": {
            "drift_soft": 15.0,
            "drift_hard": 24.0,
            "yaw_soft": 12.0,
            "yaw_hard": 20.0,
            "roll_soft": 9.0,
            "roll_hard": 15.0,
            "variance_soft": 8.0,
            "variance_hard": 14.0,
            "movement_soft": 5.5,
            "movement_hard": 10.0,
            "fatigue_drift": 16.0,
            "fatigue_variance": 4.4,
            "axis_weights": (0.50, 0.30, 0.20),
        },
    }

    def __init__(self, alpha=0.3, history_size=15):
        self.alpha = alpha
        self.history_size = history_size
        self.base_pitch = 0.0
        self.base_yaw = 0.0
        self.base_roll = 0.0
        self.smooth_pitch = 0.0
        self.smooth_yaw = 0.0
        self.smooth_roll = 0.0
        self.history = [0.0] * history_size
        self.signed_history = [0.0] * history_size
        self.yaw_history = [0.0] * history_size
        self.roll_history = [0.0] * history_size
        self.motion_history = [0.0] * history_size
        self.last_axis_vector = (0.0, 0.0, 0.0)
        self.task_mode = "reading"
        self.samples_since_reset = 0
        self.mode_changed_at = None
        self.alert_start = None
        self.passive_drift_start = None
        self.is_alert = False
        self.current_stability = 100
        self.focus_score = 100.0
        self.cognitive_load = 0.0
        self.load_level = "low"
        self.load_reason = "Stable learning state"
        self.behavioral_alignment = 100.0
        self.behavioral_level = "aligned"
        self.fatigue_risk = 0.0
        self.fatigue_level = "low"
        self.uncertainty_score = 35.0
        self.confidence_level = "warming_up"
        self.drift_trend = 0.0
        self.switching_index = 0.0
        self.state_hint = "stable"
        self.orientation_drift = 0.0
        self.movement_intensity = 0.0
        self.combined_drift = 0.0

    def process(self, raw_pitch, raw_yaw=0.0, raw_roll=0.0, motion_intensity=None, now=None):
        now = time.time() if now is None else now
        profile = self.TASK_PROFILES[self.task_mode]

        self.samples_since_reset += 1
        previous_vector = self.last_axis_vector
        self.smooth_pitch = (self.alpha * raw_pitch) + ((1 - self.alpha) * self.smooth_pitch)
        self.smooth_yaw = (self.alpha * raw_yaw) + ((1 - self.alpha) * self.smooth_yaw)
        self.smooth_roll = (self.alpha * raw_roll) + ((1 - self.alpha) * self.smooth_roll)
        self.last_axis_vector = (self.smooth_pitch, self.smooth_yaw, self.smooth_roll)

        signed_delta = self.smooth_pitch - self.base_pitch
        signed_yaw_delta = self.smooth_yaw - self.base_yaw
        signed_roll_delta = self.smooth_roll - self.base_roll
        rel_pitch = abs(signed_delta)
        rel_yaw = abs(signed_yaw_delta)
        rel_roll = abs(signed_roll_delta)
        rel = self._combine_relative_drift(rel_pitch, rel_yaw, rel_roll, profile)
        self.combined_drift = rel

        self.history.pop(0)
        self.history.append(rel)
        self.signed_history.pop(0)
        self.signed_history.append(signed_delta)
        self.yaw_history.pop(0)
        self.yaw_history.append(rel_yaw)
        self.roll_history.pop(0)
        self.roll_history.append(rel_roll)
        movement = self._resolve_movement_intensity(previous_vector, motion_intensity)
        self.motion_history.pop(0)
        self.motion_history.append(movement)

        variance = float(np.var(self.history))
        self.orientation_drift = self._compute_orientation_drift(rel_pitch, rel_yaw, rel_roll, profile)
        self.movement_intensity = movement

        self.current_stability = self._compute_stability(variance, profile)
        self.is_alert = self._update_alert_state(rel, profile["drift_hard"], now)
        self.drift_trend = self._compute_drift_trend(profile)
        self.switching_index = self._compute_switching_index(profile)
        self.behavioral_alignment = self._compute_behavioral_alignment(rel, variance, profile)
        self.behavioral_level = self._classify_behavioral_level(rel, variance, profile)
        self.fatigue_risk = self._compute_fatigue_risk(rel, variance, profile, now)
        self.fatigue_level = self._classify_band(self.fatigue_risk, medium=38, high=65)
        self.uncertainty_score = self._compute_uncertainty(variance, profile, now)
        self.confidence_level = self._classify_confidence(self.uncertainty_score)
        self.cognitive_load = self._compute_cognitive_load(rel, variance, profile)
        self.state_hint = self._classify_state_hint()
        self.focus_score = round(
            max(0.0, min(100.0, (self.behavioral_alignment * 0.65) + ((100 - self.cognitive_load) * 0.35))),
            1,
        )
        self.load_level, self.load_reason = self._classify_load_reason(rel, variance)

        return {
            "relative_pitch": round(rel_pitch, 2),
            "signed_pitch_delta": round(signed_delta, 2),
            "relative_yaw": round(rel_yaw, 2),
            "relative_roll": round(rel_roll, 2),
            "combined_drift": rel,
            "orientation_drift": self.orientation_drift,
            "movement_intensity": self.movement_intensity,
            "is_alert": self.is_alert,
            "focus_score": self.focus_score,
            "stability": self.current_stability,
            "cognitive_load": self.cognitive_load,
            "load_level": self.load_level,
            "load_reason": self.load_reason,
            "task_mode": self.task_mode,
            "behavioral_alignment": self.behavioral_alignment,
            "behavioral_level": self.behavioral_level,
            "fatigue_risk": self.fatigue_risk,
            "fatigue_level": self.fatigue_level,
            "uncertainty_score": self.uncertainty_score,
            "confidence_level": self.confidence_level,
            "drift_trend": self.drift_trend,
            "switching_index": self.switching_index,
            "state_hint": self.state_hint,
        }

    def calibrate(self):
        self.base_pitch = self.smooth_pitch
        self.base_yaw = self.smooth_yaw
        self.base_roll = self.smooth_roll
        self.reset_tracking(preserve_baseline=True)

    def reset_tracking(self, preserve_baseline=True):
        if preserve_baseline:
            self.smooth_pitch = self.base_pitch
            self.smooth_yaw = self.base_yaw
            self.smooth_roll = self.base_roll
        else:
            self.base_pitch = self.smooth_pitch
            self.base_yaw = self.smooth_yaw
            self.base_roll = self.smooth_roll
        self.history = [0.0] * len(self.history)
        self.signed_history = [0.0] * len(self.signed_history)
        self.yaw_history = [0.0] * len(self.yaw_history)
        self.roll_history = [0.0] * len(self.roll_history)
        self.motion_history = [0.0] * len(self.motion_history)
        self.last_axis_vector = (self.smooth_pitch, self.smooth_yaw, self.smooth_roll)
        self.samples_since_reset = 0
        self.mode_changed_at = None
        self.alert_start = None
        self.passive_drift_start = None
        self.is_alert = False
        self.current_stability = 100
        self.focus_score = 100.0
        self.cognitive_load = 0.0
        self.load_level = "low"
        self.load_reason = "Stable learning state"
        self.behavioral_alignment = 100.0
        self.behavioral_level = "aligned"
        self.fatigue_risk = 0.0
        self.fatigue_level = "low"
        self.uncertainty_score = 35.0
        self.confidence_level = "warming_up"
        self.drift_trend = 0.0
        self.switching_index = 0.0
        self.state_hint = "stable"
        self.orientation_drift = 0.0
        self.movement_intensity = 0.0
        self.combined_drift = 0.0

    def set_task_mode(self, task_mode, now=None):
        normalized = str(task_mode or "").strip().lower()
        if normalized not in self.TASK_PROFILES:
            return self.task_mode

        if normalized == self.task_mode:
            return self.task_mode

        now = time.time() if now is None else now
        self.task_mode = normalized
        current_pitch_rel = abs(self.smooth_pitch - self.base_pitch)
        current_yaw_rel = abs(self.smooth_yaw - self.base_yaw)
        current_roll_rel = abs(self.smooth_roll - self.base_roll)
        current_rel = self._combine_relative_drift(
            current_pitch_rel,
            current_yaw_rel,
            current_roll_rel,
            self.TASK_PROFILES[self.task_mode],
        )
        current_signed = self.smooth_pitch - self.base_pitch
        self.history = [current_rel] * len(self.history)
        self.signed_history = [current_signed] * len(self.signed_history)
        self.yaw_history = [current_yaw_rel] * len(self.yaw_history)
        self.roll_history = [current_roll_rel] * len(self.roll_history)
        self.motion_history = [0.0] * len(self.motion_history)
        self.alert_start = None
        self.passive_drift_start = None
        self.is_alert = False
        self.samples_since_reset = 0
        self.mode_changed_at = now
        return self.task_mode

    def _compute_stability(self, variance, profile):
        ratio = min(2.0, variance / max(profile["variance_hard"], 0.1))
        stability = 100 - (ratio * 52)
        return max(0, min(100, int(round(stability))))

    def _update_alert_state(self, rel, drift_hard, now):
        threshold = drift_hard + 2.0
        if rel > threshold:
            if self.alert_start is None:
                self.alert_start = now
            if now - self.alert_start > 0.8:
                return True
        else:
            self.alert_start = None
        return False

    def _compute_behavioral_alignment(self, rel, variance, profile):
        drift_penalty = min(46.0, (rel / max(profile["drift_soft"], 1.0)) * 24.0)
        motion_penalty = min(34.0, (variance / max(profile["variance_soft"], 0.1)) * 18.0)
        orientation_penalty = self.orientation_drift * 0.10
        movement_penalty = min(12.0, (self.movement_intensity / max(profile["movement_hard"], 0.1)) * 10.0)
        stability_penalty = (100 - self.current_stability) * 0.18
        switching_penalty = self.switching_index * 0.12
        trend_penalty = self.drift_trend * 0.08
        alert_penalty = 12.0 if self.is_alert else 0.0
        alignment = 100.0 - drift_penalty - motion_penalty - orientation_penalty - movement_penalty - stability_penalty - switching_penalty - trend_penalty - alert_penalty
        return round(max(0.0, min(100.0, alignment)), 1)

    def _classify_behavioral_level(self, rel, variance, profile):
        if self.is_alert or rel >= profile["drift_hard"] or self.behavioral_alignment < 42:
            return "misaligned"
        if rel >= profile["drift_soft"] or variance >= profile["variance_soft"] or self.behavioral_alignment < 72:
            return "drifting"
        return "aligned"

    def _compute_fatigue_risk(self, rel, variance, profile, now):
        passive_drift = rel >= profile["fatigue_drift"] and variance <= profile["fatigue_variance"]
        if passive_drift:
            if self.passive_drift_start is None:
                self.passive_drift_start = now
        else:
            self.passive_drift_start = None

        sustained_seconds = 0.0 if self.passive_drift_start is None else max(0.0, now - self.passive_drift_start)
        drift_floor = profile["fatigue_drift"] * 0.75
        drift_excess = max(0.0, rel - drift_floor)
        drift_scale = max(profile["drift_hard"] - drift_floor, 1.0)
        drift_ratio = min(1.0, drift_excess / drift_scale)
        low_motion_factor = 0.0
        if passive_drift:
            low_motion_factor = max(
                0.0,
                min(1.0, 1.0 - (variance / max(profile["fatigue_variance"] * 1.4, 0.1))),
            )
        slump_factor = min(1.0, sustained_seconds / 6.0) if passive_drift else 0.0
        fatigue = (drift_ratio * 26.0) + (low_motion_factor * 18.0) + (slump_factor * 38.0)
        if self.is_alert:
            fatigue += 8.0
        return round(max(0.0, min(100.0, fatigue)), 1)

    def _compute_drift_trend(self, profile):
        if len(self.history) < 6:
            return 0.0

        midpoint = len(self.history) // 2
        head_mean = float(np.mean(self.history[:midpoint]))
        tail_mean = float(np.mean(self.history[midpoint:]))
        drift_growth = max(0.0, tail_mean - head_mean)
        scale = max(profile["drift_soft"] * 0.55, 1.0)
        return round(min(100.0, (drift_growth / scale) * 100.0), 1)

    def _combine_relative_drift(self, rel_pitch, rel_yaw, rel_roll, profile):
        pitch_weight, yaw_weight, roll_weight = profile["axis_weights"]
        pitch_anchor = max(pitch_weight, 0.1)
        yaw_bonus = rel_yaw * (yaw_weight / pitch_anchor) * 0.55
        roll_bonus = rel_roll * (roll_weight / pitch_anchor) * 0.40
        return round(
            rel_pitch + yaw_bonus + roll_bonus,
            2,
        )

    def _compute_orientation_drift(self, rel_pitch, rel_yaw, rel_roll, profile):
        pitch_weight, yaw_weight, roll_weight = profile["axis_weights"]
        pitch_ratio = min(1.4, rel_pitch / max(profile["drift_soft"], 1.0))
        yaw_ratio = min(1.4, rel_yaw / max(profile["yaw_soft"], 1.0))
        roll_ratio = min(1.4, rel_roll / max(profile["roll_soft"], 1.0))
        weighted_ratio = (pitch_ratio * pitch_weight) + (yaw_ratio * yaw_weight) + (roll_ratio * roll_weight)
        return round(min(100.0, weighted_ratio * 68.0), 1)

    def _resolve_movement_intensity(self, previous_vector, explicit_intensity):
        if explicit_intensity is not None:
            try:
                return round(max(0.0, float(explicit_intensity)), 2)
            except Exception:
                pass

        previous_pitch, previous_yaw, previous_roll = previous_vector
        movement = abs(self.smooth_pitch - previous_pitch)
        movement += abs(self.smooth_yaw - previous_yaw)
        movement += abs(self.smooth_roll - previous_roll)
        return round(max(0.0, movement), 2)

    def _compute_switching_index(self, profile):
        if len(self.signed_history) < 4:
            return 0.0

        deadzone = profile["drift_soft"] * 0.22
        normalized = []
        for value in self.signed_history:
            if value > deadzone:
                normalized.append(1)
            elif value < -deadzone:
                normalized.append(-1)
            else:
                normalized.append(0)

        switches = 0
        active_pairs = 0
        previous = None
        for current in normalized:
            if current == 0:
                continue
            if previous is not None:
                active_pairs += 1
                if current != previous:
                    switches += 1
            previous = current

        if active_pairs == 0:
            return 0.0

        switch_ratio = switches / active_pairs
        step_delta = float(np.mean(np.abs(np.diff(self.signed_history))))
        amplitude_ratio = min(1.0, step_delta / max(profile["drift_soft"], 1.0))
        motion_ratio = min(1.0, float(np.mean(self.motion_history)) / max(profile["movement_soft"], 0.1))
        index = (switch_ratio * 58.0) + (amplitude_ratio * 22.0) + (motion_ratio * 20.0)
        return round(max(0.0, min(100.0, index)), 1)

    def _compute_uncertainty(self, variance, profile, now):
        warmup = max(0.0, (6 - min(self.samples_since_reset, 6)) / 6.0) * 42.0
        mode_transition = 0.0
        if self.mode_changed_at is not None:
            seconds_since_change = max(0.0, now - self.mode_changed_at)
            if seconds_since_change < 4.0:
                mode_transition = (1.0 - (seconds_since_change / 4.0)) * 24.0
            else:
                self.mode_changed_at = None

        volatility = 0.0
        if variance > profile["variance_hard"]:
            spread = max(profile["variance_hard"] * 0.8, 0.1)
            volatility = min(22.0, ((variance - profile["variance_hard"]) / spread) * 22.0)

        uncertainty = warmup + mode_transition + volatility
        return round(max(0.0, min(100.0, uncertainty)), 1)

    def _compute_cognitive_load(self, rel, variance, profile):
        drift_cost = min(48.0, (rel / max(profile["drift_hard"], 1.0)) * 34.0)
        motion_cost = min(34.0, (variance / max(profile["variance_hard"], 0.1)) * 24.0)
        orientation_cost = self.orientation_drift * 0.14
        movement_cost = min(12.0, (self.movement_intensity / max(profile["movement_hard"], 0.1)) * 11.0)
        stability_cost = (100 - self.current_stability) * 0.22
        alignment_cost = (100 - self.behavioral_alignment) * 0.18
        trend_cost = self.drift_trend * 0.14
        switching_cost = self.switching_index * 0.12
        fatigue_overlap = self.fatigue_risk * 0.1
        cognitive_load = drift_cost + motion_cost + orientation_cost + movement_cost + stability_cost + alignment_cost + trend_cost + switching_cost + fatigue_overlap
        if self.is_alert:
            cognitive_load += 10.0
        if (
            self.behavioral_alignment >= 76
            and self.fatigue_risk < 40
            and self.uncertainty_score < 45
            and self.switching_index < 38
            and 35 <= cognitive_load <= 72
        ):
            cognitive_load *= 0.9
        return round(max(0.0, min(100.0, cognitive_load)), 1)

    def _classify_load_reason(self, rel, variance):
        if self.fatigue_level == "high":
            return "high", "Possible fatigue slump"
        if self.uncertainty_score >= 55:
            return "low", "Signal warming up or mode transition"
        if self.state_hint == "productive_struggle":
            return "medium", "Aligned effort is high but still stable"
        if self.is_alert or self.cognitive_load >= 78 or self.behavioral_level == "misaligned":
            return "high", "Sustained behavior drift"
        if self.cognitive_load >= 46 or self.behavioral_level == "drifting":
            return "medium", "Behavior alignment is drifting"
        return "low", "Stable learning state"

    def _classify_state_hint(self):
        if self.uncertainty_score >= 55:
            return "signal_check"
        if self.fatigue_risk >= 65:
            return "fatigue_risk"
        if (
            self.is_alert
            or self.behavioral_level == "misaligned"
            or self.orientation_drift >= 72
            or (self.switching_index >= 48 and self.movement_intensity >= 4.0)
        ):
            return "off_task_risk"
        if (
            self.behavioral_alignment >= 76
            and self.fatigue_risk < 40
            and self.uncertainty_score < 45
            and self.switching_index < 38
            and self.drift_trend < 42
            and 35 <= self.cognitive_load <= 72
        ):
            return "productive_struggle"
        if self.behavioral_level == "drifting" or self.cognitive_load >= 46:
            return "load_rising"
        return "stable"

    def _classify_band(self, value, medium, high):
        if value >= high:
            return "high"
        if value >= medium:
            return "medium"
        return "low"

    def _classify_confidence(self, uncertainty_score):
        if uncertainty_score >= 55:
            return "low"
        if uncertainty_score >= 28:
            return "medium"
        return "high"
