"""Detail range and literal field checks, collected by test_middle_ai_first.py.

Run: .venv/Scripts/python.exe -m pytest -q
     services/math-assessment-api/tests/test_middle_ai_first.py
"""

import copy
import json

import pytest
from middle_ai_first_fixtures import ROUND, TEXT, install_documents, pipeline, task
from scripts import middle_ai_first as first
from scripts import middle_ai_read as ai
from scripts.middle_ai_fields import item_slices
from scripts.middle_items import standard_values


def test_verify_fail_closed_and_detail_locator(root):
    _, report = pipeline(root, [task(title="없는 제목"), task()])
    assert report["summary"]["kept"] == report["summary"]["discarded"] == 1
    kept = report["kept"][0]
    assert kept["locator_basis"] == "detail_lines"
    assert kept["locator"] == kept["detail_locator"]
    assert TEXT[kept["locator"]["start"]:kept["locator"]["end"]].endswith("탐구 활동지\n")
    assert report["simulated"] is True and report["run_bindings"]


@pytest.mark.parametrize("detail", [{"line_start": 3, "line_end": 7},
                                    {"line_start": 2, "line_end": 99}, "bad"])
def test_bad_detail_is_dropped_without_discarding_task(root, detail):
    _, report = pipeline(root, [task(detail_lines=detail)])
    kept = report["kept"][0]
    assert kept["detail_locator"] is None
    assert kept["detail_discarded"]["reason"]
    assert kept["methods_verified"] == []


def test_detail_can_link_by_title_text_without_overlapping_evidence(root):
    text = TEXT + "온도 관찰 보고서 평가요소 채점기준\n실습\n"
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    _, report = pipeline(root, [task(detail_lines={"line_start": 8, "line_end": 9},
                                      methods=[{"text": "실습", "line": 9}])])
    assert report["kept"][0]["locator_basis"] == "detail_lines"
    assert report["kept"][0]["methods_verified"][0]["text"] == "실습"


def test_detail_can_link_by_declared_evidence_line_range(root):
    item = task(detail_lines={"line_start": 3, "line_end": 7}, evidence=[
        {"line_start": 2, "line_end": 7, "quote": "온도 관찰 보고서"}])
    _, report = pipeline(root, [item])
    assert report["kept"][0]["locator_basis"] == "detail_lines"


def test_methods_literal_scope_scorers_and_check_state(root):
    methods = [{"text": text, "line": line} for text, line in [
        ("교사 관찰 및 기록", 5), ("모둠", 6), ("없는 실습", 7), ("발표", 4),
        ("실험", 4), ("탐구 활동지", 7), ("탐구  활동지", 7), ("온도 관찰 보고서", 1)]]
    _, report = pipeline(root, [task(methods=methods)])
    kept = report["kept"][0]
    assert [m["text"] for m in kept["methods_verified"]] == ["실험", "탐구 활동지"]
    assert len(kept["methods_discarded"]) == 6
    for entry in kept["methods_verified"]:
        loc = entry["locator"]
        assert TEXT[loc["start"]:loc["end"]] == entry["text"]


def test_methods_inside_evidence_without_detail(root):
    item = task(detail_lines=None, evidence=[{"line_start": 2, "line_end": 7,
                                            "quote": "온도 관찰 보고서"}])
    _, report = pipeline(root, [item])
    assert report["kept"][0]["methods_verified"][0]["text"] == "실험"


def test_deduplicate_unions_detail_and_methods(root):
    a = task(detail_lines={"line_start": 2, "line_end": 5})
    b = task(methods=[{"text": "탐구 활동지", "line": 7}])
    _, report = pipeline(root, [a, b])
    assert len(report["kept"]) == 1
    kept = report["kept"][0]
    assert len(kept["detail_locators"]) == 2
    assert kept["detail_locator"]["end"] == len(TEXT)
    assert {m["text"] for m in kept["methods_verified"]} == {"실험", "탐구 활동지"}


@pytest.mark.parametrize("erase_neighbor_title", [False, True])
def test_detail_rejects_neighbor_title_and_accepts_erased_mutation(root, erase_neighbor_title):
    neighbor = "소리 탐구 보고서"
    text = TEXT + f"{neighbor}\n실습\n[9과05-01]~[9과05-04]\n{neighbor}\n"
    if erase_neighbor_title:
        text = text.replace(neighbor, "지워진 이웃 제목", 1)
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    entry = task(detail_lines={"line_start": 2, "line_end": 10}, evidence=[
        {"line_start": 2, "line_end": 4, "quote": "온도 관찰 보고서"}],
        methods=[{"text": "실험", "line": 4}, {"text": "실습", "line": 9}])
    line = 11 if erase_neighbor_title else 8
    peer = task(title=neighbor, title_line=line, detail_lines=None, methods=[], evidence=[
        {"line_start": line, "line_end": line, "quote": neighbor}])
    _, report = pipeline(root, [entry, peer])
    assert len(report["kept"]) == 2
    kept = report["kept"][0]
    if erase_neighbor_title:
        assert kept["locator_basis"] == "detail_lines"
        assert kept["detail_locator"] is not None
        assert len(kept["methods_verified"]) == 2
        assert len(kept["standards_from_detail"]["value"]) == 4
    else:
        assert kept["detail_locator"] is None and kept["detail_locators"] == []
        assert kept["detail_discarded"]["reason"] == "세부표 범위에 다른 과제 제목"
        assert kept["locator_basis"] == "detail_evidence"
        assert kept["locator"] == kept["title_locator"]
        assert [m["text"] for m in kept["methods_verified"]] == ["실험"]
        assert kept["methods_discarded"][0]["value"]["text"] == "실습"
        assert kept["standards_from_detail"] == {"value": [], "occurrences": []}
        first.merge_targets(root, ROUND)
        assert first.fill_methods(root, ROUND)["changed_standards"] == 0


def test_detail_validation_runs_after_duplicate_ranges_are_unioned(root):
    text = TEXT + "소리 탐구 보고서\n실습\n온도 관찰 보고서\n채점기준\n"
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    overview = task(seen_in="overview")
    detail = task(title_line=10, detail_lines={"line_start": 10, "line_end": 11},
                  methods=[], evidence=[{"line_start": 10, "line_end": 10,
                                         "quote": "온도 관찰 보고서"}])
    peer = task(title="소리 탐구 보고서", title_line=8, detail_lines=None, methods=[],
                evidence=[{"line_start": 8, "line_end": 8, "quote": "소리 탐구 보고서"}])
    _, report = pipeline(root, [overview, detail, peer])
    assert len(report["kept"]) == 2
    kept = report["kept"][0]
    assert kept["seen_in"] == "both"
    assert kept["detail_locator"] is None
    assert kept["detail_discarded"]["reason"] == "세부표 범위에 다른 과제 제목"
    assert kept["detail_discarded"]["value"]["end"] == len(text)


def test_detail_accepts_other_occurrence_with_same_title_key(root):
    alias = "온도관찰보고서!"
    install_documents(root, [("science", "과학 평가계획.hwp", TEXT + alias + "\n")])
    peer = task(title=alias, title_line=8, detail_lines=None, methods=[], evidence=[
        {"line_start": 8, "line_end": 8, "quote": alias}])
    _, report = pipeline(root, [task(detail_lines={"line_start": 2, "line_end": 8}), peer])
    assert len(report["kept"]) == 2
    assert report["kept"][0]["detail_locator"] is not None


@pytest.mark.parametrize("key, value", [
    ("document_id", "other"), ("child_id", "other"), ("grade", 2), ("semester", 2),
])
def test_detail_neighbor_check_requires_same_document_and_scope(root, key, value):
    _, report = pipeline(root, [task()])
    kept = report["kept"][0]
    peer = {**copy.deepcopy(kept), "title": "다른 과제", key: value}
    conversions = {kept["converted_path"]: {"text": TEXT}}
    first.finalize_details([kept, peer], conversions)
    assert kept["detail_locator"] is not None
    assert peer["detail_locator"] is not None


def coded_pipeline(root):
    text = TEXT + "[9과05-01]~[9과05-04] [9과99-99]\n[9과06-01]\n"
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    output, report = pipeline(root, [task(detail_lines={"line_start": 2, "line_end": 8})])
    return text, output, report


def test_detail_standards_expand_validate_locate_and_repeat(root):
    text, output, report = coded_pipeline(root)
    kept = report["kept"][0]
    standards = kept["standards_from_detail"]
    assert standards["value"] == [f"[9과05-{number:02}]" for number in range(1, 5)]
    detail = kept["detail_locator"]
    expected = standard_values([{"raw": text[detail["start"]:detail["end"]], "locator": detail}])
    assert standards == {key: expected[key] for key in ("value", "occurrences")}
    assert standards["occurrences"][1]["expanded"] == []
    for occurrence in standards["occurrences"]:
        loc = occurrence["locator"]
        assert detail["start"] <= loc["start"] < loc["end"] <= detail["end"]
        assert text[loc["start"]:loc["end"]] == occurrence["raw"]
    before = (output / "verified.json").read_bytes()
    assert first.verify_targets(root, ROUND) == report
    assert (output / "verified.json").read_bytes() == before


@pytest.mark.parametrize("method_present", [False, True])
def test_methods_command_fills_standards_preserves_existing_values_and_repeats(
    root, monkeypatch, capsys, method_present,
):
    text, _, verified = coded_pipeline(root)
    first.merge_targets(root, ROUND)
    path = root / f"data/derived/items_ai/{ROUND}.json"
    report = ai.read_json(path)
    base = report["items"][0]
    if method_present:
        base["fields"]["method"]["value"] = ["보고서"]
    for origin in ("rule", "ai"):
        item = copy.deepcopy(base)
        item["item_id"] = origin
        item["fields"]["method"]["value"] = ["보고서"]
        item["fields"]["standards"].update(value=["[9과01-01]"], fill_method=origin)
        report["items"].append(item)
    report["ai_first_matches"][verified["kept"][0]["ai_task_id"]] = [
        i["item_id"] for i in report["items"]]
    ai.save_json(path, report)
    before, raw = copy.deepcopy(report), ai.read_text(path)
    monkeypatch.setattr(first, "ROOT", root)
    first.main(["methods", "--round-key", ROUND])
    assert json.loads(capsys.readouterr().out) == {
        "round": ROUND, "changed_items": 1,
        "changed_methods": int(not method_present), "changed_standards": 1}
    after = ai.read_json(path)
    standards = after["items"][0]["fields"]["standards"]
    assert standards["value"] == verified["kept"][0]["standards_from_detail"]["value"]
    assert standards["status"] == "present"
    assert standards["fill_method"] == "ai_first_detail_code"
    for entry in standards["evidence"]:
        loc = entry["locator"]
        assert text[loc["start"]:loc["end"]] == entry["raw"]
        assert entry["owner_item_id"] == base["item_id"]
    assert [raw[s:e] for _, s, e in item_slices(raw)][1:] == [
        ai.read_text(path)[s:e] for _, s, e in item_slices(ai.read_text(path))][1:]
    after["items"][0]["fields"] = before["items"][0]["fields"]
    assert after == before
    raw = path.read_bytes()
    assert first.fill_methods(root, ROUND) == {
        "round": ROUND, "changed_items": 0, "changed_methods": 0, "changed_standards": 0}
    assert path.read_bytes() == raw


