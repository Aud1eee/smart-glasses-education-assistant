# Branch Merge Plan

## Recommended Merge Order

1. `feature/learning-state-validation`
2. `feature/state-data-collection-protocol`
3. `feature/reflection-coach`
4. `feature/demo-storyboard`
5. `feature/presentation-assistant`
6. `feature/state-logic-refactor`
7. `feature/project-hardening`

## Why This Order

The order starts from the validation foundation, then adds collection workflow, then post-session explanation layers, then presentation layers, and finally the state-logic cleanup plus final engineering wrap-up.

## Branch Roles

### `feature/learning-state-validation`

Purpose:

- add a learning-state validation layer on top of the existing system

Main contributions:

- state window feature extraction
- rule baseline and optional sklearn baseline
- validation report outputs
- review evidence support

### `feature/state-data-collection-protocol`

Purpose:

- standardize how real sessions and labels are collected

Main contributions:

- session manifest template
- labeling-sheet draft generation
- validation-readiness summary
- collection and privacy documentation

### `feature/reflection-coach`

Purpose:

- add post-session reflection support

Main contributions:

- rule/template-based reflection summaries
- reflection markdown export
- reflection summary API and UI surface

### `feature/demo-storyboard`

Purpose:

- create a reproducible project demo narrative

Main contributions:

- five-stage storyboard generator
- storyboard markdown export
- demo API and demo page

### `feature/presentation-assistant`

Purpose:

- package the repo into demo and defense support material

Main contributions:

- project positioning
- 3-minute and 5-minute talk scripts
- metric explanations
- defense Q&A

### `feature/state-logic-refactor`

Purpose:

- stabilize and explain state interpretation without replacing legacy sensing logic

Main contributions:

- interpreted learning-state layer
- transition manager
- additional `/status` fields
- light UI preference for interpreted state

### `feature/project-hardening`

Purpose:

- do final engineering wrap-up without adding new business features

Main contributions:

- project overview documentation
- concise README refresh
- demo and validation pipeline scripts
- lightweight smoke tests
- ignore rule cleanup for runtime artifacts

## Merge Notes

- Keep `study_report.csv` schema unchanged during merge.
- Preserve legacy `state_hint` during and after merge.
- Treat all interpreted labels as **learning-state proxies**.
- Avoid describing the merged system as precise attention detection.
