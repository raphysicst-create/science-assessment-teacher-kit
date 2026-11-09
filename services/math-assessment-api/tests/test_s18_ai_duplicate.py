"""Offline S18 T3 merge regressions using saved-format inputs under tmp_path.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_s18_ai_duplicate.py
"""

import copy

import pytest
from scripts import middle_ai_read as ai

ROUND = "2026-round-1-dev2"
DOCUMENT = "doc_94d7c057f33831367dc8294e9c2b994e57a6303abb2e76ffcf7f08a8881f50f3"
# Titles, scope and disjoint source positions from the three T3 development cases.
CASES = (
    ("첨단 과학기술 활용 사례조사하기", "첨단 과학기술 활용 사례 조사하기",
     100504, 100521, 104958, 106881, 45),
    ("우리 학교 생태 지도 만들기", "우리 학교 생태 지도만들기",
     100530, 100545, 106955, 108805, 46),
    ("다양한 액체의 비열 측정하기", "다양한 액체의 비열 측정하기",
     100554, 100569, 108866, 110817, 47),
)


@pytest.fixture
def merge_inputs(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("S18 merge tests must never invoke Codex or the network")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    converted_path = "source.json"
    text_chars = [" "] * CASES[-1][5]
    for title, rule_title, start, end, rule_start, _, _ in CASES:
        text_chars[start:end] = title
        text_chars[rule_start:rule_start + len(rule_title)] = rule_title
    text = "".join(text_chars)
    ai.save_json(tmp_path / converted_path, {"text": text, "converter": "kordoc"})
    tasks, items = [], []
    for index, (title, rule_title, start, end, rule_start, rule_end, table) in enumerate(CASES):
        locator = {"start": start, "end": end, "offset_unit": "unicode_codepoint",
                   "end_exclusive": True, "converter": "kordoc", "text_field": "text"}
        task = {
            "ai_task_id": f"ai-{index}", "document_id": DOCUMENT, "child_id": None,
            "grade": 1, "semester": 1, "title": title, "title_raw": title,
            "converted_path": converted_path, "text_sha256": ai.sha(text),
            "title_locator": locator, "locator": locator, "locator_basis": "title",
            "locators": [locator], "evidence": [{"quote": title, "locator": locator}],
            "seen_in": "overview", "target_ids": ["summary-window"],
            "grade_evidence": "metadata", "semester_evidence": "metadata",
        }
        item = ai.ai_item(task)
        item.update(item_id=f"rule-{index}", extraction_status="bounded", layout="html",
                    locator={**locator, "start": rule_start, "end": rule_end},
                    layout_position={"table": table, "row": None, "col": None})
        item["fields"]["title"]["value"] = rule_title
        item.pop("extraction_method")
        tasks.append(task)
        items.append(item)
    rules = {"schema_version": 1, "round": ROUND, "items": items}
    verified = {"round": ROUND, "kept": tasks, "targets_sha256": ai.sha(""),
                "run_bindings": {}, "simulated": True}
    ai.write_text(ai.round_dir(tmp_path, ROUND) / "targets.jsonl", "")
    return tmp_path, rules, verified


def merge_saved_inputs(inputs):
    root, rules, verified = inputs
    ai.save_json(root / f"data/derived/items/{ROUND}.json", rules)
    ai.save_json(ai.round_dir(root, ROUND) / "verified.json", verified)
    return ai.merge_targets(root, ROUND)


def test_ai_read_merge_suppresses_three_t3_twins(merge_inputs):
    _, rules, _ = merge_inputs
    before = copy.deepcopy(rules)
    merged = merge_saved_inputs(merge_inputs)
    assert merged["items"] == before["items"]
    assert rules == before
    assert merged["ai_read_summary"]["added_items"] == 0
    assert merged["ai_read_summary"]["relations"]["agrees_by_title"] == 3
    assert merged["ai_relations"]["agrees_by_title"] == [
        {"ai_task_id": f"ai-{index}", "rule_item_ids": [f"rule-{index}"],
         "bounded": True, "basis": "same_cell_title_key"} for index in range(3)
    ]


@pytest.mark.parametrize("change", [
    {"title": "새로운 탐구 과제"}, {"semester": 2}, {"grade": 2},
    {"document_id": "other-document"}, {"child_id": "other-zip-child"},
])
def test_ai_read_merge_keeps_changed_title_or_scope(merge_inputs, change):
    merge_inputs[2]["kept"][0].update(change)
    merged = merge_saved_inputs(merge_inputs)
    assert merged["ai_read_summary"]["added_items"] == 1
    assert merged["ai_read_summary"]["relations"]["agrees_by_title"] == 2
    assert merged["items"][-1]["item_id"] == "ai-0"


@pytest.mark.parametrize("change", [
    {"candidate_role": "other"}, {"extraction_status": "review"},
    {"grade": None}, {"semester": None},
])
def test_ai_read_merge_requires_bounded_performance_and_exact_scope(merge_inputs, change):
    merge_inputs[1]["items"][0].update(change)
    merged = merge_saved_inputs(merge_inputs)
    assert merged["ai_read_summary"]["added_items"] == 1
    assert merged["ai_read_summary"]["relations"]["agrees_by_title"] == 2


def test_ai_read_title_match_precedes_overview_hold(merge_inputs):
    for record in [*merge_inputs[1]["items"], *merge_inputs[2]["kept"]]:
        record["school_code"] = "8761213"
    merged = merge_saved_inputs(merge_inputs)
    assert merged["ai_read_summary"]["relations"]["agrees_by_title"] == 3
    assert merged["ai_relations"]["overview_only_held"] == []


@pytest.mark.parametrize("left,right", [
    ("Task — A，Ｂ!", "taskaＢ"), ("탐구<br /> 보고서", "탐구보고서"),
    ("탐구\u00a0‘보고서’", "탐구보고서"),
])
def test_ai_read_title_key_ignores_case_spacing_breaks_and_punctuation(left, right):
    assert ai.title_key(left) == ai.title_key(right)


def test_ai_read_empty_title_key_is_not_a_match():
    task = {"document_id": "doc", "grade": 1, "semester": 1, "title": "— !"}
    item = {**task, "extraction_status": "bounded", "fields": {"title": {"value": ""}}}
    assert ai.same_cell_title_matches([item], task) == []
