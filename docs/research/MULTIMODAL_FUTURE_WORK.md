# Multimodal Future Work Framework

This document explains how **Learning State Guardian** can evolve from its current posture-centered learning-state estimator into a more complete multimodal learning-state sensing system.

## 1. Current Stage Positioning

The current system already implements these core branches:

- `Behavioral_Alignment` based on posture and stability
- `Cognitive_Load` based on posture drift and variability
- `Fatigue_Risk` based on passive downward drift and low-motion windows
- `Confidence / Uncertainty` based on warmup and fluctuation patterns

Because of that, the most accurate description of the current version is:

**a task-mode-aware posture-proxy learning-state model**

not yet a full multimodal learning-state sensing system.

## 2. Why Multimodality Matters

Using posture alone has natural limits:

1. Looking down does not always mean the learner is disengaged.
2. Stable posture does not always mean the learner understands the material smoothly.
3. Fatigue, cognitive load, and distraction can be partially entangled at the posture level.
4. Posture-only signals still have limited explanatory power for real classroom learning states.

So the next step should not be “build an even more complicated posture score.” A better direction is to decompose learning state into several interpretable branches and gradually add more modalities.

## 3. Target Framework

The recommended multimodal framework has four branches.

### 3.1 Behavioral Alignment

Question answered:

> Is the current behavior aligned with the active learning task?

Signals already available:

- `pitch`
- `variance`
- `stability`
- `task_mode`

Planned additions:

- `yaw`
- `roll`
- `gaze_target`
- `face_presence`

### 3.2 Cognitive Effort

Question answered:

> Is the learner working through the content, or clearly drifting away from the learning goal?

Signals already available:

- posture drift cost
- posture fluctuation cost
- behavioral alignment loss

Planned additions:

- `pupil_feature`
- `blink_rate`
- `fixation_dwell`
- `reread_pattern`

### 3.3 Fatigue Risk

Question answered:

> Does the current state look more like fatigue, or more like active conceptual effort?

Signals already available:

- `passive_drift`
- `low_motion_window`
- `sustained_slump`

Planned additions:

- `eye_openness`
- `blink_duration_ms`
- `perclos`

### 3.4 Confidence / Uncertainty

Question answered:

> How reliable is the current estimate, and when should it be interpreted more cautiously?

Signals already available:

- `warmup_window`
- `variance_spike`
- `mode_transition`

Planned additions:

- `face_confidence`
- `gaze_confidence`
- `tracking_quality`

## 4. Final State Output

In the multimodal stage, the final output should move away from a single “focus score” and instead expose interpretable state labels such as:

- `Deep Focus`
- `Productive Struggle`
- `Off-Task Risk`
- `Fatigue Risk`
- `Uncertain`

This format fits a smart-glasses HUD better and is also easier to explain to teachers, reviewers, and thesis evaluators.

## 5. Rokid-Oriented Integration Path

To fit the Rokid glasses scenario, a three-phase path is recommended.

### Phase 1: Already Completed

- posture-proxy model
- task-mode-aware logic
- HUD, heatmap, difficulty events, and review page

### Phase 2: Lightweight Visual Expansion

Goals:

- integrate `face presence`
- integrate `face confidence`
- integrate `gaze proxy`
- integrate `eye openness`

The focus at this phase is not to build a heavy computer-vision stack immediately. The goal is to add basic signals about whether the learner is looking at a reasonable target and whether there are interpretable fatigue cues.

### Phase 3: Richer Ocular Features

Goals:

- `pupil_feature`
- `blink_rate`
- `blink_duration_ms`
- `perclos`

This is the stage where the system gets closer to a genuinely multimodal learning-state estimator.

## 6. Future-Work Hooks Already in the Codebase

The project already contains a lightweight multimodal blueprint layer:

- [core/multimodal_schema.py](../../core/multimodal_schema.py)

It also exposes an explanatory API:

- [app.py](../../app.py) route `/api/multimodal_blueprint`

The goal of that endpoint is not to participate in inference immediately. Instead, it makes three things explicit:

- which signals are already active now
- which modalities are planned next
- how multimodal fusion is expected to be layered over time

That helps show that the future-work story is backed by concrete engineering hooks rather than only verbal plans.

## 7. Thesis-Ready Future Work Paragraph

The paragraph below can be used as a starting point in a thesis future-work section:

> The current system mainly relies on posture-related features to build a task-mode-aware proxy model of learning state, enabling behavioral alignment estimation, cognitive-load monitoring, fatigue-risk estimation, and difficulty-event marking. However, posture-only signals remain limited, because posture changes cannot fully distinguish distraction, fatigue, and high cognitive load. Future work will therefore move toward a multimodal direction. While preserving the current posture branch, later versions will gradually integrate facial visibility, gaze proxies, eyelid openness, blink duration, PERCLOS, and pupil-related features, forming a four-branch fusion framework covering behavioral alignment, cognitive effort, fatigue risk, and confidence. This roadmap better matches the real input conditions of Rokid smart glasses and is more likely to improve the interpretability and robustness of learning-state estimation.

## 8. Defense-Friendly Spoken Version

You can explain it like this during a defense:

> At the moment, the system already completes posture-related learning-state estimation, but I do not describe it as a full multimodal system yet. The next step is to use Rokid glasses as the carrier and continue adding face presence, gaze proxy, and eye openness on top of the current posture branch, followed later by blink- and pupil-related features. In other words, the current version already delivers a backend prototype and validation platform, while the future-work path is to upgrade it step by step into a more rigorous multimodal learning-state sensing system.
