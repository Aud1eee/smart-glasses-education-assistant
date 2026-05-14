# Project Memory

Read this file first before exploring the rest of the project.

## Identity

- Project name: `Focus Project`
- Current presentation name: `Learning State Guardian`
- Domain: `AI glasses for education / Rokid glasses`
- Main environment for future work: `C:\Users\11721\Desktop\focus_project_windows`

## Team-positioning summary

The broader team topic is AI glasses empowering education.

Teammates' planned directions from the PPT were mainly content-oriented:

- knowledge extension assistant
- AI tutor conversation
- writing guidance
- language tutoring
- AI note taking
- gesture / air-writing input

This project should stay differentiated by focusing on **learning-state intelligence**, not only content intelligence.

## Agreed core direction

The agreed main scope is:

- `A` Cognitive load monitoring
- `B` Adaptive focus timer
- `C` Attention heatmap review

These are not three isolated features. They should be presented as one system:

**Learning State Guardian: a learning-state sensing and adaptive regulation assistant**

## Narrative for demos and presentations

Recommended one-line positioning:

> Existing AI learning assistants mostly focus on what content to give students. This module focuses on whether the student is still in a good state to learn, when regulation is needed, and where review should happen afterward.

Recommended structure:

- A understands the learner's state
- B regulates the learning rhythm in real time
- C supports after-class reflection and review

## Current implementation status

### Already implemented

- posture smoothing and relative pitch tracking
- stability estimation
- focus score estimation
- cognitive load score and load level
- adaptive focus / recovery session engine
- HUD interface showing focus score, load, stability, timer, and guidance
- CSV logging with expanded learning-state schema
- attention heatmap report export
- optional OCR word capture and note collection

### Main files

- `app.py`
- `run.py`
- `simulate_motion.py`
- `core/posture.py`
- `core/focus_session.py`
- `core/vision.py`
- `utils/storage.py`
- `analytics/analyze_report.py`
- `web/index.html`

## Current run setup on Windows

### VSCode support files already added

- `.vscode/launch.json`
- `.vscode/tasks.json`
- `.vscode/settings.json`
- `setup_windows.ps1`
- `start_windows.ps1`
- `start_simulator.ps1`

### Python environment

- Local Windows virtual environment path: `.venv`
- `requirements.txt` already added
- Local app import was verified successfully
- Local `analytics/analyze_report.py` was verified successfully

### Remaining system dependency

- Windows `Tesseract OCR` is not installed yet
- Without Tesseract:
  - A/B/C features still run
  - OCR features do not fully work

## OCR dependency notes

- `pix2tex` is optional
- `core/vision.py` was adjusted to fall back gracefully if `pix2tex` is missing
- The real blocker for OCR on Windows is `Tesseract OCR`

## What should remain core vs secondary

### Core presentation focus

- learning-state sensing
- adaptive regulation
- attention heatmap / review

### Secondary supporting features

- OCR word capture
- active recall vocabulary card
- note collection

These should support the demo, but not dominate the project story.

## Known constraints and cautions

- The project originally came from WSL/Linux and was copied to Windows local
- Do not reuse the old Linux `venv`
- The local Windows project folder is the preferred working copy now
- Existing CSV data is real demo data and already compatible with the updated logger schema

## Recommended next steps

1. Install Windows `Tesseract OCR` and add it to `PATH`
2. Verify `run.py` and `simulate_motion.py` together in local VSCode
3. Polish the HUD text for presentation screenshots
4. Prepare a concise demo flow:
   - launch HUD
   - run motion simulator
   - show cognitive load changes
   - show adaptive guidance
   - generate heatmap report
5. Optionally add:
   - difficulty event markers
   - missed-content markers
   - more classroom-like simulated states

## Suggested future prompt for Codex

If future context is tight, start with:

> Read `PROJECT_MEMORY.md` and continue from the current Windows-local project setup.

