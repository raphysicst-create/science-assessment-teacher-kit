"""Validate offline detail replay, baseline preservation and source trace invariants."""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import subprocess
import sys

from compare_middle_items import safety_counts
from compare_middle_performance_items import ROUNDS, column_audit, independent, metrics, read
from compare_middle_s6d3 import states
from compare_middle_s6d3d import DETAIL_FIELDS, PREFIX, ROOT, field_audit, save, scope_audit
from validate_middle_s6d2e import RULE_FILES
from verify_middle_s6d3d import VIOLATIONS, guard


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {r: read(f"data/derived/items/{r}.json") for r in ROUNDS}
    comparison = read(f"docs/dev/{PREFIX}-comparison.json")
    diagnosis = read(f"docs/dev/{PREFIX}-diagnosis.json")
    recheck = read(f"docs/dev/{PREFIX}-field-recheck.json")
    baseline = read("docs/dev/2026-11-09-s6d2f-comparison.json")
    audits = {r: safety_counts(report) | column_audit(report) | field_audit(report)
              | scope_audit(report) for r, report in reports.items()}
    checks = {"fresh_audit_errors": sum(v for a in audits.values() for v in a.values()),
              "saved_audit_errors": sum(v for a in comparison["rounds"].values()
                                        for v in a["audit"].values()),
              "baseline_metric_errors": 0, "metric_replay_errors": 0,
              "field_state_replay_errors": 0, "conversion_hash_errors": 0,
              "diagnosis_coverage_errors": 0, "snapshot_hash_errors": 0}
    snapshots, conversions, expected_missing = {}, {}, set()
    for r, report in reports.items():
        before = read(f"data/derived/items/{r}.prev-s6d2f.json")
        checks["baseline_metric_errors"] += metrics(before) != baseline["rounds"][r]["after"]
        for phase, value in (("before", before), ("after", report)):
            checks["metric_replay_errors"] += metrics(value) != comparison["rounds"][r][phase]
            counts = states([i for i in independent(value) if i["extraction_status"] == "bounded"])
            checks["field_state_replay_errors"] += (
                counts != comparison["rounds"][r]["field_states"][phase])
        for ext in ("json", "md"):
            path = f"data/derived/items/{r}.prev-s6d2f.{ext}"
            snapshots[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for d in report["documents"]:
            conversions[d["converted_path"]] = d["text_sha256"]
        expected_missing.update((r, i["item_id"]) for i in independent(before)
                                if i["extraction_status"] == "bounded" and any(
                                    i["fields"][k]["status"] == "unconfirmed"
                                    for k in DETAIL_FIELDS[:3]))
    actual_missing = {(i["round"], i["item_id"]) for i in diagnosis["items"]}
    checks["diagnosis_coverage_errors"] = len(expected_missing ^ actual_missing)
    checks["diagnosis_cluster_count_errors"] = sum(
        c["count"] for c in diagnosis["clusters"]) != len(expected_missing)
    checks["conversion_hash_errors"] = sum(
        hashlib.sha256(read(path)["text"].encode()).hexdigest() != digest
        for path, digest in conversions.items())
    manifest = ROOT / "data/derived/s6d3d/snapshot-manifest.json"
    if manifest.exists():
        checks["snapshot_hash_errors"] = read(manifest) != snapshots
    else:
        save(manifest, snapshots)
    code = "\n".join((ROOT / f"scripts/{name}.py").read_text(encoding="utf-8")
                     for name in (*RULE_FILES, "assessment_symbols"))
    code += inspect.getsource(safety_counts) + inspect.getsource(column_audit)
    identifiers = {str(d[k]) for report in reports.values() for d in report["documents"]
                   for k in ("school", "school_code", "filename", "converted_path", "sha256")
                   if d.get(k) and len(str(d[k])) >= 4}
    checks["hardcoding_grep_matches"] = sorted(v for v in identifiers if v in code)
    checks["coordinate_branch_grep_matches"] = re.findall(
        r"(?:start|end|page|school|filename)\s*\]?\s*==\s*(?:[1-9]\d{2,}|['\"][^'\"]{8,})", code)
    regression = read("data/derived/s6d3d/pytest-after.json")
    before_regression = read("data/derived/s6d3d/pytest-before.json")
    before_log = (ROOT / "data/derived/s6d3d/pytest-before.log").read_text(encoding="utf-8")
    markers = "".join(re.findall(r"(?m)^([.FEsx]+)\s*\[\s*\d+%\]$", before_log))
    checks["baseline_failure_count_error"] = len(before_regression["failures"]) != 18
    checks["new_regression_failures"] = regression["new_failures"]
    checks["development_regressions"] = recheck["regressions"]
    checks["lost_present"] = comparison["lost_present"]
    checks["development_case_count_error"] = recheck["case_count"] != 42
    checks["access_violations"] = (VIOLATIONS + diagnosis["access_violations"]
                                   + comparison["access_violations"] + recheck["access_violations"]
                                   + before_regression["access_violations"]
                                   + regression["access_violations"])
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    checks["git_diff_check_errors"] = diff.returncode
    result = {"checks": checks, "audits": audits, "conversion_count": len(conversions),
              "snapshot_sha256": snapshots,
              "regression_before": {"total": len(markers), "passed": markers.count("."),
                                    "failed": markers.count("F")},
              "regression_after": regression["counts"]}
    save(ROOT / "data/derived/s6d3d/validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
