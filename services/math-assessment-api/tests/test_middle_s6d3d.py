"""Synthetic detail-field formats independent of development school documents."""

import pytest
from scripts.middle_items import field_status
from test_middle_s6d2c import extract, table


def form(rows):
    return table([["수행과제", "온도 변화를 조사하여 보고서 작성하기"],
                  ["성취기준", "[9과03-01]"], ["평가방법", "실험·실습"], *rows])


@pytest.mark.parametrize("levels", [("상", "중", "하"), ("A", "C", "E"),
                                   ("매우 우수", "보통", "매우 미흡"),
                                   ("9~10점", "5~8점", "0~4점"),
                                   ("9점 이상", "5점 이상 9점 미만", "5점 미만")])
def test_explicit_scales_and_point_columns(levels):
    text = form([["평가요소", "채점기준", "수준", "배점"],
                 ["결과 설명", "결과를 정확하게 설명함", levels[0], "10"],
                 ["결과 설명", "결과를 일부 설명함", levels[1], "6"],
                 ["결과 설명", "결과 설명이 미흡함", levels[2], "2"]])
    assert extract(text)[0]["fields"]["rubric"]["status"] == "present"


def test_embedded_point_tokens_and_merged_element():
    text = form([["평가요소", "수행 수준(채점기준) 배점"],
                 ["<span>자료 해석</span>", "자료를 모두 옳게 해석함. 7점"],
                 ["자료 해석", "자료를 일부 옳게 3점 해석함."]])
    fields = extract(text)[0]["fields"]
    assert fields["rubric"]["status"] == "present"
    assert [(v["element"], v["score"]) for v in fields["sub_scores"]["value"]] == [
        ("자료 해석", 7)]


def test_horizontal_criteria_have_scores_on_next_row():
    # Use an explicit wide criterion header, preserving the source grid.
    text = form([])[:-8] + ("<tr><td>평가요소</td><td>배점</td>"
                            "<td colspan='2'>채점기준</td></tr>"
                            "<tr><td rowspan='2'>설명하기</td><td rowspan='2'>10</td>"
                            "<td>내용을 모두 정확하게 작성함</td><td>일부만 작성함</td></tr>"
                            "<tr><td>10점</td><td>5점</td></tr></table>")
    assert extract(text)[0]["fields"]["rubric"]["status"] == "present"


@pytest.mark.parametrize("transpose", [False, True])
def test_allocation_direction_without_rubric(transpose):
    rows = ([["평가요소", "계획 작성", "결과 설명"], ["배점", "4", "6"]] if transpose else
            [["평가요소", "배점"], ["계획 작성", "4"], ["결과 설명", "6"]])
    fields = extract(form(rows))[0]["fields"]
    assert fields["rubric"]["status"] == "unconfirmed"
    assert [(v["element"], v["score"]) for v in fields["sub_scores"]["value"]] == [
        ("계획 작성", 4), ("결과 설명", 6)]


@pytest.mark.parametrize("label", ["과제 설명", "과제 내용", "활동 내용", "과제 개요", "주요활동"])
def test_description_label_vocabulary(label):
    text = form([[label, "온도 변화 자료를 해석하여 결과 보고서를 작성한다."]])
    fields = extract(text)[0]["fields"]
    assert fields["task_text"]["value"] == "온도 변화 자료를 해석하여 결과 보고서를 작성한다."


@pytest.mark.parametrize("gap", ["\n", "\n<!-- page 2 -->\n", "\n## 채점 기준\n\n- 2 -\n"])
def test_named_form_joins_split_scoring_table(gap):
    text = form([]) + gap + table([["평가요소", "척도", "배점"],
                                   ["자료 해석", "모두 옳게 작성한 경우", "10"],
                                   ["자료 해석", "일부만 작성한 경우", "5"]])
    items = extract(text)
    assert len(items) == 1
    assert items[0]["links"]
    assert items[0]["fields"]["rubric"]["status"] == "present"


@pytest.mark.parametrize("gap", ["\n나. 다른 과제\n", "\n2학년\n", "\n2학기\n"])
def test_new_boundary_prevents_continuation(gap):
    items = extract(form([]) + gap + table([["평가요소", "채점기준", "배점"],
                                           ["자료 해석", "모두 충족함", "10"],
                                           ["자료 해석", "일부 충족함", "5"]]))
    assert not items[0]["links"]
    assert items[0]["fields"]["rubric"]["status"] == "unconfirmed"


def test_markdown_scoring_table():
    text = ("| 수행과제 | 온도 변화 보고서 작성하기 |\n|---|---|\n"
            "| 평가방법 | 실험·실습 |\n| 평가요소 | 채점기준 | 배점 |\n"
            "| 결과 설명 | 결과를 모두 정확하게 설명함 | 10 |\n"
            "| 결과 설명 | 결과를 일부 설명함 | 5 |\n")
    assert extract(text)[0]["fields"]["rubric"]["status"] == "present"


@pytest.mark.parametrize("same_columns", [True, False])
def test_headerless_page_tail_requires_matching_criterion_columns(same_columns):
    first = form([["채점기준", "배점"], ["결과를 정확하게 설명함", "10"],
                  ["일부 설명함", "7"]])
    rows = [["설명이 미흡함", "4"], ["설명이 전혀 없음", "1"]]
    if not same_columns:
        rows = [row[::-1] for row in rows]
    items = extract(first + "\n<!-- page 2 -->\n" + table(rows))
    assert bool(items[0]["links"]) == same_columns
    if same_columns:
        evidence = items[0]["fields"]["rubric"]["evidence"]
        assert any(o["text"] == "설명이 전혀 없음" for o in evidence)


def test_converted_checkmark_is_selected_only_inside_method_cell():
    text = form([["평가방법", "∨ 서술·논술 □ 프로젝트"],
                 ["평가요소", "기호 ∨를 이용하여 논리를 설명하기"]])
    fields = extract(text)[0]["fields"]
    assert "서·논술" in fields["method"]["value"]
    assert fields["rubric"]["status"] == "unconfirmed"


@pytest.mark.parametrize("inline", [True, False])
def test_plain_labels_preserve_literal_evidence_and_remain_review(inline):
    title = ("수행과제: 온도 변화 보고서 작성하기\n" if inline else
             "수행과제\n온도 변화 보고서 작성하기\n")
    text = (title + "과제 개요: 온도 변화 자료를 분석하여 보고서를 작성한다.\n"
            "평가방법: 실험·실습\n평가요소\n계획 작성(4점)\n결과 설명(6점)\n"
            "채점기준\n상 결과를 모두 정확하게 설명함 10점\n하 결과 설명이 미흡함 3점\n")
    item = extract(text)[0]
    assert item["extraction_status"] == "review"
    assert item["fields"]["task_text"]["value"]
    assert field_status(item["fields"]["rubric"]) == "present"
    assert item["fields"]["method"]["value"] == ["실험·실습"]
    assert sorted(v["score"] for v in item["fields"]["sub_scores"]["value"]) == [4, 6]
