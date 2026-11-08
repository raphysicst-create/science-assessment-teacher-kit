"""School-independent assessment ownership and title regressions."""

from types import SimpleNamespace

import pytest
from scripts.middle_assessment_scope import assessment_items
from scripts.middle_identity import reconcile_items, title_key
from scripts.middle_items import extract_middle_items, ownership_errors, source_tables, title_gate
from scripts.middle_pdf_summary import matched_part, physical_columns


def table(rows):
    return "<table>" + "".join("<tr>" + "".join(f"<td>{v}</td>" for v in row)
                                 + "</tr>" for row in rows) + "</table>"


def scope(text, grade=1, term=2, end=None):
    return {"document_id": "synthetic", "child_id": None, "segment_id": "source",
            "section_id": "science", "grade": grade, "semester": term,
            "status": "target", "boundary_verified": True, "header": {"key": "과학"},
            "semester_evidence": [{"semester": term, "source": "body_heading",
                                   "text": f"{term}학기", "start": text.index(f"{term}학기"),
                                   "end": text.index(f"{term}학기") + 3}],
            "grade_evidence": [], "locator": {"start": 0, "end": end or len(text)}}


def recover(text, templates):
    conversion = {"text": text, "converter": "synthetic", "item_source_tables": source_tables(text)}
    items = assessment_items(text, templates, conversion, [])
    assert ownership_errors(items) == []
    for item in items:
        for field in item["fields"].values():
            for obs in field["evidence"]:
                loc = obs["locator"]
                assert text[loc["start"]:loc["end"]] == obs["raw"]
    return items


@pytest.mark.parametrize("subject,count", [("과학", 1), ("수학", 0), ("국어", 0)])
def test_outside_science_section_requires_subject_cell(subject, count):
    text = "# 1학년 2학기 교수학습 계획\n" + table([
        ["학년", "과목", "평가영역", "만점", "비율", "시기"],
        ["1", subject, "관찰 결과 발표하기", "100", "20%", "9월"],
    ])
    items = recover(text, [scope(text, end=text.index("<table>"))])
    assert len(items) == count
    if items:
        proof = items[0]["boundary_evidence"]["assessment_scope"]
        assert proof["subject"][0]["basis"] == "subject_cell"
        assert proof["subject"][0]["raw"] == "과학"


def test_all_grades_subjects_and_terms_are_filtered_by_row_with_rowspan():
    text = "# 1학기 및 2학기 평가 계획\n<table><tr>" + "".join(
        f"<th>{h}</th>" for h in ("학년", "학기", "과목", "평가영역", "만점", "비율", "시기",
                                "성취기준")) + "</tr>" + (
        "<tr><td rowspan='2'>1</td><td>2</td><td>수학</td><td>다른 과제</td>"
        "<td>100</td><td>20%</td><td>9월</td><td>[9수01-01]</td></tr>"
        "<tr><td>2</td><td>과학</td><td>온도 기록하기</td><td>100</td>"
        "<td>20%</td><td>9월</td><td>[9과03-01]</td></tr>"
        "<tr><td>2</td><td>1</td><td>과학</td><td>관찰 발표하기</td><td>50</td>"
        "<td>10%</td><td>4월</td><td>[9과02-01]</td></tr>"
        "<tr><td>3</td><td>2</td><td>과학</td><td>대상 외 과제</td><td>50</td>"
        "<td>10%</td><td>9월</td><td>[9과02-01]</td></tr></table>")
    items = recover(text, [scope(text), scope(text, grade=2, term=1)])
    assert {(i["grade"], i["semester"], i["fields"]["title"]["value"]) for i in items} == {
        (1, 2, "온도 기록하기"), (2, 1, "관찰 발표하기"),
    }


@pytest.mark.parametrize("prefix,expected", [("# 과학과 평가 계획", 1),
                                               ("# 수학과 평가 계획", 0), ("", 0)])
def test_codeless_detached_table_needs_subject_heading(prefix, expected):
    text = prefix + "\n# 1학년 2학기\n" + table([
        ["평가과제", "결과 비교하기"], ["만점", "30점"], ["평가시기", "10월"],
    ])
    assert len(recover(text, [scope(text)])) == expected


def test_unmixed_code_prefix_is_subject_evidence_but_never_grade_evidence():
    text = "# 1학년 2학기\n" + table([
        ["평가과제", "실험 결과 비교하기"], ["성취기준", "[9과15-03]"], ["만점", "20점"],
    ])
    item = recover(text, [scope(text)])[0]
    assert item["grade"] == 1
    assert item["boundary_evidence"]["assessment_scope"]["subject"][0]["basis"] == (
        "unmixed_standards_prefix")


def test_unknown_grade_row_and_conflicting_semester_cannot_inherit_other_rows():
    text = "# 1학년 2학기\n" + table([
        ["학년", "과목", "평가영역", "만점", "비율"],
        ["1", "과학", "온도 기록하기", "100", "20%"],
        ["미정", "과학", "미확정 과제", "100", "20%"],
    ])
    assert [i["fields"]["title"]["value"] for i in recover(text, [scope(text)])] == [
        "온도 기록하기"]
    template = scope(text)
    text = text.replace("1학년 2학기", "1학년 1학기")
    assert not recover(text, [template])


@pytest.mark.parametrize("fragment", ["를 읽고 결과 설명하기", "을 이용해 모형 제작하기",
                                     "의 특징 설명하기"])
def test_particle_leading_title_fragment_is_rejected(fragment):
    assert not title_gate(fragment)["accepted"]


@pytest.mark.parametrize("task", ["광물이 없는 생활의 변화를 서술한다.",
                                 "<관찰의 역사>를 읽고<br>관찰 방법을 설명하기"])
@pytest.mark.parametrize("area", ["", "과학탐구평가"])
def test_empty_or_generic_title_uses_owned_explicit_task_preserving_raw(task, area):
    text = "# 1학년 2학기\n" + table([
        ["평가영역", area], ["수행과제", task],
        ["성취기준", "[9과03-01]"], ["만점", "100점"],
    ])
    item = extract_middle_items(text, scope(text))[0]
    assert item["extraction_status"] == "bounded"
    title = item["fields"]["title"]
    assert title["value"] == task.replace("<br>", " ")
    assert title["evidence"][0]["raw"] == task
    assert title["status"] == "present"


def test_first_numbered_task_after_general_section_heading():
    text = "# 1학년 2학기\n라. 영역별 세부 평가 기준\n1) 관찰 계획서 작성하기\n" + table([
        ["성취기준", "[9과01-01]"], ["평가방법", "프로젝트"],
        ["평가요소", "수행수준(채점기준)"], ["탐구 동기", "A"],
    ])
    assert extract_middle_items(text, scope(text))[0]["fields"]["title"]["value"] == (
        "관찰 계획서 작성하기")


@pytest.mark.parametrize("task", ["고체의 성질을 해석하고 일상 사례에 적용하여 설명한다.",
                                 "광물이 없을 경우 생활의 변화 서술하기", "관찰 포트폴리오"])
def test_physical_area_heading_cannot_conflict_with_explicit_task_cell(task):
    heading = "과학적 글쓰기"
    text = "# 1학년 2학기\n가. " + heading + "\n" + table([
        ["평가영역", heading], ["수행과제", task], ["만점", "100점"],
        ["성취기준", "[9과03-01]"],
    ])
    start = text.index(heading)
    item = extract_middle_items(text, scope(text), {
        "text": text, "physical": {"titles": {"0": {
            "raw": heading, "text": heading, "start": start, "end": start + len(heading),
            "source_cell_proof": {"basis": "synthetic_verified_heading"},
        }}},
    })[0]
    assert item["fields"]["title"]["value"] == task
    assert item["fields"]["title"]["status"] == "present"
    assert item["fields"]["title"]["evidence"][0]["header_raw"] == "수행과제"
    assert heading in [o["text"] for o in item["fields"]["assessment_area"]["evidence"]]


def test_task_heading_before_matching_grade_heading():
    text = "# 2학기\n1) 실험·실습 (10점)\n가. 2학년\n" + table([
        ["성취기준", "[9과15-03]"], ["평가방법", "실험·실습"],
        ["평가요소", "채점기준"], ["기구 조작", "정확함"],
    ])
    assert extract_middle_items(text, scope(text, grade=2))[0]["extraction_status"] == "bounded"


@pytest.mark.parametrize("dot", ["·", "‧", "⋅", "•", "・"])
def test_middle_dot_variants_link_unique_area_with_two_independent_fields(dot):
    text = ("# 1학년 2학기\n<table><tr><td>구분</td><td colspan='2'>수행평가</td></tr>"
            f"<tr><td>평가영역</td><td>서{dot}논술형</td><td>실험·실습</td></tr>"
            "<tr><td>만점</td><td>10점</td><td>20점</td></tr>"
            "<tr><td>시기</td><td>10월</td><td>9월</td></tr></table>"
            + table([["평가영역", "실험·실습"], ["만점", "20점"], ["시기", "9월"]])
            + table([["평가영역", "서·논술형"], ["만점", "10점"], ["시기", "10월"]]))
    items = extract_middle_items(text, scope(text))
    reconcile_items(items)
    assert sum(i["candidate_role"] == "summary_duplicate" for i in items) == 2
    assert all(i["fields"]["title"]["value"] for i in items)
    assert items[0]["fields"]["assessment_area"]["evidence"][0]["raw"] == f"서{dot}논술형"
    assert title_key(f"서{dot}논술형") == title_key("서·논술형")


@pytest.mark.parametrize("dot", ["·", "‧", "⋅", "•", "・"])
def test_generic_dot_alias_does_not_join_a_different_concrete_task(dot):
    text = ("# 1학년 2학기\n<table><tr><td>구분</td><td colspan='2'>수행평가</td></tr>"
            f"<tr><td>평가영역</td><td>서{dot}논술형</td><td>프로젝트</td></tr>"
            "<tr><td>만점</td><td>10점</td><td>20점</td></tr>"
            "<tr><td>시기</td><td>10월</td><td>9월</td></tr></table>"
            + table([["평가영역", f"서{dot}논술형"], ["평가과제", "다른 결과 분석하기"],
                     ["만점", "10점"], ["시기", "10월"]]))
    items = extract_middle_items(text, scope(text))
    reconcile_items(items)
    assert not any(i.get("identity_relation") for i in items)


def test_physical_group_excludes_exam_columns_and_mapper_keeps_original_offsets():
    values = [["평가유형", "정기시험", None, "수행평가", None],
              ["평가영역", "1차", "2차", "탐구활동", "포트폴리오"],
              ["영역만점(반영비율)", "100(30%)", "100(30%)", "100(20%)", "100(20%)"],
              ["평가시기", "10월", "12월", "9월", "학기중"],
              ["교육과정성취기준", "[9과01-01]", "[9과01-01]", "[9과01-01]", "[9과02-01]"]]
    rows = [SimpleNamespace(cells=[(0, r, 1, r+1), (1, r, 3, r+1), None,
                                   (3, r, 5, r+1), None]) for r in range(5)]
    rows[1].cells = [(c, 1, c+1, 2) for c in range(5)]
    assert [c for c, _ in physical_columns(values, rows)] == [3, 4]
    cell = {"raw": "12월 2일<br>9월 1주", "text": "12월 2일 9월 1주", "start": 50, "end": 67}
    part = matched_part(cell, "9월1주")
    assert part["raw"] == "9월 1주"
    assert part["start"] == 50 + cell["raw"].index("9월")
