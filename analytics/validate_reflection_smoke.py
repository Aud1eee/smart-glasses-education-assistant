import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bootstrap_windows_runtime  # noqa: F401

from analytics.generate_demo_assets import generate_demo_report


REFLECTION_SMOKE_JSON_PATH = ROOT / "exports" / "reflection_smoke_summary.json"
REFLECTION_SMOKE_MD_PATH = ROOT / "exports" / "reflection_smoke_summary.md"
DEFAULT_PORT = 5012
DEFAULT_COMPARE_TIMEOUT = 260
SERVER_BOOTSTRAP = "import bootstrap_windows_runtime; import serve_app; serve_app.main()"


def _http_request(method, url, payload=None, timeout=40):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.getcode(), response.read().decode("utf-8")


def _http_json(method, url, payload=None, timeout=40):
    status, body = _http_request(method, url, payload=payload, timeout=timeout)
    return status, json.loads(body)


def _wait_for_backend(base_url, timeout_seconds=25):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            status, _ = _http_json("GET", f"{base_url}/api/reflection_provider_status?provider_override=heuristic", timeout=6)
            if status == 200:
                return
        except Exception as exc:  # pragma: no cover - smoke fallback
            last_error = exc
        time.sleep(0.6)
    raise RuntimeError(f"Backend did not start in time: {last_error}")


def _terminate_process_tree(process):
    if process is None:
        return
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                check=False,
                capture_output=True,
            )
        else:
            process.terminate()
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _launch_backend(port):
    env = os.environ.copy()
    env["FOCUS_PROJECT_HOST"] = "127.0.0.1"
    env["FOCUS_PROJECT_PORT"] = str(port)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-B", "-c", SERVER_BOOTSTRAP],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    return process


def _check(name, passed, detail, status=None, artifact=None):
    normalized_status = status or ("PASS" if passed else "REVIEW")
    return {
        "name": name,
        "status": normalized_status,
        "passed": bool(passed),
        "detail": detail,
        "artifact": artifact or "",
    }


def _to_json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    return value


def _build_markdown(payload):
    check_rows = []
    for item in payload["checks"]:
        check_rows.append(
            "| {name} | {status} | {detail} | {artifact} |".format(
                name=item["name"],
                status=item["status"],
                detail=item["detail"],
                artifact=item["artifact"] or "--",
            )
        )

    provider = payload.get("provider_status", {})
    runtime = payload.get("runtime_info", {})
    ollama = provider.get("ollama", {})
    models = ", ".join(item.get("name", "") for item in ollama.get("available_models", []) if item.get("name")) or "--"

    return "\n".join([
        "# Reflection Smoke Summary",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Overall status: **{payload['overall_status']}**",
        f"- Backend bootstrap: `{payload['backend_bootstrap']}`",
        f"- Validation port: `{payload['port']}`",
        f"- Demo session: `{payload['session_id']}`",
        f"- Provider requested: `{provider.get('requested_provider', '--')}`",
        f"- Backend runtime: `{runtime.get('backend_version', '--')}`",
        f"- Snapshot exporter: `{runtime.get('snapshot_exporter_version', '--')}`",
        f"- Ollama reachable: `{ollama.get('reachable', False)}`",
        f"- Ollama models: {models}",
        "",
        "## Checks",
        "",
        "| Check | Result | Detail | Artifact |",
        "| --- | --- | --- | --- |",
        *check_rows,
        "",
        "## Notes",
        "",
        "- This smoke validator boots a temporary backend through the same import-based launcher family used by the Windows startup path.",
        "- The compare endpoint is skipped when fewer than two local Ollama models are available.",
        "- Demo assets are regenerated before the checks run so the reflection flow always has deterministic evidence.",
        "",
    ])


def main():
    port = int(os.environ.get("REFLECTION_SMOKE_PORT", DEFAULT_PORT))
    compare_timeout = int(os.environ.get("REFLECTION_COMPARE_TIMEOUT_SECONDS", DEFAULT_COMPARE_TIMEOUT))
    session_id = "demo-session-1"
    base_url = f"http://127.0.0.1:{port}"
    exports_dir = ROOT / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    generate_demo_report(session_id=session_id)
    process = None
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_status": "REVIEW",
        "backend_bootstrap": SERVER_BOOTSTRAP,
        "port": port,
        "session_id": session_id,
        "checks": [],
        "provider_status": {},
        "runtime_info": {},
    }

    try:
        try:
            process = _launch_backend(port)
            _wait_for_backend(base_url)

            status, provider_status = _http_json("GET", f"{base_url}/api/reflection_provider_status?provider_override=heuristic")
            payload["provider_status"] = provider_status
            payload["checks"].append(
                _check(
                    "provider-status",
                    status == 200 and bool(provider_status.get("provider_options")),
                    f"reflection provider status responded with {len(provider_status.get('provider_options', []))} provider option(s).",
                )
            )

            runtime_status, runtime_info = _http_json("GET", f"{base_url}/api/runtime_info")
            payload["runtime_info"] = runtime_info
            runtime_ok = (
                runtime_status == 200
                and bool(runtime_info.get("backend_version"))
                and bool((runtime_info.get("feature_flags") or {}).get("snapshot_html_card_export"))
            )
            payload["checks"].append(
                _check(
                    "runtime-info",
                    runtime_ok,
                    f"runtime endpoint reported backend `{runtime_info.get('backend_version', '--')}` and snapshot exporter `{runtime_info.get('snapshot_exporter_version', '--')}`.",
                )
            )

            review_status, review_html = _http_request(
                "GET",
                f"{base_url}/review?dataset=demo&session_id={urllib.parse.quote(session_id)}&event_id=1",
            )
            review_ok = review_status == 200 and "Open in Reflection Coach" in review_html and "buildReflectionHref" in review_html
            payload["checks"].append(
                _check(
                    "review-to-reflection-link",
                    review_ok,
                    "review page exposes the reflection link entry and event-aware route builder.",
                )
            )

            reflection_status, reflection_html = _http_request(
                "GET",
                f"{base_url}/reflection?dataset=demo&session_id={urllib.parse.quote(session_id)}&event_id=1",
            )
            reflection_ok = (
                reflection_status == 200
                and "Evidence Anchor" in reflection_html
                and "function renderAnchor" in reflection_html
                and "Runtime Snapshot" in reflection_html
                and "runtime-badge-title" in reflection_html
            )
            payload["checks"].append(
                _check(
                    "reflection-anchor-page",
                    reflection_ok,
                    "reflection page renders the evidence-anchor panel, runtime badge, and route-sync logic.",
                )
            )

            coach_request = {
                "dataset": "demo",
                "session_id": session_id,
                "event_id": "99",
                "learner_note": "",
                "next_goal": "",
                "provider_override": "heuristic",
                "use_llm": False,
            }
            coach_status, coach_payload = _http_json("POST", f"{base_url}/api/reflection_coach", payload=coach_request)
            coach_ok = (
                coach_status == 200
                and coach_payload.get("requested_event_id") == 99
                and coach_payload.get("selected_event_id") == 1
                and (coach_payload.get("highlight_event") or {}).get("event_id") == 1
            )
            payload["checks"].append(
                _check(
                    "reflection-coach-fallback",
                    coach_ok,
                    "invalid event_id falls back to the strongest difficulty event without breaking the coach payload.",
                )
            )

            snapshot_status, snapshot_result = _http_json(
                "POST",
                f"{base_url}/api/reflection_snapshot",
                payload={"kind": "single", "payload": coach_payload},
            )
            snapshot_json = json.loads(Path(snapshot_result["json_path"]).read_text(encoding="utf-8"))
            snapshot_md = Path(snapshot_result["md_path"]).read_text(encoding="utf-8")
            snapshot_card = Path(snapshot_result["card_path"]).read_text(encoding="utf-8")
            single_snapshot_ok = (
                snapshot_status == 200
                and snapshot_json.get("requested_event_id") == 99
                and snapshot_json.get("selected_event_id") == 1
                and "## Evidence Anchor" in snapshot_md
                and "Anchor reason:" in snapshot_md
                and "## Replay Anchor" not in snapshot_md
                and "Evidence Anchor" in snapshot_card
                and "Coach Memo" in snapshot_card
                and "Reflection Questions" in snapshot_card
            )
            payload["checks"].append(
                _check(
                    "reflection-snapshot-single",
                    single_snapshot_ok,
                    "single snapshot keeps the selected anchor ids and writes the evidence-anchor markdown plus HTML summary card.",
                    artifact=snapshot_result["card_path"],
                )
            )

            compare_models = [
                item.get("name", "").strip()
                for item in (provider_status.get("ollama", {}) or {}).get("available_models", [])
                if item.get("name")
            ]
            if len(compare_models) >= 2:
                try:
                    compare_status, compare_payload = _http_json(
                        "POST",
                        f"{base_url}/api/reflection_compare",
                        payload={
                            "dataset": "demo",
                            "session_id": session_id,
                            "event_id": "99",
                            "learner_note": "",
                            "next_goal": "",
                            "models": compare_models[:2],
                        },
                        timeout=compare_timeout,
                    )
                    compare_ok = compare_status == 200 and len(compare_payload.get("variants", [])) == 2
                    payload["checks"].append(
                        _check(
                            "reflection-compare-endpoint",
                            compare_ok,
                            f"compare endpoint returned {len(compare_payload.get('variants', []))} variant(s).",
                        )
                    )

                    compare_snapshot_status, compare_snapshot_result = _http_json(
                        "POST",
                        f"{base_url}/api/reflection_snapshot",
                        payload={"kind": "compare", "payload": compare_payload},
                        timeout=compare_timeout,
                    )
                    compare_snapshot_md = Path(compare_snapshot_result["md_path"]).read_text(encoding="utf-8")
                    compare_snapshot_card = Path(compare_snapshot_result["card_path"]).read_text(encoding="utf-8")
                    compare_snapshot_ok = (
                        compare_snapshot_status == 200
                        and "## Shared Evidence Anchor" in compare_snapshot_md
                        and "Anchor reason:" in compare_snapshot_md
                        and "## Replay Anchor" not in compare_snapshot_md
                        and "Reflection Compare Card" in compare_snapshot_card
                        and "Evidence Anchor" in compare_snapshot_card
                    )
                    payload["checks"].append(
                        _check(
                            "reflection-snapshot-compare",
                            compare_snapshot_ok,
                            "compare snapshot writes the shared evidence-anchor section and HTML compare card for the compared variants.",
                            artifact=compare_snapshot_result["card_path"],
                        )
                    )
                except Exception as exc:  # pragma: no cover - environment-sensitive
                    payload["checks"].append(
                        _check(
                            "reflection-compare-endpoint",
                            False,
                            f"compare endpoint failed before completion: {exc.__class__.__name__}: {exc}",
                        )
                    )
                    payload["checks"].append(
                        _check(
                            "reflection-snapshot-compare",
                            False,
                            "compare snapshot was not created because the compare endpoint did not complete successfully.",
                        )
                    )
            else:
                payload["checks"].append(
                    _check(
                        "reflection-compare-endpoint",
                        True,
                        "compare endpoint skipped because fewer than two local Ollama models were detected.",
                        status="SKIP",
                    )
                )
                payload["checks"].append(
                    _check(
                        "reflection-snapshot-compare",
                        True,
                        "compare snapshot skipped because the compare endpoint did not run.",
                        status="SKIP",
                    )
                )
        except Exception as exc:  # pragma: no cover - smoke fallback
            payload["checks"].append(
                _check(
                    "reflection-smoke-runner",
                    False,
                    f"smoke validator aborted unexpectedly: {exc.__class__.__name__}: {exc}",
                )
            )

    finally:
        _terminate_process_tree(process)

    non_skipped = [item for item in payload["checks"] if item["status"] != "SKIP"]
    payload["overall_status"] = "PASS" if all(item["passed"] for item in non_skipped) else "REVIEW"
    safe_payload = _to_json_safe(payload)
    REFLECTION_SMOKE_JSON_PATH.write_text(json.dumps(safe_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    REFLECTION_SMOKE_MD_PATH.write_text(_build_markdown(safe_payload), encoding="utf-8")

    print("\nReflection smoke validation")
    print(f"- Overall status: {payload['overall_status']}")
    print(f"- Checks: {len(payload['checks'])}")
    print(f"- JSON: {REFLECTION_SMOKE_JSON_PATH}")
    print(f"- Markdown: {REFLECTION_SMOKE_MD_PATH}")

    if payload["overall_status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
