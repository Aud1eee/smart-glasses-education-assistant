# Presentation Assistant

`Presentation Assistant` is a template-based layer for project demos and defense preparation.

It is not part of the Learning State Guardian learning-state judgment main loop.

## Purpose

This module packages the current project state into presentation-friendly outputs:

- `project_positioning`
- `module_explanations`
- `demo_script_3min`
- `demo_script_5min`
- `metric_explanations`
- `defense_qa`
- `limitations`

The goal is to make project explanation and defense preparation reproducible without introducing a new inference engine.

## Inputs

The assistant reuses existing local project structures:

- `review_summary`
- `Reflection Coach` summary
- `Demo Storyboard`
- optional validation metrics from `exports/state_validation_metrics.json`

No external LLM call is used.

## Output Files

Run:

```bash
python analytics/generate_presentation_script.py
```

This generates:

- `exports/presentation_script_3min.md`
- `exports/presentation_script_5min.md`
- `exports/defense_qa.md`

Optional example:

```bash
python analytics/generate_presentation_script.py --dataset demo
python analytics/generate_presentation_script.py --dataset live
python analytics/generate_presentation_script.py --dataset demo --output-dir exports
```

## Local API

The summary API is:

- `GET /api/presentation_assistant_summary`

It returns a structured payload that can be reused by a future presentation page or a local presentation controller.

## Recommended Usage In A Defense

A compact sequence is:

1. Open the HUD to explain the live proxy layer.
2. Open the review page to show event replay and heatmap context.
3. Open Reflection Coach to show post-session reflection support.
4. Open Demo Storyboard to narrate a full session arc.
5. Use Presentation Assistant scripts and Q&A to keep the project explanation consistent.

## Guardrails

The assistant should always use conservative wording:

- `learning-state proxy`
- `cognitive load proxy`
- `behavioral alignment`
- `first-person scene proxy`

It should not claim:

- precise attention detection
- mind reading
- psychological diagnosis
- exact internal state recognition

## Scope Boundary

Presentation Assistant is for:

- project explanation
- demo narration
- defense preparation

It is not for:

- changing the main estimation logic
- replacing review or reflection modules
- asserting stronger inference claims than the core project can support
