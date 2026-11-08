"""Verify S6d-3c provenance, frozen snapshots, sampling and regression locally."""

from __future__ import annotations

import hashlib
import inspect
import json
import random
import re
import sys
from pathlib import Path

from compare_middle_performance_items import ROUNDS, column_audit, independent, read
from compare_middle_s6d3 import states
from compare_middle_s6d3c import PREFIX, SEED, field_audit, sample_population, save
from middle_items import source_tables
from validate_middle_s6d2d import scope_audit
from verify_middle_s6d3c import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    from compare_middle_items import safety_counts

    reports = {r: read(f"data/derived/items/{r}.json") for r in ROUNDS}
    comparison = read(f"docs/dev/{PREFIX}-comparison.json")
    audits = {r: safety_counts(report) | column_audit(report) | field_audit(report)
              | scope_audit(report)
              for r, report in reports.items()}
    checks = {"fresh_audit_errors": sum(v for counts in audits.values() for v in counts.values()),
              "comparison_audit_errors": sum(v for row in comparison["rounds"].values()
                                             for v in row["audit"].values()),
              "field_state_reproduction_errors": 0, "conversion_hash_mismatches": 0,
              "snapshot_baseline_errors": 0, "absence_trace_errors": 0,
              "absence_owner_errors": 0, "absence_without_proof": 0,
              "empty_bounded_titles": 0, "representative_title_trace_errors": 0}
    conversions = {}
    for r, report in reports.items():
        from compare_middle_performance_items import metrics

        baseline = read("docs/dev/2026-11-09-s6d2d-comparison.json")
        checks["snapshot_baseline_errors"] += metrics(read(
            f"data/derived/items/{r}.prev-s6d2d.json")) != baseline["rounds"][r]["after"]
        by_id = {i["item_id"]: i for i in report["items"]}
        for item in report["items"]:
            text = read(item["converted_path"])["text"]
            title = item["fields"]["title"]
            if item["extraction_status"] == "bounded":
                checks["empty_bounded_titles"] += not bool(title["value"])
            if title.get("selection_rule"):
                candidates = [o["text"] for o in title["evidence"]]
                candidates += [o["text"] for s in title.get("source_observations", [])
                               for o in s["evidence"]]
                checks["representative_title_trace_errors"] += title["value"] not in candidates
            for field in item["fields"].values():
                proof = field.get("absence_evidence", field["evidence"]
                                  if field.get("source_absent") else [])
                if field.get("source_absent") and field["status"] == "source_absent":
                    checks["absence_without_proof"] += not bool(proof)
                for obs in proof:
                    owner = by_id.get(obs.get("owner_item_id"), item)
                    loc = obs["locator"]
                    checks["absence_trace_errors"] += text[loc["start"]:loc["end"]] != obs["raw"]
                    checks["absence_owner_errors"] += not any(
                        v["start"] <= loc["start"] <= loc["end"] <= v["end"]
                        for v in owner["owned_ranges"])
        for phase, snapshot in (
            ("before", read(f"data/derived/items/{r}.prev-s6d2d.json")), ("after", report)
        ):
            bounded = [i for i in independent(snapshot) if i["extraction_status"] == "bounded"]
            checks["field_state_reproduction_errors"] += (
                states(bounded) != comparison["rounds"][r]["field_states"][phase]
            )
        for document in report["documents"]:
            conversions[document["converted_path"]] = document["text_sha256"]
    checks["conversion_hash_mismatches"] = sum(
        hashlib.sha256(read(path)["text"].encode()).hexdigest() != digest
        for path, digest in conversions.items()
    )
    snapshots = {f"data/derived/items/{r}.prev-s6d2d.{ext}": hashlib.sha256(
        (ROOT / f"data/derived/items/{r}.prev-s6d2d.{ext}").read_bytes()).hexdigest()
        for r in ROUNDS for ext in ("json", "md")}
    sample = read(f"docs/dev/{PREFIX}-field-sample.json")
    population = sample_population(reports)
    expected = [(r, i["item_id"]) for r, i in random.Random(SEED).sample(population, 14)]
    actual = [(s["round"], p["item_id"]) for s, p in zip(
        sample["source_review"], sample["pipeline_fields"], strict=True
    )]
    checks["sample_reproduction_errors"] = int(expected != actual)
    checks["sample_duplicates"] = len(actual) - len(set(actual))
    checks["sample_missing_summary_detail_ranges"] = 0
    checks["sample_source_value_leaks"] = 0
    checks["sample_locator_errors"] = 0
    checks["sample_raw_table_range_errors"] = 0
    lookup_count = 0
    allowed = {"sample_id", "round", "document_id", "child_id", "original_path",
               "converted_path", "grade", "semester", "source_ranges"}
    for entry in sample["source_review"]:
        checks["sample_source_value_leaks"] += bool(set(entry) - allowed)
        ranges = entry["source_ranges"]
        checks["sample_missing_summary_detail_ranges"] += (
            {r["source_role"] for r in ranges} != {"summary", "detail"}
        )
        text = read(entry["converted_path"])["text"]
        for loc in ranges:
            lookup_count += bool(loc.get("range_kind"))
            checks["sample_locator_errors"] += not 0 <= loc["start"] <= loc["end"] <= len(text)
            checks["sample_locator_errors"] += text.count("\n", 0, loc["start"]) + 1 != (
                loc["line_start"]
            )
            if loc.get("range_kind") == "raw_table_candidate_scope_unconfirmed":
                checks["sample_raw_table_range_errors"] += not any(
                    t["start"] == loc["start"] and t["end"] == loc["end"]
                    for t in source_tables(text))
    names = ("middle_items", "middle_fields", "middle_identity", "assessment_symbols",
             "middle_item_scope", "middle_assessment_scope", "middle_pdf_summary",
             "audit_middle_items")
    code = "\n".join((ROOT / f"scripts/{name}.py").read_text(encoding="utf-8") for name in names)
    # The generic audit is checked in full. Older school-specific diagnostic
    # example lists elsewhere in compare_middle_items do not enter extraction.
    code += "\n" + inspect.getsource(safety_counts)
    identifiers = {str(d[k]) for report in reports.values() for d in report["documents"]
                   for k in ("school", "school_code", "filename", "converted_path", "sha256")
                   if d.get(k) and len(str(d[k])) >= 4}
    checks["hardcoding_grep_matches"] = sorted(value for value in identifiers if value in code)
    checks["coordinate_branch_grep_matches"] = re.findall(
        r"(?:start|end|page|school|filename)\s*\]?\s*==\s*(?:[1-9]\d{2,}|['\"][^'\"]{8,})", code,
    )
    regression = read("data/derived/s6d3c/pytest-after.json")
    checks["new_regression_failures"] = regression["new_failures"]
    checks["regression_access_violations"] = regression["access_violations"]
    checks["report_access_violations"] = comparison["access_violations"]
    checks["access_violations"] = VIOLATIONS
    recheck = read(f"docs/dev/{PREFIX}-field-recheck.json")
    checks["development_case_count_errors"] = recheck["case_count"] != 28
    checks["development_comparable_count_errors"] = recheck["comparable_count"] != 24
    result = {"checks": checks, "audits": audits, "snapshot_sha256": snapshots,
              "conversion_count": len(conversions), "sample_population": len(population),
              "sample_lookup_scope_count": lookup_count,
              "regression_counts": regression.get("counts")}
    save(ROOT / "data/derived/s6d3c/validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
