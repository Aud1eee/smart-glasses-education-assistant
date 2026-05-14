import os
import signal
import subprocess
import sys
import time


def main():
    root = os.path.dirname(os.path.abspath(__file__))

    print("=" * 52)
    print("Focus Project | Rokid Learning State Guardian")
    print("=" * 52)

    if sys.platform != "win32":
        try:
            subprocess.run(["fuser", "-k", "5000/tcp"], capture_output=True)
        except Exception:
            pass

    print("Starting Flask HUD service...")
    app_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid if sys.platform != "win32" else None,
    )

    time.sleep(2)
    print("\nSystem ready.")
    print("HUD: http://127.0.0.1:5000")
    print("Modes: Space=capture word | Enter=collect note | C=calibrate | R=reset session")

    try:
        while True:
            print("\n" + "-" * 18 + " Console Menu " + "-" * 18)
            print(" 1. Generate attention heatmap report (png)")
            print(" 2. Review vocabulary progress (text)")
            print(" 3. Generate vocabulary difficulty chart (png)")
            print(" q. Stop system and quit")

            choice = input("\nSelect an option: ").strip().lower()

            if choice == "1":
                print("\n>>> Generating learning-state heatmap...")
                script_path = os.path.join(root, "analytics", "analyze_report.py")
                subprocess.run([sys.executable, script_path], cwd=os.path.join(root, "analytics"))

            elif choice == "2":
                print("\n>>> Reviewing vocabulary progress...")
                script_path = os.path.join(root, "analytics", "review_vocab.py")
                subprocess.run([sys.executable, script_path], cwd=os.path.join(root, "analytics"))

            elif choice == "3":
                print("\n>>> Generating vocabulary chart...")
                script_path = os.path.join(root, "analytics", "generate_word_cloud.py")
                subprocess.run([sys.executable, script_path], cwd=os.path.join(root, "analytics"))

            elif choice == "q":
                print("\nStopping services...")
                break
            else:
                print("Invalid input. Please select again.")

    except KeyboardInterrupt:
        print("\nStop signal received.")
    finally:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(app_proc.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(app_proc.pid), signal.SIGTERM)
        print("Backend service stopped safely.")


if __name__ == "__main__":
    main()
