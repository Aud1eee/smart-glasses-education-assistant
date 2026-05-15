# Focus Project on Windows

For the full project overview, setup steps, and current scope, read `README.md` first.

## Quick start

1. Open this folder in VSCode.
2. Run `Setup Windows Environment`.
3. Let VSCode use the bundled Codex runtime interpreter configured in `.vscode/settings.json`.
4. Run `Run Focus Project`.
5. Run `Run Motion Simulator`.
6. Open `http://127.0.0.1:5000`.

`Run Focus Project` and `.\start_windows.ps1` now use **serve-only mode** by default, so the Flask HUD stays alive until you stop it with `Ctrl+C`.
If you still want the old console menu, use the `Run Focus Project Console` launch config or run `python run.py` manually.

## Validation module

Run this to generate the current learning-state validation summary:

```powershell
.\generate_validation_report.ps1
```

Outputs:

- `exports\validation_summary.md`
- `exports\validation_summary.json`

## Runtime note

The old Windows `.venv` currently points to a broken local Python 3.14 installation path.

To keep the Windows workflow stable, the project now uses a **Windows runtime bridge**:

- scripts launch with the bundled Codex Python runtime
- pure-Python dependencies are bridged from the legacy `.venv\Lib\site-packages`
- plotting features that depend on incompatible binary wheels may fall back to summary-only mode

## Demo simulator modes

Default demo:

```powershell
.\start_simulator.ps1
```

This now runs the `presentation` mode, which cycles through:

- stable focus
- rising cognitive load
- high-load regulation
- recovery

You can also run a single state:

```powershell
.\start_simulator.ps1 -Mode overload
```

Available modes:

- `presentation`
- `stable`
- `rising`
- `overload`
- `recovery`

Useful options:

```powershell
& "C:\Users\11721\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\simulate_motion.py --mode presentation --loops 1
& "C:\Users\11721\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\simulate_motion.py --mode overload --duration 8
```

## Quick verification

To verify the expected state labels without opening the HUD:

```powershell
& "C:\Users\11721\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" .\analytics\verify_demo_states.py
```

The expected presentation progression is:

- `Stable focus`
- `Load rising`
- `Regulate now`
- `Recovery`

## Generate clean demo assets

To produce a fresh demo CSV and heatmap without overwriting your real study log:

```powershell
.\generate_demo_assets.ps1
```

This creates:

- `data\demo_study_report.csv`
- `data\demo_difficulty_events.csv`
- `exports\demo_attention_heatmap.png`

The live HUD now also shows:

- current or last difficulty marker
- a review note for the flagged segment

## Important note

OCR features need Windows `Tesseract OCR` installed and added to `PATH`.

For the A/B/C presentation flow, keep:

```text
ENABLE_AUTO_RECALL=0
```

in `.env`, so the HUD is not interrupted by random vocabulary prompts during the demo.
