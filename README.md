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
- classroom attention timeline visualization
- optional OCR-based word capture and note collection

The current priority is the A/B/C learning-state workflow. OCR features are kept as supporting functions, not the main story.

## Main files

- `app.py`: Flask app and status API
- `run.py`: local launcher and console menu
- `simulate_motion.py`: demo posture data simulator
- `core/posture.py`: posture metrics and cognitive load scoring
- `core/focus_session.py`: adaptive focus-cycle engine
- `core/vision.py`: OCR, translation, note capture
- `utils/storage.py`: CSV logging
- `analytics/analyze_report.py`: attention heatmap export
- `web/index.html`: HUD interface
- `PROJECT_MEMORY.md`: condensed project context for future work

## Local Windows setup

1. Open this folder in VSCode.
2. Run the `Setup Windows Environment` task.
3. Select the interpreter at `.venv\Scripts\python.exe`.
4. Run `Run Focus Project`.
5. Run `Run Motion Simulator` in a second terminal or launch config.
6. Open `http://127.0.0.1:5000`.

PowerShell commands also work:

```powershell
.\setup_windows.ps1
.\start_windows.ps1
.\start_simulator.ps1
```

## Dependencies

Core Python dependencies are listed in `requirements.txt`.

System dependency:

- `Tesseract OCR` for Windows is required for OCR features.

Optional dependency:

- `pix2tex` is optional. If missing, the app falls back to basic OCR.

## Output files

- `exports\attention_heatmap.png`: A/B/C attention heatmap report
- `exports\study_analysis.png`: same report exported under the legacy name
- `data\study_report.csv`: posture and learning-state log
- `data\my_vocabulary.csv`: captured vocabulary
- `data\study_notes.md`: collected OCR notes

## Documentation

- `README.md`: project overview and setup
- `README_WINDOWS.md`: short Windows-specific run note
- `PROJECT_MEMORY.md`: project decisions, current scope, and next-step context

## Current scope

The main demo story should stay focused on:

- real-time learning-state sensing
- adaptive study regulation
- after-class attention review

Avoid presenting OCR and note capture as the core innovation, because those overlap more with teammates' content-assistance ideas.
