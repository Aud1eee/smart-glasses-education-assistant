# Reflection Remote Provider Contract

This document defines the expected interface for a **remote reflection provider**.

The purpose is to keep the `Learning Reflection Coach` deployable across:

- local Windows demo mode
- a nearby laptop or phone relay
- a future Rokid-connected service
- a remote campus or cloud endpoint

The reflection page should not need to change when the backend provider changes.

## 1. Provider role

The remote provider does **not** own the learning-state pipeline.

It only receives:

- the structured reflection context
- the current heuristic draft
- optional learner note
- optional next-session goal

Then it returns:

- refined reflection wording
- refined reflection questions
- refined next-session experiments

It should not:

- explain subject knowledge
- behave like an AI tutor chat
- write notes for the learner
- overlap with writing correction or language tutoring

## 2. Environment variables in this project

The current app reads:

```env
LLM_PROVIDER=remote
REFLECTION_REMOTE_URL=http://127.0.0.1:5051/reflect
REFLECTION_REMOTE_AUTH_TOKEN=
REFLECTION_REMOTE_LABEL=remote-reflection-service
```

## 3. Request shape

HTTP:

- method: `POST`
- content type: `application/json`

Authorization:

- optional `Authorization: Bearer <token>`
- sent only when `REFLECTION_REMOTE_AUTH_TOKEN` is configured

### Request body

```json
{
  "instruction": "system-style instruction string",
  "prompt": "full serialized prompt string",
  "schema": {
    "headline": "string",
    "overview": "string",
    "why_it_matters": "string",
    "next_boundary": "string",
    "coach_memo": "string",
    "reflection_questions": [
      { "question": "string" }
    ],
    "next_session_experiments": [
      {
        "title": "string",
        "detail": "string",
        "success_marker": "string"
      }
    ]
  },
  "context": {
    "summary": {},
    "highlight_event": {},
    "distributions": {},
    "anchors": {}
  },
  "draft": {
    "signature": {},
    "coach_summary": {},
    "reflection_questions": [],
    "next_session_experiments": [],
    "coach_memo": "string"
  },
  "learner_note": "string",
  "next_goal": "string"
}
```

## 4. Response shape

The provider should return JSON directly matching this contract:

```json
{
  "headline": "string",
  "overview": "string",
  "why_it_matters": "string",
  "next_boundary": "string",
  "coach_memo": "string",
  "reflection_questions": [
    { "question": "string" },
    { "question": "string" },
    { "question": "string" }
  ],
  "next_session_experiments": [
    {
      "title": "string",
      "detail": "string",
      "success_marker": "string"
    },
    {
      "title": "string",
      "detail": "string",
      "success_marker": "string"
    },
    {
      "title": "string",
      "detail": "string",
      "success_marker": "string"
    }
  ]
}
```

Minimum expectations:

- all top-level string fields must be present
- return at least 3 reflection questions
- return at least 3 next-session experiments
- experiments must include `title`, `detail`, and `success_marker`

## 5. Failure behavior

If the remote provider:

- times out
- returns invalid JSON
- returns the wrong shape

the main app will automatically fall back to `heuristic`.

That means the remote provider can fail without breaking the reflection page.

## 6. Local mock provider

This project now includes a lightweight mock service:

- [mock_reflection_provider.py](../../mock_reflection_provider.py)
- [scripts/legacy/start_mock_reflection_provider.ps1](../../scripts/legacy/start_mock_reflection_provider.ps1)

Default mock endpoint:

- `http://127.0.0.1:5051/reflect`

Health check:

- `http://127.0.0.1:5051/health`

## 7. Local remote-path test

1. Start the mock provider:

```powershell
.\scripts\legacy\start_mock_reflection_provider.ps1
```

2. Set `.env`:

```env
LLM_PROVIDER=remote
REFLECTION_REMOTE_URL=http://127.0.0.1:5051/reflect
REFLECTION_REMOTE_LABEL=mock-reflection-provider
```

3. Start the main project:

```powershell
.\scripts\legacy\start_windows.ps1
```

4. Open:

- `http://127.0.0.1:5000/reflection`

5. Turn on `Use provider-backed wording polish`.

Expected result:

- the reflection page still loads
- `generation.mode` becomes `remote`
- the returned memo includes the mock provider suffix

## 8. Recommended future Rokid deployment shape

For a Rokid-connected deployment, the preferred split is:

1. Rokid or companion client uploads learning-state session data.
2. The main learning-state backend builds the reflection context.
3. A remote reflection provider refines the wording.
4. The final result returns to the review / reflection surface.

This keeps the device-side requirement small and lets the LLM provider change later without changing the reflection page contract.
