"""Source-independent summary allocations, representative titles and absence."""

import copy

import pytest
from scripts.middle_identity import merge_pair, reconcile_items
from scripts.middle_items import field_status, field_value
from test_middle_s6d2c import extract, table


def summary():
    return ("<table><tr><td>구분</td><td colspan='2'>수행평가</td></tr>"
            "<tr><td>평가영역</td><td>온도 측정하기</td><td>관찰 결과 발표하기</td></tr>"
            "<tr><td>만점</td><td>30점</td><td>20점</td></tr>"
            "<tr><td>학기말 반영비율(%)</td><td>30%</td><td>20%</td></tr>"
            "<tr><td>평가시기</td><td>4월</td><td>5월</td></tr></table>")


def detail(title, score=""):
    return table([["수행과제", title], ["성취기준", "[9과03-01]"],
                  ["만점", score], ["평가방법", "실험·실습"]])


def test_literal_title_and_complete_order_merge_summary_numbers_without_codes():
    items = reconcile_items(extract(summary() + detail("온도 측정하기")
                                    + detail("관찰 결과 발표하기")))
    target = items[2]
    assert {"literal_task_title", "column_detail_order"} <= set(
        target["identity_relation"]["matched_fields"])
    for name, value in (("score", 30), ("weight", 30), ("timing", "4월")):
        field = target["fields"][name]
        assert field["value"] == value
        assert field["value_source"] == "summary"
        assert field["source_observations"][0]["evidence"]


@pytest.mark.parametrize("value,status", [("30점", "present"), ("25점", "conflict")])
def test_summary_numeric_agreement_and_conflict_preserve_both_sources(value, status):
    items = reconcile_items(extract(summary() + detail("온도 측정하기", value)
                                    + detail("관찰 결과 발표하기")))
    score = items[2]["fields"]["score"]
    assert score["status"] == status
    assert [o["value"] for o in score["source_observations"]] == [30, float(value[:-1])]
    assert score["value"] == (30 if status == "present" else "")


def test_title_alone_cannot_link_incomplete_sequence():
    items = reconcile_items(extract(summary() + detail("온도 측정하기")))
    assert not any(i.get("identity_relation") for i in items)


@pytest.mark.parametrize("grade,term,document", [(2, 1, "synthetic"),
                                                (1, 2, "synthetic"), (1, 1, "other")])
def test_no_cross_scope_summary_merge(grade, term, document):
    items = extract(summary() + detail("온도 측정하기") + detail("관찰 결과 발표하기"))
    for item in items[2:]:
        item.update(grade=grade, semester=term, document_id=document)
    reconcile_items(items)
    assert not any(i.get("identity_relation") for i in items)


def test_row_summary_uses_spanned_headers_and_detail_area_order():
    overview = ("<table><tr><th rowspan='2'>평가방법</th><th rowspan='2'>평가영역</th>"
                "<th rowspan='2'>영역만점(점)</th><th rowspan='2'>학기말 반영비율(%)</th>"
                "<th colspan='2'>평가 유형별 반영 비율(%)</th>"
                "<th rowspan='2'>평가시기</th></tr>"
                "<tr><td>서술형</td><td>논술형</td></tr>"
                "<tr><td rowspan='2'>수행평가</td><td>실험·실습</td><td>30</td><td>30</td>"
                "<td>30</td><td>0</td><td>4월</td></tr>"
                "<tr><td>과학 글쓰기</td><td>20</td><td>20</td>"
                "<td>0</td><td>20</td><td>5월</td></tr>"
                "<tr><td colspan='3'>합계</td><td>50</td><td>30</td><td>20</td>"
                "<td></td></tr></table>")
    text = (overview + "\n가. 실험·실습\n" + detail("온도를 측정하여 변화 설명하기")
            + "\n나. 과학 글쓰기\n" + detail("측정 방법의 장단점을 글로 쓰기"))
    items = reconcile_items(extract(text))
    assert len(items) == 4
    assert items[-1]["fields"]["score"]["value"] == 20
    assert items[-1]["fields"]["timing"]["value"] == "5월"
    assert "unique_area_label" in items[-1]["identity_relation"]["matched_fields"]


def test_conflicting_title_retains_representative_and_all_literal_candidates():
    observations = [{"raw": v, "text": v} for v in ("온도 측정하기", "온도 결과 보고하기")]
    field = field_value("title", observations)
    assert field_status(field) == "conflict"
    assert field["value"] == "온도 측정하기"
    assert field["observed_values"] == [o["text"] for o in observations]


def test_number_identity_title_conflict_still_has_representative():
    items = extract(detail("온도 측정하기") + detail("온도 결과 보고하기"))
    source, target = items
    source["title_role"] = target["title_role"] = "task"
    merge_pair(source, target, {"basis": "unique_task_number"})
    assert target["fields"]["title"]["status"] == "conflict"
    assert target["fields"]["title"]["value"] == "온도 결과 보고하기"
    assert len(target["fields"]["title"]["source_observations"]) == 2


def test_explicit_task_statement_outranks_area_and_preserves_literal_ending():
    task = "관찰 결과를 비교하고 차이를 논리적으로 서술할 수 있다."
    item = extract("\n가. 과학 논술 (20점)\n" + table([
        ["수행과제", task], ["성취기준", "[9과03-01]"], ["평가방법", "논술형"],
    ]))[0]
    assert item["fields"]["title"]["value"] == task
    assert "과학 논술" in item["fields"]["assessment_area"]["value"]


@pytest.mark.parametrize("empty", ["", " ", "<br>", "-", "없음"])
def test_owned_empty_numeric_cells_have_absence_locations(empty):
    item = extract(table([["수행과제", "관찰 결과 발표하기"], ["만점", empty],
                          ["반영비율", empty]]))[0]
    for name in ("score", "weight"):
        field = item["fields"][name]
        assert field["status"] == "source_absent"
        assert field["absence_basis"] == "explicit_empty_cell"
        assert field["absence_evidence"][0]["locator"]


@pytest.mark.parametrize("levels", [("A", "B", "C"), ("상", "중", "하"),
                                   ("매우우수", "보통", "매우미흡")])
def test_qualitative_task_scale_proves_absent_allocations(levels):
    rubric = ("<table><tr><td>수행과제</td><td colspan='2'>결과를 발표하기</td></tr>"
              "<tr><td>평가방법</td><td colspan='2'>발표</td></tr>"
              "<tr><td>평가요소</td><td colspan='2'>채점기준</td></tr>"
              f"<tr><td rowspan='3'>자료 설명</td><td>자료를 모두 설명함</td>"
              f"<td>{levels[0]}</td></tr><tr><td>일부를 설명함</td><td>{levels[1]}</td></tr>"
              f"<tr><td>설명하지 못함</td><td>{levels[2]}</td></tr></table>")
    item = extract(rubric)[0]
    for name in ("score", "weight", "sub_scores"):
        assert item["fields"][name]["status"] == "source_absent"
        assert item["fields"][name]["absence_evidence"]


@pytest.mark.parametrize("value", ["?", "�", "판독 불가"])
def test_unreadable_numeric_cell_stays_unconfirmed(value):
    item = extract(detail("관찰 결과 발표하기", value))[0]
    assert item["fields"]["score"]["status"] == "unconfirmed"
    assert item["fields"]["weight"]["status"] == "unconfirmed"


def test_curriculum_levels_alone_do_not_prove_absent_scores():
    item = extract(table([["수행과제", "결과 발표하기"], ["성취기준", "[9과03-01]"],
                          ["성취수준", "A"], ["", "B"], ["평가방법", "발표"]]))[0]
    assert item["fields"]["score"]["status"] == "unconfirmed"


def test_task_levels_after_method_prove_absence_without_element_label():
    text = table([["수행과제", "관찰 결과 발표하기"], ["평가방법", "발표"],
                  ["성취수준", "A", "자료를 모두 설명함"],
                  ["", "B", "자료를 일부 설명함"], ["", "C", "자료를 설명하지 못함"]])
    item = extract(text)[0]
    assert item["fields"]["score"]["status"] == "source_absent"


def test_summary_explicit_empty_cell_can_supply_absence_to_detail():
    text = summary().replace("<td>30점</td>", "<td></td>")
    items = extract(text + detail("온도 측정하기") + detail("관찰 결과 발표하기"))
    # The detail has no maximum slot, so only the summary owns the absence proof.
    target = items[2]["fields"]["score"]
    target.update(evidence=[], status="unconfirmed", source_absent=False)
    reconcile_items(items)
    assert target["status"] == "source_absent"
    assert target["value_source"] == "summary"
    assert target["absence_evidence"][0]["raw"] == ""


def test_numbered_curriculum_heading_cannot_create_a_task_form():
    text = "\n### 3) 물질의 상태 변화\n" + table([
        ["성취기준", "[9과04-04]"], ["성취수준", "A"], ["", "B"],
    ])
    assert not any(i["extraction_status"] == "bounded" for i in extract(text))


@pytest.mark.parametrize("header,value", [("배점(만점)", "10점"),
                                          ("학기말 반영비율(%)", "10%"),
                                          ("반영비율(배점)", "10%<br>(10점)")])
def test_summary_numeric_header_variants(header, value):
    text = ("<table><tr><td>구분</td><td>수행평가</td></tr>"
            "<tr><td>평가영역</td><td>결과 발표하기</td></tr>"
            f"<tr><td>{header}</td><td>{value}</td></tr></table>")
    item = extract(text)[0]
    name = "weight" if header.startswith("학기말") else "score"
    assert item["fields"][name]["value"] == 10
    if header == "반영비율(배점)":
        assert item["fields"]["weight"]["value"] == 10


def test_numbered_checklist_is_holistic_without_element_allocations():
    text = ("<table><tr><td>수행과제</td><td colspan='2'>관찰 기록하기</td></tr>"
            "<tr><td>평가요소</td><td>채점기준</td><td>배점</td></tr>"
            "<tr><td rowspan='2'>1. 관찰하였는가?<br>2. 기록하였는가?</td>"
            "<td>모두 만족함</td><td>10</td></tr>"
            "<tr><td>일부 만족함</td><td>5</td></tr></table>")
    field = extract(text)[0]["fields"]["sub_scores"]
    assert field["status"] == "source_absent"
    assert field["value"] == []


def test_reconciliation_does_not_mutate_original_source_snapshots():
    items = extract(summary() + detail("온도 측정하기") + detail("관찰 결과 발표하기"))
    before = copy.deepcopy(items[0]["fields"]["score"])
    reconcile_items(items)
    assert items[2]["fields"]["score"]["source_observations"][0]["value"] == before["value"]


def test_concrete_title_cell_precedes_activity_in_a_rubric():
    text = ("<table><tr><td>평가영역</td><td colspan='2'>자연 관찰 탐구보고서</td></tr>"
            "<tr><td>평가요소</td><td>채점기준</td><td>배점</td></tr>"
            "<tr><td rowspan='2'>식물 관찰 보고서 작성하기</td>"
            "<td>모두 만족함</td><td>100</td></tr>"
            "<tr><td>일부 만족함</td><td>50</td></tr></table>")
    assert extract(text)[0]["fields"]["title"]["value"] == "자연 관찰 탐구보고서"


@pytest.mark.parametrize("intervening", ["", "\n### 4) 다른 과제\n", "\n2학년\n", "\n2학기\n"])
def test_fragmented_standard_header_and_rubric_require_heading_continuity(intervening):
    text = ("\n### 3) 관찰 결과 서평쓰기(10점)\n"
            "<table><tr><th colspan='2'>성취기준</th></tr>"
            "<tr><td>성취수준</td><td>A</td></tr></table>\n[9과03-01]\n"
            + intervening + "<table><tr><td></td><td>B</td><td>일부 설명함</td></tr>"
            "<tr><td>평가방법</td><td colspan='2'>논술형</td></tr>"
            "<tr><td>평가요소</td><td>채점기준</td><td>배점</td></tr>"
            "<tr><td rowspan='2'>1. 관찰하였는가?<br>2. 기록하였는가?</td>"
            "<td>모두 만족함</td><td>10</td></tr>"
            "<tr><td>일부 만족함</td><td>5</td></tr></table>")
    items = extract(text)
    linked = [i for i in items if i["links"]]
    assert bool(linked) == (not intervening)
    if linked:
        assert linked[0]["fields"]["score"]["value"] == 10
        assert linked[0]["fields"]["standards"]["value"] == ["[9과03-01]"]
        assert linked[0]["fields"]["sub_scores"]["status"] == "source_absent"
