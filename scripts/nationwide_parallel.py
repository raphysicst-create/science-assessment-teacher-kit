"""Schedule two nationwide rounds with shared resource locks and cooperative stops.

Run scripts/run_nationwide.py run --bundles 1 [--sequential-rounds].
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_run_nationwide_parallel.py.
"""

from __future__ import annotations

import threading
import time
from contextlib import nullcontext

from scripts.nationwide_steps import (
    ROUND_ORDER,
    publication_rounds,
    publish_steps,
    round_key,
    round_steps,
)


class StopRun(Exception):
    def __init__(self, code: int, status: str, reason: str, *, stop_others=None):
        super().__init__(reason)
        self.code, self.status = code, status
        self.stop_others = (code != 1 or status != "failed") if stop_others is None else stop_others
        self.details = {}


def fail(runner, error: BaseException) -> None:
    with runner.checkpoint_lock:
        if not any(previous is error for previous in runner.failures):
            runner.failures.append(error)
        if not isinstance(error, StopRun) or error.stop_others:
            runner.stop_event.set()


def run_step(runner, bundle: int, key: str, step) -> bool:
    if runner.stop_event.is_set():
        return False
    with runner.checkpoint_lock:
        scope = runner.scope(bundle, key)
        record = scope["steps"].setdefault(step.name, {"status": "pending"})
        record.setdefault("failures", 0)
        if record["status"] == "done":
            return True
    resource = {"ai": runner.ai_lock, "collect": runner.collect_lock}.get(step.kind)
    with resource if resource is not None else nullcontext():
        if runner.stop_event.is_set():
            return False
        try:
            if step.kind == "ai":
                runner.ai_step(bundle, key, step, record)
            else:
                runner.attempt(bundle, key, step, record)
            with runner.checkpoint.edit():
                record.update(status="done", failures=0)
            return True
        except BaseException as error:
            if isinstance(error, Exception) and not isinstance(error, StopRun):
                # Unexpected Python errors keep their shared stop while gaining step context.
                error = StopRun(1, "failed", str(error), stop_others=True)
            fail(runner, error)
            with runner.checkpoint.edit():
                record.update(status="failed", reason=str(error))
                scope["status"] = "failed"
                if isinstance(error, StopRun):
                    if error.code == 1 and error.status == "failed":
                        record["failures"] += 1
                    error.details.update(scope=scope.get("key", key), step=step.name,
                                         failures=record["failures"])
            raise error


def run_round(runner, bundle: int, number: int) -> None:
    key = round_key(bundle, number)
    try:
        if runner.steps(bundle, key, round_steps(runner.cfg, bundle, number)):
            with runner.checkpoint.edit():
                runner.scope(bundle, key)["status"] = "done"
    except BaseException as error:
        fail(runner, error)
    finally:
        try:
            runner.checkpoint.save()
        except BaseException as error:
            fail(runner, error)


def run_rounds(runner, bundle: int) -> None:
    runner.stop_event.clear()
    runner.failures.clear()
    if runner.cfg.sequential_rounds:
        for number in ROUND_ORDER:
            run_round(runner, bundle, number)
            if runner.failures or runner.stop_event.is_set():
                break
    else:
        threads = [threading.Thread(target=run_round, args=(runner, bundle, number),
                                    name=round_key(bundle, number)) for number in ROUND_ORDER]
        started = []
        try:
            for thread in threads:
                thread.start()
                started.append(thread)
            for thread in started:
                thread.join()
        except BaseException as error:
            fail(runner, error)
        finally:
            for thread in started:
                thread.join()
    if runner.failures:
        stops = [error for error in runner.failures if isinstance(error, StopRun)]
        # N2b review: a shared stop (limit 3, restriction 4, ...) outranks an earlier step failure
        # so the restart loop never retries through a usage limit or access restriction.
        shared = [error for error in stops if error.code != 1]
        raise (shared or stops or runner.failures)[0]


def run_bundle(runner, bundle: int, run_gates) -> None:
    started = time.monotonic()
    try:
        runner.prepare_bundle(bundle)
        run_rounds(runner, bundle)
        with runner.checkpoint.edit():
            publish = runner.scope(bundle, "publish")
            if "rounds" not in publish:
                publish["rounds"] = publication_rounds(runner.checkpoint.state)
        runner.steps(bundle, "publish", publish_steps(runner.cfg, tuple(publish["rounds"])))
        with runner.checkpoint.edit():
            publish["status"] = "done"
        try:
            run_gates(runner, bundle)
        except (Exception, KeyboardInterrupt) as error:
            raise StopRun(2, "gate_failed", str(error)) from error
        with runner.checkpoint.edit():
            runner.checkpoint.state["bundles"][str(bundle)]["status"] = "done"
    finally:
        with runner.checkpoint.edit():
            entry = runner.checkpoint.state["bundles"][str(bundle)]
            entry["wall_seconds"] = round(entry.get("wall_seconds", 0)
                                          + time.monotonic() - started, 3)
