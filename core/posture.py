import numpy as np
import time

class PostureEngine:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.base_pitch = 0.0
        self.smooth_pitch = 0.0
        self.history = [0.0] * 15
        self.alert_start = None
        self.is_alert = False
        self.current_stability = 100
        self.focus_score = 100
        self.cognitive_load = 0
        self.load_level = "low"
        self.load_reason = "Stable posture"

    def process(self, raw_pitch):
        self.smooth_pitch = (self.alpha * raw_pitch) + ((1 - self.alpha) * self.smooth_pitch)
        rel = abs(self.smooth_pitch - self.base_pitch)
        
        self.history.pop(0)
        self.history.append(rel)
        variance = np.var(self.history)
        self.current_stability = max(0, min(100, int(100 - variance * 4)))
        
        focus_score = max(0, 100 - (rel * 1.5) - (variance * 2))
        self.focus_score = round(focus_score, 1)
        cognitive_load = min(100, max(0, (rel * 1.7) + (variance * 2.4) + ((100 - self.current_stability) * 0.35)))
        
        if rel > 28.0:
            if not self.alert_start: self.alert_start = time.time()
            if time.time() - self.alert_start > 0.8: self.is_alert = True
        else:
            self.alert_start = None
            self.is_alert = False

        if self.is_alert:
            cognitive_load = min(100, cognitive_load + 15)

        self.cognitive_load = round(cognitive_load, 1)
        self.load_level, self.load_reason = self._classify_load(rel, variance)
            
        return {
            "relative_pitch": rel,
            "is_alert": self.is_alert,
            "focus_score": self.focus_score,
            "stability": self.current_stability,
            "cognitive_load": self.cognitive_load,
            "load_level": self.load_level,
            "load_reason": self.load_reason,
        }

    def calibrate(self):
        self.base_pitch = self.smooth_pitch

    def _classify_load(self, rel, variance):
        if self.is_alert or self.cognitive_load >= 75:
            return "high", "Sustained posture drift"
        if rel > 18 or variance > 12 or self.cognitive_load >= 45:
            return "medium", "Rising motion or reading effort"
        return "low", "Stable learning state"
