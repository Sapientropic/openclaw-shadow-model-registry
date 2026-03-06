#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_HEALTHCHECK_PROMPT = "healthcheck: reply with OK and current provider/model only"


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return copy.deepcopy(default)
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    mode = None
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    if mode is not None:
        os.chmod(tmp_path, mode)
    os.replace(tmp_path, path)


def sanitize_rel_path(path: Path) -> Path:
    return Path(path.as_posix().lstrip("/"))


def backup_file(path: Path, backup_root: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "backupPath": None,
    }
    backup_path = backup_root / sanitize_rel_path(path)
    record["backupPath"] = str(backup_path)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, backup_path)
    return record


def restore_file(record: dict[str, Any]) -> None:
    target = Path(record["path"])
    backup = Path(record["backupPath"])
    if record["exists"]:
        if not backup.exists():
            raise FileNotFoundError(f"Missing backup file: {backup}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
    elif target.exists():
        target.unlink()


def merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def merge_model_list(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in existing:
        model_id = item.get("id")
        if not model_id:
            continue
        by_id[model_id] = copy.deepcopy(item)
        order.append(model_id)
    for item in incoming:
        model_id = item.get("id")
        if not model_id:
            raise ValueError(f"Provider model is missing id: {item}")
        if model_id in by_id:
            by_id[model_id] = merge_dict(by_id[model_id], item)
        else:
            by_id[model_id] = copy.deepcopy(item)
            order.append(model_id)
    return [by_id[model_id] for model_id in order]


def merge_provider(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(existing)
    for key, value in incoming.items():
        if key == "models":
            result[key] = merge_model_list(existing.get("models", []), value)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def run_cmd(
    cmd: list[str],
    *,
    env: dict[str, str],
    timeout: int | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def write_command_result(report_dir: Path, name: str, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    base = report_dir / "commands"
    base.mkdir(parents=True, exist_ok=True)
    stdout_path = base / f"{name}.stdout.txt"
    stderr_path = base / f"{name}.stderr.txt"
    stdout_path.write_text(result.stdout or "", encoding="utf-8")
    stderr_path.write_text(result.stderr or "", encoding="utf-8")
    return {
        "name": name,
        "returncode": result.returncode,
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
    }


def ensure_allowlist_entry(config: dict[str, Any], model_ref: str, value: dict[str, Any] | None = None) -> None:
    defaults = config.setdefault("agents", {}).setdefault("defaults", {}).setdefault("models", {})
    if model_ref not in defaults:
        defaults[model_ref] = copy.deepcopy(value) if value is not None else {}
        return
    if value is None:
        return
    existing = defaults.get(model_ref)
    if isinstance(existing, dict) and isinstance(value, dict):
        defaults[model_ref] = merge_dict(existing, value)
    else:
        defaults[model_ref] = copy.deepcopy(value)


def find_agent_entry(config: dict[str, Any], agent_id: str) -> dict[str, Any]:
    for entry in config.get("agents", {}).get("list", []):
        if entry.get("id") == agent_id:
            return entry
    raise KeyError(f"Agent not found in config: {agent_id}")


def patch_config(config: dict[str, Any], overrides: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    touched_agents: list[str] = []
    models = config.setdefault("models", {})
    requested_models_mode = overrides.get("modelsMode")
    if requested_models_mode is not None:
        models["mode"] = requested_models_mode
    providers = models.setdefault("providers", {})

    for provider_id, provider_patch in overrides.get("providers", {}).items():
        providers[provider_id] = merge_provider(providers.get(provider_id, {}), provider_patch)

    for agent_id, agent_patch in overrides.get("agents", {}).items():
        touched_agents.append(agent_id)
        agent_entry = find_agent_entry(config, agent_id)
        model_patch = agent_patch.get("model", {})
        if model_patch:
            agent_model = agent_entry.setdefault("model", {})
            if "primary" in model_patch:
                agent_model["primary"] = model_patch["primary"]
            if "fallbacks" in model_patch:
                agent_model["fallbacks"] = copy.deepcopy(model_patch["fallbacks"])
        for model_ref, allowlist_cfg in agent_patch.get("allowlist", {}).items():
            ensure_allowlist_entry(config, model_ref, allowlist_cfg)
        primary = model_patch.get("primary")
        if primary:
            ensure_allowlist_entry(config, primary)
        for fallback in model_patch.get("fallbacks", []):
            ensure_allowlist_entry(config, fallback)

    return config, touched_agents


def render_agent_models_file(path: Path, provider_overrides: dict[str, Any]) -> dict[str, Any]:
    data = load_json(path, default={"providers": {}})
    providers = data.setdefault("providers", {})
    for provider_id, provider_patch in provider_overrides.items():
        providers[provider_id] = merge_provider(providers.get(provider_id, {}), provider_patch)
    return data


def render_sessions_file(path: Path, session_overrides: dict[str, Any]) -> dict[str, Any]:
    data = load_json(path, default={})
    for session_key, patch in session_overrides.items():
        entry = data.setdefault(session_key, {})
        for key, value in patch.items():
            entry[key] = copy.deepcopy(value)
    return data


def unique_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def wait_for_gateway(
    env: dict[str, str],
    report_dir: Path,
    timeout_seconds: int = 30,
    command_prefix: str = "run",
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_result: subprocess.CompletedProcess[str] | None = None
    while time.time() < deadline:
        result = run_cmd(["openclaw", "gateway", "status"], env=env, timeout=timeout_seconds)
        last_result = result
        if result.returncode == 0 and "RPC probe: ok" in result.stdout:
            return {
                "ok": True,
                "command": write_command_result(report_dir, f"{command_prefix}-gateway-status", result),
            }
        time.sleep(2)
    if last_result is None:
        raise RuntimeError("Gateway status did not run.")
    return {
        "ok": False,
        "command": write_command_result(report_dir, f"{command_prefix}-gateway-status", last_result),
    }


def run_healthcheck(
    agent_id: str,
    spec: dict[str, Any],
    *,
    env: dict[str, str],
    report_dir: Path,
    command_prefix: str = "run",
) -> dict[str, Any]:
    prompt = spec.get("prompt", DEFAULT_HEALTHCHECK_PROMPT)
    timeout_seconds = int(spec.get("timeoutSeconds", 120))
    cmd = [
        "openclaw",
        "agent",
        "--agent",
        agent_id,
        "--message",
        prompt,
        "--json",
        "--timeout",
        str(timeout_seconds),
    ]
    result = run_cmd(cmd, env=env, timeout=timeout_seconds + 30)
    command_record = write_command_result(report_dir, f"{command_prefix}-healthcheck-{agent_id}", result)
    payload = None
    parse_error = None
    if result.stdout:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
    agent_meta = (((payload or {}).get("result") or {}).get("meta") or {}).get("agentMeta") or {}
    payloads = (((payload or {}).get("result") or {}).get("payloads") or [])
    text = payloads[0].get("text") if payloads else None
    checks = []
    ok = result.returncode == 0 and parse_error is None
    expect_text = spec.get("expectText")
    expect_provider = spec.get("expectProvider")
    expect_model = spec.get("expectModel")
    if expect_text is not None:
        matched = text == expect_text
        checks.append({"field": "text", "expected": expect_text, "actual": text, "matched": matched})
        ok = ok and matched
    if expect_provider is not None:
        actual = agent_meta.get("provider")
        matched = actual == expect_provider
        checks.append({"field": "provider", "expected": expect_provider, "actual": actual, "matched": matched})
        ok = ok and matched
    if expect_model is not None:
        actual = agent_meta.get("model")
        matched = actual == expect_model
        checks.append({"field": "model", "expected": expect_model, "actual": actual, "matched": matched})
        ok = ok and matched
    return {
        "agentId": agent_id,
        "ok": ok,
        "returncode": result.returncode,
        "parseError": parse_error,
        "text": text,
        "agentMeta": agent_meta,
        "checks": checks,
        "command": command_record,
    }


def run_models_status(
    agent_id: str,
    *,
    env: dict[str, str],
    report_dir: Path,
    command_prefix: str = "run",
    expect_resolved: str | None = None,
) -> dict[str, Any]:
    result = run_cmd(
        ["openclaw", "models", "status", "--agent", agent_id, "--json"],
        env=env,
        timeout=60,
    )
    command_record = write_command_result(report_dir, f"{command_prefix}-models-status-{agent_id}", result)
    payload = None
    parse_error = None
    if result.stdout:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
    checks = []
    ok = result.returncode == 0 and parse_error is None
    missing = (((payload or {}).get("auth") or {}).get("missingProvidersInUse") or [])
    missing_ok = missing == []
    checks.append({"field": "missingProvidersInUse", "expected": [], "actual": missing, "matched": missing_ok})
    ok = ok and missing_ok
    if expect_resolved is not None:
        actual = (payload or {}).get("resolvedDefault")
        matched = actual == expect_resolved
        checks.append({"field": "resolvedDefault", "expected": expect_resolved, "actual": actual, "matched": matched})
        ok = ok and matched
    return {
        "agentId": agent_id,
        "ok": ok,
        "returncode": result.returncode,
        "parseError": parse_error,
        "resolvedDefault": (payload or {}).get("resolvedDefault"),
        "defaultModel": (payload or {}).get("defaultModel"),
        "checks": checks,
        "command": command_record,
    }


def rollback(records: list[dict[str, Any]], report_dir: Path) -> None:
    for record in reversed(records):
        restore_file(record)
    (report_dir / "rollback.done").write_text(datetime.now().isoformat(), encoding="utf-8")


def build_env(config_path: Path, state_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OPENCLAW_CONFIG_PATH"] = str(config_path)
    env["OPENCLAW_STATE_DIR"] = str(state_dir)
    return env


def build_report_dir(report_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_dir = report_root / f"openclaw-model-patch-{stamp}"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch OpenClaw model registry with local overrides.")
    parser.add_argument(
        "--overrides",
        default=str(Path(__file__).with_name("openclaw-model-overrides.json")),
        help="Path to overrides JSON file.",
    )
    parser.add_argument(
        "--config",
        default=str(Path.home() / ".openclaw" / "openclaw.json"),
        help="OpenClaw config path.",
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help="OpenClaw state dir. Defaults to the parent directory of --config.",
    )
    parser.add_argument(
        "--report-root",
        default=str(Path(__file__).resolve().parent / "reports"),
        help="Directory for run reports and backups.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only render the planned patch summary.")
    parser.add_argument("--skip-restart", action="store_true", help="Do not restart the gateway.")
    parser.add_argument("--skip-healthcheck", action="store_true", help="Skip post-restart healthchecks.")
    parser.add_argument(
        "--allow-empty-overrides",
        action="store_true",
        help="Allow running with an empty overrides file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overrides_path = Path(args.overrides).expanduser().resolve()
    config_path = Path(args.config).expanduser().resolve()
    state_dir = Path(args.state_dir).expanduser().resolve() if args.state_dir else config_path.parent
    report_root = Path(args.report_root).expanduser().resolve()
    report_dir = build_report_dir(report_root)
    backups_root = report_dir / "backups"
    summary: dict[str, Any] = {
        "startedAt": datetime.now().isoformat(),
        "overridesPath": str(overrides_path),
        "configPath": str(config_path),
        "stateDir": str(state_dir),
        "reportDir": str(report_dir),
        "dryRun": args.dry_run,
        "rollback": {"performed": False, "reason": None},
    }

    overrides = load_json(overrides_path, default={"providers": {}, "agents": {}})
    if not overrides.get("providers") and not overrides.get("agents") and not args.allow_empty_overrides:
        summary["error"] = "Overrides file is empty."
        atomic_write_json(report_dir / "summary.json", summary)
        print("Overrides file is empty. Use --allow-empty-overrides to inspect only.", file=sys.stderr)
        return 2

    config = load_json(config_path)
    patched_config, touched_agents = patch_config(copy.deepcopy(config), overrides)
    provider_overrides = overrides.get("providers", {})

    touched_files: list[Path] = [config_path]
    planned_file_data: dict[Path, Any] = {config_path: patched_config}
    for agent_id in touched_agents:
        if provider_overrides:
            models_path = state_dir / "agents" / agent_id / "agent" / "models.json"
            touched_files.append(models_path)
            planned_file_data[models_path] = render_agent_models_file(models_path, provider_overrides)
        session_overrides = overrides.get("agents", {}).get(agent_id, {}).get("sessionOverrides", {})
        if session_overrides:
            session_path = state_dir / "agents" / agent_id / "sessions" / "sessions.json"
            touched_files.append(session_path)
            planned_file_data[session_path] = render_sessions_file(session_path, session_overrides)
    touched_files = unique_paths(touched_files)

    summary["touchedAgents"] = touched_agents
    summary["touchedFiles"] = [str(path) for path in touched_files]
    original_primary_by_agent = {
        agent_id: find_agent_entry(config, agent_id).get("model", {}).get("primary")
        for agent_id in touched_agents
    }

    preview = {
        "modelsMode": overrides.get("modelsMode"),
        "providers": list(overrides.get("providers", {}).keys()),
        "agents": overrides.get("agents", {}),
    }
    atomic_write_json(report_dir / "planned-overrides.json", preview)
    atomic_write_json(report_dir / "patched-config.preview.json", patched_config)

    if args.dry_run:
        summary["status"] = "dry-run"
        atomic_write_json(report_dir / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    planned_changes = []
    changed_files: list[Path] = []
    for path in touched_files:
        current_exists = path.exists()
        current_data = load_json(path) if current_exists else None
        target_data = planned_file_data[path]
        changed = (not current_exists) or current_data != target_data
        planned_changes.append(
            {
                "path": str(path),
                "exists": current_exists,
                "changed": changed,
            }
        )
        if changed:
            changed_files.append(path)
    summary["filePlan"] = planned_changes
    summary["changedFiles"] = [str(path) for path in changed_files]
    summary["unchangedFiles"] = [item["path"] for item in planned_changes if not item["changed"]]

    if not changed_files:
        summary["status"] = "noop"
        atomic_write_json(report_dir / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    preflight_env = build_env(report_dir / "patched-config.preview.json", state_dir)
    preflight_validate = run_cmd(["openclaw", "config", "validate"], env=preflight_env, timeout=60)
    summary["preflightValidate"] = write_command_result(report_dir, "preflight-config-validate", preflight_validate)
    if preflight_validate.returncode != 0:
        summary["error"] = "Preflight config validation failed."
        summary["status"] = "preflight-failed"
        atomic_write_json(report_dir / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 2

    env = build_env(config_path, state_dir)
    before_models_status = []
    for agent_id in touched_agents:
        before_models_status.append(
            run_models_status(
                agent_id,
                env=env,
                report_dir=report_dir,
                command_prefix="before",
                expect_resolved=original_primary_by_agent.get(agent_id),
            )
        )
    if before_models_status:
        summary["beforeModelsStatus"] = before_models_status

    backup_records = [backup_file(path, backups_root) for path in changed_files]
    summary["backups"] = backup_records

    try:
        for path in changed_files:
            atomic_write_json(path, planned_file_data[path])

        validate_result = run_cmd(["openclaw", "config", "validate"], env=env, timeout=60)
        summary["validate"] = write_command_result(report_dir, "config-validate", validate_result)
        if validate_result.returncode != 0:
            raise RuntimeError("Config validation failed.")

        if not args.skip_restart:
            restart_result = run_cmd(["openclaw", "gateway", "restart"], env=env, timeout=120)
            summary["restart"] = write_command_result(report_dir, "gateway-restart", restart_result)
            if restart_result.returncode != 0:
                raise RuntimeError("Gateway restart failed.")
            gateway_status = wait_for_gateway(env, report_dir, timeout_seconds=45, command_prefix="run")
            summary["gatewayStatus"] = gateway_status
            if not gateway_status["ok"]:
                raise RuntimeError("Gateway did not become healthy after restart.")

        models_status = []
        for agent_id in touched_agents:
            models_status.append(
                run_models_status(
                    agent_id,
                    env=env,
                    report_dir=report_dir,
                    command_prefix="run",
                    expect_resolved=overrides.get("agents", {}).get(agent_id, {}).get("model", {}).get("primary"),
                )
            )
        if models_status:
            summary["modelsStatus"] = models_status
            failed_models_status = [item for item in models_status if not item["ok"]]
            if failed_models_status:
                raise RuntimeError(
                    "Model status check failed for agent(s): "
                    + ", ".join(item["agentId"] for item in failed_models_status)
                )

        if not args.skip_healthcheck:
            healthchecks = []
            for agent_id, agent_patch in overrides.get("agents", {}).items():
                spec = agent_patch.get("healthcheck")
                if not spec:
                    continue
                healthchecks.append(
                    run_healthcheck(
                        agent_id,
                        spec,
                        env=env,
                        report_dir=report_dir,
                        command_prefix="run",
                    )
                )
            summary["healthchecks"] = healthchecks
            failed = [item for item in healthchecks if not item["ok"]]
            if failed:
                raise RuntimeError(f"Healthcheck failed for agent(s): {', '.join(item['agentId'] for item in failed)}")

        summary["status"] = "applied"
        atomic_write_json(report_dir / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        summary["error"] = str(exc)
        summary["rollback"]["performed"] = True
        summary["rollback"]["reason"] = str(exc)
        rollback(backup_records, report_dir)
        restore_validate = run_cmd(["openclaw", "config", "validate"], env=env, timeout=60)
        summary["restoreValidate"] = write_command_result(report_dir, "restore-config-validate", restore_validate)
        if not args.skip_restart:
            restore_restart = run_cmd(["openclaw", "gateway", "restart"], env=env, timeout=120)
            summary["restoreRestart"] = write_command_result(report_dir, "restore-gateway-restart", restore_restart)
            restore_gateway_status = wait_for_gateway(
                env,
                report_dir,
                timeout_seconds=45,
                command_prefix="restore",
            )
            summary["restoreGatewayStatus"] = restore_gateway_status
        restore_models_status = []
        for agent_id in touched_agents:
            restore_models_status.append(
                run_models_status(
                    agent_id,
                    env=env,
                    report_dir=report_dir,
                    command_prefix="restore",
                    expect_resolved=original_primary_by_agent.get(agent_id),
                )
            )
        if restore_models_status:
            summary["restoreModelsStatus"] = restore_models_status
        if not args.skip_healthcheck:
            restore_healthchecks = []
            for agent_id, agent_patch in overrides.get("agents", {}).items():
                spec = agent_patch.get("restoreHealthcheck") or agent_patch.get("rollbackHealthcheck")
                if not spec:
                    continue
                restore_healthchecks.append(
                    run_healthcheck(
                        agent_id,
                        spec,
                        env=env,
                        report_dir=report_dir,
                        command_prefix="restore",
                    )
                )
            summary["restoreHealthchecks"] = restore_healthchecks
        summary["status"] = "rolled-back"
        atomic_write_json(report_dir / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
