"""Replay S6d-2c provenance, edition, scope, sampling and regression audits."""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from pathlib import Path

from compare_middle_items import safety_counts
from compare_middle_performance_items import ROUNDS, column_audit, read
from compare_middle_s6d2c import PREFIX, REVIEW_PREFIXES, SEED, save
from compare_middle_s6d3 import extra_audit
from middle_items import source_tables
from verify_middle_s6d2c import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]


def regression_counts(path):
    log = path.read_text(encoding="utf-8")
    markers = "".join(re.match(r"^[.FEsx]+", line)[0] for line in log.splitlines()
                      if re.fullmatch(r"[.FEsx]+\s*\[\s*\d+%\]", line))
    return {"passed": markers.count("."), "failed": markers.count("F"),
            "total": len(markers)}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {r: read(f"data/derived/items/{r}.json") for r in ROUNDS}
    comparison = read(f"docs/dev/{PREFIX}-comparison.json")
    checks = {}
    audits = {r: safety_counts(report) | column_audit(report) | extra_audit(report)
              for r, report in reports.items()}
    checks["fresh_audit_errors"] = sum(v for counts in audits.values() for v in counts.values())
    checks["comparison_audit_errors"] = sum(v for row in comparison["rounds"].values()
                                            for v in row["audit"].values())
    checks["unselected_edition_items"] = 0
    checks["bounded_scope_conflicts"] = 0
    checks["nonempty_span_overlap_promotions"] = 0
    conversions = {}
    tables = {}
    for report in reports.values():
        selected = {d["converted_path"] for d in report["documents"]
                    if d["development_selected"]}
        for d in report["documents"]:
            conversions[d["converted_path"]] = d["text_sha256"]
        for item in report["items"]:
            checks["unselected_edition_items"] += item["converted_path"] not in selected
            if item["extraction_status"] != "bounded":
                continue
            scope = item["boundary_evidence"].get("item_scope", {})
            checks["bounded_scope_conflicts"] += bool(
                scope.get("grade") and scope["grade"]["grade"] != item["grade"]
                or scope.get("heading") and scope["heading"]["program"]
            )
            overlaps = item["boundary_evidence"].get("empty_span_overlaps", [])
            if overlaps:
                path = item["converted_path"]
                if path not in tables:
                    tables[path] = source_tables(read(path)["text"])
                table = tables[path][item["layout_position"]["table"]]
                by_start = {c["start"]: c for c in table["cells"]}
                checks["nonempty_span_overlap_promotions"] += sum(
                    bool(by_start[o["previous_start"]]["text"]) for o in overlaps
                )
    checks["conversion_hash_mismatches"] = sum(
        hashlib.sha256(read(p)["text"].encode("utf-8")).hexdigest() != digest
        for p, digest in conversions.items()
    )
    snapshots = {f"data/derived/items/{r}.prev-s6d3.{ext}": hashlib.sha256(
        (ROOT / f"data/derived/items/{r}.prev-s6d3.{ext}").read_bytes()).hexdigest()
        for r in ROUNDS for ext in ("json", "md")}
    sample = read(f"docs/dev/{PREFIX}-review-sample.json")
    excluded = {(c["round"], c["school"], c["grade"], c["semester"])
                for prefix in REVIEW_PREFIXES
                for c in read(f"docs/dev/{prefix}-review-sample.json")["source_review"]}
    population = [(r, school, grade, term) for r, term in zip(ROUNDS[1:], (2, 1), strict=True)
                  for school in sorted({d["school"] for d in reports[r]["documents"]})
                  for grade in (1, 2) if (r, school, grade, term) not in excluded]
    actual = [(c["round"], c["school"], c["grade"], c["semester"])
              for c in sample["source_review"]]
    checks["sample_reproduction_errors"] = int(random.Random(SEED).sample(population, 16) != actual)
    checks["sample_previous_overlap"] = len(set(actual) & excluded)
    checks["sample_duplicate_count"] = 16 - len(set(actual))
    allowed = {"cell_id", "round", "school", "grade", "semester", "science_ranges",
               "unreadable_documents", "reviewer_items"}
    checks["sample_source_value_leaks"] = sum(bool(set(c) - allowed) or bool(c["reviewer_items"])
                                            for c in sample["source_review"])
    checks["sample_source_value_leaks"] += sum(
        bool(set(source) & {"boundary_verified", "document_status", "bounded_items", "fields"})
        for c in sample["source_review"] for source in c["science_ranges"]
    )
    checks["sample_nonrepresentative_sources"] = sum(
        not next(d["development_selected"] for d in reports[c["round"]]["documents"]
                 if d["converted_path"] == source["converted_path"])
        for c in sample["source_review"] for source in c["science_ranges"]
    )
    names = ("middle_items", "middle_identity", "middle_item_scope", "middle_item_editions",
             "audit_middle_items")
    code = "\n".join((ROOT / f"scripts/{name}.py").read_text(encoding="utf-8") for name in names)
    identifiers = {str(d[k]) for report in reports.values() for d in report["documents"]
                   for k in ("school", "school_code", "filename", "converted_path", "sha256")
                   if d.get(k) and len(str(d[k])) >= 4}
    checks["hardcoding_grep_matches"] = sorted(i for i in identifiers if i in code)
    checks["coordinate_branch_grep_matches"] = re.findall(
        r"(?:start|end|page|school|filename)\s*\]?\s*==\s*(?:[1-9]\d{2,}|['\"][^'\"]{8,})", code,
    )
    regression = read("data/derived/s6d2c/pytest-after.json")
    checks["new_regression_failures"] = regression["new_failures"]
    checks["regression_access_violations"] = regression["access_violations"]
    checks["report_access_violations"] = comparison["access_violations"]
    checks["access_violations"] = VIOLATIONS
    counts = {phase: regression_counts(ROOT / f"data/derived/s6d2c/pytest-{phase}.log")
              for phase in ("before", "after")}
    result = {"checks": checks, "audits": audits, "snapshot_sha256": snapshots,
              "conversion_count": len(conversions), "regression_counts": counts,
              "sample_population": len(population), "snapshot_count": len(snapshots)}
    save(ROOT / "data/derived/s6d2c/validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
