# Project Overview

## System Position

Learning State Guardian is a study-process support system that uses **learning-state proxy** framing. It combines live sensing, interpreted logic, regulation, review, validation, and presentation support in one repo.

The project should be described as:

- a conservative learning-state proxy system
- a study-process replay and coaching workflow
- a smart-glasses-ready architecture for future Rokid integration

It should **not** be described as:

- precise attention detection
- mind reading
- psychological diagnosis

## Full System Structure

### 1. Real-Time Learning-State Sensing

Purpose:

- turn live posture and behavior signals into study-relevant proxy metrics
- attach first-person scene context when Rokid-style frame data is available

Main files:

- `core/posture.py`
- `core/rokid_frame_adapter.py`
- `core/rokid_adapter.py`

Outputs include:

- focus score
- cognitive-load proxy
- behavioral alignment
- fatigue risk proxy
- uncertainty score
- switching index
- first-person scene proxies

### 2. Interpreted Learning-State Logic Layer

Purpose:

- make state output more stable and explainable without replacing legacy logic

Main files:

- `core/state_interpreter.py`
- `core/state_transition_manager.py`

This layer adds:

- interpreted label
- confidence
- evidence
- uncertainty reason
- engagement / cognitive load / fatigue / signal quality axes
- transition stability rules

Legacy `state_hint` is preserved as a compatibility field.

### 3. Adaptive Focus Regulation

Purpose:

- turn the live proxy stream into guidance during the current study block

Main file:

- `core/focus_session.py`

This layer handles:

- focus vs recovery phase
- guidance text
- state label for live HUD support

### 4. Review / Heatmap

Purpose:

- help the learner replay the most meaningful strain segment after the session

Main files:

- `core/difficulty_marker.py`
- `analytics/analyze_report.py`
- `web/review.html`

This layer surfaces:

- difficulty events
- review summary
- heatmap asset
- next-step review cues

### 5. Learning-State Validation

Purpose:

- move from single-threshold snapshots toward windowed validation
- support human labels and optional baseline metrics

Main files:

- `core/state_feature_extractor.py`
- `core/state_classifier.py`
- `analytics/validate_learning_state.py`

This layer supports:

- state window features
- rule baseline
- optional sklearn baseline
- validation report and correlations

### 6. State Data Collection Protocol

Purpose:

- standardize how real session data and labels are collected

Main files:

- `docs/STATE_DATA_COLLECTION_PROTOCOL.md`
- `data/session_manifest_template.csv`
- `analytics/build_labeling_sheet.py`
- `analytics/summarize_validation_readiness.py`

This layer helps coordinate:

- session manifest records
- label drafts
- readiness reporting

### 7. Reflection Coach

Purpose:

- convert review and proxy evidence into reflection questions and next actions

Main files:

- `core/reflection_coach.py`
- `analytics/generate_reflection_report.py`
- `docs/REFLECTION_COACH.md`

This is a reflection support layer, not a diagnosis layer.

### 8. Demo Storyboard

Purpose:

- turn the system into a reproducible demonstration narrative

Main files:

- `core/demo_storyboard.py`
- `analytics/generate_demo_storyboard.py`
- `web/demo.html`
- `docs/DEMO_STORYBOARD.md`

Storyboard stages:

- `stable_focus`
- `load_rising`
- `productive_struggle`
- `off_task_risk`
- `recovery`

### 9. Presentation Assistant

Purpose:

- help package the repo into demo and defense material

Main files:

- `core/presentation_assistant.py`
- `analytics/generate_presentation_script.py`
- `docs/PRESENTATION_ASSISTANT.md`

Outputs include:

- short demo scripts
- defense Q&A
- metric explanations
- limitations

### 10. Rokid Integration Readiness

Purpose:

- keep the project ready for real smart-glasses input without rewriting the full stack

Current readiness points:

- first-person scene proxy interface already exists
- interpreted logic is separated from legacy sensing logic
- validation and labeling flow can absorb future Rokid sessions
- state data collection protocol can track capture conditions and session metadata

Future calibration can therefore focus on:

- real frame quality
- timestamp alignment
- session coverage
- label quality
- cross-user differences

## Recommended Reading Path

1. `README.md`
2. `docs/PROJECT_OVERVIEW.md`
3. `docs/LEARNING_STATE_VALIDATION.md`
4. `docs/STATE_DATA_COLLECTION_PROTOCOL.md`
5. `docs/REFLECTION_COACH.md`
6. `docs/DEMO_STORYBOARD.md`
7. `docs/PRESENTATION_ASSISTANT.md`
8. `docs/STATE_LOGIC_REFACTOR.md`
