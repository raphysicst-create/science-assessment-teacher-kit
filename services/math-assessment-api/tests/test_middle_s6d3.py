"""S6d-3 approved field rules, entirely synthetic sources."""

import pytest
from scripts.middle_fields import reference_codes
from scripts.middle_identity import reconcile_items
from scripts.middle_items import extract_middle_items, ownership_errors, standard_values


def table(rows):
    return "<table>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row)
                                 + "</tr>" for row in rows) + "</table>"


def extract(text, **scope):
    return extract_middle_items(text, {
        "document_id": "synthetic", "segment_id": "section", "section_id": "science",
        "grade": 1, "semester": 2, "status": "target", "boundary_verified": True,
        "header": {"key": "과학"}, "locator": {"start": 0, "end": len(text)}, **scope,
    })


def form(rows=()):
    return table([["과제명", "온도 측정하기"], *rows])


def field(text, name):
    item = extract(text)[0]
    for f in item["fields"].values():
        for o in f["evidence"] + f.get("occurrences", []) + f.get("reference_evidence", []):
            loc = o["locator"]
            assert text[loc["start"]:loc["end"]] == o["raw"]
    assert ownership_errors([item]) == []
    return item["fields"][name]


@pytest.mark.parametrize("title,expected,role,number", [
    ("실험", "실험", "assessment_area", ""),
    ("실험 2", "실험 2", "task_no", "실험 2"),
    ("과제 2: 온도 측정하기", "온도 측정하기", "task", "과제 2"),
    ("1. 온도 측정하기", "온도 측정하기", "task", "1"),
    ("1", "1", "task_no", "1"),
    ("온도 측정하기 (30점)", "온도 측정하기", "task", ""),
])
def test_title_category_number_activity(title, expected, role, number):
    item = extract(table([["과제명", title]]))[0]
    assert item["fields"]["title"]["value"] == expected
    assert item["title_role"] == role
    assert item["fields"]["task_no"]["value"] == number


def test_title_alias_and_semantic_conflict():
    from scripts.middle_items import field_value
    observations = [{"text": s, "raw": s} for s in ("온도 측정하기", "온도측정하기")]
    result = field_value("title", observations)
    assert result["aliases"] == [o["text"] for o in observations]
    result = field_value("title", observations + [{"text": "전류 측정하기"}])
    assert result["status"] == "conflict" and result["value"] == ""
    result = field_value("title", [{"text": s} for s in (
        "탐구가 됬는지 기록하기", "탐구가 됐는지 기록하기",
    )])
    assert len(result["aliases"]) == 2


def test_explicit_number_only_form_requires_plan_metadata():
    text = table([["과제번호", "1"], ["평가방법", "실험"], ["평가시기", "10월"]])
    item = extract(text)[0]
    assert item["fields"]["title"]["value"] == "1"
    assert item["extraction_status"] == "bounded"


@pytest.mark.parametrize("method,expected", [
    ("실험, 보고서, 모둠, 개별", ["실험, 보고서, 모둠, 개별"]),
    ("☑ 실험 □ 보고서 ☑ 관찰평가", ["실험", "관찰평가"]),
    ("온도 측정하기", []), ("-", []), ("□ 실험 □ 보고서", []),
])
def test_method_literal_and_choices(method, expected):
    result = field(form([["평가방법", method]]), "method")
    assert result["value"] == expected
    if "□" in method:
        assert len(result["options"]) >= 2
    if not expected:
        assert result["status"] == "source_absent"


def test_teaching_methods_timing_and_codes_are_reference_only():
    text = table([["단원명", "시기", "평가방법", "성취기준"],
                  ["열", "9월(수행평가)", "관찰평가, 형성평가", "[9과03-01]"]])
    text += form()
    item = next(i for i in extract(text) if i["candidate_role"] == "performance")
    for name in ("method", "timing", "standards"):
        assert item["fields"][name]["value"] in ("", [])


def test_task_steps_are_preserved_without_borrowing_teaching_plan():
    description = "1. 실험 설계 및 수행<br>2. 결과 정리 / 탐구 과정 정리"
    assert field(form([["과제설명", description]]), "task_text")["value"] == [
        "온도 측정하기", "1. 실험 설계 및 수행 2. 결과 정리 / 탐구 과정 정리",
    ]
    assert field(form(), "task_text")["value"] == "온도 측정하기"


def test_summary_timing_and_other_ratio():
    text = form([["평가시기", "10월 2주"], ["서·논술형 반영비율", "5%"]])
    assert field(text, "timing")["value"] == "10월 2주"
    assert field(text, "weight")["value"] == ""
    assert field(text, "essay_weight")["value"] == 5


def test_local_reference_range_across_areas_and_invalid_codes():
    assert len(reference_codes()) == 87
    raw = "[9과08-01]~<br>[9과11-04]"
    result = standard_values([{"raw": raw, "locator": {"start": 0, "end": len(raw)}}])
    assert result["value"] == [c for c in reference_codes() if "[9과08-01]" <= c <= "[9과11-04]"]
    assert "[9과08-99]" not in result["value"]
    raw = "[9과22-01]~[9과24-99]"
    result = standard_values([{"raw": raw, "locator": {"start": 0, "end": len(raw)}}])
    assert result["value"] == [c for c in reference_codes() if c >= "[9과22-01]"]
    raw = "[9과99-01]~[9과99-03]"
    assert not standard_values([{"raw": raw, "locator": {"start": 0, "end": len(raw)}}])["value"]


def test_general_levels_are_not_rubric_or_task_codes():
    text = form() + table([["성취기준", "성취기준별 성취수준"],
                           ["[9과03-01]", "A 높은 이해 B 보통 이해 E 도움 필요"]])
    item = next(i for i in extract(text) if i["candidate_role"] == "performance")
    assert not item["fields"]["rubric"]["value"]
    assert not item["fields"]["standards"]["value"]


def test_dedicated_levels_are_rubric_but_element_points_only_are_not():
    text = form([["평가요소", "척도", "채점기준"],
                 ["실험 설계", "A", "변인을 모두 통제함"],
                 ["실험 설계", "E", "변인 통제에 도움이 필요함"]])
    assert field(text, "rubric")["status"] == "present"
    text = form([["평가요소", "배점"], ["실험 설계", "30"], ["결과 정리", "70"]])
    assert not field(text, "rubric")["value"]
    assert [(v["element"], v["score"]) for v in field(text, "sub_scores")["value"]] == [
        ("실험 설계", 30), ("결과 정리", 70),
    ]
    assert not field(text.replace("평가요소", "채점기준"), "rubric")["value"]


def test_inline_subscores_and_compound_numbers():
    text = form([["만점(반영비율)", "100<br>(20%)"],
                 ["평가요소(배점)", "실험 설계(30점)<br>결과 정리(70점)"]])
    assert field(text, "score")["value"] == 100
    assert field(text, "weight")["value"] == 20
    assert [(v["element"], v["score"]) for v in field(text, "sub_scores")["value"]] == [
        ("실험 설계", 30), ("결과 정리", 70),
    ]
    text = table([["과제명", "온도 측정하기 (20점)"]])
    assert field(text, "score")["value"] == 20
    assert field(form([["반영비율", "20점"]]), "weight")["status"] == "conflict"
    assert field(form([["만점", "100<br>(20%)"]]), "score")["value"] == 100
    assert field(form([["만점", "100<br>(20%)"]]), "weight")["value"] == 20


def test_grouped_levels_and_general_levels_before_task_rubric():
    text = form([["성취기준", "성취기준별 성취수준"],
                 ["[9과03-01]", "A 일반 설명 E 일반 설명"],
                 ["평가요소", "척도", "수행 수준(채점 기준)"],
                 ["변인 통제", "A·B", "모든 변인을 적절히 통제함"],
                 ["변인 통제", "C·D", "변인 통제에 일부 오류가 있음"],
                 ["변인 통제", "E", "변인 통제에 도움이 필요함"]])
    rubric = field(text, "rubric")
    assert rubric["status"] == "present"
    assert all("일반 설명" not in o["text"] for o in rubric["evidence"])
    assert field(text, "free_semester")["value"] is True


@pytest.mark.parametrize("policy,expected", [
    ("1학년 2학기는 자유학기이다.\n", True),
    ("성취도 미산출·이수/미이수\n", True),
    ("2학년 1학기는 자유학기이다.\n", False), ("일반 평가계획\n", False),
])
def test_free_semester_scoped_policy(policy, expected):
    result = field(policy + form(), "free_semester")
    assert result["value"] is expected and result["status"] == "present"
    assert bool(result["reference_evidence"]) == expected


def test_unscored_task_levels_imply_free_semester():
    text = form([["평가요소", "척도", "채점기준"],
                 ["실험 설계", "A", "충실함"], ["실험 설계", "E", "도움 필요"]])
    assert field(text, "free_semester")["value"] is True
    assert field(text.replace("척도", "배점").replace(
        "<td>A</td>", "<td>100점</td>"), "free_semester")["value"] is False


def test_field_conflict_keeps_bounded_and_common_codes():
    summary = ('<table><tr><td>구분</td><td>수행평가</td></tr>'
               '<tr><td>평가영역</td><td>온도 측정하기</td></tr>'
               '<tr><td>만점</td><td>100점</td></tr>'
               '<tr><td>시기</td><td>10월</td></tr>'
               '<tr><td>성취기준</td><td>[9과03-01] [9과03-02]</td></tr></table>')
    text = summary + form([["만점", "100점"], ["시기", "10월"],
                           ["성취기준", "[9과03-02] [9과03-03]"]])
    items = reconcile_items(extract(text))
    assert all(i["extraction_status"] == "bounded" for i in items)
    result = items[-1]["fields"]["standards"]
    assert result["status"] == "conflict" and result["value"] == ["[9과03-02]"]
    assert result["conflict_values"] == ["[9과03-01]", "[9과03-03]"]
