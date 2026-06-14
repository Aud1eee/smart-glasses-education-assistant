# Learning State Guardian

Learning State Guardian is a conservative **learning-state proxy** project for smart-glasses-ready study sensing, interpretable state explanation, adaptive regulation, review, validation, and demo support.

## Project Positioning

This repository focuses on one question:

How can observable posture, behavioral alignment, and first-person scene cues be turned into a useful learning-process replay and coaching loop?

The current answer is an **interpretable learning-state sensing** workflow:

- real-time posture and scene-based sensing
- interpreted state explanation with anti-jitter handling
- adaptive focus regulation
- difficulty segment marking
- review and heatmap replay
- optional validation and labeling support
- post-session reflection and presentation packaging

## Core Features

- live sensing of posture, drift, stability, cognitive-load proxy, fatigue-risk proxy, uncertainty, and switching pressure
- first-person scene proxy extraction for scene content, text density, surface quality, scene lock, blur, and brightness
- interpreted state output with confidence, evidence, uncertainty reason, and anti-jitter transition rules
- adaptive focus guidance and recovery support during the study block
- difficulty-event marking for sustained high-load or review-worthy segments
- review, heatmap, and evidence surfaces for after-session replay
- validation workflow for window features, manual labels, and readiness summaries
- Reflection Coach, Demo Storyboard, and Presentation Assistant for post-session explanation and defense prep

## System Architecture

- `core/`: sensing, interpreted state logic, regulation, difficulty marking, reflection, storyboard, and presentation support
- `analytics/`: demo generation, validation, labeling-sheet generation, readiness checks, and smoke utilities
- `web/`: live HUD, review page, reflection page, demo page, and presentation helper page
- `utils/`: storage and presentation-support helpers
- `docs/`: system overview, validation, data collection, reflection, storyboard, presentation, and merge-planning docs
- `scripts/`: GitHub-ready PowerShell entrypoints for demo and validation pipelines
- `tests/smoke/`: lightweight verification for the interpreted state layer and major app summaries

## Directory Structure

```text
.
├─ app.py
├─ run.py
├─ core/
├─ analytics/
├─ web/
├─ utils/
├─ docs/
│  ├─ archive/
│  └─ research/
├─ scripts/
│  └─ legacy/
├─ tests/
│  └─ smoke/
├─ images/
└─ data/
   ├─ demo_study_report.csv
   ├─ demo_difficulty_events.csv
   └─ state_labels_template.csv
```

## Quick Start

Run the Flask app:

```bash
python run.py --serve-only
```

Open:

- `http://127.0.0.1:5000/`
- `http://127.0.0.1:5000/review`
- `http://127.0.0.1:5000/reflection`
- `http://127.0.0.1:5000/demo`
- `http://127.0.0.1:5000/presentation`

Windows helper scripts:

```powershell
.\scripts\run_demo_pipeline.ps1
.\scripts\run_validation_pipeline.ps1
```

## Demo Pipeline

Deterministic demo generation:

```bash
python analytics/generate_demo_assets.py
python analytics/generate_reflection_report.py
python analytics/generate_demo_storyboard.py
python analytics/generate_presentation_script.py
```

Main local outputs:

- `data/demo_study_report.csv`
- `data/demo_difficulty_events.csv`
- `exports/reflection_report.md`
- `exports/demo_storyboard.md`
- `exports/presentation_script_3min.md`
- `exports/presentation_script_5min.md`
- `exports/defense_qa.md`

## Validation Pipeline

Validation and labeling workflow:

```bash
python analytics/validate_learning_state.py
python analytics/build_labeling_sheet.py
python analytics/summarize_validation_readiness.py
```

Main local outputs:

- `data/state_labels_template.csv`
- `data/state_labels_draft.csv`
- `data/state_window_features.csv`
- `exports/state_validation_report.md`
- `exports/state_validation_metrics.json`
- `exports/validation_readiness.md`

## Reflection Coach / Demo Storyboard / Presentation Assistant

- Reflection Coach turns review summaries, difficulty events, and proxy evidence into reflection questions and next actions.
- Demo Storyboard turns the project into a reproducible five-stage narrative for demos and defenses.
- Presentation Assistant packages the project into short scripts, metric explanations, defense Q&A, and limitations.

## Limitations

- all state outputs remain **learning-state proxies**
- the project should be described as **interpretable learning-state sensing proxy** with conservative scene-driven wording
- no gaze, blink, fixation, or pupil pipeline is required in the current baseline
- validation quality depends on real session coverage, label quality, and cross-user calibration
- first-person scene proxies can degrade under blur, low visibility, unstable camera motion, or material-specific lighting conditions

## Related Docs

- `docs/PROJECT_OVERVIEW.md`
- `docs/LEARNING_STATE_VALIDATION.md`
- `docs/STATE_DATA_COLLECTION_PROTOCOL.md`
- `docs/REFLECTION_COACH.md`
- `docs/DEMO_STORYBOARD.md`
- `docs/PRESENTATION_ASSISTANT.md`
- `docs/STATE_LOGIC_REFACTOR.md`
- `docs/BRANCH_MERGE_PLAN.md`
- `docs/archive/`
- `docs/research/`
