"""Check course-subject guards with synthetic plans and saved fake AI responses.

Run/verify: .venv/Scripts/python.exe -m pytest -q
            services/math-assessment-api/tests/test_n2_course_subject.py
No real AI calls or source fixtures; temporary outputs stay under tmp_path.
"""

import importlib
from pathlib import Path

import pytest
from middle_ai_first_fixtures import TEXT, install_documents, pipeline, task
from middle_ai_first_fixtures import offline as offline
from middle_ai_first_fixtures import root as root
from scripts import middle_ai_first as first
from scripts import middle_ai_read as ai
from scripts.course_subject import MAX_LOOKBACK_LINES, course_name_before, is_non_science_course

PROJECT = Path(__file__).resolve().parents[3]
ROUND = "synthetic-first"
HEADERS = ("과목", "과목명", "강좌", "강좌명", "프로그램", "프로그램명")


def markdown_cover(course):
    return ("2026학년도 교수학습 및 평가 계획\n"
            "| 학년 | 과목 | 학기 | 학급 |\n| --- | --- | --- | --- |\n"
            f"| 1학년 | {course} | 1학기 | 1~3반 |\n")


@pytest.mark.parametrize("header", HEADERS)
@pytest.mark.parametrize("html", [False, True])
def test_course_column_next_data_row(header, html):
    if html:
        lines = ["교수·학습 및 평가 계획", "<table>",
                 f'<tr><th>학년</th><th class="subject">{header}</th><th>학기</th></tr>',
                 "<tr><td>1학년</td><td><b>코딩반</b></td><td>1학기</td></tr>",
                 "</table>", "수행평가 [9과01-01]"]
    else:
        lines = ["교수·학습 및 평가 계획", f"| 학년 | {header} | 학기 |",
                 "| :--- | ---: | --- |", "", "| 1학년 | 코딩반 | 1학기 |",
                 "수행평가 [9과01-01]"]
    result = course_name_before(lines, len(lines))
    assert result == {"course": "코딩반", "line": 4 if html else 5, "kind": "table"}
    assert is_non_science_course(result["course"])


@pytest.mark.parametrize("phrase", ["주제선택활동(코딩반)", "주제선택（코딩반）",
                                   "자유학기 활동 (코딩반)",
                                   "자유학기(1학년) 주제선택활동(코딩반)"])
def test_course_name_in_plan_title(phrase):
    lines = [f"# 2026학년도 {phrase} 교수학습 및 평가 계획", "수행평가"]
    assert course_name_before(lines, 2) == {"course": "코딩반", "line": 1, "kind": "title"}


@pytest.mark.parametrize("name,blocked", [
    ("코딩반", True), ("로봇제작", True), ("수학", True), ("과학", False),
    (" 과 학 탐구반 ", False), ("", False), ("  ", False), ("공통", False),
    ("전교과", False), ("통합", False), ("전 과목", False),
    # N2 개발 회차 오탐: 과학 동아리·주제 이름·칸이 어긋난 머리표는 막지 않는다(fail-open).
    ("싸이언스 홀릭", False), ("주제선택 (지구의 세포들)", False), ("1학년", False),
    ("정보", True), ("수학탐구", True),
    # N2 검수: 과학 낱말·과학 주제 낱말이 없는 강좌는 막는다.
    ("디지털리터러시", True), ("연극반", True), ("경제금융", True), ("자기주도학습반", True),
    ("생태 환경 탐사반", False),
    # N2 묶음 1 실데이터: 강좌명이 아닌 머리 칸 값·과제 문장은 판단하지 않는다.
    ("2회 정기시험", False), ("주제선택활동", False),
    ("모형을 이용하여 달의 위상 변화 관찰하기", False),
    ("진로탐색활동", True), ("쓸모의 재발견", True), ("즐거운수학", True),
])
def test_non_science_course_names(name, blocked):
    assert is_non_science_course(name) is blocked


def test_science_table_and_nearest_plan_boundary():
    lines = (markdown_cover("코딩반")
             + "이전 과제\n과학과 교수ㆍ학습 및 평가 계획\n수행평가").splitlines()
    assert course_name_before(lines, len(lines)) is None
    lines = (markdown_cover("코딩반") + markdown_cover("과학") + "수행평가").splitlines()
    assert course_name_before(lines, len(lines)) == {"course": "과학", "line": 8, "kind": "table"}


def test_policy_sentences_and_subsection_parentheses_are_not_course_titles():
    lines = (markdown_cover("코딩반") + "# 주제선택(진로탐색)활동평가 세부계획\n"
             "### 교수·학습 및 평가계획에 반영한다.\n"
             "### 다. 확정된 평가 계획은 학생과 학부모에게 공개한다.\n수행평가").splitlines()
    assert course_name_before(lines, len(lines)) == {"course": "코딩반", "line": 4, "kind": "table"}


def test_lookback_has_exactly_600_lines_and_does_not_seek_a_future_value():
    lines = ["| 과목 |", "| 코딩반 |"] + ["본문"] * (MAX_LOOKBACK_LINES - 2)
    assert course_name_before(lines, MAX_LOOKBACK_LINES)["course"] == "코딩반"
    lines.append("수행평가")
    assert course_name_before(lines, MAX_LOOKBACK_LINES + 1) is None
    assert course_name_before(["| 과목 |", "| 코딩반 |"], 1) is None
    assert course_name_before(lines, 0) is None


@pytest.mark.parametrize("course,blocked", [("코딩반", True), ("과학", False), ("공통", False)])
def test_ai_first_verify_filters_saved_fake_answers_by_evidence_first_line(root, course, blocked):
    text = markdown_cover(course) + TEXT
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    answer = task(title_line=6, evidence=[{"line_start": 6, "line_end": 6,
                                         "quote": "온도 관찰 보고서"}],
                  grade_evidence={"line": 5, "quote": "1학년"},
                  semester_evidence={"line": 5, "quote": "1학기"},
                  detail_lines={"line_start": 6, "line_end": 11},
                  methods=[{"text": "실험", "line": 8}])
    output, report = pipeline(root, [answer])
    assert len(report["kept"]) == int(not blocked)
    assert [e["reason"] for e in report["discarded"]] == (
        ["other_subject_course:코딩반"] if blocked else [])
    if blocked:
        assert report["discarded"][0]["course_evidence"]["line"] == 4
    saved = {p.name: p.read_bytes() for p in (output / "responses").iterdir()}
    assert first.verify_targets(root, ROUND) == report
    assert {p.name: p.read_bytes() for p in (output / "responses").iterdir()} == saved


def test_ai_first_uses_earliest_verified_evidence_not_title_or_detail(tmp_path, monkeypatch):
    text = markdown_cover("코딩반") + markdown_cover("과학") + "과제 제목\n"
    target = {"target_id": "fake"}
    verified = {"grade": 1, "title_line": 9, "evidence": [
        {"line_start": 9}, {"line_start": 4}]}
    monkeypatch.setattr(ai, "parse_response", lambda *_: {"tasks": [{}], "uncertain": []})
    monkeypatch.setattr(ai, "verify_task", lambda *_: verified)
    monkeypatch.setattr(first, "verify_extras", lambda *_: verified)
    kept, discarded = [], []
    first.verify_response(target, tmp_path, {"text": text}, kept, discarded, [], [])
    assert kept == []
    assert [e["reason"] for e in discarded] == ["other_subject_course:코딩반"]


def install_rule_plan(tmp_path, course):
    form = ("<table>\n<tr><td>평가영역</td><td>온도 변화 탐구</td></tr>\n"
            "<tr><td>평가방법</td><td>☑ 실험·실습</td></tr>\n"
            "<tr><td>만점(점)</td><td>100</td></tr>\n"
            "<tr><td>성취기준</td><td>[9과01-01]</td></tr>\n</table>")
    text = markdown_cover(course) + form
    path = "conversion.json"
    document = {"document_id": "doc", "converted_path": path, "text_sha256": ai.sha(text),
                "original_path": "plan.hwp", "filename": "계획.hwp", "grades": [1],
                "school": "가상중", "school_code": "1"}
    section = {"document_id": "doc", "child_id": None, "segment_id": "seg",
               "section_id": "subj", "converted_path": path, "school": "가상중", "grade": 1,
               "status": "target", "science_candidate": True, "boundary_verified": True,
               "header": {"key": "과학", "raw": "과학"},
               "locator": {"start": len(text) - len(form), "end": len(text)}}
    source = {**document, "edition": {}, "sha256": "a" * 64, "segments": [
        {"segment_id": "seg", "grade_evidence": [], "semester": 1, "semester_evidence": []}]}
    ai.save_json(tmp_path / path, {"text": text, "converter": "synthetic"})
    ai.save_json(tmp_path / f"data/derived/segments/{ROUND}.json", {"documents": [source]})
    input_path = tmp_path / "subjects.json"
    ai.save_json(input_path, {"round": ROUND, "documents": [document], "sections": [section]})
    return input_path


@pytest.mark.parametrize("course,blocked", [("코딩반", True), ("과학", False)])
def test_rule_items_audit_excludes_course_despite_science_codes(tmp_path, monkeypatch,
                                                              course, blocked):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    audit = importlib.import_module("audit_middle_items")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    input_path = install_rule_plan(tmp_path, course)
    report = audit.audit(input_path)
    assert bool(report["items"]) is not blocked
    assert [e["reason"] for e in report["excluded"]] == (
        ["other_subject_course"] if blocked else [])
    if blocked:
        assert report["summary"]["bounded"] == 0
        assert report["excluded"][0]["course_evidence"] == {
            "course": course, "line": 4, "kind": "table"}
    else:
        assert report["summary"]["bounded"] == 1
        assert report["items"][0]["fields"]["standards"]["value"] == ["[9과01-01]"]


def test_science_heading_stops_before_previous_subject_cover():
    # N2 개발 회차: "# 과학 평가" 아래 항목이 수백 줄 위 수학 계획 머리표를 가져오면 안 된다.
    lines = ["# 평가 운영 계획", "| 학교명 | 과목 | 학년 |", "| --- | --- | --- |",
             "| 가중 | 수학 | 1 |", *["본문"] * 50, "# 과학 평가", "", "온도 관찰 보고서"]
    found = course_name_before(lines, len(lines))
    assert found == {"course": "과학", "line": len(lines) - 2, "kind": "heading"}
    assert not is_non_science_course(found["course"])


def test_science_word_in_policy_heading_is_not_a_boundary():
    # 코딩반 계획 안의 방침 문장 "### 아. … 과학적 문제 해결력"은 경계가 아니다.
    lines = ["2026학년도 자유학기 주제선택활동(코딩반)", "교수학습 및 평가 계획", "",
             "| 학년 | 과목 | 학기 |", "| --- | --- | --- |", "| 1학년 | 코딩반 | 1학기 |",
             "### 아. 창의적 사고력, 과학적 문제 해결력을 평가한다.", "",
             "메타버스 학교 만들기"]
    found = course_name_before(lines, len(lines))
    assert found["course"] == "코딩반" and is_non_science_course(found["course"])
