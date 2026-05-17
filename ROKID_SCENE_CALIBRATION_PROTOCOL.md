# Rokid Scene Calibration Protocol

This document defines the recommended **standard calibration workflow** for the current first-person Rokid scene logic.

It is intended for:

- local threshold tuning
- repeatable thesis experiments
- future real-device calibration sessions
- defense demos that need a stable explanation path

## 1. Purpose

The current Rokid branch does not assume precise eye tracking or guaranteed raw IMU callbacks.

Instead, it works by deriving scene-level proxies from first-person frames, such as:

- `scene_content_score`
- `scene_text_score`
- `scene_stability_score`
- `scene_switch_rate`
- `study_surface_score`
- `scene_lock_score`

Because these proxies depend heavily on the actual learning surface, lighting, and switching behavior, they should be calibrated with a standard process rather than by ad hoc threshold edits.

## 2. Calibration principles

The calibration process should follow these rules:

1. Start from a built-in preset before making any manual threshold change.
2. Change only 1-2 related thresholds at a time.
3. Use short but stable first-person frame bursts instead of isolated frames.
4. Save each verified threshold set as a named profile.
5. Treat false `off_task_risk` and false `signal_check` as different problems.

## 3. Built-in presets

The debug page currently provides four starting presets:

- `Balanced Reading`
  Best default for books, printed notes, and general reading surfaces.

- `Screen Lecture`
  Better for PPT slides, projected content, and text-light screen material.

- `Notes Switching`
  Better for alternating between screen, book, and note page during note-taking.

- `Strict Review`
  Better for controlled demos where valid scene lock is expected and drift should be exposed quickly.

## 4. Standard scenario set

Every calibration run should cover these four scenarios.

### S1. Stable book reading

Goal:

- verify that a book or printed page can become scene-locked
- verify that the system stays near `stable` or `productive_struggle`

Start preset:

- `Balanced Reading`

Typical issues:

- content judged too sparse
- surface never locks
- stable reading still looks uncertain

First thresholds to try:

- `content_sparse_floor`
- `scene_locked_surface_floor`
- `scene_locked_lock_floor`
- `surface_expectation_bias`

### S2. Stable screen or PPT viewing

Goal:

- verify that screen-based learning does not collapse into sparse-signal logic

Start preset:

- `Screen Lecture`

Typical issues:

- slides rejected as too low-text
- stable screens still produce `signal_check`

First thresholds to try:

- `content_sparse_floor`
- `content_expectation_bias`
- `scene_locked_surface_floor`

### S3. Book-screen or notes switching

Goal:

- verify that valid note-taking does not instantly become `off_task_risk`

Start preset:

- `Notes Switching`

Typical issues:

- switching is over-penalized
- scene lock collapses after every short transition

First thresholds to try:

- `off_task_switch_floor`
- `lock_switch_ceiling`
- `productive_lock_floor`

### S4. Leaving the study area

Goal:

- verify that obvious departure from the learning target is actually detected

Start preset:

- `Strict Review`

Typical issues:

- off-task scenes remain falsely accepted
- signal response is too slow

First thresholds to try:

- `off_task_switch_floor`
- `scene_locked_lock_floor`
- `surface_expectation_bias`
- `lock_switch_ceiling`

## 5. Per-run checklist

For each scenario, record:

- task mode
- material type
- lighting
- capture source
- chosen preset
- changed thresholds
- observed `state_hint`
- final saved profile name

Use the worksheet generator if you want a ready-to-fill form:

- `.\generate_scene_calibration_sheet.ps1`

Output:

- `exports\rokid_scene_calibration_sheet.md`

## 6. Profile-saving rule

After a scenario becomes acceptable:

1. save the tuned result in the Rokid debug page
2. name it after the real use case
3. include lighting or material context in the note

Recommended naming style:

- `desk-reading-warm-light`
- `lecture-screen-daylight`
- `notes-switching-narrow-desk`

## 7. What counts as a good calibrated profile

A calibrated profile is acceptable when:

- valid study surfaces stop falling into `content_sparse` too often
- stable reading or screen viewing can lock after warmup
- note-taking transitions do not instantly become `off_task_risk`
- clearly leaving the study area still pushes the system toward `off_task_risk` or `signal_check`

## 8. Thesis-ready interpretation

The purpose of this protocol is not to claim perfect attention ground truth.

Instead, it provides a repeatable method for calibrating a **Rokid-constrained first-person scene proxy model** so that:

- stable study surfaces are accepted more consistently
- valid switching behavior is less likely to be over-penalized
- clearly off-task scenes remain detectable

This makes the current system more reproducible for:

- local device-side tuning
- scene-specific demo preparation
- graduation-project experiment reporting
