"""보류 카드가 생긴 뒤 사례 요약 다시 계산·검사의 사용법.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_refresh_case_summaries.py
"""

import json
import sqlite3
from contextlib import closing

from scripts import check_science_case_summaries as checker
from scripts import refresh_science_case_summaries as rs

CLEAN = {name: 0 for name in checker.CHECKS}
SNAPSHOT_TABLES = ("cases", "case_task_names", "case_action_tags", "case_detail_status",
                   "assessment_item_rankings")


def rows(database, sql, parameters=()):
    with closing(sqlite3.connect(database)) as db:
        return db.execute(sql, parameters).fetchall()


def execute(database, sql, parameters=()):
    with closing(sqlite3.connect(database)) as db, db:
        db.execute(sql, parameters)


def snapshot(database):
    return {table: rows(database, f"SELECT * FROM {table} ORDER BY 1, 2")
            for table in SNAPSHOT_TABLES}


CARD_TABLES = ("assessment_items", "assessment_item_axes")


def card_snapshot(database):
    return {table: rows(database, f"SELECT * FROM {table} ORDER BY 1, 2")
            for table in CARD_TABLES}


def case_cards(database):
    """사례 하나와 그 카드 (item_id, title_raw) 목록(item_order 순). 데모는 사례마다 카드 2장."""
    case_id = rows(database, "SELECT case_id FROM cases ORDER BY case_id LIMIT 1")[0][0]
    cards = rows(database, "SELECT item_id, title_raw FROM assessment_items "
                           "WHERE case_id = ? ORDER BY item_order", (case_id,))
    return case_id, cards


def hold(database, item_id):
    execute(database, "UPDATE assessment_items SET extraction_status = 'review' "
                      "WHERE item_id = ?", (item_id,))


def test_fresh_build_is_left_unchanged(science_demo):
    database = science_demo["database"]
    before = snapshot(database)
    report = rs.refresh(database)
    assert report["changed_cases"] == 0 and report["rankings_fixed"] == 0
    assert report["held_cases"] == 0 and report["public_cases"] == report["cases"] == 2
    assert snapshot(database) == before
    assert checker.check(database) == CLEAN


def test_held_card_title_leaves_the_case_summary(science_demo):
    database, client = science_demo["database"], science_demo["client"]
    case_id, cards = case_cards(database)
    (held_id, held_title), (_, kept_title) = cards
    hold(database, held_id)
    stale = checker.check(database)
    assert stale["held_title_listed"] == 1 and stale["title_count_differs"] == 1
    assert stale["primary_not_first_card"] == 1
    cards_before = card_snapshot(database)

    report = rs.refresh(database)

    assert card_snapshot(database) == cards_before
    assert report["changed_cases"] == 1 and report["held_cases"] == 0
    assert checker.check(database) == CLEAN
    listed = {item["case_id"]: item for item in client.get("/api/v1/cases").json()["items"]}
    assert listed[case_id]["primary_task_name"] == kept_title
    assert listed[case_id]["task_names"] == [kept_title]
    assert held_title not in listed[case_id]["evidence_excerpt"]
    assert rows(database, "SELECT task_name FROM case_task_names WHERE case_id = ?",
                (case_id,)) == [(kept_title,)]
    assert rs.refresh(database)["changed_cases"] == 0


def test_case_without_public_cards_leaves_the_library_and_can_return(science_demo):
    database, client = science_demo["database"], science_demo["client"]
    case_id, cards = case_cards(database)
    for item_id, _ in cards:
        hold(database, item_id)
    assert checker.check(database)["public_case_without_card"] == 1
    assert client.get("/api/v1/cases").json()["total"] == 2
    cards_before = card_snapshot(database)

    report = rs.refresh(database)

    assert card_snapshot(database) == cards_before
    assert report["held_cases"] == 1 and report["held_case_ids"] == [case_id]
    assert checker.check(database) == CLEAN
    library = client.get("/api/v1/cases").json()
    assert library["total"] == 1
    assert case_id not in [item["case_id"] for item in library["items"]]
    assert client.get(f"/api/v1/cases/{case_id}").status_code == 404
    assert sum(row["count"] for row in client.get("/api/v1/facets").json()["regions"]) == 1

    execute(database, "UPDATE assessment_items SET extraction_status = 'bounded' "
                      "WHERE case_id = ?", (case_id,))
    assert checker.check(database)["card_case_not_public"] == 1
    assert rs.refresh(database)["held_cases"] == 0
    assert checker.check(database) == CLEAN
    assert client.get("/api/v1/cases").json()["total"] == 2


def test_blank_method_drops_the_method_signal_and_score(science_demo):
    database = science_demo["database"]
    item_id, case_id, score = rows(
        database,
        "SELECT r.item_id, i.case_id, r.priority_score FROM assessment_item_rankings r "
        "JOIN assessment_items i ON i.item_id = r.item_id "
        "WHERE r.priority_signals_json LIKE ? ORDER BY r.item_id LIMIT 1",
        (f"%{rs.METHOD_SIGNAL}%",))[0]
    execute(database, "UPDATE assessment_items SET method = '' WHERE item_id = ?", (item_id,))

    assert rs.refresh(database)["rankings_fixed"] == 1

    new_score, signals = rows(
        database, "SELECT priority_score, priority_signals_json FROM assessment_item_rankings "
                  "WHERE item_id = ?", (item_id,))[0]
    assert new_score == score - rs.METHOD_WEIGHT
    assert rs.METHOD_SIGNAL not in json.loads(signals)
    stored = rows(database, "SELECT assessment_method_marker_count FROM cases "
                            "WHERE case_id = ?", (case_id,))[0][0]
    with_method = rows(database, "SELECT COUNT(*) FROM assessment_items "
                                 "WHERE case_id = ? AND method != ''", (case_id,))[0][0]
    assert stored == with_method
    assert rs.refresh(database)["rankings_fixed"] == 0


def test_public_card_the_detail_api_would_hide_is_reported(science_demo):
    database, client = science_demo["database"], science_demo["client"]
    case_id, cards = case_cards(database)
    item_id = cards[0][0]
    assert client.get(f"/api/v1/assessment-items/{item_id}").status_code == 200
    execute(database, "UPDATE assessment_items SET title_basis = 'section' WHERE item_id = ?",
            (item_id,))

    assert client.get(f"/api/v1/assessment-items/{item_id}").status_code == 404
    assert checker.check(database) == {**CLEAN, "public_card_not_viewable": 1}


def test_same_weight_written_two_ways_is_listed_once():
    assert rs.unique_weights(["30.0", "30", "", "15", "20%"]) == ["30.0", "15", "20%"]


def test_method_option_containing_the_separator_keeps_the_stored_value():
    # 선택지 하나가 '실험 · 실습'이면 카드의 방법 글에서는 둘로 갈라지지만 화면 글은 같다.
    case = {"methods_json": json.dumps(["실험 · 실습", "서술"], ensure_ascii=False)}
    assert rs.changed_columns(case, {"methods_json": ["실험", "실습", "서술"]}) == {}
    assert rs.changed_columns(case, {"methods_json": ["실험", "서술"]}) == {
        "methods_json": '["실험","서술"]'}
