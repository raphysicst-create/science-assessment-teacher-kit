"""Verify round concurrency, cooperative stops and timing with synthetic children.

Run .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
    services/math-assessment-api/tests/test_run_nationwide_parallel.py.
"""

import json
import threading
import time
from dataclasses import replace
from types import SimpleNamespace

import pytest
from scripts import nationwide_parallel as parallel
from scripts import nationwide_state as state_module
from scripts import run_nationwide as runner
from scripts.nationwide_state import load_state
from scripts.nationwide_steps import OUTPUT, Config, Step, round_key, round_steps
from test_run_nationwide import HALF
from test_run_nationwide import no_real_children as no_real_children
from test_run_nationwide import setup as setup


class ObservedLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.contended = threading.Event()

    def __enter__(self):
        if self.lock.locked():
            self.contended.set()
        self.lock.acquire()
        return self

    def __exit__(self, *args):
        self.lock.release()

    def locked(self):
        return self.lock.locked()


def make_runner(cfg, fake, execute):
    return runner.Runner(cfg, execute, fake.waits.append, fake.start, fake.stop,
                         lambda server, marker: None, lambda: True)


def use_rounds(monkeypatch, steps_by_round):
    def planned(cfg, bundle, number):
        return steps_by_round[number]

    monkeypatch.setattr(runner, "round_steps", planned)
    monkeypatch.setattr(parallel, "round_steps", planned)


def test_parallel_rounds_serialize_resources_and_overlap_cpu(setup, monkeypatch):
    cfg, fake = setup
    cfg = replace(cfg, sequential_rounds=False)
    keys = {round_key(1, number) for number in (3, 1)}
    barrier, counter_lock = threading.Barrier(2), threading.Lock()
    active = dict.fromkeys(("ai", "collect", "command"), 0)
    peak, threads = active.copy(), set()
    ai_lock, collect_lock, checkpoint_lock = (threading.Lock() for _ in range(3))
    original_json = state_module.atomic_json

    def atomic_json(path, value):
        assert checkpoint_lock.locked()
        original_json(path, value)

    def execute(step, path):
        if path.parent.name not in keys:
            if step.name == "build0":
                assert all(scope["status"] == "done" for scope in
                           load_state(cfg.root)["bundles"]["1"]["rounds"].values())
            return fake.execute(step, path)
        with counter_lock:
            threads.add(threading.get_ident())
            active[step.kind] += 1
            peak[step.kind] = max(peak[step.kind], active[step.kind])
        try:
            if step.kind in ("ai", "collect"):
                assert (ai_lock if step.kind == "ai" else collect_lock).locked()
            if step.name == "conversion":
                barrier.wait(timeout=10)
            time.sleep(0.01)  # Only the fake child runs briefly to expose overlap.
            return fake.execute(step, path)
        finally:
            with counter_lock:
                active[step.kind] -= 1

    monkeypatch.setattr(state_module, "atomic_json", atomic_json)
    assert fake.run(cfg, execute=execute, ai_lock=ai_lock, collect_lock=collect_lock,
                    checkpoint_lock=checkpoint_lock,
                    find_codex=lambda: ai_lock.locked()) == 0
    assert peak == {"ai": 1, "collect": 1, "command": 2}
    assert len(threads) == 2
    for key in keys:
        assert [name for scope, name, _ in fake.calls if scope == key] == [
            step.name for step in round_steps(cfg, 1, 3)]
    records = [json.loads(line) for line in
               (cfg.root / OUTPUT / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sum(event["event"] == "start" for event in records) > 2


def test_parallel_resume_skips_every_completed_step(setup):
    cfg, fake = setup
    cfg = replace(cfg, sequential_rounds=False)
    fake.responses[(round_key(1, 3), "subjects")] = [RuntimeError("synthetic stop")]
    assert fake.run(cfg) == 1
    rounds = load_state(cfg.root)["bundles"]["1"]["rounds"]
    done = {(key, name) for key, scope in rounds.items() for name, record in
            scope["steps"].items() if record["status"] == "done"}
    assert done
    count = len(fake.calls)
    assert fake.run(cfg) == 0
    resumed = {(key, name) for key, name, _ in fake.calls[count:]}
    assert not done & resumed
    assert (round_key(1, 3), "subjects") in resumed
    assert all(scope["status"] == "done" for scope in
               load_state(cfg.root)["bundles"]["1"]["rounds"].values())


@pytest.mark.parametrize("later_exit", [0, 9])
def test_restriction_finishes_current_step_and_keeps_first_stop_code(
        setup, monkeypatch, later_exit):
    cfg, fake = setup
    cfg = replace(cfg, sequential_rounds=False)
    use_rounds(monkeypatch, {3: [Step("collect", (), kind="collect")],
                            1: [Step("conversion", ()), Step("segments", ())]})
    current_started = threading.Event()

    def execute(step, path):
        if step.name == "collect":
            assert current_started.wait(10)
            fake.calls.append((path.parent.name, step.name, step))
            return 1, runner.RESTRICTION_MESSAGE
        current_started.set()
        assert instance.stop_event.wait(10)
        fake.calls.append((path.parent.name, step.name, step))
        return later_exit, "synthetic CPU result"

    instance = make_runner(cfg, fake, execute)
    assert runner.run_attempt(instance) == 4
    assert "segments" not in fake.names() and "build0" not in fake.names()
    state = load_state(cfg.root)
    rounds = state["bundles"]["1"]["rounds"]
    record = rounds[round_key(1, 1)]["steps"]["conversion"]
    assert record["status"] == ("done" if later_exit == 0 else "failed")
    assert record["ended_at"] and record["exit_code"] == later_exit
    assert rounds[round_key(1, 1)]["steps"]["segments"]["status"] == "pending"
    assert state["last_stop"]["code"] == 4


@pytest.mark.parametrize("kind", ["ai", "collect"])
def test_waiting_for_resource_rechecks_stop_before_start(setup, kind):
    cfg, fake = setup
    instance = make_runner(cfg, fake, fake.execute)
    instance.plan()
    resource = ObservedLock()
    setattr(instance, f"{kind}_lock", resource)
    step = Step("first-run" if kind == "ai" else "collect", (), kind=kind)
    result = []
    with resource:
        worker = threading.Thread(target=lambda: result.append(instance.step(
            1, round_key(1, 3), step)))
        worker.start()
        assert resource.contended.wait(10)
        instance.stop_event.set()
    worker.join(timeout=10)
    assert not worker.is_alive() and result == [False] and not fake.calls


def test_usage_wait_holds_ai_lock_while_other_round_cpu_progresses(setup, monkeypatch):
    cfg, fake = setup
    cfg = replace(cfg, sequential_rounds=False)
    use_rounds(monkeypatch, {3: [Step("first-run", (), kind="ai")],
                            1: [Step("conversion", ()), Step("fields-run", (), kind="ai")]})
    fake.responses[(round_key(1, 3), "first-run")] = [(0, HALF), (0, HALF)]
    sleeping, cpu_done, second_ai = (threading.Event() for _ in range(3))
    ai_lock = ObservedLock()

    def execute(step, path):
        if step.name == "conversion":
            assert sleeping.wait(10)
            cpu_done.set()
        elif step.name == "fields-run":
            second_ai.set()
        return fake.execute(step, path)

    def sleep(seconds):
        fake.waits.append(seconds)
        sleeping.set()
        assert cpu_done.wait(10)
        assert ai_lock.contended.wait(10)
        assert ai_lock.locked() and not second_ai.is_set()
        assert load_state(cfg.root)["bundles"]["1"]["rounds"][
            round_key(1, 3)]["steps"]["first-run"]["status"] == "waiting"

    assert fake.run(cfg, execute=execute, sleep=sleep, ai_lock=ai_lock) == 0
    assert fake.waits == [3600] and second_ai.is_set()


def test_wall_seconds_and_status_show_wall_and_stage_totals(setup, monkeypatch, capsys):
    cfg, fake = setup
    clock = iter((100, 160))
    monkeypatch.setattr(parallel, "time", SimpleNamespace(monotonic=lambda: next(clock)))
    assert fake.run(replace(cfg, sequential_rounds=False)) == 0
    entry = load_state(cfg.root)["bundles"]["1"]
    assert entry["wall_seconds"] == 60
    assert runner.main(["status"], root=cfg.root) == 0
    total = next(line for line in capsys.readouterr().out.splitlines() if "합계" in line)
    assert f"초 {entry['seconds']:.3f}" in total and "wall_seconds 60.000" in total


def test_sequential_rounds_preserve_complete_old_order(setup):
    cfg, fake = setup
    assert Config(cfg.root).sequential_rounds is False
    assert fake.run(cfg) == 0
    keys = [key for key, _, _ in fake.calls if key not in ("publish", "gate")]
    length = len(round_steps(cfg, 1, 3))
    assert keys == [round_key(1, 3)] * length + [round_key(1, 1)] * length
