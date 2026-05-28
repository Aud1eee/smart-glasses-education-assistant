# Learning-State Sensing Experiment and Validation Draft

This document turns the current validation results into a version that is suitable for direct thesis citation and also usable as a spoken defense summary.

Related raw validation artifacts:

- `exports/validation_summary.md`
- `exports/validation_summary.json`

## 1. Experiment Goal

The purpose of this experiment is not to prove that the system can directly measure a student’s true internal focus state. Instead, it evaluates whether the current **Learning State Guardian** prototype can, under known simulated learning scenarios:

1. produce stable learning-state labels that match expectation
2. maintain consistent state statistics across the full demo pipeline
3. provide a repeatable algorithm-validation baseline for future Rokid-device inputs

So this experiment should be understood as **prototype-consistency validation** and **demo-level algorithm-behavior validation**, not a large-scale real-user study.

## 2. Experiment Target

The validated target is the learning-state sensing backend in this project, mainly including:

- posture-related state estimation:
  - `Behavioral_Alignment`
  - `Cognitive_Load`
  - `Fatigue_Risk`
  - `Confidence_Level`
- adaptive regulation states:
  - `Focus settling`
  - `Stable focus`
  - `Load rising`
  - `High load`
  - `Regulate now`
  - `Fatigue risk`
- difficulty-event marking and the demo pipeline

## 3. Experiment Environment

The validation was executed in the current Windows local project copy:

- `focus_project_windows`

Command:

```powershell
.\scripts\legacy\generate_validation_report.ps1
```

That command automatically runs two parts:

1. four deterministic scenario checks
2. one complete demo-pipeline validation pass

Output files:

- `exports/validation_summary.md`
- `exports/validation_summary.json`

## 4. Experiment Design

### 4.1 Scenario-Level Validation

To verify whether the algorithm behaves reasonably across different learning states, the system constructs four deterministic simulated scenarios:

| Scenario | Meaning | Expected output characteristics |
| --- | --- | --- |
| `stable` | stable learning state | low load, high focus proxy, final state trends toward `Stable focus` |
| `rising` | gradually increasing cognitive load | load enters a medium-to-high range, state should move into `Load rising` or a later regulation state |
| `overload` | prolonged high load | high load, reduced focus proxy, state should enter `High load / Regulate now / Fatigue risk` |
| `recovery` | recovery after overload | load decreases, focus proxy rebounds, final state returns to a stable learning state |

One important note is that the system currently keeps a conservative transition state called `Focus settling`.

Because of that, for both `stable` and `recovery`, a tail-dominant state of either `Focus settling` or `Stable focus` is treated as a reasonable result. This is intentional: the regulation engine keeps a “restabilizing” buffer instead of flipping immediately back to fully stable the moment recovery begins.

### 4.2 Pipeline-Level Validation

Beyond single-scenario checks, the project also runs an end-to-end validation of the full demo pipeline. That flow automatically generates:

- [data/demo_study_report.csv](../../data/demo_study_report.csv)
- [data/demo_difficulty_events.csv](../../data/demo_difficulty_events.csv)

It then checks:

- whether the sample count is sufficient to form a full timeline
- whether average behavioral alignment remains in a reasonable range
- whether average cognitive load shows a mixed pattern of stability, load rise, and recovery
- whether fatigue risk exists without dominating the whole run
- whether drift risk, high-load ratio, and low-confidence ratio stay reasonable
- whether at least one difficulty event is produced

## 5. Evaluation Metrics

This validation mainly uses the following metrics:

- `avg_alignment`: average behavioral alignment
- `avg_focus`: average focus proxy score
- `avg_load`: average cognitive load
- `avg_fatigue`: average fatigue risk
- `drift_ratio`: drift-risk ratio
- `high_load_ratio`: high-load ratio
- `low_conf_ratio`: low-confidence ratio
- `difficulty_event_count`: number of difficulty events

These metrics are not direct measurements of a learner’s true psychological state. They are used to evaluate the **internal consistency** and **behavioral plausibility** of the current algorithmic framework under simulated learning conditions.

## 6. Experiment Results

### 6.1 Scenario-Level Results

The current validation results show that all four deterministic scenarios pass:

| Scenario | Tail-dominant state | Final state | Average load | Average focus proxy | Result |
| --- | --- | --- | ---: | ---: | --- |
| Stable focus | Focus settling | Stable focus | 1.2 | 98.8 | PASS |
| Rising cognitive load | Fatigue risk | Fatigue risk | 55.2 | 49.3 | PASS |
| High-load regulation | Fatigue risk | Fatigue risk | 85.7 | 23.4 | PASS |
| Recovery state | Focus settling | Stable focus | 5.0 | 95.1 | PASS |

This suggests:

- the `stable` and `recovery` scenarios both keep low average load and high focus-proxy scores, and both end in `Stable focus`
- the `rising` scenario reaches an average load of `55.2`, showing that the system can detect medium-to-high regulation pressure
- the `overload` scenario reaches an average load of `85.7` while average focus proxy falls to `23.4`, showing a clear separation from normal study behavior under high pressure

### 6.2 End-to-End Demo Pipeline Results

The complete demo-pipeline check reports `8/8 passed`, with overall status `PASS`.

The main statistics are:

- sample count: `349`
- average behavioral alignment: `63.9`
- average focus proxy: `61.7`
- average cognitive load: `42.6`
- average fatigue risk: `30.6`
- drift-risk ratio: `57.0%`
- high-load ratio: `36.7%`
- low-confidence ratio: `0.0%`
- difficulty-event count: `1`

This means the demo flow contains both stable study segments and clearly elevated-load segments, plus a recovery segment, so it can present the full main pipeline clearly:

**state sensing -> real-time regulation -> difficulty-event marking -> after-class review**

## 7. Experiment Conclusion

Based on the current validation results, the following conclusions can be drawn:

1. the current learning-state sensing prototype produces expected state transitions across four standard simulated scenarios
2. the full demo pipeline passes checks on sample count, load distribution, fatigue risk, and event production
3. the prototype is therefore reasonably stable at the level of **demo-grade validation** and **algorithm-consistency validation**
4. this provides a reliable experimental baseline for replacing simulator input with real Rokid posture and visual input later

## 8. Limitations

Even though the current validation passes, several limitations still need to be stated clearly:

1. the experiment mainly uses deterministic simulated data rather than large-scale real classroom user data
2. the current state inference is still dominated by posture-related features and is not yet a fully multimodal learning-state system
3. the results demonstrate **model-behavior consistency**, not an absolute measurement of real mental learning state
4. under the current Windows runtime bridge, `matplotlib` still has binary-compatibility limitations, so the workflow currently allows “valid numeric summary with skipped heatmap re-export” as an acceptable condition

## 9. Suggested Next Experimental Steps

If the graduation project continues, the next validation layers should include:

1. **real Rokid-input validation**  
   replace the simulator input with actual device posture streams
2. **human-annotation comparison**  
   manually label video segments as stable learning, load rise, fatigue, recovery, and similar states
3. **task-performance comparison**  
   correlate the inferred states with quiz scores, review-hit rate, and task completion outcomes
4. **multimodal extension validation**  
   after adding eye or face features, validate the joint behavior of behavioral alignment, cognitive load, and fatigue risk together

## 10. Thesis-Ready Paragraph

The paragraph below can be used as a starting point in a thesis experiment-and-validation section:

> To validate the stability and consistency of the proposed learning-state sensing prototype, this work constructs a repeatable validation module. The module includes four deterministic simulated learning scenarios, corresponding to stable learning, cognitive-load rise, high-load regulation, and recovery, together with a complete demo pipeline for checking system behavior over a continuous study process. The results show that all four scenario checks pass and that all eight checks in the complete demo pipeline also pass. Specifically, the current demo data contains 349 samples, with average behavioral alignment of 63.9, average cognitive load of 42.6, average fatigue risk of 30.6, a high-load ratio of 36.7%, and one successfully detected difficulty event. These results indicate that the current prototype is stable at the levels of demo-grade validation and algorithm-behavior consistency, and that it can serve as a reliable baseline for later integration with real Rokid smart-glasses input.

## 11. Defense-Friendly Spoken Version

You can explain it like this during a defense:

> In addition to building the system itself, I also built a validation module. It does not just check whether the interface looks correct. It automatically runs four standard scenarios: stable learning, rising load, overload, and recovery. Then it runs the full demo pipeline and checks sample count, average load, fatigue risk, high-load ratio, and difficulty-event count. The current result is 4/4 scenario checks passed and 8/8 demo checks passed, with overall status PASS. That tells me the current prototype is stable at this stage and that its state transitions are consistent with expectation, so it is a suitable baseline for later Rokid-device integration.
