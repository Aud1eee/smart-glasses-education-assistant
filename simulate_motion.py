import argparse
import math
import random
import time

import requests


BASE_URL = "http://127.0.0.1:5000"
POSTURE_URL = f"{BASE_URL}/api/v1/posture"


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


def run_single_mode(mode, interval):
    config = SCENARIOS[mode]
    step = 0
    print(f"Running simulator mode: {config['label']}")
    while True:
        pitch = scenario_pitch(config, step)
        post_pitch(pitch)
        print(f"\r{config['label']:<24} | pitch {pitch:5.2f} deg", end="")
        step += 1
        time.sleep(interval)


def run_presentation(interval):
    sequence = [
        ("stable", 10),
        ("rising", 10),
        ("overload", 12),
        ("recovery", 10),
    ]

    step = 0
    while True:
        for mode, seconds in sequence:
            config = SCENARIOS[mode]
            samples = max(1, int(seconds / interval))
            print(f"\nSwitching to: {config['label']} ({seconds}s)")
            for _ in range(samples):
                pitch = scenario_pitch(config, step)
                post_pitch(pitch)
                print(f"\r{config['label']:<24} | pitch {pitch:5.2f} deg", end="")
                step += 1
                time.sleep(interval)


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
    return parser.parse_args()


def main():
    args = parse_args()
    print("Preparing demo baseline and resetting session...")
    reset_demo_state()

    try:
        if args.mode == "presentation":
            run_presentation(args.interval)
        else:
            run_single_mode(args.mode, args.interval)
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
