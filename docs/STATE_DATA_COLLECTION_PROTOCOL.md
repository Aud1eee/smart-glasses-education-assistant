# State Data Collection Protocol

## 1. Why Real Session Data Matters

The current validation layer improves transparency, but it still depends on **learning-state proxy** signals rather than direct internal-state measurement. Real session data is needed to:

- test whether the proxy behaves consistently across realistic study sessions
- compare rule-based labels with manual review and self-report feedback
- understand where the current proxy is reliable and where it remains uncertain
- build enough labeled windows for credible rule-baseline and sklearn-baseline comparisons

This protocol is designed to extend the existing validation layer without changing the `study_report.csv` schema or rewriting the live engines.

## 2. Recommended Collection Scenarios

Try to cover both relatively stable study behavior and more difficult or noisy situations.

Recommended scenarios:

- stable reading:
  textbook or article reading with one surface and low switching
- screen lecture:
  slide, video lecture, or teacher screen viewing with stable first-person content
- notes switching:
  alternating between slides, notes, and notebook pages
- concept struggle:
  problem solving or review where cognitive load rises but the learner remains engaged
- fatigue / late-session review:
  longer review segments near the end of a study block

## 3. Suggested Duration Per Scenario

Suggested minimum collection lengths:

- stable reading: 8 to 10 minutes
- screen lecture: 8 to 10 minutes
- notes switching: 8 to 10 minutes
- concept struggle: 6 to 8 minutes
- fatigue / late-session review: 6 to 8 minutes

For a first multi-session dataset, a practical target is:

- 3 to 5 participants
- 3 to 5 sessions per participant
- 3 or more scenarios per participant

## 4. Session Manifest

Use `data/session_manifest_template.csv` as the starting point for session-level metadata.

Recommended workflow:

1. Copy `data/session_manifest_template.csv` to `data/session_manifest.csv`.
2. Assign a pseudonymous `participant_id`.
3. Fill one row per session.
4. Keep any real participant-identifying metadata outside the repository.

Key fields:

- `session_id`
- `participant_id`
- `scenario`
- `task_mode`
- `material_type`
- `lighting`
- `capture_source`
- `start_time`
- `duration_seconds`
- `notes`

## 5. How To Label `state_labels.csv`

Recommended process:

1. Generate window features with `python analytics/validate_learning_state.py` or `python core/state_feature_extractor.py`.
2. Build a draft labeling sheet with `python analytics/build_labeling_sheet.py`.
3. Review `data/state_labels_draft.csv`.
4. Use the auto-filled `predicted_label`, `confidence`, `evidence_summary`, and key metrics as a starting point.
5. Fill the manual fields:
   `label`, `self_report_load`, `self_report_attention`, `self_report_fatigue`, `task_difficulty`, `quiz_score`, `notes`
6. Copy curated rows into `data/state_labels.csv`.

Label definitions:

- `stable_focus`
- `load_rising`
- `productive_struggle`
- `off_task_risk`
- `fatigue_risk`
- `signal_uncertain`

Important:

- treat labels as conservative judgments over windows, not precise claims about hidden mental state
- use `signal_uncertain` whenever the scene or signal quality is not strong enough

## 6. How To Run Validation

Main command:

```bash
python analytics/validate_learning_state.py
```

Explicit-path command:

```bash
python analytics/validate_learning_state.py --features data/state_window_features.csv --labels data/state_labels.csv --output-dir exports
```

Useful support commands:

```bash
python analytics/build_labeling_sheet.py
python analytics/summarize_validation_readiness.py
```

## 7. How To Interpret Validation Results

Primary outputs:

- `exports/state_validation_report.md`
- `exports/state_validation_metrics.json`
- `exports/state_confusion_matrix.png` when `matplotlib` is available
- `exports/validation_readiness.md`

How to read them:

- `accuracy`:
  overall agreement between predicted labels and curated labels
- `macro_f1`:
  balanced class performance when labels are uneven
- `confusion_matrix`:
  where classes are being mixed up
- self-report correlations:
  whether load and focus proxies move in roughly the same direction as human self-report

Suggested minimum label volume:

- 20 windows:
  enough to prove the workflow runs end to end
- 50 windows:
  enough for an early internal demo
- 100 windows:
  a better point for comparing rule and sklearn baselines

## 8. Data Privacy Notes

- do not store real participant names in repository files
- use pseudonymous `participant_id` values
- do not commit `data/session_manifest.csv`, `data/state_labels.csv`, or other real participant data files by default
- keep free-text notes free of personally identifying information
- avoid storing unnecessary raw media if derived proxy signals are sufficient
- make sure participants understand what is being collected and how it will be used

The goal of this protocol is to support safer, more explainable learning-state proxy validation rather than over-collecting sensitive personal data.
