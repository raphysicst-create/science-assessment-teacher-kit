"""Promote a fully audited recovery catalogue to the local publish layer.

Current publish databases and manifests are copied to a timestamped archive
before any canonical path is replaced.  The script refuses promotion unless
all evidence, title, subject, detail, publication, and recovery-table gates
match the expected release counts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_rules import blocking_errors, public_items

EXPECTED = {
    "cases": 9096,
    "items": 24154,
    "public_cases": 4979,
    "public_items": 10981,
    "recovery_public_cases": 116,
    "recovery_public_items": 221,
}
REQUIRED_REPORT_FIELDS = {
    "publication": (
        "passed", "blocking_public_items", "manual_queue_count",
        "item_counts.blocking_public_item", "item_counts.confirmed_public_item",
        "case_counts.blocking_public_case", "case_counts.confirmed_public_case",
    ),
    "title": ("passed", "blocking_public_items"),
    "subject": ("passed", "blocking_public_items"),
    "detail": ("gates",),
    "table": ("blocking_public_items", "warning_items"),
    "completeness": ("checks",),
}


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"JSON object required: {path}")
    return value


def load_report(name: str, path: Path) -> dict[str, object]:
    """Fail closed when an auditor's required output contract changes."""
    report = load_json(path)
    for field in REQUIRED_REPORT_FIELDS[name]:
        value = report
        for key in field.split("."):
            if not isinstance(value, dict) or key not in value:
                raise SystemExit(f"report missing field: {name}.{field} ({path})")
            value = value[key]
    return report


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def database_counts(path: Path) -> dict[str, object]:
    connection = sqlite3.connect(path)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        counts: dict[str, object] = {
            "integrity": integrity,
            "cases": int(connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]),
        }
        if "assessment_items" in tables:
            counts.update(
                {
                    "items": int(
                        connection.execute("SELECT COUNT(*) FROM assessment_items").fetchone()[0]
                    ),
                    "case_details": int(
                        connection.execute("SELECT COUNT(*) FROM case_detail_status").fetchone()[0]
                    ),
                    "rankings": int(
                        connection.execute(
                            "SELECT COUNT(*) FROM assessment_item_rankings"
                        ).fetchone()[0]
                    ),
                    "null_source_html": int(
                        connection.execute(
                            "SELECT COUNT(*) FROM assessment_items WHERE source_html_zlib IS NULL"
                        ).fetchone()[0]
                    ),
                }
            )
        return counts
    finally:
        connection.close()


def checked_replace(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=target.name + "_promote_", suffix=".partial", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temp_name)
    try:
        shutil.copy2(source, temporary)
        expected_hash = sha256(source)
        if sha256(temporary) != expected_hash:
            raise SystemExit(f"promotion copy hash mismatch: {source}")
        os.replace(temporary, target)
        return expected_hash
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-db", type=Path, required=True)
    parser.add_argument("--detail-db", type=Path, required=True)
    parser.add_argument("--base-manifest", type=Path, required=True)
    parser.add_argument("--detail-manifest", type=Path, required=True)
    parser.add_argument("--title-audit", type=Path, required=True)
    parser.add_argument("--subject-audit", type=Path, required=True)
    parser.add_argument("--detail-audit", type=Path, required=True)
    parser.add_argument("--publication-gate", type=Path, required=True)
    parser.add_argument("--recovery-table-audit", type=Path, required=True)
    parser.add_argument("--combined-table-audit", type=Path, required=True)
    parser.add_argument("--completeness-summary", type=Path, required=True)
    parser.add_argument("--publish-dir", type=Path, default=root / "data" / "publish")
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--release-manifest", type=Path)
    args = parser.parse_args()

    blocked = {
        item["item_id"]: codes
        for item in public_items(args.detail_db)
        if (codes := blocking_errors(item))
    }
    if blocked:
        raise SystemExit(f"promotion blocked by science errors: {blocked}")

    title = load_report("title", args.title_audit)
    subject = load_report("subject", args.subject_audit)
    detail = load_report("detail", args.detail_audit)
    publication = load_report("publication", args.publication_gate)
    recovery_table = load_report("table", args.recovery_table_audit)
    combined_table = load_report("table", args.combined_table_audit)
    completeness = load_report("completeness", args.completeness_summary)

    base_counts = database_counts(args.base_db)
    detail_counts = database_counts(args.detail_db)
    if base_counts != {"integrity": "ok", "cases": EXPECTED["cases"]}:
        raise SystemExit(f"unexpected base database counts: {base_counts}")
    if not (
        detail_counts.get("integrity") == "ok"
        and detail_counts.get("cases") == EXPECTED["cases"]
        and detail_counts.get("case_details") == EXPECTED["cases"]
        and detail_counts.get("items") == EXPECTED["items"]
        and detail_counts.get("rankings") == EXPECTED["items"]
        and detail_counts.get("null_source_html") == 0
    ):
        raise SystemExit(f"unexpected detail database counts: {detail_counts}")

    if publication["passed"] is not True or publication["blocking_public_items"] != 0:
        raise SystemExit("publication audit did not pass or has blocking public items")
    if publication["item_counts"]["blocking_public_item"] != 0:
        raise SystemExit("publication item counts have blocking public items")
    if publication["case_counts"]["blocking_public_case"] != 0:
        raise SystemExit("publication case counts have blocking public cases")
    if title["passed"] is not True or title["blocking_public_items"] != 0:
        raise SystemExit("title audit did not pass")
    if subject["passed"] is not True or subject["blocking_public_items"] != 0:
        raise SystemExit("subject audit did not pass or has blocking public items")
    detail_gates = detail["gates"]
    if not detail_gates or not all(bool(value) for value in detail_gates.values()):
        raise SystemExit(f"detail audit gates did not pass: {detail_gates}")
    if publication["case_counts"]["confirmed_public_case"] != EXPECTED[
        "public_cases"
    ]:
        raise SystemExit("publication case count mismatch")
    if publication["item_counts"]["confirmed_public_item"] != EXPECTED[
        "public_items"
    ]:
        raise SystemExit("publication item count mismatch")
    if recovery_table["blocking_public_items"] != 0 or recovery_table["warning_items"] != 0:
        raise SystemExit("recovery release still has structural table flags")
    checks = completeness["checks"]
    if not checks or not all(bool(value) for value in checks.values()):
        raise SystemExit(f"completeness checks did not pass: {checks}")

    publish_dir = args.publish_dir.resolve()
    timestamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = (
        args.archive_dir or publish_dir / "archive" / f"recovery-v1-{timestamp}"
    ).resolve()
    release_manifest = (
        args.release_manifest
        or publish_dir / "math_assessment_recovery_v1_release_manifest.json"
    ).resolve()
    if archive_dir.exists():
        raise SystemExit(f"archive directory already exists: {archive_dir}")
    archive_dir.mkdir(parents=True)

    canonical = {
        "base_db": publish_dir / "math_assessment_catalog.sqlite",
        "detail_db": publish_dir / "math_assessment_catalog_detail.sqlite",
        "base_manifest": publish_dir / "math_assessment_publish_manifest.json",
        "detail_manifest": publish_dir / "math_assessment_detail_manifest.json",
    }
    archived: list[dict[str, object]] = []
    for label, path in canonical.items():
        if not path.is_file():
            continue
        destination = archive_dir / path.name
        shutil.copy2(path, destination)
        if sha256(path) != sha256(destination):
            raise SystemExit(f"archive copy hash mismatch: {path}")
        archived.append(
            {
                "label": label,
                "path": str(destination),
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            }
        )

    promoted_hashes = {
        "base_db": checked_replace(args.base_db, canonical["base_db"]),
        "detail_db": checked_replace(args.detail_db, canonical["detail_db"]),
        "base_manifest": checked_replace(args.base_manifest, canonical["base_manifest"]),
        "detail_manifest": checked_replace(args.detail_manifest, canonical["detail_manifest"]),
    }
    promoted_counts = {
        "base": database_counts(canonical["base_db"]),
        "detail": database_counts(canonical["detail_db"]),
    }
    if promoted_counts["base"] != base_counts or promoted_counts["detail"] != detail_counts:
        raise SystemExit("promoted database counts differ from staged inputs")

    report = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "release": "recovery_v1",
        "expected": EXPECTED,
        "counts": promoted_counts,
        "promoted_sha256": promoted_hashes,
        "archived_previous_release": archived,
        "audits": {
            "title_passed": True,
            "unsafe_public_items": 0,
            "detail_gates_passed": True,
            "recovery_structural_flags": 0,
            "combined_structural_blocking_items": combined_table["blocking_public_items"],
            "combined_structural_warning_items": combined_table["warning_items"],
            "publication_manual_queue": publication["manual_queue_count"],
        },
        "policy": (
            "Recovery items are public only when source-bounded titles, subject alignment, "
            "traceability, and conservative table screening pass. Existing source files and "
            "the previous publish databases remain archived."
        ),
    }
    release_manifest.parent.mkdir(parents=True, exist_ok=True)
    release_manifest.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
