# State Logic Refactor

## Why split the state into four axes

The legacy `state_hint` is useful for lightweight feedback, but it compresses several different signals into a single label. This refactor adds a more explainable interpretation layer that keeps the original engines intact while separating the proxy into four axes:

- `engagement_score`: whether posture, alignment, and scene anchoring still look compatible with active study behavior
- `cognitive_load_score`: whether the current learning segment looks easy, rising, or effortful
- `fatigue_score`: whether the segment looks more like conceptual difficulty or a fatigue-like slump
- `signal_quality_score`: whether the underlying posture and first-person scene proxy is strong enough to trust cautiously

This helps future Rokid calibration because we can adjust axis weighting and transition rules without rewriting `PostureEngine`, `FocusSessionEngine`, or `DifficultyEventMarker`.

## Productive struggle vs off-task risk

`productive_struggle` and `off_task_risk` can both happen during higher load, but they are not the same:

- `productive_struggle` means the cognitive-load proxy is elevated while engagement and scene anchoring still look relatively strong
- `off_task_risk` means switching pressure rises while engagement, scene lock, or study-surface support drop

The system therefore treats challenge plus alignment differently from challenge plus drift. This is still a learning-state proxy, not a direct measurement of attention.

## Valid learning switch vs off-task switch

Some switching is valid. For example:

- note-taking while alternating between notebook and screen
- review while moving between question stem and answer area
- short material checks during a tightly anchored task

The refactor adds:

- `valid_learning_switch`: switching that still looks compatible with learning flow
- `off_task_switch`: switching that looks more like target drift

This is meant to reduce false alarms in note-taking or review scenarios without removing the original legacy `state_hint`.

## Why use a transition manager

Single-snapshot proxy labels can jitter when signals are noisy. A transition manager helps by adding:

- minimum enter time
- minimum exit time
- cooldown time
- per-label persistence rules

This makes the displayed state more stable across `stable_focus`, `load_rising`, `off_task_risk`, and `fatigue_risk`, while still keeping the raw legacy logic available underneath.

## What changed in practice

- `core/state_interpreter.py` reorganizes current posture, scene, and session signals into explainable proxy labels, evidence, and axes
- `core/state_transition_manager.py` stabilizes the interpreted label over time
- `/status` now exposes interpreted fields in addition to the original `state_hint`
- `web/index.html` and `web/review.html` prefer `interpreted_state` when available, but safely fall back to legacy fields

## Smoke test

Run:

```bash
python analytics/smoke_state_interpreter.py
```

This prints several hand-built snapshots such as `stable_focus`, `productive_struggle`, `off_task_risk`, `fatigue_risk`, `signal_uncertain`, and `note_taking_valid_switch`.

## Important framing

This refactor does not claim precise attention detection. The project still uses:

- learning-state proxy estimation
- cognitive-load proxy estimation
- behavioral alignment
- first-person scene proxy

The output should be read as cautious interpretation support for review and calibration, not as mind reading or psychological diagnosis.
