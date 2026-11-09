"""Synthetic gold scoring regressions, with no corpus dependency."""

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import gold_score  # noqa: E402
from gold_score import (  # noqa: E402
    FIELD_MAP,
    SourceMap,
    ai_window_coverage,
    combined_items,
    compare_item_metrics,
    confirmed,
    field_locators,
    field_result,
    independent,
    method_tokens,
    misattributions,
    pair_combined_items,
    pair_items,
    score,
    task_number,
    wilson,
)


def envelope(value, status="present"):
    return {"status": status, "value": value, "accepted": [value]}


def text_value(raw):
    return {"status": "present", "values": [{"raw": raw}]}


def gold(key="g1", title="실험", line=10):
    return {
        "item_key": key,
        "school_id": "school",
        "grade": 1,
        "semester": 1,
        "representative_title": {"raw": title},
        "aliases": [],
        "occurrences": [{"doc_id": "doc", "line": line}],
        "fields": {"title": envelope(text_value(title))},
    }


def pipeline(key="p1", title="실험", line=10, status="bounded"):
    return {
        "score_id": key,
        "school_id": "school",
        "grade": 1,
        "semester": 1,
        "occurrences": [{"doc_id": "doc", "line": line}],
        "fields": {"title": {"status": "present", "value": title}},
        "extraction_status": status,
        "candidate_role": "performance",
        "public_eligible": False,
    }


def test_one_to_one_and_ambiguous_ties():
    gs = [gold(), gold("g2", "관찰", 20)]
    ps = [pipeline(), pipeline("p2", "관찰", 20)]
    pairs, missing, extra = pair_items(gs, ps)
    assert [(p["gold_key"], p["pipeline_key"]) for p in pairs] == [("g1", "p1"), ("g2", "p2")]
    assert not missing and not extra
    pairs, missing, extra = pair_items([gold()], [pipeline(), pipeline("duplicate")])
    assert not pairs and missing == [0] and extra == [0, 1]


def test_alias_title_and_title_only_matching():
    g = gold(title="대표 제목")
    g["aliases"] = [{"raw": "다른 이름"}]
    p = pipeline(title="다른\n이름", line=999)
    assert field_result("title", g, p)["result"] == "정답"
    pairs, _, _ = pair_items([g], [p])
    assert pairs[0]["basis"]["normalized_title_matches"] == ["다른이름"]
    assert pairs[0]["basis"]["overlap_pack_lines"] == 0


@pytest.mark.parametrize(
    "actual,status,expected",
    [(20, "present", "정답"), (None, "conflict", "정답"), (30, "present", "오값")],
)
def test_conflict_alternatives(actual, status, expected):
    g, p = gold(), pipeline()
    g["fields"]["ratio"] = envelope(
        {"values": [{"raw": "15%", "norm": 15}, {"raw": "20%", "norm": 20}]}, "conflict"
    )
    p["fields"]["weight"] = {"status": status, "value": actual}
    result = field_result("ratio", g, p)
    assert result["result"] == expected and result["gold_conflict"]


def test_false_value_missing_and_both_absent():
    g, p = gold(), pipeline()
    g["fields"]["max_score"] = envelope({"values": [{"raw": "100", "norm": 100}]})
    assert field_result("max_score", g, p)["result"] == "누락"
    g["fields"]["max_score"]["status"] = "source_absent"
    assert field_result("max_score", g, p)["result"] == "누락"
    p["fields"]["score"] = {"status": "source_absent", "value": None}
    assert field_result("max_score", g, p)["result"] == "둘다없음"
    p["fields"]["score"] = {"status": "present", "value": 100}
    assert field_result("max_score", g, p)["result"] == "허위값"
    p["fields"]["score"]["status"] = "unconfirmed"
    assert field_result("max_score", g, p)["result"] == "누락"


@pytest.mark.parametrize("expected_status", ["present", "source_absent", "conflict"])
def test_unconfirmed_is_missing_even_with_stale_value(expected_status):
    g, p = gold(), pipeline()
    g["fields"]["task_text"] = envelope(text_value("관찰하기"), expected_status)
    p["fields"]["task_text"] = envelope(["관찰하기"], "unconfirmed")
    assert field_result("task_text", g, p)["result"] == "누락"


@pytest.mark.parametrize("status", ["present", "ambiguous", "conflict"])
def test_source_absent_requires_pipeline_source_absent_for_both_absent(status):
    g, p = gold(), pipeline()
    g["fields"]["task_text"] = envelope(None, "source_absent")
    p["fields"]["task_text"] = envelope(None, status)
    assert field_result("task_text", g, p)["result"] == "누락"


@pytest.mark.parametrize(
    "actual,outcome",
    [
        ("<b>관찰</b> 하기", "정답"),
        (["관찰 하기", "관찰하기"], "정답"),
        (["관찰하기", "보고서 작성하기"], "부분"),
        ("관찰하기 및 보고서 작성하기", "부분"),
        ("관찰", "부분"),
        (["실험 설계하기"], "오값"),
        ([], "누락"),
    ],
)
def test_task_text_normalizes_strings_and_lists_and_separates_partial(actual, outcome):
    g, p = gold(), pipeline()
    g["fields"]["task_text"] = envelope(text_value("관찰하기"))
    p["fields"]["task_text"] = envelope(actual)
    assert field_result("task_text", g, p)["result"] == outcome


@pytest.mark.parametrize(
    "actual,outcome",
    [
        (["보고서 작성하기", "관찰하기"], "정답"),
        (["관찰하기"], "부분"),
        ("관찰하기 보고서 작성하기", "부분"),
        (["관찰하기", "다른 활동"], "부분"),
    ],
)
def test_task_text_gold_step_list_comparison(actual, outcome):
    g, p = gold(), pipeline()
    g["fields"]["task_text"] = envelope(
        {"values": [{"raw": "관찰하기"}, {"raw": "보고서 작성하기"}]}
    )
    p["fields"]["task_text"] = envelope(actual)
    assert field_result("task_text", g, p)["result"] == outcome


def test_task_text_accepted_alternative_can_be_exact_after_partial():
    g, p = gold(), pipeline()
    g["fields"]["task_text"] = envelope(text_value("관찰하기 보고서 작성하기"))
    g["fields"]["task_text"]["accepted"].append(text_value("관찰하기"))
    p["fields"]["task_text"] = envelope(["관찰하기"])
    assert field_result("task_text", g, p)["result"] == "정답"


@pytest.mark.parametrize(
    "actual,outcome",
    [
        (
            [{"element": "실험<br>설계", "score": 40.0},
             {"element": "실험 수행", "score": 20.0}],
            "정답",
        ),
        (
            [{"element": "실험 수행", "score": 20},
             {"element": "실험 설계", "score": 40},
             {"element": "실험 설계", "score": 40}],
            "정답",
        ),
        (
            [{"element": "실험 설계", "score": 20},
             {"element": "실험 수행", "score": 40}],
            "오값",
        ),
        (
            [{"element": "다른 요소", "score": 40},
             {"element": "실험 수행", "score": 20}],
            "오값",
        ),
        ([{"element": "실험 설계", "score": 40}], "오값"),
        ([], "누락"),
    ],
)
def test_sub_scores_compares_element_score_pairs(actual, outcome):
    g, p = gold(), pipeline()
    g["fields"]["sub_scores"] = envelope(
        {"values": [
            {"name": "실험 설계", "norm": 40, "raw": "(40)"},
            {"name": "실험 수행", "raw": "20점"},
        ]}
    )
    p["fields"]["sub_scores"] = envelope(actual)
    p["fields"]["points"] = envelope(999)
    assert FIELD_MAP["sub_scores"] == "sub_scores"
    assert field_result("sub_scores", g, p)["result"] == outcome


def test_sub_scores_preserves_legacy_gold_value_shape_and_conflict_alternatives():
    g, p = gold(), pipeline()
    value = {"values": [{"name": "요소 1", "norm": 0, "raw": "0점"}]}
    g["fields"]["sub_scores"] = envelope(value, "conflict")
    g["fields"]["sub_scores"]["accepted"].append(
        {"values": [{"name": "요소 1", "raw": "2.5점"}]}
    )
    p["fields"]["sub_scores"] = envelope([{"element": "요소 1", "score": 2.5}])
    assert field_result("sub_scores", g, p)["result"] == "정답"
    p["fields"]["sub_scores"] = envelope(value)
    assert field_result("sub_scores", g, p)["result"] == "정답"


def test_misattribution_counts_field_once_and_respects_group():
    g, peer, p = gold(), gold("g2", "관찰"), pipeline()
    g["fields"]["ratio"] = envelope({"values": [{"raw": "10", "norm": 10}]})
    peer["fields"]["ratio"] = envelope({"values": [{"raw": "20", "norm": 20}]})
    p["fields"]["weight"] = {"status": "present", "value": 20}
    errors = misattributions(g, p, [g, peer], ["ratio"])
    assert len(errors) == 1 and errors[0]["other_gold_keys"] == ["g2"]
    peer["semester"] = 2
    assert not misattributions(g, p, [g, peer], ["ratio"])


def test_task_number_not_scored():
    assert "task_no" not in FIELD_MAP


@pytest.mark.parametrize("raw", ["수행평가 1", "수행 평가 (1).", "1", "①", "１", "제1번"])
def test_task_number_normalizes_identity_labels(raw):
    assert task_number(text_value(raw)) == "1"


@pytest.mark.parametrize("raw", ["실험 1", "1/2", "수행평가", "0", "1학기 수행평가 2"])
def test_task_number_does_not_read_prose_or_multiple_numbers(raw):
    assert task_number(raw) is None


def numbered_gold(key, number, title="실험", line=10):
    row = gold(key, title, line)
    row["fields"]["task_no"] = envelope(text_value(number))
    return row


@pytest.mark.parametrize("line", [10, 999])
def test_task_number_resolves_overlap_ties_and_identity_only_fallback(line):
    gs = [numbered_gold("g1", "①", "관찰"), numbered_gold("g2", "수행평가 2", "실험")]
    ps = [pipeline("p2", "수행평가 2", line), pipeline("p1", "수행평가 1", line)]
    assert not pair_items(gs, ps, use_task_no=False)[0]
    pairs, missing, extra = pair_items(gs, ps)
    assert [(p["gold_key"], p["pipeline_key"]) for p in pairs] == [("g1", "p1"), ("g2", "p2")]
    assert not missing and not extra
    assert [p["basis"]["normalized_task_no"] for p in pairs] == ["1", "2"]
    assert all(p["basis"]["task_no_used"] for p in pairs)


def test_pipeline_explicit_task_number_with_descriptive_title():
    g, p = numbered_gold("g", "1."), pipeline(title="다른 과제명", line=999)
    p["fields"]["task_no"] = envelope("①")
    pairs, missing, extra = pair_items([g], [p])
    assert pairs[0]["basis"]["task_no_used"] and not missing and not extra


@pytest.mark.parametrize("duplicate_side", ["gold", "pipeline"])
def test_task_number_requires_mutual_uniqueness(duplicate_side):
    gs = [numbered_gold("g1", "1", "관찰")]
    ps = [pipeline("p1", "수행평가 1", line=999)]
    if duplicate_side == "gold":
        gs.append(numbered_gold("g2", "①", "실험"))
    else:
        ps.append(pipeline("p2", "수행평가 1", line=999))
    pairs, missing, extra = pair_items(gs, ps)
    assert not pairs and missing == list(range(len(gs))) and extra == list(range(len(ps)))


@pytest.mark.parametrize("duplicate_side", ["gold", "pipeline"])
def test_number_uniqueness_includes_already_paired_rows(duplicate_side):
    gs = [numbered_gold("g1", "1", "관찰"), numbered_gold("g2", "1", "실험")]
    ps = [pipeline("p1", "관찰"), pipeline("p2", "수행평가 1", line=999)]
    if duplicate_side == "pipeline":
        gs[1]["fields"]["task_no"] = envelope("2")
        ps[0]["fields"]["task_no"] = envelope("2")
        ps[1]["fields"]["title"]["value"] = "수행평가 2"
    pairs, missing, extra = pair_items(gs, ps)
    assert [(p["gold_key"], p["pipeline_key"]) for p in pairs] == [("g1", "p1")]
    assert not pairs[0]["basis"]["task_no_used"]
    assert missing == [1] and extra == [1]


@pytest.mark.parametrize("key,value", [("school_id", "other"), ("grade", 2), ("semester", 2)])
def test_task_numbers_cannot_cross_identity_groups(key, value):
    g, p = numbered_gold("g", "1"), pipeline(title="수행평가 1", line=999)
    p[key] = value
    pairs, missing, extra = pair_items([g], [p])
    assert not pairs and missing == [0] and extra == [0]


def test_scored_field_values_never_break_identity_ties():
    gs = [numbered_gold("g1", "1", "관찰"), numbered_gold("g2", "2", "실험")]
    ps = [pipeline("p1", "과제명 미상"), pipeline("p2", "과제명 미상")]
    for i, (g, p) in enumerate(zip(gs, ps, strict=True)):
        for name, pipeline_name in FIELD_MAP.items():
            if name in {"title", "task_text"}:
                continue
            value = 20 + i if name in {"max_score", "ratio", "sub_scores"} else f"내용 {i}"
            g["fields"][name] = envelope(value)
            p["fields"][pipeline_name] = envelope(value)
    pairs, missing, extra = pair_items(gs, ps)
    assert not pairs and missing == [0, 1] and extra == [0, 1]
    # Identity numbers win even when every scored value suggests the opposite pairing.
    ps[0]["fields"]["task_no"] = envelope("2")
    ps[1]["fields"]["task_no"] = envelope("1")
    pairs, missing, extra = pair_items(gs, ps)
    assert [(p["gold_key"], p["pipeline_key"]) for p in pairs] == [("g1", "p2"), ("g2", "p1")]
    assert not missing and not extra


def test_explicit_number_disagreement_with_generic_title_is_held():
    g, p = numbered_gold("g", "1"), pipeline(title="수행평가 1", line=999)
    p["fields"]["task_no"] = envelope("2")
    assert not pair_items([g], [p])[0]


def test_task_number_does_not_override_existing_location_title_pair():
    g, p = numbered_gold("g", "1"), pipeline()
    p["fields"]["task_no"] = envelope("2")
    pairs, missing, extra = pair_items([g], [p])
    assert not missing and not extra and not pairs[0]["basis"]["task_no_used"]


def test_number_link_releases_location_tie_with_auditable_phase():
    gs = [numbered_gold("g1", "1", "관찰"), gold("g2", "실험")]
    ps = [pipeline("p1", "수행평가 1"), pipeline("p2", "이름 미상")]
    pairs, missing, extra = pair_items(gs, ps)
    assert not missing and not extra
    assert [p["basis"]["pairing_phase"] for p in pairs] == [
        "task_no", "location_title_after_task_no",
    ]
    assert [p["basis"]["task_no_used"] for p in pairs] == [True, False]
    reversed_pairs, _, _ = pair_items(list(reversed(gs)), list(reversed(ps)))
    assert {(p["gold_key"], p["pipeline_key"]) for p in reversed_pairs} == {
        ("g1", "p1"), ("g2", "p2"),
    }


@pytest.mark.parametrize("number,status", [("1/2", "present"), ("1", "conflict")])
def test_ambiguous_pipeline_number_cannot_fall_back_to_generic_title(number, status):
    g, p = numbered_gold("g", "1"), pipeline(title="수행평가 1", line=999)
    p["fields"]["task_no"] = envelope(number, status)
    assert not pair_items([g], [p])[0]


def test_confirmed_and_all_stages_summary_alias_exclusion():
    bounded, review = pipeline(), pipeline("review", status="review")
    alias = {
        **pipeline("alias"),
        "candidate_role": "summary_duplicate",
        "identity_relation": {"x": 1},
    }
    candidates = [p for p in [bounded, review, alias] if independent(p)]
    assert len(candidates) == 2
    assert [p["score_id"] for p in candidates if confirmed(p)] == ["p1"]
    review["public_eligible"] = True
    assert confirmed(review)


def test_stage_matching_recall_uses_same_gold_denominator():
    gs = [gold(), gold("g2", "관찰", 20)]
    ps = [pipeline(), pipeline("p2", "관찰", 20, status="review")]
    all_pairs, _, _ = pair_items(gs, ps)
    bounded_pairs, missing, _ = pair_items(gs, [p for p in ps if confirmed(p)])
    assert wilson(len(all_pairs), len(gs))["value"] == 1
    assert wilson(len(bounded_pairs), len(gs))["value"] == 0.5
    assert missing == [1]


def test_source_map_end_exclusive_and_zip_container_offsets():
    mapper = SourceMap.__new__(SourceMap)
    mapper.records = {
        "source": [
            {
                "doc_id": "child",
                "start": 100,
                "end": 110,
                "pack_offset": 4,
                "line_starts": [0, 4, 9, 14],
            }
        ]
    }
    assert mapper.locate("source", {"start": 100, "end": 105}) == [
        {"doc_id": "child", "line_start": 2, "line_end": 2}
    ]
    assert mapper.locate("source", {"start": 105, "end": 110}) == [
        {"doc_id": "child", "line_start": 3, "line_end": 3}
    ]
    assert mapper.locate("source", {"start": 90, "end": 100}) == []


def test_rubric_requires_source_overlap():
    g, p = gold(), pipeline()
    g["fields"]["rubric"] = envelope(
        {"values": [{"raw": "채점표", "loc": {"doc_id": "doc", "line_start": 10, "line_end": 15}}]}
    )
    p["fields"]["rubric"] = {"status": "present", "value": "채점 기준 내용"}
    p["field_locations"] = {"rubric": [{"doc_id": "doc", "line": 12}]}
    assert field_result("rubric", g, p)["result"] == "정답"
    p["field_locations"]["rubric"] = [{"doc_id": "doc", "line": 20}]
    assert field_result("rubric", g, p)["result"] == "오값"


@pytest.mark.parametrize(
    "source", ["evidence", "table_locators", "value_evidence", "value_locator"]
)
@pytest.mark.parametrize("line,outcome", [(12, "정답"), (20, "오값")])
def test_rubric_new_schema_locators_map_to_gold_table(source, line, outcome):
    g, p = gold(), pipeline()
    g["fields"]["rubric"] = envelope(
        {"values": [{"raw": "채점표", "loc": {"doc_id": "doc", "line": 12}}]}
    )
    locator = {"start": line - 1, "end": line}
    field = envelope(["정답과 전사가 다른 수준 문장", "A"])
    if source == "evidence":
        field["evidence"] = [{"locator": locator}]
    elif source == "table_locators":
        field["table_locators"] = [locator]
    elif source == "value_evidence":
        field["value"] = [{"text": "수준 문장", "evidence": [{"locator": locator}]}]
    else:
        field["value"] = [{"text": "수준 문장", "locator": locator}]
    # Header/alternate observation locations must not turn a wrong table into a hit.
    field["header_locator"] = {"start": 11, "end": 12}
    field["source_observations"] = [{"locator": {"start": 11, "end": 12}}]
    p["fields"]["rubric"] = field
    mapper = SourceMap.__new__(SourceMap)
    mapper.records = {
        "source": [{
            "doc_id": "doc",
            "start": 0,
            "end": 30,
            "pack_offset": 0,
            "line_starts": list(range(30)),
        }]
    }
    p["field_locations"] = {
        "rubric": [loc for pos in field_locators(field) for loc in mapper.locate("source", pos)]
    }
    assert field_result("rubric", g, p)["result"] == outcome


def test_rubric_uses_accepted_locations_but_excludes_reference_only_locations():
    g, p = gold(), pipeline()
    g["fields"]["rubric"] = envelope(
        {"values": [{"raw": "채점표", "loc": {"doc_id": "doc", "line": 10}}]}
    )
    g["fields"]["rubric"]["accepted"].append(
        {"values": [{"raw": "채점표", "loc": {"doc_id": "doc", "line": 12}}]}
    )
    g["fields"]["rubric"]["references"] = [{"doc_id": "doc", "line": 20}]
    p["fields"]["rubric"] = envelope(["수준 문장"])
    p["field_locations"] = {"rubric": [{"doc_id": "doc", "line": 12}]}
    assert field_result("rubric", g, p)["result"] == "정답"
    p["field_locations"]["rubric"] = [{"doc_id": "doc", "line": 20}]
    assert field_result("rubric", g, p)["result"] == "오값"
    p["field_locations"]["rubric"] = [{"doc_id": "another", "line": 12}]
    assert field_result("rubric", g, p)["result"] == "오값"


def test_rubric_present_source_location_suffices_without_transcription():
    g, p = gold(), pipeline()
    g["fields"]["rubric"] = envelope({"values": [{"loc": {"doc_id": "doc", "line": 12}}]})
    p["fields"]["rubric"] = envelope(None)
    p["field_locations"] = {"rubric": [{"doc_id": "doc", "line": 12}]}
    assert field_result("rubric", g, p)["result"] == "정답"
    p["fields"]["rubric"]["status"] = "unconfirmed"
    assert field_result("rubric", g, p)["result"] == "누락"


def test_method_checked_only_no_semantic_expansion():
    value = {
        "options": [
            {"text": "실험·실습", "state": "checked"},
            {"text": "논술", "state": "unchecked"},
        ],
        "plain_text": "관찰/보고서",
    }
    assert method_tokens(value) == method_tokens(["실험·실습", "관찰", "보고서"])
    assert method_tokens(value) != method_tokens(["실험", "관찰", "보고서"])


def test_method_new_schema_selected_list_ignores_unchecked_option_metadata():
    g, p = gold(), pipeline()
    g["fields"]["method"] = envelope(
        {
            "options": [
                {"text": "실험·실습", "state": "checked"},
                {"text": "논술", "state": "unchecked"},
            ],
            "plain_text": "관찰/보고서",
        }
    )
    p["fields"]["method"] = envelope(["실험·실습", "보고서", "관찰", "보고서"])
    p["fields"]["method"]["options"] = [{"text": "논술", "state": "unchecked"}]
    assert field_result("method", g, p)["result"] == "정답"
    p["fields"]["method"]["value"].append("논술")
    assert field_result("method", g, p)["result"] == "오값"


@pytest.mark.parametrize(
    "codes,relation,outcome",
    [
        (["[9과01-01]"], "subset", "오값"),
        (["[9과01-01]", "[9과01-02]"], "equal", "정답"),
        (["[9과01-01]", "[9과01-02]", "[9과01-03]"], "excess", "오값"),
    ],
)
def test_standards_set_comparison(codes, relation, outcome):
    g, p = gold(), pipeline()
    g["fields"]["standards"] = envelope([{"codes": ["[9과01-01]", "[9과01-02]"]}])
    p["fields"]["standards"] = {"value": codes, "status": "present"}
    result = field_result("standards", g, p)
    assert (result["standards_relation"], result["result"]) == (relation, outcome)


def test_false_free_semester_is_present():
    g, p = gold(), pipeline()
    g["fields"]["free_semester"] = envelope(False)
    p["fields"]["free_semester"] = {"value": False, "status": "present"}
    assert field_result("free_semester", g, p)["result"] == "정답"


@pytest.mark.parametrize("value", [0, 1, "false", "true", None, []])
def test_free_semester_requires_bool(value):
    g, p = gold(), pipeline()
    g["fields"]["free_semester"] = envelope(False)
    p["fields"]["free_semester"] = envelope(value)
    assert field_result("free_semester", g, p)["result"] == "누락"


def test_item_metric_comparison_ignores_field_changes_and_detects_pair_changes():
    before = {
        "stages": {"confirmed": {
            "recall": wilson(1, 2),
            "precision": wilson(1, 1),
            "role_counts": {"performance": 1},
            "missing_gold_keys": ["g2"],
            "pairs": [{
                "gold_key": "g1",
                "pipeline_key": "p1",
                "basis": {"task_no_used": False},
                "fields": {"task_text": "오값"},
            }],
        }},
        "loss_map": {"confirmed": 1},
        "raw_independent_diagnostic": {"count": 1},
        "excluded_summary_aliases": [],
    }
    after = deepcopy(before)
    after["stages"]["confirmed"]["pairs"][0]["fields"]["task_text"] = "부분"
    assert compare_item_metrics(before, after) == {"equal": True, "differences": []}
    after["stages"]["confirmed"]["pairs"][0]["pipeline_key"] = "p2"
    assert compare_item_metrics(before, after) == {
        "equal": False, "differences": ["stages.confirmed.pairs"],
    }
    after["stages"]["confirmed"]["recall"] = wilson(2, 2)
    assert "stages.confirmed.recall" in compare_item_metrics(before, after)["differences"]


def test_wilson_zero_and_known_interval():
    assert wilson(0, 0)["value"] is None
    lower, upper = wilson(10, 10)["ci95"]
    assert lower == pytest.approx(0.7224672) and upper == pytest.approx(1)


def score_row(key, title="실험", line=10, status="bounded"):
    return {
        **pipeline(key, title, line, status),
        "item_id": key, "school": "학교", "converted_path": "conversion",
        "original_path": "source", "locator": {"start": line, "end": line + 1},
    }


@pytest.fixture
def synthetic_score(monkeypatch):
    """Exercise score's normal loading path entirely in memory."""
    root = Path("synthetic-root")
    mapper = SimpleNamespace(
        index=[{"school_name": "학교", "school_id": "school"}],
        records={"conversion": [{"doc_id": "doc", "child_id": None}]},
        diagnostics=[],
        locate=lambda path, loc: [
            {"doc_id": "doc", "line_start": loc["start"], "line_end": loc["end"] - 1}
        ],
    )
    monkeypatch.setattr(gold_score, "SourceMap", lambda root, reports: mapper)
    monkeypatch.setattr(gold_score, "seal_check", lambda root: {"checked": 0, "mismatches": []})
    read_text = Path.read_text
    monkeypatch.setattr(
        Path, "read_text",
        lambda path, **kwargs: "" if path.name == "targets.jsonl" else read_text(path, **kwargs),
    )

    def run(items, *, ai=False, items_dir=None, gs=None, relations=None):
        payload = "\n".join(json.dumps({"type": "item", **g}) for g in (gs or [gold()])).encode()
        labels = SimpleNamespace(
            read_text=lambda **kw: payload.decode(), read_bytes=lambda: payload,
        )
        s6 = {"round": "round", "items": items, "excluded": []}
        if ai:
            s6["ai_relations"] = relations or {}
        reports = {
            "meta.json": {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "scored_fields": list(FIELD_MAP), "not_scored": [],
            },
            "segments": {"round": "round", "documents": [], "excluded_non_plan": [],
                         "incomplete_sources": []},
            "subjects": {"sections": []}, "items": s6, "items_ai": s6,
        }
        loaded = []

        def load(path):
            key = path.name if path.name == "meta.json" else path.parent.name
            loaded.append(key)
            return deepcopy(reports[key])

        monkeypatch.setattr(gold_score, "read", load)
        report = score(root, labels, root / "meta.json", ["round"], items_dir=items_dir)
        return report, loaded

    return run


def test_default_items_dir_matches_explicit_default(synthetic_score):
    rows = [score_row("p1"), score_row("review", "관찰", 20, "review")]
    implicit, loaded = synthetic_score(rows)
    explicit, _ = synthetic_score(rows, items_dir=Path("data/derived/items"))
    assert implicit == explicit
    assert "items" in loaded and "items_ai" not in loaded
    assert set(implicit["stages"]) == {"confirmed", "all_candidates"}


def test_ai_items_do_not_change_either_legacy_stage(synthetic_score):
    rules = [score_row("p1"), score_row("review", "관찰", 20, "review")]
    base, _ = synthetic_score(rules)
    with_ai, _ = synthetic_score(
        [*rules, score_row("ai", "관찰", 30, "ai_verified")], ai=True,
        items_dir=Path("data/derived/items_ai"),
    )
    assert base["stages"] == {k: with_ai["stages"][k] for k in base["stages"]}
    assert compare_item_metrics(base, with_ai) == {"equal": True, "differences": []}


def test_combined_union_deduplicates_support_and_excludes_other_relations():
    rows = [score_row("a"), score_row("b", status="ai_verified")]
    rows[0].update(extraction_status="review", public_eligible=True)
    rows += [score_row(key, status="review") for key in ("c", "ct", "held", "bounded_rel")]
    rows = [{**p, "score_id": "r/" + p["item_id"]} for p in rows]
    relations = {
        "agrees": [
            {"rule_item_id": "c", "ai_task_id": "t1", "bounded": False},
            {"rule_item_id": "bounded_rel", "ai_task_id": "t2", "bounded": True},
            {"rule_item_id": "a", "ai_task_id": "t3", "bounded": False},
        ],
        "agrees_by_title": [
            {"rule_item_ids": ["c", "ct"], "ai_task_id": "t4", "bounded": False},
        ],
        "agrees_by_evidence": [
            {"rule_item_ids": ["held"], "ai_task_id": "t5", "bounded": False},
        ],
        "conflict": [{"rule_item_ids": ["held"]}],
        "ai_split_suggested": [{"rule_item_id": "held"}],
    }
    before = deepcopy(rows)
    selected = combined_items(rows, [{"round": "r", "ai_relations": relations}])
    assert {p["item_id"]: p["contributions"] for p in selected} == {
        "a": ["a", "c_location"], "b": ["b"],
        "c": ["c_location", "c_title"], "ct": ["c_title"],
    }
    assert rows == before
    # Identical local item IDs in another round must not inherit this support.
    assert not combined_items([{**rows[2], "score_id": "other/c"}], [
        {"round": "r", "ai_relations": relations},
    ])


def test_combined_stage_counts_ai_false_positives_and_unextracted_fields(synthetic_score):
    gs = [gold(), gold("g2", "관찰", 20)]
    rows = [score_row("p1"), score_row("ai", "관찰", 20, "ai_verified"),
            score_row("extra", "새로운 과제", 999, "ai_verified")]
    report, _ = synthetic_score(rows, ai=True, gs=gs)
    stage = report["stages"]["rule_ai"]
    assert stage["recall"] == wilson(2, 2)
    assert stage["precision"] == wilson(2, 3)
    assert stage["contribution_counts"]["b"] == {
        "input": 2, "matched": 1, "unmatched": 1, "new_gold": 1,
    }
    assert len(report["unmatched_ai_pipeline"]) == 1
    extra = report["unmatched_ai_pipeline"][0]
    assert extra["title"] == "새로운 과제" and extra["estimated_reason"] == "정답 누락 가능성"
    assert stage["title_accuracy"] == wilson(2, 2)
    assert stage["fields"]["ratio"]["미추출"] == 1
    assert stage["fields"]["ratio"]["누락"] == 1  # Rule item only.
    assert stage["ai_unextracted_fields"]["ratio"] == {"input": 2, "matched": 1}
    assert report["newly_matched_gold"][0]["gold_key"] == "g2"
    assert any(c["type"] == "ai_unmatched" for c in report["cases"])


def test_owned_ranges_fallback_has_separate_basis_and_does_not_mutate_items():
    p = pipeline("ai", "다른 제목", 999, "ai_verified")
    p["owned_occurrences"] = [{"doc_id": "doc", "line": 10}]
    before = deepcopy(p)
    pairs, missing, extra = pair_combined_items([gold()], [p])
    assert not missing and not extra
    assert pairs[0]["basis"]["owned_ranges_used"] is True
    assert pairs[0]["basis"]["overlap_pack_lines"] == 1
    assert pairs[0]["basis"]["locator_overlap_pack_lines"] == 0
    assert pairs[0]["basis"]["pairing_phase"] == "owned_ranges"
    assert p == before


def test_score_maps_owned_ranges_and_reports_fallback(synthetic_score):
    ai = score_row("ai", "다른 제목", 999, "ai_verified")
    ai["owned_ranges"] = [{"start": 20, "end": 21}]
    report, _ = synthetic_score(
        [score_row("a"), ai], ai=True, gs=[gold(), gold("g2", "관찰", 20)],
    )
    pair = report["stages"]["rule_ai"]["pairs"][1]
    assert pair["gold_key"] == "g2" and pair["basis"]["owned_ranges_used"]
    assert pair["pipeline_locations"] == [{"doc_id": "doc", "line_start": 20, "line_end": 20}]
    assert report["newly_matched_gold"][0]["basis"]["owned_ranges_used"]


def test_score_counts_location_and_title_support_separately(synthetic_score):
    relations = {
        "agrees": [{"rule_item_id": "c1", "ai_task_id": "t1", "bounded": False}],
        "agrees_by_title": [{"rule_item_ids": ["c2"], "ai_task_id": "t2", "bounded": False}],
    }
    rows = [score_row("a"), score_row("b", "관찰", 20, "ai_verified"),
            score_row("c1", "보고서", 30, "review"), score_row("c2", "발표", 40, "review")]
    gs = [gold(), gold("g2", "관찰", 20), gold("g3", "보고서", 30), gold("g4", "발표", 40)]
    report, _ = synthetic_score(rows, ai=True, gs=gs, relations=relations)
    stage = report["stages"]["rule_ai"]
    assert stage["input_count"] == 4 and stage["recall"] == wilson(4, 4)
    assert stage["contribution_counts"]["c_location"]["new_gold"] == 1
    assert stage["contribution_counts"]["c_title"]["new_gold"] == 1
    assert [p["contributions"] for p in stage["pairs"]] == [
        ["a"], ["b"], ["c_location"], ["c_title"],
    ]


def test_primary_locator_and_title_pairs_precede_owned_ranges():
    p = pipeline("ai", "실험", 999, "ai_verified")
    p["owned_occurrences"] = [{"doc_id": "doc", "line": 20}]
    pairs, missing, _ = pair_combined_items([gold(), gold("g2", "관찰", 20)], [p])
    assert pairs[0]["gold_key"] == "g1" and missing == [1]
    assert pairs[0]["basis"]["owned_ranges_used"] is False


def test_owned_ranges_fallback_preserves_ambiguous_ties():
    ps = [pipeline(k, "미상", 999, "ai_verified") for k in ("a", "b")]
    for p in ps:
        p["owned_occurrences"] = [{"doc_id": "doc", "line": 10}]
    pairs, missing, extra = pair_combined_items([gold()], ps)
    assert not pairs and missing == [0] and extra == [0, 1]


def test_owned_fallback_keeps_unmatched_rule_competitors():
    ps = [pipeline(k, "미상") for k in ("rule1", "rule2")]
    ai = pipeline("ai", "미상", 999, "ai_verified")
    ai["owned_occurrences"] = [{"doc_id": "doc", "line": 10}]
    pairs, missing, extra = pair_combined_items([gold()], [*ps, ai])
    assert not pairs and missing == [0] and extra == [0, 1, 2]


def test_window_coverage_uses_mapped_source_positions():
    windows = [
        {"target_id": "in", "locations": [{"doc_id": "doc", "line_start": 5, "line_end": 10}]},
        {"target_id": "other", "locations": [{"doc_id": "other", "line": 10}]},
    ]
    assert ai_window_coverage(gold(), windows)["ai_window_ids"] == ["in"]
    assert ai_window_coverage(gold(line=11), windows)["ai_window_status"] == "창 밖"


def test_unmatched_ai_method_diagnosis_does_not_create_a_pair():
    g = gold()
    g["fields"]["method"] = envelope({
        "plain_text": "실험 보고서 평가",
        "values": [{"raw": "실험 보고서 평가", "loc": {"doc_id": "doc", "line": 999}}],
    })
    p = score_row("ai", "실험 보고서 평가", 999, "ai_verified")
    assert not pair_combined_items([g], [p])[0]
    record = gold_score.unmatched_ai_record(p, [g], [])
    assert record["estimated_reason"] == "수행평가 아님"
    assert record["method_diagnostic_gold_keys"] == ["g1"]


def test_v13_markdown_keeps_korean_and_does_not_mutate_counts(synthetic_score):
    report, _ = synthetic_score([score_row("ai", status="ai_verified")], ai=True)
    report.update(
        baseline={"path": "baseline", "sha256": "test"}, item_metric_comparison={"equal": True},
        comparison={"v1.2": {"stages": deepcopy(report["stages"])}},
    )
    before = deepcopy(report)
    rendered = gold_score.markdown(report)
    assert "규칙+AI" in rendered and "미추출" in rendered and "제목 정확도" in rendered
    assert report == before
