"""Audit source traces, sibling arithmetic, development replay and offline scope."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

from compare_middle_performance_items import ROUNDS, column_audit, metrics, read, safety_counts
from compare_middle_s6d2e import compare_cell, representative_items, reviewer_rows, save
from compare_middle_s6d2f import PREFIX, REVIEW_PREFIXES, suspects
from compare_middle_s6d3b import field_audit
from validate_middle_s6d2e import RULE_FILES, scope_audit
from verify_middle_s6d2f import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {r: read(f"data/derived/items/{r}.json") for r in ROUNDS}
    comparison = read(f"docs/dev/{PREFIX}-comparison.json")
    recheck = read(f"docs/dev/{PREFIX}-recheck.json")
    audits = {r: safety_counts(report) | column_audit(report) | field_audit(report)
              | scope_audit(report) for r, report in reports.items()}
    checks = {"fresh_audit_errors": sum(v for a in audits.values() for v in a.values()),
              "comparison_audit_errors": sum(v for a in comparison["rounds"].values()
                                             for v in a["audit"].values()),
              "metric_replay_errors": 0, "snapshot_baseline_errors": 0,
              "conversion_hash_mismatches": 0, "sibling_arithmetic_errors": 0,
              "development_replay_errors": 0}
    snapshots, conversions = {}, {}
    baseline = read("docs/dev/2026-11-09-s6d2e-comparison.json")
    before_reports = {}
    for r, report in reports.items():
        before = read(f"data/derived/items/{r}.prev-s6d2e.json")
        before_reports[r] = before
        checks["snapshot_baseline_errors"] += metrics(before) != baseline["rounds"][r]["after"]
        for phase, value in (("before", before), ("after", report)):
            checks["metric_replay_errors"] += metrics(value) != comparison["rounds"][r][phase]
        for ext in ("json", "md"):
            path = f"data/derived/items/{r}.prev-s6d2e.{ext}"
            snapshots[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for d in report["documents"]:
            conversions[d["converted_path"]] = d["text_sha256"]
        for item in report["items"]:
            for name, f in item["fields"].items():
                if f.get("aggregation") != "sum_sibling_allocations":
                    continue
                evidence = f["evidence"]
                cols = item["boundary_evidence"]["merged_columns"]
                checks["sibling_arithmetic_errors"] += not (
                    len(cols) > 1 and len(evidence) == len(cols)
                    and {o["locator"]["col"] for o in evidence} == set(cols)
                    and len({o["locator"]["row"] for o in evidence}) == 1
                    and all(o["locator"]["colspan"] == 1 for o in evidence)
                    and f["components"] == [o["normalized"] for o in evidence]
                    and f["value"] == sum(f["components"])
                    and all(o["unit"] == ("점" if name == "score" else "%") for o in evidence))
    checks["conversion_hash_mismatches"] = sum(
        hashlib.sha256(read(p)["text"].encode()).hexdigest() != sha
        for p, sha in conversions.items())
    manifest = ROOT / "data/derived/s6d2f/snapshot-manifest.json"
    if manifest.exists():
        checks["snapshot_baseline_errors"] += read(manifest) != snapshots
    else:
        save(manifest, snapshots)
    selected_cache = {id(report): representative_items(report)
                      for phase in (before_reports, reports) for report in phase.values()}
    import compare_middle_s6d2e as shared

    shared.representative_items = lambda report: selected_cache[id(report)]
    all_cells = []
    for prefix in REVIEW_PREFIXES:
        sample = read(f"docs/dev/{prefix}-review-sample.json")
        reviewer = ROOT / (
            "docs/dev/2026-11-09-s6d2b-astra-review.md" if prefix == "2026-11-08-s6d2b"
            else f"docs/dev/{prefix}-astra-review.md")
        rows = reviewer_rows(reviewer)
        for cell in sample["source_review"]:
            all_cells.append((cell["round"], cell["school"], cell["grade"], cell["semester"]))
            actual = next(c for c in recheck["cells"]
                          if c["sample"] == prefix and c["cell"]["cell_id"] == cell["cell_id"])
            for phase, collection in (("before", before_reports), ("after", reports)):
                expected = compare_cell(rows[cell["cell_id"]], collection[cell["round"]], cell)
                # Reviewer line spans are tuples in memory and arrays in JSON.
                expected = json.loads(json.dumps(expected, ensure_ascii=False))
                checks["development_replay_errors"] += expected != actual[phase]
    checks["development_coverage_errors"] = len(all_cells) != 80 or len(set(all_cells)) != 80
    checks["unreadable_cell_count_errors"] = sum(c["unreadable"] for c in recheck["cells"]) != 4
    checks["suspect_replay_errors"] = suspects(reports) != read(f"docs/dev/{PREFIX}-suspects.json")
    checks["new_independent_sample_created"] = any(
        (ROOT / f"docs/dev/{PREFIX}-review-sample.{ext}").exists() for ext in ("json", "md"))
    code = "\n".join((ROOT / f"scripts/{name}.py").read_text(encoding="utf-8")
                     for name in RULE_FILES)
    code += "\n" + inspect.getsource(safety_counts) + inspect.getsource(column_audit)
    identifiers = {str(d[k]) for report in reports.values() for d in report["documents"]
                   for k in ("school", "school_code", "filename", "converted_path", "sha256")
                   if d.get(k) and len(str(d[k])) >= 4}
    checks["hardcoding_grep_matches"] = sorted(v for v in identifiers if v in code)
    checks["coordinate_branch_grep_matches"] = re.findall(
        r"(?:start|end|page|school|filename)\s*\]?\s*==\s*(?:[1-9]\d{2,}|['\"][^'\"]{8,})", code)
    regression = read("data/derived/s6d2f/pytest-after.json")
    checks["new_regression_failures"] = regression["new_failures_excluding_gold_score"]
    checks["regression_access_violations"] = regression["access_violations"]
    checks["report_access_violations"] = comparison["access_violations"]
    checks["access_violations"] = VIOLATIONS
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    checks["git_diff_check_errors"] = diff.returncode
    historical = subprocess.run(["git", "diff", "--name-only", "--", "docs/dev/*-review-sample.*",
                                 "docs/dev/*-astra-review.md"],
                                cwd=ROOT, capture_output=True, text=True)
    checks["historical_review_artifacts_changed"] = bool(historical.stdout.strip())
    result = {"checks": checks, "audits": audits, "snapshot_sha256": snapshots,
              "conversion_count": len(conversions), "regression_counts": regression["counts"],
              "gold_score_failures": regression["gold_score_failures"]}
    save(ROOT / "data/derived/s6d2f/validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
