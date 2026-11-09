"""Synthetic offline source ownership and S6e-3 pipeline regressions."""

import json
import shutil
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from scripts import middle_ai_fields as f
from scripts import middle_ai_read as ai

PROJECT = Path(__file__).resolve().parents[3]
ROUND = "synthetic-dev"


@pytest.fixture
def directory(monkeypatch):
    parent = PROJECT / ".tmp/s6e3-tests"
    path = parent / uuid4().hex
    path.mkdir(parents=True)

    def forbidden(*args, **kwargs):
        pytest.fail("No real subprocess or network in S6e-3 tests")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    yield path
    assert path.resolve().is_relative_to(parent.resolve())
    shutil.rmtree(path)


def column_text(merged=False, group=True):
    methods = ('<td colspan="2">프로젝트</td>' if merged
               else "<td>실험</td><td>발표</td>")
    return ("과학 1학년 1학기\n<table>\n"
            + ('<tr><th>평가유형</th><th colspan="2">수행평가</th></tr>\n' if group else "")
            + '<tr><td>평가 영역</td><td>온도 측정하기</td><td>생태 지도 만들기</td></tr>\n'
            + f"<tr><td>평가 방법</td>{methods}</tr>\n"
            + '<tr><td>평가시기</td><td>5월</td><td>6월</td></tr>\n'
            + '<tr><td>성취기준</td><td>[9과01-01]</td><td>[9과02-01]</td></tr>\n'
            + '<tr><td>만점</td><td>100점</td><td>80점</td></tr>\n'
            + "</table>\n")


def setup_source(text=None, titles=("온도 측정하기", "생태 지도 만들기")):
    text = text or column_text()
    conversion = {"text": text, "converter": "synthetic"}
    target = {"target_id": "window", "document_id": "doc", "round": ROUND,
              "line_start": 1, "line_end": len(text.splitlines()),
              "converted_path": "conversion.json", "text_sha256": ai.sha(text)}
    section = {"document_id": "doc", "segment_id": "segment", "section_id": "section",
               "grade": 1, "semester": 1, "status": "target", "science_candidate": True,
               "boundary_verified": True, "locator": {"start": 0, "end": len(text)}}
    known = []
    for number, title in enumerate(titles):
        start = text.index(title)
        loc = ai.text_locator(start, start + len(title), conversion)
        fields = {name: {"value": [], "status": "unconfirmed", "reason": NO_REASON,
                         "evidence": []} for name in f.items.FIELDS}
        fields["title"] = {"value": title, "status": "present", "reason": "",
                           "evidence": [{"raw": title, "text": title, "locator": loc}]}
        known.append({"item_id": f"task-{number}", "document_id": "doc", "child_id": None,
                      "grade": 1, "semester": 1, "fields": fields, "locator": loc,
                      "owned_ranges": [loc], "extraction_status": "ai_verified",
                      "extraction_method": "ai_read", "public_eligible": False,
                      "candidate_role": "performance",
                      "target_ids": ["window"], "school": "가상학교", "school_code": "school"})
    tables, structures = f.structures_for(conversion, section)
    return conversion, target, section, known, tables, structures


NO_REASON = "AI 읽기 1단계: 필드 미추출"


def answer(text, quote, value, status="present"):
    lo = text[:text.index(quote)].count("\n") + 1
    return {"status": status, "value": value,
            "evidence": [{"line_start": lo, "line_end": lo, "quote": quote}]}


def verify(source, name, quote, value, index=0):
    conversion, target, _, known, tables, structures = source
    return f.verify_field(known[index], name, answer(conversion["text"], quote, value),
                          target, conversion, tables, structures, known)


@pytest.mark.parametrize("group", [True, False])
def test_same_column_and_neighbor_rejection(group):
    source = setup_source(column_text(group=group))
    field, _ = verify(source, "method", "실험", ["실험"])
    assert field["evidence"][0]["ai_alignment"] == "same_column"
    assert field["fill_method"] == "ai_read"
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "발표", ["발표"])


def test_repeated_quote_resolved_only_by_source_column():
    source = setup_source(column_text().replace("<td>발표</td>", "<td>실험</td>"))
    first, _ = verify(source, "method", "실험", ["실험"])
    second, _ = verify(source, "method", "실험", ["실험"], 1)
    assert first["evidence"][0]["locator"]["col"] == 1
    assert second["evidence"][0]["locator"]["col"] == 2


def test_shared_span_and_collision_rejection():
    source = setup_source(column_text(merged=True))
    entries = []
    for index in (0, 1):
        field, cells = verify(source, "method", "프로젝트", ["프로젝트"], index)
        assert field["evidence"][0]["ai_alignment"] == "shared_span"
        entries.append({"item_id": f"task-{index}", "field": field, "cells": cells})
    assert all(e["field"] for e in f.reject_collisions(entries))
    for entry in entries:
        entry["cells"] = [("doc", 1, 9, "same_column")]
    assert all(e["field"] is None for e in f.reject_collisions(entries))


def test_wrong_owner_claim_invalidates_legitimate_cell_too():
    source = setup_source()
    field, cells = verify(source, "method", "실험", ["실험"])
    with pytest.raises(ValueError) as failure:
        verify(source, "method", "실험", ["실험"], 1)
    entries = [{"item_id": "task-0", "field": field, "cells": cells},
               {"item_id": "task-1", "field": None, "cells": failure.value.cells}]
    assert all(e["field"] is None for e in f.reject_collisions(entries))


def test_row_table_same_row():
    text = ("<table>\n<tr><th>평가 영역</th><th>평가 방법</th><th>만점</th></tr>\n"
            "<tr><td>온도 측정하기</td><td>실험</td><td>100점</td></tr>\n"
            "<tr><td>생태 지도 만들기</td><td>발표</td><td>80점</td></tr>\n</table>")
    source = setup_source(text)
    field, _ = verify(source, "score", "100점", 100)
    assert field["evidence"][0]["ai_alignment"] == "same_row"
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "score", "80점", 80)


def test_detail_own_table_and_foreign_title_rejection():
    text = ("<table>\n<tr><td>수행과제</td><td>온도 측정하기</td></tr>\n"
            "<tr><td>평가 방법</td><td>실험</td></tr>\n"
            "<tr><td>채점기준</td><td>변인을 통제하여 결과를 설명한다</td></tr>\n</table>\n"
            "생태 지도 만들기")
    source = setup_source(text)
    field, _ = verify(source, "rubric", "변인을 통제하여 결과를 설명한다", None)
    assert field["evidence"][0]["ai_alignment"] == "own_table"
    bad = setup_source(text.replace("<td>실험</td>", "<td>생태 지도 만들기</td>"))
    with pytest.raises(ValueError, match="표 위치"):
        verify(bad, "rubric", "변인을 통제하여 결과를 설명한다", None)


def test_prose_requires_exclusive_owned_range():
    source = setup_source("온도 측정하기\n5월 관찰\n생태 지도 만들기\n")
    conversion, _, _, known, _, _ = source
    known[0]["owned_ranges"] = [{"start": 0, "end": conversion["text"].index("생태")}]
    field, _ = verify(source, "timing", "5월 관찰", "5월")
    assert field["evidence"][0]["ai_alignment"] == "prose"
    known[1]["owned_ranges"] = known[0]["owned_ranges"]
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "timing", "5월 관찰", "5월")


@pytest.mark.parametrize(("name", "value", "quote"), [
    ("score", 10, "100점"), ("score", True, "1"), ("weight", 20, "30%"),
    ("standards", ["[9과99-99]"], "[9과99-99]"),
    ("standards", ["[9과1-1]"], "[9과1-1]"),
    ("standards", ["[9과01-01]"], "[9과02-01]"),
    ("method", ["온도 측정하기"], "온도 측정하기"),
    ("method", ["실험"], "발표"), ("task_text", ["만든 문장"], "원문 문장"),
    ("timing", "4월", "5월"), ("assessment_area", "미래", "생태"),
    ("sub_scores", [{"element": "관찰", "score": 5}], "관찰 10점"),
    ("sub_scores", [{"element": "해석", "score": 10}], "관찰 10점"),
])
def test_value_literal_failures(name, value, quote):
    with pytest.raises(ValueError, match="값과 인용"):
        f.check_value(name, value, [quote])


def test_values_and_exact_raw_quote_window():
    source = setup_source()
    field, _ = verify(source, "standards", "[9과01-01]", ["[9과01-01]"])
    assert field["status"] == "present"
    conversion, target, _, known, tables, structures = source
    forged = answer(conversion["text"], "100점", 100)
    forged["evidence"][0]["quote"] = "１００점"
    with pytest.raises(ValueError, match="불일치"):
        f.verify_field(known[0], "score", forged, target, conversion, tables, structures, known)
    target["line_end"] = 1
    with pytest.raises(ValueError, match="범위 밖"):
        verify(source, "score", "100점", 100)


def test_absent_uncertain_and_rubric_location():
    source = setup_source()
    conversion, target, _, known, tables, structures = source
    absent, _ = f.verify_field(known[0], "score", {"status": "absent"}, target,
                               conversion, tables, structures, known)
    assert absent["status"] == "unconfirmed"
    assert absent["reason"] == "AI: 원문에 없다고 답함(미검증)"
    field, cells = verify(source, "rubric", "100점", None)
    entry = {"item_id": "task-0", "name": "rubric", "field": field,
             "reason": "", "cells": cells}
    result = f.apply_entries(known, [entry])
    assert result[0]["field_locations"]["rubric"] == [field["evidence"][0]["locator"]]
    known[0]["fields"]["free_semester"] = {
        "value": True, "status": "present", "reason": "", "evidence": [],
        "reference_evidence": [{"raw": "자유학기", "locator": known[0]["locator"]}]}
    free = f.apply_entries(known, [])
    assert all(free[0]["fields"][n]["status"] == "source_absent"
               and free[0]["fields"][n]["fill_method"] == "rule_reuse"
               for n in ("score", "weight", "sub_scores"))


def test_rule_reuse_unique_and_ambiguous_structure():
    conversion, _, section, known, _, structures = setup_source()
    columns = [s for s in structures if s["layout"] == "column"]
    filled, detail = f.rule_fill(known[0], conversion, section, columns)
    assert detail["matches"] == 1
    assert filled["fields"]["score"]["value"] == 100
    assert filled["fields"]["score"]["fill_method"] == "rule_reuse"
    assert filled["fields"]["score"]["evidence"][0]["owner_item_id"] == known[0]["item_id"]
    ambiguous, detail = f.rule_fill(known[0], conversion, section, columns + columns)
    assert detail["matches"] == 2
    assert ambiguous["fields"]["score"]["status"] == "unconfirmed"


def test_merge_exact_rule_bytes_relations_and_set_guard():
    _, _, _, known, _, _ = setup_source()
    rule = {"item_id": "rule", "extraction_status": "bounded", "fields": {"value": "그대로"}}
    raw = json.dumps({"items": [rule, *known], "ai_relations": {"new": ["task-0"]}},
                     ensure_ascii=False, indent=3)
    merged = f.merge_text(raw, known)
    before = next(raw[s:e] for i, s, e in f.item_slices(raw) if i["item_id"] == "rule")
    after = next(merged[s:e] for i, s, e in f.item_slices(merged) if i["item_id"] == "rule")
    assert before.encode() == after.encode()
    assert json.loads(merged)["ai_relations"] == {"new": ["task-0"]}
    with pytest.raises(ValueError, match="집합"):
        f.merge_text(raw, known[:1])
    with pytest.raises(ValueError, match="집합"):
        f.merge_text(raw, [*known, rule])


def test_shadow_stratification_school_cap():
    candidates = [{"item_id": f"{layout}-{school}-{index}", "layout": layout,
                   "school": str(school)} for layout in ("row", "column", "form")
                  for school in range(15) for index in range(6)]
    selected = f.stratified_sample(candidates, 36, 123)
    assert selected == f.stratified_sample(list(reversed(candidates)), 36, 123)
    assert Counter(i["layout"] for i in selected) == {"row": 12, "column": 12, "form": 12}
    assert max(Counter(i["school"] for i in selected).values()) <= 4


def write_fixture(root, text=None):
    text = text or ("<table>\n<tr><th>평가 영역</th><th>평가 방법</th><th>만점</th></tr>\n"
            "<tr><td>온도 측정하기</td><td>실험</td><td>100점</td></tr>\n"
            "<tr><td>생태 지도 만들기</td><td>발표</td><td>80점</td></tr>\n</table>")
    conversion, target, section, known, _, _ = setup_source(text)
    target["tasks"] = [f.context_item(i, conversion["text"], list(f.ASK_FIELDS)) for i in known]
    document = {"document_id": "doc", "converted_path": "conversion.json",
                "text_sha256": ai.sha(conversion["text"])}
    ai.save_json(root / "conversion.json", conversion)
    ai.save_json(root / f"data/derived/segments/{ROUND}.json", {"documents": [document]})
    ai.save_json(root / f"data/derived/subjects/{ROUND}.json", {"sections": [section]})
    ai.save_json(f.input_path(root, ROUND), {"items": known, "ai_relations": {"new": [1, 2]}})
    source_output = ai.round_dir(root, ROUND)
    ai.write_text(source_output / "targets.jsonl", json.dumps(target) + "\n")
    prompt_dir = root / "scripts/prompts"
    prompt_dir.mkdir(parents=True)
    ai.write_text(prompt_dir / "middle_ai_fields_v1.md", "Synthetic instructions")
    return known


def fake_run(output, target, response, fake=False):
    identity = target["target_id"]
    answer_path = output / f"responses/{identity}.json"
    events = output / f"responses/{identity}.events.jsonl"
    ai.save_json(answer_path, response)
    ai.write_text(events, '{"type":"turn.completed"}\n')
    status = {"valid": True, "fake": fake, "prompt_sha256": target["prompt_sha256"],
              "answer_sha256": ai.sha(ai.read_text(answer_path)),
              "events_sha256": ai.sha(ai.read_text(events))}
    ai.save_json(output / f"responses/{identity}.status.json", status)


def test_pipeline_no_answers_and_merge_backup(directory):
    known = write_fixture(directory)
    f.fields_rule(directory, ROUND)
    f.fields_targets(directory, ROUND)
    f.fields_verify(directory, ROUND)
    original = ai.read_text(f.input_path(directory, ROUND))
    f.fields_merge(directory, ROUND)
    assert ai.read_text(f.input_path(directory, ROUND).with_name(
        f"{ROUND}.prev-s6e3.json")) == original
    result = ai.read_json(f.input_path(directory, ROUND))
    assert [i["item_id"] for i in result["items"]] == [i["item_id"] for i in known]
    assert result["ai_relations"] == {"new": [1, 2]}
    assert result["items"][0]["fields"]["score"]["fill_method"] == "rule_reuse"
    assert all(fld["reason"] != NO_REASON for i in result["items"] for fld in i["fields"].values())


def test_audit_hash_resumption_with_existing_runner(directory, monkeypatch):
    write_fixture(directory)
    f.fields_rule(directory, ROUND)
    f.fields_targets(directory, ROUND)
    output = f.directory(directory, ROUND)
    target = ai.load_targets(output)[0]
    fake_run(output, target, {"tasks": [], "uncertain": []})
    assert ai.valid_run(output, target)[0]
    monkeypatch.setattr(ai, "isolated_directory", lambda path: path)
    result = f.dispatch(directory, SimpleNamespace(
        command="fields-run", round_key=ROUND, isolated_cwd=directory,
        workers=4, fake_responses=directory, dry_run=False, shadow=False))
    assert result["skipped"] == 1
    prompt = output / f"prompts/{target['target_id']}.md"
    ai.write_text(prompt, ai.read_text(prompt) + "changed")
    assert not ai.valid_run(output, target)[0]
    f.fields_targets(directory, ROUND)
    events = output / f"responses/{target['target_id']}.events.jsonl"
    ai.write_text(events, '{"type":"item.completed","item":{"type":"command_execution"}}\n'
                  '{"type":"turn.completed"}\n')
    assert not ai.valid_run(output, target)[0]
    report = f.fields_verify(directory, ROUND)
    assert any("감사" in reason for c in report["fields"].values() for reason in c["discarded"])


def test_stale_input_and_stage_guard(directory):
    write_fixture(directory)
    f.fields_rule(directory, ROUND)
    f.fields_targets(directory, ROUND)
    f.fields_verify(directory, ROUND)
    output = f.directory(directory, ROUND)
    ai.write_text(output / "rule.json", ai.read_text(output / "rule.json") + " ")
    with pytest.raises(ValueError, match="규칙 결과"):
        f.fields_merge(directory, ROUND)


def test_gold_cli_guard_without_opening_sources(directory):
    with pytest.raises(ValueError):
        f.dispatch(directory, SimpleNamespace(command="fields-rule", round_key="synthetic-gold"))


def test_real_entry_points_ai_fields_and_rubric_merge(directory):
    write_fixture(directory, column_text(group=False))
    f.fields_rule(directory, ROUND)
    f.fields_targets(directory, ROUND)
    output = f.directory(directory, ROUND)
    target = ai.load_targets(output)[0]
    text = ai.read_json(directory / "conversion.json")["text"]
    response = {"tasks": [{"item_id": "task-0", "fields": {
        "score": answer(text, "100점", 100),
        "rubric": answer(text, "5월", None),
        "standards": answer(text, "[9과01-01]", ["[9과99-99]"]),
        "weight": {"status": "absent"}}}], "uncertain": []}
    fake_run(output, target, response, fake=True)
    summary = f.fields_verify(directory, ROUND)
    assert summary["fields"]["score"]["ai_read"] == 1
    assert summary["simulated"] is True
    f.fields_merge(directory, ROUND)
    merged = ai.read_json(f.input_path(directory, ROUND))
    item = merged["items"][0]
    assert item["fields"]["score"]["value"] == 100
    # The cited cell now supplies the value even when the AI gives a wrong code.
    assert item["fields"]["standards"]["value"] == ["[9과01-01]"]
    assert item["fields"]["standards"]["ai_value_mismatch"]["ai_value"] == ["[9과99-99]"]
    assert item["fields"]["weight"]["reason"] == "AI: 원문에 없다고 답함(미검증)"
    assert item["field_locations"]["rubric"]
    assert item["fields"]["rubric"]["evidence"][0]["ai_alignment"] == "same_column"
    # A new staged pass preserves the original backup and replaces the summary.
    backup = f.input_path(directory, ROUND).with_name(f"{ROUND}.prev-s6e3.json")
    original_backup = backup.read_bytes()
    f.fields_rule(directory, ROUND)
    f.fields_targets(directory, ROUND)
    f.fields_verify(directory, ROUND)
    f.fields_merge(directory, ROUND)
    assert backup.read_bytes() == original_backup


def test_repeated_title_block_does_not_borrow_same_column():
    text = column_text(group=False).replace(
        "</table>", "<tr><td>평가 영역</td><td>다른 활동</td><td>또 다른 활동</td></tr>\n"
        "<tr><td>평가 방법</td><td>관찰</td><td>보고서</td></tr>\n</table>")
    with pytest.raises(ValueError, match="표 위치"):
        verify(setup_source(text), "method", "관찰", ["관찰"])


def test_field_locations_are_not_written_for_rejected_rubric():
    source = setup_source()
    _, _, _, known, _, _ = source
    result = f.apply_entries(known, [{"item_id": "task-0", "name": "rubric", "field": None,
                                     "reason": f.ALIGNMENT_FAILURE}])
    assert result[0]["field_locations"]["rubric"] == []


def test_shadow_generation_masks_rule_fields_and_reports_every_discard(directory, monkeypatch):
    known = write_fixture(directory)
    monkeypatch.setattr(ai, "DEV_ROUNDS", (ROUND,))
    conversion = ai.read_json(directory / "conversion.json")
    for item in known:
        item.update(extraction_status="bounded", subject_status="target", layout="row",
                    segment_id="segment", section_id="section",
                    boundary_evidence={"section_locator": {
                        "start": 0, "end": len(conversion["text"])}})
        item["fields"]["score"] = {"value": 100, "status": "present", "reason": "",
                                     "evidence": []}
    ai.save_json(directory / f"data/derived/items/{ROUND}.json", {"items": known})
    summary = f.fields_shadow(directory, ROUND, sample=2, seed=5)
    assert summary["items"] == 2
    output = f.directory(directory, ROUND, True)
    target = ai.load_targets(output)[0]
    prompt = ai.read_text(output / f"prompts/{target['target_id']}.md")
    payload = json.loads(prompt.splitlines()[2])
    assert all("fields" not in t for t in payload["tasks"])
    assert all(t["requested_fields"] == list(f.ASK_FIELDS) for t in target["tasks"])
    assert all(all(o["item_id"] != t["item_id"] for o in t["other_tasks"])
               for t in target["tasks"])
    fake_run(output, target, {"tasks": [{"item_id": "task-0", "fields": {
        "score": answer(conversion["text"], "80점", 80)}}], "uncertain": []})
    report = f.fields_verify(directory, ROUND, shadow=True)
    assert report["counts"]["score"]["버림"] == 1
    comparison = ai.read_json(f.directory(directory, ROUND) / "shadow-comparison.json")
    assert comparison["rule_is_gold"] is False
    discarded = next(d for d in comparison["differences"] if d["category"] == "버림")
    assert discarded["quote"] == ["80점"]
    assert any(d["category"] == "규칙만" for d in comparison["differences"])


def test_linked_detail_rubric_and_rule_reuse():
    text = ("<table>\n<tr><td>수행과제</td><td>온도 측정하기</td></tr>\n"
            "<tr><td>평가 방법</td><td>실험</td></tr>\n</table>\n"
            "<table>\n<tr><th>채점기준</th><th>배점</th></tr>\n"
            "<tr><td>변인을 통제하여 결과를 설명한다</td><td>10</td></tr>\n</table>\n"
            "생태 지도 만들기")
    source = setup_source(text)
    field, _ = verify(source, "rubric", "변인을 통제하여 결과를 설명한다", None)
    assert field["evidence"][0]["ai_alignment"] == "own_table"
    conversion, _, section, known, _, structures = source
    enriched, _ = f.rule_fill(known[0], conversion, section, structures)
    assert enriched["fields"]["method"]["fill_method"] == "rule_reuse"
    # The original form rule requires its own criterion/scale grammar.
    assert enriched["fields"]["rubric"]["status"] == "unconfirmed"


def test_shared_rowspan():
    text = ("<table>\n<tr><th>평가 영역</th><th>평가 방법</th><th>만점</th></tr>\n"
            '<tr><td>온도 측정하기</td><td rowspan="2">실험</td><td>100점</td></tr>\n'
            "<tr><td>생태 지도 만들기</td><td>80점</td></tr>\n</table>")
    source = setup_source(text)
    for index in (0, 1):
        field, _ = verify(source, "method", "실험", ["실험"], index)
        assert field["evidence"][0]["ai_alignment"] == "shared_span"


def test_sub_scores_retain_owned_evidence():
    source = setup_source(column_text().replace("100점", "관찰 10점"))
    field, _ = verify(source, "sub_scores", "관찰 10점", [{"element": "관찰", "score": 10}])
    assert field["value"][0]["evidence"][0]["owner_item_id"] == "task-0"
    assert field["value"][0]["evidence"][0]["ai_alignment"] == "same_column"


def test_source_change_and_invalid_output_directory(directory, monkeypatch):
    write_fixture(directory)
    f.fields_rule(directory, ROUND)
    f.fields_targets(directory, ROUND)
    conversion = ai.read_json(directory / "conversion.json")
    conversion["text"] += "changed"
    ai.save_json(directory / "conversion.json", conversion)
    with pytest.raises(ValueError, match="해시"):
        f.fields_verify(directory, ROUND)
    monkeypatch.setattr(ai, "isolated_directory", lambda path: path)
    with pytest.raises(ValueError, match="해당 회차"):
        ai.run_targets(directory, ROUND, directory, output_dir=directory)


def test_rule_reuse_partial_section_with_table_header_outside():
    text = ("<table>\n<tr><th>평가 영역</th><th>평가 방법</th><th>만점</th></tr>\n"
            "<tr><td>온도 측정하기</td><td>실험</td><td>100점</td></tr>\n"
            "<tr><td>생태 지도 만들기</td><td>발표</td><td>80점</td></tr>\n</table>")
    conversion, _, section, known, _, _ = setup_source(text)
    section["locator"] = {"start": text.index("<tr><td>온도"),
                          "end": text.index("<tr><td>생태")}
    enriched, detail = f.rule_fill(known[0], conversion, section)
    assert detail["matches"] == 1
    assert enriched["fields"]["score"]["fill_method"] == "rule_reuse"
    assert enriched["fields"]["score"]["value"] == 100


@pytest.mark.parametrize("row_layout", [False, True])
def test_geometry_without_rule_structures_and_structure_gate(row_layout):
    text = ("<table>\n<tr><th>평가 영역</th><th>평가 방법</th><th>만점</th></tr>\n"
            "<tr><td>온도 측정하기</td><td>실험</td><td>100점</td></tr>\n"
            "<tr><td>생태 지도 만들기</td><td>발표</td><td>80점</td></tr>\n</table>"
            if row_layout else column_text())
    conversion, target, section, known, tables, _ = setup_source(text)
    for table in tables:
        table["structure_verified"] = False
    source = conversion, target, section, known, tables, []
    field, _ = verify(source, "method", "실험", ["실험"])
    assert field["evidence"][0]["ai_alignment"] == ("same_row" if row_layout else "same_column")
    assert field["value_source"] == "rule_from_cell"
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "발표", ["발표"])
    if not row_layout:
        first, _ = verify(source, "assessment_area", "온도 측정하기", "온도 측정하기")
        assert first["evidence"][0]["locator"]["col"] == 1


def test_inconsistent_grid_is_rejected_even_when_structure_gate_passes():
    source = setup_source(column_text().replace("<td>80점</td>", ""))
    assert source[4][0]["structure_verified"]
    assert not f.consistent_grid(source[4][0])
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "실험", ["실험"])


def test_neighboring_detail_continuation_only_one_table_without_foreign_titles():
    detail = ("<table>\n<tr><td>수행과제</td><td>온도 측정하기</td></tr>\n"
              "<tr><td>평가 방법</td><td>실험</td></tr>\n</table>\n")
    continuation = ("<table>\n<tr><td>채점기준</td><td>변인을 통제한다</td></tr>\n</table>\n")
    source = setup_source(detail + continuation + continuation.replace("통제한다", "설명한다")
                          + "생태 지도 만들기")
    field, _ = verify(source, "rubric", "변인을 통제한다", None)
    assert field["evidence"][0]["ai_alignment"] == "own_table"
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "rubric", "변인을 설명한다", None)
    for changed in (continuation.replace("채점기준", "생태 지도 만들기"),
                    continuation.replace("채점기준", "평가 과제")):
        bad = setup_source(detail + changed + "생태 지도 만들기")
        with pytest.raises(ValueError, match="표 위치"):
            verify(bad, "rubric", "변인을 통제한다", None)


def test_cell_values_override_ai_and_expand_ranges():
    source = setup_source(column_text().replace("[9과01-01]", "[9과01-01]~[9과01-03]"))
    score, _ = verify(source, "score", "100점", 10)
    assert score["value"] == 100
    assert score["value_source"] == "rule_from_cell"
    assert score["ai_value_mismatch"] == {"code_value": 100, "ai_value": 10}
    standards, _ = verify(source, "standards", "[9과01-01]~[9과01-03]",
                          ["[9과01-01]", "[9과01-03]"])
    assert standards["value"] == ["[9과01-01]", "[9과01-02]", "[9과01-03]"]
    assert standards["ai_value_mismatch"]["code_value"] == standards["value"]
    # Selecting only the numeric token still reads the entire chosen cell.
    partial, _ = verify(source, "score", "100", 10)
    assert partial["value"] == 100
    malformed_ai, _ = verify(source, "score", "100점", [True, 1, {"bad": "shape"}])
    assert malformed_ai["value"] == 100
    assert malformed_ai["ai_value_mismatch"]["ai_value"] == [True, 1, {"bad": "shape"}]


def test_method_text_numeric_and_allocation_normalization():
    source = setup_source(column_text().replace("<td>실험</td>", "<td>서‧논술형 평가</td>"))
    method, _ = verify(source, "method", "서‧논술형 평가", ["서·논술형평가"])
    assert method["value"] == ["서‧논술형 평가"]
    assert "ai_value_mismatch" not in method
    source = setup_source(column_text().replace("100점", "관찰(10점)"))
    allocation, _ = verify(source, "sub_scores", "관찰(10점)", [{"element": "관찰", "score": 5}])
    assert allocation["value_source"] == "rule_from_cell"
    assert allocation["value"][0]["score"] == 10
    assert f.comparable(["서‧논술형 평가<br> "]) == f.comparable("서·논술형평가")
    assert f.comparable(10) == f.comparable(10.0)
    f.check_value("score", 10, ["10.0점"])
    fallback, _ = verify(setup_source(column_text().replace("100점", "관찰 10점")),
                          "sub_scores", "관찰 10점", [{"element": "관찰", "score": 10}])
    assert fallback["value_source"] == "ai_literal"
    multiline_text = ("<table>\n<tr><td>수행과제</td><td>온도 측정하기</td></tr>\n"
                      "<tr><td>평가요소</td><td>배점</td></tr>\n"
                      "<tr><td>관찰<br>기록(10점)</td><td>10</td></tr>\n</table>\n생태 지도 만들기")
    multiline, _ = verify(setup_source(multiline_text),
                           "sub_scores", "관찰<br>기록(10점)",
                           [{"element": "관찰<br>기록", "score": 10}])
    assert multiline["value_source"] == "ai_literal"
    assert multiline["value"][0]["element"] == "관찰<br>기록"


def test_rubric_comparison_uses_overlapping_locations():
    def field(start, end, value):
        return {"value": value, "status": "present", "reason": "",
                "evidence": [{"locator": {"start": start, "end": end},
                              "raw": value, "ai_alignment": "own_table"}]}
    assert f.rubric_overlap(field(10, 20, "규칙"), field(19, 30, "다른 문자열"))
    assert not f.rubric_overlap(field(10, 20, "같음"), field(20, 30, "같음"))


def test_mutation_function_rejects_neighbor_columns_and_rows():
    for text in (column_text(),
                 "<table>\n<tr><th>평가 영역</th><th>평가 방법</th></tr>\n"
                 "<tr><td>온도 측정하기</td><td>실험</td></tr>\n"
                 "<tr><td>생태 지도 만들기</td><td>발표</td></tr>\n</table>"):
        source = setup_source(text)
        conversion, _, _, known, tables, structures = source
        field, _ = verify(source, "method", "실험", ["실험"])
        results = f.mutate_cell_claims(known[0], field["evidence"][0]["locator"], tables,
                                       structures, known, conversion["text"])
        assert results and all(not r["accepted"] for r in results)


def test_repeated_verification_after_merge_preserves_saved_targets(directory):
    write_fixture(directory)
    f.fields_rule(directory, ROUND)
    f.fields_targets(directory, ROUND)
    output = f.directory(directory, ROUND)
    targets = (output / "targets.jsonl").read_bytes()
    for _ in range(2):
        f.fields_verify(directory, ROUND)
        f.fields_merge(directory, ROUND)
    assert (output / "targets.jsonl").read_bytes() == targets
    raw = ai.read_json(f.input_path(directory, ROUND))
    raw["ai_relations"] = {"changed": True}
    ai.save_json(f.input_path(directory, ROUND), raw)
    with pytest.raises(ValueError, match="입력 변경"):
        f.fields_verify(directory, ROUND)


def test_overview_geometry_can_use_repeated_literal_title():
    overview = column_text()
    detail = ("<table>\n<tr><td>수행 과제</td><td>온도 측정하기</td></tr>\n"
              "<tr><td>평가 방법</td><td>관찰</td></tr>\n</table>")
    source = setup_source(overview + detail)
    text = source[0]["text"]
    loc = {"start": text.rindex("온도 측정하기"),
           "end": text.rindex("온도 측정하기") + len("온도 측정하기")}
    source[3][0]["fields"]["title"]["evidence"][0]["locator"] = loc
    field, _ = verify(source, "method", "실험", ["실험"])
    assert field["evidence"][0]["ai_alignment"] == "same_column"


def test_ambiguous_axes_and_unknown_neighbor_candidates_are_rejected():
    text = ("<table>\n<tr><td>평가 영역</td><td>평가 과제</td><td>평가 방법</td></tr>\n"
            "<tr><td>평가 영역</td><td>온도 측정하기</td><td>생태 지도 만들기</td></tr>\n"
            "<tr><td>평가 방법</td><td>실험</td><td>발표</td></tr>\n</table>")
    source = setup_source(text)
    assert f.literal_orientation(source[4][0], source[4][0]["rows"][1][1]) is None
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "실험", ["실험"])
    # A discovered task's absence from the known list never licenses its column.
    source = setup_source(column_text(), titles=("온도 측정하기",))
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "발표", ["발표"])


def test_compound_numeric_cells_use_rule_units():
    source = setup_source(column_text().replace("<td>만점</td>", "<td>만점(반영비율)</td>")
                          .replace("100점", "100점 (20%)"))
    score, _ = verify(source, "score", "100점 (20%)", 10)
    weight, _ = verify(source, "weight", "100점 (20%)", 10)
    assert score["value"] == 100 and weight["value"] == 20
    assert score["value_source"] == weight["value_source"] == "rule_from_cell"


def test_mutation_command_writes_both_offline_reports(directory):
    known = write_fixture(directory, column_text())
    source = setup_source(column_text())
    field, cells = verify(source, "method", "실험", ["실험"])
    ai.save_json(directory / f"data/derived/items/{ROUND}.json", {"items": known})
    report = {"items": known, "entries": [{"item_id": "task-0", "name": "method",
                                           "target_id": "window", "field": field, "cells": cells}]}
    for shadow in (False, True):
        ai.save_json(f.directory(directory, ROUND, shadow) / "verified.json", report)
    args = SimpleNamespace(command="fields-mutation-check", round_key=ROUND)
    result = f.dispatch(directory, args)
    assert result["calls"] == result["neighbor_accepted"] == 0
    assert result["mutations"] == result["rejected"] == 2
    assert (f.directory(directory, ROUND) / "mutation-check.md").exists()


@pytest.mark.parametrize("separator", ["<br>", "<BR />", "\n"])
def test_method_list_preserves_printed_breaks(separator):
    raw = f"구술, 발표 평가{separator}포트폴리오 평가"
    source = setup_source(column_text().replace("<td>실험</td>", f"<td>{raw}</td>"))
    response = answer(source[0]["text"], raw, ["구술, 발표 평가", "포트폴리오 평가"])
    response["evidence"][0]["line_end"] += raw.count("\n")
    field, _ = f.verify_field(source[3][0], "method", response, source[1], source[0],
                              source[4], source[5], source[3])
    assert field["value"] == ["구술, 발표 평가", "포트폴리오 평가"]
    assert all(f.rules.method_literal(v) for v in field["value"])
    assert "ai_value_mismatch" not in field


def test_task_list_uses_each_partial_citation_and_keeps_sentence_wrap():
    quotes = ["입자의 운동을 모형<br>으로 나타내기", "관찰 결과 설명하기"]
    raw = "평가 안내<br>" + "<br>".join(quotes) + "<br>각 10점"
    source = setup_source(column_text().replace("<td>실험</td>", f"<td>{raw}</td>"))
    response = {"status": "present", "value": quotes,
                "evidence": [answer(source[0]["text"], q, [])['evidence'][0] for q in quotes]}
    field, _ = f.verify_field(source[3][0], "task_text", response, source[1], source[0],
                              source[4], source[5], source[3])
    assert field["value"] == ["입자의 운동을 모형 으로 나타내기", "관찰 결과 설명하기"]
    assert len(field["evidence"]) == 2
    assert all(e["raw"] in quotes for e in field["evidence"])


def test_standards_breaks_keep_individual_codes_and_range_expansion():
    raw = "[9과01-01]<br>[9과01-02]~[9과01-03]"
    source = setup_source(column_text().replace("[9과01-01]", raw))
    field, _ = verify(source, "standards", raw, ["[9과01-01]"])
    assert field["value"] == ["[9과01-01]", "[9과01-02]", "[9과01-03]"]


def detail_text(value="실험"):
    return ("<table>\n<tr><td>수행과제</td><td>온도 측정하기</td></tr>\n"
            f"<tr><td>평가 방법</td><td>{value}</td></tr>\n"
            "<tr><td>만점</td><td>100점</td></tr>\n</table>\n생태 지도 만들기")


@pytest.mark.parametrize("status", ["candidate", "unconfirmed"])
def test_foreign_title_requires_confirmed_task(status):
    source = setup_source(detail_text("생태 지도 만들기"))
    source[3][1]["extraction_status"] = status
    field, _ = verify(source, "score", "100점", 100)
    assert field["status"] == "present"
    source[3][1].update(extraction_status="bounded", extraction_method="rule")
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "score", "100점", 100)


def test_foreign_title_matches_whole_cell_only():
    source = setup_source(detail_text("실험 생태 지도 만들기 결과"))
    assert verify(source, "score", "100점", 100)[0]["status"] == "present"


@pytest.mark.parametrize("role", ["summary_duplicate", "area_only"])
def test_foreign_title_requires_confirmed_rule_performance_role(role):
    source = setup_source(detail_text("생태 지도 만들기"))
    source[3][1].update(extraction_status="bounded", extraction_method="rule",
                        candidate_role=role)
    assert verify(source, "score", "100점", 100)[0]["status"] == "present"


@pytest.mark.parametrize("other", ["온도 측정", "온도 측정하기 보고서", "온도 측정하기"])
def test_foreign_title_excludes_own_title_containment(other):
    source = setup_source(detail_text(other), titles=("온도 측정하기",))
    candidate = json.loads(json.dumps(source[3][0]))
    candidate["item_id"] = "alias-task"
    candidate["fields"]["title"]["value"] = other
    source[3].append(candidate)
    assert verify(source, "score", "100점", 100)[0]["status"] == "present"


def test_foreign_title_excludes_label_cells():
    source = setup_source(detail_text(), titles=("온도 측정하기",))
    candidate = json.loads(json.dumps(source[3][0]))
    candidate["item_id"] = "label-task"
    candidate["fields"]["title"]["value"] = "평가 방법"
    source[3].append(candidate)
    assert verify(source, "score", "100점", 100)[0]["status"] == "present"


def block_text():
    return ("<table>\n<tr><td>수행과제</td><td>온도 측정하기</td></tr>\n"
            "<tr><td>평가 방법</td><td>실험</td></tr>\n"
            "<tr><td>만점</td><td>100점</td></tr>\n"
            "<tr><td>수행과제</td><td>생태 지도 만들기</td></tr>\n"
            "<tr><td>평가 방법</td><td>발표</td></tr>\n"
            "<tr><td>만점</td><td>80점</td></tr>\n</table>")


@pytest.mark.parametrize("known_neighbor", [True, False])
def test_own_block_stops_at_next_title_label_and_mutates_neighbor(known_neighbor):
    source = setup_source(block_text(), titles=("온도 측정하기", "생태 지도 만들기")
                          if known_neighbor else ("온도 측정하기",))
    field, _ = verify(source, "method", "실험", ["실험"])
    assert field["evidence"][0]["ai_alignment"] == "own_block"
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "발표", ["발표"])
    results = f.mutate_cell_claims(source[3][0], field["evidence"][0]["locator"],
                                   source[4], source[5], source[3], source[0]["text"])
    assert len(results) == 3
    assert all(r["kind"] == "neighbor_block" and not r["accepted"] for r in results)


def test_own_block_uses_known_unlabelled_title_and_rejects_cross_boundary_span():
    text = block_text().replace("<td>수행과제</td><td>생태 지도 만들기</td>",
                                '<td colspan="2">생태 지도 만들기</td>')
    source = setup_source(text)
    field, _ = verify(source, "method", "실험", ["실험"])
    assert field["evidence"][0]["ai_alignment"] == "own_block"
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "score", "80점", 80)
    table = source[4][0]
    cell = next(c for c in table["cells"] if c["raw"] == "100점")
    cell["rowspan"] = 2
    assert not f.own_block(table, cell, source[3][0], source[3][1:])


def test_ambiguous_duplicate_block_title_is_rejected():
    source = setup_source(block_text().replace("생태 지도 만들기", "온도 측정하기"),
                          titles=("온도 측정하기",))
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "실험", ["실험"])


def test_ambiguous_unlabelled_duplicate_block_title_is_rejected():
    text = block_text().replace("생태 지도 만들기", "온도 측정하기").replace(
        "<td>수행과제</td><td>온도 측정하기</td>", '<td colspan="2">온도 측정하기</td>')
    source = setup_source(text, titles=("온도 측정하기",))
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "실험", ["실험"])


def test_block_cannot_fall_back_to_whole_table_for_unknown_next_task():
    text = block_text().replace("<td>수행과제</td><td>온도 측정하기</td>",
                                '<td colspan="2">온도 측정하기</td>')
    source = setup_source(text, titles=("온도 측정하기",))
    assert verify(source, "method", "실험", ["실험"])[0]["evidence"][0][
        "ai_alignment"] == "own_block"
    with pytest.raises(ValueError, match="표 위치"):
        verify(source, "method", "발표", ["발표"])


def test_empty_trailing_rowspan_clips_without_moving_data_cells():
    text = ("<table>\n<tr><td>수행과제</td><td>온도 측정하기</td>"
            '<td rowspan="2"></td></tr>\n'
            '<tr><td>평가 방법</td><td colspan="2">실험</td></tr>\n</table>')
    source = setup_source(text, titles=("온도 측정하기",))
    assert f.consistent_grid(source[4][0])
    field, _ = verify(source, "method", "실험", ["실험"])
    assert field["evidence"][0]["locator"]["col"] == 1
    bad = setup_source(text.replace('rowspan="2"></td>', 'rowspan="2">메모</td>'),
                       titles=("온도 측정하기",))
    assert not f.consistent_grid(bad[4][0])
    with pytest.raises(ValueError, match="표 위치"):
        verify(bad, "method", "실험", ["실험"])


def test_form_title_label_with_value_is_not_a_row_header():
    text = ("<table>\n<tr><td>평가 영역</td><td>관찰 영역</td>"
            "<td>시기</td><td>5월</td></tr>\n"
            '<tr><td colspan="4">온도 측정하기</td></tr>\n</table>')
    source = setup_source(text, titles=("온도 측정하기",))
    field, _ = verify(source, "timing", "5월", "5월")
    assert field["evidence"][0]["ai_alignment"] == "own_table"
