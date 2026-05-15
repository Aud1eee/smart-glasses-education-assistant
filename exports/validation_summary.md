# Learning State Validation Summary

- Generated: 2026-05-15 16:33:37
- Overall status: **PASS**

## Validation Scope

- Scenario-level checks for `stable`, `rising`, `overload`, and `recovery` traces
- End-to-end demo pipeline checks using `demo_study_report.csv` and `demo_difficulty_events.csv`

## Scenario Overview

| Scenario | Tail dominant | Final state | Avg load | Avg focus | Result |
| --- | --- | --- | ---: | ---: | --- |
| Stable focus | Focus settling | Stable focus | 1.2 | 98.8 | PASS |
| Rising cognitive load | Fatigue risk | Fatigue risk | 55.2 | 49.3 | PASS |
| High-load regulation | Fatigue risk | Fatigue risk | 85.7 | 23.4 | PASS |
| Recovery state | Focus settling | Stable focus | 5.0 | 95.1 | PASS |

## Scenario Check Details

| Scenario | Metric | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| Stable focus | tail_dominant_state | Focus settling / Stable focus | Focus settling | PASS |
| Stable focus | final_state | Stable focus | Stable focus | PASS |
| Stable focus | avg_load | <= 15 | 1.2 | PASS |
| Stable focus | avg_focus | >= 90 | 98.8 | PASS |
| Rising cognitive load | state_counts | Load rising | Fatigue risk, Focus settling, High load, Load rising | PASS |
| Rising cognitive load | tail_dominant_state | Fatigue risk / Load rising / Regulate now | Fatigue risk | PASS |
| Rising cognitive load | final_state | Fatigue risk / Load rising / Regulate now | Fatigue risk | PASS |
| Rising cognitive load | avg_load | 40 - 70 | 55.2 | PASS |
| Rising cognitive load | avg_focus | <= 65 | 49.3 | PASS |
| High-load regulation | tail_dominant_state | Fatigue risk / High load / Regulate now | Fatigue risk | PASS |
| High-load regulation | final_state | Fatigue risk / High load / Regulate now | Fatigue risk | PASS |
| High-load regulation | avg_load | >= 75 | 85.7 | PASS |
| High-load regulation | avg_focus | <= 40 | 23.4 | PASS |
| High-load regulation | high_load_ratio | >= 60 | 98.8 | PASS |
| Recovery state | tail_dominant_state | Focus settling / Stable focus | Focus settling | PASS |
| Recovery state | final_state | Stable focus | Stable focus | PASS |
| Recovery state | avg_load | <= 15 | 5.0 | PASS |
| Recovery state | avg_focus | >= 85 | 95.1 | PASS |

## End-to-End Demo Checks

| Metric | Expected | Observed | Rationale | Result |
| --- | --- | --- | --- | --- |
| samples | >= 300 | 349 | Demo run should contain enough samples for a meaningful timeline. | PASS |
| avg_alignment | 55 - 75 | 63.9 | Average behavioral alignment should stay in a realistic mid-high range. | PASS |
| avg_load | 30 - 55 | 42.6 | Average load should show both stable and stressed segments. | PASS |
| avg_fatigue | 20 - 40 | 30.6 | Average fatigue should remain noticeable but not dominant across the full demo. | PASS |
| drift_ratio | 40 - 70 | 57.0 | Drift-risk ratio should reflect a mixed session rather than a perfectly stable trace. | PASS |
| high_load_ratio | 25 - 55 | 36.7 | High-load ratio should stay concentrated instead of filling the whole session. | PASS |
| low_conf_ratio | <= 5 | 0.0 | Low-confidence ratio should stay low in the deterministic demo run. | PASS |
| difficulty_event_count | >= 1 | 1 | At least one difficulty event should be captured in the presentation sequence. | PASS |

## Notes

- Heatmap export was skipped in the current Windows runtime bridge because `matplotlib` is not available in a compatible binary form. This does not affect the scenario checks or summary metrics.
- The scenario validation uses deterministic simulated motion, so it is intended to verify algorithm behavior and demo consistency, not real-world educational validity.
- `Stable` and `recovery` scenarios currently allow `Focus settling` as an acceptable tail-dominant state because the session engine intentionally uses a conservative settling phase before fully stabilizing.
- This validation layer is best paired with manual observation, task performance, and future Rokid-device input tests.
