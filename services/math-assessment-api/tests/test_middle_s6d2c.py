"""S6d-2c structural regressions using synthetic, school-independent inputs."""

import copy

import pytest
from scripts.middle_identity import reconcile_items
from scripts.middle_item_editions import edition_history, select_editions
from scripts.middle_items import extract_middle_items, ownership_errors, source_tables


def table(rows):
    return "<table>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row)
                                 + "</tr>" for row in rows) + "</table>"


def extract(text, **scope):
    items = extract_middle_items(text, {
        "document_id": "synthetic", "segment_id": "section", "section_id": "science",
        "grade": 1, "semester": 1, "status": "target", "boundary_verified": True,
        "header": {"key": "과학"}, "locator": {"start": 0, "end": len(text)}, **scope,
    })
    for item in items:
        for field in item["fields"].values():
            for obs in field["evidence"]:
                loc = obs["locator"]
                assert text[loc["start"]:loc["end"]] == obs["raw"]
    assert ownership_errors(items) == []
    return items


def overview():
    return ("<table><tr><td>평가유형</td><td colspan='2'>수행평가</td></tr>"
            "<tr><td>평가영역</td><td>온도 탐구</td><td>탐구 발표</td></tr>"
            "<tr><td>성취기준</td><td>[9과03-01]</td><td>[9과02-01]</td></tr>"
            "</table>")


def details():
    return (table([["과제명", "온도 탐구 결과 보고서 제작하기"],
                   ["성취기준", "[9과03-01]"]])
            + table([["과제명", "관찰 결과를 설명하는 발표하기"],
                     ["성취기준", "[9과02-01]"]]))


def test_order_and_code_link_different_titles_and_preserve_fields():
    items = extract(overview() + details())
    reconcile_items(items)
    assert sum(i["candidate_role"] == "summary_duplicate" for i in items) == 2
    assert items[-1]["fields"]["title"]["value"] == "관찰 결과를 설명하는 발표하기"
    assert len(items[-1]["fields"]["title"]["source_observations"]) == 2
    assert {"standards", "column_detail_order"} <= set(
        items[-1]["identity_relation"]["matched_fields"])


def test_title_inclusion_and_code_are_two_votes():
    text = overview() + table([["과제명", "온도 탐구 결과 보고서 제작하기"],
                                ["성취기준", "[9과03-01]"]])
    items = extract(text)
    reconcile_items(items)
    assert items[0]["candidate_role"] == "summary_duplicate"
    assert "title_containment" in items[-1]["identity_relation"]["matched_fields"]


def test_title_only_never_links():
    items = extract(overview() + table([["과제명", "온도 탐구"]]))
    reconcile_items(items)
    assert not any(i.get("identity_relation") for i in items)


@pytest.mark.parametrize("files,expected", [
    (["계획.hwpx", "계획(최종).hwpx"], 1),
    (["계획.hwpx", "계획(수정).hwpx"], 1),
    (["계획(최종).hwpx", "계획(26.08.21. 수정).hwpx"], 1),
    (["계획(26.08.21. 수정).hwpx", "계획(26.09.03. 수정).hwpx"], 1),
])
def test_general_edition_selection(files, expected):
    documents = [{"school_code": "synthetic", "grades": [1, 2], "filename": f,
                  "text_sha256": str(n), "converted_path": f"source-{n}",
                  "edition": {"file_seq": str(n)}} for n, f in enumerate(files)]
    select_editions(documents)
    assert [d["development_selected"] for d in documents] == [False, True]
    assert documents[expected]["representative_converted_path"] == f"source-{expected}"


def test_edition_history_retains_differences_and_representative_value():
    documents = [{"school_code": "synthetic", "filename": f"계획{suffix}.hwpx",
                  "grades": [1], "converted_path": str(n), "text_sha256": str(n)}
                 for n, suffix in enumerate(("", "(수정)"))]
    select_editions(documents)
    first = extract(table([["과제명", "온도 탐구하기"], ["만점", "30점"]]))[0]
    second = copy.deepcopy(first)
    first["converted_path"], second["converted_path"] = "0", "1"
    second["fields"]["score"]["value"] = 40
    items, history = edition_history(documents, [first, second])
    assert items[0]["fields"]["score"]["value"] == 40
    assert history[0]["differences"][0]["fields"]["score"] == {
        "previous": 30, "representative": 40,
    }


def test_identical_body_and_publication_order_select_one_edition():
    documents = [{"school_code": "synthetic", "filename": f"{name} 1학기.hwpx",
                  "grades": [1], "converted_path": str(n), "text_sha256": "same-body",
                  "edition": {"file_seq": str(n)}}
                 for n, name in enumerate(("교과별 계획", "과목 평가 계획"))]
    select_editions(documents)
    assert [d["development_selected"] for d in documents] == [True, False]


def test_combined_document_grade_is_structural_and_conflict_is_review():
    text = "# 과학\n가. 2학년\n" + table([["과제명", "온도 탐구하기"],
                                                   ["성취기준", "[9과03-01]"]])
    item = extract(text)[0]
    assert item["extraction_status"] == "review"
    assert "항목 학년 표지와 S5 학년 귀속 충돌" in item["review_reasons"]
    assert extract(text, grade=2)[0]["extraction_status"] == "bounded"


@pytest.mark.parametrize("program", ["주제선택(탐구반)", "특성화 프로그램", "동아리", "예술·체육"])
def test_other_programme_heading_excludes_science_items(program):
    text = f"# 2026학년도 1학년 1학기 {program}\n" + table([
        ["과제명", "온도 탐구하기"], ["성취기준", "[9과03-01]"],
    ])
    assert all(i["extraction_status"] == "review" for i in extract(text))


def test_science_heading_resets_programme_scope():
    text = "# 주제선택(탐구반)\n# 과학과 교수학습 및 평가계획\n" + table([
        ["과제명", "온도 탐구하기"],
    ])
    assert extract(text)[0]["extraction_status"] == "bounded"


@pytest.mark.parametrize("scale", [("상", "중", "하"), ("A", "B", "C", "D", "E")])
def test_unscored_free_semester_with_decorated_labels(scale):
    text = "자유학기 이수/미이수\n" + table([
        ["➊ 평가영역", "온도 탐구하기"], ["성취기준", "[9과03-01]"],
        ["➊ 평가요소", "➋ 수행수준(채점기준)"],
        *[[s, f"{s} 수준에서 관찰 결과를 정확하게 기록함"] for s in scale],
    ])
    item = extract(text)[0]
    assert item["extraction_status"] == "bounded"
    assert item["fields"]["score"]["value"] == ""
    assert item["fields"]["free_semester"]["value"] is True


def test_method_header_can_hold_literal_activity_title():
    text = ("<table><tr><td>종류</td><td colspan='2'>수행평가</td></tr>"
            "<tr><td>평가유형</td><td>온도 탐구하기</td><td>결과 발표하기</td></tr>"
            "<tr><td>성취기준</td><td>[9과03-01]</td><td>[9과02-01]</td></tr></table>")
    assert [i["fields"]["title"]["value"] for i in extract(text)] == [
        "온도 탐구하기", "결과 발표하기",
    ]


def test_empty_span_collision_is_distinct_from_value_collision():
    text = ("<table><tr><td>과제명</td><td colspan='2'>온도 탐구하기</td></tr>"
            "<tr><td colspan='2'></td><td rowspan='2'></td></tr>"
            "<tr><td colspan='3'>관찰 기록</td></tr></table>")
    parsed = source_tables(text)[0]
    assert parsed["structure_verified"]
    assert parsed["empty_span_overlaps"]
    assert not source_tables(text.replace("rowspan='2'></td>",
                                         "rowspan='2'>내용</td>"))[0]["structure_verified"]


def test_experiment_practice_is_an_area_item():
    item = extract(table([["과제명", "실험·실습"], ["성취기준", "[9과03-01]"]]))[0]
    assert item["fields"]["title"]["value"] == "실험·실습"
    assert item["extraction_status"] == "bounded"


def test_explicit_short_task_description_wins_over_area():
    item = extract(table([["평가영역", "서·논술형"],
                          ["활동내용", "관찰 결과를 과학 만화로 표현하기"]]))[0]
    assert item["fields"]["title"]["value"] == "관찰 결과를 과학 만화로 표현하기"
    assert item["title_role"] == "task"


def test_programme_context_survives_internal_science_subheading():
    text = ("# 2026학년도 1학년 주제선택(탐구반)\n"
            "| 학년 | 과목 | 학기 |\n| --- | --- | --- |\n"
            "| 1학년 | 탐구반 | 1학기 |\n# 과학과 교수학습\n"
            + table([["과제명", "온도 탐구하기"]]))
    assert extract(text)[0]["extraction_status"] == "review"


def test_markdown_grade_plan_heading_overrides_previous_grade():
    text = ("가. 1학년\n| 2 |  | 2학년 1학기 평가 계획 |\n| --- | --- | --- |\n"
            + table([["과제명", "온도 탐구하기"]]))
    item = next(i for i in extract(text) if i["layout"] == "form")
    assert item["extraction_status"] == "review"
