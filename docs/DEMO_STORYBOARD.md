# Demo Storyboard

`Demo Storyboard` is a reproducible presentation layer for the current Learning State Guardian workflow.

It does not replace the existing HUD, review page, or Reflection Coach. Instead, it connects those parts into one presentation-friendly narrative with conservative wording.

## Purpose

The storyboard is designed to help a presenter explain the system in a clear sequence:

1. `stable_focus`
2. `load_rising`
3. `productive_struggle`
4. `off_task_risk`
5. `recovery`

The framing should stay conservative:

- use `learning-state proxy`
- use `cognitive load proxy`
- use `behavioral alignment`
- use `first-person scene proxy` when scene evidence is discussed

Do not describe the system as precisely detecting attention.

## What The Storyboard Uses

The generator reads from local project artifacts only:

- `data/demo_study_report.csv`
- or `data/study_report.csv`
- `data/demo_difficulty_events.csv`
- or `data/difficulty_events.csv`
- Reflection Coach summary logic
- optional `data/state_window_features.csv`

No external LLM call is required.

## Generate Demo Assets First

If you want a reproducible demo path, start with:

```bash
python analytics/generate_demo_assets.py
```

This prepares demo session artifacts that the review flow and storyboard can reuse.

## Generate The Markdown Storyboard

Run:

```bash
python analytics/generate_demo_storyboard.py
```

Optional examples:

```bash
python analytics/generate_demo_storyboard.py --dataset demo
python analytics/generate_demo_storyboard.py --dataset live
python analytics/generate_demo_storyboard.py --dataset demo --output exports/demo_storyboard.md
```

The output file is:

- `exports/demo_storyboard.md`

## Open The Demo Page

Start the local app:

```bash
python run.py --serve-only
```

Then open:

- `/demo?dataset=demo`
- or `/demo?dataset=live`

The page will fetch:

- `GET /api/demo_storyboard`

## Suggested Defense Flow

A simple presentation sequence is:

1. Show the HUD to explain real-time proxy signals.
2. Move to the review page to show the flagged difficulty window and heatmap.
3. Open Reflection Coach to show post-session reflection support.
4. Open Demo Storyboard to narrate the full arc from stable focus to recovery.

## How To Talk About The Stages

- `stable_focus`: the learner appears relatively settled and aligned with one target.
- `load_rising`: proxy signals suggest rising regulation pressure.
- `productive_struggle`: a brief high-challenge window still looks replayable, rather than fully fragmented.
- `off_task_risk`: switching, drift, or overload start to dominate the learning-state proxy.
- `recovery`: the session becomes steadier again and easier to coach.

## Guardrails

The storyboard should always be presented as:

- a demo narrative
- a conservative proxy interpretation layer
- a review and reflection aid

It should not be presented as:

- precise attention detection
- mind reading
- psychological diagnosis
- proof of exact learner intent
