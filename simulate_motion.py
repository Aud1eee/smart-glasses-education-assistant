import argparse
import math
import random
import time

import bootstrap_windows_runtime  # noqa: F401
import requests


BASE_URL = "http://127.0.0.1:5000"
POSTURE_URL = f"{BASE_URL}/api/v1/posture"
PRESENTATION_SEQUENCE = [
    ("stable", 10),
    ("rising", 10),
    ("overload", 12),
    ("recovery", 10),
]


SCENARIOS = {
    "stable": {
        "center": 8.0,
        "swing": 1.0,
        "noise": 0.35,
        "speed": 0.18,
        "label": "Stable focus",
    },
    "rising": {
        "center": 28.0,
        "swing": 2.2,
        "noise": 0.6,
        "speed": 0.22,
        "label": "Rising cognitive load",
    },
    "overload": {
        "center": 44.0,
        "swing": 3.0,
        "noise": 0.9,
        "speed": 0.28,
        "label": "High-load regulation",
    },
    "recovery": {
        "center": 10.0,
        "swing": 1.4,
        "noise": 0.4,
        "speed": 0.16,
        "label": "Recovery state",
    },
}


def post_pitch(pitch):
    requests.post(POSTURE_URL, json={"pitch": pitch}, timeout=2)


def reset_demo_state():
    requests.get(f"{BASE_URL}/reset_session", timeout=2)

    # Warm up the exponential smoother before calibrating the baseline.
    for _ in range(20):
        post_pitch(8.0)
        time.sleep(0.05)

    requests.get(f"{BASE_URL}/calibrate", timeout=2)
    requests.get(f"{BASE_URL}/reset_session", timeout=2)


def scenario_pitch(config, step):
    wave = math.sin(step * config["speed"]) * config["swing"]
    noise = random.uniform(-config["noise"], config["noise"])
    return config["center"] + wave + noise


def run_single_mode(mode, interval, duration=None):
    config = SCENARIOS[mode]
    step = 0
    start_time = time.time()
    print(f"Running simulator mode: {config['label']}")
    while True:
        if duration is not None and time.time() - start_time >= duration:
            break
        pitch = scenario_pitch(config, step)
        post_pitch(pitch)
        print(f"\r{config['label']:<24} | pitch {pitch:5.2f} deg", end="")
        step += 1
        time.sleep(interval)
    print()


def run_presentation(interval, loops=0):
    step = 0
    completed_loops = 0
    while True:
        for mode, seconds in PRESENTATION_SEQUENCE:
            config = SCENARIOS[mode]
            samples = max(1, int(seconds / interval))
            print(f"\nSwitching to: {config['label']} ({seconds}s)")
            for _ in range(samples):
                pitch = scenario_pitch(config, step)
                post_pitch(pitch)
                print(f"\r{config['label']:<24} | pitch {pitch:5.2f} deg", end="")
                step += 1
                time.sleep(interval)
        completed_loops += 1
        if loops and completed_loops >= loops:
            print()
            break


def parse_args():
    parser = argparse.ArgumentParser(
        description="Deterministic simulator for the Learning State Guardian demo."
    )
    parser.add_argument(
        "--mode",
        choices=["presentation", "stable", "rising", "overload", "recovery"],
        default="presentation",
        help="Which classroom state to simulate.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.12,
        help="Seconds between posture samples.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional total seconds for a single-mode run.",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=0,
        help="Optional number of presentation loops. 0 means infinite.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("Preparing demo baseline and resetting session...")
    reset_demo_state()

    try:
        if args.mode == "presentation":
            run_presentation(args.interval, loops=args.loops)
        else:
            run_single_mode(args.mode, args.interval, duration=args.duration)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
