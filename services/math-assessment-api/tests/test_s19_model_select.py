"""Test model selection, cached responses and timing with synthetic fake responses.

Run .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
    services/math-assessment-api/tests/test_s19_model_select.py
Verify .venv/Scripts/python.exe -m ruff check this file.
All generated inputs and outputs live under tmp_path; Codex and network are blocked.
"""

import json

import pytest
from scripts import middle_ai_fields as fields
from scripts import middle_ai_read as ai
from scripts import science_axes_ai as axes
from scripts import science_card_check as cards


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Only fake responses are allowed: no Codex or network calls")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(ai, "find_codex", lambda: "offline-codex.exe")
    monkeypatch.delenv(ai.AI_MODEL_ENV, raising=False)


def fake_responses(directory, targets, marker):
    for target in targets:
        identity = target["target_id"]
        ai.save_json(directory / f"{identity}.json", {"tasks": [], "uncertain": [marker]})
        ai.write_text(directory / f"{identity}.events.jsonl", '{"type":"turn.completed"}\n')
    return directory


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    output, isolated = tmp_path / "output", tmp_path / "isolated"
    isolated.mkdir()
    targets = []
    for identity in ("one", "two"):
        prompt = f"Synthetic input {identity}\n"
        targets.append({"target_id": identity, "prompt_sha256": ai.sha(prompt)})
        ai.write_text(output / f"prompts/{identity}.md", prompt)
    ai.write_text(output / "targets.jsonl", "".join(json.dumps(t) + "\n" for t in targets))
    # The production boundary requires a directory outside D:/workspace; these
    # offline tests keep every file inside tmp_path and stub only that boundary.
    monkeypatch.setattr(ai, "isolated_directory", lambda path: isolated)
    return {"root": tmp_path, "output": output, "isolated": isolated, "targets": targets,
            "fake": fake_responses(tmp_path / "fake", targets, "original")}


def run(workspace, **kwargs):
    options = {"workers": 1, "output_dir": workspace["output"],
               "fake_responses": workspace["fake"], **kwargs}
    return ai.run_targets(workspace["root"], None, workspace["isolated"], **options)


@pytest.mark.parametrize("argument, environment, expected", [
    (None, None, None),
    (None, "gpt-6.1-terra", "gpt-6.1-terra"),
    ("gpt-6-luna", "gpt-6.1-terra", "gpt-6-luna"),
])
def test_command_model_precedence(tmp_path, monkeypatch, argument, environment, expected):
    if environment is not None:
        monkeypatch.setenv(ai.AI_MODEL_ENV, environment)
    expected = expected or ai.DEFAULT_AI_MODEL
    answer = tmp_path / "answer.json"
    command = ai.codex_command(tmp_path, answer, codex="offline", model=argument)
    assert command == ["offline", "exec", "--strict-config", "--skip-git-repo-check",
                       "-m", expected, "-s", "read-only", "-C", str(tmp_path),
                       "--json", "-o", str(answer), "-"]


def test_default_constant_is_resolved_at_call_time(tmp_path, monkeypatch):
    monkeypatch.setattr(ai, "DEFAULT_AI_MODEL", "gpt-6-luna")
    command = ai.codex_command(tmp_path, tmp_path / "answer.json", codex="offline")
    assert command[command.index("-m") + 1] == "gpt-6-luna"


@pytest.mark.parametrize("source", ["argument", "environment", "default"])
@pytest.mark.parametrize("model", ["gpt-6-astra", "GPT-6-ASTRA-preview"])
def test_astra_is_rejected_even_for_fake_and_dry_runs(workspace, monkeypatch, source, model):
    argument = model if source == "argument" else None
    if source == "environment":
        monkeypatch.setenv(ai.AI_MODEL_ENV, model)
    elif source == "default":
        monkeypatch.setattr(ai, "DEFAULT_AI_MODEL", model)
    with pytest.raises(ValueError, match="gpt-6-astra"):
        ai.codex_command(workspace["isolated"], workspace["root"] / "answer", model=argument)
    for dry_run in (False, True):
        with pytest.raises(ValueError, match="gpt-6-astra"):
            run(workspace, model=argument, dry_run=dry_run)
    assert not (workspace["output"] / "responses").exists()


def test_explicit_model_overrides_excluded_environment_and_config(workspace, monkeypatch):
    monkeypatch.setenv(ai.AI_MODEL_ENV, "gpt-6-astra")
    ai.write_text(workspace["root"] / "config.toml", 'model = "gpt-6-astra"\n')
    monkeypatch.setenv("CODEX_HOME", str(workspace["root"]))
    assert run(workspace, model="gpt-6-luna")["valid"] == 2
    command = ai.codex_command(workspace["isolated"], workspace["root"] / "answer",
                               model="gpt-6-luna")
    assert command[command.index("-m") + 1] == "gpt-6-luna"


def test_same_model_skips_and_changed_model_reads_new_fake_folder(workspace):
    first = run(workspace, model="gpt-6-luna")
    assert first["model"] == "gpt-6-luna" and first["called"] == first["valid"] == 2
    statuses = [workspace["output"] / f"responses/{t['target_id']}.status.json"
                for t in workspace["targets"]]
    before = [path.read_bytes() for path in statuses]
    for path in statuses:
        status = ai.read_json(path)
        assert status["model"] == "gpt-6-luna"
        assert isinstance(status["elapsed_seconds"], float) and status["elapsed_seconds"] >= 0
        assert status["elapsed_seconds"] == round(status["elapsed_seconds"], 1)
    second = run(workspace, model="gpt-6-luna", fake_responses=workspace["root"] / "missing")
    assert second["skipped"] == second["valid"] == 2 and second["called"] == 0
    assert second["mean_elapsed_seconds"] is None
    assert [path.read_bytes() for path in statuses] == before
    alternate = fake_responses(workspace["root"] / "alternate", workspace["targets"], "terra")
    third = run(workspace, model="gpt-6.1-terra", fake_responses=alternate)
    assert third["skipped"] == 0 and third["called"] == third["valid"] == 2
    assert ai.read_json(workspace["output"] / "run.json") == third
    for target, path in zip(workspace["targets"], statuses, strict=True):
        assert ai.read_json(path)["model"] == "gpt-6.1-terra"
        answer = workspace["output"] / f"responses/{target['target_id']}.json"
        assert ai.read_json(answer)["uncertain"] == ["terra"]
        assert ai.valid_run(workspace["output"], target)[0]


def test_elapsed_mean_counts_only_calls_and_includes_failures(workspace, monkeypatch):
    ticks = iter((10, 11.24, 20, 23.64))
    monkeypatch.setattr(ai.time, "perf_counter", lambda: next(ticks))
    first = run(workspace)
    assert [r["elapsed_seconds"] for r in first["results"]] == [1.2, 3.6]
    assert first["called"] == 2 and first["mean_elapsed_seconds"] == 2.4
    path = workspace["output"] / "responses/two.status.json"
    status = ai.read_json(path)
    status["valid"] = False
    ai.save_json(path, status)
    ticks = iter((100, 102.26))
    report = run(workspace, fake_responses=workspace["root"] / "missing")
    assert report["called"] == report["skipped"] == report["valid"] == 1
    assert report["mean_elapsed_seconds"] == 2.3
    status = ai.read_json(path)
    assert not status["valid"] and status["elapsed_seconds"] == 2.3
    assert status["model"] == ai.DEFAULT_AI_MODEL


def test_legacy_status_is_sol_even_if_default_changes(workspace, monkeypatch):
    run(workspace, model="gpt-6.1-sol")
    for target in workspace["targets"]:
        path = workspace["output"] / f"responses/{target['target_id']}.status.json"
        status = ai.read_json(path)
        del status["model"]
        ai.save_json(path, status)
    monkeypatch.setattr(ai, "DEFAULT_AI_MODEL", "gpt-6.1-terra")
    for target in workspace["targets"]:
        assert ai.valid_run(workspace["output"], target)[0]
        assert ai.valid_run(workspace["output"], target, model="gpt-6.1-sol")[0]
        assert not ai.valid_run(workspace["output"], target, model="gpt-6.1-terra")[0]
    assert run(workspace, model="gpt-6.1-sol")["skipped"] == 2
    assert run(workspace)["called"] == 2


def cli(workspace, monkeypatch, command):
    common = ["--isolated-cwd", str(workspace["isolated"]),
              "--fake-responses", str(workspace["fake"])]
    if command in {"run", "fields-run"}:
        monkeypatch.setattr(ai, "ROOT", workspace["root"])
        monkeypatch.setattr(ai, "round_dir", lambda root, key: workspace["output"])
        monkeypatch.setattr(fields, "directory", lambda *args: workspace["output"])
        return ai.main, [command, "--round-key", "synthetic", *common]
    main = cards.main if command == "cards" else axes.main
    return main, ["run", "--out-dir", str(workspace["output"]), *common]


@pytest.mark.parametrize("command", ["run", "fields-run", "cards", "axes"])
@pytest.mark.parametrize("explicit", [True, False])
def test_cli_passes_selected_model(workspace, monkeypatch, command, explicit):
    monkeypatch.setenv(ai.AI_MODEL_ENV, "gpt-6.1-terra")
    main, argv = cli(workspace, monkeypatch, command)
    assert main(argv + (["--model", "gpt-6-luna"] if explicit else [])) in (None, 0)
    report = ai.read_json(workspace["output"] / "run.json")
    expected = "gpt-6-luna" if explicit else "gpt-6.1-terra"
    assert report["model"] == expected and report["valid"] == report["called"] == 2
    assert all(r["model"] == expected for r in report["results"])


@pytest.mark.parametrize("command", ["run", "fields-run"])
def test_dry_run_prints_model_without_counting_calls(workspace, monkeypatch, capsys, command):
    main, argv = cli(workspace, monkeypatch, command)
    assert main([*argv, "--model", "gpt-6-luna", "--dry-run"]) is None
    assert "-m gpt-6-luna" in capsys.readouterr().out
    report = run(workspace, model="gpt-6-luna", dry_run=True)
    assert report["model"] == "gpt-6-luna"
    assert report["called"] == 0 and report["mean_elapsed_seconds"] is None
    assert not (workspace["output"] / "responses").exists()
    assert not (workspace["output"] / "run.json").exists()
