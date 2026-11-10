"""Verify detached launching, bounded restarts and liveness using only fake children.

Run .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .tmp/n1/pt-w4
    services/math-assessment-api/tests/test_run_nationwide_launch.py.
Verify .venv/Scripts/python.exe -m ruff check scripts/*nationwide*.py
       services/math-assessment-api/tests/test_run_nationwide*.py.
"""

import json
import os
import re
import subprocess
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest
from scripts import nationwide_launch as launcher
from scripts import nationwide_state as state_module
from scripts import run_nationwide as runner
from scripts.nationwide_state import Checkpoint, load_state, pid_is_alive, runner_lock
from scripts.nationwide_steps import OUTPUT, Config, round_key
from test_run_nationwide import HALF
from test_run_nationwide import no_real_children as no_real_children
from test_run_nationwide import setup as setup

STARTED = "2026-11-10T14:00:00+09:00"
HEARTBEAT = "2026-11-10T14:01:00+09:00"
ENDED = "2026-11-10T14:02:00+09:00"


def events(root):
    return [json.loads(line) for line in
            (root / OUTPUT / "events.jsonl").read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("platform", ["nt", "posix"])
def test_launch_detaches_and_passes_config(tmp_path, capsys, platform):
    cfg = Config(tmp_path, (2, 3), "synthetic-model", 4, tmp_path / "isolated", 17)
    calls = []

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        with runner_lock(tmp_path):
            pass  # The launcher must release its probe before spawning.
        stream = kwargs["stdout"]
        assert stream.encoding == "utf-8" and not stream.closed
        stream.write("가짜 실행기\n")
        return SimpleNamespace(pid=123)

    assert launcher.launch(cfg, popen=popen, platform=platform) == 0
    argv, options = calls[0]
    assert argv[:3] == [sys.executable, "scripts/run_nationwide.py", "run"]
    args = launcher.build_parser("").parse_args(argv[2:])
    assert (args.bundles, args.model, args.workers, args.isolated_cwd, args.wait_seconds) == (
        cfg.bundles, cfg.model, cfg.workers, cfg.isolated_cwd, cfg.wait_seconds)
    assert argv[-2:] == ["--restart-on-failure", "3"]
    assert options["stdin"] == subprocess.DEVNULL
    assert options["stderr"] == subprocess.STDOUT
    assert options["close_fds"] is True and options["cwd"] == tmp_path
    assert options["env"]["PYTHONIOENCODING"] == "utf-8"
    if platform == "nt":
        assert options["creationflags"] == 0x00000008 | 0x00000200
        assert "start_new_session" not in options
    else:
        assert options["start_new_session"] is True
        assert "creationflags" not in options
    logs = list((tmp_path / OUTPUT).glob("runner-*.log"))
    assert len(logs) == 1 and re.fullmatch(r"runner-\d{8}-\d{6}\.log", logs[0].name)
    assert logs[0].read_text(encoding="utf-8") == "가짜 실행기\n"
    assert options["stdout"].closed
    assert capsys.readouterr().out.splitlines() == ["PID: 123", f"로그: {logs[0]}"]
    assert not (tmp_path / OUTPUT / "state.json").exists()


def test_launch_cli_forwards_options_and_default_restart(tmp_path):
    calls = []

    def popen(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(pid=123)

    argv = ["launch", "--bundles", "2-6", "--model", "synthetic", "--workers", "2",
            "--isolated-cwd", "isolated", "--wait-seconds", "12.5"]
    assert runner.main(argv, root=tmp_path, popen=popen) == 0
    assert calls[0][4] == "2,3,4,5,6"
    assert str(tmp_path / "isolated") in calls[0]
    assert calls[0][-2:] == ["--restart-on-failure", "3"]
    assert runner.main([*argv, "--restart-on-failure", "8"], root=tmp_path, popen=popen) == 0
    assert calls[1][-2:] == ["--restart-on-failure", "8"]


def test_launch_locked_never_spawns_or_changes_state(tmp_path):
    checkpoint = Checkpoint(tmp_path)
    checkpoint.save()
    path = tmp_path / OUTPUT / "state.json"
    before = path.read_bytes()
    with runner_lock(tmp_path):
        assert runner.main(["launch", "--bundles", "2-6"], root=tmp_path) == 5
    assert path.read_bytes() == before
    assert not list((tmp_path / OUTPUT).glob("runner-*.log"))


@pytest.mark.parametrize("command", ["run", "launch"])
def test_cli_requires_bundles_and_nonnegative_restarts(tmp_path, command):
    for args in ([command], [command, "--bundles", "1", "--restart-on-failure", "-1"]):
        with pytest.raises(SystemExit) as error:
            runner.main(args, root=tmp_path)
        assert error.value.code == 2
    assert not (tmp_path / OUTPUT).exists()


def test_run_cli_passes_restart_and_argv(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(runner, "run", lambda cfg, **kwargs: calls.append((cfg, kwargs)) or 0)
    args = ["run", "--bundles", "2-3", "--restart-on-failure", "4"]
    assert runner.main(args, root=tmp_path) == 0
    assert calls[0][0].bundles == (2, 3)
    assert calls[0][1] == {"restart_on_failure": 4,
                           "argv": ["scripts/run_nationwide.py", *args]}
    assert runner.main(["run", "--bundles", "1"], root=tmp_path) == 0
    assert calls[1][1]["restart_on_failure"] == 0


def test_restart_resumes_same_bundles_and_holds_lock_during_wait(setup):
    cfg, fake = setup
    cfg = replace(cfg, bundles=(1, 2))
    fake.responses["conversion"] = [(1, "transient failure")]

    def sleep(seconds):
        fake.waits.append(seconds)
        state = load_state(cfg.root)
        assert "ended_at" not in state["runner"]
        assert runner.main(["launch", "--bundles", "1,2"], root=cfg.root) == 5

    assert fake.run(cfg, restart_on_failure=3, sleep=sleep) == 0
    assert fake.waits == [300]
    assert fake.names()[:4] == ["collect", "collect-retry", "conversion", "conversion"]
    records = events(cfg.root)
    restarts = [event for event in records if event["event"] == "restart"]
    assert len(restarts) == 1
    assert restarts[0]["attempt"] == 1 and restarts[0]["seconds"] == 300
    assert restarts[0]["reason"] == f"{round_key(1, 3)}/conversion exited 1"
    assert all(load_state(cfg.root)["bundles"][str(b)]["status"] == "done" for b in (1, 2))


@pytest.mark.parametrize("code", [2, 3, 4, 6])
def test_nonretryable_exit_never_restarts(setup, code):
    cfg, fake = setup
    if code == 2:
        fake.responses["mobile-1"] = [(0, {"overflow_px": 1})]
    elif code == 3:
        fake.responses["first-run"] = [(0, HALF)] * 6
    elif code == 4:
        fake.responses["collect"] = [(1, runner.RESTRICTION_MESSAGE)]
    else:
        fake.codex = False
    assert fake.run(cfg, restart_on_failure=3) == code
    assert 300 not in fake.waits
    assert not any(event["event"] == "restart" for event in events(cfg.root))
    assert load_state(cfg.root)["runner"]["exit_code"] == code


@pytest.mark.parametrize("step_name", ["first-run", "fields-run", "ax-run", "cc-run"])
def test_all_failed_exit_uses_usage_limit_stop_without_restart(setup, step_name):
    cfg, fake = setup
    failed = {"called": 20, "valid": 80, "skipped": 80, "all_failed": True,
              "results": [{}] * 100}
    fake.responses[step_name] = [(3, failed)] * 6
    assert fake.run(cfg, restart_on_failure=3) == 3
    assert fake.waits == [3600, 3600]
    state = load_state(cfg.root)
    assert state["status"] == "usage_limit_stop"
    assert state["runner"]["exit_code"] == state["last_stop"]["code"] == 3
    scope = (state["bundles"]["1"]["publish"] if step_name in ("ax-run", "cc-run")
             else state["bundles"]["1"]["rounds"][round_key(1, 3)])
    record = scope["steps"][step_name]
    assert record["attempts"] == 6 and record["low_streak"] == 3
    assert record["called"] == 120 and record["fresh_valid"] == 0
    assert record["last_fresh_rate"] == 0
    records = events(cfg.root)
    assert not any(event["event"] == "restart" for event in records)
    assert [event["valid_rate"] for event in records if event["event"] == "wait"] == [0, 0]


def test_locked_run_does_not_retry_or_write_runner(setup):
    cfg, fake = setup
    with runner_lock(cfg.root):
        assert fake.run(cfg, restart_on_failure=3) == 5
    assert not fake.calls and not fake.waits
    assert "runner" not in load_state(cfg.root)


def test_restart_budget_returns_last_failure(setup):
    cfg, fake = setup
    fake.responses["conversion"] = [(9, "still failed")] * 3
    assert fake.run(cfg, restart_on_failure=2) == 1
    assert fake.waits == [300, 300]
    assert fake.names().count("collect") == 1
    assert fake.names().count("conversion") == 3
    restarts = [event for event in events(cfg.root) if event["event"] == "restart"]
    assert [event["attempt"] for event in restarts] == [1, 2]
    state = load_state(cfg.root)
    assert state["runner"]["ended_at"] and state["runner"]["exit_code"] == 1
    assert state["last_stop"]["reason"].endswith("exited 9")


@pytest.mark.parametrize("injected, expected", [(None, 9), (7, 7)])
def test_restart_wait_can_be_changed_without_real_sleep(setup, monkeypatch, injected, expected):
    cfg, fake = setup
    monkeypatch.setattr(runner, "RESTART_WAIT_SECONDS", 9)
    fake.responses["collect"] = [(1, "fail")] * 2
    assert fake.run(cfg, restart_on_failure=1, restart_wait_seconds=injected) == 1
    assert fake.waits == [expected]


def test_interrupted_restart_wait_records_final_exit(setup):
    cfg, fake = setup
    fake.responses["collect"] = [(1, "fail")]

    def interrupt(seconds):
        raise KeyboardInterrupt("synthetic restart wait interruption")

    assert fake.run(cfg, restart_on_failure=3, sleep=interrupt) == 1
    state = load_state(cfg.root)
    assert fake.names() == ["collect"]
    assert state["runner"]["ended_at"] and state["runner"]["exit_code"] == 1
    assert state["status"] == "interrupted"


def test_run_records_live_runner_then_end_and_refreshes_next_run(setup):
    cfg, fake = setup
    observations = []
    argv = ["scripts/run_nationwide.py", "run", "--bundles", "1"]

    def execute(step, log_path):
        active = load_state(cfg.root)["runner"]
        assert active["pid"] == os.getpid() and active["argv"] == argv
        assert active["started_at"] and active["heartbeat_at"] and "ended_at" not in active
        observations.append(active)
        return fake.execute(step, log_path)

    assert fake.run(cfg, execute=execute, argv=argv) == 0
    state = load_state(cfg.root)
    assert observations and state["runner"]["ended_at"]
    assert state["runner"]["exit_code"] == 0
    assert state["runner"]["heartbeat_at"] == events(cfg.root)[-1]["time"]
    fake.responses["conversion"] = [(1, "unused because done")]
    assert fake.run(cfg, argv=["resumed"]) == 0
    state = load_state(cfg.root)
    assert state["runner"]["argv"] == ["resumed"] and "last_stop" not in state


def test_every_event_refreshes_persisted_heartbeat(tmp_path, monkeypatch):
    clock = [STARTED]
    monkeypatch.setattr(state_module, "now", lambda: clock[0])
    checkpoint = Checkpoint(tmp_path)
    checkpoint.start_runner(["synthetic"])
    assert load_state(tmp_path)["runner"]["heartbeat_at"] == STARTED
    clock[0] = HEARTBEAT
    checkpoint.event("synthetic-event")
    assert load_state(tmp_path)["runner"]["heartbeat_at"] == HEARTBEAT
    assert events(tmp_path)[-1]["time"] == HEARTBEAT
    clock[0] = ENDED
    checkpoint.end_runner(0)
    assert load_state(tmp_path)["runner"]["ended_at"] == ENDED


@pytest.mark.parametrize("kind", ["running", "stopped", "disconnected"])
def test_status_first_line_and_json_are_read_only(tmp_path, capsys, kind):
    checkpoint = Checkpoint(tmp_path)
    checkpoint.state.update(status="failed", runner={"pid": 123, "started_at": STARTED,
                            "heartbeat_at": HEARTBEAT, "argv": ["synthetic"]})
    if kind == "stopped":
        checkpoint.state["runner"].update(ended_at=ENDED, exit_code=1)
        checkpoint.state["last_stop"] = {"time": ENDED, "code": 1, "reason": "synthetic fail"}
    checkpoint.save()
    path = tmp_path / OUTPUT / "state.json"
    before = path.read_bytes()
    calls = []

    def alive(pid):
        calls.append(pid)
        return kind == "running"

    expected = {"running": f"실행기: 실행 중(PID 123, 마지막 기록 {HEARTBEAT})",
                "stopped": f"실행기: 멈춤(종료 코드 1, 끝난 시각 {ENDED}, 이유 synthetic fail)",
                "disconnected": f"실행기: 끊김(PID 123, 마지막 기록 {HEARTBEAT}) "
                                "— 같은 launch 명령으로 이으면 된다"}
    assert runner.main(["status"], root=tmp_path, pid_alive=alive) == 0
    assert capsys.readouterr().out.splitlines()[0] == expected[kind]
    assert calls == ([] if kind == "stopped" else [123])
    calls.clear()
    assert runner.main(["status", "--json"], root=tmp_path, pid_alive=alive) == 0
    assert json.loads(capsys.readouterr().out)["runner"]["pid"] == 123
    assert not calls and path.read_bytes() == before


@pytest.mark.parametrize("output, expected", [("python.exe 123 Console 1 123 K", True),
                                              ("python.exe 1234 Console 1 0 K", False),
                                              ("INFO: No tasks match", False)])
def test_windows_liveness_uses_exact_tasklist_pid(output, expected):
    calls = []

    def tasklist(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout=output)

    assert pid_is_alive(123, platform="nt", run_command=tasklist) is expected
    assert calls == [["tasklist", "/FI", "PID eq 123", "/NH"]]


def test_missing_tasklist_is_treated_as_disconnected():
    def missing(*args, **kwargs):
        raise FileNotFoundError("synthetic missing tasklist")

    assert pid_is_alive(123, platform="nt", run_command=missing) is False


@pytest.mark.parametrize("error, expected", [(None, True), (PermissionError(), True),
                                           (ProcessLookupError(), False)])
def test_posix_liveness_injects_signal_check(error, expected):
    calls = []

    def kill(pid, signal):
        calls.append((pid, signal))
        if error is not None:
            raise error

    assert pid_is_alive(123, platform="posix", kill=kill) is expected
    assert calls == [(123, 0)]
    assert pid_is_alive(0, platform="posix", kill=kill) is False
