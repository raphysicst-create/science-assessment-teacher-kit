"""Offline Codex discovery and exit-code regressions using synthetic files.

Run: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider services/math-assessment-api/tests/test_middle_ai_read_codex.py
"""

import importlib.util
import os
from pathlib import Path

import pytest
from scripts import middle_ai_read as ai
from test_middle_s6e1 import ROUND, directory, fake_files, install_source


@pytest.fixture(autouse=True)
def offline_codex(directory, monkeypatch):
    # The reused directory fixture blocks subprocess.run and socket connections.
    binary = directory / "bin/installed/codex.exe"
    binary.parent.mkdir(parents=True)
    binary.touch()
    monkeypatch.setattr(ai, "CODEX_GLOB", str(directory / "bin/*/codex.exe"))
    monkeypatch.delenv(ai.CODEX_EXE_ENV, raising=False)
    return binary


def test_find_codex_chooses_latest(directory):
    for name, mtime in (("aaa", 100), ("bbb", 200)):
        binary = directory / f"versions/{name}/codex.exe"
        binary.parent.mkdir(parents=True)
        binary.touch()
        os.utime(binary, (mtime, mtime))
    pattern = str(directory / "versions/*/codex.exe")
    assert Path(ai.find_codex(pattern, env={})) == directory / "versions/bbb/codex.exe"


def test_find_codex_environment_overrides_glob(directory, offline_codex, monkeypatch):
    override = directory / "override.exe"
    override.touch()
    assert ai.find_codex(env={"CODEX_EXE": str(override)}) == str(override)
    monkeypatch.setenv("CODEX_EXE", str(override))
    assert ai.find_codex() == str(override)
    assert Path(ai.find_codex(env={"CODEX_EXE": str(directory / "missing.exe")})) == offline_codex


def test_find_codex_missing(directory):
    pattern = str(directory / "missing/*/codex.exe")
    with pytest.raises(FileNotFoundError) as excinfo:
        ai.find_codex(pattern, env={})
    assert str(excinfo.value) == f"Codex 실행 파일을 찾지 못함: {pattern}"


def test_codex_command_explicit_and_discovered(directory, monkeypatch):
    calls = []

    def find():
        calls.append(True)
        return "discovered.exe"

    monkeypatch.setattr(ai, "find_codex", find)
    answer = directory / "answer.json"
    assert ai.codex_command(directory, answer, codex="X")[0] == "X"
    assert calls == []
    assert ai.codex_command(directory, answer)[0] == "discovered.exe"
    assert calls == [True]


def test_module_has_no_stale_hash():
    assert "14b838c1d074ff01" not in Path(ai.__file__).read_text(encoding="utf-8")


def test_import_does_not_discover_codex(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Import must not discover Codex")

    monkeypatch.setattr(ai.glob, "glob", forbidden)
    spec = importlib.util.spec_from_file_location("scripts._codex_import_test", ai.__file__)
    spec.loader.exec_module(importlib.util.module_from_spec(spec))


@pytest.mark.parametrize("report, expected", [
    ({"all_failed": True}, 3), ({"all_failed": False}, 0), ({}, 0),
])
def test_run_exit_code(report, expected):
    assert ai.run_exit_code(report) == expected


def prepare_run(directory, monkeypatch, command):
    install_source(directory, "과학 평가계획\n1학년 1학기\n관찰 보고서\n")
    ai.build_targets(directory, ROUND)
    output = ai.round_dir(directory, ROUND)
    targets = ai.load_targets(output)
    assert targets
    if command == "fields-run":
        fields_output = output / "fields"
        ai.write_text(fields_output / "targets.jsonl", ai.read_text(output / "targets.jsonl"))
        for target in targets:
            prompt = f"prompts/{target['target_id']}.md"
            ai.write_text(fields_output / prompt, ai.read_text(output / prompt))
        output = fields_output
    monkeypatch.setattr(ai, "ROOT", directory)
    monkeypatch.setattr(ai, "isolated_directory", lambda path: directory)
    argv = [command, "--round-key", ROUND, "--isolated-cwd", str(directory)]
    return output, targets, argv


@pytest.mark.parametrize("command", ["run", "fields-run"])
def test_main_all_failed_then_valid(directory, monkeypatch, capsys, command):
    output, targets, argv = prepare_run(directory, monkeypatch, command)
    fake = directory / "fake"
    with pytest.raises(SystemExit) as excinfo:
        ai.main([*argv, "--fake-responses", str(fake)])
    assert excinfo.value.code == 3
    report = ai.read_json(output / "run.json")
    assert report["valid"] == 0 and report["all_failed"] is True
    captured = capsys.readouterr()
    assert '"all_failed": true' in captured.out
    assert captured.err == "유효 응답 0: 모든 호출이 실패함\n"

    fake_files(directory, targets)
    assert ai.main([*argv, "--fake-responses", str(fake)]) is None
    report = ai.read_json(output / "run.json")
    assert report["valid"] == len(targets) and report["all_failed"] is False
    assert ai.run_exit_code(report) == 0


@pytest.mark.parametrize("command", ["run", "fields-run"])
def test_dry_run_is_success(directory, monkeypatch, command):
    output, _, argv = prepare_run(directory, monkeypatch, command)
    report = ai.run_targets(directory, ROUND, directory, dry_run=True, output_dir=output)
    assert report["valid"] == 0 and report["all_failed"] is False
    assert ai.run_exit_code(report) == 0
    assert ai.main([*argv, "--dry-run"]) is None


@pytest.mark.parametrize("command", ["run", "fields-run"])
def test_main_missing_codex_exits_two(directory, monkeypatch, capsys, command):
    _, _, argv = prepare_run(directory, monkeypatch, command)
    monkeypatch.setattr(ai, "default_model_guard", lambda: None)
    monkeypatch.setattr(ai, "CODEX_GLOB", str(directory / "missing/*/codex.exe"))
    with pytest.raises(SystemExit) as excinfo:
        ai.main(argv)
    assert excinfo.value.code == 2
    assert "Codex 실행 파일을 찾지 못함:" in capsys.readouterr().err


def test_no_targets_is_not_all_failed(directory, monkeypatch):
    output, _, _ = prepare_run(directory, monkeypatch, "run")
    ai.write_text(output / "targets.jsonl", "")
    report = ai.run_targets(directory, ROUND, directory, fake_responses=directory / "fake")
    assert report["results"] == [] and report["valid"] == 0
    assert report["all_failed"] is False
    assert ai.run_exit_code(report) == 0
