# Learning State Validation

## 1. Why Validation Matters

The current Learning State Guardian pipeline is useful for live guidance, but its outputs are still best treated as **learning-state proxy estimation** rather than precise attention detection. Validation adds a conservative second layer that helps us:

- move from single-frame or single-threshold judgments toward 5s/10s temporal windows
- compare rule outputs with manual labels and self-report data
- measure where the current proxy is reliable and where it is uncertain
- expose confidence and evidence on the review page

## 2. Conservative Framing

This repository does **not** claim to read minds or precisely detect attention.

Recommended wording:

- learning-state proxy
- cognitive load proxy
- behavioral alignment
- first-person scene proxy
- confidence and evidence

The validation layer is designed to make the existing system more transparent and easier to audit, not to overstate certainty.

## 3. Signal Sources

The validation layer combines four signal groups:

- posture / motion:
  `Relative_Pitch`, `Relative_Yaw`, `Relative_Roll`, `Combined_Drift`, `Motion_Intensity`, `Stability`
- first-person scene features:
  `Scene_Content_Score`, `Scene_Text_Score`, `Scene_Stability_Score`, `Scene_Switch_Rate`, `Study_Surface_Score`, `Scene_Lock_Score`, `Blur_Score`, `Brightness_Score`
- session state:
  `Focus_Score`, `Cognitive_Load`, `Behavioral_Alignment`, `Fatigue_Risk`, `Uncertainty_Score`, `Switching_Index`, `State_Hint`, `Load_Level`, `Task_Mode`
- human feedback:
  manual labels, self-report load, self-report attention, self-report fatigue, task difficulty, and optional quiz score

## 4. Generate Window Features

The new extractor converts sample-level logs into sliding-window features.

Default behavior:

- `window_seconds = 10`
- `step_seconds = 5`

Example:

```bash
python core/state_feature_extractor.py \
  --input data/study_report.csv \
  --output data/state_window_features.csv \
  --window-seconds 10 \
  --step-seconds 5
```

What it outputs:

- one row per window
- majority fields for task mode / state hint / load level
- `mean / std / min / max / range / slope` for supported numeric fields
- extra ratios such as `high_load_ratio`, `low_focus_ratio`, `off_task_hint_ratio`, `productive_struggle_ratio`, `signal_check_ratio`, `scene_locked_ratio`, `unstable_scene_ratio`

Missing source fields do not crash the extractor. They are skipped and recorded in the validation report.

## 5. Fill `state_labels.csv`

Template file:

- `data/state_labels_template.csv`

Runtime behavior:

- if `data/state_labels.csv` does not exist, the validation script automatically creates it from the template

Columns:

- `session_id`
- `start_sample`
- `end_sample`
- `label`
- `self_report_load`
- `self_report_attention`
- `self_report_fatigue`
- `task_difficulty`
- `quiz_score`
- `notes`

Allowed `label` values:

- `stable_focus`
- `load_rising`
- `productive_struggle`
- `off_task_risk`
- `fatigue_risk`
- `signal_uncertain`

Suggested labeling workflow:

1. Run the extractor and open the review page or exported heatmap.
2. Pick a window or difficulty segment by sample range.
3. Fill `session_id`, `start_sample`, and `end_sample`.
4. Choose the most conservative label that matches the observed pattern.
5. Add self-report values on a 1-7 scale.
6. Add `quiz_score` only when a real short assessment exists.
7. Use `notes` to explain ambiguous cases.

Self-report scales:

- `self_report_load`: `1 = very low load`, `7 = very high load`
- `self_report_attention`: `1 = very unfocused`, `7 = very focused`
- `self_report_fatigue`: `1 = not fatigued`, `7 = very fatigued`
- `task_difficulty`: `1 = very easy`, `7 = very difficult`

### Build A Labeling Draft

You can prefill a draft sheet before manual review:

```bash
python analytics/build_labeling_sheet.py
python analytics/build_labeling_sheet.py --features data/state_window_features.csv --output data/state_labels_draft.csv
```

The draft file includes:

- `predicted_label`
- `confidence`
- `evidence_summary`
- key window metrics such as `cognitive_load_mean` and `scene_lock_score_mean`

The script preserves any manual values already present in `data/state_labels_draft.csv` when it regenerates the draft.

### Move From `state_labels_draft.csv` To `state_labels.csv`

Recommended flow:

1. Generate `data/state_labels_draft.csv`.
2. Review each row and update the manual fields.
3. Copy the curated columns into `data/state_labels.csv`.
4. Keep `data/state_labels_draft.csv` as a working draft and `data/state_labels.csv` as the cleaner evaluation file.

## 6. Run Validation

Example:

```bash
python analytics/validate_learning_state.py \
  --features data/state_window_features.csv \
  --labels data/state_labels.csv \
  --output-dir exports
```

Quick commands:

```bash
python analytics/validate_learning_state.py
python analytics/validate_learning_state.py --features data/state_window_features.csv --labels data/state_labels.csv --output-dir exports
```

Script behavior:

1. Creates `data/state_labels_template.csv` if needed.
2. Creates `data/state_labels.csv` from the template if it is missing.
3. Auto-generates `data/state_window_features.csv` from `data/study_report.csv` if needed.
4. Aligns labels to windows by `session_id + sample overlap`.
5. Runs the rule baseline on all windows.
6. Trains an sklearn baseline only when enough labels are available.
7. Writes the report, metrics JSON, and confusion matrix.

## 7. How To Read The Outputs

Generated artifacts:

- `exports/state_validation_report.md`
- `exports/state_validation_metrics.json`
- `exports/state_confusion_matrix.png`
- `exports/state_classifier_model.joblib` when sklearn training succeeds

Key metrics:

- `accuracy`: overall agreement between predicted label and manual label
- `macro_f1`: balanced class-level performance, useful when labels are uneven
- `per_class_precision`: how often a predicted class was correct
- `per_class_recall`: how often a labeled class was recovered
- `confusion_matrix`: where classes are being mixed up
- `correlation_between_predicted_load_and_self_report_load`: whether the cognitive load proxy roughly tracks human self-report
- `correlation_between_focus_score_and_self_report_attention`: whether the focus proxy roughly tracks self-reported attention

Interpretation guidance:

- 20 labeled windows:
  enough to prove the workflow runs end to end
- 50 labeled windows:
  enough for an early internal demo
- 100 labeled windows:
  a better point for comparing the rule baseline and sklearn baseline
- high accuracy with low macro F1 often means one or two classes dominate
- low confusion between `productive_struggle` and `off_task_risk` is especially valuable for coaching quality
- strong correlations can support the proxy, but they do not prove precise internal-state measurement

## 8. Current Limits

- sample size may be too small for stable estimates
- self-report labels are subjective
- different users may show different posture and scene patterns
- without eye tracking or pupil data, this remains a proxy estimator

## 9. Future Additions

Potential next signals:

- gaze
- blink
- fixation
- quiz performance
- NASA-TLX short form

These additions can improve proxy quality, especially when combined with the current posture, scene, and self-report features.
