import time


class StateTransitionManager:
    """Stabilize interpreted proxy states over time.

    The goal is to reduce UI jitter and avoid overreacting to brief spikes in
    proxy signals while keeping the logic fully rule-based and inspectable.
    """

    DEFAULT_RULE = {
        "min_enter_seconds": 3.0,
        "min_exit_seconds": 2.0,
        "cooldown_seconds": 3.0,
    }

    DEFAULT_PER_LABEL_RULES = {
        "stable_focus": {"min_enter_seconds": 4.0, "min_exit_seconds": 2.5, "cooldown_seconds": 2.5},
        "load_rising": {"min_enter_seconds": 3.0, "min_exit_seconds": 2.0, "cooldown_seconds": 2.0},
        "productive_struggle": {"min_enter_seconds": 3.5, "min_exit_seconds": 2.0, "cooldown_seconds": 2.0},
        "off_task_risk": {"min_enter_seconds": 4.0, "min_exit_seconds": 3.0, "cooldown_seconds": 4.0},
        "fatigue_risk": {"min_enter_seconds": 4.0, "min_exit_seconds": 3.0, "cooldown_seconds": 4.5},
        "signal_uncertain": {"min_enter_seconds": 2.0, "min_exit_seconds": 1.5, "cooldown_seconds": 1.5},
    }

    def __init__(
        self,
        min_enter_seconds=3.0,
        min_exit_seconds=2.0,
        cooldown_seconds=3.0,
        per_label_rules=None,
    ):
        self.default_rule = {
            "min_enter_seconds": float(min_enter_seconds),
            "min_exit_seconds": float(min_exit_seconds),
            "cooldown_seconds": float(cooldown_seconds),
        }
        self.per_label_rules = {
            label: self._merged_rule(overrides)
            for label, overrides in self.DEFAULT_PER_LABEL_RULES.items()
        }
        if isinstance(per_label_rules, dict):
            for label, overrides in per_label_rules.items():
                if not isinstance(overrides, dict):
                    continue
                self.per_label_rules[str(label).strip()] = self._merged_rule(overrides)
        self.reset()

    def reset(self, now=None):
        now = time.time() if now is None else float(now)
        self.current_label = None
        self.current_entered_at = None
        self.pending_label = None
        self.pending_since = None
        self.last_transition_at = None
        self.transition_reason = "Transition manager is warming up and waiting for the first interpreted snapshot."
        return self.snapshot()

    def update(self, interpreted_state, now=None):
        now = time.time() if now is None else float(now)
        candidate_label = str((interpreted_state or {}).get("label") or "").strip() or "stable_focus"

        if self.current_label is None:
            self.current_label = candidate_label
            self.current_entered_at = now
            self.pending_label = None
            self.pending_since = None
            self.last_transition_at = now
            self.transition_reason = f"Initialized stable proxy label as {candidate_label} from the first interpreted snapshot."
            return self.snapshot()

        if candidate_label == self.current_label:
            self.pending_label = None
            self.pending_since = None
            self.transition_reason = f"Holding {self.current_label} because the current proxy evidence remains consistent."
            return self.snapshot()

        if self.pending_label != candidate_label:
            self.pending_label = candidate_label
            self.pending_since = now
            self.transition_reason = (
                f"Observed a candidate shift toward {candidate_label}; waiting for persistence before leaving {self.current_label}."
            )
            return self.snapshot()

        pending_elapsed = max(0.0, now - (self.pending_since or now))
        required_persistence = max(
            self.rule_for(candidate_label)["min_enter_seconds"],
            self.rule_for(self.current_label)["min_exit_seconds"],
        )
        cooldown_seconds = max(
            self.rule_for(candidate_label)["cooldown_seconds"],
            self.rule_for(self.current_label)["cooldown_seconds"],
        )
        time_since_last_transition = None
        if self.last_transition_at is not None:
            time_since_last_transition = max(0.0, now - self.last_transition_at)

        if time_since_last_transition is not None and time_since_last_transition < cooldown_seconds:
            self.transition_reason = (
                f"Cooling down after the last state change, so the display keeps {self.current_label} for now."
            )
            return self.snapshot()

        if pending_elapsed < required_persistence:
            self.transition_reason = (
                f"Candidate {candidate_label} has persisted for {pending_elapsed:.1f}s, which is below the {required_persistence:.1f}s threshold."
            )
            return self.snapshot()

        previous_label = self.current_label
        self.current_label = candidate_label
        self.current_entered_at = now
        self.pending_label = None
        self.pending_since = None
        self.last_transition_at = now
        self.transition_reason = (
            f"Switched from {previous_label} to {candidate_label} after {pending_elapsed:.1f}s of consistent proxy evidence."
        )
        return self.snapshot()

    def snapshot(self):
        return {
            "stable_label": self.current_label or "stable_focus",
            "display_label": self.current_label or "stable_focus",
            "transition_reason": self.transition_reason,
            "pending_label": self.pending_label,
        }

    def rule_for(self, label):
        normalized = str(label or "").strip()
        return dict(self.per_label_rules.get(normalized, self.default_rule))

    def _merged_rule(self, overrides):
        rule = dict(self.default_rule)
        for key in ("min_enter_seconds", "min_exit_seconds", "cooldown_seconds"):
            if key not in overrides:
                continue
            try:
                rule[key] = float(overrides[key])
            except Exception:
                continue
        return rule
