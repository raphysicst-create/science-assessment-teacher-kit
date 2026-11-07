"""S6 structural extraction, synthetic text only and network disabled."""

import importlib
from collections import defaultdict

import pytest
from scripts.assessment_symbols import SELECTED_BOXES
from scripts.middle_items import (
    extract_middle_items,
    method_values,
    ownership_errors,
    title_gate,
)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("S6 must remain offline")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def section(text, grade=1, **kwargs):
    return {
        "document_id": "doc_synthetic",
        "child_id": None,
        "segment_id": f"seg_{grade}",
        "section_id": f"subj_{grade}",
        "grade": grade,
        "semester": 2,
        "status": "target",
        "boundary_verified": True,
        "header": {"key": "과학", "raw": "과학"},
        "locator": {"start": 0, "end": len(text)},
        **kwargs,
    }


def table(rows):
    return (
        "<table>"
        + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
        + "</table>"
    )


def extract(text, **kwargs):
    return extract_middle_items(text, section(text, **kwargs))


def value(item, name):
    return item["fields"][name]["value"]


def form(title="달의 위상 변화 관찰", number="실험1", extra=()):
    return table([("평가영역", title), ("평가과제", number), *extra])


def test_pdf_collapsed_exam_and_performance_group_cannot_be_single_bounded_form():
    text = table([
        ("평가 종류 정기시험 수행평가 합계",),
        ("횟수/영역", "1회고사", "2회고사", "전류 탐구 보고서", "소화 탐구 보고서"),
        ("평가 시기", "10월", "12월", "9월", "11월"),
    ])
    items = extract(text)
    assert items and all(i["extraction_status"] == "review" for i in items)
    assert "동일 제목 라벨 복수 값·항목 경계 미확정" in items[0]["review_reasons"]


def test_pdf_title_and_score_in_same_cell_stays_raw_and_requires_review():
    text = table([
        ("평가 영역명", "합성 물질 탐구 영역 만점 30"),
        ("수행과제", "원자 모형 탐구"),
        ("평가방법", "☑ 실험·실습"),
    ])
    item = extract(text)[0]
    assert item["extraction_status"] == "review"
    assert item["fields"]["title"]["value"] == "합성 물질 탐구 영역 만점 30"
    assert item["fields"]["score"]["value"] == ""
    assert "제목 셀에 필드 라벨 혼입·경계 미확정" in item["review_reasons"]


def test_text_only_fallback_cannot_certify_table_shaped_source_text():
    text = form()
    item = extract_middle_items(text, section(text), {
        "text": text, "converter": "pymupdf", "conversion_status": "fallback_text_only",
    })[0]
    assert item["extraction_status"] == "review"
    assert "PDF 평문 폴백·표 구조 미보존" in item["review_reasons"]


def test_pdf_auxiliary_labels_stop_title_and_method_cell_ownership():
    text = table([
        ("평가 영역", "합성 힘 탐구", "관련단원", "힘의 작용", "평가시기", "9월"),
        ("평가유형", "☑ 실험·실습"),
        ("평가주체", "☑ 교사평가"),
        ("평가방식", "☑ 개인별 수행"),
    ])
    item = extract(text)[0]
    assert item["extraction_status"] == "bounded"
    assert value(item, "title") == "합성 힘 탐구"
    assert value(item, "assessment_area") == "합성 힘 탐구"
    assert value(item, "method") == ["실험·실습"]
    assert value(item, "timing") == "9월"


def test_one_form_one_item_and_all_field_evidence():
    text = form(
        extra=[
            ("평가방법", "☑ 서·논술 ☑ 프로젝트 □ 실험·실습 ☑ 기타(실험 안전 점검)"),
            ("만점(점)", "100"),
            ("반영비율(%)", "30"),
            ("평가시기", "10월"),
            ("성취기준", "[9과19-01]~[9과19-03]"),
            ("채점기준", "관측 결과 기록 10점"),
        ]
    )
    items = extract(text)
    assert len(items) == 1
    item = items[0]
    assert item["extraction_status"] == "bounded"
    assert value(item, "title") == "달의 위상 변화 관찰"
    assert value(item, "assessment_area") == "달의 위상 변화 관찰"
    assert value(item, "task_no") == "실험1"
    assert value(item, "task_text") == "실험1"
    assert value(item, "method") == ["서·논술", "프로젝트", "기타"]
    assert item["fields"]["method"]["options"][-1]["other_content"] == "실험 안전 점검"
    assert value(item, "score") == 100
    assert value(item, "weight") == 30
    assert value(item, "standards") == ["[9과19-01]", "[9과19-02]", "[9과19-03]"]
    assert item["fields"]["standards"]["occurrences"][0]["raw"] == "[9과19-01]~[9과19-03]"
    for field in item["fields"].values():
        for obs in field["evidence"]:
            loc = obs["locator"]
            assert text[loc["start"] : loc["end"]] == obs["raw"]
            assert obs["owner_item_id"] == item["item_id"]
            assert {"table", "row", "col"} <= loc.keys()
    for option in item["fields"]["method"]["options"]:
        loc = option["locator"]
        assert text[loc["start"] : loc["end"]] == option["raw"]
    for name, unit in (("score", "점"), ("weight", "%")):
        obs = item["fields"][name]["evidence"][0]
        assert obs["raw"] == str(int(obs["normalized"]))
        assert obs["header_unit"] == unit


@pytest.mark.parametrize("separator", ["·", "ㆍ", "･", "・", "‧"])
def test_checkbox_variants(separator):
    item = extract(form(extra=[("평가방법", f"☑ 서{separator}논술 ☑ 프로젝트")]))[0]
    assert value(item, "method") == ["서·논술", "프로젝트"]


@pytest.mark.parametrize("symbol", sorted(SELECTED_BOXES) + ["gfedcb"])
def test_shared_selected_symbols(symbol):
    item = extract(form(extra=[("평가방법", symbol + " 프로젝트")]))[0]
    assert value(item, "method") == ["프로젝트"]


def test_row_multi_item_ownership_and_numeric_roles():
    text = table(
        [
            ("평가영역", "평가과제", "성취기준", "평가방법", "만점(점)", "반영비율(%)", "배점"),
            ("달의 위상 변화 관찰", "실험1", "[9과07-04]", "보고서", "100", "30", "5"),
            ("포트폴리오", "서논술형2", "[9과03-01]", "☑ 프로젝트", "50", "20", "3"),
        ]
    )
    items = extract(text)
    assert len(items) == 2
    assert [value(i, "score") for i in items] == [100, 50]
    assert [value(i, "points") for i in items] == [5, 3]
    assert [value(i, "weight") for i in items] == [30, 20]
    assert [value(i, "standards") for i in items] == [["[9과07-04]"], ["[9과03-01]"]]
    assert ownership_errors(items) == []
    locations = defaultdict(set)
    for item in items:
        for field in item["fields"].values():
            for obs in field["evidence"]:
                locations[obs["locator"]["start"]].add(item["item_id"])
    assert all(len(owners) == 1 for owners in locations.values())


def test_same_name_different_grade_and_same_grade_different_locations():
    text = form("포트폴리오", "실험1") + form("포트폴리오", "실험2")
    first, second = extract(text)
    other_grade = extract_middle_items(text, section(text, grade=2))
    assert value(first, "title") == value(second, "title") == "포트폴리오"
    assert len({i["item_id"] for i in [first, second, *other_grade]}) == 4
    assert all(i["title_generated"] is False for i in [first, second, *other_grade])


@pytest.mark.parametrize("title", ["실험1", "포트폴리오", "달의 위상 변화 관찰"])
def test_explicit_titles_survive_science_gate(title):
    publish = importlib.import_module("scripts.build_math_assessment_publish_db")
    assert value(extract(table([("수행과제", title)]))[0], "title") == title
    assert not publish.task_name_is_rejected(title, "science", source_title=True)


@pytest.mark.parametrize(
    "title",
    [
        "평가방법",
        "성취기준별 성취수준",
        "설명할 수 있다.",
        "다음 과제를 수행하십시오",
        "결시자는 인정점을 부여한다.",
    ],
)
def test_structural_policy_and_instruction_titles_rejected(title):
    assert not title_gate(title)["accepted"]
    assert all(value(i, "title") != title for i in extract(table([("수행과제", title)])))


def test_no_checkbox_no_invented_method_and_separate_levels_table():
    text = table([("수행과제", "영양소 검출 실험 탐구하기"), ("반영비율(%)", "30")])
    text += table(
        [("성취기준", "성취기준별 성취수준"), ("[9과13-01]", "A 영양소를 설명할 수 있다.")]
    )
    items = extract(text)
    item = items[0]
    assert value(item, "method") == []
    assert item["fields"]["method"]["reason"] == "체크 없음"
    assert value(item, "standards") == []
    assert not item["links"]
    assert items[1]["extraction_status"] == "review"


def test_method_state_and_plain_text_are_separate():
    unchecked = extract(form(extra=[("평가방법", "□ 프로젝트 ☐ 기타( )")]))[0]
    assert unchecked["fields"]["method"]["state"] == "all_unselected"
    assert value(unchecked, "method") == []
    plain = extract(form(extra=[("평가방법", "보고서")]))[0]
    assert plain["fields"]["method"]["state"] == "plain"
    assert value(plain, "method") == ["보고서"]
    assert (
        method_values(plain["fields"]["method"]["evidence"], conversion_loss=True)["state"]
        == "conversion_loss"
    )


def test_shinmok_column_summary_with_shared_weight():
    text = (
        '<table><tr><th rowspan="3">학기 영역</th><th>정기시험</th>'
        '<th colspan="2">수행평가</th></tr>'
        "<tr><td>중간</td><td>힘과 운동</td><td>기체의 성질</td></tr>"
        "<tr><td>선택형</td><td>실험 평가 (11월)</td><td>서·논술형 (10월)</td></tr>"
        "<tr><td>배점</td><td>100점</td><td>10점</td><td>15점</td></tr>"
        '<tr><td>비율</td><td>30%</td><td colspan="2">40%</td></tr></table>'
    )
    items = extract(text)
    assert len(items) == 2
    assert [value(i, "title") for i in items] == ["힘과 운동", "기체의 성질"]
    assert [value(i, "points") for i in items] == [10, 15]
    assert all(value(i, "weight") == "" for i in items)
    assert all(i["shared_fields"][0]["raw"] == "40%" for i in items)
    assert all(value(i, "standards") == [] for i in items)
    assert ownership_errors(items) == []


def test_summary_per_item_weight():
    text = table(
        [("영역", "평가방법", "배점", "반영비율(%)"), ("기체의 성질", "서·논술형", "15점", "20")]
    )
    item = extract(text)[0]
    assert value(item, "title") == value(item, "assessment_area") == "기체의 성질"
    assert value(item, "points") == 15
    assert value(item, "weight") == 20


@pytest.mark.parametrize("number,joined", [("실험1", True), ("실험2", False), ("", False)])
def test_separate_rubric_requires_number_and_continuity(number, joined):
    text = form()
    text += "\n<!-- page 2 -->\n" + table(
        [
            ("과제번호", number),
            ("성취기준", "[9과07-04]"),
            ("채점기준", "배점"),
            ("관측 결과 기록", "5"),
        ]
    )
    items = extract(text)
    assert bool(items[0]["links"]) == joined
    assert value(items[0], "standards") == (["[9과07-04]"] if joined else [])
    assert bool(value(items[0], "rubric")) == joined


def test_number_match_with_intervening_text_does_not_join():
    text = (
        form()
        + "다음 항목의 별도 자료"
        + table(
            [
                ("과제번호", "실험1"),
                ("성취기준", "[9과03-01]"),
                ("채점기준", "기록"),
            ]
        )
    )
    assert not extract(text)[0]["links"]


def test_title_hint_does_not_establish_bounds_or_copy_fields():
    text = "포트폴리오 실험1 ☑ 프로젝트 30% [9과03-01]"
    items = extract_middle_items(text, section(text), title_hints=("포트폴리오", "실험1"))
    assert len(items) == 2
    assert all(i["extraction_status"] == "review" for i in items)
    assert all(value(i, "standards") == [] for i in items)
    assert all(value(i, "weight") == "" for i in items)


def test_markdown_table_and_exact_code_science_configuration():
    text = (
        "| 평가영역 | 평가방법 | 만점(점) | 반영비율(%) |\n"
        "|---|---|---|---|\n| 실험1 | 보고서 | 100 | 30 |\n"
    )
    items = extract(text)
    assert len(items) == 1
    assert value(items[0], "score") == 100
    parser = importlib.import_module("scripts.math_assessment_detail_parser")
    source = "[9과03-01] [12수학01-01]"
    assert parser._exact_fields(source, subject_family="science")["standards"] == ["[9과03-01]"]
    assert parser._exact_fields(source)["standards"] == ["[12수학01-01]"]


def test_science_boundary_and_mixed_item_quarantined():
    text = form(extra=[("성취기준", "[9과03-01] [9도01-01]")])
    assert extract(text)[0]["extraction_status"] == "review"
    assert extract(text, boundary_verified=False)[0]["extraction_status"] == "review"
    assert extract_middle_items(text, section(text, grade=3)) == []
    assert extract_middle_items(text, section(text, status="mixed")) == []


def test_grade_fragment_uses_only_its_own_table_and_unique_columns():
    def summary(grade, titles):
        return (
            '<table><tr><th rowspan="3" colspan="2">학기 영역</th>'
            '<th colspan="2">수행평가</th></tr>'
            f"<tr><td>{titles[0]}</td><td>{titles[1]}</td></tr>"
            "<tr><td>실험 (10월)</td><td>보고서 (11월)</td></tr>"
            f"<tr><td>{grade}학년</td><td>배점</td><td>10점</td><td>15점</td></tr>"
            "</table>"
        )

    first = summary(1, ["포트폴리오", "달의 위상 관찰"])
    second = summary(2, ["포트폴리오", "영양소 검출"])
    text = first + second
    boundary = text.index("<tr><td>2학년")
    grade1 = extract_middle_items(text, section(text, locator={"start": 0, "end": boundary}))
    grade2 = extract_middle_items(
        text, section(text, grade=2, locator={"start": boundary, "end": len(text)})
    )
    assert [value(i, "title") for i in grade1] == ["포트폴리오", "달의 위상 관찰"]
    assert [value(i, "title") for i in grade2] == ["포트폴리오", "영양소 검출"]
    assert len({i["item_id"] for i in grade1 + grade2}) == 4
    assert ownership_errors(grade1 + grade2) == []
    assert all(value(i, "timing") in {"10월", "11월"} for i in grade1 + grade2)


def test_summary_without_title_cell_never_uses_time_or_method_as_title():
    text = (
        "<table><tr><th>구분</th><th>수행평가</th></tr>"
        "<tr><td>평가방법</td><td>실험</td></tr>"
        "<tr><td>평가시기</td><td>10월 4주</td></tr>"
        "<tr><td>만점(점)</td><td>100</td></tr></table>"
    )
    item = extract(text)[0]
    assert value(item, "title") == ""
    assert item["extraction_status"] == "review"


def test_code_mentions_in_elements_do_not_become_standards():
    text = form(extra=[("성취기준", "[9과03-01]"), ("평가요소", "별도 참고 [9과07-01]")])
    assert value(extract(text)[0], "standards") == ["[9과03-01]"]


def test_unknown_check_is_preserved_and_not_all_unselected():
    text = form(extra=[("평가방법", "� 프로젝트 □ 기타(안전)")])
    item = extract(text)[0]
    method = item["fields"]["method"]
    assert method["state"] == "unknown"
    assert method["options"][0]["state"] == "unknown"
    assert method["options"][0]["raw"].startswith("�")
    assert item["extraction_status"] == "review"


def test_same_title_does_not_link_rubric_across_grade_boundary():
    first = form("포트폴리오", "실험1")
    second = table([("과제번호", "실험1"), ("성취기준", "[9과03-01]"), ("채점기준", "기록")])
    text = first + second
    items = extract_middle_items(text, section(text, locator={"start": 0, "end": len(first)}))
    assert not items[0]["links"]
    assert value(items[0], "standards") == []


def test_identity_includes_edition_semester_child_and_position():
    text = form("포트폴리오", "실험1")
    source = section(text)
    base = extract_middle_items(text, source)[0]
    changed = [
        extract_middle_items(text, {**source, **change})[0]
        for change in (
            {"document_id": "doc_edition2"},
            {"semester": 1},
            {"child_id": "child2"},
            {"segment_id": "seg_other"},
        )
    ]
    assert len({i["item_id"] for i in [base, *changed]}) == 5


def test_no_title_generation_even_with_unmatched_hints():
    text = "[9과03-01] 수행평가 계획에 대한 운영 설명"
    item = extract_middle_items(text, section(text), title_hints=("창작 제목",))[0]
    assert value(item, "title") == ""
    assert item["title_generated"] is False


def test_multiple_forms_in_one_table_own_their_fields():
    text = table(
        [
            ("평가영역", "포트폴리오"),
            ("평가과제", "실험1"),
            ("만점(점)", "100"),
            ("성취기준", "[9과03-01]"),
            ("평가영역", "포트폴리오"),
            ("평가과제", "실험2"),
            ("만점(점)", "50"),
            ("성취기준", "[9과07-01]"),
        ]
    )
    items = extract(text)
    assert len(items) == 2
    assert [value(i, "score") for i in items] == [100, 50]
    assert [value(i, "standards") for i in items] == [["[9과03-01]"], ["[9과07-01]"]]
    assert ownership_errors(items) == []


@pytest.mark.parametrize(
    "text",
    [
        table([("평가영역", "관찰", "평가영역", "실험")]),
        "<table><tr><td>평가영역</td><td><table><tr><td>관찰</td></tr></table></td></tr></table>",
        "<table><tr><td>평가영역</td><td>관찰</td></tr><tr><td>불완전</tr></table>",
    ],
)
def test_unproven_or_nested_cells_remain_review(text):
    items = extract(text)
    assert all(i["extraction_status"] == "review" for i in items)


def test_zero_is_a_value_and_non_numeric_grading_preserved():
    text = table(
        [("평가영역", "평가방법", "만점(점)", "반영비율(%)"), ("포트폴리오", "보고서", "P", "0")]
    )
    item = extract(text)[0]
    assert value(item, "score") == "P"
    assert value(item, "weight") == 0


def test_numeric_unit_conflict_is_blank_with_raw_evidence():
    item = extract(form(extra=[("만점(점)", "30%"), ("반영비율(%)", "100점")]))[0]
    assert value(item, "score") == value(item, "weight") == ""
    assert item["fields"]["weight"]["reason"] == "원문 값·머리글 단위 충돌"
    assert item["fields"]["weight"]["evidence"][0]["raw"] == "100점"
