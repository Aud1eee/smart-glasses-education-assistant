# Project Explanation Draft

This document is the long-term explanation draft for the graduation project.

Use it as the main place to accumulate:

- module explanations
- demo logic
- data interpretation
- heatmap interpretation
- presentation-ready wording

## 1. Project positioning

This project is an **AI-enhanced education assistant for smart glasses**, oriented to the Rokid glasses scenario.

Its current core direction is not only content assistance, but also:

- learning-state sensing
- adaptive regulation
- after-class review support

At this stage, the main completed module is:

**Learning State Guardian**

It includes:

- `A` Cognitive load monitoring
- `B` Adaptive focus timer
- `C` Attention heatmap review
- `D` Difficulty event marking
- `E` Difficulty review and catch-up page

Recommended one-line description:

> Existing AI learning assistants mostly focus on what content to give students. This module focuses on whether the student is still in a good state to learn, when regulation is needed, and where review should happen afterward.

## 2. What this completed module does

The completed A/B/C module forms a closed loop:

1. collect posture-related learning-state signals
2. estimate focus score and cognitive load
3. generate real-time guidance on the HUD
4. record the learning-state timeline as structured data
5. produce a heatmap for after-class reflection
6. mark sustained difficulty segments for later review

In simple terms:

- `A` understands the learner's current state
- `B` regulates the learning rhythm in real time
- `C` visualizes the learning process afterward
- `D` identifies which segment was likely difficult
- `E` turns flagged segments into review priorities and catch-up suggestions

The current review page is now designed as a **presentation-ready after-class follow-up surface** rather than a plain debug panel. It includes:

- a session timeline that locates flagged segments in the full run
- an insight strip that summarizes the review priority in one glance
- a selected-event spotlight card for the currently focused difficulty segment
- a catch-up action panel for concrete replay guidance
- a heatmap export entry so the reviewer can jump from structured events to the full report image
- a cleaner editorial layout that reduces visual clutter and separates:
  - session summary
  - replay priority
  - detailed event list
  - supporting report assets

## 2.0 Independent follow-up module: Learning Reflection Coach

The project now also includes an independent module called:

**Learning Reflection Coach**

This module does not replace the main `Learning State Guardian` pipeline. Instead, it sits after the session and asks a different question:

> Given the learning-state evidence, how should the learner reflect on what happened and what should change in the next attempt?

Its input is:

- the structured study-session log
- the difficulty-event log
- the session summary already produced by the review layer
- an optional learner self-note or next-session goal

Its output is:

- a session signature such as productive challenge, switching drift, fatigue drag, signal check, or steady control
- a short coach memo
- reflection questions
- next-session experiments

This matters because it keeps the module differentiated from teammates' directions. It does not do:

- knowledge explanation
- AI tutor conversation
- writing guidance
- language tutoring
- AI note taking
- gesture input

Instead, it focuses on:

- metacognitive reflection
- self-regulation
- replay strategy
- study-process experimentation

The current runtime entry points are:

- `/reflection`
- `/api/reflection_coach`

The current implementation now uses a **switchable provider architecture**:

- `heuristic`
- `ollama`
- `remote`
- `openai`

This matters for future deployment. The reflection logic does not need to be rewritten when moving toward Rokid-side integration:

- for local free demos, it can use a local Ollama model
- for later deployment, it can switch to a remote API provider
- if no model is available, it still falls back to the heuristic coach

The evidence base still comes from the local learning-state logs. Model providers only refine the reflection wording and experiment framing.

## 2.1 Validation and experiment layer

The project now includes a **repeatable validation module** for the current learning-state algorithm.

Its purpose is not to prove absolute educational truth, but to verify that the current state engine behaves consistently across known simulated scenarios.

The validation layer includes:

- deterministic scenario checks for:
  - `stable`
  - `rising`
  - `overload`
  - `recovery`
- end-to-end demo pipeline checks using:
  - `demo_study_report.csv`
  - `demo_difficulty_events.csv`

The main outputs are:

- [validation_summary.md](</C:/Users/11721/Desktop/focus_project_windows/exports/validation_summary.md>)
- [validation_summary.json](</C:/Users/11721/Desktop/focus_project_windows/exports/validation_summary.json>)
- [THESIS_EXPERIMENT_DRAFT.md](</C:/Users/11721/Desktop/focus_project_windows/THESIS_EXPERIMENT_DRAFT.md>)

The validation launcher for Windows is:

- [generate_validation_report.ps1](</C:/Users/11721/Desktop/focus_project_windows/generate_validation_report.ps1>)

For paper writing and defense preparation, the preferred human-readable writeup is:

- [THESIS_EXPERIMENT_DRAFT.md](</C:/Users/11721/Desktop/focus_project_windows/THESIS_EXPERIMENT_DRAFT.md>)

## 2.2 Multimodal future-work framework

The next algorithm-development direction is no longer "make the posture score more complicated". Instead, the recommended route is to gradually expand the current posture proxy into a **multimodal learning-state framework**.

The preferred planning document is:

- [MULTIMODAL_FUTURE_WORK.md](</C:/Users/11721/Desktop/focus_project_windows/MULTIMODAL_FUTURE_WORK.md>)

The project also now includes a lightweight code-level blueprint:

- [multimodal_schema.py](</C:/Users/11721/Desktop/focus_project_windows/core/multimodal_schema.py>)
- `/api/multimodal_blueprint`

This blueprint separates the future system into four branches:

- behavioral alignment
- cognitive effort
- fatigue risk
- confidence / uncertainty

## 2.3 Latest judgment-method upgrade

The latest posture-proxy version no longer relies only on "how large the drift is" at a single moment.

It now adds two temporal features:

- `drift_trend`
  - whether posture drift is building up over the recent history window
- `switching_index`
  - whether the learner is repeatedly switching targets instead of holding one stable learning direction

Based on these features, the algorithm now exposes a `state_hint` layer that helps distinguish different meanings behind similar load levels:

- `stable`
- `load_rising`
- `productive_struggle`
- `off_task_risk`
- `fatigue_risk`
- `signal_check`

## 2.4 Rokid first-person scene adapter

The project no longer assumes that Rokid can directly provide stable raw head-pose or self-face signals to the application layer.

Instead, the current Rokid path is designed around a more realistic assumption:

- the glasses can provide first-person images or video frames
- the backend derives scene-level learning proxies from those frames

The current frame-driven scene adapter focuses on:

- `scene_content_score`
- `scene_text_score`
- `scene_stability_score`
- `scene_switch_rate`
- `study_surface_score`
- `scene_lock_score`

These metrics are then folded into the main learning-state logic to influence:

- `behavioral_alignment`
- `cognitive_load`
- `uncertainty_score`
- `state_hint`

This means the Rokid branch is currently best described as:

> a first-person scene-driven learning-state proxy, rather than a direct physiological attention detector.

## 2.5 Rokid scene tuning page

To make the first-person logic adjustable without changing source code, the project now includes a runtime tuning surface:

- [rokid_debug.html](</C:/Users/11721/Desktop/focus_project_windows/web/rokid_debug.html>)

The tuning page can:

- inspect the current posture-side scene thresholds
- inspect the current frame-adapter thresholds
- apply new threshold values at runtime
- reset all tuning values back to defaults

The related APIs are:

- `/api/rokid_scene_tuning`
- `/api/rokid_scene_tuning/reset`

This is useful for:

- local parameter calibration
- future Rokid device-side debugging
- thesis and presentation explanation of how scene thresholds are controlled

The tuning page now also includes a **scene calibration workflow**:

- preset-based starting points for:
  - `Balanced Reading`
  - `Screen Lecture`
  - `Notes Switching`
  - `Strict Review`
- diagnosis cards that explain whether the current first-person scene is:
  - too sparse
  - too dim or blurred
  - too strict to lock
  - too switch-sensitive for note-taking

The related calibration APIs are:

- `/api/rokid_scene_calibration`
- `/api/rokid_scene_tuning/preset`

The calibration layer is now also **persistent**. A tuned first-person threshold set can be:

- saved as a named local profile
- reloaded in later sessions
- exported as JSON for reporting or device-side replay

The related profile APIs are:

- `/api/rokid_scene_profiles`
- `/api/rokid_scene_profiles/save`
- `/api/rokid_scene_profiles/load`
- `/api/rokid_scene_profiles/export`

The local profile store is:

- `data/rokid_scene_profiles.json`

The project now also includes a **standardized Rokid calibration method**:

- [ROKID_SCENE_CALIBRATION_PROTOCOL.md](</C:/Users/11721/Desktop/focus_project_windows/ROKID_SCENE_CALIBRATION_PROTOCOL.md>)
- [generate_scene_calibration_sheet.ps1](</C:/Users/11721/Desktop/focus_project_windows/generate_scene_calibration_sheet.ps1>)

The protocol defines four standard first-person scenarios:

- stable book reading
- stable screen or PPT viewing
- book/screen or note-switching
- clearly leaving the study area

This matters because it turns scene tuning from ad hoc threshold editing into a repeatable experiment workflow.

This upgrade is important because the system no longer treats every medium/high load state as a negative event.

In particular:

- `productive_struggle` means the learner is still behaviorally aligned, but effort is clearly elevated
- `off_task_risk` means drift and switching are rising in a way that is more consistent with lost alignment

This makes the current prototype more educationally meaningful, because it is better at separating:

- "working hard on a difficult concept"
- from "drifting away from the learning target"

The upgraded state semantics are no longer isolated inside the scoring function. They are now reflected in:

- CSV report fields
- heatmap summary ratios
- review-page insight cards
- timeline risk lanes
- event spotlight and catch-up wording

Its purpose is to prove that future multimodal work has already been structured at the architecture level, even though device-side signals such as gaze, eye openness, blink, and pupil-related features are not active yet in the current prototype.

## 3. Completed submodules

### 3.1 Deterministic demo simulator

The simulator is implemented in [simulate_motion.py](</C:/Users/11721/Desktop/focus_project_windows/simulate_motion.py:1>).

Its role is to produce a **repeatable demo sequence** instead of random-only motion.

It now supports four key presentation states:

- `stable`
- `rising`
- `overload`
- `recovery`

The default presentation sequence is:

- stable focus
- rising cognitive load
- high-load regulation
- recovery

This is important because it makes the project easier to demonstrate in a graduation defense setting. The system no longer depends on accidental data changes during a live demo.

### 3.2 Learning-state scoring

The posture-based scoring logic is implemented in [core/posture.py](</C:/Users/11721/Desktop/focus_project_windows/core/posture.py:5>).

The current system now uses a **task-mode-aware posture proxy** instead of a single raw focus formula.

It still begins from posture input, but the output is now split into multiple interpretable signals.

Supported task modes are:

- `lecture`
- `reading`
- `note-taking`
- `review`

The current engine uses:

- smoothed pitch
- relative pitch offset from the calibrated baseline
- short-window variance
- stability estimation
- alert detection for sustained drift

The output includes:

- `Focus_Score`
- `Cognitive_Load`
- `Load_Level`
- `Load_Reason`
- `Behavioral_Alignment`
- `Behavioral_Level`
- `Fatigue_Risk`
- `Fatigue_Level`
- `Uncertainty_Score`
- `Confidence_Level`
- `Task_Mode`

The meaning of these outputs is:

- `Behavioral_Alignment`: whether current posture behavior still matches the intended study mode
- `Cognitive_Load`: whether regulation pressure is rising
- `Fatigue_Risk`: whether the learner may be entering a passive slump state
- `Uncertainty_Score`: whether the current estimate should be interpreted cautiously

The current implementation also includes two important safeguards:

- `Fatigue_Risk` has a zero-like baseline in steady posture, so stable behavior is not automatically treated as tiredness
- `Uncertainty_Score` is handled as a separate confidence dimension, rather than being directly mixed into `Load_Level`

This stage is best described as a **task-mode-aware, posture-based learning-state proxy**, not a final absolute attention detector. That wording is more rigorous for the graduation project.

### 3.3 Adaptive focus regulation

The real-time regulation logic is implemented in [core/focus_session.py](</C:/Users/11721/Desktop/focus_project_windows/core/focus_session.py:4>).

This engine converts raw state values into presentation-level labels and guidance, such as:

- `Focus settling`
- `Stable focus`
- `Load rising`
- `High load`
- `Regulate now`
- `Recovery`
- `Fatigue risk`
- `Signal check`

The engine also gives action guidance such as:

- continue
- regulate
- slow down
- micro break
- recover focus

This is the core of part `B`, because it changes the system from passive monitoring into adaptive study support.

After the recent refactor, the regulation logic no longer depends only on `load_level`. It also reacts to:

- fatigue risk
- signal confidence
- task-mode-aware alignment drift

### 3.4 HUD interaction layer

The Flask service and the HUD are connected through:

- [app.py](</C:/Users/11721/Desktop/focus_project_windows/app.py:16>)
- [web/index.html](</C:/Users/11721/Desktop/focus_project_windows/web/index.html:204>)

The current input layer exposes two runtime paths:

- `/api/v1/posture` for simulator-driven packets
- `/api/v1/rokid/head-pose` for Rokid-style head pose and IMU packets
- `/api/v1/rokid/frame` for first-person video frames or single-frame images

This keeps the active implementation aligned with realistic smart-glasses signals:

- `pitch / yaw / roll`
- optional `motion_intensity`
- optional `accel_magnitude / gyro_magnitude`
- `task_mode` as app-side learning context

When only frame or video input is available, the system now uses a **video-frame adapter** that derives coarse learning-state cues from first-person scene structure rather than from wearer-face detection.

The active scene logic now emphasizes:

- frame-to-frame scene motion
- content density and scene-text richness
- blur and brightness quality
- anchor stability across time
- scene switching rate
- study-surface confidence
- persistent scene lock across consecutive frames

This path should be described as a **scene-derived learning-state proxy**, not as precise eye tracking, native IMU telemetry, or direct face-based head-pose recovery.

In the current Windows bundled runtime, this frame path still depends on native OpenCV availability. If OpenCV is not available in that runtime, the endpoint remains useful as an interface scaffold, but the actual scene-driven proxy extraction will stay in a degraded `frame_unavailable` state until an OpenCV-capable runtime is used.

To support this path locally, `start_windows.ps1` now prefers a Python runtime that can successfully import `cv2`, which means the launcher will fall back to the project `.venv` when the bundled runtime does not provide native OpenCV support.

To make this path easier to inspect during development, the system now includes a dedicated **Rokid frame debug page**:

- `/rokid_debug`
- upload, local path, and demo-image probes for `/api/v1/rokid/frame`
- live cards for `tracking_state`, `tracking_confidence`, pose proxy, movement, `study_surface`, `scene_lock`, and `state_hint`
- quick navigation from the HUD (`K`) and from the review page (`Rokid Debug`)

For continuous local validation, the project now also includes a **frame-stream test chain**:

- `stream_rokid_frames.py`
- `start_rokid_frame_stream.ps1`

This chain reads from an image loop, a video file, or a camera source, then continuously posts frames into `/api/v1/rokid/frame`. It is meant to answer the practical question:

> If Rokid only gives us first-person frames or a video stream, can the learning-state pipeline continue running over time rather than only on single-frame probes?

The current HUD has been redesigned to better match a **Rokid-style near-eye display** rather than a desktop dashboard.

The main visual principles are:

- lens-first layout with a lighter center occlusion
- warm amber monochrome accents inspired by Rokid product visuals
- central state card for immediate guidance
- slim left and right rails for secondary data
- top task-mode capsules for quick switching and recognition

The HUD now supports two display views:

- `Glasses view`: low-occlusion mode intended for actual near-eye use
- `Demo view`: fuller information layout intended for presentations and defense demos

The HUD shows:

- behavior alignment / focus proxy
- cognitive load
- fatigue risk
- stability
- current state label
- adaptive guidance
- session phase and time remaining
- task mode
- confidence level
- difficulty marker and review note
- a lightweight Rokid sensor summary for `yaw / roll / movement`

The redesigned layout is intended to fit the logic of smart glasses:

- the center focuses on only the most important learning-state message
- side rails reduce central visual clutter
- confidence and task mode remain visible without blocking the main view
- Rokid-style sensor context is surfaced in a compact top-strip pill instead of a central card
- keyboard and clickable mode switching make demo interaction easier

In `Glasses view`, the HUD further reduces occlusion by:

- shrinking the main state card toward the upper-right area
- fading into a quieter compact state during stable learning
- hiding keyboard hint strips that are only useful during demos
- compressing side information into narrow edge docks
- showing difficulty emphasis only when a real event is active
- converting long guidance text into short glasses-style status vocabulary
- adding a dot-based signal language for alignment, load, fatigue, confidence, and difficulty

This makes the system easier to explain as a **glasses-oriented HUD prototype** rather than a general web dashboard.

For local Windows use, the launcher now defaults to a **serve-only mode**:

- `start_windows.ps1` runs `run.py --serve-only`
- the default VSCode profile `Run Focus Project` also uses this mode
- this keeps the Flask HUD alive for browser testing instead of dropping into the old console menu flow

If the analytics console menu is needed, it is still available through:

- `Run Focus Project Console`
- or a direct `python run.py`

### 3.5 Clean demo asset pipeline

The demo asset generation pipeline is implemented in:

- [analytics/generate_demo_assets.py](</C:/Users/11721/Desktop/focus_project_windows/analytics/generate_demo_assets.py:29>)
- [analytics/analyze_report.py](</C:/Users/11721/Desktop/focus_project_windows/analytics/analyze_report.py:9>)
- [generate_demo_assets.ps1](</C:/Users/11721/Desktop/focus_project_windows/generate_demo_assets.ps1:1>)

Its purpose is:

- generate a clean demo CSV
- generate a clean heatmap
- avoid overwriting the real study log

This is very useful for defense preparation, because it produces stable and reusable presentation material.

### 3.6 Difficulty event marker

The difficulty-event marker is implemented in [core/difficulty_marker.py](</C:/Users/11721/Desktop/focus_project_windows/core/difficulty_marker.py:4>).

Its purpose is to detect a **sustained difficult segment**, instead of only showing instantaneous load values.

The current logic watches for:

- medium load that lasts long enough
- high load that lasts long enough
- return to a stable state for event closure

The event output includes:

- event id
- severity
- start and end timestamps
- start and end sample indices
- duration
- peak load
- minimum focus
- peak pitch
- lowest stability
- primary trigger label
- trigger reason
- review note

In educational terms, this module tries to answer:

> Which part of the learning process was likely difficult enough to deserve review afterward?

This is important because the system now moves from general state monitoring to **difficulty localization**.

### 3.7 Difficulty review and catch-up page

The review page is implemented through:

- [app.py](</C:/Users/11721/Desktop/focus_project_windows/app.py:67>)
- [utils/storage.py](</C:/Users/11721/Desktop/focus_project_windows/utils/storage.py:213>)
- [web/review.html](</C:/Users/11721/Desktop/focus_project_windows/web/review.html:1>)

Its purpose is to convert difficulty-event logs into a **review-first action page**.

The current page provides:

- session-level summary
- difficulty-event list
- session timeline with event positioning
- event severity and time window
- task-mode context
- missed-content risk hint
- review note
- catch-up action suggestion

This makes the system more educationally complete, because the pipeline is no longer:

- detect state
- show status

It becomes:

- detect state
- identify difficult segments
- guide the learner on what to revisit next

## 4. What the data means

The clean demonstration data is stored in:

- [demo_study_report.csv](</C:/Users/11721/Desktop/focus_project_windows/data/demo_study_report.csv>)
- [demo_difficulty_events.csv](</C:/Users/11721/Desktop/focus_project_windows/data/demo_difficulty_events.csv>)

This file is generated by running the same internal scoring logic used by the real system. It is not hand-written fake data.

The main fields are:

- `Session_ID`: which learning session this row belongs to
- `Timestamp`: sampling time
- `Relative_Pitch`: deviation from the calibrated pitch baseline
- `Task_Mode`: the expected learning behavior mode
- `Stability`: short-window posture stability
- `Is_Alert`: whether sustained drift triggered an alert
- `Focus_Score`: focus proxy score
- `Cognitive_Load`: estimated cognitive load
- `Load_Level`: low / medium / high
- `Behavioral_Alignment`: posture-based task alignment score
- `Behavioral_Level`: aligned / drifting / misaligned
- `Fatigue_Risk`: fatigue-related risk estimate
- `Fatigue_Level`: low / medium / high
- `Uncertainty_Score`: caution level for the estimate
- `Confidence_Level`: low / medium / high confidence
- `Guidance`: real-time system guidance at that moment
- `Phase`: focus or break
- `Elapsed_Seconds`: elapsed session time
- `Cycle_Index`: which focus cycle the user is in

These fields together describe both:

- how the learner's posture-related state changes over time
- how the system responds to those state changes

The difficulty-event CSV adds another layer:

- which session the event belongs to
- which continuous segment was marked as difficult
- how long it lasted
- how strong the difficulty signal became
- what kind of review guidance should be attached to it

The session field is important because the project now supports **multiple resettable study sessions in one cumulative log file**. When the user recalibrates or resets the study cycle, the system starts a new `Session_ID` instead of mixing old and new samples into one ambiguous timeline.

## 5. How to explain the heatmap

The clean demonstration heatmap is stored in:

- [demo_attention_heatmap.png](</C:/Users/11721/Desktop/focus_project_windows/exports/demo_attention_heatmap.png>)

This figure now has four layers under the upgraded algorithm framework.

The event overlays are session-aware. In other words, if the log contains multiple study sessions, each difficulty event is drawn inside the correct session segment instead of being shifted back to the beginning of the full timeline.

### 5.1 Top chart: learning-state overview

The top chart shows:

- green line: `Behavioral alignment`
- yellow line: `Load comfort`, which is `100 - Cognitive_Load`
- blue line: `Fatigue comfort`, which is `100 - Fatigue_Risk`
- red shaded background: high-load periods
- gray shaded background: low-confidence / signal-check periods
- blue difficulty-event overlay labels such as `D1`

This layer answers:

> How did the learner's study state change over time?

And, if difficulty events are present:

> Which continuous segment should be reviewed first?

### 5.2 Middle band: risk heat bands

The middle band uses color to compare three kinds of risk:

- behavior alignment risk
- cognitive load
- fatigue risk

This helps the audience distinguish whether the system is reacting to drift, regulation pressure, or possible fatigue.

### 5.3 Third chart: confidence and task mode context

This chart shows:

- uncertainty score
- stability
- task-mode spans such as `lecture`, `reading`, `note-taking`, and `review`

This layer answers:

> Was the system highly confident at this point, and under which learning mode was the learner operating?

### 5.4 Bottom chart: motion evidence

The bottom chart shows:

- blue line: `Pitch delta`
- light line: `Stability`
- yellow points: medium-load samples
- red points: high-load samples
- blue cross markers: fatigue-risk samples

This layer answers:

> What posture-motion evidence supported the higher-level state interpretation?

It provides a visible motion-based explanation for the state changes.

## 6. Current demo result

The latest generated clean demo summary is:

- samples: `349`
- average behavioral alignment: `63.9`
- average focus proxy: `61.7`
- average cognitive load: `42.6`
- average fatigue risk: `30.6`
- high-load ratio: `36.7%`
- low-confidence ratio: `0.0%`
- difficulty events: `1`

The demo sequence can currently be interpreted as:

1. the learner starts in a stable study state
2. the learner enters a rising-load period
3. the learner reaches a high-load regulation period
4. the learner gradually returns to recovery
5. the system marks the long rising/high-load segment as one review-worthy difficulty event

This matches the intended A/B/C demonstration logic.

## 7. Recommended explanation for defense

Recommended short explanation:

> This module estimates task-mode-aware learning-state changes from posture-related signals, provides adaptive guidance in real time, records structured state data, and generates a report afterward for reflection and review.

Recommended longer explanation:

> The completed module is Learning State Guardian. It includes task-mode-aware behavioral alignment estimation, cognitive load monitoring, fatigue-risk estimation, and adaptive regulation. First, the system receives posture-related input and converts it into behavioral alignment, cognitive load, fatigue risk, and confidence indicators. Then it provides real-time guidance through the HUD, such as stable focus, signal check, load rising, regulation, fatigue risk, or recovery. At the same time, it records the full learning-state timeline. After the session, the recorded data is converted into a multi-layer report, which helps identify when behavior was aligned, when load rose, when signal confidence was low, and which time periods are worth reviewing.

Recommended wording for the difficulty-event marker:

> Beyond continuous monitoring, the system also identifies sustained difficult segments. If cognitive load keeps rising or remains high for long enough, the system groups that period into a difficulty event and records it separately. This helps transform raw state changes into concrete review targets.

## 8. How to extend this document later

When new modules are added later, continue extending this file with the same structure:

1. module name and positioning
2. implementation summary
3. input and output data
4. visualization or interaction result
5. how to explain it in a defense

Recommended future sections:

- OCR and vocabulary capture
- missed-content marking
- difficulty event markers
- Rokid device integration
- algorithm design evolution
