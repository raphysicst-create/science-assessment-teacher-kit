"""Inventory legacy rule sites with AST definitions/imports and literal locations.

Run: .venv/Scripts/python.exe scripts/check_science_rule_sites.py --report report.json
Use --targets file.py ... for one migrated slice; defaults to the full S15 target set.
Unknown files fail classification; inventories never execute scripts or read data.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

# Q2-1 R1/R2/R4 audit, repair, promotion sites and R3 _exact_fields consumers.
S15_TARGETS = frozenset(
    {
        "audit_math_assessment_subject_alignment.py",
        "audit_math_assessment_titles_full.py",
        "audit_math_assessment_detail_db.py",
        "audit_math_assessment_publication_gate.py",
        "audit_math_assessment_table_structure.py",
        "audit_math_assessment_release_precision.py",
        "audit_math_assessment_publish_titles.py",
        "audit_unresolved_math_assessment_titles.py",
        "audit_math_assessment_explicit_item_candidate.py",
        "repair_math_assessment_detail_db.py",
        "repair_math_assessment_titles.py",
        "repair_math_assessment_item_fields.py",
        "apply_math_assessment_table_boundary_repairs.py",
        "promote_math_assessment_recovery_release.py",
        "promote_recovered_math_assessment_titles.py",
        "propose_math_assessment_explicit_item_recovery.py",
        "propose_math_assessment_unbounded_bundle_splits.py",
        "propose_math_assessment_table_boundary_repairs.py",
        "quarantine_rejected_math_assessment_titles.py",
        "validate_math_assessment_publish_quality.py",
    }
)
LEGACY_MATH_PIPELINE = frozenset(
    {
        "math_assessment_detail_parser.py",
        "math_subject_aliases.py",
        "build_math_assessment_manifest.py",
        "build_math_assessment_evidence_index.py",
        "build_strict_math_shortlist.py",
        "build_math_assessment_detail_db.py",
        "build_math_assessment_publish_db.py",
        "build_school_subject_assessment_catalog.py",
        "build_schoolinfo_4ga_semester.py",
        "extract_math_assessment_batch.py",
        "extract_math_assessment_samples.py",
        "extract_math_candidate_text.py",
        "fallback_math_assessment_records.py",
        "retry_math_assessment_records.py",
        "build_priority_review_packet.py",
        "build_remaining_generic_candidate_index.py",
        "audit_reference_coverage.py",
        "export_assessment_item_pdf.py",
    }
)
SCIENCE_RULE_FILES = frozenset(
    {
        "science_rules.py",
        "science_title_rules.py",
        "check_science_rule_sites.py",
        "audit_middle_segments.py",
        "middle_items.py",
        "middle_fields.py",
        "middle_subjects.py",
        "middle_segments.py",
        # The product boundary checker checks the retained upstream attribution.
        "check-product-boundary.mjs",
    }
)
RULE_NAMES = frozenset(
    {
        "BLOCKING_TABLE_FLAGS",
        "WARNING_TABLE_FLAGS",
        "OTHER_SUBJECT_TITLE_RE",
        "PUBLIC_ITEM_SQL",
        "EXPECTED_STANDARD_PREFIXES",
        "standard_alignment",
        "subject_code_key",
        "subjects_for_standard_codes",
        "SUBJECT_PATTERNS",
        "OTHER_SUBJECT_RE",
        "MATH_CONTEXT_RE",
        "NON_MATH_SOURCE_SIGNAL_RE",
        "METHOD_TERMS",
        "METHOD_LABELS",
        "TASK_SIGNAL_RE",
        "task_name_is_rejected",
        "audit_flags",
        "_exact_fields",
    }
)
ROOT = Path(__file__).resolve().parents[1]


def classification(path: Path) -> str:
    name = path.relative_to(ROOT / "scripts").as_posix()
    for label, names in (
        ("s15_target", S15_TARGETS),
        ("legacy_math_pipeline", LEGACY_MATH_PIPELINE),
        ("science_rule", SCIENCE_RULE_FILES),
    ):
        if name in names:
            return label
    return "unclassified"


def inventory(path: Path) -> list[dict]:
    source = path.read_text(encoding="utf-8-sig")
    result = []

    def add(line: int, kind: str, symbol: str, forbidden: bool = False) -> None:
        result.append(
            {
                "file": path.relative_to(ROOT).as_posix(),
                "line": line,
                "kind": kind,
                "symbol": symbol,
                "classification": classification(path),
                "forbidden_in_target": forbidden,
            }
        )

    for number, line in enumerate(source.splitlines(), 1):
        if "10|12" in line:
            add(number, "legacy_prefix", "10|12", True)
        if "수학" in line:
            add(number, "text", "수학")
    if path.suffix != ".py":
        return result
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in RULE_NAMES:
            add(node.lineno, "definition", node.name, True)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name) and name.id in RULE_NAMES:
                        add(node.lineno, "definition", name.id, True)
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in RULE_NAMES:
                    shared = (node.module or "").split(".")[-1] == "science_rules"
                    add(node.lineno, "import", alias.name, not shared)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", default=sorted(S15_TARGETS))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    targets = {Path(name).name for name in args.targets}
    sites = [
        site
        for path in sorted((ROOT / "scripts").rglob("*"))
        if path.suffix in {".py", ".js", ".mjs", ".ts"}
        for site in inventory(path)
    ]
    unclassified = [site for site in sites if site["classification"] == "unclassified"]
    violations = [
        site for site in sites if Path(site["file"]).name in targets and site["forbidden_in_target"]
    ]
    missing = sorted(name for name in targets if not (ROOT / "scripts" / name).is_file())
    report = {
        "passed": not (unclassified or violations or missing),
        "targets": sorted(targets),
        "sites": sites,
        "violations": violations,
        "unclassified": unclassified,
        "missing_targets": missing,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for site in violations + unclassified:
        print(f"{site['file']}:{site['line']}: {site['kind']} {site['symbol']}")
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "sites": len(sites),
                "violations": len(violations),
                "unclassified": len(unclassified),
                "missing_targets": missing,
            }
        )
    )
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
