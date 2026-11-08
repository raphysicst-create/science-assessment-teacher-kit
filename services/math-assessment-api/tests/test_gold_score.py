"""Synthetic gold scoring regressions, with no corpus dependency."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from gold_score import (  # noqa: E402
    FIELD_MAP,
    SourceMap,
    confirmed,
    field_result,
    independent,
    method_tokens,
    misattributions,
    pair_items,
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
    assert field_result("max_score", g, p)["result"] == "둘다없음"
    p["fields"]["score"] = {"status": "present", "value": 100}
    assert field_result("max_score", g, p)["result"] == "허위값"
    p["fields"]["score"]["status"] = "unconfirmed"
    assert field_result("max_score", g, p)["result"] == "둘다없음"


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


def test_wilson_zero_and_known_interval():
    assert wilson(0, 0)["value"] is None
    lower, upper = wilson(10, 10)["ci95"]
    assert lower == pytest.approx(0.7224672) and upper == pytest.approx(1)
