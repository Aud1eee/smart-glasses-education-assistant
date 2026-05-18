import bootstrap_windows_runtime  # noqa: F401
from app import app


def main():
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
