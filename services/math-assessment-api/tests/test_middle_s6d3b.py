"""Synthetic task-owned detail fields, converted glyphs and policy scopes."""

import pytest
from scripts.assessment_symbols import marker_state
from scripts.middle_identity import reconcile_items
from scripts.middle_items import extract_middle_items, ownership_errors, standard_values


def table(rows):
    return "<table>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row)
                                 + "</tr>" for row in rows) + "</table>"


def extract(text, start=0, grade=1, semester=2):
    result = extract_middle_items(text, {
        "document_id": "synthetic", "segment_id": "science", "section_id": "science",
        "grade": grade, "semester": semester, "status": "target", "boundary_verified": True,
        "header": {"key": "과학"}, "locator": {"start": start, "end": len(text)},
    })
    assert not ownership_errors(result)
    for item in result:
        for field in item["fields"].values():
            for obs in field["evidence"] + field.get("occurrences", []) + field.get(
                "reference_evidence", []
            ) + field.get("options", []):
                loc = obs["locator"]
                assert text[loc["start"]:loc["end"]] == obs["raw"]
    return result


def form(rows=()):
    return table([["과제명", "소리 탐구하기"], *rows])


@pytest.mark.parametrize("label", ["과제 내용", "수행 과제(과제 내용)", "수행 과제", "평가 과제"])
def test_task_stages_are_description_without_becoming_another_item(label):
    text = form([[label, "1. 변인을 정하고 실험하기<br>2. 측정값을 그래프로 나타내기"]])
    items = extract(text)
    assert len(items) == 1
    assert items[0]["fields"]["title"]["value"] == "소리 탐구하기"
    assert "그래프" in str(items[0]["fields"]["task_text"]["value"])
    assert not extract(form())[0]["fields"]["task_text"]["value"]


def test_spanned_element_maxima_and_graded_criteria():
    text = ('<table><tr><td>과제명</td><td colspan="3">소리 탐구하기</td></tr>'
            '<tr><td>평가 요소</td><td colspan="2">채점 기준</td><td>배점</td></tr>'
            '<tr><td rowspan="2">실험 설계</td><td>A</td><td>변인을 모두 통제함</td>'
            '<td>40</td></tr><tr><td>C</td><td>일부 변인을 통제하지 못함</td><td>20</td></tr>'
            '<tr><td rowspan="2">자료 해석</td><td>A</td><td>측정 결과를 정확하게 설명함</td>'
            '<td>60</td></tr><tr><td>C</td><td>결과 설명에 오류가 있음</td>'
            '<td>30</td></tr></table>')
    fields = extract(text)[0]["fields"]
    assert [(v["element"], v["score"]) for v in fields["sub_scores"]["value"]] == [
        ("실험 설계", 40), ("자료 해석", 60),
    ]
    assert fields["rubric"]["status"] == "present"
    assert fields["rubric"]["table_locators"] and fields["rubric"]["summary"]
    assert "측정 결과" in str(fields["task_text"]["value"])
    assert not fields["score"]["value"]  # Element maxima never create a task total.
    assert fields["free_semester"]["value"] is False  # Bare numeric rubric scores are scored.


def test_element_points_only_are_not_a_rubric():
    fields = extract(form([["평가요소", "배점"], ["실험 설계", "40"],
                           ["자료 해석", "60"]]))[0]["fields"]
    assert len(fields["sub_scores"]["value"]) == 2
    assert not fields["rubric"]["value"]


def test_repeated_element_levels_share_one_maximum_and_inline_pair():
    text = form([["평가요소", "채점기준", "배점"],
                 ["자료 해석(60점)", "결과를 모두 정확하게 해석함", "60"],
                 ["자료 해석(60점)", "결과를 일부 해석함", "30"]])
    fields = extract(text)[0]["fields"]
    assert [(v["element"], v["score"]) for v in fields["sub_scores"]["value"]] == [
        ("자료 해석", 60),
    ]
    assert fields["rubric"]["status"] == "present"


def test_derived_description_cannot_supply_a_missing_title():
    text = table([["평가요소", "채점기준", "배점"],
                  ["자료 해석", "실험 결과를 모두 해석함", "60"],
                  ["자료 해석", "실험 결과를 일부 해석함", "30"]])
    assert not extract(text)[0]["fields"]["title"]["value"]


def test_enriched_activities_cannot_create_summary_detail_identity_votes():
    from scripts.middle_identity import title_key, titles

    text = form([["평가요소", "채점기준", "배점"],
                 ["보조 과제 수행하기", "온도를 모두 정확하게 측정함", "60"],
                 ["보조 과제 수행하기", "온도를 일부만 측정함", "30"]])
    item = extract(text)[0]
    assert "보조 과제 수행하기" in str(item["fields"]["task_text"]["value"])
    assert title_key("보조 과제 수행하기") not in titles(item)


@pytest.mark.parametrize("yes,no", [
    ("gfedcb", "gfedc"), ("■", "▢"), ("☑", "□"), ("√", "○"), ("●", "○"),
    ("[V]", "[ ]"), ("þ", "☐"),
    ("[ √ ]", "[ ○ ]"), ("[ ■ ]", "[ □ ]"),
])
@pytest.mark.parametrize("suffix", [False, True])
def test_check_alphabet_and_both_marker_positions(yes, no, suffix):
    raw = f"서술·논술 {no} 구술·발표 {yes}" if suffix else f"{no} 서술·논술 {yes} 구술·발표"
    method = extract(form([["평가방법", raw]]))[0]["fields"]["method"]
    assert method["value"] == ["구술·발표"]
    assert [v["state"] for v in method["options"]] == ["unchecked", "checked"]
    assert marker_state(yes) == "checked" and marker_state(no) == "unchecked"


@pytest.mark.parametrize("unknown", ["\ufffd", "\uf08a", "[?]", "gfedx", "gfedcx"])
def test_unreadable_check_is_unconfirmed(unknown):
    method = extract(form([["평가방법", f"{unknown} 구술·발표 □ 실험·실습"]]))[0][
        "fields"]["method"]
    assert method["status"] == "unconfirmed" and method["value"] == []
    assert method["options"][0]["state"] == "unknown"


def test_method_subrows_include_evaluator_but_exclude_competency_and_score_scheme():
    text = ('<table><tr><td>과제명</td><td colspan="3">소리 탐구하기</td></tr>'
            '<tr><td rowspan="3">평가방법</td><td>유형</td>'
            '<td>gfedcb 실험·실습 gfedc 구술·발표</td><td rowspan="3">교과역량</td></tr>'
            '<tr><td>주체</td><td>gfedcb 교사평가 gfedc 자기평가</td></tr>'
            '<tr><td>점수부여방법</td><td>gfedcb 원점수(합산) gfedc 평균점</td></tr></table>')
    method = extract(text)[0]["fields"]["method"]
    assert method["value"] == ["실험·실습", "교사평가"]
    assert len(method["options"]) == 4
    assert method["options"][2]["kind"] == "evaluator"


def test_method_prose_is_task_description():
    prose = "고무줄의 길이를 단계별로 바꾸어 소리를 측정하고 측정 결과를 그래프로 나타내어 설명함."
    fields = extract(form([["평가유형", "☑ 실험·실습 □ 구술·발표"],
                           ["평가방법", prose]]))[0]["fields"]
    assert fields["task_text"]["value"] == prose
    assert fields["method"]["value"] == ["실험·실습"]


def test_summary_method_row_and_detail_only_numeric_fields_and_conflicts():
    summary = table([["구분", "수행평가"], ["평가영역", "소리 탐구하기"],
                     ["과제번호", "과제 1"],
                     ["성취기준", "[9과07-01]"], ["평가방법", "포트폴리오"]])
    detail = form([["과제번호", "과제 1"], ["성취기준", "[9과07-01]"], ["시기", "11월 2주"],
                   ["만점(반영비율)", "80점<br>(25%)"]])
    item = reconcile_items(extract(summary + detail))[-1]
    assert item["fields"]["method"]["value"] == ["포트폴리오"]
    assert item["fields"]["timing"]["value"] == "11월 2주"
    assert item["fields"]["score"]["value"] == 80
    assert item["fields"]["weight"]["value"] == 25
    summary = table([["구분", "수행평가"], ["평가영역", "소리 탐구하기"],
                     ["과제번호", "과제 1"],
                     ["성취기준", "[9과07-01]"], ["시기", "10월"],
                     ["만점", "100점"], ["반영비율", "20%"]])
    item = reconcile_items(extract(summary + detail))[-1]
    for name in ("timing", "score", "weight"):
        assert item["fields"][name]["status"] == "conflict"
        assert len(item["fields"][name]["source_observations"]) == 2


def test_displaced_detail_time_and_compound_numeric_label():
    text = form([["시기", "만점<br>10월<br>(반영비율)", "100점<br>(25%)"]])
    fields = extract(text)[0]["fields"]
    assert fields["timing"]["value"] == "10월"
    assert fields["score"]["value"] == 100
    assert fields["weight"]["value"] == 25


@pytest.mark.parametrize("detail_method,expected,status", [
    ("☑ 서술·논술 ☑ 구술·발표 ☑ 교사평가", ["서·논술", "구술·발표", "교사평가"], "present"),
    ("□ 서술·논술 ☑ 구술·발표", [], "conflict"),
    ("[?] 구술·발표", ["서·논술형 평가"], "unconfirmed"),
])
def test_summary_and_detail_method_evidence(detail_method, expected, status):
    summary = table([["구분", "수행평가"], ["평가영역", "소리 탐구하기"],
                     ["과제번호", "과제 1"], ["평가방법", "서·논술형 평가"]])
    detail = form([["과제번호", "과제 1"], ["평가방법", detail_method]])
    method = reconcile_items(extract(summary + detail))[-1]["fields"]["method"]
    assert method["value"] == expected and method["status"] == status
    assert len(method["source_observations"]) == 2


def test_reference_normalization_keeps_raw_and_ignores_outside_codes():
    raw = "[9과4-04] [9 과\n04 - 04] [9과99-01] [9과04-99] [9과6-01]〜<br>[9과06-03]"
    result = standard_values([{"raw": raw, "locator": {"start": 0, "end": len(raw)}}])
    assert result["value"] == ["[9과04-04]", "[9과06-01]", "[9과06-02]", "[9과06-03]"]
    assert result["occurrences"][0]["raw"] == "[9과4-04]"
    assert result["occurrences"][2]["expanded"] == []


@pytest.mark.parametrize("policy,grade,term,expected", [
    ("1학년은 자유학기이다.", 1, 2, True),
    ("1학년은 자유학기를 운영한다.", 2, 2, False),
    ("1학년 1학기는 자유학기이다.", 1, 2, False),
    ("1학년 2학기는 자유학기이다.", 1, 2, True),
    ("1학년은 자유학기를 운영하지 않는다.", 1, 2, False),
])
def test_grade_wide_policy_before_subject_section(policy, grade, term, expected):
    prefix = policy + "\n일반 평가 방침\n"
    fields = extract(prefix + form(), start=len(prefix), grade=grade, semester=term)[0]["fields"]
    assert fields["free_semester"]["value"] is expected
    if expected:
        assert fields["free_semester"]["reference_evidence"][0]["scope"] == "document_grade_policy"
