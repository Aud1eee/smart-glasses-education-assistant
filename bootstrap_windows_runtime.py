from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parent
LEGACY_SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
CODEX_RUNTIME_MARKER = "codex-primary-runtime"


def enable_windows_runtime_bridge():
    if os.name != "nt":
        return

    executable_text = str(sys.executable).lower()
    using_bundled_runtime = CODEX_RUNTIME_MARKER in executable_text
    if using_bundled_runtime and LEGACY_SITE_PACKAGES.exists():
        legacy_path = str(LEGACY_SITE_PACKAGES)
        if legacy_path not in sys.path:
            sys.path.append(legacy_path)

    os.environ.setdefault("MPLBACKEND", "Agg")


enable_windows_runtime_bridge()
