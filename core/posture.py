import time

import numpy as np


class PostureEngine:
    TASK_PROFILES = {
        "lecture": {
            "drift_soft": 10.0,
            "drift_hard": 18.0,
            "variance_soft": 4.5,
            "variance_hard": 9.5,
            "fatigue_drift": 12.0,
            "fatigue_variance": 3.2,
        },
        "reading": {
            "drift_soft": 13.0,
            "drift_hard": 22.0,
            "variance_soft": 6.5,
            "variance_hard": 12.5,
            "fatigue_drift": 14.0,
            "fatigue_variance": 4.0,
        },
        "note-taking": {
            "drift_soft": 17.0,
            "drift_hard": 26.0,
            "variance_soft": 9.5,
            "variance_hard": 16.5,
            "fatigue_drift": 18.0,
            "fatigue_variance": 5.0,
        },
        "review": {
            "drift_soft": 15.0,
            "drift_hard": 24.0,
            "variance_soft": 8.0,
            "variance_hard": 14.0,
            "fatigue_drift": 16.0,
            "fatigue_variance": 4.4,
        },
    }

    def __init__(self, alpha=0.3, history_size=15):
        self.alpha = alpha
        self.history_size = history_size
        self.base_pitch = 0.0
        self.smooth_pitch = 0.0
        self.history = [0.0] * history_size
        self.signed_history = [0.0] * history_size
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

    def process(self, raw_pitch, now=None):
        now = time.time() if now is None else now
        profile = self.TASK_PROFILES[self.task_mode]

        self.samples_since_reset += 1
        self.smooth_pitch = (self.alpha * raw_pitch) + ((1 - self.alpha) * self.smooth_pitch)
        signed_delta = self.smooth_pitch - self.base_pitch
        rel = abs(signed_delta)

        self.history.pop(0)
        self.history.append(rel)
        self.signed_history.pop(0)
        self.signed_history.append(signed_delta)

        variance = float(np.var(self.history))

        self.current_stability = self._compute_stability(variance, profile)
        self.is_alert = self._update_alert_state(rel, profile["drift_hard"], now)
        self.behavioral_alignment = self._compute_behavioral_alignment(rel, variance, profile)
        self.behavioral_level = self._classify_behavioral_level(rel, variance, profile)
        self.fatigue_risk = self._compute_fatigue_risk(rel, variance, profile, now)
        self.fatigue_level = self._classify_band(self.fatigue_risk, medium=38, high=65)
        self.uncertainty_score = self._compute_uncertainty(variance, profile, now)
        self.confidence_level = self._classify_confidence(self.uncertainty_score)
        self.cognitive_load = self._compute_cognitive_load(rel, variance, profile)
        self.focus_score = round(
            max(0.0, min(100.0, (self.behavioral_alignment * 0.65) + ((100 - self.cognitive_load) * 0.35))),
            1,
        )
        self.load_level, self.load_reason = self._classify_load_reason(rel, variance)

        return {
            "relative_pitch": rel,
            "signed_pitch_delta": round(signed_delta, 2),
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
        }

    def calibrate(self):
        self.base_pitch = self.smooth_pitch
        self.reset_tracking(preserve_baseline=True)

    def reset_tracking(self, preserve_baseline=True):
        if preserve_baseline:
            self.smooth_pitch = self.base_pitch
        else:
            self.base_pitch = self.smooth_pitch
        self.history = [0.0] * len(self.history)
        self.signed_history = [0.0] * len(self.signed_history)
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

    def set_task_mode(self, task_mode, now=None):
        normalized = str(task_mode or "").strip().lower()
        if normalized not in self.TASK_PROFILES:
            return self.task_mode

        if normalized == self.task_mode:
            return self.task_mode

        now = time.time() if now is None else now
        self.task_mode = normalized
        current_rel = abs(self.smooth_pitch - self.base_pitch)
        current_signed = self.smooth_pitch - self.base_pitch
        self.history = [current_rel] * len(self.history)
        self.signed_history = [current_signed] * len(self.signed_history)
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
        stability_penalty = (100 - self.current_stability) * 0.18
        alert_penalty = 12.0 if self.is_alert else 0.0
        alignment = 100.0 - drift_penalty - motion_penalty - stability_penalty - alert_penalty
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
        stability_cost = (100 - self.current_stability) * 0.22
        alignment_cost = (100 - self.behavioral_alignment) * 0.18
        fatigue_overlap = self.fatigue_risk * 0.1
        cognitive_load = drift_cost + motion_cost + stability_cost + alignment_cost + fatigue_overlap
        if self.is_alert:
            cognitive_load += 10.0
        return round(max(0.0, min(100.0, cognitive_load)), 1)

    def _classify_load_reason(self, rel, variance):
        if self.fatigue_level == "high":
            return "high", "Possible fatigue slump"
        if self.uncertainty_score >= 55:
            return "low", "Signal warming up or mode transition"
        if self.is_alert or self.cognitive_load >= 78 or self.behavioral_level == "misaligned":
            return "high", "Sustained behavior drift"
        if self.cognitive_load >= 46 or self.behavioral_level == "drifting":
            return "medium", "Behavior alignment is drifting"
        return "low", "Stable learning state"

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
