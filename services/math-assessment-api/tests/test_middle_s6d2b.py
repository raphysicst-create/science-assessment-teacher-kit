"""General item failures from independent review, using synthetic sources only."""

import hashlib

import pytest
from scripts.middle_identity import reconcile_items
from scripts.middle_items import extract_middle_items, ownership_errors
from scripts.middle_segments import segment_document
from scripts.middle_subjects import subject_sections


def table(rows):
    return "<table>" + "".join(
        "<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows
    ) + "</table>"


def extract(text):
    return extract_middle_items(text, {
        "document_id": "synthetic", "segment_id": "segment", "section_id": "science",
        "grade": 1, "semester": 2, "status": "target", "boundary_verified": True,
        "header": {"key": "과학"}, "locator": {"start": 0, "end": len(text)},
    })


def value(item, name):
    return item["fields"][name]["value"]


def summary(areas=("관찰 기록 작성하기", "전류 측정하기"), group="수행평가(40%)"):
    return (
        '<table><tr><td>구분</td><td>정기시험</td>'
        f'<td colspan="2">{group}</td></tr>'
        + table([
            ["명칭, 영역", "시험", *areas],
            ["평가 방법", "선택형", "실험, 보고서, 모둠, 개별", "서논술형"],
            ["배점(점)", "100점", "100점", "100점"],
            ["반영비율", "60%", "20%", "20%"],
            ["시기", "12월", "9월", "10월"],
        ]).removeprefix("<table>").removesuffix("</table>") + "</table>"
    )


@pytest.mark.parametrize("unit", [
    "Ⅳ. 물질의 상태변화 2. 상태 변화와 열에너지",
    "Ⅰ. 물질의 특성 Ⅱ. 지권의 변화", "IV. 빛과 파동",
])
def test_unit_number_cannot_establish_item_or_override_task(unit):
    text = table([["평가영역", unit], ["성취기준", "[9과04-04]"]])
    assert all(i["extraction_status"] == "review" for i in extract(text))
    items = extract(table([
        ["평가영역", unit], ["수행 과제", "온도 측정하기"],
        ["성취기준", "[9과04-04]"],
    ]))
    assert len(items) == 1
    assert value(items[0], "title") == "온도 측정하기"
    assert items[0]["extraction_status"] == "bounded"


@pytest.mark.parametrize("header", ["단원", "단원명", "단원내용", "평가영역명(관련단원명)"])
def test_unit_column_does_not_supply_title(header):
    items = extract(table([[header, "열과 에너지"], ["성취기준", "[9과03-01]"]]))
    assert all(not value(i, "title") and i["extraction_status"] == "review" for i in items)


@pytest.mark.parametrize("group", ["수행평가(40%)", "수행평가(과정 중심 평가)", "과정중심평가"])
def test_annotated_group_and_title_row_beat_methods_and_competencies(group):
    items = extract(summary(group=group))
    assert [value(i, "title") for i in items] == ["관찰 기록 작성하기", "전류 측정하기"]
    assert all(i["extraction_status"] == "bounded" for i in items)
    assert all(value(i, "score") == 100 for i in items)
    assert ownership_errors(items) == []


def test_competency_and_method_lists_are_not_representative_titles():
    items = extract(summary(("과학적 탐구능력", "과학적사고력")))
    assert all(not value(i, "title") and i["extraction_status"] == "review" for i in items)


def test_nested_process_marker_is_not_a_second_group():
    items = extract(summary(("과정중심평가", "관찰 기록 작성하기")))
    assert len(items) == 2
    assert ownership_errors(items) == []


def details(areas=("과학적 탐구 능력", "과학적 사고력")):
    return "".join(table([
        ["평가영역(단원)", area], ["수행 과제", title],
        ["평가 방법", method], ["만점", "100점"], ["반영비율", "20%"],
        ["성취기준", code],
    ]) for area, title, method, code in zip(
        areas, ("관찰 기록 작성하기", "전류 측정하기"),
        ("실험, 보고서, 모둠, 개별", "서논술형"),
        ("[9과01-01]", "[9과02-01]"), strict=True,
    ))


def test_unique_literal_area_score_and_order_link_summary_without_counting_twice():
    items = reconcile_items(extract(summary(("과학적 탐구능력", "과학적사고력")) + details()))
    duplicates = [i for i in items if i["candidate_role"] == "summary_duplicate"]
    assert len(duplicates) == 2
    assert all(set(i["identity_relation"]["matched_fields"]) >= {"score", "column_detail_order"}
               for i in duplicates)
    independent = [i for i in items if i["candidate_role"] != "summary_duplicate"]
    assert len(independent) == 2
    assert all(i["extraction_status"] == "bounded" for i in independent)
    assert ownership_errors(items) == []


def test_repeated_area_and_order_alone_do_not_link():
    items = reconcile_items(extract(
        summary(("과학적 사고력", "과학적 사고력"))
        + details(("과학적 사고력", "과학적 사고력")),
    ))
    assert not any(i.get("identity_relation") for i in items)


def test_linked_code_conflict_keeps_both_source_observations():
    text = summary() + details(("관찰 기록 작성하기", "전류 측정하기"))
    # Add an explicit, conflicting summary code row to this synthetic source.
    text = text.replace("</table>", table([
        ["성취기준", "", "[9과02-01]", "[9과01-01]"],
    ]).removeprefix("<table>"), 1)
    items = reconcile_items(extract(text))
    independent = [i for i in items if i["candidate_role"] != "summary_duplicate"]
    assert len(independent) == 2
    for item in independent:
        field = item["fields"]["standards"]
        assert field["status"] == "conflict" and field["value"] == []
        assert len(field["source_observations"]) == 2
        assert item["extraction_status"] == "review"


def test_free_semester_unscored_heading_form_is_a_performance_item():
    text = "자유학기 영역별 평가 계획\n\n1) 일상 문제 탐구하기\n\n" + table([
        ["성취기준", "[9과01-01]"], ["평가 방법", "서술형"],
        ["평가 요소", "척도", "평가 기준"], ["탐구 계획", "A", "충실함"],
        ["", "E", "도움 필요"],
    ])
    items = extract(text)
    assert len(items) == 1 and items[0]["extraction_status"] == "bounded"
    assert value(items[0], "title") == "일상 문제 탐구하기"
    assert value(items[0], "score") == "" and value(items[0], "weight") == ""
    assert all(text[o["locator"]["start"]:o["locator"]["end"]] == o["raw"]
               for f in items[0]["fields"].values() for o in f["evidence"])


def test_two_term_document_is_split_at_whole_grade_term_headings():
    text = "과학과 평가 운영 계획\n\n"
    for grade in (1, 2, 3):
        for term in (1, 2):
            text += f"## {grade}) {grade}학년 {term}학기\n\n" + table([
                ["평가과제", f"관측 {grade}-{term} 기록하기"], ["성취기준", "[9과01-01]"],
            ]) + "\n\n"
    source = {"sha256": hashlib.sha256(b"synthetic").hexdigest(),
              "candidate_name": "science-plan.hwp"}
    conversion = {"text": text, "converter": "synthetic", "conversion_status": "ok"}
    segments = segment_document(source, conversion)
    sections = subject_sections(text, segments, conversion)
    items = [i for s in sections for i in extract_middle_items(text, s, conversion)]
    assert {(i["grade"], i["semester"], value(i, "title")) for i in items} == {
        (g, t, f"관측 {g}-{t} 기록하기") for g in (1, 2) for t in (1, 2)
    }


def test_grade_term_in_policy_sentence_does_not_split():
    text = "과학과 평가 계획\n1학년\n1학기\n2학년 2학기에 평가를 실시한다.\n"
    source = {"sha256": hashlib.sha256(b"policy").hexdigest(), "candidate_name": "plan.hwp"}
    segments = segment_document(source, {"text": text, "conversion_status": "ok"})
    assert len(segments) == 1 and segments[0]["grade"] == 1


def test_terminal_score_is_split_with_full_raw_cell_preserved():
    text = table([["평가과제", "광물 분류하기 (35점)"], ["성취기준", "[9과09-03]"]])
    item = extract(text)[0]
    assert value(item, "title") == "광물 분류하기"
    assert value(item, "score") == 35
    title = item["fields"]["title"]["evidence"][0]
    assert title["cell_raw"] == "광물 분류하기 (35점)"
    assert text[title["cell_locator"]["start"]:title["cell_locator"]["end"]] == title["cell_raw"]
    assert item["extraction_status"] == "bounded"


def test_html_break_in_standard_range_preserves_raw_and_expands_syntactically():
    text = table([["평가과제", "변화 기록하기"], ["성취기준", "[9과04-02]~<br>[9과04-04]"]])
    field = extract(text)[0]["fields"]["standards"]
    assert field["value"] == ["[9과04-02]", "[9과04-03]", "[9과04-04]"]
    assert field["occurrences"][0]["raw"] == "[9과04-02]~<br>[9과04-04]"


def test_literal_task_cell_precedes_adjacent_heading_and_preserves_heading_evidence():
    text = "가. 빛 원리 분석하기\n\n" + table([
        ["수행 과제", "빛의 원리 분석하기"], ["성취기준", "[9과10-01]"],
        ["평가 방법", "서술형"],
    ])
    item = extract(text)[0]
    assert value(item, "title") == "빛의 원리 분석하기"
    assert item["extraction_status"] == "bounded"
    heading = item["boundary_evidence"]["adjacent_task_heading"]
    assert heading["raw"] == "빛 원리 분석하기"
    assert text[heading["locator"]["start"]:heading["locator"]["end"]] == heading["raw"]
