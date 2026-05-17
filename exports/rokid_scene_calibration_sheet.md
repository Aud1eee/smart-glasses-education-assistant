# Rokid Scene Calibration Worksheet

Generated: 2026-05-17 20:59:42

Use this worksheet together with:

- `http://127.0.0.1:5000/rokid_debug`
- the built-in scene presets
- the saved-profile workflow in the Rokid debug page

## Standard flow

1. Choose the target scenario below.
2. Start from the recommended preset.
3. Feed a short, stable first-person frame sequence.
4. Watch `scene_content`, `study_surface`, `scene_lock`, `scene_switch`, and `state_hint`.
5. Make only 1-2 threshold changes at a time.
6. Save the tuned profile with a clear scenario-specific name.

## Global notes

- Record lighting, distance, and material type each time.
- Prefer one tuned profile per task mode and scene family.
- Do not overwrite a working profile until a new one is verified in at least two short runs.

## S1. Stable book reading

- Task mode: `reading`
- Recommended preset: `Balanced Reading`
- Goal: Confirm that a stable first-person textbook or printed page scene becomes scene-locked and stays in stable or productive-struggle states.

### Expected behavior

- `scene_content_score` and `study_surface_score` remain clearly non-zero
- `scene_lock_score` rises after a short warmup
- `state_hint` trends toward `stable` or `productive_struggle`, not `off_task_risk`

### First tuning moves if it looks wrong

- If the page keeps looking sparse, lower `content_sparse_floor` or `surface_expectation_bias`.
- If the page is visible but never locks, lower `scene_locked_surface_floor` and `scene_locked_lock_floor`.

### Run record

- Material / environment:
- Lighting:
- Camera / capture source:
- Final chosen preset:
- Final threshold changes:
- Observed `state_hint` progression:
- Was the behavior acceptable? (`yes / partly / no`):
- Saved profile name:
- Notes:

## S2. Stable screen or PPT viewing

- Task mode: `lecture`
- Recommended preset: `Screen Lecture`
- Goal: Check that slides or screen content with lower text density are still treated as valid learning scenes.

### Expected behavior

- Medium content scenes do not collapse into `content_sparse` too early
- `state_hint` stays away from `signal_check` once the screen is stable
- `off_task_risk` is not triggered merely because the slide has less dense text than a book page

### First tuning moves if it looks wrong

- If slides are rejected as sparse, lower `content_sparse_floor`.
- If stable screen viewing still feels too strict, lower `scene_locked_surface_floor` and reduce `content_expectation_bias`.

### Run record

- Material / environment:
- Lighting:
- Camera / capture source:
- Final chosen preset:
- Final threshold changes:
- Observed `state_hint` progression:
- Was the behavior acceptable? (`yes / partly / no`):
- Saved profile name:
- Notes:

## S3. Book-screen or notes switching

- Task mode: `note-taking`
- Recommended preset: `Notes Switching`
- Goal: Separate valid note-taking switches from genuine off-task drift.

### Expected behavior

- `scene_switch_rate` increases, but the system does not instantly classify the session as off-task
- `state_hint` may move through `load_rising` or `productive_struggle` rather than always `off_task_risk`
- Recovered stable frames can relock after short switching bursts

### First tuning moves if it looks wrong

- If valid note-taking is penalized too quickly, raise `off_task_switch_floor`.
- If scene lock drops on every switch, raise `lock_switch_ceiling` or lower `productive_lock_floor` slightly.

### Run record

- Material / environment:
- Lighting:
- Camera / capture source:
- Final chosen preset:
- Final threshold changes:
- Observed `state_hint` progression:
- Was the behavior acceptable? (`yes / partly / no`):
- Saved profile name:
- Notes:

## S4. Leaving the study area

- Task mode: `reading`
- Recommended preset: `Strict Review`
- Goal: Verify that looking away from the learning surface does raise `off_task_risk` or `signal_check` in a timely way.

### Expected behavior

- Content and surface scores drop when the learning target leaves the view
- `state_hint` moves toward `off_task_risk` or `signal_check`
- The system does not remain falsely scene-locked after the user clearly leaves the study surface

### First tuning moves if it looks wrong

- If off-task scenes remain too tolerant, lower `off_task_switch_floor` and tighten `scene_locked_lock_floor`.
- If the system reacts too slowly, raise `surface_expectation_bias` or lower `lock_switch_ceiling`.

### Run record

- Material / environment:
- Lighting:
- Camera / capture source:
- Final chosen preset:
- Final threshold changes:
- Observed `state_hint` progression:
- Was the behavior acceptable? (`yes / partly / no`):
- Saved profile name:
- Notes:

## Final summary

- Which preset worked best overall?
- Which scenario produced the most false positives?
- Which threshold changed most often?
- Which profile should be used for future Rokid demos?
