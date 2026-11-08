"""Reproduce offline scope, geometry, sampling and regression checks."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from compare_middle_performance_items import ROUNDS, column_audit, metrics, read
from compare_middle_s6d2d import PREFIX, representative_items, sample, save
from compare_middle_s6d3b import field_audit
from middle_subjects import subject_headers
from verify_middle_s6d2d import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
RULE_FILES = ("middle_items", "middle_fields", "middle_identity", "middle_item_scope",
              "middle_assessment_scope", "middle_pdf_summary")


def scope_audit(report):
    checks = dict.fromkeys(("assessment_subject_trace", "assessment_subject_basis",
                            "assessment_grade_trace", "assessment_semester_trace",
                            "assessment_row_context", "pdf_cell_geometry",
                            "pdf_cell_value_alignment"), 0)
    cache, headings, pdfs = {}, {}, {}
    import fitz
    from middle_pdf_summary import compact

    try:
        for item in report["items"]:
            proof = item["boundary_evidence"].get("assessment_scope")
            if not proof:
                continue
            path = item["converted_path"]
            if path not in cache:
                cache[path] = read(path)["text"]
                headings[path] = subject_headers(cache[path])
            text = cache[path]
            for obs in proof["subject"]:
                loc = obs["locator"]
                raw = text[loc["start"]:loc["end"]]
                checks["assessment_subject_trace"] += raw != obs["raw"]
                basis = obs["basis"]
                if basis == "subject_cell":
                    checks["assessment_subject_basis"] += compact(raw) not in {"과학", "과학과"}
                elif basis == "subject_heading":
                    checks["assessment_subject_basis"] += not any(
                        h["key"] == "과학" and h["start"] == loc["start"]
                        and h["end"] == loc["end"] for h in headings[path])
                elif basis == "unmixed_standards_prefix":
                    checks["assessment_subject_basis"] += not re.fullmatch(r"\[\s*9\s*과", raw)
                else:
                    checks["assessment_subject_basis"] += 1
            checks["assessment_subject_basis"] += not bool(proof["subject"])
            checks["assessment_grade_trace"] += not bool(proof["grade"])
            for grade in proof["grade"]:
                source = item["filename"] if grade.get("source") == "filename" else text
                checks["assessment_grade_trace"] += (
                    grade["grade"] != item["grade"]
                    or source[grade["start"]:grade["end"]] != grade["raw"])
            for term in proof["semester"]:
                source = item["filename"] if term["source"] == "filename" else text
                checks["assessment_semester_trace"] += (
                    term["semester"] != item["semester"]
                    or source[term["start"]:term["end"]] != term["text"])
            for role, obs in item["boundary_evidence"].get("row_context", {}).items():
                raw = obs["raw"]
                loc = obs["locator"]
                checks["assessment_row_context"] += text[loc["start"]:loc["end"]] != raw
                if role in {"grade", "semester"}:
                    checks["assessment_row_context"] += int(compact(raw)[0]) != item[role]
                elif role == "subject":
                    checks["assessment_row_context"] += compact(raw) not in {"과학", "과학과"}
            if not item["boundary_evidence"].get("pdf_summary"):
                continue
            original = item["original_path"]
            if original not in pdfs:
                pdfs[original] = fitz.open(ROOT / original)
            pdf = pdfs[original]
            for field in item["fields"].values():
                for obs in field["evidence"]:
                    physical = obs.get("source_cell_proof")
                    if not physical:
                        checks["pdf_cell_geometry"] += 1
                        continue
                    page = pdf[physical["page"] - 1]
                    actual = compact(page.get_textbox(fitz.Rect(physical["bbox"])))
                    expected = compact(physical["value"])
                    checks["pdf_cell_geometry"] += actual != expected
                    normalized = compact(re.sub(r"<[^>]*>", "", obs["raw"]))
                    checks["pdf_cell_value_alignment"] += normalized not in expected
    finally:
        for pdf in pdfs.values():
            pdf.close()
    return checks


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    from compare_middle_items import safety_counts

    reports = {r: read(f"data/derived/items/{r}.json") for r in ROUNDS}
    comparison = read(f"docs/dev/{PREFIX}-comparison.json")
    audits = {r: safety_counts(report) | column_audit(report) | field_audit(report)
              | scope_audit(report) for r, report in reports.items()}
    checks = {"fresh_audit_errors": sum(v for a in audits.values() for v in a.values()),
              "comparison_audit_errors": sum(v for r in comparison["rounds"].values()
                                             for v in r["audit"].values()),
              "metric_reproduction_errors": 0, "snapshot_replay_errors": 0,
              "conversion_hash_mismatches": 0, "representative_edition_errors": 0}
    checks["explicit_task_heading_conflicts"] = sum(
        i["fields"]["title"]["status"] == "conflict"
        and any(o.get("header_raw") and re.fullmatch(
            r"(?:수행|평가)\s*과제", o["header_raw"])
                for o in i["fields"]["title"]["evidence"])
        and any(not o.get("header_raw") and o.get("source_cell_proof")
                for o in i["fields"]["title"]["evidence"])
        for report in reports.values() for i in report["items"]
        if i["extraction_status"] == "bounded")
    checks["particle_leading_bounded_titles"] = sum(
        bool(re.match(r"^(?:을|를|은|는|이|가|와|과|의|에|에서|으로|로)\s",
                      i["fields"]["title"]["value"]))
        for report in reports.values() for i in report["items"]
        if i["extraction_status"] == "bounded")
    snapshots, conversions = {}, {}
    for r, report in reports.items():
        before = read(f"data/derived/items/{r}.prev-s6d3b.json")
        for phase, value in (("before", before), ("after", report)):
            checks["metric_reproduction_errors"] += metrics(value) != comparison["rounds"][r][phase]
        # Frozen JSON must be the immediate pre-work S6d-3b result, not an
        # earlier S6d-2c snapshot or a later partially implemented replay.
        baseline = read("docs/dev/2026-11-09-s6d3b-comparison.json")
        checks["snapshot_replay_errors"] += metrics(before) != baseline["rounds"][r]["after"]
        selected = {d["converted_path"] for d in report["documents"] if d["development_selected"]}
        checks["representative_edition_errors"] += any(
            i["converted_path"] not in selected for i in representative_items(report))
        for ext in ("json", "md"):
            path = f"data/derived/items/{r}.prev-s6d3b.{ext}"
            snapshots[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for d in report["documents"]:
            conversions[d["converted_path"]] = d["text_sha256"]
    checks["conversion_hash_mismatches"] = sum(
        hashlib.sha256(read(p)["text"].encode()).hexdigest() != digest
        for p, digest in conversions.items())
    actual = read(f"docs/dev/{PREFIX}-review-sample.json")
    expected = sample(reports)
    actual_cells = [(c["round"], c["school"], c["grade"], c["semester"])
                    for c in actual["source_review"]]
    expected_cells = [(c["round"], c["school"], c["grade"], c["semester"])
                      for c in expected["source_review"]]
    checks["sample_reproduction_errors"] = actual_cells != expected_cells
    checks["sample_duplicates"] = len(actual_cells) - len(set(actual_cells))
    checks["sample_frame_errors"] = (actual["population_size"] != 32
                                      or actual["excluded_cell_count"] != 48)
    allowed = {"cell_id", "round", "school", "grade", "semester", "science_ranges",
               "source_documents", "unreadable_documents", "reviewer_items", "instruction"}
    source_allowed = {"original_path", "filename", "document_id", "child_id", "converted_path",
                      "locator", "line_start", "line_end", "semester", "semester_evidence"}
    checks["sample_source_value_leaks"] = sum(
        bool(set(c) - allowed) or bool(c["reviewer_items"])
        or any(set(s) - source_allowed for s in c["science_ranges"])
        or any(set(d) - {"document_id", "child_id", "original_path", "converted_path",
                         "filename", "grades"} for d in c["source_documents"])
        for c in actual["source_review"])
    checks["sample_document_reproduction_errors"] = any(
        a["source_documents"] != b["source_documents"]
        for a, b in zip(actual["source_review"], expected["source_review"], strict=True))
    checks["sample_whole_document_instruction_missing"] = sum(
        "문서 전체" not in c["instruction"] for c in actual["source_review"])
    checks["sample_pipeline_reproduction_errors"] = (
        actual["pipeline_comparison"] != expected["pipeline_comparison"])
    code = "\n".join((ROOT / f"scripts/{name}.py").read_text(encoding="utf-8")
                     for name in RULE_FILES)
    identifiers = {str(d[k]) for report in reports.values() for d in report["documents"]
                   for k in ("school", "school_code", "filename", "converted_path", "sha256")
                   if d.get(k) and len(str(d[k])) >= 4}
    checks["hardcoding_grep_matches"] = sorted(v for v in identifiers if v in code)
    checks["coordinate_branch_grep_matches"] = re.findall(
        r"(?:start|end|page|school|filename)\s*\]?\s*==\s*(?:[1-9]\d{2,}|['\"][^'\"]{8,})", code)
    regression = read("data/derived/s6d2d/pytest-after.json")
    checks["new_regression_failures"] = regression["new_failures"]
    checks["regression_access_violations"] = regression["access_violations"]
    checks["report_access_violations"] = comparison["access_violations"]
    checks["access_violations"] = VIOLATIONS
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    checks["git_diff_check_errors"] = diff.returncode
    result = {"checks": checks, "audits": audits, "snapshot_sha256": snapshots,
              "conversion_count": len(conversions), "sample_population": actual["population_size"],
              "regression_counts": regression["counts"]}
    save(ROOT / "data/derived/s6d2d/validation.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
