"""first-merge checks each converted document once, and still stops on a changed one.

Run: .venv/Scripts/python.exe -m pytest -q \
    services/math-assessment-api/tests/test_merge_checks_each_conversion_once.py
Why: nw6 round 3 re-read 1,297 documents for 5,293 tasks (526 s, 11-19).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import middle_ai_first_merge as merge  # noqa: E402

ROUND = "2026-round-3-nw9"


def task(path, text_sha="h1"):
    return {"target_ids": ["t1"], "converted_path": path, "text_sha256": text_sha}


@pytest.fixture
def stubbed(monkeypatch, tmp_path):
    calls = []
    verified = {"round": ROUND, "targets_sha256": "s", "run_bindings": {"t1": {"a": 1}},
                "kept": [task("a.json"), task("a.json"), task("b.json"), task("a.json")]}
    ai = merge.ai
    monkeypatch.setattr(ai, "round_dir", lambda root, key: tmp_path)
    monkeypatch.setattr(ai, "read_json", lambda path: (
        verified if path.name == "verified.json" else {"a": 1}))
    monkeypatch.setattr(ai, "read_text", lambda path: "targets")
    monkeypatch.setattr(ai, "sha", lambda text: "s")
    monkeypatch.setattr(ai, "load_targets", lambda out: [{"target_id": "t1"}])
    monkeypatch.setattr(ai, "valid_run", lambda out, target: (True, {}))

    def conversion_for(root, document):
        calls.append(document["converted_path"])
        if document["text_sha256"] != "h1":
            raise KeyError("hash")  # stands in for a changed conversion
        return {}

    monkeypatch.setattr(ai, "conversion_for", conversion_for)
    return verified, calls


def test_each_document_is_checked_once(stubbed, tmp_path):
    verified, calls = stubbed
    assert merge.verified_input(tmp_path, ROUND) is verified
    assert calls == ["a.json", "b.json"]


def test_same_path_with_other_hash_is_checked_and_fails(stubbed, tmp_path):
    verified, calls = stubbed
    verified["kept"].append(task("a.json", "h2"))
    with pytest.raises(ValueError, match="verify"):
        merge.verified_input(tmp_path, ROUND)
    assert calls == ["a.json", "b.json", "a.json"]
