"""A document posted in several rounds becomes one card; real item_id collisions still fail.

Run: .venv/Scripts/python.exe -m pytest -q
     services/math-assessment-api/tests/test_science_catalog_duplicates.py
"""

import copy
import json
import sqlite3
from pathlib import Path

import pytest
from scripts.build_math_assessment_demo import demo_records
from scripts.build_science_catalog_db import write_science_catalog
from scripts.science_catalog_inputs import drop_repeated_documents

ROOT = Path(__file__).resolve().parents[3]
# The runner lists the second-semester round (round-3) first.
ROUNDS = ["2026-round-3-nwX", "2026-round-1-nwX"]


def posted_twice(filename="2026학년도 1학기 1학년 과학 평가계획.pdf"):
    """One synthetic document (two items) re-posted unchanged in both rounds."""
    base = demo_records()[:2]
    records = []
    for source_round in ROUNDS:
        for record in copy.deepcopy(base):
            record["source_round"] = source_round
            record["document"] = {"document_id": record["item"]["document_id"],
                                  "filename": filename, "text_sha256": "t" * 64}
            records.append(record)
    return records


def test_same_document_in_two_rounds_is_written_once():
    summary = {}
    kept = drop_repeated_documents(posted_twice(), ROUNDS, summary)
    assert [record["source_round"] for record in kept] == [ROUNDS[1]] * 2
    assert summary["documents"] == 1 and summary["dropped_items"] == 2
    assert summary["details"][0]["kept_round"] == ROUNDS[1]
    assert summary["details"][0]["dropped_rounds"] == [ROUNDS[0]]
    reference = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    with sqlite3.connect(":memory:") as connection:
        write_science_catalog(connection, kept, reference)
        count = connection.execute("SELECT COUNT(*) FROM assessment_items").fetchone()[0]
    assert count == 2


def test_without_semester_in_file_name_the_earlier_round_is_kept():
    kept = drop_repeated_documents(posted_twice("과학 평가계획.pdf"), ROUNDS)
    assert {record["source_round"] for record in kept} == {ROUNDS[0]}


def test_same_text_under_new_document_id_in_another_round_is_dropped():
    records = posted_twice()
    for record in records[2:]:
        record["item"]["document_id"] = record["document"]["document_id"] = "demo-reupload"
        record["item"]["item_id"] += "-reupload"
    kept = drop_repeated_documents(records, ROUNDS)
    assert len(kept) == 2 and {record["source_round"] for record in kept} == {ROUNDS[1]}


def test_same_text_twice_in_one_round_is_left_alone():
    records = posted_twice()[:2]
    second = copy.deepcopy(records)
    for record in second:
        record["item"]["document_id"] = record["document"]["document_id"] = "demo-copy"
        record["item"]["item_id"] += "-copy"
    summary = {}
    assert len(drop_repeated_documents(records + second, ROUNDS, summary)) == 4
    assert summary["documents"] == 0


def test_different_documents_sharing_an_item_id_still_fail():
    records = posted_twice()
    for record in records[2:]:
        record["item"]["document_id"] = record["document"]["document_id"] = "demo-other"
        record["document"]["text_sha256"] = "u" * 64
    with pytest.raises(ValueError, match="item_id collision across different documents"):
        drop_repeated_documents(records, ROUNDS)


def test_dropped_items_leave_the_activity_axes_summary():
    records = posted_twice()
    for record in records:
        record["activity_axes_rule_version"] = "v"
    summary = {"overridden_items": 4, "missing_rounds": 0, "missing_items": 0}
    drop_repeated_documents(records, ROUNDS, activity_axes_summary=summary)
    assert summary["overridden_items"] == 2


def test_document_and_text_links_do_not_depend_on_record_order():
    # r3 holds A and B with the same text; r1 holds B again without a text hash.
    # All three belong to one document, whichever of A or B is read first.
    records = posted_twice()
    a_in_r3, b_in_r1 = records[:2], records[2:]
    for record in a_in_r3:
        record["item"]["document_id"] = record["document"]["document_id"] = "demo-A"
    for record in b_in_r1:
        record["item"]["document_id"] = record["document"]["document_id"] = "demo-B"
        record["item"]["item_id"] += "-b"
        record["document"]["text_sha256"] = None
    b_in_r3 = copy.deepcopy(b_in_r1)
    for record in b_in_r3:
        record["source_round"] = ROUNDS[0]
        record["document"]["text_sha256"] = "t" * 64
    for ordered in (a_in_r3 + b_in_r3 + b_in_r1, b_in_r3 + a_in_r3 + b_in_r1):
        kept = drop_repeated_documents(copy.deepcopy(ordered), ROUNDS)
        assert [record["source_round"] for record in kept] == [ROUNDS[1]] * 2
