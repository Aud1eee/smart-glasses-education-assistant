# Ollama Reflection Setup

This document is the practical Windows checklist for running the `Learning Reflection Coach` with a **free local model**.

Recommended local default:

- provider: `ollama`
- model: `qwen3:4b`

The reflection module still keeps a heuristic fallback, so if the model provider is down, the page should keep working.

## 1. Install Ollama

Install Ollama for Windows from the official site:

- [Ollama docs](https://docs.ollama.com/)

After installation, confirm that the `ollama` command works in PowerShell:

```powershell
ollama --version
```

## 2. Pull a free local model

Recommended first model:

```powershell
ollama pull qwen3:4b
```

Optional larger local variant:

```powershell
ollama pull qwen3:8b
```

Official model page:

- [Ollama qwen3 library page](https://ollama.com/library/qwen3)

## 3. Confirm Ollama is responding

Quick check:

```powershell
ollama run qwen3:4b "Return exactly: ollama ready"
```

API check:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:11434/api/tags
```

If the API responds, the local reflection page can try provider-backed wording polish.

## 4. Configure this project

Set `.env` like this:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434/api
OLLAMA_MODEL=qwen3:4b
OLLAMA_TIMEOUT_SECONDS=120
```

You do not need `OPENAI_API_KEY` for this path.

## 5. Run the project

In one terminal:

```powershell
.\scripts\legacy\start_windows.ps1
```

If needed, in a second terminal:

```powershell
.\scripts\legacy\start_simulator.ps1
```

Open:

- `http://127.0.0.1:5000/reflection`

## 6. Reflection page test flow

1. Keep provider on `Configured Default` or switch it to `Ollama Local`.
2. Turn on `Use provider-backed wording polish`.
3. Add an optional learner note or next goal.
4. Generate the coach view.

Expected behavior:

- if Ollama is reachable, `generation.mode` should show `ollama`
- if Ollama is unavailable, the page should fall back to `heuristic`

## 7. Typical failure cases

### `generation.mode = heuristic` even though Ollama was selected

Likely causes:

- Ollama app or service is not running
- `qwen3:4b` was not pulled yet
- `OLLAMA_BASE_URL` does not match the local service
- the local model is slow enough that the request hits the timeout limit

Check:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:11434/api/tags
```

### Ollama works in terminal but not in the app

Check that `.env` matches:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434/api
OLLAMA_MODEL=qwen3:4b
```

Then restart the Flask backend.

If the local model is large or cold-starting, increase:

```env
OLLAMA_TIMEOUT_SECONDS=120
```

## 8. Recommended project stance

For this graduation-project module, the local model should only do:

- reflection wording polish
- metacognitive question refinement
- next-session experiment phrasing

It should not do:

- content tutoring
- knowledge explanation
- writing correction
- note taking
- open-ended AI conversation

That keeps the module aligned with the project boundary and distinct from teammate directions.
