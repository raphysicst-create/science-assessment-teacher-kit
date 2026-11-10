"""Exercise nationwide execution with synthetic rosters, DB and injected children.

Run .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .tmp/n1/pt-w2
    services/math-assessment-api/tests/test_run_nationwide.py.
Verify .venv/Scripts/python.exe -m ruff check scripts/*nationwide*.py
       services/math-assessment-api/tests/test_run_nationwide.py.
"""

import csv
import json
import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest
from scripts import run_nationwide as runner
from scripts.nationwide_gates import RENDERER_METRICS, server_steps
from scripts.nationwide_state import load_state, runner_lock
from scripts.nationwide_steps import (
    DEFAULT_ROUNDS,
    OUTPUT,
    PUBLIC_DATABASE,
    ROUND_COLUMNS,
    Config,
    gate_steps,
    publication_rounds,
    publish_steps,
    roster_path,
    round_key,
    round_steps,
)

FULL = {"called": 1, "valid": 2, "total": 2}
HALF = {"called": 2, "valid": 1, "total": 2}


@pytest.fixture(autouse=True)
def no_real_children(monkeypatch):
    def reject(*args, **kwargs):
        pytest.fail("nationwide tests must inject fake child processes")

    monkeypatch.setattr("subprocess.Popen", reject)


class Fake:
    def __init__(self):
        self.calls, self.waits, self.started, self.stopped = [], [], [], []
        self.responses = {}
        self.codex = True

    def execute(self, step, log_path):
        self.calls.append((log_path.parent.name, step.name, step))
        queue = self.responses.get((log_path.parent.name, step.name),
                                   self.responses.get(step.name, []))
        result = queue.pop(0) if queue else self.default_result(step)
        if isinstance(result, BaseException):
            raise result
        code, value = result
        text = value if isinstance(value, str) else json.dumps(value)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(text + "\n")
        return code, text

    @staticmethod
    def default_result(step):
        if step.kind == "ai":
            return 0, FULL
        if step.kind == "renderer":
            return 0, dict.fromkeys(RENDERER_METRICS, 0)
        return 0, {"overflow_px": 0}

    def start(self, step, log_path):
        server = SimpleNamespace(process=SimpleNamespace(pid=100 + len(self.started)))
        self.started.append((step, log_path, server))
        return server

    def stop(self, server):
        self.stopped.append(server.process.pid)

    def run(self, cfg, **extra):
        hooks = {"execute": self.execute, "sleep": self.waits.append,
                 "start_server": self.start, "stop_server": self.stop,
                 "wait_ready": lambda server, marker: None, "find_codex": lambda: self.codex}
        hooks.update(extra)
        return runner.run(cfg, **hooks)

    def names(self):
        return [name for _, name, _ in self.calls]


@pytest.fixture
def setup(tmp_path):
    iso = tmp_path / "isolated"
    iso.mkdir()
    for bundle in (1, 2, 3):
        for number in (3, 1):
            path = tmp_path / roster_path(bundle, number)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=ROUND_COLUMNS)
                writer.writeheader()
                writer.writerow(dict.fromkeys(ROUND_COLUMNS, str(bundle)))
    path = tmp_path / PUBLIC_DATABASE
    path.parent.mkdir(parents=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE assessment_items (case_id TEXT, item_id TEXT, source_round TEXT)")
        db.executemany("INSERT INTO assessment_items VALUES (?, ?, ?)",
                       [(f"case{b}", f"item{b}", round_key(b, 3)) for b in (1, 2, 3)])
    return Config(tmp_path, isolated_cwd=iso), Fake()


def first_record(cfg):
    return load_state(cfg.root)["bundles"]["1"]["rounds"][round_key(1, 3)]["steps"]["first-run"]


def test_step_contracts_and_gold_environment(setup, monkeypatch):
    cfg, _ = setup
    monkeypatch.setenv("MIDDLE_AI_READ_GOLD", "must-remove")
    monkeypatch.setenv("SCIENCE_AXES_GOLD", "must-remove")
    monkeypatch.setenv("lower_gold", "must-remove")
    steps = round_steps(cfg, 2, 3)
    assert round_key(2, 3) == "2026-round-3-nw2"
    assert roster_path(2, 3) == "data/rosters/middle-nw2-round-3.csv"
    assert steps[0].argv[2:] == ("--roster", roster_path(2, 3), "--round", "3",
                                "--run-label", "nw2")
    assert steps[1].argv == (*steps[0].argv, "--retry-failed")
    assert not {"--pause", "--workers"} & set(steps[0].argv)
    assert [step.name for step in steps][-2:] == ["first-methods", "axes"]
    all_steps = (steps + publish_steps(cfg, DEFAULT_ROUNDS)
                 + gate_steps(cfg) + list(server_steps(cfg)))
    for step in all_steps:
        assert not any(key.upper().endswith("_GOLD") for key in step.env)
        assert step.env["MIDDLE_AI_MODEL"] == cfg.model
        assert step.env["PYTHONIOENCODING"] == "utf-8"
        if step.kind == "ai":
            assert step.ok_codes == (0, 3)
    assert "--per-card" in next(s for s in all_steps if s.name == "ax-targets").argv
    with pytest.raises(ValueError):
        round_steps(cfg, 1, 3, key="2026-round-3-gold")


def test_resume_after_interruption_and_done_run_is_noop(setup):
    cfg, fake = setup
    fake.responses["subjects"] = [RuntimeError("synthetic interruption")]
    assert fake.run(cfg) == 1
    before = fake.names()
    assert before == ["collect", "collect-retry", "conversion", "segments", "subjects"]
    assert json.loads((cfg.root / OUTPUT / "state.json").read_text())["last_stop"]["code"] == 1
    assert fake.run(cfg) == 0
    resumed = fake.names()[len(before):]
    assert resumed[:3] == ["subjects", "items", "first-targets"]
    expected = [s.name for s in round_steps(cfg, 1, 3)][4:]
    expected += [s.name for s in round_steps(cfg, 1, 1)]
    expected += [s.name for s in publish_steps(cfg, ())]
    expected += ["renderer", "registry", "package", "web-build", "mobile-1", "mobile-2",
                 "mobile-3", "mobile-4", "detail", "restore-before-verify", "verify",
                 "restore-after-verify"]
    assert resumed == expected
    count = len(fake.calls)
    assert fake.run(cfg) == 0
    assert len(fake.calls) == count
    assert len(fake.started) == 2
    assert fake.stopped == [101, 100]


def test_failed_exit_is_checkpointed_and_retried(setup):
    cfg, fake = setup
    fake.responses["conversion"] = [(23, "failed")]
    assert fake.run(cfg) == 1
    record = load_state(cfg.root)["bundles"]["1"]["rounds"][round_key(1, 3)]["steps"]["conversion"]
    assert record["status"] == "failed" and record["exit_code"] == 23
    assert record["started_at"] and record["ended_at"] and record["seconds"] >= 0
    count = len(fake.calls)
    assert fake.run(cfg) == 0
    assert fake.calls[count][1] == "conversion"


def test_low_rate_waits_and_retries_only_same_command(setup):
    cfg, fake = setup
    fake.responses["first-run"] = [(0, HALF), (0, HALF), (0, FULL)]
    assert fake.run(cfg) == 0
    assert fake.waits == [3600]
    record = first_record(cfg)
    assert {key: record[key] for key in ("called", "valid", "total", "retries", "waits")} == {
        "called": 5, "valid": 2, "total": 2, "retries": 2, "waits": 1}
    calls = [step.argv for key, name, step in fake.calls if key == round_key(1, 3)
             and name == "first-run"]
    assert len(calls) == 3 and calls[0] == calls[1] == calls[2]
    lines = (cfg.root / OUTPUT / "events.jsonl").read_text().splitlines()
    events = [json.loads(line) for line in lines]
    assert {"wait", "retry", "start", "end"} <= {event["event"] for event in events}
    assert all("T" in event["time"] for event in events)


@pytest.mark.parametrize("include_skipped", [True, False])
def test_cached_successes_do_not_hide_fresh_failures(setup, include_skipped):
    cfg, fake = setup
    first = {"called": 20, "valid": 82, "total": 100}
    retry = {"called": 19, "valid": 81, "total": 100}
    full = {"called": 19, "valid": 100, "total": 100}
    if include_skipped:
        for summary, skipped in ((first, 80), (retry, 81), (full, 81)):
            summary["skipped"] = skipped
    fake.responses["first-run"] = [(0, first), (0, retry), (0, full)]

    def sleep(seconds):
        fake.waits.append(seconds)
        record = first_record(cfg)
        assert record["status"] == "waiting" and record["attempts"] == 2
        assert (record["called"], record["fresh_valid"]) == (39, 2)
        assert record["last_fresh_rate"] == pytest.approx(2 / 39)
        events = [json.loads(line) for line in
                  (cfg.root / OUTPUT / "events.jsonl").read_text().splitlines()]
        assert events[-1]["event"] == "wait" and events[-1]["seconds"] == 3600
        assert events[-1]["valid_rate"] == pytest.approx(2 / 39)

    assert fake.run(cfg, sleep=sleep) == 0
    assert fake.waits == [3600]
    record = first_record(cfg)
    assert (record["called"], record["fresh_valid"], record["valid"], record["total"]) == (
        58, 21, 100, 100)
    assert record["last_fresh_rate"] == 1 and record["low_streak"] == 0
    calls = [step.argv for key, name, step in fake.calls
             if key == round_key(1, 3) and name == "first-run"]
    assert len(calls) == 3 and calls[0] == calls[1] == calls[2]


def test_all_failed_exit_waits_then_recovers(setup):
    cfg, fake = setup
    failed = {"called": 20, "valid": 80, "total": 100, "skipped": 80, "all_failed": True}
    full = {"called": 20, "valid": 100, "total": 100, "skipped": 80}
    fake.responses["first-run"] = [(3, failed), (3, failed), (0, full)]

    def sleep(seconds):
        fake.waits.append(seconds)
        record = first_record(cfg)
        assert record["exit_code"] == 3 and record["status"] == "waiting"
        assert record["called"] == 40 and record["fresh_valid"] == 0
        assert record["last_fresh_rate"] == 0

    assert fake.run(cfg, sleep=sleep) == 0
    assert fake.waits == [3600]
    record = first_record(cfg)
    assert record["status"] == "done" and record["exit_code"] == 0
    assert record["called"] == 60 and record["fresh_valid"] == 20


@pytest.mark.parametrize("code, extra", [
    (3, {}), (3, {"all_failed": False}), (3, {"all_failed": 1}),
    (2, {"all_failed": True}), (4, {"all_failed": True}),
])
def test_ai_invalid_exit_is_step_failure(setup, code, extra):
    cfg, fake = setup
    fake.responses["first-run"] = [(code, {**FULL, **extra})]
    assert fake.run(cfg) == 1
    record = first_record(cfg)
    assert record["status"] == "failed" and record["exit_code"] == code
    assert record["attempts"] == 1 and not fake.waits
    assert load_state(cfg.root)["status"] == "failed"


@pytest.mark.parametrize("include_skipped", [True, False])
def test_all_cached_needs_no_wait(setup, include_skipped):
    cfg, fake = setup
    summary = {"called": 0, "valid": 100, "total": 100}
    if include_skipped:
        summary["skipped"] = 100
    fake.responses["first-run"] = [(0, summary)]
    assert fake.run(cfg) == 0
    record = first_record(cfg)
    assert record["called"] == record["fresh_valid"] == 0
    assert record["last_fresh_rate"] == 1 and record["attempts"] == 1
    assert not fake.waits


def test_completed_retry_passes_even_with_low_combined_fresh_rate(setup):
    cfg, fake = setup
    fake.responses["first-run"] = [
        (0, {"called": 20, "valid": 80, "total": 100, "skipped": 80}),
        (0, {"called": 20, "valid": 100, "total": 100, "skipped": 80}),
    ]
    assert fake.run(cfg) == 0
    record = first_record(cfg)
    assert record["called"] == 40 and record["fresh_valid"] == 20
    assert record["last_fresh_rate"] == 0.5 and record["low_streak"] == 0
    assert record["attempts"] == 2 and not fake.waits


def test_three_low_cycles_stop_with_usage_limit(setup):
    cfg, fake = setup
    fake.responses["first-run"] = [(0, HALF)] * 6
    assert fake.run(cfg) == 3
    assert fake.waits == [3600, 3600]
    assert first_record(cfg)["low_streak"] == 3
    assert first_record(cfg)["called"] == 12
    assert load_state(cfg.root)["status"] == "usage_limit_stop"
    assert fake.names()[-6:] == ["first-run"] * 6


@pytest.mark.parametrize("summary", [
    {"called": 5, "valid": 9, "total": 10},
    {"called": 0, "valid": 0, "results": []},
])
def test_ai_incomplete_retries_once_and_zero_total_is_valid(setup, summary):
    cfg, fake = setup
    fake.responses["first-run"] = [(0, summary), (0, summary)]
    assert fake.run(cfg) == 0
    assert first_record(cfg)["attempts"] == (2 if summary["valid"] else 1)
    assert not fake.waits


def test_missing_json_is_failure(setup):
    cfg, fake = setup
    fake.responses["first-run"] = [(0, "no json here")]
    assert fake.run(cfg) == 1
    assert first_record(cfg)["status"] == "failed"


@pytest.mark.parametrize("step", ["collect", "collect-retry"])
def test_schoolinfo_restriction_stops_immediately(setup, step):
    cfg, fake = setup
    fake.responses[step] = [(1, "paused after Schoolinfo access restriction or service response")]
    assert fake.run(cfg) == 4
    assert fake.names()[-1] == step
    assert "conversion" not in fake.names()
    assert load_state(cfg.root)["status"] == "schoolinfo_restricted"


@pytest.mark.parametrize("problem", ["nonempty", "missing", "codex"])
def test_ai_preflight_stops_before_child(setup, problem):
    cfg, fake = setup
    if problem == "nonempty":
        (cfg.isolated_cwd / "leftover").write_text("file")
    elif problem == "missing":
        cfg = replace(cfg, isolated_cwd=cfg.root / "not-created")
    else:
        fake.codex = False
    assert fake.run(cfg) == 6
    assert fake.names()[-1] == "first-targets"
    assert not (cfg.root / "not-created").exists()


def test_gate_failure_stops_next_bundle_and_cleans_owned_servers(setup):
    cfg, fake = setup
    fake.responses["mobile-1"] = [(0, {"overflow_px": 1})]
    assert fake.run(replace(cfg, bundles=(1, 2))) == 2
    assert fake.stopped == [101, 100]
    assert not any("nw2" in key for key, _, _ in fake.calls)
    assert load_state(cfg.root)["bundles"]["2"]["rounds"][round_key(2, 3)]["status"] == "pending"
    assert load_state(cfg.root)["status"] == "gate_failed"
    result = json.loads((cfg.root / OUTPUT / "gates/nw1.json").read_text())
    assert result["status"] == "failed"
    assert result["steps"]["mobile-1"]["metrics"]["overflow_px"] == 1
    assert result["steps"]["mobile-1"]["exit_code"] == 0


@pytest.mark.parametrize("metrics", [{}, dict.fromkeys(RENDERER_METRICS, 1)])
def test_renderer_requires_both_zero_metrics(setup, metrics):
    cfg, fake = setup
    fake.responses["renderer"] = [(0, metrics)]
    assert fake.run(cfg) == 2
    assert not fake.started


def test_status_reads_only_checkpoint_and_json_parses(setup, capsys):
    cfg, fake = setup
    assert runner.main(["status"], root=cfg.root) == 0
    assert capsys.readouterr().out.strip() == "기록 없음"
    assert fake.run(cfg) == 0
    path = cfg.root / OUTPUT / "state.json"
    before = path.read_bytes()
    assert runner.main(["status"], root=cfg.root) == 0
    text = capsys.readouterr().out
    assert all(word in text for word in ("학교 수 1", "초", "called", "무효", "완료"))
    assert runner.main(["status", "--json"], root=cfg.root) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["bundles"]["1"]["school_round_count"] == 2
    assert state["bundles"]["1"]["called"] == 6
    assert path.read_bytes() == before


def test_runner_lock_rejects_second_run_without_modifying_state(setup):
    cfg, fake = setup
    with runner_lock(cfg.root):
        assert fake.run(cfg) == 5
        assert not fake.calls
        assert runner.main(["status", "--json"], root=cfg.root) == 0


def test_publication_accumulates_completed_rounds_and_context_excludes_gold(setup):
    cfg, fake = setup
    assert fake.run(replace(cfg, bundles=(1, 2))) == 0
    state = load_state(cfg.root)
    rounds = publication_rounds(state)
    assert rounds == (*DEFAULT_ROUNDS, round_key(1, 3), round_key(1, 1),
                      round_key(2, 3), round_key(2, 1))
    assert state["bundles"]["1"]["publish"]["rounds"] == list(rounds[:-2])
    for key in (round_key(1, 3), round_key(2, 1)):
        path = cfg.root / f"data/derived/ai_read/{key}/first/verified.json"
        path.parent.mkdir(parents=True)
        path.write_text("{}")
    context = next(s for s in publish_steps(cfg, rounds) if s.name == "context")
    assert context.argv[4:] == (round_key(1, 3), round_key(2, 1))
    assert not any("gold" in arg for arg in context.argv)


@pytest.mark.parametrize("value, expected", [("2-6", (2, 3, 4, 5, 6)), ("1", (1,)),
                                              ("2,3", (2, 3))])
def test_parse_bundles(value, expected):
    assert runner.parse_bundles(value) == expected


def test_missing_roster_stops_before_any_child(setup):
    cfg, fake = setup
    (cfg.root / roster_path(1, 1)).unlink()
    assert fake.run(cfg) == 1
    assert not fake.calls
    assert "missing roster" in load_state(cfg.root)["last_stop"]["reason"]


def test_interrupted_wait_resumes_same_ai_stage(setup):
    cfg, fake = setup
    fake.responses["first-run"] = [(0, HALF), (0, HALF)]

    def interrupt(seconds):
        raise KeyboardInterrupt("synthetic wait interruption")

    code = runner.run(cfg, execute=fake.execute, sleep=interrupt,
                      start_server=fake.start, stop_server=fake.stop,
                      wait_ready=lambda server, marker: None, find_codex=lambda: True)
    assert code == 1
    assert first_record(cfg)["waits"] == 1
    count = len(fake.calls)
    assert fake.run(cfg) == 0
    assert fake.calls[count][1] == "first-run"
    record = first_record(cfg)
    assert record["called"] == 5 and record["fresh_valid"] == 3
    assert record["last_fresh_rate"] == 1 and record["low_streak"] == 0


def test_restore_failure_is_ignored_and_successful_gates_record_detail_seconds(setup):
    cfg, fake = setup
    fake.responses["restore-before-verify"] = [(1, "ignored")]
    fake.responses["restore-after-verify"] = [(1, "ignored")]
    fake.responses["audit-full"] = [(1, "expected blocking in full database")]
    fake.responses["method-text"] = [(1, "record only")]
    assert fake.run(cfg) == 0
    result = json.loads((cfg.root / OUTPUT / "gates/nw1.json").read_text())
    assert result["status"] == "done" and result["detail_seconds"] >= 0
    assert result["audit-public"]["exit_code"] == 0
    assert result["blocking_public_items"] == 0
    mobile = [step for _, name, step in fake.calls if name.startswith("mobile-")]
    assert [step.argv[-1] for step in mobile] == [
        "http://127.0.0.1:3102/", "http://127.0.0.1:3102/cases",
        "http://127.0.0.1:3102/references", "http://127.0.0.1:3102/cases/case1?item=item1"]


def test_last_json_reads_outer_report_and_results_fallback():
    text = 'progress {broken}\n{"old": 0}\n{"called": 2, "valid": 1, "results": [{"x": 3}]}'
    assert runner.ai_metrics(text) == {"called": 2, "valid": 1, "total": 1, "fresh_valid": 2}


@pytest.mark.parametrize("include_skipped", [True, False])
def test_fresh_valid_is_clamped_at_zero(include_skipped):
    summary = {"called": 20, "valid": 79, "total": 100}
    if include_skipped:
        summary["skipped"] = 80
    assert runner.ai_metrics(json.dumps(summary))["fresh_valid"] == 0


def test_all_failed_exit_forces_zero_fresh_valid():
    summary = {"called": 20, "valid": 82, "skipped": 80, "all_failed": True,
               "results": [{}] * 100}
    counts = runner.ai_metrics(json.dumps(summary), exit_code=3)
    assert counts == {"called": 20, "valid": 82, "total": 100, "fresh_valid": 0}


def test_server_readiness_failure_cleans_started_process(setup):
    cfg, fake = setup

    def timeout(server, marker):
        raise TimeoutError("synthetic readiness timeout")

    assert fake.run(cfg, wait_ready=timeout) == 2
    assert fake.stopped == [100]
    assert "web-build" not in fake.names()
    state = load_state(cfg.root)
    assert state["bundles"]["1"]["gate"]["steps"]["api-server"]["status"] == "failed"


def test_changed_roster_restarts_affected_round_and_publication(setup):
    cfg, fake = setup
    assert fake.run(cfg) == 0
    path = cfg.root / roster_path(1, 1)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(",".join(["second-school"] * len(ROUND_COLUMNS)) + "\n")
    count = len(fake.calls)
    assert fake.run(cfg) == 0
    new_calls = fake.calls[count:]
    assert new_calls[0][0:2] == (round_key(1, 1), "collect")
    assert not any(key == round_key(1, 3) for key, _, _ in new_calls)
    assert "build0" in [name for _, name, _ in new_calls]
    assert load_state(cfg.root)["bundles"]["1"]["school_count"] == 2
