# Focus Project

Rokid glasses oriented education prototype focused on **learning-state sensing** rather than only content assistance.

The current project direction is:

- `A` Cognitive load monitoring
- `B` Adaptive focus timer
- `C` Attention heatmap review

These three parts are packaged as one system:

**Learning State Guardian**

## What this project does

This prototype combines:

- real-time posture and stability sensing
- cognitive load estimation
- adaptive focus / recovery guidance
- difficulty event marking
- classroom attention timeline visualization
- learning reflection coaching for post-session self-regulation
- optional OCR-based word capture and note collection

The current priority is the A/B/C learning-state workflow. OCR features are kept as supporting functions, not the main story.

## Presentation story

The project is easiest to explain as two connected surfaces:

- **Live learning-state loop**
  - sense the learner's state
  - regulate the learning rhythm in real time
  - record evidence for after-class review
- **Post-session reflection loop**
  - reopen the flagged session
  - anchor reflection to the strongest difficulty event
  - generate next-session experiments and export a clean reflection card

In short:

1. `Learning State Guardian` handles sensing, regulation, and review.
2. `Learning Reflection Coach` handles post-session reflection and self-regulation planning.

## Main files

- `app.py`: Flask app and status API
- `run.py`: local launcher and console menu
- `simulate_motion.py`: demo posture data simulator
- `core/posture.py`: posture metrics and cognitive load scoring
- `core/focus_session.py`: adaptive focus-cycle engine
- `core/difficulty_marker.py`: sustained difficulty event detection
- `core/reflection_coach.py`: post-session reflection coaching engine
- `core/presentation_companion.py`: presentation mission intake and rehearsal analysis engine
- `core/vision.py`: OCR, translation, note capture
- `utils/storage.py`: CSV logging
- `utils/presentation_storage.py`: local JSON store for presentation missions and rehearsal runs
- `analytics/analyze_report.py`: attention heatmap export
- `web/index.html`: HUD interface
- `web/reflection.html`: reflection coach page
- `web/presentation.html`: academic presentation companion page
- `PROJECT_MEMORY.md`: condensed project context for future work

## Local Windows setup

1. Open this folder in VSCode.
2. Run the `Setup Windows Environment` task.
3. Use the bundled Codex Python runtime configured in `.vscode\settings.json`.
4. Run `Run Focus Project`.
5. Run `Run Motion Simulator` in a second terminal or launch config.
6. Open `http://127.0.0.1:5000`.

Notes:

- `Run Focus Project` and `start_windows.ps1` now default to **serve-only mode**, which keeps the Flask HUD running for browser testing.
- on this Windows setup, `start_windows.ps1` now boots the backend through an import-based launcher instead of direct `app.py` execution, because that path proved more reliable for the reflection snapshot exporter.
- if you want the original console menu for analytics scripts, use the `Run Focus Project Console` launch config or run `python run.py` manually.

Validation:

- run `generate_validation_report.ps1` on Windows to produce:
  - `exports/validation_summary.md`
  - `exports/validation_summary.json`
- this checks four deterministic scenarios (`stable`, `rising`, `overload`, `recovery`) and the end-to-end demo pipeline against the current learning-state model.
- run `generate_reflection_smoke_report.ps1` on Windows to produce:
  - `exports/reflection_smoke_summary.md`
  - `exports/reflection_smoke_summary.json`
- this boots a temporary reflection backend through the import-based Windows launcher and smoke-tests `/review`, `/reflection`, `/api/reflection_coach`, `/api/reflection_compare`, and `/api/reflection_snapshot`.
- the reflection snapshot flow now also emits presentation-ready HTML reflection cards alongside the JSON and Markdown exports.
- the `/reflection` page now also surfaces backend runtime info, so you can tell whether the current Flask process supports the latest HTML card exporter.
- the reflection top bar also includes a compact runtime badge for demos, so you can point at the active backend/exporter state without scrolling into the provider strip.

PowerShell commands also work:

```powershell
.\setup_windows.ps1
.\start_windows.ps1
.\start_simulator.ps1
```

For the Rokid-like video-frame path, you can now also run:

```powershell
.\start_rokid_frame_stream.ps1 -Source image -ImagePath .\images\demo.jpg -MaxFrames 12
```

or switch to a camera / video source:

```powershell
.\start_rokid_frame_stream.ps1 -Source camera -TaskMode reading
.\start_rokid_frame_stream.ps1 -Source video -VideoPath C:\path\to\clip.mp4 -LoopVideo
```

For standardized Rokid scene calibration, you can now run:

```powershell
.\generate_scene_calibration_sheet.ps1
```

This writes:

- `exports\rokid_scene_calibration_sheet.md`

The recommended method is documented in:

- `ROKID_SCENE_CALIBRATION_PROTOCOL.md`

Current Windows note:

- the legacy `.venv` still stores project packages, but its original Python 3.14 interpreter path is broken on this machine
- the Windows scripts now use a bundled Codex Python runtime bridge and reuse pure-Python packages from `.venv\Lib\site-packages`
- some binary plotting features may fall back to summary-only mode until a native Windows environment is rebuilt

## Dependencies

Core Python dependencies are listed in `requirements.txt`.

System dependency:

- `Tesseract OCR` for Windows is required for OCR features.

Optional dependency:

- `pix2tex` is optional. If missing, the app falls back to basic OCR.
- the reflection coach can run in three ways:
  - `heuristic` only
  - free local `Ollama` models such as `qwen3:4b`
  - remote API providers
- `OPENAI_API_KEY` remains optional if you want an OpenAI-backed wording provider, but it is no longer required for the reflection module.

Demo-friendly default:

- `ENABLE_AUTO_RECALL=0` keeps random vocabulary flashcards from interrupting the A/B/C presentation flow.

## Output files

- `exports\attention_heatmap.png`: A/B/C attention heatmap report
- `exports\study_analysis.png`: same report exported under the legacy name
- `exports\demo_attention_heatmap.png`: clean deterministic demo heatmap
- `data\study_report.csv`: posture and learning-state log
- `data\difficulty_events.csv`: detected difficulty-event log
- `data\demo_study_report.csv`: deterministic presentation-mode demo log
- `data\demo_difficulty_events.csv`: deterministic demo difficulty-event log
- `data\my_vocabulary.csv`: captured vocabulary
- `data\study_notes.md`: collected OCR notes

## Documentation

- `README.md`: project overview and setup
- `README_WINDOWS.md`: short Windows-specific run note
- `PROJECT_MEMORY.md`: project decisions, current scope, and next-step context
- `PROJECT_EXPLANATION.md`: long-form explanation draft for defense and reporting
- `OLLAMA_REFLECTION_SETUP.md`: free local-model reflection setup checklist
- `REFLECTION_REMOTE_PROVIDER_CONTRACT.md`: remote provider interface contract
- `ROKID_SCENE_CALIBRATION_PROTOCOL.md`: standard first-person scene calibration method

## Current scope

The main demo story should stay focused on:

- real-time learning-state sensing
- adaptive study regulation
- difficulty event marking
- after-class attention review

Avoid presenting OCR and note capture as the core innovation, because those overlap more with teammates' content-assistance ideas.

## Module boundaries

This project should stay clearly separated from content-assistance directions.

The core module does:

- learning-state sensing
- adaptive regulation
- difficulty-event marking
- after-class review
- reflection on learning process

The core module does **not** aim to become:

- a knowledge-explanation assistant
- an AI tutor chat surface
- a writing-correction tool
- a language-tutoring system
- an AI note-taking workflow
- a gesture-input feature

## Independent Reflection Module

The project now also includes an independent page at `/reflection`:

- it reads the logged learning-state session and difficulty events
- it converts them into a reflection signature, metacognitive questions, and next-session experiments
- it stays process-focused, so it does not overlap with tutoring, writing help, language coaching, note taking, or gesture input
- it can run fully in heuristic mode
- it can optionally use a free local Ollama model such as `qwen3:4b`
- it can later be switched to a remote API provider for Rokid-side deployment without changing the reflection page structure
- it can compare two local Ollama models on the same session from the `/reflection` page
- it can export both single-run and compare snapshots to `exports/reflection_snapshots/` as JSON, Markdown, and one-page HTML cards

Recommended free local setup:

1. Install Ollama.
2. Pull a local model such as `qwen3:4b`.
3. Keep `.env` on:
   - `LLM_PROVIDER=ollama`
   - `OLLAMA_BASE_URL=http://127.0.0.1:11434/api`
   - `OLLAMA_MODEL=qwen3:4b`
4. Open `/reflection`, turn on provider-backed wording polish, and keep heuristic fallback enabled by default.

If you want to test the future remote deployment path without a real server yet:

1. Start `.\start_mock_reflection_provider.ps1`
2. Set `LLM_PROVIDER=remote`
3. Point `REFLECTION_REMOTE_URL` to `http://127.0.0.1:5051/reflect`

See:

- `OLLAMA_REFLECTION_SETUP.md`
- `REFLECTION_REMOTE_PROVIDER_CONTRACT.md`

Suggested local flow:

1. Run a live session or generate demo assets.
2. Open `/review` to inspect flagged segments.
3. Open `/reflection` to generate a reflection view for the same session.
4. Use the local compare panel to contrast `qwen3:4b` with another installed model such as `deepseek-r1:7b`.
5. Save the reflection snapshot or compare snapshot for reporting, thesis material, or future Rokid-side replay.
6. Open the exported HTML card when you need a cleaner one-page artifact for a defense, demo, or presentation appendix.

## Independent Presentation Module

The project now also includes an independent page at `/presentation`:

- it turns one academic presentation task into a `brief -> script -> rehearse` workflow
- the student still writes the actual outline, speaker notes, and cue cards
- the script workspace now supports `slide-linked cards`, so each card can map to one PPT page or one tightly linked speaking unit
- each slide card can now also hold a longer `teleprompter_script`, which is split into glance-sized chunks for runtime delivery
- the rehearsal page now also includes a lightweight `presentation controller` with:
  - `phone` as the default main control source
  - `rokid_button` as a lightweight chunk / slide control scaffold
  - `present` mode for a compact current-slide view instead of a long script view
  - a controller snapshot that shows the active slide, queued next slide, cue state, and input hints
  - a `phone controller surface` at `/presentation/controller`
  - a `companion sync scaffold` that keeps the phone controller, future Rokid HUD pull, and button-event mapping on one mission state
  - a `real-time companion bridge` with:
    - mission-level pairing pin / bridge key
    - simple claim / release ownership for the phone controller surface
    - live HUD visibility into the current bridge owner
- AI can help with:
  - task-intake field extraction
  - section scaffold suggestions
  - rehearsal transcript review
  - rehearsal feedback wording
- AI does **not** act as:
  - an AI tutor
  - a content explainer
  - a one-click final-script generator
  - a generic writing-correction tool
  - an AI note-taking workflow
- the detailed results stay on the web page, while the backend also returns a lightweight rehearsal HUD summary for future Rokid-side use
- if no model provider is configured, the page still works through:
  - heuristic intake extraction
  - timing-based rehearsal feedback
  - manual or browser-speech transcript input

The core routes are:

- `/presentation`
- `/presentation/controller`
- `/api/presentation_missions`
- `/api/presentation_missions/intake_extract`
- `/api/presentation_missions/<mission_id>/script`
- `/api/presentation_missions/<mission_id>/presentation_state`
- `/api/presentation_missions/<mission_id>/presentation_control`
- `/api/presentation_missions/<mission_id>/companion_sync`
- `/api/presentation_missions/<mission_id>/pairing_state`
- `/api/presentation_missions/<mission_id>/pairing_start`
- `/api/presentation_missions/<mission_id>/pairing_join`
- `/api/presentation_missions/<mission_id>/pairing_end`
- `/api/presentation_missions/<mission_id>/bridge_state`
- `/api/presentation_missions/<mission_id>/bridge_claim`
- `/api/presentation_missions/<mission_id>/bridge_release`
- `/api/presentation_missions/<mission_id>/rokid_event`
- `/api/presentation_missions/<mission_id>/live_hud`
- `/api/presentation_rehearsals`
- `/api/presentation_rehearsals/<rehearsal_id>/analyze`
- `/api/presentation_rehearsals/<rehearsal_id>/hud_summary`

The phone-side controller now also includes a lightweight pairing sheet:

- large join code display for the current session
- readable pairing lifecycle labels and next-step guidance
- auto-refresh while a pairing window is waiting or already paired
- explicit separation between `owner_surface` and the joined companion surface

The live presentation runtime now also supports chunk-level teleprompter navigation:

- `next` and `previous` act as step navigation, moving chunk-first before switching slides
- explicit `previous_chunk`, `next_chunk`, `previous_slide`, and `next_slide` controls are available on the phone controller
- a `chunk navigator` rail now lets the phone-side controller jump straight to any chunk on the current slide
- the controller and stage now expose previous / current / next chunk previews so the presenter can quickly regain place after an interruption
- the stage supports vertical swipe for chunk navigation and horizontal swipe for slide navigation
- keyboard shortcuts now also support `1-9` for direct chunk jumps during local testing
- the default Rokid button mapping is now:
  - `single_press -> next_chunk`
  - `double_press -> previous_chunk`
  - `long_press -> next_slide`
- the live HUD payload now exposes the current teleprompter chunk, chunk-progress label, and next-chunk preview for future glasses-side display

Local artifact note:

- presentation missions and rehearsal runs are stored in `data/presentation_companion_store.json`
- uploaded rehearsal audio is stored in `data/presentation_audio/`
- both should stay local and should not be committed

Quick smoke verification:

```powershell
& "C:\Users\11721\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\analytics\presentation_smoke_check.py
```

This checks:

- mission creation
- intake extraction fallback
- script save
- presentation-state save
- pairing start / expire / join / end
- presentation next / previous / cue-toggle control
- bridge claim / release
- rehearsal save
- rehearsal analysis
- HUD summary output
- live HUD sync payload

## Recommended defense demo flow

If you need a short, repeatable demo path for a defense or checkpoint review, use this order:

1. Start the HUD and run the deterministic presentation simulator.
2. Show the live transition from stable focus to rising load and regulation.
3. Open `/review` and highlight the strongest difficulty event.
4. Jump into `/reflection` from that event.
5. Generate a reflection view in `heuristic` mode first.
6. Optionally enable local Ollama wording polish or compare two local models.
7. Save the reflection snapshot and open the exported HTML reflection card.

This sequence tells a clean product story:

**sense -> regulate -> mark -> review -> reflect**
