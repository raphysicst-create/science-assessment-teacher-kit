"""활동 라벨 검사기·비교기 단위 테스트(가짜 자료, 정답 세트 파일은 쓰지 않는다).

Run: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_gold_activity.py
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from scripts import gold_activity_diff as diff
from scripts import gold_activity_validate as val

PROJECT = Path(__file__).resolve().parents[3]
VERSION = "activity-def-v1"


@pytest.fixture
def directory():
    path = PROJECT / ".tmp/activity-tests" / uuid4().hex
    path.mkdir(parents=True)
    yield path
    for child in path.iterdir():
        child.unlink()
    path.rmdir()


def write_jsonl(path: Path, records):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                    encoding="utf-8", newline="\n")


ITEMS = [
    {"item_key": "ms-gold-busan-city-g1-s1-01", "school_id": "ms-gold-busan-city", "grade": 1,
     "semester": 1, "representative_title": {"raw": "밀도 구하기"},
     "occurrences": [{"doc_id": "abcdef012345", "line": 10}]},
    {"item_key": "ms-gold-busan-city-g1-s1-02", "school_id": "ms-gold-busan-city", "grade": 1,
     "semester": 1, "representative_title": {"raw": "과학 글쓰기"},
     "occurrences": [{"doc_id": "abcdef012345", "line_start": 20, "line_end": 25}]},
]


def label(key, primary, secondary=(), **extra):
    record = {"item_key": key, "definition_version": VERSION, "primary": primary,
              "secondary": list(secondary),
              "evidence": [{"type": "checkbox", "quote": "☑ 실험·실습",
                            "loc": {"doc_id": "abcdef012345", "line": 10}}]}
    record.update(extra)
    return record


def test_validate_accepts_complete_labels(directory):
    items = directory / "items.jsonl"
    labels = directory / "a.jsonl"
    write_jsonl(items, ITEMS)
    write_jsonl(labels, [label(ITEMS[0]["item_key"], "계산·측정", ["실험평가"]),
                         label(ITEMS[1]["item_key"], None, ["작성"], abstain_reason="근거 동률",
                               evidence=[])])
    report = val.validate(labels, items, expect_version=VERSION)
    assert report["errors"] == []
    assert report["primary_counts"] == {"계산·측정": 1, "(기권)": 1}


def test_validate_reports_each_violation(directory):
    items = directory / "items.jsonl"
    labels = directory / "b.jsonl"
    write_jsonl(items, ITEMS)
    bad = label(ITEMS[0]["item_key"], "없는활동", ["계산·측정", "계산·측정"], extra_key=1)
    bad["evidence"][0]["loc"] = {"doc_id": "ffffffffffff", "line": 1, "line_start": 1}
    write_jsonl(labels, [bad, label(ITEMS[0]["item_key"], None),
                         {**label("ms-gold-x-city-g1-s1-99", "탐구"),
                          "definition_version": "activity-def-v2"}])
    joined = "\n".join(val.validate(labels, items, expect_version=VERSION)["errors"])
    for needle in ("primary 값 오류", "secondary 중복", "허용되지 않은 키", "2번 중복", "라벨 없음",
                   "묶음에 없는 항목", "definition_version이 하나가 아님", "abstain_reason",
                   "원문 문서가 아님", "line 하나 또는"):
        assert needle in joined, needle


def test_diff_counts_agreement_and_lists_disagreements(directory):
    items = {i["item_key"]: i for i in ITEMS}
    a = {ITEMS[0]["item_key"]: label(ITEMS[0]["item_key"], "계산·측정", ["실험평가"]),
         ITEMS[1]["item_key"]: label(ITEMS[1]["item_key"], "작성", ["추론·설명"])}
    b = {ITEMS[0]["item_key"]: label(ITEMS[0]["item_key"], "계산·측정", ["실험평가"]),
         ITEMS[1]["item_key"]: label(ITEMS[1]["item_key"], None, ["작성", "추론·설명"],
                                     abstain_reason="근거 동률")}
    report = diff.compare(a, b, items)
    assert report["primary_agree"] == 1 and report["primary_disagreements"] == 1
    assert report["rows"][0]["item_key"] == ITEMS[1]["item_key"]
    assert report["rows"][0]["B_primary"] == "(기권)"
    out = directory / "dis"
    diff.write_outputs(report, out, "a", "b")
    assert (directory / "dis.csv").exists() and "과학 글쓰기" in (
        directory / "dis.md"
    ).read_text(encoding="utf-8")
    (directory / "dis.json").unlink()
