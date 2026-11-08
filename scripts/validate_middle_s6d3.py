"""Read-only checks for S6d-3 reports, provenance, snapshots and hardcoding."""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from pathlib import Path

from compare_middle_items import safety_counts
from compare_middle_performance_items import ROUNDS, column_audit, independent, read
from compare_middle_s6d3 import PREFIX, SEED, extra_audit, save
from verify_middle_s6d3 import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    comparison = read(f"docs/dev/{PREFIX}-comparison.json")
    reports = {r: read(f"data/derived/items/{r}.json") for r in ROUNDS}
    checks = {}
    checks["audit_errors"] = sum(v for row in comparison["rounds"].values()
                                  for v in row["audit"].values())
    fresh_audits = {r: safety_counts(report) | column_audit(report) | extra_audit(report)
                   for r, report in reports.items()}
    checks["fresh_audit_errors"] = sum(v for row in fresh_audits.values() for v in row.values())
    snapshots = {}
    for r in ROUNDS:
        for ext in ("json", "md"):
            path = ROOT / f"data/derived/items/{r}.prev-s6d2b.{ext}"
            snapshots[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    checks["snapshot_count"] = len(snapshots)
    conversions = {d["converted_path"]: d["text_sha256"] for report in reports.values()
                   for d in report["documents"]}
    checks["conversion_hash_mismatches"] = sum(
        hashlib.sha256(read(path)["text"].encode("utf-8")).hexdigest() != digest
        for path, digest in conversions.items()
    )
    checks["conversion_count"] = len(conversions)
    sample = read(f"docs/dev/{PREFIX}-field-sample.json")
    population = sorted([(r, i) for r in ROUNDS[1:] for i in independent(reports[r])
                         if i["extraction_status"] == "bounded"],
                        key=lambda p: (p[0], p[1]["item_id"]))
    chosen = random.Random(SEED).sample(population, 14)
    checks["sample_reproduction_errors"] = sum(
        source["round"] != r or pipeline["item_id"] != item["item_id"]
        or pipeline["fields"] != item["fields"]
        for (r, item), source, pipeline in zip(chosen, sample["source_review"],
                                              sample["pipeline_fields"], strict=True)
    )
    checks["sample_duplicate_count"] = 14 - len({p["item_id"] for p in sample["pipeline_fields"]})
    allowed = {"sample_id", "round", "document_id", "child_id", "original_path",
               "converted_path", "grade", "semester", "source_ranges"}
    checks["sample_source_section_value_leaks"] = sum(
        bool(set(s) - allowed) for s in sample["source_review"])
    paths = [ROOT / f"scripts/{name}.py" for name in
             ("middle_items", "middle_fields", "middle_identity")]
    code = "\n".join(p.read_text(encoding="utf-8") for p in paths)
    identifiers = {str(d[key]) for report in reports.values() for d in report["documents"]
                   for key in ("school", "filename", "converted_path", "sha256")
                   if d.get(key) and len(str(d[key])) >= 4}
    checks["hardcoding_grep_matches"] = sorted(s for s in identifiers if s in code)
    checks["coordinate_branch_grep_matches"] = re.findall(
        r"(?:start|end|page|school|filename)\s*\]?\s*==\s*(?:[1-9]\d{2,}|['\"][^'\"]{8,})",
        code,
    )
    regression = read("data/derived/s6d3/pytest-after.json")
    checks["new_regression_failures"] = regression["new_failures"]
    checks["access_violations"] = VIOLATIONS
    checks["report_access_violations"] = comparison["access_violations"]
    result = {"checks": checks, "snapshot_sha256": snapshots}
    save(ROOT / "data/derived/s6d3/validation.json", result)
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    errors = [v for k, v in checks.items() if k not in {
        "snapshot_count", "conversion_count",
    } and v]
    if errors or checks["snapshot_count"] != 6:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
