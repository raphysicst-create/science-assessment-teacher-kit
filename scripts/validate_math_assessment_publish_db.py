"""Validate math catalogs or science catalogs with preserved classification evidence.

Run --profile science --database <catalog.sqlite> for science validation.
Verify with pytest services/math-assessment-api/tests/test_publish_builder.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METHOD_STATES = {"checked", "unchecked", "no_box", "lost", "plain"}
LOCATOR_COLUMNS = {
    "assessment_items": ("locator",),
    "assessment_item_axes": ("locator",),
    "assessment_item_methods": ("locator",),
    "source_segments": ("start_locator", "end_locator"),
}


def query_value(connection: sqlite3.Connection, sql: str, parameters: tuple = ()) -> object:
    row = connection.execute(sql, parameters).fetchone()
    return row[0] if row else None


def uses_index(plan_rows: list[sqlite3.Row], index_name: str) -> bool:
    return any(index_name in str(row[3]) for row in plan_rows)


def catalog_privacy_counts(connection: sqlite3.Connection) -> tuple[int, int]:
    local_paths = query_value(
        connection,
        """SELECT COUNT(*) FROM cases
        WHERE evidence_excerpt LIKE '%data/raw/%'
           OR evidence_excerpt LIKE '%C:\\Users\\%'
           OR source_url LIKE 'file:%'""",
    )
    invalid_urls = query_value(
        connection,
        """SELECT COUNT(*) FROM cases
        WHERE source_url != '' AND source_url NOT LIKE '%schoolinfo.go.kr%'""",
    )
    return int(local_paths or 0), int(invalid_urls or 0)


def invalid_locator_count(connection: sqlite3.Connection) -> int:
    invalid = 0
    required = {"start", "end", "sha256"}
    for table, columns in LOCATOR_COLUMNS.items():
        for row in connection.execute(f"SELECT {', '.join(columns)} FROM {table}"):
            for value in row:
                try:
                    locator = json.loads(value)
                    valid = (
                        isinstance(locator, dict)
                        and required <= locator.keys()
                        and isinstance(locator["sha256"], str)
                        and bool(locator["sha256"].strip())
                    )
                except (TypeError, ValueError):
                    valid = False
                invalid += int(not valid)
    return invalid


def science_axis_counts(connection: sqlite3.Connection) -> dict[str, int]:
    reference = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    values = {
        "unit": {f"{number:02d}" for number in range(1, 24)},
        "activity": {activity["id"] for activity in reference["activities"]},
    }
    counts = {"axis_rows": 0, "empty_axis_fields": 0, "invalid_axis_values": 0}
    for row in connection.execute(
        "SELECT axis, value, basis, evidence, locator, rule_version FROM assessment_item_axes"
    ):
        counts["axis_rows"] += 1
        counts["empty_axis_fields"] += sum(not str(value or "").strip() for value in row[2:])
        counts["invalid_axis_values"] += int(row[1] not in values.get(row[0], set()))
    counts["duplicate_primary_activities"] = int(query_value(
        connection,
        """SELECT COUNT(*) FROM (
        SELECT item_id FROM assessment_item_axes WHERE axis='activity' AND rank=1
        GROUP BY item_id HAVING COUNT(*) > 1)""",
    ) or 0)
    return counts


def science_catalog_counts(connection: sqlite3.Connection) -> dict[str, int]:
    local_paths, invalid_urls = catalog_privacy_counts(connection)
    counts = science_axis_counts(connection)
    counts.update({
        "cases": int(query_value(connection, "SELECT COUNT(*) FROM cases") or 0),
        "distinct_case_ids": int(query_value(
            connection, "SELECT COUNT(DISTINCT case_id) FROM cases"
        ) or 0),
        "fts_rows": int(query_value(connection, "SELECT COUNT(*) FROM cases_fts") or 0),
        "maximum_excerpt_chars": int(query_value(
            connection, "SELECT COALESCE(MAX(length(evidence_excerpt)), 0) FROM cases"
        ) or 0),
        "local_path_leaks": local_paths,
        "invalid_source_urls": invalid_urls,
        "invalid_locators": invalid_locator_count(connection),
        "missing_segments": int(query_value(
            connection, """SELECT COUNT(*) FROM assessment_items i
            LEFT JOIN source_segments s ON s.segment_id=i.segment_id WHERE s.segment_id IS NULL"""
        ) or 0),
        "invalid_method_states": sum(
            row[0] not in METHOD_STATES
            for row in connection.execute("SELECT state FROM assessment_item_methods")
        ),
        "foreign_key_violations": len(connection.execute("PRAGMA foreign_key_check").fetchall()),
    })
    return counts


def validate_science(connection: sqlite3.Connection) -> dict:
    counts = science_catalog_counts(connection)
    plan = connection.execute(
        "EXPLAIN QUERY PLAN SELECT item_id FROM assessment_item_axes WHERE axis='unit' AND value=?",
        ("03",),
    ).fetchall()
    checks = {
        "integrity_check": query_value(connection, "PRAGMA integrity_check") == "ok",
        "case_ids_unique": counts["cases"] == counts["distinct_case_ids"],
        "fts_rows_match_cases": counts["cases"] == counts["fts_rows"],
        "excerpt_length_limited": counts["maximum_excerpt_chars"] <= 902,
        "no_local_path_leaks": counts["local_path_leaks"] == 0,
        "source_urls_are_schoolinfo_only": counts["invalid_source_urls"] == 0,
        "axis_evidence_complete": counts["empty_axis_fields"] == 0,
        "axis_values_allowed": counts["invalid_axis_values"] == 0,
        "primary_activity_unique": counts["duplicate_primary_activities"] == 0,
        "locators_valid": counts["invalid_locators"] == 0,
        "all_item_segments_exist": counts["missing_segments"] == 0,
        "method_states_allowed": counts["invalid_method_states"] == 0,
        "foreign_keys_valid": counts["foreign_key_violations"] == 0,
        "axis_filter_uses_index": uses_index(plan, "idx_axes_axis_value"),
    }
    return {
        "passed": all(checks.values()), "checks": checks, "counts": counts,
        "query_plans": {"unit_filter": [str(row[3]) for row in plan]},
    }


def write_result(result: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    print(json.dumps(result, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("math", "science"), default="math")
    parser.add_argument("--database", type=Path, default=None)
    parser.add_argument(
        "--source-validation", type=Path,
        default=ROOT / "data/derived/math_assessment_catalog_validation_v2.json",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.database is None:
        args.database = ROOT / "data/publish" / (
            "science/math_assessment_catalog_detail.sqlite" if args.profile == "science"
            else "math_assessment_catalog.sqlite"
        )
    if args.output is None:
        args.output = ROOT / "data/publish" / (
            "science/validation.json" if args.profile == "science"
            else "math_assessment_publish_validation.json"
        )
    return args


def math_catalog_counts(connection: sqlite3.Connection, source: dict) -> dict[str, int]:
    local_paths, invalid_urls = catalog_privacy_counts(connection)
    return {
        "schools_in_source_validation": int(source.get("counts", {}).get("schools") or 0),
        "cases": int(query_value(connection, "SELECT COUNT(*) FROM cases") or 0),
        "subjects": int(query_value(connection, "SELECT COUNT(*) FROM subject_stats") or 0),
        "coverage_subjects": int(query_value(
            connection, "SELECT COUNT(*) FROM subject_stats WHERE coverage_found IS NOT NULL"
        ) or 0),
        "fts_rows": int(query_value(connection, "SELECT COUNT(*) FROM cases_fts") or 0),
        "maximum_excerpt_chars": int(query_value(
            connection, "SELECT COALESCE(MAX(excerpt_char_count), 0) FROM cases"
        ) or 0),
        "local_path_leaks": local_paths,
        "invalid_source_urls": invalid_urls,
    }


def math_query_plans(connection: sqlite3.Connection) -> dict[str, list]:
    return {
        "subject_filter": connection.execute(
            """EXPLAIN QUERY PLAN SELECT case_id FROM cases
            WHERE curriculum = ? AND subject = ?
            ORDER BY review_score DESC, case_id LIMIT 20""", ("2022", "대수"),
        ).fetchall(),
        "tag_filter": connection.execute(
            "EXPLAIN QUERY PLAN SELECT case_id FROM case_action_tags WHERE tag = ? LIMIT 20",
            ("탐구",),
        ).fetchall(),
    }


def validate_math(connection: sqlite3.Connection, source: dict) -> dict:
    counts = math_catalog_counts(connection, source)
    plans = math_query_plans(connection)
    schema_names = {
        str(row[0]) for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type IN ('table', 'view')"
        )
    }
    distinct_cases = int(query_value(
        connection, "SELECT COUNT(DISTINCT case_id) FROM cases"
    ) or 0)
    checks = {
        "source_validation_passed": source.get("passed") is True,
        "integrity_check": query_value(connection, "PRAGMA integrity_check") == "ok",
        "case_count_matches": counts["cases"] == int(
            source.get("counts", {}).get("strict_rows") or 0
        ),
        "case_ids_unique": distinct_cases == counts["cases"],
        "subject_groups_include_24_courses_and_shared_groups": counts["subjects"] >= 24,
        "coverage_subject_groups_match_24_courses": counts["coverage_subjects"] == 24,
        "fts_rows_match_cases": counts["fts_rows"] == counts["cases"],
        "excerpt_length_limited": counts["maximum_excerpt_chars"] <= 902,
        "no_local_path_leaks": counts["local_path_leaks"] == 0,
        "source_urls_are_schoolinfo_only": counts["invalid_source_urls"] == 0,
        "no_forbidden_raw_schema": not any(
            "raw" in name.lower() or "full_text" in name.lower() for name in schema_names
        ),
        "subject_filter_uses_index": uses_index(
            plans["subject_filter"], "idx_cases_curriculum_subject_review"
        ),
        "tag_filter_uses_index": uses_index(
            plans["tag_filter"], "idx_case_action_tags_tag_case"
        ),
    }
    return {
        "passed": all(checks.values()), "checks": checks, "counts": counts,
        "query_plans": {name: [str(row[3]) for row in rows] for name, rows in plans.items()},
    }


def main() -> None:
    args = parse_args()
    if not args.database.is_file():
        raise SystemExit("publish database is missing")
    source = {}
    if args.profile == "math":
        if not args.source_validation.is_file():
            raise SystemExit("publish database or source validation is missing")
        source = json.loads(args.source_validation.read_text(encoding="utf-8"))
    database_uri = f"file:{args.database.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(database_uri, uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        result = validate_science(connection) if args.profile == "science" else validate_math(
            connection, source
        )
    write_result(result, args.output)


if __name__ == "__main__":
    main()
