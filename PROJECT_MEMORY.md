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
- behavioral alignment scoring
- fatigue-risk estimation
- uncertainty / confidence scoring
- task-mode-aware thresholds:
  - `lecture`
  - `reading`
  - `note-taking`
  - `review`
- adaptive focus / recovery session engine
- difficulty event marker for sustained rising/high load segments
- HUD interface showing focus score, load, stability, timer, and guidance
- CSV logging with expanded learning-state schema
- attention heatmap report export
- deterministic simulator modes for presentation demos
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
- `ENABLE_AUTO_RECALL=0` is the preferred demo default so A/B/C presentations stay focused

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

## Development roadmap

### Phase 1 goal

Build a **stable local demo** for the A/B/C system:

- `A` Cognitive load monitoring should be visible and understandable
- `B` Adaptive focus timer should produce meaningful guidance changes
- `C` Attention heatmap should be generated reliably after a demo run

### Phase 1 acceptance criteria

- The app runs locally on Windows in VSCode without WSL
- `run.py` and `simulate_motion.py` work together in a clean demo flow
- The HUD clearly shows focus score, cognitive load, stability, timer, and guidance
- At least 3 demo states are easy to show:
  - stable focus
  - rising load
  - high-load / regulation state
- `exports/attention_heatmap.png` is generated successfully after the demo
- Core demo steps are documented so the project can be presented repeatedly

### Phase 1 task breakdown

1. Verify the Windows-local runtime and OCR constraints
2. Stabilize the HUD text and state transitions for presentation use
3. Improve the simulator so it can intentionally trigger demo scenarios
4. Verify heatmap generation from a fresh local demo run
5. Save the final demo flow in docs and commit the phase result

### Immediate first task

The first concrete task is:

**Make the simulator and HUD work as a predictable presentation demo**

That means:

- the simulator should support clearly different learning states
- the HUD should react in a way that is easy to explain live
- the output should be repeatable, not random-only

### Phase 1 progress note

Completed:

- the simulator now supports:
  - `presentation`
  - `stable`
  - `rising`
  - `overload`
  - `recovery`
- the default Windows simulator launcher now starts the `presentation` mode
- Windows quick-start notes were updated to explain the demo modes

Next:

- verify the HUD transitions against these modes in a full local run
- tune thresholds or wording if one state is not visually clear enough

### Scenario verification status

The current verified presentation-mode progression is:

- `Stable focus`
- `Load rising`
- `Regulate now`
- `Recovery`

This was checked with `analytics/verify_demo_states.py` using the deterministic simulator profiles.

### Demo asset pipeline

There is now a non-destructive demo asset flow:

- `generate_demo_assets.ps1`
- `analytics/generate_demo_assets.py`

It creates:

- `data/demo_study_report.csv`
- `exports/demo_attention_heatmap.png`
- `data/demo_difficulty_events.csv`

This is preferred when preparing screenshots or presentation materials, because it does not overwrite the real `data/study_report.csv`.

### Demo asset verification

The demo asset pipeline was run successfully on Windows local.

Latest generated summary:

- samples: `349`
- average focus: `66.7`
- average cognitive load: `42.3`
- high-load ratio: `37.0%`
- difficulty events: `1`

The current `demo_attention_heatmap.png` is visually clean and suitable as a presentation asset.

### Difficulty-event marker status

The first version of the difficulty-event marker is now integrated across:

- real-time detection
- live HUD status output
- CSV event logging
- demo asset generation
- heatmap event overlays

Current demo output:

- one sustained high-severity event is detected in the rising/overload segment
- the demo difficulty-event CSV records:
  - start and end timestamps
  - start and end sample indices
  - severity
  - peak load
  - min focus
  - peak pitch
  - lowest stability
  - trigger label and reason
  - review note

### Consistency fixes completed

The following consistency fixes were completed after review:

- difficulty-event start timestamps now match the real candidate start, not the later trigger moment
- `/status` no longer re-runs the regulation engine and no longer changes guidance labels just because the page is polling
- `calibrate` and `reset_session` now clear:
  - sample counter
  - visible difficulty state
  - stale posture age state
- learning-state logs and difficulty-event logs are now session-aware:
  - `Session_ID` is stored in both CSV files
  - `reset_session` and `calibrate` create a new session id
  - difficulty-event counters reset to `0` for the new session
  - heatmap overlays are aligned by `Session_ID + Start_Sample / End_Sample`

Current behavior after the fix:

- state labels remain stable during polling if no new posture data arrives
- `stale_seconds` is exposed from the session snapshot
- the demo pipeline still produces `1` deterministic difficulty event with correct timing fields
- real API validation confirms that after `reset_session`:
  - a new `session_id` is returned
  - `difficulty.event_count` returns to `0`
  - the visible state returns to `Focus settling`

### Phase 1 algorithm refactor completed

The learning-state algorithm has now been upgraded from a mostly posture-only `focus_score` framing into a more explicit multi-signal proxy framework that still works with the current hardware limits.

New posture-engine outputs:

- `behavioral_alignment`
- `behavioral_level`
- `fatigue_risk`
- `fatigue_level`
- `uncertainty_score`
- `confidence_level`
- `task_mode`

Current interpretation:

- `focus_score` is retained mainly for compatibility with the existing HUD and heatmap
- `behavioral_alignment` is the more honest primary signal for presentation and explanation
- `fatigue_risk` is now separated from generic load
- `uncertainty_score` prevents overconfident interpretation during warm-up or task-mode transitions

The adaptive engine now also reacts to:

- low-confidence signal states
- fatigue-risk states
- task-mode-aware alignment drift

The HUD also now exposes:

- task mode
- confidence level
- fatigue risk

Verified after refactor:

- syntax check passed
- demo asset pipeline still runs successfully
- local API returns:
  - `task_mode`
  - `behavioral_alignment`
  - `fatigue_risk`
  - `confidence_level`

### HUD redesign completed

The HUD in `web/index.html` has been redesigned to better fit a Rokid-style glasses display.

The new interface direction is:

- less like a desktop dashboard
- more like a lens-first HUD
- lighter central occlusion
- amber monochrome accent inspired by Rokid product visuals
- central state card + slim side rails + task-mode capsules

New HUD interaction highlights:

- clickable and keyboard-switchable task-mode chips
- central state emphasis
- separate confidence and difficulty indicators
- reduced visual clutter in the middle of the view
- dual display modes:
  - `glasses` for low-occlusion near-eye use
  - `demo` for full presentation layout
- quiet automatic compact state during stable low-risk learning in glasses view
- narrower edge docks and event-only difficulty emphasis for glasses view
- compact glasses-specific state/guidance vocabulary in the live HUD
- dot-based icon language for the live glasses HUD state summary

Verification:

- local page HTML served successfully from Flask
- simulator-driven `/status` updates still work with the redesigned HUD
- Browser plugin runtime was unavailable in this environment, so final verification was done through local server fetch + API checks rather than in-app visual automation

### Difficulty review page added

The project now includes a separate review page at `/review`.

This page is backed by `logger.build_review_payload(...)` and turns logged difficulty events into:

- session summary
- flagged event list
- session timeline
- missed-content risk hints
- review notes
- catch-up action suggestions

The HUD also has a direct shortcut (`G`) to open this page during demos.

### Windows runtime bridge enabled

The original Windows `.venv` still stores project packages, but its Python 3.14 interpreter path is broken on this machine.

To keep local VSCode and PowerShell runs stable, the project now uses:

- the bundled Codex Python runtime as the active Windows interpreter
- `bootstrap_windows_runtime.py` to bridge pure-Python dependencies from `.venv\Lib\site-packages`
- updated PowerShell launch scripts and `.vscode/settings.json`

Known limitation:

- `matplotlib` from the legacy `.venv` is binary-incompatible with the bundled runtime, so Windows local chart export now falls back to summary-only mode with an explicit message instead of crashing

### Post-refactor algorithm fixes

After a review pass, three important fixes were applied:

- `reset_session` now clears posture-tracking state while preserving the current calibrated baseline
- `fatigue_risk` now has a true zero baseline in steady posture instead of carrying a built-in positive offset
- `uncertainty_score` no longer upgrades `load_level` to `medium`; it now stays a separate `Signal check / confidence` dimension

Verified after the fix:

- steady-state probe: `fatigue_risk = 0.0`, `cognitive_load = 0.0`
- task-mode switch warm-up: `load_level = low`, `load_reason = Signal warming up or mode transition`
- local API after overload + `reset_session`:
  - `cognitive_load = 0.0`
  - `fatigue_risk = 0.0`
  - `confidence_level = warming_up`
  - `state_label = Focus settling`

### Report layer upgraded

`analytics/analyze_report.py` has now been upgraded to match the new algorithm semantics.

The report now emphasizes:

- behavioral alignment
- cognitive load
- fatigue risk
- confidence / uncertainty
- task-mode context

The demo report now prints:

- average behavioral alignment
- average focus proxy
- average cognitive load
- average fatigue risk
- drift-risk ratio
- high-load ratio
- low-confidence ratio
- task modes present

## Suggested future prompt for Codex

If future context is tight, start with:

> Read `PROJECT_MEMORY.md` and continue from the current Windows-local project setup.

## Explanation draft

The long-form explanation draft now lives in:

- `PROJECT_EXPLANATION.md`

This should be the main expandable document for:

- defense notes
- module explanations
- data interpretation
- heatmap interpretation
