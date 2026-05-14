import time


class FocusSessionEngine:
    def __init__(
        self,
        focus_minutes=25,
        break_minutes=5,
        stable_focus_seconds=8,
        high_load_seconds=5,
        recovery_window_seconds=12,
    ):
        self.focus_duration = focus_minutes * 60
        self.break_duration = break_minutes * 60
        self.stable_focus_seconds = stable_focus_seconds
        self.high_load_seconds = high_load_seconds
        self.recovery_window_seconds = recovery_window_seconds
        self.phase = "focus"
        self.phase_start = time.time()
        self.cycle_index = 1
        self.high_load_start = None
        self.low_load_start = time.time()
        self.last_high_load_at = None
        self.last_guidance = "Keep learning steadily."
        self.last_action = "continue"
        self.last_state_label = "Focus settling"

    def update(self, state, now=None):
        now = time.time() if now is None else now
        duration = self.focus_duration if self.phase == "focus" else self.break_duration
        elapsed = int(now - self.phase_start)

        if elapsed >= duration:
            self._switch_phase(now)
            duration = self.focus_duration if self.phase == "focus" else self.break_duration
            elapsed = 0

        load = float(state.get("cognitive_load", 0))
        level = state.get("load_level", "low")
        focus_score = float(state.get("focus_score", 100))

        if level == "high":
            if self.high_load_start is None:
                self.high_load_start = now
            self.last_high_load_at = now
            self.low_load_start = None
        else:
            self.high_load_start = None
            if level == "low":
                if self.low_load_start is None:
                    self.low_load_start = now
            else:
                self.low_load_start = None

        guidance, action, state_label = self._make_guidance(now, load, level, focus_score)
        self.last_guidance = guidance
        self.last_action = action
        self.last_state_label = state_label

        return {
            "phase": self.phase,
            "phase_label": "Focus" if self.phase == "focus" else "Recovery",
            "cycle_index": self.cycle_index,
            "elapsed_seconds": elapsed,
            "remaining_seconds": max(0, int(duration - elapsed)),
            "progress": round(min(1, elapsed / duration), 3) if duration else 0,
            "guidance": guidance,
            "action": action,
            "state_label": state_label,
        }

    def reset(self, now=None):
        now = time.time() if now is None else now
        self.phase = "focus"
        self.phase_start = now
        self.cycle_index = 1
        self.high_load_start = None
        self.low_load_start = now
        self.last_high_load_at = None
        self.last_guidance = "Keep learning steadily."
        self.last_action = "continue"
        self.last_state_label = "Focus settling"

    def _switch_phase(self, now):
        if self.phase == "focus":
            self.phase = "break"
        else:
            self.phase = "focus"
            self.cycle_index += 1
        self.phase_start = now
        self.high_load_start = None
        self.low_load_start = now
        self.last_high_load_at = None

    def _make_guidance(self, now, load, level, focus_score):
        if self.phase == "break":
            if load < 35:
                return "Recovery looks good. Prepare for the next focus round.", "recover", "Recovery"
            return "Keep the break gentle until posture stabilizes.", "recover", "Recovery"

        recent_high = self.last_high_load_at and (now - self.last_high_load_at <= self.recovery_window_seconds)

        if level == "low" and recent_high and self.low_load_start and (now - self.low_load_start >= 2):
            return "Recovery is working. Rebuild a steady rhythm.", "recover_focus", "Recovery"

        if self.high_load_start and now - self.high_load_start >= self.high_load_seconds:
            return "High load detected. Pause briefly and mark this moment.", "micro_break", "Regulate now"
        if level == "high":
            return "Posture drift is high. Slow down and breathe.", "slow_down", "High load"
        if level == "medium" or focus_score < 45:
            return "Learning load is rising. Reduce switching and keep one target.", "regulate", "Load rising"
        if self.low_load_start and now - self.low_load_start >= self.stable_focus_seconds:
            return "Deep focus is stable. Continue this rhythm.", "continue", "Stable focus"
        return "Keep learning steadily.", "continue", "Focus settling"
