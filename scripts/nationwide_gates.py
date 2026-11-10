"""Manage local gate servers and build the mobile/detail verification commands.

Run .venv/Scripts/python.exe scripts/run_nationwide.py run --bundles 1.
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide.py.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from scripts.nationwide_state import atomic_json, now
from scripts.nationwide_steps import (
    API_URL,
    OUTPUT,
    PUBLIC_DATABASE,
    WEB_URL,
    Step,
    command,
    gate_steps,
    round_key,
)

READY_TIMEOUT_SECONDS = 300
READY_POLL_SECONDS = 0.2
MOBILE_PATHS = ("/", "/cases", "/references")
RENDERER_METRICS = ("source_text_loss_document_count", "rendered_table_topology_failure_count")


def native_argv(argv: tuple[str, ...]) -> list[str]:
    result = list(argv)
    if os.name == "nt" and result[0] in ("npm", "npx", "node", "git"):
        result[0] = shutil.which(result[0]) or result[0]
    return result


@dataclass
class Server:
    process: subprocess.Popen
    log_path: Path
    stream: object


def start_server(step: Step, log_path: Path) -> Server:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stream = log_path.open("wb")
    try:
        process = subprocess.Popen(native_argv(step.argv), cwd=step.cwd, env=step.env,
                                   stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT)
    except BaseException:
        stream.close()
        raise
    return Server(process, log_path, stream)


def wait_ready(server: Server, marker: str) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if server.process.poll() is not None:
            raise RuntimeError(f"server exited before ready: {server.log_path}")
        if marker in server.log_path.read_text(encoding="utf-8", errors="replace"):
            return
        time.sleep(READY_POLL_SECONDS)
    raise TimeoutError(f"server readiness timeout: {server.log_path}")


def stop_server(server: Server) -> None:
    try:
        if os.name == "nt" and server.process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(server.process.pid), "/T", "/F"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.STDOUT, check=False)
        elif server.process.poll() is None:
            server.process.terminate()
        server.process.wait(timeout=30)
    finally:
        server.stream.close()


def card_path(root: Path, bundle: int) -> str:
    database = (root / PUBLIC_DATABASE).resolve()
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        row = connection.execute(
            "SELECT case_id, item_id FROM assessment_items WHERE source_round IN (?, ?) "
            "ORDER BY item_id LIMIT 1", (round_key(bundle, 3), round_key(bundle, 1)),
        ).fetchone()
    if row is None:
        raise ValueError(f"no public card for nw{bundle}")
    return f"/cases/{quote(str(row[0]), safe='')}?item={quote(str(row[1]), safe='')}"


def mobile_steps(cfg, bundle: int, logs: Path) -> list[Step]:
    paths = (*MOBILE_PATHS, card_path(cfg.root, bundle))
    return [command(cfg, f"mobile-{index}", "node",
                    "apps/math-assessment-web/scripts/check-mobile-overflow.mjs", "--width", "390",
                    "--screenshot", str(logs / f"390-{index}.png"), WEB_URL + path, kind="mobile")
            for index, path in enumerate(paths, 1)]


def server_steps(cfg) -> tuple[Step, Step]:
    env = {"MATH_ASSESSMENT_DETAIL_DB": str((cfg.root / PUBLIC_DATABASE).resolve()),
           "API_ORIGIN": API_URL}
    api = command(cfg, "api-server", str(cfg.root / ".venv/Scripts/python.exe"), "-m", "uvicorn",
                  "app.main:app", "--app-dir", "services/math-assessment-api",
                  "--host", "127.0.0.1", "--port", "8012", env=env)
    web = command(cfg, "web-server", "npx", "next", "start", "-p", "3102", env=env,
                  cwd=cfg.root / "apps/math-assessment-web")
    return api, web


def restore_generated(runner, logs: Path, name: str) -> None:
    step = command(runner.cfg, name, "git", "checkout", "--",
                   "apps/math-assessment-web/next-env.d.ts")
    try:
        code, _ = runner.execute(step, logs / f"{name}.out")
        runner.checkpoint.event("restore", step=name, exit_code=code)
    except Exception as error:
        runner.checkpoint.event("restore", step=name, reason=str(error))


def launch(runner, bundle: int, step: Step, logs: Path, servers: list, marker: str) -> None:
    with runner.checkpoint.edit():
        record = runner.scope(bundle, "gate")["steps"].setdefault(step.name, {})
        record.update(status="running", started_at=now())
    started = time.monotonic()
    try:
        server = runner.start_server(step, logs / f"{step.name}.out")
        servers.append(server)
        runner.checkpoint.event("server-start", bundle=bundle, step=step.name,
                                pid=server.process.pid)
        runner.wait_ready(server, marker)
        with runner.checkpoint.edit():
            record.update(status="done", exit_code=0)
    except BaseException as error:
        with runner.checkpoint.edit():
            record.update(status="failed", exit_code=None, reason=str(error))
        raise
    finally:
        with runner.checkpoint.edit():
            record.update(ended_at=now(),
                          seconds=round(record.get("seconds", 0) + time.monotonic() - started, 3))


def live_gates(runner, bundle: int, logs: Path) -> None:
    cfg = runner.cfg
    servers = []
    api, web = server_steps(cfg)
    try:
        for step, marker in ((api, "Application startup complete"), (web, "Ready")):
            if step.name == "web-server":
                runner.step(bundle, "gate", command(cfg, "web-build", "npm", "run", "build",
                                                   env={"API_ORIGIN": API_URL}))
            launch(runner, bundle, step, logs, servers, marker)
        runner.steps(bundle, "gate", mobile_steps(cfg, bundle, logs))
        runner.step(bundle, "gate", command(
            cfg, "detail", "node", "apps/math-assessment-web/scripts/check-card-detail-text.mjs",
            "--web-url", WEB_URL, "--api-url", API_URL, "--width", "390", "--concurrency", "4",
            "--output", str(logs / "card-detail-text.json")))
    finally:
        errors = []
        for server in reversed(servers):
            try:
                runner.stop_server(server)
            except BaseException as error:
                errors.append(error)
            finally:
                runner.checkpoint.event("server-stop", bundle=bundle, pid=server.process.pid)
        if errors:
            raise errors[0]


def run_gates(runner, bundle: int) -> None:
    with runner.checkpoint.edit():
        scope = runner.scope(bundle, "gate")
    if scope.get("status") == "done":
        return
    logs = runner.cfg.root / OUTPUT / f"logs/nw{bundle}/gate"
    try:
        runner.steps(bundle, "gate", gate_steps(runner.cfg))
        try:
            live_gates(runner, bundle, logs)
        finally:
            restore_generated(runner, logs, "restore-before-verify")
        try:
            runner.step(bundle, "gate", command(runner.cfg, "verify", "npm", "run", "verify"))
        finally:
            restore_generated(runner, logs, "restore-after-verify")
        with runner.checkpoint.edit():
            scope["status"] = "done"
    except BaseException:
        with runner.checkpoint.edit():
            scope["status"] = "failed"
        raise
    finally:
        runner.checkpoint.save()
        with runner.checkpoint.lock:
            audit = runner.scope(bundle, "publish")["steps"].get("audit-public", {})
        atomic_json(runner.cfg.root / OUTPUT / f"gates/nw{bundle}.json",
                    {"time": now(), "status": scope.get("status", "failed"),
                     "audit-public": audit, "steps": scope["steps"],
                     "blocking_public_items": 0 if audit.get("exit_code") == 0 else None,
                     "detail_seconds": scope["steps"].get("detail", {}).get("seconds", 0)})
