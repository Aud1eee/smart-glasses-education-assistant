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
- optional OCR-based word capture and note collection

The current priority is the A/B/C learning-state workflow. OCR features are kept as supporting functions, not the main story.

## Main files

- `app.py`: Flask app and status API
- `run.py`: local launcher and console menu
- `simulate_motion.py`: demo posture data simulator
- `core/posture.py`: posture metrics and cognitive load scoring
- `core/focus_session.py`: adaptive focus-cycle engine
- `core/difficulty_marker.py`: sustained difficulty event detection
- `core/vision.py`: OCR, translation, note capture
- `utils/storage.py`: CSV logging
- `analytics/analyze_report.py`: attention heatmap export
- `web/index.html`: HUD interface
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
- if you want the original console menu for analytics scripts, use the `Run Focus Project Console` launch config or run `python run.py` manually.

Validation:

- run `generate_validation_report.ps1` on Windows to produce:
  - `exports/validation_summary.md`
  - `exports/validation_summary.json`
- this checks four deterministic scenarios (`stable`, `rising`, `overload`, `recovery`) and the end-to-end demo pipeline against the current learning-state model.

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

## Current scope

The main demo story should stay focused on:

- real-time learning-state sensing
- adaptive study regulation
- difficulty event marking
- after-class attention review

Avoid presenting OCR and note capture as the core innovation, because those overlap more with teammates' content-assistance ideas.
