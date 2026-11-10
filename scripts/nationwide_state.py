"""Persist nationwide checkpoints/events and format status without running children.

Run .venv/Scripts/python.exe scripts/run_nationwide.py status [--json].
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide.py.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from scripts.nationwide_steps import OUTPUT

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
    def __init__(self, root: Path):
        self.root = root
        self.state = load_state(root)

    def save(self) -> None:
        update_totals(self.state)
        self.state["updated_at"] = now()
        atomic_json(self.root / OUTPUT / "state.json", self.state)

    def event(self, event: str, **details) -> None:
        path = self.root / OUTPUT / "events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"time": now(), "event": event, **details},
                                    ensure_ascii=False) + "\n")
            stream.flush()

    def stop(self, status: str, reason: str, code: int) -> None:
        self.state.update(status=status, last_stop={"reason": reason, "time": now(), "code": code})
        self.save()
        self.event("stop", status=status, reason=reason, exit_code=code)


def status_text(state: dict) -> str:
    if not state.get("bundles"):
        return "기록 없음"
    lines = [f"상태 {state['status']}",
             "묶음 | 회차/구분 | 단계 | 상태 | 초 | called | valid | total | 무효 | 재시도 | 대기"]
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
                     f"학교 수 {bundle.get('school_count', 0)} | "
                     f"학교·회차당 초 {bundle.get('seconds_per_school_round')}")
    stop = state.get("last_stop")
    if stop:
        lines.append(f"마지막 멈춤 {stop['time']} | {stop['reason']}")
    return "\n".join(lines)
