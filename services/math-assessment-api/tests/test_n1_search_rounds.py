"""N1: 검색 교차 검사의 기본 기대값 회차는 DB에 실린 회차 전부다(전국 묶음 회차 포함).

Run: pytest -q services/math-assessment-api/tests/test_n1_search_rounds.py
"""

import sqlite3
from contextlib import closing

from scripts.check_science_search import database_rounds
from scripts.science_catalog_inputs import DEFAULT_ROUNDS


def make_db(path, rounds):
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE assessment_items (item_id TEXT, source_round TEXT)")
        db.executemany("INSERT INTO assessment_items VALUES (?, ?)",
                       [(f"i{n}", r) for n, r in enumerate(rounds)])
        db.commit()


def test_default_rounds_follow_database_including_nationwide(tmp_path):
    path = tmp_path / "catalog.sqlite"
    make_db(path, ["2026-round-1-nw1", DEFAULT_ROUNDS[2], DEFAULT_ROUNDS[0],
                   "2026-round-3-nw1", DEFAULT_ROUNDS[0]])
    assert database_rounds(path) == [DEFAULT_ROUNDS[0], DEFAULT_ROUNDS[2],
                                     "2026-round-1-nw1", "2026-round-3-nw1"]


def test_default_rounds_equal_default_list_for_existing_catalog(tmp_path):
    path = tmp_path / "catalog.sqlite"
    make_db(path, list(DEFAULT_ROUNDS))
    assert database_rounds(path) == list(DEFAULT_ROUNDS)
