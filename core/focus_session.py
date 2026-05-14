import time


class FocusSessionEngine:
    def __init__(self, focus_minutes=25, break_minutes=5):
        self.focus_duration = focus_minutes * 60
        self.break_duration = break_minutes * 60
        self.phase = "focus"
        self.phase_start = time.time()
        self.cycle_index = 1
        self.high_load_start = None
        self.low_load_start = time.time()
        self.last_guidance = "Keep learning steadily."
        self.last_action = "continue"

    def update(self, state):
        now = time.time()
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
            self.low_load_start = None
        else:
            self.high_load_start = None
            if level == "low" and self.low_load_start is None:
                self.low_load_start = now

        guidance, action = self._make_guidance(now, load, level, focus_score)
        self.last_guidance = guidance
        self.last_action = action

        return {
            "phase": self.phase,
            "phase_label": "Focus" if self.phase == "focus" else "Recovery",
            "cycle_index": self.cycle_index,
            "elapsed_seconds": elapsed,
            "remaining_seconds": max(0, int(duration - elapsed)),
            "progress": round(min(1, elapsed / duration), 3) if duration else 0,
            "guidance": guidance,
            "action": action,
        }

    def reset(self):
        self.phase = "focus"
        self.phase_start = time.time()
        self.cycle_index = 1
        self.high_load_start = None
        self.low_load_start = time.time()
        self.last_guidance = "Keep learning steadily."
        self.last_action = "continue"

    def _switch_phase(self, now):
        if self.phase == "focus":
            self.phase = "break"
        else:
            self.phase = "focus"
            self.cycle_index += 1
        self.phase_start = now
        self.high_load_start = None
        self.low_load_start = now

    def _make_guidance(self, now, load, level, focus_score):
        if self.phase == "break":
            if load < 35:
                return "Recovery looks good. Prepare for the next focus round.", "recover"
            return "Keep the break gentle until posture stabilizes.", "recover"

        if self.high_load_start and now - self.high_load_start >= 8:
            return "High load detected. Pause briefly and mark this moment.", "micro_break"
        if level == "high":
            return "Posture drift is high. Slow down and breathe.", "slow_down"
        if level == "medium" or focus_score < 45:
            return "Learning load is rising. Reduce switching and keep one target.", "regulate"
        if self.low_load_start and now - self.low_load_start >= 120:
            return "Deep focus is stable. Continue this rhythm.", "continue"
        return "Keep learning steadily.", "continue"
