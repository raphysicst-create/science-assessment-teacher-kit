"""Synthetic, offline gap selection and source-location regressions."""

import copy
import json

import pytest
import test_middle_s6e1 as baseline
from scripts import middle_ai_read as ai
from test_middle_s6e1 import (
    ROUND,
    install_source,
    rule_item,
    source,
    verified_tasks,
)

directory = baseline.directory


def section(text, start=0, end=None, **changes):
    return {"document_id": "synthetic-document", "section_id": "science-section",
            "science_candidate": True, "grade": 1, "semester": 1, "status": "target",
            "locator": {"start": start, "end": len(text) if end is None else end}, **changes}


def candidate(start=0, end=1, **changes):
    return {"item_id": "synthetic-item", "document_id": "synthetic-document",
            "school": "가상중학교", "grade": 1, "semester": 1,
            "section_id": "science-section", "candidate_role": "performance",
            "table_role": "detail", "extraction_status": "bounded",
            "fields": {"title": {"value": "합성 과제"}},
            "locator": {"start": start, "end": end}, **changes}


def windows(text, sections, items=(), school_items=None, grades=(1,)):
    document = {"grades": list(grades), "segments": [{"semester": 1}]}
    return ai.gap_windows(text, "과학 평가계획.hwp", document, sections, list(items),
                          list(items if school_items is None else school_items))


@pytest.mark.parametrize("positive", [True, False])
def test_g1_requires_subject_marker(positive):
    text = "과학\n평가계획\n" if positive else "과학적 사고력을 기른다.\n"
    # Grade 1 keeps the document in scope; grade-3-only plans are skipped on purpose.
    result = windows(text, [], grades=(1,))
    assert bool(result) == positive
    if positive:
        assert "G1" in result[0]["signals"]


@pytest.mark.parametrize("positive", [True, False])
def test_g2_empty_cell_and_school_wide_bounded(positive):
    text = "과학\n합성 과제\n"
    bounded = candidate(document_id="another-document")
    result = windows(text, [section(text)], school_items=[] if positive else [bounded])
    assert bool(result) == positive
    if positive:
        assert result[0]["signals"] == ["G2"]
        assert result[0]["signal_evidence"][0]["grade"] == 1


def test_g2_unknown_grade_and_missing_grade_section_use_document():
    text = "표지\n과학\n합성 과제\n"
    result = windows(text, [], grades=())
    evidence = result[0]["signal_evidence"]
    assert {e.get("grade") for e in evidence if e["signal"] == "G2"} == {1, 2}
    assert result[0]["line_start"] == 1 and result[0]["line_end"] == 3
    result = windows(text, [section(text, start=3, grade=3)], grades=(1, 3))
    assert result[0]["line_start"] == 1


def test_g2_skips_document_with_only_other_grade_or_term():
    text = "과학\n합성 과제\n"
    assert not windows(text, [section(text, grade=3)], grades=(3,))
    document = {"grades": [1], "segments": [{"semester": 2}]}
    assert not ai.gap_windows(text, "과학.hwp", document, [section(text)], [], [candidate()])


@pytest.mark.parametrize("positive", [True, False])
def test_g3_unconfirmed_performance_only(positive):
    text = "과학\n합성 과제\n"
    item = candidate(extraction_status="review" if positive else "bounded")
    result = windows(text, [section(text)], [item], school_items=[candidate()])
    assert bool(result) == positive
    if positive:
        assert result[0]["signals"] == ["G3"]
        assert result[0]["signal_evidence"][0]["item_id"] == item["item_id"]


def test_g3_large_science_section_uses_120_context_lines():
    lines = ["본문 " * 30 + "\n"] * 1000
    text = "".join(lines)
    start = len("".join(lines[:499]))
    item = candidate(start, start + len(lines[499]), extraction_status="unconfirmed")
    result = windows(text, [section(text)], [item], school_items=[candidate()])
    assert (result[0]["line_start"], result[0]["line_end"]) == (380, 620)


@pytest.mark.parametrize("positive", [True, False])
def test_g4_summary_must_link_to_bounded_detail(positive):
    text = "과학\n합성 과제\n"
    summary = candidate(candidate_role="summary_duplicate", table_role="summary",
                        identity_relation={"detail_item_id": "detail"})
    detail = candidate(item_id="detail", extraction_status="review" if positive else "bounded")
    result = windows(text, [section(text)], [summary, detail], school_items=[candidate()])
    assert ("G4" in {s for w in result for s in w["signals"]}) == positive
    if not positive:
        assert not result


def test_g4_blank_summary_and_bounded_only_sections_are_not_gaps():
    text = "過程\n" * 400
    blank = candidate(candidate_role="summary", table_role="summary", fields={"title": {}})
    assert not windows(text, [section(text)], [blank], school_items=[candidate()])
    split = len(text) // 2
    sections = [section(text, end=split),
                section(text, start=split, section_id="review-section")]
    bounded = candidate()
    review = candidate(split, split + 1, item_id="review", section_id="review-section",
                       extraction_status="review")
    result = windows(text, sections, [bounded, review])
    assert len(result) == 1 and result[0]["line_start"] == 201


def test_merge_adjacent_windows_and_split_with_original_overlap():
    entries = [{"line_start": lo, "line_end": hi, "signals": [signal],
                "signal_evidence": [{"signal": signal}]}
               for lo, hi, signal in [(1, 10, "G1"), (31, 40, "G3"), (62, 70, "G4")]]
    merged = ai.merge_signal_windows(entries)
    assert len(merged) == 2
    assert merged[0]["signals"] == ["G1", "G3"]
    assert len(merged[0]["signal_evidence"]) == 2
    lines = ["x" * 999 + "\n"] * 150
    chunks = ai.split_window(lines, 1, 150)
    assert all(sum(map(len, lines[lo - 1:hi])) <= ai.MAX_CHARS for lo, hi in chunks)
    assert all((a[1] - b[0] + 1) * 1000 >= ai.OVERLAP
               for a, b in zip(chunks, chunks[1:], strict=False))


def test_title_locator_prefers_detail_and_dedup_preserves_all_owned_ranges():
    text = ("1학년 1학기\n| 개요 | 과제 |\n| --- | --- |\n| 합성 과제 | 20 |\n\n"
            "| 수행 과제 | 채점 기준 |\n| --- | --- |\n| 합성 과제 | 관찰 |\n")
    conversion, target, task = source(text)
    task.update(title="합성 과제", title_line=4, seen_in="both", evidence=[
        {"line_start": 4, "line_end": 4, "quote": "합성 과제"},
        {"line_start": 8, "line_end": 8, "quote": "합성 과제"}])
    verified = ai.verify_task(task, target, conversion)
    assert verified["locator"]["start"] == text.rindex("합성 과제")
    assert verified["locator_basis"] == "detail_evidence"
    overview = copy.deepcopy(verified)
    overview.update(locator=verified["locators"][0], locator_basis="title_evidence")
    combined = ai.deduplicate([overview, verified])[0]
    item = ai.ai_item(combined)
    assert item["locator"] == verified["locator"]
    assert len(item["owned_ranges"]) == 2
    assert item["locator"]["start"] > item["owned_ranges"][0]["end"]


def test_title_locator_cited_range_contains_title_even_if_quote_is_other_text():
    conversion, target, task = source()
    task["evidence"] = [{"line_start": 2, "line_end": 3, "quote": "수행평가 실험"}]
    verified = ai.verify_task(task, target, conversion)
    assert ai.overlaps(verified["locator"], verified["title_locator"])
    assert len(ai.ai_item(verified)["owned_ranges"]) == 1


@pytest.mark.parametrize("keys", [("grade",), ("semester",), ("grade", "semester")])
def test_none_scope_merge_marks_wildcard_without_mutating_rules(keys):
    _, _, tasks = verified_tasks()
    item = rule_item(tasks[0])
    for key in keys:
        item[key] = None
    rules = {"items": [item]}
    before = copy.deepcopy(rules)
    result = ai.merge_report(rules, {"kept": tasks})
    assert rules == before and result["items"][0] == item
    relation = result["ai_relations"]["agrees"][0]
    assert relation["scope_wildcards"] == [{"rule_item_id": item["item_id"], "fields": list(keys)}]
    assert len(result["ai_relations"]["new"]) == 1


def test_merge_rejects_known_other_scope_and_ignores_distant_owned_ranges():
    _, _, tasks = verified_tasks()
    item = rule_item(tasks[0])
    item["grade"] = 2
    assert not ai.merge_report({"items": [item]}, {"kept": tasks})["ai_relations"]["agrees"]
    item["grade"] = None
    tasks[1]["locators"].append(tasks[0]["locator"])
    merged = ai.merge_report({"items": [item]}, {"kept": tasks})
    assert len(merged["ai_relations"]["agrees"]) == 1
    assert not merged["ai_relations"]["conflict"]


def test_legacy_verified_union_is_reanchored_when_merged():
    _, _, tasks = verified_tasks()
    old = copy.deepcopy(tasks[1])
    old.pop("locator_basis")
    old["locators"].insert(0, tasks[0]["locator"])
    old["locator"] = {**old["locator"], "start": tasks[0]["locator"]["start"]}
    item = ai.ai_item(old)
    assert item["locator"] == tasks[1]["locator"]
    assert len(item["owned_ranges"]) == 2
    rules = {"items": [rule_item(tasks[0])]}
    relations = ai.merge_report(rules, {"kept": [old]})["ai_relations"]
    # Precision first: one evidence span on exactly one confirmed rule item
    # holds the task, so the legacy union is not added as a new item.
    assert relations["new"] == []
    assert len(relations["agrees_by_evidence"]) == 1


def test_gaps_metadata_and_all_snapshot_have_independent_hashes(directory):
    text = "과학\n1학년 1학기\n합성 과제\n"
    install_source(directory, text, sections=[section(text)])
    item = candidate(extraction_status="review")
    bounded = candidate(item_id="bounded", start=3, end=5)
    ai.save_json(directory / f"data/derived/items/{ROUND}.json", {"items": [item, bounded]})
    ai.build_targets(directory, ROUND, mode="all")
    output = ai.round_dir(directory, ROUND)
    original = ai.read_text(output / "all/targets.jsonl")
    ai.build_targets(directory, ROUND)
    target = ai.load_targets(output)[0]
    assert target["signals"] == ["G3"] and target["bounded_item_ids"] == ["bounded"]
    assert ai.read_text(output / "all/targets.jsonl") == original
    assert target["target_id"] != json.loads(original)["target_id"]
    assert target["prompt_sha256"] != json.loads(original)["prompt_sha256"]
    ai.build_targets(directory, ROUND)
    assert ai.load_targets(output)[0] == target


def test_legacy_all_targets_and_prompt_hashes(directory):
    install_source(directory, "과학\n1학년 1학기\n합성 과제\n")
    ai.build_targets(directory, ROUND, mode="all")
    output = ai.round_dir(directory, ROUND)
    original = ai.read_text(output / "all/targets.jsonl")
    # Synthetic target fingerprint, including its prompt hash (prompt template v2).
    assert ai.sha(original) == "8311516e274209d86c4bccf12388c70e2c0f93b5a4d363b84bfd8c76359adf24"
    # Emulate an existing S6e-1 root target, then snapshot its full binding.
    target = json.loads(original)
    ai.write_text(output / "targets.jsonl", original)
    ai.write_text(output / f"prompts/{target['target_id']}.md",
                  ai.read_text(output / f"all/prompts/{target['target_id']}.md"))
    ai.build_targets(directory, ROUND)
    assert ai.read_text(output / "all/targets.jsonl") == original


def test_coverage_counts_misses_and_lists_every_uncovered_position(directory, monkeypatch):
    text = "과학\n1학년 1학기\n합성 과제\n누락 과제\n"
    install_source(directory, text, sections=[section(text)])
    ai.build_targets(directory, ROUND, mode="all")
    ai.build_targets(directory, ROUND)
    output = ai.round_dir(directory, ROUND)
    target = ai.load_targets(output)[0]
    target["start"] = text.index("합성 과제")
    target["end"] = text.index("누락 과제")
    ai.write_text(output / "targets.jsonl", json.dumps(target, ensure_ascii=False) + "\n")
    reference = {"sample": "synthetic", "cell": {"cell_id": "S01", "round": ROUND,
                 "school": "가상중학교", "grade": 1, "semester": 1}, "unreadable": False,
                 "rows": [{"title": "합성 과제", "source_lines": [(3, 3)]},
                          {"title": "누락 과제", "source_lines": [(4, 4)]}], "reference_count": 2}
    monkeypatch.setattr(ai, "load_references", lambda root: [reference])
    report = ai.measure_coverage(directory, ROUND)
    assert report["rule_missed"] == 2 and report["signal_covered"] == 1
    assert report["by_signal"]["G2"] == 1
    missed = report["misses"][1]
    assert missed["positions"][0]["start"] == text.index("누락 과제")
    assert not missed["covered"] and "다른 구간" in missed["reason_estimate"]
    assert "누락 과제" in ai.read_text(output / "coverage.md")


def test_empty_gaps_can_be_built_repeatedly(directory):
    text = "과학\n1학년 1학기\n합성 과제\n"
    install_source(directory, text, sections=[section(text)])
    ai.save_json(directory / f"data/derived/items/{ROUND}.json", {"items": [candidate()]})
    assert ai.build_targets(directory, ROUND)["chunks"] == 0
    assert ai.build_targets(directory, ROUND)["chunks"] == 0


def test_reference_pairs_shared_overview_by_title_location_and_private_detail(directory):
    text = "과학\n1학년 1학기\n합성 과제(서술형)\n설명 문장\n"
    document = install_source(directory, text)
    _, target, task = source(text)
    task.update(title="합성 과제(서술형)", title_line=3,
                grade_evidence="metadata", semester_evidence="metadata",
                evidence=[{"line_start": 3, "line_end": 3, "quote": "합성 과제(서술형)"}])
    item = rule_item(ai.verify_task(task, target, {"text": text}))
    reference = {"rows": [{"title": "합성 과제", "source_lines": [(3, 3)]}]}
    result = ai.pair_reference_positions(reference, [item], [document], directory,
                                         {item["converted_path"]: text})
    assert result["position_paired"] == 1 and not result["missed"]
    assert result["matches"][0]["basis"] == "unique_document_source_position"
    # Two differently named references in one common overview range cannot both
    # consume the same broad bounded item.
    reference["rows"] = [{"title": "가상 설명 가", "source_lines": [(3, 4)]},
                          {"title": "가상 설명 나", "source_lines": [(3, 4)]}]
    result = ai.pair_reference_positions(reference, [item], [document], directory,
                                         {item["converted_path"]: text})
    assert len(result["missed"]) == 2 and not result["matches"]


def test_reference_location_requires_same_document(directory):
    text = "과학\n1학년 1학기\n합성 과제\n"
    document = install_source(directory, text)
    _, target, task = source(text)
    task.update(title="합성 과제", title_line=3,
                grade_evidence="metadata", semester_evidence="metadata",
                evidence=[{"line_start": 3, "line_end": 3, "quote": "합성 과제"}])
    item = rule_item(ai.verify_task(task, target, {"text": text}))
    item["document_id"] = "other-document"
    item["fields"]["title"]["value"] = "다른 제목"
    reference = {"rows": [{"title": "합성 과제", "source_lines": [(3, 3)]}]}
    result = ai.pair_reference_positions(reference, [item], [document], directory,
                                         {item["converted_path"]: text})
    assert len(result["missed"]) == 1 and not result["matches"]


def test_g1_skips_grade3_only_and_other_subject_documents():
    g1_out_of_scope = ai.g1_out_of_scope

    assert g1_out_of_scope("2026 3학년 1학기 평가 계획.pdf", {"grades": [3]}, [])
    assert g1_out_of_scope("2026-1학기 사회, 역사, 도덕과 평가 계획.hwpx",
                           {"grades": [1, 2, 3]}, [])
    # A parenthesised revision note does not make it another subject's plan.
    assert not g1_out_of_scope("2026 1학기 평가 운영 계획(생활중국어, 체육 수정).hwp",
                               {"grades": [1, 2]}, [])
    assert not g1_out_of_scope("2026학년도 1학기 교과별 평가 연간 계획(전과목).hwpx", {}, [])
    assert not g1_out_of_scope("2026 1학년 과학과 평가 계획.pdf", {"grades": [1]}, [])


def test_gold_measurement_override_keeps_labels_closed(tmp_path, monkeypatch):
    monkeypatch.delenv(ai.GOLD_MEASUREMENT_ENV, raising=False)
    with pytest.raises(ValueError):
        ai.round_dir(tmp_path, "2026-round-1-gold")
    with pytest.raises(ValueError):
        ai.guard_path(tmp_path / "data/derived/items/2026-round-1-gold.json")
    monkeypatch.setenv(ai.GOLD_MEASUREMENT_ENV, "chief-measurement")
    assert ai.round_dir(tmp_path, "2026-round-1-gold").name == "2026-round-1-gold"
    ai.guard_path(tmp_path / "data/derived/items/2026-round-1-gold.json")
    for closed in ("data/gold/gold_v1.jsonl", "data/.gold-before-acl-fix/pack/x.md"):
        with pytest.raises(ValueError):
            ai.guard_path(tmp_path / closed)
    monkeypatch.setenv(ai.GOLD_MEASUREMENT_ENV, "yes")
    with pytest.raises(ValueError):
        ai.round_dir(tmp_path, "2026-round-1-gold")


def _ai_task(identity, title, seen_in, start, target, document="doc-ai", grade=1):
    locator = {"start": start, "end": start + 5}
    return {"ai_task_id": identity, "document_id": document, "child_id": None,
            "school_code": "S1", "grade": grade, "semester": 1, "title": title,
            "title_locator": locator, "locator": locator, "locator_basis": "title",
            "locators": [locator], "evidence": [{"locator": locator}],
            "seen_in": seen_in, "target_ids": [target], "title_raw": title,
            "grade_evidence": "metadata", "semester_evidence": "metadata"}


def test_dedupe_joins_overview_and_detail_reads_of_one_task():
    overview = _ai_task("a", "탐구 보고서", "overview", 0, "t1")
    detail = _ai_task("b", "탐구 보고서", "detail", 500, "t2")
    assert len(ai.deduplicate([overview, detail])) == 1
    # Same title in the same table read is kept apart: it may be two activities.
    twin = _ai_task("c", "탐구 보고서", "overview", 900, "t1")
    assert len(ai.deduplicate([overview, twin])) == 2
    # Another grade is another task.
    other = _ai_task("d", "탐구 보고서", "detail", 500, "t2", grade=2)
    assert len(ai.deduplicate([overview, other])) == 2


def test_merge_skips_ai_task_already_held_by_same_title_rule_item():
    rule = {"item_id": "rule-1", "document_id": "doc-rule", "child_id": None,
            "school_code": "S1", "grade": 1, "semester": 1,
            "candidate_role": "performance", "extraction_status": "bounded",
            "locator": {"start": 0, "end": 10},
            "fields": {"title": {"value": "탐구  보고서"}}}
    rules = {"items": [rule]}
    task = _ai_task("a", "탐구 보고서", "overview", 100, "t1")
    result = ai.merge_report(rules, {"kept": [task]})
    assert result["ai_relations"]["agrees_by_title"][0]["rule_item_ids"] == ["rule-1"]
    assert result["ai_relations"]["new"] == []
    assert len(result["items"]) == 1


def test_merge_skips_ai_task_whose_evidence_touches_one_confirmed_item():
    detail = {"start": 500, "end": 520}
    rule = {"item_id": "rule-1", "document_id": "doc-ai", "child_id": None,
            "school_code": "S1", "grade": 1, "semester": 1,
            "candidate_role": "performance", "extraction_status": "bounded",
            "locator": {"start": 490, "end": 900},
            "fields": {"title": {"value": "구체 과제 문장"}}}
    task = _ai_task("a", "영역 이름", "both", 0, "t1", document="doc-ai")
    task["locators"] = [task["locator"], detail]
    result = ai.merge_report({"items": [rule]}, {"kept": [task]})
    assert result["ai_relations"]["agrees_by_evidence"][0]["rule_item_ids"] == ["rule-1"]
    assert result["ai_relations"]["new"] == []
    # An overview line touching two confirmed items does not hold the task.
    other = {**rule, "item_id": "rule-2", "locator": {"start": 505, "end": 600}}
    result = ai.merge_report({"items": [rule, other]}, {"kept": [task]})
    assert result["ai_relations"]["agrees_by_evidence"] == []
