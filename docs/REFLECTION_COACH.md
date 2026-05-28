# Reflection Coach

`Reflection Coach` is a post-session reflection helper layered on top of the existing Learning State Guardian review flow.

It reads structured review artifacts such as:

- `review_summary`
- `difficulty_events`
- optional `data/state_window_features.csv`
- session guidance already captured in the review payload
- heatmap availability from exported review assets

The module is intentionally conservative.

- It uses learning-state proxies rather than claiming precise attention detection.
- It does not diagnose mental state, motivation, or learning ability.
- It is meant to support replay, reflection, and next-step planning after a study session.

## What It Produces

The Reflection Coach summary returns:

- `session_summary`
- `key_moments`
- `reflection_questions`
- `next_actions`
- `encouragement`

These outputs are generated with rule- and template-based logic only.

## Local API

The review page now reads:

- `GET /api/reflection_coach_summary`

This lightweight endpoint is separate from the richer:

- `GET /api/reflection_coach`

The summary endpoint is meant for the review page sidebar and keeps the wording focused on post-session reflection.

## Generate A Markdown Report

Run:

```bash
python analytics/generate_reflection_report.py
```

Optional examples:

```bash
python analytics/generate_reflection_report.py --dataset demo
python analytics/generate_reflection_report.py --dataset live --session-id your-session-id
python analytics/generate_reflection_report.py --features data/state_window_features.csv --output exports/reflection_report.md
```

The script reads from:

- `data/study_report.csv`
- or `data/demo_study_report.csv`

and writes:

- `exports/reflection_report.md`

## Graceful Fallback Behavior

- If no difficulty event exists, the coach falls back to session-wide rhythm and guidance cues.
- If no state-window features exist, the coach still works from review summary and difficulty markers.
- If no session data exists, the coach returns a clear setup message instead of pretending to infer a state.

## Review Page Intent

The `Reflection Coach` area in `web/review.html` is meant to answer:

- What was the overall session pattern?
- Which moments are most worth replaying?
- What questions should the learner ask after the session?
- What concrete next action should happen before the next block?

## Safety Boundary

Reflection Coach should always be described as:

- a post-session reflection aid
- a learning-state proxy layer
- a conservative interpretation of behavioral and scene evidence

It should not be described as:

- precise attention detection
- mind reading
- psychological diagnosis
- a replacement for tutoring or clinical judgment
