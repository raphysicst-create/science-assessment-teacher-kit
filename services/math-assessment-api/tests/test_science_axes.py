"""S8 활동 축 정의 검사(완료 기준 2). 실제 파일과 가짜 입력 둘 다 검사한다.

Run: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_science_axes.py
"""

import copy
import json

import pytest
from scripts import check_science_axes as check

AXES = check.load_json(check.AXES_PATH)
STANDARDS = check.load_json(check.STANDARDS_PATH)


def test_units_cover_23_areas_and_87_standards():
    assert check.check_units(AXES, STANDARDS) == []
    assert len(AXES["units"]["areas"]) == 23
    assert sum(len(a["standards"]) for a in AXES["units"]["areas"]) == 87


def test_activities_have_definition_examples_and_rules():
    assert check.check_activities(AXES) == []
    assert [a["name"] for a in AXES["activities"]] == [
        "탐구", "실험평가", "작성", "제작", "분석", "추론·설명", "발표·토론", "계산·측정", "과정평가", "문제해결"]


def test_definition_document_matches_json():
    text = check.DOC_PATH.read_text(encoding="utf-8")
    assert check.check_document(AXES, text) == []


def test_citations_resolve_to_development_sample_items():
    items = check.load_sample_items(AXES["sample_rounds"])
    if items is None:
        pytest.skip("개발 표본 항목 파일(data/derived/items) 없음")
    assert check.check_citations(AXES, items) == []


def test_checker_reports_broken_inputs():
    broken = copy.deepcopy(AXES)
    broken["units"]["areas"][0]["standards"].pop()
    broken["activities"][0]["id"] = broken["activities"][1]["id"]
    broken["activities"][2]["includes"] = broken["activities"][2]["includes"][:1]
    broken["activities"][3]["definition"] = "첫 문장. 둘째 문장."
    broken["activities"][4]["boundary"][0]["ruling"] = "없는활동"
    problems = check.check_units(broken, STANDARDS) + check.check_activities(broken)
    joined = "\n".join(problems)
    assert "성취기준 수 86" in joined
    assert "활동 id 중복" in joined
    assert "포함 사례 1" in joined
    assert "정의가 1문장이 아님" in joined
    assert "없는활동" in joined


def test_citation_checker_rejects_gold_and_fabricated_quotes():
    fake_items = {"item_x": {"item_id": "item_x", "school": "가상중", "fields": {"title": {"value": "밀도 구하기"}}}}
    axes = {"activities": [{"id": "t", "includes": [
        {"item_id": "item_x", "school": "가상중", "round": "2026-round-1-gold", "title": "밀도 구하기",
         "quote": "지어낸 인용"},
        {"item_id": "item_y", "school": "가상중", "round": "2026-round-3", "title": "없음", "quote": "x"},
    ], "excludes": [], "boundary": []}]}
    problems = check.check_citations(axes, fake_items)
    assert any("정답 세트 회차" in p for p in problems)
    assert any("원문에 없음" in p for p in problems)
    assert any("인용 항목 없음" in p for p in problems)


def test_run_on_real_files_has_no_problems():
    report = check.run()
    assert report["problems"] == [], json.dumps(report["problems"], ensure_ascii=False)
