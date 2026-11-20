"""Run nationwide bundles with parallel rounds, resumable checkpoints and local gates.

Run .venv/Scripts/python.exe scripts/run_nationwide.py run --bundles 2-6.
Launch .venv/Scripts/python.exe scripts/run_nationwide.py launch --bundles 2-6.
Inspect .venv/Scripts/python.exe scripts/run_nationwide.py status [--json].
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide.py.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import io
import json
import sqlite3
import subprocess
import sys
import threading
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
from scripts.nationwide_launch import (  # noqa: E402, F401
    DEFAULT_MAX_STEP_FAILURES,
    build_parser,
    launch,
    parse_bundles,
)
from scripts.nationwide_parallel import StopRun, run_bundle, run_step  # noqa: E402
from scripts.nationwide_state import (  # noqa: E402
    REPEATED_FAILURE_CODE,
    Checkpoint,
    load_state,
    now,
    reset,
    reset_publication,
    runner_lock,
    status_text,
)
from scripts.nationwide_steps import (  # noqa: E402
    CODEX_PATTERN,
    OUTPUT,
    ROUND_COLUMNS,
    ROUND_ORDER,
    Config,
    Step,
    gate_steps,
    publish_steps,
    roster_path,
    round_key,
    round_steps,
)

MIN_VALID_RATE = 0.8
MAX_LOW_CYCLES = 3
RESTRICTION_MESSAGE = "paused after Schoolinfo access restriction"
RESTART_WAIT_SECONDS = 300


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


def ai_metrics(text: str, *, exit_code: int = 0) -> dict:
    value = last_json(text)
    if exit_code == 3 and value.get("all_failed") is not True:
        raise ValueError("AI exit 3 requires all_failed: true")
    total = value["total"] if "total" in value else len(value["results"])
    counts = {"called": value["called"], "valid": value["valid"], "total": total}
    if any(type(count) is not int or count < 0 for count in counts.values()):
        raise ValueError("AI counts must be nonnegative integers")
    if counts["valid"] > total:
        raise ValueError("AI valid count exceeds total")
    skipped = value.get("skipped", total - counts["called"])
    if "skipped" in value and (type(skipped) is not int or skipped < 0):
        raise ValueError("AI skipped count must be a nonnegative integer")
    counts["fresh_valid"] = 0 if exit_code == 3 else max(0, counts["valid"] - skipped)
    return counts


def codex_available() -> bool:
    return bool(glob.glob(CODEX_PATTERN))


class Runner:
    def __init__(self, cfg, execute_fn, sleep, start, stop, ready, find_codex, *,
                 ai_lock=None, collect_lock=None, checkpoint_lock=None):
        self.cfg, self.execute, self.sleep = cfg, execute_fn, sleep
        self.start_server, self.stop_server, self.wait_ready = start, stop, ready
        self.find_codex = find_codex
        self.ai_lock = ai_lock if ai_lock is not None else threading.Lock()
        self.collect_lock = collect_lock if collect_lock is not None else threading.Lock()
        self.checkpoint_lock = checkpoint_lock if checkpoint_lock is not None else threading.Lock()
        self.stop_event, self.failures = threading.Event(), []
        self.checkpoint = Checkpoint(cfg.root, self.checkpoint_lock)

    def scope(self, bundle: int, key: str) -> dict:
        """Get or create a scope while the caller holds the checkpoint lock."""
        entry = self.checkpoint.state["bundles"][str(bundle)]
        if key in ("publish", "gate"):
            return entry.setdefault(key, {"key": f"{key}:nw{bundle}", "steps": {},
                                          "status": "pending"})
        return entry["rounds"].setdefault(key, {"steps": {}, "status": "pending"})

    def plan(self) -> None:
        with self.checkpoint.edit():
            for bundle in self.cfg.bundles:
                self.checkpoint.state["bundles"].setdefault(str(bundle), {"rounds": {}})
                phases = [(round_key(bundle, number), round_steps(self.cfg, bundle, number))
                          for number in ROUND_ORDER]
                phases.extend([("publish", publish_steps(self.cfg, ())),
                               ("gate", gate_steps(self.cfg))])
                for key, steps in phases:
                    scope = self.scope(bundle, key)
                    for step in steps:
                        record = scope["steps"].setdefault(step.name, {"status": "pending"})
                        record.setdefault("failures", 0)
                gate = self.scope(bundle, "gate")["steps"]
                for name in ("api-server", "web-build", "web-server", "mobile-1", "mobile-2",
                             "mobile-3", "mobile-4", "detail", "verify"):
                    gate.setdefault(name, {"status": "pending", "failures": 0})

    def prepare_bundle(self, bundle: int) -> None:
        school_ids = set()
        for number in ROUND_ORDER:
            path = roster_path(bundle, number)
            if not (self.cfg.root / path).is_file():
                raise StopRun(1, "failed", f"missing roster: {path}")
            raw = (self.cfg.root / path).read_bytes()
            reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
            if tuple(reader.fieldnames or ()) != ROUND_COLUMNS:
                raise ValueError(f"invalid roster columns: {path}")
            schools = list(reader)
            school_ids.update(row["school_id"] for row in schools)
            fingerprint = hashlib.sha256(raw).hexdigest()
            with self.checkpoint.edit():
                scope = self.scope(bundle, round_key(bundle, number))
                changed = scope.get("roster_sha256", fingerprint) != fingerprint
                if changed:
                    scope.update(steps={}, status="pending")
                    for other_number, other in self.checkpoint.state["bundles"].items():
                        if int(other_number) >= bundle:
                            other.pop("publish", None)
                            other.pop("gate", None)
                scope.update(roster=path, roster_sha256=fingerprint, school_count=len(schools))
            if changed:
                self.checkpoint.event("invalidate", bundle=bundle, scope=round_key(bundle, number),
                                      reason="roster changed")
        with self.checkpoint.edit():
            self.checkpoint.state["bundles"][str(bundle)]["school_count"] = len(school_ids)

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
        with self.checkpoint.edit():
            record.setdefault("started_at", now())
            record.update(status="running", attempt_started_at=now(),
                          attempts=record.get("attempts", 0) + 1, exit_code=None)
            record.pop("reason", None)
            if step.kind == "ai":
                record["retries"] = record["attempts"] - 1
        if step.kind == "ai" and record["retries"]:
            self.checkpoint.event("retry", bundle=bundle, scope=key, step=step.name,
                                  attempt=record["attempts"])
        self.checkpoint.event("start", bundle=bundle, scope=key, step=step.name,
                              attempt=record["attempts"])
        try:
            path = self.cfg.root / OUTPUT / f"logs/nw{bundle}/{key}/{step.name}.out"
            code, text = self.execute(step, path)
            with self.checkpoint.edit():
                record["exit_code"] = code
                if step.kind == "collect" and RESTRICTION_MESSAGE in text:
                    raise StopRun(4, "schoolinfo_restricted", RESTRICTION_MESSAGE)
                if code not in step.ok_codes:
                    raise StopRun(1, "failed", f"{key}/{step.name} exited {code}")
                return self.metrics(step, text, record)
        finally:
            with self.checkpoint.edit():
                record["ended_at"] = now()
                record["seconds"] = round(record.get("seconds", 0) + time.monotonic() - started, 3)
            self.checkpoint.event("end", bundle=bundle, scope=key, step=step.name,
                                  exit_code=record.get("exit_code"), seconds=record["seconds"])

    def metrics(self, step: Step, text: str, record: dict) -> dict | None:
        if step.kind == "ai":
            counts = ai_metrics(text, exit_code=record["exit_code"])
            record.update(valid=counts["valid"], total=counts["total"],
                          called=record.get("called", 0) + counts["called"],
                          fresh_valid=record.get("fresh_valid", 0) + counts["fresh_valid"])
            return counts
        if step.kind in ("renderer", "mobile"):
            keys = RENDERER_METRICS if step.kind == "renderer" else ("overflow_px",)
            values = last_json(text)
            record["metrics"] = {key: values.get(key) for key in keys}
            if any(type(values.get(key)) not in (int, float) or values[key] != 0 for key in keys):
                raise ValueError(f"{step.name} requires numeric zero metrics: {record['metrics']}")
        return None

    def stop_if_requested(self, key: str, step: Step) -> None:
        # 공유 중단 원인이 생기면 재시도·대기 뒤 새 호출을 시작하지 않는다.
        if self.stop_event.is_set():
            raise StopRun(1, "stopped", f"{key}/{step.name}: other round stopped")

    def ai_step(self, bundle: int, key: str, step: Step, record: dict) -> None:
        while True:
            self.stop_if_requested(key, step)
            counts = self.attempt(bundle, key, step, record)
            called, fresh_valid = counts["called"], counts["fresh_valid"]
            if counts["valid"] < counts["total"]:
                self.stop_if_requested(key, step)
                counts = self.attempt(bundle, key, step, record)
                called += counts["called"]
                fresh_valid += counts["fresh_valid"]
            rate = fresh_valid / called if called else 1
            # 새 호출 유효율 80% 미만이면 재시도로 다 채워졌어도 쉬고 잇는다(N1 재검수).
            low_rate = rate < MIN_VALID_RATE
            with self.checkpoint.edit():
                record["last_fresh_rate"] = rate
                record["low_streak"] = record.get("low_streak", 0) + 1 if low_rate else 0
            if not low_rate:
                return
            if record["low_streak"] >= MAX_LOW_CYCLES:
                raise StopRun(3, "usage_limit_stop", f"{key}/{step.name} valid rate {rate:.3f}")
            with self.checkpoint.edit():
                record.update(status="waiting", waits=record.get("waits", 0) + 1)
            self.checkpoint.event("wait", bundle=bundle, scope=key, step=step.name,
                                  seconds=self.cfg.wait_seconds, valid_rate=rate)
            wait_started = time.monotonic()
            try:
                self.sleep(self.cfg.wait_seconds)
            finally:
                with self.checkpoint.edit():
                    record["wait_seconds"] = round(record.get("wait_seconds", 0)
                                                   + time.monotonic() - wait_started, 3)

    def step(self, bundle: int, key: str, step: Step) -> bool:
        return run_step(self, bundle, key, step)

    def steps(self, bundle: int, key: str, steps: list[Step]) -> bool:
        with self.checkpoint.edit():
            scope = self.scope(bundle, key)
            for step in steps:
                scope["steps"].setdefault(step.name, {"status": "pending"})
        for step in steps:
            if not self.step(bundle, key, step):
                return False
        return True

    def bundle(self, bundle: int) -> None:
        run_bundle(self, bundle, run_gates)


def run_attempt(runner: Runner) -> int:
    checkpoint = runner.checkpoint
    try:
        with checkpoint.edit():
            checkpoint.state["status"] = "running"
            checkpoint.state.pop("last_stop", None)
        runner.plan()
        for bundle in runner.cfg.bundles:
            runner.bundle(bundle)
        with checkpoint.edit():
            checkpoint.state["status"] = "done"
        return 0
    except StopRun as error:
        checkpoint.stop(error.status, str(error), error.code, **error.details)
        return error.code
    except (Exception, KeyboardInterrupt) as error:
        status = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        checkpoint.stop(status, str(error), 1)
        return 1


def run(cfg: Config, *, execute=execute, sleep=time.sleep, start_server=start_server,
        stop_server=stop_server, wait_ready=wait_ready, find_codex=codex_available,
        restart_on_failure=0, restart_wait_seconds=None,
        max_step_failures=DEFAULT_MAX_STEP_FAILURES, argv=None,
        ai_lock=None, collect_lock=None, checkpoint_lock=None) -> int:
    if max_step_failures < 1:
        raise ValueError("max-step-failures must be positive")
    wait = RESTART_WAIT_SECONDS if restart_wait_seconds is None else restart_wait_seconds
    try:
        with runner_lock(cfg.root):
            runner = Runner(cfg, execute, sleep, start_server, stop_server, wait_ready, find_codex,
                            ai_lock=ai_lock, collect_lock=collect_lock,
                            checkpoint_lock=checkpoint_lock)
            checkpoint = runner.checkpoint
            checkpoint.start_runner(sys.argv if argv is None else argv)
            code = 1
            try:
                for attempt in range(restart_on_failure + 1):
                    code = run_attempt(runner)
                    failures = ({"status": error.status, **error.details}
                                for error in runner.failures if isinstance(error, StopRun)
                                and error.code == 1)
                    if code == 1 and checkpoint.stop_repeated_failure(max_step_failures, failures):
                        code = REPEATED_FAILURE_CODE
                    if code != 1 or attempt == restart_on_failure:
                        return code
                    with checkpoint.edit():
                        checkpoint.state["status"] = "restart_wait"
                    checkpoint.event("restart", attempt=attempt + 1,
                                     reason=checkpoint.state["last_stop"]["reason"], seconds=wait)
                    sleep(wait)
            except (Exception, KeyboardInterrupt) as error:
                status = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                code = 1
                checkpoint.stop(status, str(error), code)
                return code
            finally:
                checkpoint.end_runner(code)
    except sqlite3.OperationalError as error:
        if "locked" not in str(error).casefold():
            raise
        print("nationwide runner is already locked", file=sys.stderr)
        return 5


def main(argv=None, *, root=None, popen=None, pid_alive=None) -> int:
    parser = build_parser(__doc__)
    args = parser.parse_args(argv)
    project = Path(root or Path(__file__).resolve().parents[1]).resolve()
    if args.command == "status":
        state = load_state(project)
        print(json.dumps(state, ensure_ascii=False, indent=2) if args.json
              else status_text(state, pid_alive=pid_alive))
        return 0
    if args.command == "reset":
        if args.publish_from:
            return reset_publication(project, args.bundles, args.publish_from)
        return reset(project, args.bundles, args.from_step)
    if (args.workers < 1 or args.max_step_failures < 1 or args.wait_seconds < 0
            or args.restart_on_failure < 0):
        parser.error("workers and max-step-failures must be positive; "
                     "wait-seconds and restart-on-failure nonnegative")
    isolated = args.isolated_cwd
    if not isolated.is_absolute():
        isolated = project / isolated
    cfg = Config(project, args.bundles, args.model, args.workers, isolated, args.wait_seconds,
                 args.sequential_rounds, args.publish_last)
    if args.command == "launch":
        return launch(cfg, args.restart_on_failure, max_step_failures=args.max_step_failures,
                      popen=popen)
    return run(cfg, restart_on_failure=args.restart_on_failure,
               max_step_failures=args.max_step_failures,
               argv=sys.argv if argv is None else ["scripts/run_nationwide.py", *argv])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔·Git Bash에서 상태 표 한글이 깨지지 않게
    raise SystemExit(main())
