"""S18 기준 1 집계기: 정상 항목 오제거와 T3 사례 걸림을 센다.

Verify: .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_s18_card_check_dev.py
"""

import csv
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import s18_card_check_dev as dev  # noqa: E402


def make_db(path, rows):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE cases (case_id TEXT, school_name TEXT)")
        db.execute("CREATE TABLE assessment_items (item_id TEXT, case_id TEXT, source_item_id TEXT,"
                   " title TEXT, source_round TEXT, grade INT, semester INT)")
        db.execute("INSERT INTO cases VALUES ('c1', '가상중학교')")
        db.executemany("INSERT INTO assessment_items VALUES (?, 'c1', ?, ?, 'r', 1, 1)", rows)


def make_exclusions(path, item_ids):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "title", "blocking_codes"])
        writer.writeheader()
        writer.writerows({"item_id": i, "title": i, "blocking_codes": "AI1"} for i in item_ids)


def test_normal_removal_counts_only_unsuspected_labels(tmp_path):
    db = tmp_path / "x.sqlite"
    make_db(db, [("d1", "s1", "가"), ("d2", "s2", "나"), ("d3", "s3", "다")])
    labels = tmp_path / "labels.jsonl"
    labels.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
        {"item_id": "s1", "note": ""}, {"item_id": "s2", "note": "항목 의심: 요약표 행"},
        {"item_id": "s3", "note": "정상"}]), encoding="utf-8")
    exclusions = tmp_path / "ex.csv"
    make_exclusions(exclusions, ["d2"])
    result = dev.normal_removals(db, exclusions, labels)
    assert (result["normal_in_db"], result["normal_removed"]) == (2, 0)
    assert (result["suspect_in_db"], result["suspect_removed"]) == (1, 1)
    make_exclusions(exclusions, ["d1", "d2"])
    assert dev.normal_removals(db, exclusions, labels)["normal_removed"] == 1


def test_t3_cases_are_counted_from_case_list(tmp_path):
    db = tmp_path / "x.sqlite"
    make_db(db, [("d1", "ai1", "같은 과제"), ("d2", "rule1", "같은 과제")])
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps({"cases": [{"type": "T3", "case_id": "T3-1", "item_id": "ai1"},
                                           {"type": "T1", "case_id": "T1-1", "item_id": "x"}]}),
                     encoding="utf-8")
    exclusions = tmp_path / "ex.csv"
    make_exclusions(exclusions, ["d1"])
    result = dev.t3_caught(db, exclusions, cases)
    assert (result["t3_listed"], result["t3_caught"]) == (1, 1)
