"""Parse nationwide commands and detach the runner from its calling tool.

Run .venv/Scripts/python.exe scripts/run_nationwide.py launch --bundles 2-6.
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide_launch.py.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from scripts.nationwide_state import runner_lock
from scripts.nationwide_steps import (
    DEFAULT_ISOLATED_CWD,
    DEFAULT_MODEL,
    DEFAULT_WAIT_SECONDS,
    DEFAULT_WORKERS,
    MAX_WORKERS,
    OUTPUT,
    Config,
    child_env,
    round_steps,
)

DEFAULT_LAUNCH_RESTARTS = 3
DEFAULT_MAX_STEP_FAILURES = 2
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
LOG_TIME_FORMAT = "%Y%m%d-%H%M%S"


def parse_bundles(value: str) -> tuple[int, ...]:
    try:
        numbers = set()
        for part in value.split(","):
            bounds = [int(item) for item in part.split("-")]
            if any(number not in range(1, 7) for number in bounds):
                raise ValueError
            if len(bounds) == 1:
                numbers.add(bounds[0])
            elif len(bounds) == 2 and bounds[0] <= bounds[1]:
                numbers.update(range(bounds[0], bounds[1] + 1))
            else:
                raise ValueError
        if not numbers or not numbers <= set(range(1, 7)):
            raise ValueError
        return tuple(sorted(numbers))
    except ValueError as error:
        raise argparse.ArgumentTypeError("bundles must be 1..6, e.g. 2-6 or 2,3") from error


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, restarts in (("run", 0), ("launch", DEFAULT_LAUNCH_RESTARTS)):
        start = commands.add_parser(name, help=f"{name} bundles with resumable checkpoints")
        start.add_argument("--bundles", type=parse_bundles, required=True)
        start.add_argument("--model", default=DEFAULT_MODEL)
        start.add_argument("--workers", type=int, choices=range(1, MAX_WORKERS + 1),
                           default=DEFAULT_WORKERS)
        start.add_argument("--sequential-rounds", action="store_true",
                           help="run round 3 then round 1 instead of two threads")
        start.add_argument("--isolated-cwd", type=Path, default=DEFAULT_ISOLATED_CWD)
        start.add_argument("--wait-seconds", type=float, default=DEFAULT_WAIT_SECONDS)
        start.add_argument("--restart-on-failure", type=int, default=restarts)
        start.add_argument("--max-step-failures", type=int, default=DEFAULT_MAX_STEP_FAILURES,
                           help="stop after this many consecutive failures of the same step")
    status = commands.add_parser("status", help="read checkpoints and check the runner PID")
    status.add_argument("--json", action="store_true")
    reset = commands.add_parser("reset", help="clear round stages and later publication/gates")
    reset.add_argument("--bundles", type=parse_bundles, required=True)
    reset.add_argument("--from", dest="from_step", required=True,
                       choices=[step.name for step in round_steps(Config(Path(".")), 1, 3)])
    return parser


def launch(cfg: Config, restart_on_failure: int = DEFAULT_LAUNCH_RESTARTS, *,
           max_step_failures: int = DEFAULT_MAX_STEP_FAILURES, popen=None, platform=None) -> int:
    if max_step_failures < 1:
        raise ValueError("max-step-failures must be positive")
    try:
        with runner_lock(cfg.root):
            pass
    except sqlite3.OperationalError as error:
        if "locked" not in str(error).casefold():
            raise
        print("nationwide runner is already locked", file=sys.stderr)
        return 5
    project = cfg.root.resolve()
    stamp = datetime.now().strftime(LOG_TIME_FORMAT)
    log_path = project / OUTPUT / f"runner-{stamp}.log"
    argv = [sys.executable, "scripts/run_nationwide.py", "run",
            "--bundles", ",".join(map(str, cfg.bundles)), "--model", cfg.model,
            "--workers", str(cfg.workers), "--isolated-cwd", str(cfg.isolated_cwd),
            "--wait-seconds", str(cfg.wait_seconds),
            "--max-step-failures", str(max_step_failures),
            *(("--sequential-rounds",) if cfg.sequential_rounds else ()),
            "--restart-on-failure", str(restart_on_failure)]
    options = ({"creationflags": DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP}
               if (platform or os.name) == "nt" else {"start_new_session": True})
    with log_path.open("a", encoding="utf-8") as stream:
        process = (popen or subprocess.Popen)(
            argv, cwd=project, env=child_env(cfg.model), stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, close_fds=True, **options)
    print(f"PID: {process.pid}")
    print(f"로그: {log_path}")
    return 0
