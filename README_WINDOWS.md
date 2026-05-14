# Focus Project on Windows

For the full project overview, setup steps, and current scope, read `README.md` first.

## Quick start

1. Open this folder in VSCode.
2. Run `Setup Windows Environment`.
3. Select `.venv\Scripts\python.exe`.
4. Run `Run Focus Project`.
5. Run `Run Motion Simulator`.
6. Open `http://127.0.0.1:5000`.

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
.\.venv\Scripts\python.exe .\simulate_motion.py --mode presentation --loops 1
.\.venv\Scripts\python.exe .\simulate_motion.py --mode overload --duration 8
```

## Quick verification

To verify the expected state labels without opening the HUD:

```powershell
.\.venv\Scripts\python.exe .\analytics\verify_demo_states.py
```

The expected presentation progression is:

- `Stable focus`
- `Load rising`
- `Regulate now`
- `Recovery`

## Important note

OCR features need Windows `Tesseract OCR` installed and added to `PATH`.

For the A/B/C presentation flow, keep:

```text
ENABLE_AUTO_RECALL=0
```

in `.env`, so the HUD is not interrupted by random vocabulary prompts during the demo.
