import bootstrap_windows_runtime  # noqa: F401
import os

from app import app


def _server_host():
    return str(os.environ.get("FOCUS_PROJECT_HOST", "0.0.0.0")).strip() or "0.0.0.0"


def _server_port():
    try:
        return int(str(os.environ.get("FOCUS_PROJECT_PORT", "5000")).strip() or "5000")
    except (TypeError, ValueError):
        return 5000


def main():
    app.run(host=_server_host(), port=_server_port(), debug=False)


if __name__ == "__main__":
    main()
