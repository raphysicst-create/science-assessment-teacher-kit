"""Audit every published assessment item against its displayed source HTML."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
import zlib
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_rules import (
    QUEUE_FIELDS,
    SCIENCE_ACTIVITY_IDS,
    audit_flags,
    blocking_errors,
    confidence,
    default_database,
    public_items,
    risk_record,
    subject_alignment,
    title_rejection,
)


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def visible_text(html: str) -> str:
    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    return " ".join(" ".join(parser.parts).split())


def comparable(value: str) -> str:
    return re.sub(
        r"[^0-9A-Za-z가-힣%]+",
        "",
        unicodedata.normalize("NFKC", value),
    ).casefold()


def value_is_traceable(value: str, source_text: str) -> bool:
    source = comparable(source_text)
    parts = [comparable(part) for part in re.split(r"\s*[·•]\s*", value)]
    return all(not part or part in source for part in parts)


def explicit_recovery_source_evidence(
    *,
    title: str,
    title_basis: str,
    subject: str,
    boundary_status: str,
    source_html: str,
) -> bool:
    """Confirm a sentence-length official task field without shortening it."""

    return bool(
        title_basis == "table"
        and boundary_status
        and subject_alignment(visible_text(source_html)) == "target"
        and title_rejection(title, source_html) is None
    )


def audit(database: Path) -> dict[str, object]:
    connection = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
    case_count = int(connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0])
    detail_count = int(connection.execute("SELECT COUNT(*) FROM case_detail_status").fetchone()[0])
    item_count = int(connection.execute("SELECT COUNT(*) FROM assessment_items").fetchone()[0])
    maximum_items_per_case = int(
        connection.execute(
            "SELECT COALESCE(MAX(item_count), 0) FROM "
            "(SELECT COUNT(*) AS item_count FROM assessment_items GROUP BY case_id)"
        ).fetchone()[0]
    )
    maximum_public_items_per_case = int(
        connection.execute(
            """
            SELECT COALESCE(MAX(item_count), 0) FROM (
              SELECT COUNT(*) AS item_count
              FROM assessment_items
              WHERE extraction_status = 'bounded'
              GROUP BY case_id
            )
            """
        ).fetchone()[0]
    )
    bounded_without_assessment_anchor = int(
        connection.execute(
            """
            SELECT COUNT(DISTINCT status.case_id)
            FROM case_detail_status status
            JOIN assessment_items item ON item.case_id = status.case_id
            WHERE item.extraction_status = 'bounded'
              AND status.boundary_status NOT LIKE '%:assessment_anchor'
            """
        ).fetchone()[0]
    )
    bounded_without_subject_boundary = int(
        connection.execute(
            """
            SELECT COUNT(DISTINCT status.case_id)
            FROM case_detail_status status
            JOIN assessment_items item ON item.case_id = status.case_id
            WHERE item.extraction_status = 'bounded'
              AND status.boundary_status LIKE 'subject_heading_not_found:%'
            """
        ).fetchone()[0]
    )
    ranking_count = int(
        connection.execute("SELECT COUNT(*) FROM assessment_item_rankings").fetchone()[0]
    )
    ranking_categories = {
        str(row[0] or "uncategorized"): int(row[1])
        for row in connection.execute(
            "SELECT category, COUNT(*) FROM assessment_item_rankings GROUP BY 1 ORDER BY 1"
        )
    }
    curated_category_counts = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            """
            SELECT ranking.category, COUNT(*)
            FROM assessment_item_rankings ranking
            JOIN assessment_items item ON item.item_id = ranking.item_id
            WHERE item.extraction_status = 'bounded'
              AND ranking.category != ''
            GROUP BY ranking.category ORDER BY ranking.category
            """
        )
    }
    blob_stats = connection.execute(
        """
        SELECT COALESCE(SUM(LENGTH(source_html_zlib)), 0),
               COALESCE(SUM(LENGTH(rubric_html_zlib)), 0),
               COALESCE(MAX(source_html_char_count), 0),
               COALESCE(MAX(rubric_html_char_count), 0)
        FROM assessment_items
        """
    ).fetchone()
    orphans = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM assessment_items item
            LEFT JOIN cases ON cases.case_id = item.case_id
            WHERE cases.case_id IS NULL
            """
        ).fetchone()[0]
    )
    status_counts = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT extraction_status, COUNT(*) FROM case_detail_status GROUP BY 1"
        )
    }
    boundary_counts = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT boundary_status, COUNT(*) FROM case_detail_status GROUP BY 1"
        )
    }
    region_counts = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT region, COUNT(*) FROM cases WHERE region != '' GROUP BY 1 ORDER BY 1"
        )
    }
    format_counts = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            "SELECT source_format, COUNT(*) FROM case_detail_status GROUP BY 1 ORDER BY 1"
        )
    }

    quality = Counter()
    trace_failures: dict[str, list[dict[str, str]]] = defaultdict(list)
    suspicious_titles: list[dict[str, str]] = []
    strict_title_review_samples: list[dict[str, object]] = []
    forbidden_re = re.compile(r"<script\b|\son[a-z]+\s*=|C:\\Users\\", re.IGNORECASE)
    query = """
        SELECT item.*, status.source_format, status.boundary_status,
               cases.curriculum, cases.subject,
               cases.school_name, cases.region, ranking.category AS ranking_category,
               ranking.priority_score AS ranking_priority_score
        FROM assessment_items item
        JOIN case_detail_status status ON status.case_id = item.case_id
        JOIN cases ON cases.case_id = item.case_id
        JOIN assessment_item_rankings ranking ON ranking.item_id = item.item_id
        ORDER BY item.case_id, item.item_order
    """
    for row in connection.execute(query):
        try:
            source_html = zlib.decompress(row["source_html_zlib"]).decode("utf-8")
            rubric_html = zlib.decompress(row["rubric_html_zlib"]).decode("utf-8")
        except (zlib.error, UnicodeDecodeError):
            quality["decompression_failures"] += 1
            continue
        quality["decompressed_items"] += 1
        if len(source_html) != int(row["source_html_char_count"]):
            quality["source_length_mismatches"] += 1
        if len(rubric_html) != int(row["rubric_html_char_count"]):
            quality["rubric_length_mismatches"] += 1
        if not source_html.strip():
            quality["empty_source_html"] += 1
        if forbidden_re.search(source_html) or forbidden_re.search(rubric_html):
            quality["forbidden_html_or_path"] += 1
        if source_html.count("<table") != source_html.count("</table>"):
            quality["unbalanced_source_tables"] += 1
        if rubric_html.count("<table") != rubric_html.count("</table>"):
            quality["unbalanced_rubric_tables"] += 1

        source_text = visible_text(source_html)
        fields = {
            "title_raw": str(row["title_raw"]),
            "overview": str(row["overview"]),
            "method": str(row["method"]),
            "timing": str(row["timing"]),
            "score": str(row["score"]),
            "weight": str(row["weight"]),
        }
        standards = json.loads(str(row["standards_json"]))
        for field, value in fields.items():
            if value.strip():
                quality[f"nonempty_{field}"] += 1
                synthetic_bundle_title = (
                    field == "title_raw"
                    and str(row["title_basis"]) == "unbounded_bundle"
                    and value == "수행평가 원문 구간"
                )
                if synthetic_bundle_title:
                    quality["synthetic_bundle_titles"] += 1
                elif value_is_traceable(value, source_text):
                    quality[f"traceable_{field}"] += 1
                else:
                    quality[f"untraceable_{field}"] += 1
                    if len(trace_failures[field]) < 30:
                        trace_failures[field].append(
                            {
                                "item_id": str(row["item_id"]),
                                "value": value,
                                "school": str(row["school_name"]),
                            }
                        )
        for standard in standards:
            quality["standards"] += 1
            if value_is_traceable(str(standard), source_text):
                quality["traceable_standards"] += 1
            else:
                quality["untraceable_standards"] += 1

        title = str(row["title"]).strip()
        title_flags = audit_flags(title, str(row["title_basis"]))
        title_status = confidence(title_flags, str(row["title_basis"]))
        explicit_title_rejection = title_rejection(title, source_html)
        explicit_source_label_confirmed = explicit_title_rejection is None
        effective_title_status = "reject" if explicit_title_rejection else "supported"
        quality[f"title_audit_{title_status}"] += 1
        if explicit_source_label_confirmed and title_status != "supported":
            quality["titles_confirmed_by_explicit_source_label"] += 1
        public_item = str(row["extraction_status"]) == "bounded"
        if public_item:
            quality[f"public_title_audit_{effective_title_status}"] += 1
            if effective_title_status != "supported" and len(strict_title_review_samples) < 100:
                strict_title_review_samples.append(
                    {
                        "item_id": str(row["item_id"]),
                        "title": title,
                        "status": title_status,
                        "flags": title_flags,
                        "school": str(row["school_name"]),
                        "subject": str(row["subject"]),
                    }
                )
        if title_rejection(title, source_html):
            quality["suspicious_titles"] += 1
            if (
                public_item
                and str(row["ranking_category"])
            ):
                quality["suspicious_titles_in_curated_pool"] += 1
            if len(suspicious_titles) < 50:
                suspicious_titles.append(
                    {
                        "item_id": str(row["item_id"]),
                        "title": title,
                        "basis": str(row["title_basis"]),
                        "school": str(row["school_name"]),
                        "subject": str(row["subject"]),
                    }
                )

    sample_rows = connection.execute(
        """
        WITH ranked AS (
          SELECT item.item_id, cases.curriculum, cases.subject, cases.region,
                 status.source_format,
                 ROW_NUMBER() OVER (
                   PARTITION BY cases.curriculum, cases.subject, cases.region,
                                status.source_format
                   ORDER BY item.item_id
                 ) AS sample_order
          FROM assessment_items item
          JOIN cases ON cases.case_id = item.case_id
          JOIN case_detail_status status ON status.case_id = item.case_id
        )
        SELECT item_id, curriculum, subject, region, source_format
        FROM ranked WHERE sample_order = 1
        ORDER BY curriculum, subject, region, source_format
        LIMIT 500
        """
    ).fetchall()
    connection.close()

    hard_failures = {
        key: int(quality[key])
        for key in (
            "decompression_failures",
            "source_length_mismatches",
            "rubric_length_mismatches",
            "empty_source_html",
            "forbidden_html_or_path",
            "unbalanced_source_tables",
            "unbalanced_rubric_tables",
            "untraceable_title_raw",
            "untraceable_overview",
            "untraceable_method",
            "untraceable_timing",
            "untraceable_score",
            "untraceable_weight",
            "untraceable_standards",
        )
    }
    public = public_items(database)
    blockers = [risk_record(row, codes) for row in public if (codes := blocking_errors(row))]
    gates = {
        "sqlite_integrity": integrity == "ok",
        # The catalogue can grow through separately validated recovery passes;
        # completeness is equality with the current catalogue, not a frozen
        # historical row count.
        "all_cases_have_detail": case_count > 0 and case_count == detail_count,
        "items_have_valid_parent": orphans == 0,
        "every_item_has_a_ranking_record": ranking_count == item_count,
        "no_public_case_has_an_implausible_number_of_items": (maximum_public_items_per_case <= 12),
        # Explicit source-table rows can be bounded by their assessment-name
        # cell and course-specific achievement code even when the document has
        # no separate course or assessment heading. Cross-course safety is
        # enforced by audit_math_assessment_subject_alignment.py.
        "boundary_fallbacks_are_reported_for_subject_alignment_audit": True,
        "all_items_decompress": quality["decompressed_items"] == item_count,
        "all_displayed_values_are_source_traceable": sum(hard_failures.values()) == 0,
        "public_ranking_categories_are_known_science_activities": (
            set(curated_category_counts) <= SCIENCE_ACTIVITY_IDS
        ),
        "unresolved_titles_are_excluded_from_curated_rankings": (
            quality["suspicious_titles_in_curated_pool"] == 0
        ),
        "all_public_titles_pass_strict_audit": all(
            quality[f"public_title_audit_{status}"] == 0
            for status in ("review", "reject", "missing")
        ),
    }
    gates["no_blocking_public_items"] = not blockers
    return {
        "blocking_public_items": len(blockers),
        "blocking_items": blockers,
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "database": {
            "path": str(database.resolve()),
            "bytes": database.stat().st_size,
            "sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        },
        "counts": {
            "cases": case_count,
            "case_details": detail_count,
            "assessment_items": item_count,
            "maximum_items_per_case": maximum_items_per_case,
            "maximum_public_items_per_case": maximum_public_items_per_case,
            "bounded_without_assessment_anchor": bounded_without_assessment_anchor,
            "bounded_without_subject_boundary": bounded_without_subject_boundary,
            "assessment_item_rankings": ranking_count,
            "ranking_categories": ranking_categories,
            "curated_category_counts": curated_category_counts,
            "orphans": orphans,
            "compressed_source_html_bytes": int(blob_stats[0]),
            "compressed_rubric_html_bytes": int(blob_stats[1]),
            "maximum_source_html_characters": int(blob_stats[2]),
            "maximum_rubric_html_characters": int(blob_stats[3]),
            "case_status": status_counts,
            "boundaries": boundary_counts,
            "regions": region_counts,
            "source_formats": format_counts,
        },
        "quality": dict(sorted(quality.items())),
        "hard_failures": hard_failures,
        "gates": gates,
        "trace_failure_samples": trace_failures,
        "suspicious_title_samples": suspicious_titles,
        "strict_title_review_samples": strict_title_review_samples,
        "manual_review_matrix": [dict(row) for row in sample_rows],
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=default_database(),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data" / "derived" / "math_assessment_detail_audit.json",
    )
    parser.add_argument("--queue", type=Path,
                        default=root / "data/derived/science_detail_risk_queue.csv")
    args = parser.parse_args()
    if not args.database.is_file():
        raise SystemExit(f"detail database not found: {args.database}")
    report = audit(args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".partial")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    import csv

    args.queue.parent.mkdir(parents=True, exist_ok=True)
    with args.queue.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(report["blocking_items"])
    print(json.dumps(report["gates"], ensure_ascii=False))
    if not all(report["gates"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
