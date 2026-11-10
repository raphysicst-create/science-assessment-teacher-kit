"""Verify checkpoint-only reset boundaries without executing any pipeline children.

Run .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
    services/math-assessment-api/tests/test_run_nationwide_reset.py.
"""

import copy
import json

import pytest
from scripts import run_nationwide as runner
from scripts.nationwide_state import Checkpoint, load_state, runner_lock
from scripts.nationwide_steps import OUTPUT, ROUND_ORDER, Config, round_key, round_steps
from test_run_nationwide import no_real_children as no_real_children


def completed_checkpoint(root):
    checkpoint = Checkpoint(root)
    names = [step.name for step in round_steps(Config(root), 1, 3)]
    with checkpoint.edit() as state:
        state["status"] = "done"
        for number in (1, 2, 3):
            state["bundles"][str(number)] = {
                "status": "done", "school_count": 1,
                "rounds": {round_key(number, term): {
                    "status": "done", "roster_sha256": "synthetic",
                    "steps": {name: {"status": "done", "seconds": 1} for name in names},
                } for term in ROUND_ORDER},
                "publish": {"key": f"publish:nw{number}", "status": "done",
                            "rounds": ["saved publication input"],
                            "steps": {"build0": {"status": "done", "seconds": 2}}},
                "gate": {"key": f"gate:nw{number}", "status": "done",
                         "rounds": ["saved gate input"],
                         "steps": {"verify": {"status": "done", "seconds": 2}}},
            }
        state["last_stop"] = {"reason": "old failure", "code": 1, "time": "synthetic"}
    return copy.deepcopy(checkpoint.state)


@pytest.mark.parametrize("bundles", [(1,), (2,), (1, 3)])
def test_reset_only_selected_round_suffix_and_following_publication(tmp_path, bundles):
    before = completed_checkpoint(tmp_path)
    names = [step.name for step in round_steps(Config(tmp_path), 1, 3)]
    split = names.index("items")
    assert runner.main(["reset", "--bundles", ",".join(map(str, bundles)),
                        "--from", "items"], root=tmp_path) == 0
    state = load_state(tmp_path)
    for number in (1, 2, 3):
        entry, old = state["bundles"][str(number)], before["bundles"][str(number)]
        for key, scope in entry["rounds"].items():
            if number in bundles:
                assert list(scope["steps"]) == names[:split]
                assert scope["steps"] == {name: old["rounds"][key]["steps"][name]
                                          for name in names[:split]}
                assert scope["status"] == "pending" and scope["roster_sha256"] == "synthetic"
            else:
                assert scope == old["rounds"][key]
        if number >= min(bundles):
            assert "publish" not in entry and "gate" not in entry
            assert entry["status"] == "pending"
        else:
            assert entry == old
    assert state["status"] == "pending" and "last_stop" not in state
    records = (tmp_path / OUTPUT / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(records) == 1
    event = json.loads(records[0])
    assert event["event"] == "reset" and event["from_step"] == "items"
    assert event["bundles"] == list(bundles)


def test_reset_rejects_running_lock_without_modifying_checkpoint(tmp_path):
    completed_checkpoint(tmp_path)
    path = tmp_path / OUTPUT / "state.json"
    before = path.read_bytes()
    with runner_lock(tmp_path):
        assert runner.main(["reset", "--bundles", "1", "--from", "items"],
                           root=tmp_path) == 5
    assert path.read_bytes() == before and not (tmp_path / OUTPUT / "events.jsonl").exists()


@pytest.mark.parametrize("name", ["build0", "gate", "not-a-step"])
def test_reset_rejects_non_round_steps_without_touching_state(tmp_path, name):
    with pytest.raises(SystemExit) as error:
        runner.main(["reset", "--bundles", "1", "--from", name], root=tmp_path)
    assert error.value.code == 2 and not (tmp_path / OUTPUT).exists()
