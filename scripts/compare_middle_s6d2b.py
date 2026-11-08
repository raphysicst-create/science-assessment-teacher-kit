"""Reproduce S6d-2b on the three development rounds, with source-first holdout."""

from __future__ import annotations

import argparse
import copy
import json
import random
import shutil
import sys
from pathlib import Path

import compare_middle_performance_items as prior
from audit_middle_items import audit, markdown
from audit_middle_segments import (
    aggregate,
    markdown_report,
    science_heading_candidates,
    summarize_segments,
)
from audit_middle_subjects import audit as subject_audit
from audit_middle_subjects import markdown as subject_markdown
from middle_rounds import roster_path
from middle_segments import RULE_VERSION as SEGMENT_RULE_VERSION
from middle_segments import segment_document
from verify_middle_s6d2b import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "2026-11-08-s6d2b"
SEED = 2026110823


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save_json(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def preserve(path):
    target = path.with_name(path.stem + ".prev-s6d2" + path.suffix)
    if not target.exists():
        shutil.copyfile(path, target)


def refresh(round_key):
    for kind in ("items", "segments", "subjects"):
        for ext in ("json", "md"):
            path = ROOT / f"data/derived/{kind}/{round_key}.{ext}"
            if path.exists():
                preserve(path)
    path = ROOT / f"data/derived/segments/{round_key}.json"
    s4 = prior.read(path)
    changed = []
    for document in s4["documents"]:
        conversion = prior.read(document["converted_path"])
        child = conversion if document.get("child_id") else None
        segments = segment_document(document["source"], conversion, child)
        if child:
            for segment in segments:
                segment["document_id"] = document["document_id"]
                segment["locator"]["text_field"] = "text"
        # Edition decisions are unchanged; retain their quarantine on new spans.
        if document.get("version_status") in {"superseded", "version_conflict"}:
            for segment in segments:
                segment["statuses"].append(document["version_status"])
        if segments != document["segments"]:
            changed.append(document["document_id"])
            document["segments"] = segments
            document["summary"] = summarize_segments(segments)
    s4["rule_version"] = SEGMENT_RULE_VERSION
    s4["summary"] = aggregate(s4["documents"])
    s4["science_heading_candidates"] = science_heading_candidates(s4["documents"])
    save_json(path, s4)
    write(path.with_suffix(".md"), markdown_report(s4))
    if changed:
        # Keep the original conversion cache, source metadata and edition choice.
        subjects = subject_audit(path, roster_path(ROOT, round_key, None))
        save_json(ROOT / f"data/derived/subjects/{round_key}.json", subjects)
        write(ROOT / f"data/derived/subjects/{round_key}.md", subject_markdown(subjects))
    result = audit(ROOT / f"data/derived/subjects/{round_key}.json",
                   roster_path(ROOT, round_key, None))
    save_json(ROOT / f"data/derived/items/{round_key}.json", result)
    write(ROOT / f"data/derived/items/{round_key}.md", markdown(result))
    return result, changed


def holdout(reports):
    previous = prior.read(f"docs/dev/{prior.PREFIX}-review-sample.json")
    excluded = {(c["round"], c["school"], c["grade"], c["semester"])
                for c in previous["source_review"]}
    population = [
        (r, school, grade, 1 if r == prior.ROUNDS[2] else 2)
        for r in prior.ROUNDS[1:]
        for school in sorted({d["school"] for d in reports[r]["documents"]})
        for grade in (1, 2)
        if (r, school, grade, 1 if r == prior.ROUNDS[2] else 2) not in excluded
    ]
    chosen = random.Random(SEED).sample(population, 16)
    sources, pipelines = [], []
    for n, (r, school, grade, semester) in enumerate(chosen, 1):
        cell_id = f"S{n:02}"
        report = reports[r]
        sources.append({
            "cell_id": cell_id, "round": r, "school": school, "grade": grade,
            "semester": semester,
            "science_ranges": prior.source_ranges(report, grade, semester, school),
            "unreadable_documents": [
                {k: d.get(k) for k in ("original_path", "converted_path", "status", "grades")}
                for d in report["documents"]
                if d["school"] == school and d["status"] == "image_only"
            ], "reviewer_items": [],
        })
        bounded = [i for i in prior.independent(report)
                   if i["school"] == school and i["grade"] == grade
                   and i["extraction_status"] == "bounded"]
        pipelines.append({
            "cell_id": cell_id,
            "bounded_items": [prior.pipeline_item(i) for i in bounded
                              if i["semester"] == semester],
            "semester_unresolved_bounded_items": [prior.pipeline_item(i) for i in bounded
                                                   if i["semester"] is None],
        })
    return {"seed": SEED, "population_size": len(population), "sample_size": 16,
            "excluded_prior_cells": len(excluded), "sampling": previous["sampling"],
            "source_review": sources, "pipeline_comparison": pipelines}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-items", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports, result = {}, {"rounds": {}}
    lines = ["# S6d-2b 개발 자료 전후 비교", "",
             "독립 후보 수. bounded는 구조 확정 수이며 정확도가 아니다. "
             "이전 결과는 *.prev-s6d2.*에 보존했다.", "",
             "| 회차 | bounded 전→후 | 검토 전→후 |", "|---|---:|---:|"]
    for r in prior.ROUNDS:
        if args.refresh_items:
            report = audit(ROOT / f"data/derived/subjects/{r}.json", roster_path(ROOT, r, None))
            save_json(ROOT / f"data/derived/items/{r}.json", report)
            write(ROOT / f"data/derived/items/{r}.md", markdown(report))
        report, changed = refresh(r) if args.refresh else (
            prior.read(f"data/derived/items/{r}.json"), [],
        )
        reports[r] = report
        previous_segments = prior.read(f"data/derived/segments/{r}.prev-s6d2.json")
        current_segments = prior.read(f"data/derived/segments/{r}.json")
        previous_documents = {d["document_id"]: d for d in previous_segments["documents"]}
        changed = [d["document_id"] for d in current_segments["documents"]
                   if d["segments"] != previous_documents[d["document_id"]]["segments"]]
        old = prior.read(f"data/derived/items/{r}.prev-s6d2.json")
        counts = prior.safety_counts(report) | prior.column_audit(report)
        row = {"before": prior.metrics(old), "after": prior.metrics(report),
               "audit": counts, "resegmented_documents": changed}
        result["rounds"][r] = row
        lines.append(f"| {r} | {row['before']['bounded']}→{row['after']['bounded']} | "
                     f"{row['before']['review']}→{row['after']['review']} |")
        print(r, row["before"]["bounded"], row["after"]["bounded"], counts, flush=True)
    for r, row in result["rounds"].items():
        lines += ["", f"## {r}", "", f"감사: `{row['audit']}`", "",
                  "| 검토 사유 | 전 | 후 |", "|---|---:|---:|"]
        for reason in sorted(row["before"]["review_reasons"].keys()
                             | row["after"]["review_reasons"].keys()):
            lines.append(f"| {reason} | {row['before']['review_reasons'].get(reason, 0)} | "
                         f"{row['after']['review_reasons'].get(reason, 0)} |")
    result["access_violations"] = copy.deepcopy(VIOLATIONS)
    save_json(ROOT / f"docs/dev/{PREFIX}-comparison.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-comparison.md", "\n".join(lines) + "\n")
    review = holdout(reports)
    save_json(ROOT / f"docs/dev/{PREFIX}-review-sample.json", review)
    md = prior.sample_markdown(review).replace("S6d-2 독립", "S6d-2b 독립")
    md = md.replace(f"seed={prior.SEED}", f"seed={SEED}")
    md = md.replace(
        "## 1. 원문만", "이전 독립 표본 16칸을 제외한 모집단에서 새 시드로 뽑았다.\n\n## 1. 원문만",
    )
    write(ROOT / f"docs/dev/{PREFIX}-review-sample.md", md)
    if VIOLATIONS or any(v for row in result["rounds"].values() for v in row["audit"].values()):
        raise SystemExit("S6d-2b audit violations")


if __name__ == "__main__":
    main()
