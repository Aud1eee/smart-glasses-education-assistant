import math
import random
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.focus_session import FocusSessionEngine
from core.posture import PostureEngine
from simulate_motion import SCENARIOS


def evaluate_scenario(name, seconds=10, interval=0.12, seed=7):
    random.seed(seed)
    config = SCENARIOS[name]
    posture = PostureEngine()
    session = FocusSessionEngine()

    now = 0.0
    for _ in range(20):
        posture.process(8.0, now=now)
        now += 0.05

    posture.calibrate()
    session.reset(now=now)

    labels = []
    actions = []
    loads = []
    focus_scores = []
    samples = max(1, int(seconds / interval))

    for step in range(samples):
        pitch = config["center"] + math.sin(step * config["speed"]) * config["swing"]
        pitch += random.uniform(-config["noise"], config["noise"])
        result = posture.process(pitch, now=now)
        session_result = session.update(result, now=now)
        labels.append(session_result["state_label"])
        actions.append(session_result["action"])
        loads.append(result["cognitive_load"])
        focus_scores.append(result["focus_score"])
        now += interval

    return {
        "scenario": name,
        "label": config["label"],
        "dominant_state": Counter(labels).most_common(1)[0][0],
        "dominant_action": Counter(actions).most_common(1)[0][0],
        "avg_load": round(sum(loads) / len(loads), 1),
        "avg_focus": round(sum(focus_scores) / len(focus_scores), 1),
        "final_state": labels[-1],
        "final_action": actions[-1],
    }


def main():
    print("Demo scenario verification")
    for name in ["stable", "rising", "overload", "recovery"]:
        item = evaluate_scenario(name)
        print(
            f"- {item['label']}: dominant={item['dominant_state']}, "
            f"final={item['final_state']}, avg_load={item['avg_load']}, avg_focus={item['avg_focus']}"
        )


if __name__ == "__main__":
    main()
