"""Run nationwide bundles sequentially with resumable checkpoints and local gates.

Run .venv/Scripts/python.exe scripts/run_nationwide.py run --bundles 2-6.
Inspect .venv/Scripts/python.exe scripts/run_nationwide.py status [--json].
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide.py.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.nationwide_gates import (  # noqa: E402
    RENDERER_METRICS,
    native_argv,
    run_gates,
    start_server,
    stop_server,
    wait_ready,
)
from scripts.nationwide_state import (  # noqa: E402
    Checkpoint,
    load_state,
    now,
    runner_lock,
    status_text,
)
from scripts.nationwide_steps import (  # noqa: E402
    CODEX_PATTERN,
    DEFAULT_ISOLATED_CWD,
    DEFAULT_MODEL,
    DEFAULT_WAIT_SECONDS,
    DEFAULT_WORKERS,
    OUTPUT,
    ROUND_COLUMNS,
    ROUND_ORDER,
    Config,
    Step,
    gate_steps,
    publication_rounds,
    publish_steps,
    roster_path,
    round_key,
    round_steps,
)

MIN_VALID_RATE = 0.8
MAX_LOW_CYCLES = 3
RESTRICTION_MESSAGE = "paused after Schoolinfo access restriction"


class StopRun(Exception):
    def __init__(self, code: int, status: str, reason: str):
        super().__init__(reason)
        self.code, self.status = code, status


def execute(step: Step, log_path: Path) -> tuple[int, str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as stream:
        offset = stream.tell()
        result = subprocess.run(native_argv(step.argv), cwd=step.cwd, env=step.env,
                                stdin=subprocess.DEVNULL, stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    with log_path.open("rb") as stream:
        stream.seek(offset)
        output = stream.read().decode("utf-8", errors="replace")
    return result.returncode, output


def last_json(text: str) -> dict:
    decoder, position, result = json.JSONDecoder(), 0, None
    while (position := text.find("{", position)) != -1:
        try:
            value, end = decoder.raw_decode(text, position)
        except ValueError:
            position += 1
            continue
        if isinstance(value, dict):
            result = value
        position = end
    if result is None:
        raise ValueError("child stdout has no JSON object")
    return result


def ai_metrics(text: str) -> dict:
    value = last_json(text)
    total = value["total"] if "total" in value else len(value["results"])
    counts = {"called": value["called"], "valid": value["valid"], "total": total}
    if any(type(count) is not int or count < 0 for count in counts.values()):
        raise ValueError("AI counts must be nonnegative integers")
    if counts["valid"] > total:
        raise ValueError("AI valid count exceeds total")
    return counts


def codex_available() -> bool:
    return bool(glob.glob(CODEX_PATTERN))


class Runner:
    def __init__(self, cfg, execute_fn, sleep, start, stop, ready, find_codex):
        self.cfg, self.execute, self.sleep = cfg, execute_fn, sleep
        self.start_server, self.stop_server, self.wait_ready = start, stop, ready
        self.find_codex = find_codex
        self.checkpoint = Checkpoint(cfg.root)

    def scope(self, bundle: int, key: str) -> dict:
        entry = self.checkpoint.state["bundles"][str(bundle)]
        if key in ("publish", "gate"):
            return entry.setdefault(key, {"key": f"{key}:nw{bundle}", "steps": {},
                                          "status": "pending"})
        return entry["rounds"].setdefault(key, {"steps": {}, "status": "pending"})

    def plan(self) -> None:
        for bundle in self.cfg.bundles:
            self.checkpoint.state["bundles"].setdefault(str(bundle), {"rounds": {}})
            phases = [(round_key(bundle, number), round_steps(self.cfg, bundle, number))
                      for number in ROUND_ORDER]
            phases.extend([("publish", publish_steps(self.cfg, ())),
                           ("gate", gate_steps(self.cfg))])
            for key, steps in phases:
                scope = self.scope(bundle, key)
                for step in steps:
                    scope["steps"].setdefault(step.name, {"status": "pending"})
            gate = self.scope(bundle, "gate")["steps"]
            for name in ("api-server", "web-build", "web-server", "mobile-1", "mobile-2",
                         "mobile-3", "mobile-4", "detail", "verify"):
                gate.setdefault(name, {"status": "pending"})
        self.checkpoint.save()

    def prepare_bundle(self, bundle: int) -> None:
        entry = self.checkpoint.state["bundles"].setdefault(str(bundle), {"rounds": {}})
        school_ids = set()
        for number in ROUND_ORDER:
            path = roster_path(bundle, number)
            scope = self.scope(bundle, round_key(bundle, number))
            if not (self.cfg.root / path).is_file():
                raise StopRun(1, "failed", f"missing roster: {path}")
            raw = (self.cfg.root / path).read_bytes()
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            if tuple(reader.fieldnames or ()) != ROUND_COLUMNS:
                raise ValueError(f"invalid roster columns: {path}")
            schools = list(reader)
            school_ids.update(row["school_id"] for row in schools)
            fingerprint = hashlib.sha256(raw).hexdigest()
            if scope.get("roster_sha256", fingerprint) != fingerprint:
                scope.update(steps={}, status="pending")
                for other_number, other in self.checkpoint.state["bundles"].items():
                    if int(other_number) >= bundle:
                        other.pop("publish", None)
                        other.pop("gate", None)
                self.checkpoint.event("invalidate", bundle=bundle, scope=round_key(bundle, number),
                                      reason="roster changed")
            scope.update(roster=path, roster_sha256=fingerprint, school_count=len(schools))
        entry["school_count"] = len(school_ids)
        self.checkpoint.save()

    def preflight_ai(self) -> None:
        iso = self.cfg.isolated_cwd
        if not iso.is_dir() or next(iso.iterdir(), None) is not None:
            raise StopRun(6, "preflight_failed", f"isolated cwd must exist and be empty: {iso}")
        if not self.find_codex():
            raise StopRun(6, "preflight_failed", f"Codex executable missing: {CODEX_PATTERN}")

    def attempt(self, bundle: int, key: str, step: Step, record: dict) -> dict | None:
        if step.kind == "ai":
            self.preflight_ai()
        started = time.monotonic()
        record.setdefault("started_at", now())
        record.update(status="running", attempt_started_at=now(),
                      attempts=record.get("attempts", 0) + 1, exit_code=None)
        record.pop("reason", None)
        if step.kind == "ai":
            record["retries"] = record["attempts"] - 1
            if record["retries"]:
                self.checkpoint.event("retry", bundle=bundle, scope=key, step=step.name,
                                      attempt=record["attempts"])
        self.checkpoint.save()
        self.checkpoint.event("start", bundle=bundle, scope=key, step=step.name,
                              attempt=record["attempts"])
        try:
            path = self.cfg.root / OUTPUT / f"logs/nw{bundle}/{key}/{step.name}.out"
            code, text = self.execute(step, path)
            record["exit_code"] = code
            if step.kind == "collect" and RESTRICTION_MESSAGE in text:
                raise StopRun(4, "schoolinfo_restricted", RESTRICTION_MESSAGE)
            if code not in step.ok_codes:
                raise StopRun(1, "failed", f"{key}/{step.name} exited {code}")
            return self.metrics(step, text, record)
        finally:
            record["ended_at"] = now()
            record["seconds"] = round(record.get("seconds", 0) + time.monotonic() - started, 3)
            self.checkpoint.save()
            self.checkpoint.event("end", bundle=bundle, scope=key, step=step.name,
                                  exit_code=record.get("exit_code"), seconds=record["seconds"])

    def metrics(self, step: Step, text: str, record: dict) -> dict | None:
        if step.kind == "ai":
            counts = ai_metrics(text)
            record.update(valid=counts["valid"], total=counts["total"],
                          called=record.get("called", 0) + counts["called"])
            return counts
        if step.kind in ("renderer", "mobile"):
            keys = RENDERER_METRICS if step.kind == "renderer" else ("overflow_px",)
            values = last_json(text)
            record["metrics"] = {key: values.get(key) for key in keys}
            if any(type(values.get(key)) not in (int, float) or values[key] != 0 for key in keys):
                raise ValueError(f"{step.name} requires numeric zero metrics: {record['metrics']}")
        return None

    def ai_step(self, bundle: int, key: str, step: Step, record: dict) -> None:
        while True:
            counts = self.attempt(bundle, key, step, record)
            if counts["valid"] < counts["total"]:
                counts = self.attempt(bundle, key, step, record)
            rate = counts["valid"] / counts["total"] if counts["total"] else 1
            record["low_streak"] = record.get("low_streak", 0) + 1 if rate < MIN_VALID_RATE else 0
            if rate >= MIN_VALID_RATE:
                return
            if record["low_streak"] >= MAX_LOW_CYCLES:
                raise StopRun(3, "usage_limit_stop", f"{key}/{step.name} valid rate {rate:.3f}")
            record.update(status="waiting", waits=record.get("waits", 0) + 1)
            self.checkpoint.save()
            self.checkpoint.event("wait", bundle=bundle, scope=key, step=step.name,
                                  seconds=self.cfg.wait_seconds, valid_rate=rate)
            wait_started = time.monotonic()
            try:
                self.sleep(self.cfg.wait_seconds)
            finally:
                record["wait_seconds"] = round(record.get("wait_seconds", 0)
                                               + time.monotonic() - wait_started, 3)
                self.checkpoint.save()

    def step(self, bundle: int, key: str, step: Step) -> None:
        scope = self.scope(bundle, key)
        record = scope["steps"].setdefault(step.name, {"status": "pending"})
        if record["status"] == "done":
            return
        try:
            if step.kind == "ai":
                self.ai_step(bundle, key, step, record)
            else:
                self.attempt(bundle, key, step, record)
            record["status"] = "done"
        except BaseException as error:
            record.update(status="failed", reason=str(error))
            scope["status"] = "failed"
            raise
        finally:
            self.checkpoint.save()

    def steps(self, bundle: int, key: str, steps: list[Step]) -> None:
        scope = self.scope(bundle, key)
        for step in steps:
            scope["steps"].setdefault(step.name, {"status": "pending"})
        self.checkpoint.save()
        for step in steps:
            self.step(bundle, key, step)

    def bundle(self, bundle: int) -> None:
        self.prepare_bundle(bundle)
        for number in ROUND_ORDER:
            key = round_key(bundle, number)
            self.steps(bundle, key, round_steps(self.cfg, bundle, number))
            self.scope(bundle, key)["status"] = "done"
            self.checkpoint.save()
        publish = self.scope(bundle, "publish")
        if "rounds" not in publish:
            publish["rounds"] = publication_rounds(self.checkpoint.state)
        self.steps(bundle, "publish", publish_steps(self.cfg, tuple(publish["rounds"])))
        publish["status"] = "done"
        self.checkpoint.save()
        try:
            run_gates(self, bundle)
        except (Exception, KeyboardInterrupt) as error:
            raise StopRun(2, "gate_failed", str(error)) from error
        self.checkpoint.state["bundles"][str(bundle)]["status"] = "done"
        self.checkpoint.save()


def run(cfg: Config, *, execute=execute, sleep=time.sleep, start_server=start_server,
        stop_server=stop_server, wait_ready=wait_ready, find_codex=codex_available) -> int:
    try:
        with runner_lock(cfg.root):
            runner = Runner(cfg, execute, sleep, start_server, stop_server, wait_ready, find_codex)
            try:
                runner.checkpoint.state["status"] = "running"
                runner.plan()
                for bundle in cfg.bundles:
                    runner.bundle(bundle)
                runner.checkpoint.state["status"] = "done"
                runner.checkpoint.save()
                return 0
            except StopRun as error:
                runner.checkpoint.stop(error.status, str(error), error.code)
                return error.code
            except (Exception, KeyboardInterrupt) as error:
                status = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                runner.checkpoint.stop(status, str(error), 1)
                return 1
    except sqlite3.OperationalError as error:
        if "locked" not in str(error).casefold():
            raise
        print("nationwide runner is already locked", file=sys.stderr)
        return 5


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


def main(argv=None, *, root=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("run", help="run bundles sequentially, resuming completed steps")
    start.add_argument("--bundles", type=parse_bundles, required=True)
    start.add_argument("--model", default=DEFAULT_MODEL)
    start.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    start.add_argument("--isolated-cwd", type=Path, default=DEFAULT_ISOLATED_CWD)
    start.add_argument("--wait-seconds", type=float, default=DEFAULT_WAIT_SECONDS)
    status = commands.add_parser("status", help="read checkpoints only")
    status.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    project = Path(root or Path(__file__).resolve().parents[1]).resolve()
    if args.command == "status":
        state = load_state(project)
        print(json.dumps(state, ensure_ascii=False, indent=2) if args.json else status_text(state))
        return 0
    if args.workers < 1 or args.wait_seconds < 0:
        parser.error("workers must be positive and wait-seconds must be nonnegative")
    isolated = args.isolated_cwd
    if not isolated.is_absolute():
        isolated = project / isolated
    return run(Config(project, args.bundles, args.model, args.workers, isolated, args.wait_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
