"""Offline S19 boundary, method text, roster and display-title regressions.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_s19_merge_method.py
All generated inputs and SQLite catalogs live under tmp_path.
"""

import copy
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import middle_ai_fields as fields
from scripts import middle_ai_read as ai
from scripts.build_science_catalog_db import item_row
from scripts.check_science_method_text import check_database
from scripts.middle_items import method_values, visible
from scripts.middle_rounds import roster_path

ROOT = Path(__file__).resolve().parents[3]
ROUND = "2026-round-1-fresh19"


@pytest.fixture
def merge_inputs(tmp_path):
    title = "금속의 밀도 구하기"
    text = f"과학 2학년 1학기\n{title}\n실험, 보고서"
    conversion = {"text": text, "converter": "kordoc"}
    loc = ai.text_locator(text.index(title), text.index(title) + len(title), conversion)
    task = {
        "ai_task_id": "ai-task", "document_id": "document", "child_id": None,
        "school": "가상중학교", "school_code": "school", "grade": 2, "semester": 1,
        "title": title, "title_raw": title, "converted_path": "conversion.json",
        "text_sha256": ai.sha(text), "title_locator": loc, "locator": loc,
        "locator_basis": "title", "locators": [loc],
        "evidence": [{"raw": title, "text": title, "locator": loc}],
        "seen_in": "detail", "target_ids": ["window"],
        "grade_evidence": {"raw": "2학년"}, "semester_evidence": {"raw": "1학기"},
    }
    rule = ai.ai_item(task)
    rule.update(item_id="rule-item", extraction_status="review", layout="html",
                review_reasons=["별도 표 연결 미확정"])
    rule.pop("extraction_method")
    rules = {"schema_version": 1, "round": ROUND, "items": [rule]}
    verified = {"round": ROUND, "kept": [task], "targets_sha256": ai.sha(""),
                "run_bindings": {}, "simulated": True}
    ai.save_json(tmp_path / "conversion.json", conversion)
    ai.save_json(tmp_path / "rules.json", rules)
    ai.save_json(tmp_path / "verified.json", verified)
    return (json.loads((tmp_path / "rules.json").read_text(encoding="utf-8")),
            json.loads((tmp_path / "verified.json").read_text(encoding="utf-8")))


def test_unbounded_rule_is_preserved_and_ai_boundary_is_added(merge_inputs):
    rules, verified = merge_inputs
    before = copy.deepcopy(rules)
    result = ai.merge_report(rules, verified)
    assert rules == before
    assert result["items"][0] == before["items"][0]
    assert result["items"][0]["extraction_status"] == "review"
    added = result["items"][-1]
    assert added == ai.ai_item(verified["kept"][0])
    assert fields.is_ai(added)
    assert result["ai_relations"]["replaces_unbounded"] == [
        {"ai_task_id": "ai-task", "rule_item_id": "rule-item"}]
    assert result["ai_relations"]["new"][0]["reason"] == "규칙 미확정 항목을 AI가 경계 확정"
    assert result["ai_relations"]["agrees"] == []


@pytest.mark.parametrize("status,reasons,bounded", [
    ("review", ["별도 표 연결 미확정", "변환 손실"], False),
    ("bounded", [], True),
])
def test_conversion_loss_and_existing_bounded_agreement(merge_inputs, status, reasons, bounded):
    rules, verified = merge_inputs
    rules["items"][0].update(extraction_status=status, review_reasons=reasons)
    result = ai.merge_report(rules, verified)
    assert result["items"] == rules["items"]
    assert result["ai_relations"]["replaces_unbounded"] == []
    assert result["ai_relations"]["agrees"] == [
        {"ai_task_id": "ai-task", "rule_item_id": "rule-item", "bounded": bounded}]


@pytest.mark.parametrize("basis", ["same_cell_title_key", "evidence", "school_title"])
def test_unbounded_replacement_still_runs_duplicate_guards(merge_inputs, basis):
    rules, verified = merge_inputs
    twin = copy.deepcopy(rules["items"][0])
    twin.update(item_id="bounded-twin", extraction_status="bounded",
                locator={"start": 1000, "end": 2000})
    if basis == "evidence":
        twin["fields"]["title"]["value"] = "다른 표의 과제명"
        verified["kept"][0]["locators"].append({"start": 1100, "end": 1200})
    elif basis == "school_title":
        twin["document_id"] = "another-document"
    rules["items"].append(twin)
    result = ai.merge_report(rules, verified)
    assert result["items"] == rules["items"]
    assert result["ai_relations"]["new"] == []
    assert result["ai_relations"]["replaces_unbounded"] == []
    relation = "agrees_by_evidence" if basis == "evidence" else "agrees_by_title"
    assert result["ai_relations"][relation][0]["rule_item_ids"] == ["bounded-twin"]


def test_multiple_ai_tasks_do_not_claim_one_unbounded_replacement(merge_inputs):
    rules, verified = merge_inputs
    other = {**verified["kept"][0], "ai_task_id": "another-task", "title": "다른 과제"}
    verified["kept"].append(other)
    result = ai.merge_report(rules, verified)
    assert result["ai_relations"]["replaces_unbounded"] == []
    assert len(result["ai_relations"]["ai_split_suggested"]) == 1


def test_development_geumseong_boundary_replay(tmp_path):
    paths = [ROOT / "data/derived/items/2026-round-1-fresh3.json",
             ROOT / "data/derived/ai_read/2026-round-1-fresh3/verified.json"]
    if not all(path.is_file() for path in paths):
        pytest.skip("fresh3 development inputs are absent")
    for path in paths:
        (tmp_path / path.name).write_bytes(path.read_bytes())
    rules, verified = [json.loads((tmp_path / path.name).read_text(encoding="utf-8"))
                       for path in paths]
    merged = ai.merge_report(rules, verified)
    matches = [item for item in merged["items"] if (
        "금성" in item.get("school", "") and item.get("grade") == 2
        and item.get("semester") == 1 and fields.is_ai(item)
        and item["fields"]["title"]["value"] == "철과 알루미늄의 밀도 구하기")]
    assert len(matches) == 1
    assert any(row["ai_task_id"] == matches[0]["item_id"]
               for row in merged["ai_relations"]["replaces_unbounded"])


METHOD_CASES = [
    ("☑교사 관찰 및 기록", [], ["교사 관찰 및 기록"]),
    ("■개별수행", [], ["개별수행"]),
    ("실험, 보고서, 모둠, 개별", ["실험, 보고서"], ["모둠", "개별"]),
    ("모둠/개별평가", [], ["모둠", "개별평가"]),
    ("관찰⋅기록", [], ["관찰⋅기록"]),
    ("조사·관찰 보고서", ["조사·관찰 보고서"], []),
    ("관찰", ["관찰"], []),
    ("관찰 평가", ["관찰 평가"], []),
    ("☑실험, 보고서, 모둠, 개별", ["실험, 보고서"], ["모둠", "개별"]),
    ("개인별 수행，조별평가、개인", [], ["개인별 수행", "조별평가", "개인"]),
    ("실험/모둠/보고서", ["실험/보고서"], ["모둠"]),
    ("실험，모둠、보고서", ["실험、보고서"], ["모둠"]),
    ("☑조사·관찰 보고서", ["조사·관찰 보고서"], []),
    ("☑관찰", ["관찰"], []),
]
METHOD_CASES.extend((f"{subject} {action}", [], [f"{subject} {action}"])
                    for subject in ("교사", "자기", "동료", "상호")
                    for action in ("관찰", "평가", "관찰 및 기록", "관찰 평가"))
METHOD_CASES.extend((f"관찰{separator}기록", [], [f"관찰{separator}기록"])
                    for separator in (" 및 ", "·", "⋅", "･", "ㆍ", "・", "‧", "•", " "))
METHOD_CASES.extend((form + suffix, [], [form + suffix])
                    for form in ("개별", "개인별", "개인", "모둠", "모둠별", "조별")
                    for suffix in ("", "수행", "평가"))


@pytest.mark.parametrize("raw,expected,scorers", METHOD_CASES)
def test_rule_and_ai_paths_share_method_filter(tmp_path, raw, expected, scorers):
    observations = [{"raw": raw, "text": visible(raw), "locator": {
        "start": 0, "end": len(raw), "offset_unit": "unicode_codepoint", "end_exclusive": True}}]
    ai.save_json(tmp_path / "observations.json", observations)
    saved = json.loads((tmp_path / "observations.json").read_text(encoding="utf-8"))
    result = method_values(copy.deepcopy(saved))
    assert result["value"] == expected
    assert result["scorer_values"] == scorers
    assert fields.value_from_cells("method", saved, [], {}) == expected
    if expected:
        fields.check_value("method", expected, [raw])
    else:
        with pytest.raises(ValueError, match="인용 대조"):
            fields.check_value("method", [visible(raw).lstrip("☑■")], [raw])


def test_plain_method_with_only_scorer_checkboxes_is_retained(tmp_path):
    observations = [{"raw": raw, "text": visible(raw), "locator": {"start": 0, "end": len(raw)}}
                    for raw in ("실험·실습", "☑ 교사 관찰 및 기록 □ 자기평가 □ 동료평가")]
    ai.save_json(tmp_path / "observations.json", observations)
    result = fields.value_from_cells("method", observations, [], {})
    assert result == ["실험·실습"]
    with pytest.raises(ValueError):
        fields.check_value("method", ["실험·실습", "교사 관찰 및 기록"],
                           [obs["raw"] for obs in observations])


@pytest.mark.parametrize("raw", ["☑교사 관찰 및 기록", "모둠/개별평가", "□실험 ☑모둠"])
def test_ai_verify_does_not_restore_removed_method(tmp_path, merge_inputs, raw):
    task = merge_inputs[1]["kept"][0]
    title = task["title"]
    text = (f"<table>\n<tr><td>수행 과제</td><td>{title}</td></tr>\n"
            f"<tr><td>평가 방법</td><td>{raw}</td></tr>\n</table>")
    conversion = {"text": text, "converter": "kordoc"}
    ai.save_json(tmp_path / "verify-conversion.json", conversion)
    section = {"locator": {"start": 0, "end": len(text)}}
    tables, structures = fields.structures_for(conversion, section)
    loc = ai.text_locator(text.index(title), text.index(title) + len(title), conversion)
    item = ai.ai_item({**task, "title_locator": loc, "locator": loc, "locators": [loc]})
    target = {"line_start": 1, "line_end": 4}
    answer = {"status": "present", "value": ["교사 관찰 및 기록"],
              "evidence": [{"quote": raw, "line_start": 3, "line_end": 3}]}
    field, _ = fields.verify_field(item, "method", answer, target, conversion,
                                   tables, structures, [item])
    assert field["value"] == []
    assert field["status"] == "unconfirmed"


def catalog_record(item, text):
    return {"item": item, "text": text, "source_round": ROUND,
            "document": {"sha256": "source-sha"},
            "axes": {"unit": {"status": "undetermined"},
                     "activity": {"abstain_reason": "미확정"}}}


@pytest.mark.parametrize("raw,expected", [
    ("·동물세포 관찰", "동물세포 관찰"), ("Ÿ 물속에서", "물속에서"),
    ("-과학적 탐구 보고서", "과학적 탐구 보고서"), ("·", "·"),
])
def test_display_title_only_strips_leading_symbols(merge_inputs, raw, expected):
    task = {**merge_inputs[1]["kept"][0], "title": raw, "title_raw": raw}
    item = ai.ai_item(task)
    record = catalog_record(item, " " * item["locator"]["end"])
    row = item_row(record, 0)
    assert row["title"] == expected
    assert row["title_raw"] == raw
    item["fields"]["title"]["value"] = expected
    expected_row = item_row(record, 0)
    assert {k: v for k, v in row.items() if k not in {"title", "title_raw"}} == {
        k: v for k, v in expected_row.items() if k not in {"title", "title_raw"}}


def test_replacement_uses_normal_ai_field_and_database_paths(tmp_path, merge_inputs):
    result = ai.merge_report(*merge_inputs)
    item = result["items"][-1]
    raw = "실험, 보고서, 모둠, 개별"
    observations = [{"raw": raw, "text": raw, "locator": {"start": 0, "end": len(raw)}}]
    item["fields"]["method"]["value"] = fields.value_from_cells("method", observations, [], {})
    row = item_row(catalog_record(item, " " * item["locator"]["end"]), 0)
    assert fields.is_ai(item)
    assert row["source_item_id"] == item["item_id"]
    assert row["source_extraction_status"] == "ai_verified"
    assert row["extraction_status"] == "bounded"
    assert row["method"] == "실험, 보고서"
    ai.save_json(tmp_path / "row.json", {k: v for k, v in row.items() if not isinstance(v, bytes)})


@pytest.mark.parametrize("suffix,filename", [
    ("fresh3", "middle-fresh3.csv"), ("fresh19", "middle-fresh19.csv"),
    ("fresh001", "middle-fresh001.csv"), ("dev2", "middle-dev2-20.csv"),
    ("other", "middle-dev12.csv"),
])
def test_fresh_roster_round_generalization(tmp_path, suffix, filename):
    assert roster_path(tmp_path, f"2026-round-1-{suffix}") == tmp_path / "data/rosters" / filename
    assert roster_path(tmp_path, f"2026-round-1-{suffix}", Path("custom.csv")) == (
        tmp_path / "custom.csv")


@pytest.mark.parametrize("method,count", [
    ("교사 관찰 및 기록", 1), ("관찰⋅기록", 1), ("모둠", 1), ("실험, 보고서", 0),
])
def test_method_text_checker_cli_and_rows(tmp_path, method, count):
    database = tmp_path / "catalog.sqlite"
    with sqlite3.connect(database) as conn:
        conn.executescript("""
            CREATE TABLE cases (case_id TEXT PRIMARY KEY, school_name TEXT);
            CREATE TABLE assessment_items (
                item_id TEXT PRIMARY KEY, case_id TEXT, source_round TEXT,
                title TEXT, method TEXT, extraction_status TEXT);
            INSERT INTO cases VALUES ('case', '가상중학교');
        """)
        conn.execute("INSERT INTO assessment_items VALUES (?, ?, ?, ?, ?, ?)",
                     ("item", "case", ROUND, "탐구 과제", method, "bounded"))
        conn.execute("INSERT INTO assessment_items VALUES (?, ?, ?, ?, ?, ?)",
                     ("review", "case", ROUND, "검토 과제", "개별", "review"))
    report = check_database(database)
    assert report["count"] == count
    assert report["items"] == ([{"item_id": "item", "source_round": ROUND,
                                 "school_name": "가상중학교", "title": "탐구 과제",
                                 "method": method}] if count else [])
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_science_method_text.py"),
                             "--database", str(database), "--output", "json"],
                            capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == count
    assert json.loads(result.stdout) == report
