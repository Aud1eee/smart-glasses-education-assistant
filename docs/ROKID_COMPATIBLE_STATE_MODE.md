# Rokid Compatible State Mode

This note describes the conservative guard layer used when the Learning State Guardian is driven by `POST /api/v1/rokid/frame` without a measured head-pose signal or IMU.

## Purpose

The frame adapter can turn first-person video into useful scene cues such as:

- `study-surface lock`
- `scene-switch proxy`
- `scene stability`
- `content / text density`
- `tracking confidence`

Those are useful for a **scene-driven proxy**, but they should not be treated as measured IMU or a measured head-pose signal; keep them at conservative learning-state proxy strength.

## What A Single Image Can Say

A single frame should only be treated as:

- `scene_snapshot`
- or `signal_uncertain`

It can describe whether the scene looks like a readable study surface, whether blur or lighting are acceptable, and whether the scene appears visually anchored.

It should stay away from stronger claims about sustained focus, definitive off-task behavior, fatigue-risk indication without pose/IMU, or a measured head-pose signal.

## What Low-Frequency Continuous Frames Can Say

When the system receives a short valid run, for example:

- about `3-6 seconds`
- about `4-6 valid frames`
- with acceptable blur / brightness / scene stability

it can produce a **scene-driven learning-state proxy** such as:

- `stable_focus`
- `load_rising_proxy`
- `off_task_risk_proxy`

These are still conservative descriptions. In frame-only mode:

- `productive_struggle` is downgraded to `load_rising_proxy`
- `off_task_risk` is expressed only as `off_task_risk_proxy`
- `fatigue_risk` is not strongly asserted without measured pose or IMU

## Minimum Recommended Input

For a meaningful frame-only demo, the recommended minimum is:

- `3-6 seconds` of continuous input
- `4-6 valid frames`
- stable first-person study material such as a book, notes, slides, or a screen

If the frame run is shorter than that, the output should stay at `scene_snapshot` or `signal_uncertain`.

## Recommended Integration Order

The safest production-facing order is still:

1. connect `POST /api/v1/rokid/head-pose`
2. add low-frequency `POST /api/v1/rokid/frame`
3. treat frame-only mode as a conservative fallback or demo mode

Frame-only mode is helpful for scene awareness, but it should not be described as a substitute for IMU or a measured head-pose signal.
