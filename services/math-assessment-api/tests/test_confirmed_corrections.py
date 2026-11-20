"""확인된 오류만 고치는 공개판 정정(N3 fresh7 뒤)의 사용법.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_confirmed_corrections.py
"""

import sqlite3
import zlib
from contextlib import closing

import pytest
from scripts import apply_confirmed_corrections as cc

SANGAN_F13 = (
    "평가방법 | ◻ 서술·논술 ◻ 구술·발표 ◻ 토의·토론 ◻ 프로젝트 \n"
    " ☑ 실험·실습 ◻ 포트폴리오 ◻ 기타 | \n"
    " | ☑ 교사 관찰 및 기록 ◻ 자기평가 ◻ 동료평가 | \n"
    " | 평가요소 | 수행수준(채점기준) | 배점 |")
HWIGYEONG = (
    "평가방법 | ■ 서술・논술 o 구술・발표 o 토의・토론 o 조사·관찰보고서"
    " ■ 실험・실습 \n o 실기·시연 o 포트폴리오 o 프로젝트 o 기타 ( ) | \n"
    " | ■ 교사 관찰 및 기록 o 자기평가 o 동료평가 | \n | 평가시기 |")
CHECK_O = (
    "평가방법 | ✔o 서술・논술 o 구술・발표 o 토의・토론 o 조사·관찰보고서"
    " ✔o 실험・실습 \n o 실기·시연 o 기타 ( ) | \n"
    " | ✔o 교사 관찰 및 기록 o 자기평가 o 동료평가 |")
TYPE_LABEL = (
    "평가 유형 | ◻ 서술･논술 ☑ 구술･발표 ◻ 토의･토론 ☑ 프로젝트 \n"
    " ◻ 포트폴리오 ◻ 자기평가 | \n"
    " | 교과 핵심역량 | ☑ 문제해결 ◻ 추론 ☑ 창의･융합 |")
LEAKED = "실험·실습 ◻ 포트폴리오 ◻ 기타 · 교사 관찰 및 기록 ◻ 자기평가 ◻ 동료평가"
ROWS_SQL = "SELECT item_id, extraction_status || '|' || method FROM assessment_items"


@pytest.mark.parametrize("title", [
    "평가의 종류 및 반영 비율", "평가 영역 및 반영 비율", "배점/ 반영비율",
    "배점(총 15점)", "2026학년도 1학기 1학년 평가 계획", "평가계획"])
def test_heading_titles_are_held(title):
    assert cc.heading_title(title)


@pytest.mark.parametrize("title", [
    "샤를 법칙 실험 반영비율", "평가 과제: 용수철의 탄성력 측정 실험",
    "물질의 상태 변화 탐구활동", "지필형 탐구평가"])
def test_task_titles_with_heading_words_stay(title):
    assert not cc.heading_title(title)


@pytest.mark.parametrize("source, expected", [
    (SANGAN_F13, ["실험·실습"]),
    (HWIGYEONG, ["서술・논술", "실험・실습"]),
    (CHECK_O, ["서술・논술", "실험・실습"]),
    (TYPE_LABEL, ["구술･발표", "프로젝트"]),
])
def test_checked_methods_come_from_source_boxes(source, expected):
    assert cc.source_checked_methods(source) == expected


def test_source_without_boxes_gives_none():
    assert cc.source_checked_methods("평가 방법 | 선택형 | 서․논술형 | 개별평가 |") is None


def test_unchecked_list_is_reread_and_blank_without_source_boxes():
    assert cc.corrected_method(LEAKED, SANGAN_F13) == "실험·실습"
    assert cc.corrected_method(LEAKED, "<p>원문에 방법 칸 없음</p>") == ""


@pytest.mark.parametrize("method, expected", [
    ("글쓰기 · 실험•실습 · 자기•동료평가", "글쓰기 · 실험•실습"),
    ("논술 · 토의 토론 · 교사의 관찰 및 기록", "논술 · 토의 토론"),
    ("개별평가 교사평가", ""),
    ("모둠 프로젝트", "모둠 프로젝트"),
    ("서술·논술 · 실험·실습", "서술·논술 · 실험·실습"),
    ("관찰평가", "관찰평가"),
])
def test_evaluator_pieces_are_dropped(method, expected):
    assert cc.corrected_method(method, "") == expected


def make_db(path, rows):
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY, school_code TEXT)")
        db.execute("CREATE TABLE assessment_items (item_id TEXT PRIMARY KEY, case_id TEXT,"
                   " grade INTEGER, title TEXT, method TEXT, source_html_zlib BLOB,"
                   " extraction_status TEXT)")
        db.executemany("INSERT INTO cases VALUES (?, ?)", {(r[1], r[1]) for r in rows})
        db.executemany("INSERT INTO assessment_items VALUES (?, ?, ?, ?, ?, ?, 'bounded')",
                       [(*r[:5], zlib.compress(r[5].encode())) for r in rows])


def read_rows(database):
    with closing(sqlite3.connect(database)) as db:
        return dict(db.execute(ROWS_SQL))


def test_apply_holds_and_cleans_in_place(tmp_path):
    database = tmp_path / "public.sqlite"
    school, grade, title = cc.CONFIRMED_GRADE_ERRORS[0]
    make_db(database, [
        ("heading", "S1", 1, "평가의 종류 및 반영 비율", "선택형", ""),
        ("grade", school, grade, title, "서술·논술", ""),
        ("same-title-grade2", school, 2, title, "서술·논술", ""),
        ("method", "S1", 1, "기화할 때 질량과 부피 변화 측정하기", LEAKED, SANGAN_F13),
        ("clean", "S1", 1, "부력 측정하기", "실험·실습", ""),
    ])
    report = cc.apply(database)
    rows = read_rows(database)
    assert rows == {"heading": "review|선택형", "grade": "review|서술·논술",
                    "same-title-grade2": "bounded|서술·논술", "method": "bounded|실험·실습",
                    "clean": "bounded|실험·실습"}
    assert report["held_heading_titles"] == 1 and report["held_confirmed_grade_errors"] == 1
    assert report["methods_cleaned"] == 1 and report["methods_blanked"] == 0
    cc.apply(database)
    assert read_rows(database) == rows
