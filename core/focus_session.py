import time


class FocusSessionEngine:
    def __init__(
        self,
        focus_minutes=25,
        break_minutes=5,
        stable_focus_seconds=8,
        high_load_seconds=5,
        recovery_window_seconds=12,
        fatigue_trigger_seconds=4,
    ):
        self.focus_duration = focus_minutes * 60
        self.break_duration = break_minutes * 60
        self.stable_focus_seconds = stable_focus_seconds
        self.high_load_seconds = high_load_seconds
        self.recovery_window_seconds = recovery_window_seconds
        self.fatigue_trigger_seconds = fatigue_trigger_seconds
        self.phase = "focus"
        self.phase_start = time.time()
        self.cycle_index = 1
        self.high_load_start = None
        self.fatigue_start = None
        self.low_load_start = time.time()
        self.last_high_load_at = None
        self.last_guidance = "Keep learning steadily."
        self.last_action = "continue"
        self.last_state_label = "Focus settling"
        self.last_update_at = self.phase_start

    def update(self, state, now=None):
        now = time.time() if now is None else now
        self.last_update_at = now
        duration = self.focus_duration if self.phase == "focus" else self.break_duration
        elapsed = int(now - self.phase_start)

        if elapsed >= duration:
            self._switch_phase(now)
            duration = self.focus_duration if self.phase == "focus" else self.break_duration
            elapsed = 0

        load = float(state.get("cognitive_load", 0))
        level = state.get("load_level", "low")
        focus_score = float(state.get("focus_score", 100))
        fatigue_risk = float(state.get("fatigue_risk", 0))
        uncertainty = float(state.get("uncertainty_score", 0))
        behavioral_level = state.get("behavioral_level", "aligned")
        task_mode = state.get("task_mode", "reading")

        if level == "high" or fatigue_risk >= 65:
            if self.high_load_start is None:
                self.high_load_start = now
            self.last_high_load_at = now
            self.low_load_start = None
        else:
            self.high_load_start = None
            if (
                level == "low"
                and fatigue_risk < 40
                and uncertainty < 45
                and behavioral_level == "aligned"
            ):
                if self.low_load_start is None:
                    self.low_load_start = now
            else:
                self.low_load_start = None

        if fatigue_risk >= 50:
            if self.fatigue_start is None:
                self.fatigue_start = now
        else:
            self.fatigue_start = None

        guidance, action, state_label = self._make_guidance(
            now,
            load,
            level,
            focus_score,
            fatigue_risk,
            uncertainty,
            behavioral_level,
            task_mode,
        )
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
        self.fatigue_start = None
        self.low_load_start = now
        self.last_high_load_at = None
        self.last_guidance = "Keep learning steadily."
        self.last_action = "continue"
        self.last_state_label = "Focus settling"
        self.last_update_at = now

    def snapshot(self, now=None):
        now = time.time() if now is None else now
        duration = self.focus_duration if self.phase == "focus" else self.break_duration
        elapsed = int(now - self.phase_start)
        remaining = max(0, int(duration - elapsed))
        return {
            "phase": self.phase,
            "phase_label": "Focus" if self.phase == "focus" else "Recovery",
            "cycle_index": self.cycle_index,
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "progress": round(min(1, elapsed / duration), 3) if duration else 0,
            "guidance": self.last_guidance,
            "action": self.last_action,
            "state_label": self.last_state_label,
            "stale_seconds": round(max(0.0, now - self.last_update_at), 1),
        }

    def _switch_phase(self, now):
        if self.phase == "focus":
            self.phase = "break"
        else:
            self.phase = "focus"
            self.cycle_index += 1
        self.phase_start = now
        self.high_load_start = None
        self.fatigue_start = None
        self.low_load_start = now
        self.last_high_load_at = None

    def _make_guidance(
        self,
        now,
        load,
        level,
        focus_score,
        fatigue_risk,
        uncertainty,
        behavioral_level,
        task_mode,
    ):
        if self.phase == "break":
            if fatigue_risk >= 45:
                return "Use this recovery window to release fatigue before returning.", "recover", "Recovery"
            return "Recovery looks good. Prepare for the next focus round.", "recover", "Recovery"

        recent_high = self.last_high_load_at and (now - self.last_high_load_at <= self.recovery_window_seconds)

        if uncertainty >= 55:
            return (
                f"Signal confidence is still warming up for {task_mode}. Hold steady or recalibrate.",
                "signal_check",
                "Signal check",
            )

        if fatigue_risk >= 70:
            return "Possible fatigue slump detected. Take a short recovery pause.", "micro_break", "Fatigue risk"

        if self.fatigue_start and now - self.fatigue_start >= self.fatigue_trigger_seconds:
            return "Fatigue risk is staying elevated. Pause briefly before continuing.", "micro_break", "Fatigue risk"

        if level == "low" and recent_high and self.low_load_start and (now - self.low_load_start >= 2):
            return "Recovery is working. Rebuild a steady rhythm.", "recover_focus", "Recovery"

        if self.high_load_start and now - self.high_load_start >= self.high_load_seconds:
            return "High strain detected. Pause briefly and mark this segment.", "micro_break", "Regulate now"

        if level == "high":
            if fatigue_risk >= 45:
                return "Fatigue is mixing with drift. Slow down and rest your eyes.", "slow_down", "Fatigue risk"
            return "Behavior drift is high. Reduce switching and keep one target.", "slow_down", "High load"

        if level == "medium" or focus_score < 45 or behavioral_level == "drifting":
            return (
                f"Behavior alignment is drifting in {task_mode}. Reduce switching and keep one target.",
                "regulate",
                "Load rising",
            )

        if self.low_load_start and now - self.low_load_start >= self.stable_focus_seconds:
            return "Behavior is aligned and stable. Continue this rhythm.", "continue", "Stable focus"

        return "Keep one learning target and settle into the current mode.", "continue", "Focus settling"
