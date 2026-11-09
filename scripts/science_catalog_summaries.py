"""Aggregate science item evidence into legacy case and subject summaries.

Used by build_science_catalog_db.py. Verify with test_publish_builder.py.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from statistics import median

from scripts.science_catalog_axes import digest, encoded, source_sha256

UNKNOWN_COVERAGE = (None, None, None, None, None)
PRIORITY_FIELDS = (
    ("title", 18, "수행평가명 원문 확인"),
    ("standards", 12, "성취기준 명시"),
    ("rubric", 14, "채점기준 확인"),
    ("method", 9, "평가방법 명시"),
    ("weight_or_score", 8, "배점·반영비율 명시"),
    ("task_text", 7, "평가개요 확인"),
)


def field_value(record: dict, name: str):
    value = record["item"]["fields"].get(name, {}).get("value")
    return "" if value is None else value


def field_text(record: dict, name: str, separator: str = " / ") -> str:
    value = field_value(record, name)
    return separator.join(map(str, value)) if isinstance(value, list) else str(value)


def title(record: dict) -> str:
    return (
        field_text(record, "title") or field_text(record, "assessment_area") or "수행평가명 미확정"
    )


def science_priority(record: dict) -> tuple[int, list[str]]:
    signals = []
    score = 0
    for name, weight, signal in PRIORITY_FIELDS:
        present = field_value(record, name)
        if name == "title":
            present = present or field_value(record, "assessment_area")
        if name == "weight_or_score":
            present = field_value(record, "weight") or field_value(record, "score")
        if present:
            score += weight
            signals.append(signal)
    return score, signals


def insert_row(connection: sqlite3.Connection, table: str, row: dict) -> None:
    columns = ", ".join(row)
    placeholders = ", ".join("?" for _ in row)
    connection.execute(
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(row.values())
    )


def case_id(record: dict) -> str:
    item = record["item"]
    return digest(f"{item['document_id']}|{item['grade']}", 24)


def unique(values) -> list:
    return list(dict.fromkeys(value for value in values if value is not None and value != ""))


def combined_fields(records: list[dict], name: str) -> list:
    values = []
    for record in records:
        value = field_value(record, name)
        values.extend(value if isinstance(value, list) else [value])
    return unique(values)


def case_row(records: list[dict]) -> dict:
    first = records[0]
    item, document = first["item"], first["document"]
    edition = document.get("edition") or {}
    titles = [title(record) for record in records]
    tags = unique(record["axes"]["activity"].get("primary") for record in records)
    excerpt = "\n".join(f"수행평가명: {value}" for value in titles)[:902]
    score = max(science_priority(record)[0] for record in records)
    row = {
        "case_id": case_id(first),
        "source_sha256": source_sha256(first),
        "curriculum": "2022",
        "curriculum_basis": "science_axes_v2",
        "subject": "과학",
        "school_code": item.get("school_code") or document.get("school_code", ""),
        "school_name": item.get("school") or document.get("school", ""),
        "region": first["region"],
        "district": first["district"],
        "academic_years_json": encoded([edition.get("year") or 2026]),
        "grades_json": encoded([item["grade"]]),
        "semesters_json": encoded(unique(record["item"].get("semester") for record in records)),
        "candidate_name": document.get("filename") or item.get("filename", ""),
        "source_url": edition.get("source_url") or "",
        "extract_status": "ok",
        "primary_task_name": titles[0],
        "task_names_json": encoded(titles),
        "action_tags_json": encoded(tags),
        "evidence_score": score,
        "review_score": score,
        "evidence_excerpt": excerpt,
        "excerpt_char_count": len(excerpt),
        "source_char_count": len(first["text"]),
        "summary_overview": "",
        "methods_json": encoded(combined_fields(records, "method")),
        "weight_summary": " / ".join(map(str, combined_fields(records, "weight"))),
        "standards_json": encoded(combined_fields(records, "standards")),
        "criteria_json": "[]",
        "title_basis": "source_detail",
        "category": "",
        "priority_score": score,
        "priority_signals_json": "[]",
    }
    for column, fields in marker_fields().items():
        row[column] = sum(any(field_value(record, name) for name in fields) for record in records)
    return row


def marker_fields() -> dict:
    return {
        "rubric_marker_count": ("rubric",),
        "achievement_standard_marker_count": ("standards",),
        "weight_or_points_marker_count": ("score", "weight"),
        "assessment_method_marker_count": ("method",),
    }


def write_case(connection: sqlite3.Connection, records: list[dict]) -> dict:
    row = case_row(records)
    insert_row(connection, "cases", row)
    for position, record in enumerate(records, 1):
        connection.execute(
            "INSERT INTO case_task_names VALUES (?, ?, ?)",
            (row["case_id"], position, title(record)),
        )
    for tag in unique(record["axes"]["activity"].get("primary") for record in records):
        connection.execute("INSERT INTO case_action_tags VALUES (?, ?)", (row["case_id"], tag))
    first = records[0]
    connection.execute(
        "INSERT INTO case_detail_status VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["case_id"],
            Path(row["candidate_name"]).suffix.lstrip("."),
            "subject_section",
            "bounded",
            len(records),
            len(records),
            row["task_names_json"],
            sum(
                record["item"]["locator"]["end"] - record["item"]["locator"]["start"]
                for record in records
            ),
            first["document"].get("text_sha256") or first["item"].get("text_sha256") or "",
            0,
        ),
    )
    return row


def write_stats(connection: sqlite3.Connection, cases: list[dict], records: list[dict]) -> None:
    documents = {record["item"]["document_id"] for record in records}
    schools = {case["school_code"] for case in cases}
    years = sorted(
        {
            year
            for record in records
            for year in [record["document"].get("edition", {}).get("year") or 2026]
        }
    )
    grades = [
        len(
            {
                record["item"]["document_id"]
                for record in records
                if record["item"]["grade"] == grade
            }
        )
        for grade in (1, 2, 3)
    ]
    markers = []
    for fields in marker_fields().values():
        markers.append(
            len(
                {
                    record["item"]["document_id"]
                    for record in records
                    if any(field_value(record, name) for name in fields)
                }
            )
        )
    scores = [case["review_score"] for case in cases]
    connection.execute(
        "INSERT INTO subject_stats VALUES (" + ",".join("?" for _ in range(20)) + ")",
        (
            "2022",
            "과학",
            len(documents),
            len(schools),
            encoded(years),
            *grades,
            *markers,
            median(scores) if scores else None,
            len(records),
            int(len(schools) < 30),
            *UNKNOWN_COVERAGE,
        ),
    )
    write_subject_tags(connection, records)


def write_subject_tags(connection: sqlite3.Connection, records: list[dict]) -> None:
    tags = unique(record["axes"]["activity"].get("primary") for record in records)
    for tag in tags:
        selected = [
            record for record in records if record["axes"]["activity"].get("primary") == tag
        ]
        connection.execute(
            "INSERT INTO subject_action_tags VALUES (?, ?, ?, ?, ?)",
            (
                "2022",
                "과학",
                tag,
                len({record["item"]["document_id"] for record in selected}),
                len({record["item"].get("school_code", "") for record in selected}),
            ),
        )
