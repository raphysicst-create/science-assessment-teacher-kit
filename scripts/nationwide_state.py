"""Persist nationwide checkpoints/events and format status without running children.

Run .venv/Scripts/python.exe scripts/run_nationwide.py status [--json].
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide.py.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from scripts.nationwide_steps import OUTPUT, ROUND_ORDER, Config, round_key, round_steps

STATE_VERSION = 1
REPLACE_ATTEMPTS = 10
REPLACE_RETRY_SECONDS = 0.05
STATUS_LABELS = {"done": "완료", "failed": "실패", "pending": "대기",
                 "running": "진행", "waiting": "대기"}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        for attempt in range(REPLACE_ATTEMPTS):
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if attempt == REPLACE_ATTEMPTS - 1:
                    raise
                time.sleep(REPLACE_RETRY_SECONDS)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_state(root: Path) -> dict:
    path = root / OUTPUT / "state.json"
    if not path.is_file():
        return {"version": STATE_VERSION, "status": "pending", "bundles": {}}
    return json.loads(path.read_text(encoding="utf-8"))


@contextmanager
def runner_lock(root: Path):
    path = root / OUTPUT / "runner.lock.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=0)
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
    finally:
        connection.rollback()
        connection.close()


def scopes(bundle: dict):
    yield from bundle["rounds"].items()
    for name in ("publish", "gate"):
        if name in bundle:
            yield bundle[name]["key"], bundle[name]


def update_totals(state: dict) -> None:
    for bundle in state["bundles"].values():
        records = [record for _, scope in scopes(bundle) for record in scope["steps"].values()]
        bundle["stage_seconds"] = round(sum(record.get("seconds", 0) for record in records), 3)
        bundle["wait_seconds"] = round(sum(record.get("wait_seconds", 0) for record in records), 3)
        bundle["seconds"] = round(bundle["stage_seconds"] + bundle["wait_seconds"], 3)
        bundle["called"] = sum(record.get("called", 0) for record in records)
        bundle["school_round_count"] = sum(r.get("school_count", 0)
                                             for r in bundle["rounds"].values())
        count = bundle["school_round_count"]
        bundle["seconds_per_school_round"] = round(bundle["seconds"] / count, 3) if count else None


class Checkpoint:
    def __init__(self, root: Path, lock=None):
        self.root = root
        self.lock = lock if lock is not None else threading.Lock()
        self.state = load_state(root)

    @contextmanager
    def edit(self):
        with self.lock:
            try:
                yield self.state
            finally:
                self._save()

    def save(self) -> None:
        with self.lock:
            self._save()

    def _save(self) -> None:
        update_totals(self.state)
        self.state["updated_at"] = now()
        atomic_json(self.root / OUTPUT / "state.json", self.state)

    def event(self, event: str, **details) -> None:
        with self.lock:
            self._event(event, **details)

    def _event(self, event: str, **details) -> None:
        timestamp = now()
        path = self.root / OUTPUT / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": timestamp, "event": event, **details},
                                    ensure_ascii=False) + "\n")
            stream.flush()
        if "runner" in self.state:
            self.state["runner"]["heartbeat_at"] = timestamp
            self._save()

    def start_runner(self, argv: list[str]) -> None:
        with self.lock:
            timestamp = now()
            self.state["runner"] = {"pid": os.getpid(), "started_at": timestamp,
                                    "heartbeat_at": timestamp, "argv": list(argv)}
            self.state["status"] = "running"
            self.state.pop("last_stop", None)
            self._event("runner-start", pid=os.getpid())

    def end_runner(self, code: int) -> None:
        with self.lock:
            self.state["runner"].update(ended_at=now(), exit_code=code)
            self._event("runner-end", exit_code=code)

    def stop(self, status: str, reason: str, code: int) -> None:
        with self.lock:
            self.state.update(status=status,
                              last_stop={"reason": reason, "time": now(), "code": code})
            self._save()
            self._event("stop", status=status, reason=reason, exit_code=code)


def reset(root: Path, bundles: tuple[int, ...], from_step: str) -> int:
    names = [step.name for step in round_steps(Config(root), 1, 3)]
    following = names[names.index(from_step):]
    try:
        with runner_lock(root):
            checkpoint = Checkpoint(root)
            with checkpoint.edit() as state:
                for number, bundle in state["bundles"].items():
                    if int(number) in bundles:
                        for term in ROUND_ORDER:
                            scope = bundle["rounds"].get(round_key(int(number), term))
                            if scope is not None:
                                for name in following:
                                    scope["steps"].pop(name, None)
                                scope["status"] = "pending"
                    if int(number) >= min(bundles):
                        bundle.pop("publish", None)
                        bundle.pop("gate", None)
                        bundle["status"] = "pending"
                state["status"] = "pending"
                state.pop("last_stop", None)
            checkpoint.event("reset", bundles=list(bundles), from_step=from_step)
        return 0
    except sqlite3.OperationalError as error:
        if "locked" not in str(error).casefold():
            raise
        print("nationwide runner is already locked", file=sys.stderr)
        return 5


def pid_is_alive(pid: int, *, run_command=None, platform=None, kill=None) -> bool:
    if pid <= 0:
        return False
    if (platform or os.name) == "nt":
        try:
            result = (run_command or subprocess.run)(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"], stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                encoding="utf-8", errors="replace", check=False)
            return result.returncode == 0 and str(pid) in result.stdout.split()
        except OSError:
            return False
    try:
        (kill or os.kill)(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def runner_status(state: dict, pid_alive=None) -> str:
    runner = state.get("runner")
    if not runner:
        return ""
    pid, heartbeat = runner["pid"], runner["heartbeat_at"]
    if runner.get("ended_at"):
        reason = state.get("last_stop", {}).get("reason", state["status"])
        return (f"실행기: 멈춤(종료 코드 {runner['exit_code']}, "
                f"끝난 시각 {runner['ended_at']}, 이유 {reason})")
    if (pid_alive or pid_is_alive)(pid):
        return f"실행기: 실행 중(PID {pid}, 마지막 기록 {heartbeat})"
    return f"실행기: 끊김(PID {pid}, 마지막 기록 {heartbeat}) — 같은 launch 명령으로 이으면 된다"


def status_text(state: dict, *, pid_alive=None) -> str:
    lines = []
    if heading := runner_status(state, pid_alive):
        lines.append(heading)
    if not state.get("bundles"):
        return "\n".join([*lines, "기록 없음"])
    lines.extend([f"상태 {state['status']}",
                  "묶음 | 회차/구분 | 단계 | 상태 | 초 | called | valid | total | "
                  "무효 | 재시도 | 대기"])
    for number in sorted(state["bundles"], key=int):
        bundle = state["bundles"][number]
        for key, scope in scopes(bundle):
            for name, record in scope["steps"].items():
                total, valid = record.get("total", 0), record.get("valid", 0)
                lines.append(f"nw{number} | {key} | {name} | "
                             f"{STATUS_LABELS.get(record['status'], record['status'])} | "
                             f"{record.get('seconds', 0):.3f} | {record.get('called', 0)} | "
                             f"{valid} | {total} | {total - valid} | "
                             f"{record.get('retries', 0)} | {record.get('waits', 0)}")
            if "school_count" in scope:
                lines.append(f"  {key} 학교 수 {scope['school_count']}")
        lines.append(f"nw{number} 합계 | 초 {bundle.get('seconds', 0):.3f} | "
                     f"wall_seconds {bundle.get('wall_seconds', 0):.3f} | "
                     f"학교 수 {bundle.get('school_count', 0)} | "
                     f"학교·회차당 초 {bundle.get('seconds_per_school_round')}")
    stop = state.get("last_stop")
    if stop:
        lines.append(f"마지막 멈춤 {stop['time']} | {stop['reason']}")
    return "\n".join(lines)
