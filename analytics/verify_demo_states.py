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


def run_scenario_trace(name, seconds=10, interval=0.12, seed=7):
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
    alignments = []
    fatigue_scores = []
    confidence_levels = []
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
        alignments.append(result["behavioral_alignment"])
        fatigue_scores.append(result["fatigue_risk"])
        confidence_levels.append(result["confidence_level"])
        now += interval

    return {
        "scenario": name,
        "label": config["label"],
        "labels": labels,
        "actions": actions,
        "loads": loads,
        "focus_scores": focus_scores,
        "alignments": alignments,
        "fatigue_scores": fatigue_scores,
        "confidence_levels": confidence_levels,
        "samples": samples,
    }


def _tail_values(values, ratio=0.4):
    if not values:
        return []
    tail_count = max(1, int(len(values) * ratio))
    return values[-tail_count:]


def evaluate_scenario(name, seconds=10, interval=0.12, seed=7):
    trace = run_scenario_trace(name, seconds=seconds, interval=interval, seed=seed)
    labels = trace["labels"]
    actions = trace["actions"]
    loads = trace["loads"]
    focus_scores = trace["focus_scores"]
    alignments = trace["alignments"]
    fatigue_scores = trace["fatigue_scores"]
    confidence_levels = trace["confidence_levels"]

    state_counts = Counter(labels)
    tail_state_counts = Counter(_tail_values(labels))

    return {
        "scenario": trace["scenario"],
        "label": trace["label"],
        "dominant_state": state_counts.most_common(1)[0][0],
        "tail_dominant_state": tail_state_counts.most_common(1)[0][0],
        "dominant_action": Counter(actions).most_common(1)[0][0],
        "avg_load": round(sum(loads) / len(loads), 1),
        "avg_focus": round(sum(focus_scores) / len(focus_scores), 1),
        "avg_alignment": round(sum(alignments) / len(alignments), 1),
        "avg_fatigue": round(sum(fatigue_scores) / len(fatigue_scores), 1),
        "high_load_ratio": round((sum(1 for item in loads if item >= 70) / len(loads)) * 100, 1),
        "low_conf_ratio": round((sum(1 for item in confidence_levels if item == "low") / len(confidence_levels)) * 100, 1),
        "final_state": labels[-1],
        "final_action": actions[-1],
        "state_counts": dict(state_counts),
        "tail_state_counts": dict(tail_state_counts),
        "sample_count": trace["samples"],
    }


def main():
    print("Demo scenario verification")
    for name in ["stable", "rising", "overload", "recovery"]:
        item = evaluate_scenario(name)
        print(
            f"- {item['label']}: dominant={item['dominant_state']}, "
            f"tail={item['tail_dominant_state']}, final={item['final_state']}, "
            f"avg_load={item['avg_load']}, avg_focus={item['avg_focus']}, avg_fatigue={item['avg_fatigue']}"
        )


if __name__ == "__main__":
    main()
