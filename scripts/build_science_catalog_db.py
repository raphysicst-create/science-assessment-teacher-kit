"""Build the local-review middle-school science SQLite catalog atomically.

Run .venv/Scripts/python.exe scripts/build_science_catalog_db.py --output PATH
    [--activity-axes-dir DIR]. Only activity axes are overridden when supplied.
Verify with validate_math_assessment_publish_db.py --profile science --database PATH.
Verify .venv/Scripts/python.exe -m pytest -q
       services/math-assessment-api/tests/test_science_axes_ai.py
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
import tempfile
import zlib
from collections import defaultdict
from contextlib import closing
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_math_assessment_detail_db import SCHEMA_SQL as DETAIL_SCHEMA
from scripts.build_math_assessment_publish_db import SCHEMA_SQL as PUBLISH_SCHEMA
from scripts.math_assessment_detail_parser import markdown_fragment_to_html
from scripts.science_catalog_axes import (
    axis_rows,
    digest,
    encoded,
    locator,
    method_rows,
    segment_id,
    source_sha256,
)
from scripts.science_catalog_inputs import DEFAULT_ROUNDS, ROOT, load_science_records, read_json
from scripts.science_catalog_summaries import (
    case_id,
    field_text,
    field_value,
    insert_row,
    science_priority,
    title,
    unique,
    write_case,
    write_stats,
)

SCIENCE_SCHEMA_SQL = """
ALTER TABLE assessment_items ADD COLUMN segment_id TEXT NOT NULL DEFAULT '';
ALTER TABLE assessment_items ADD COLUMN task_no TEXT NOT NULL DEFAULT '';
ALTER TABLE assessment_items ADD COLUMN locator TEXT NOT NULL DEFAULT '{}';
ALTER TABLE assessment_items ADD COLUMN grade INTEGER;
ALTER TABLE assessment_items ADD COLUMN semester INTEGER;
ALTER TABLE assessment_items ADD COLUMN unit_status TEXT NOT NULL DEFAULT '';
ALTER TABLE assessment_items ADD COLUMN unit_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE assessment_items ADD COLUMN activity_abstain_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE assessment_items ADD COLUMN source_item_id TEXT NOT NULL DEFAULT '';
ALTER TABLE assessment_items ADD COLUMN source_round TEXT NOT NULL DEFAULT '';
ALTER TABLE assessment_items ADD COLUMN source_extraction_status TEXT NOT NULL DEFAULT '';
CREATE TABLE source_segments (
 segment_id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL, zip_child TEXT,
 grade INTEGER, semester INTEGER, subject_status TEXT NOT NULL,
 curriculum_status TEXT NOT NULL, start_locator TEXT NOT NULL,
 end_locator TEXT NOT NULL, rule_version TEXT NOT NULL);
CREATE TABLE assessment_item_methods (
 item_id TEXT NOT NULL, option_text TEXT NOT NULL, state TEXT NOT NULL,
 custom_text TEXT, locator TEXT NOT NULL,
 PRIMARY KEY (item_id, option_text)) WITHOUT ROWID;
CREATE TABLE assessment_item_axes (
 item_id TEXT NOT NULL REFERENCES assessment_items(item_id),
 axis TEXT NOT NULL CHECK (axis IN ('unit','activity')), value TEXT NOT NULL,
 rank INTEGER NOT NULL, basis TEXT NOT NULL, evidence TEXT NOT NULL,
 locator TEXT NOT NULL, rule_version TEXT NOT NULL, status TEXT NOT NULL,
 undetermined_reason TEXT,
 PRIMARY KEY (item_id, axis, value)) WITHOUT ROWID;
CREATE INDEX idx_axes_axis_value ON assessment_item_axes(axis, value, item_id);
CREATE INDEX idx_assessment_items_grade ON assessment_items(grade, item_id);
CREATE TABLE assessment_item_rankings (
 item_id TEXT PRIMARY KEY REFERENCES assessment_items(item_id), category TEXT NOT NULL,
 priority_score INTEGER NOT NULL, priority_signals_json TEXT NOT NULL) WITHOUT ROWID;
CREATE INDEX idx_assessment_item_rankings_category_priority
 ON assessment_item_rankings(category, priority_score DESC, item_id);
"""


def close_table_fragments(text: str) -> str:
    """Flatten orphan table tags while keeping complete (also nested) tables verbatim."""
    tables: list[tuple[int, int]] = []
    openings: list[int] = []
    for match in re.finditer(r"</?table\b[^>]*>", text, flags=re.I):
        if not match.group().startswith("</"):
            openings.append(match.start())
        elif openings:
            start = openings.pop()
            while tables and tables[-1][0] > start:
                tables.pop()
            tables.append((start, match.end()))

    def flatten(fragment: str) -> str:
        if not re.search(r"</?(?:table|tr|td|th)\b[^>]*>", fragment, flags=re.I):
            return fragment
        # Adjacent cell end/start tags denote a single visible cell boundary.
        return re.sub(
            r"</t[dh]\s*>\s*<t[dh]\b[^>]*>|</?(?:table|tr|td|th)\b[^>]*>|<br\s*/?>",
            lambda match: " | " if re.match(r"</?t[dh]\b", match.group(), re.I) else "\n",
            fragment,
            flags=re.I,
        )

    parts: list[str] = []
    cursor = 0
    for start, end in tables:
        parts.extend((flatten(text[cursor:start]), text[start:end]))
        cursor = end
    parts.append(flatten(text[cursor:]))
    return "".join(parts)


def item_row(record: dict, order: int) -> dict:
    item = record["item"]
    start, end = item["locator"]["start"], item["locator"]["end"]
    if not 0 <= start <= end <= len(record["text"]):
        raise ValueError(f"invalid source range: {item['item_id']}")
    html = markdown_fragment_to_html(close_table_fragments(record["text"][start:end]))
    row = {
        "item_id": digest(item["item_id"], 28),
        "case_id": case_id(record),
        "item_order": order,
        "title": title(record),
        "title_raw": title(record),
        "title_basis": "table" if item["fields"].get("title", {}).get("evidence") else "section",
        "extraction_status": "bounded",
        "source_start": start,
        "source_end": end,
        "overview": field_text(record, "task_text"),
        "method": field_text(record, "method", " · "),
        "timing": field_text(record, "timing"),
        "score": field_text(record, "score"),
        "weight": field_text(record, "weight"),
        "standards_json": encoded(field_value(record, "standards") or []),
        "source_html_zlib": zlib.compress(html.encode("utf-8"), 9),
        "rubric_html_zlib": zlib.compress(b"", 9),
        "source_html_char_count": len(html),
        "rubric_html_char_count": 0,
        "segment_id": segment_id(record),
        "task_no": field_text(record, "task_no"),
        "locator": locator(record),
        "grade": item["grade"],
        "semester": item.get("semester"),
        "unit_status": record["axes"]["unit"]["status"],
        "unit_reason": record["axes"]["unit"].get("reason") or "",
        "activity_abstain_reason": record["axes"]["activity"].get("abstain_reason") or "",
        "source_item_id": item["item_id"],
        "source_round": record["source_round"],
        "source_extraction_status": item["extraction_status"],
    }
    return row


def write_segments(connection: sqlite3.Connection, records: list[dict]) -> None:
    groups = defaultdict(list)
    for record in records:
        groups[segment_id(record)].append(record)
    for identity, group in groups.items():
        first, item = group[0], group[0]["item"]
        statuses = {record["axes"]["unit"]["status"] for record in group}
        curriculum = "2022"
        if "conflict" in statuses:
            curriculum = "conflict"
        elif statuses == {"undetermined"}:
            curriculum = "undetermined"
        bounds = first.get("section", {}).get("locator") or {
            "start": min(record["item"]["locator"]["start"] for record in group),
            "end": max(record["item"]["locator"]["end"] for record in group),
        }
        connection.execute(
            "INSERT INTO source_segments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                identity,
                source_sha256(first),
                item.get("child_id"),
                item["grade"],
                item.get("semester"),
                item.get("subject_status") or "unknown",
                curriculum,
                locator(first, bounds),
                locator(first, bounds),
                first["item_rule_version"],
            ),
        )


def catalog_axis_rows(record: dict, activity_ids: dict) -> list[tuple]:
    """Retain unit provenance; share the AI card quote with its secondary labels."""
    version = record.get("activity_axes_rule_version")
    if version is None:
        return axis_rows(record, activity_ids)
    activity = record["axes"]["activity"]
    evidence = list(activity["evidence"])
    quotes = [row["quote"] for row in evidence
              if row["type"] == "ai_quote" and isinstance(row.get("quote"), str)
              and row["quote"].strip()]
    for name in activity.get("secondary", []):
        if not any(row["activity"] == name for row in evidence):
            evidence.extend({"type": "ai_quote", "quote": quote, "activity": name}
                            for quote in quotes)
    amended = {**record, "axes": {**record["axes"], "activity": {**activity, "evidence": evidence}}}
    return [row[:7] + (version,) + row[8:] if row[1] == "activity" else row
            for row in axis_rows(amended, activity_ids)]


def write_science_catalog(
    connection: sqlite3.Connection, records: list[dict], axes_reference: dict,
    activity_axes_dir: str = "data/derived/axes",
) -> dict:
    """Write records containing item, axes, document, section, text and provenance."""
    connection.executescript(PUBLISH_SCHEMA + DETAIL_SCHEMA + SCIENCE_SCHEMA_SQL)
    activity_ids = {activity["name"]: activity["id"] for activity in axes_reference["activities"]}
    groups = defaultdict(list)
    for record in records:
        if record["item"].get("grade") not in (1, 2):
            raise ValueError("only grades 1 and 2 may be published")
        groups[case_id(record)].append(record)
    cases = []
    for group in groups.values():
        group.sort(
            key=lambda record: (record["item"]["locator"]["start"], record["item"]["item_id"])
        )
        cases.append(write_case(connection, group))
        for order, record in enumerate(group, 1):
            row = item_row(record, order)
            insert_row(connection, "assessment_items", row)
            connection.executemany(
                "INSERT INTO assessment_item_axes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                catalog_axis_rows(record, activity_ids),
            )
            connection.executemany(
                "INSERT OR IGNORE INTO assessment_item_methods VALUES (?, ?, ?, ?, ?)",
                method_rows(record),
            )
            score, signals = science_priority(record)
            category = activity_ids.get(record["axes"]["activity"].get("primary"), "")
            connection.execute(
                "INSERT INTO assessment_item_rankings VALUES (?, ?, ?, ?)",
                (row["item_id"], category, score, encoded(signals)),
            )
    write_segments(connection, records)
    write_stats(connection, cases, records)
    return finish_catalog(connection, records, len(cases), activity_axes_dir)


def finish_catalog(connection: sqlite3.Connection, records: list[dict], case_count: int,
                   activity_axes_dir: str = "data/derived/axes") -> dict:
    metadata = {
        # 검색 검사(check_science_search)가 같은 활동 축 파일로 기대값을 계산하도록 남긴다.
        "activity_axes_dir": activity_axes_dir,
        "dataset_scope": "middle_science_local_review",
        "dataset_profile": "science",
        "axes_rule_version": unique(record["axes_rule_version"] for record in records),
        "rounds": unique(record["source_round"] for record in records),
        "public_release": False,
        "item_count": len(records),
        "case_count": case_count,
    }
    versions = metadata["axes_rule_version"]
    metadata["axes_rule_version"] = versions[0] if len(versions) == 1 else versions
    connection.executemany(
        "INSERT INTO metadata VALUES (?, ?)",
        [(key, encoded(value)) for key, value in metadata.items()],
    )
    connection.execute("INSERT INTO cases_fts(cases_fts) VALUES('rebuild')")
    if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise ValueError("database integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("database foreign key check failed")
    count = connection.execute("SELECT COUNT(*) FROM assessment_items").fetchone()[0]
    if count != len(records):
        raise ValueError("item count differs from axis inputs")
    return {"item_count": count, "case_count": case_count}


def build_catalog(output: Path, rounds=DEFAULT_ROUNDS, replace: bool = False,
                  activity_axes_dir: Path | None = None) -> dict:
    if output.exists() and not replace:
        raise ValueError(f"output already exists: {output}")
    activity_summary = {"overridden_items": 0, "missing_rounds": 0, "missing_items": 0}
    records = (load_science_records(rounds) if activity_axes_dir is None else load_science_records(
        rounds, activity_axes_dir=activity_axes_dir, activity_axes_summary=activity_summary))
    reference = read_json(ROOT / "data/reference/science_axes.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        database = Path(temporary) / "catalog.sqlite"
        with closing(sqlite3.connect(database)) as connection:
            axes_dir = ("data/derived/axes" if activity_axes_dir is None else
                        Path(activity_axes_dir).resolve().relative_to(ROOT).as_posix())
            result = write_science_catalog(connection, records, reference, axes_dir)
            connection.commit()
        os.replace(database, output)
    if activity_axes_dir is not None:
        result["activity_axes"] = activity_summary
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/publish/science/math_assessment_catalog_detail.sqlite"),
    )
    parser.add_argument("--rounds", nargs="+", default=DEFAULT_ROUNDS)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--activity-axes-dir", type=Path)
    args = parser.parse_args()
    try:
        result = build_catalog(args.output, args.rounds, args.replace, args.activity_axes_dir)
    except (ValueError, KeyError, sqlite3.Error) as error:
        raise SystemExit(str(error)) from error
    print(encoded({"output": str(args.output), **result}))


if __name__ == "__main__":
    main()
