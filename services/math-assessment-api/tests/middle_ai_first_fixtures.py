"""Shared synthetic AI-first fixtures and builders; all writes use tmp_path.

Run: .venv/Scripts/python.exe -m pytest -q
     services/math-assessment-api/tests/test_middle_ai_first.py
"""

import copy
import json
from pathlib import Path

import pytest
from scripts import middle_ai_first as first
from scripts import middle_ai_read as ai

ROUND = "synthetic-first"
PROJECT = Path(__file__).resolve().parents[3]
TEXT = ("1학년 1학기\n온도 관찰 보고서\n평가요소 채점기준\n"
        "■ 실험 □ 발표\n교사 관찰 및 기록\n모둠\n탐구 활동지\n")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("AI-first tests must never invoke AI or the network")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(ai, "isolated_directory", lambda path: path)
    monkeypatch.delenv(ai.GOLD_MEASUREMENT_ENV, raising=False)


@pytest.fixture
def root(tmp_path):
    template = ai.read_text(PROJECT / "scripts/prompts/middle_ai_first_v1.md")
    ai.write_text(tmp_path / "scripts/prompts/middle_ai_first_v1.md", template)
    install_documents(tmp_path, [("science", "과학 평가계획.hwp", TEXT)])
    return tmp_path


def install_documents(root, specifications, *, sections=None, grades=None):
    documents = []
    for identity, filename, text in specifications:
        path = f"data/derived/conversions/{identity}.json"
        ai.save_json(root / path, {"text": text, "converter": "synthetic"})
        documents.append({"document_id": identity, "converted_path": path,
                          "text_sha256": ai.sha(text), "grades": grades or [1],
                          "source": {"school_name": "가상중", "school_code": "synthetic-school",
                                     "candidate_name": filename},
                          "segments": [{"grade": 1, "semester": 1}]})
    ai.save_json(root / f"data/derived/segments/{ROUND}.json", {"documents": documents})
    ai.save_json(root / f"data/derived/subjects/{ROUND}.json", {"sections": sections or []})
    ai.save_json(root / f"data/derived/items/{ROUND}.json", {"round": ROUND, "items": []})
    return documents


def task(**changes):
    result = {"grade": 1, "semester": 1, "title": "온도 관찰 보고서", "title_line": 2,
              "evidence": [{"line_start": 2, "line_end": 2, "quote": "온도 관찰 보고서"}],
              "grade_evidence": {"line": 1, "quote": "1학년"},
              "semester_evidence": {"line": 1, "quote": "1학기"},
              "seen_in": "detail", "detail_lines": {"line_start": 2, "line_end": 7},
              "methods": [{"text": "실험", "line": 4}]}
    result.update(changes)
    return result


def fake_responses(root, targets, tasks=None):
    fake = root / "fake"
    for target in targets:
        identity = target["target_id"]
        ai.save_json(fake / f"{identity}.json", {"tasks": tasks or [], "uncertain": []})
        ai.write_text(fake / f"{identity}.events.jsonl", "".join(
            json.dumps({"type": kind}) + "\n" for kind in ("turn.started", "turn.completed")))
    return fake


def pipeline(root, tasks=None):
    first.build_targets(root, ROUND)
    output = ai.round_dir(root, ROUND) / "first"
    targets = ai.load_targets(output)
    fake = fake_responses(root, targets, tasks)
    first.run_targets(root, ROUND, root, fake_responses=fake)
    return output, first.verify_targets(root, ROUND)


def rule_item(verified, identity="rule", status="bounded", title="다른 제목", locator=None):
    item = ai.ai_item(verified)
    item.update(item_id=identity, extraction_status=status,
                locator=copy.deepcopy(locator or verified["locator"]))
    item.pop("extraction_method")
    item["fields"]["title"]["value"] = title
    return item


