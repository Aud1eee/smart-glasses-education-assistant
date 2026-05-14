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

The current system uses:

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

This stage is best described as a **posture-based learning-state proxy**, not a final absolute attention detector. That wording is more rigorous for the graduation project.

### 3.3 Adaptive focus regulation

The real-time regulation logic is implemented in [core/focus_session.py](</C:/Users/11721/Desktop/focus_project_windows/core/focus_session.py:4>).

This engine converts raw state values into presentation-level labels and guidance, such as:

- `Focus settling`
- `Stable focus`
- `Load rising`
- `High load`
- `Regulate now`
- `Recovery`

The engine also gives action guidance such as:

- continue
- regulate
- slow down
- micro break
- recover focus

This is the core of part `B`, because it changes the system from passive monitoring into adaptive study support.

### 3.4 HUD interaction layer

The Flask service and the HUD are connected through:

- [app.py](</C:/Users/11721/Desktop/focus_project_windows/app.py:16>)
- [web/index.html](</C:/Users/11721/Desktop/focus_project_windows/web/index.html:204>)

The HUD shows:

- focus score
- cognitive load
- stability
- pitch delta
- current state label
- adaptive guidance
- session phase and time remaining

This allows the user to understand the current study state at a glance, which is especially suitable for smart-glasses-style display.

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

## 4. What the data means

The clean demonstration data is stored in:

- [demo_study_report.csv](</C:/Users/11721/Desktop/focus_project_windows/data/demo_study_report.csv>)
- [demo_difficulty_events.csv](</C:/Users/11721/Desktop/focus_project_windows/data/demo_difficulty_events.csv>)

This file is generated by running the same internal scoring logic used by the real system. It is not hand-written fake data.

The main fields are:

- `Session_ID`: which learning session this row belongs to
- `Timestamp`: sampling time
- `Relative_Pitch`: deviation from the calibrated pitch baseline
- `Stability`: short-window posture stability
- `Is_Alert`: whether sustained drift triggered an alert
- `Focus_Score`: focus proxy score
- `Cognitive_Load`: estimated cognitive load
- `Load_Level`: low / medium / high
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

This figure has three layers.

The event overlays are session-aware. In other words, if the log contains multiple study sessions, each difficulty event is drawn inside the correct session segment instead of being shifted back to the beginning of the full timeline.

### 5.1 Top chart: learning-state trend

The top chart shows:

- green line: `Focus score`
- yellow line: `Load comfort`, which is `100 - Cognitive_Load`
- red shaded background: high-load periods
- blue difficulty-event overlay labels such as `D1`

This layer answers:

> How did the learner's study state change over time?

And, if difficulty events are present:

> Which continuous segment should be reviewed first?

### 5.2 Middle band: cognitive-load heatmap

The middle band uses color to show the overall intensity of cognitive load:

- green: low load
- yellow: medium load
- red: high load

This is the most intuitive part of the figure, because it helps the audience quickly locate difficult periods.

### 5.3 Bottom chart: motion evidence

The bottom chart shows:

- blue line: `Pitch delta`
- light line: `Stability`
- yellow points: medium-load samples
- red points: high-load samples

This layer answers:

> Why did the system classify a time range as rising load or high load?

It provides a visible motion-based explanation for the state changes.

## 6. Current demo result

The latest generated clean demo summary is:

- samples: `349`
- average focus score: `66.7`
- average cognitive load: `42.3`
- high-load ratio: `37.0%`
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

> This module simulates and detects posture-related learning-state changes, provides adaptive guidance in real time, records the process as structured study-state data, and generates a heatmap afterward for reflection and review.

Recommended longer explanation:

> The completed module is Learning State Guardian. It includes cognitive load monitoring, adaptive focus regulation, and attention heatmap review. First, the system receives posture-related input and converts it into focus score, cognitive load, and load level. Then it provides real-time guidance through the HUD, such as stable focus, rising load, regulation, or recovery. At the same time, it records the full learning-state timeline. After the session, the recorded data is converted into a heatmap, which helps identify when the learner was stable, when the load rose, and which time periods are worth reviewing.

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
