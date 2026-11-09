"""Offline S6d-2e snapshots, development comparisons and fourth cell sample."""

from __future__ import annotations

import copy
import json
import re
import shutil
import sys
from pathlib import Path

import compare_middle_performance_items as prior
from audit_middle_items import audit, markdown
from compare_middle_s6d3b import field_audit
from middle_item_editions import select_editions
from middle_items import standard_values, title_gate
from middle_items import visible as source_visible
from middle_rounds import roster_path
from recheck_middle_s6d2b import normalize
from verify_middle_s6d2e import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "2026-11-09-s6d2e"
REVIEW_PREFIXES = ("2026-11-08-s6d2", "2026-11-08-s6d2b", "2026-11-09-s6d2c",
                   "2026-11-09-s6d2d")


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def representative_items(report, reader=None):
    reader = prior.read if reader is None else reader
    documents = copy.deepcopy(report["documents"])
    source = reader(f"data/derived/segments/{report['round']}.json")
    editions = {d["converted_path"]: d["edition"] for d in source["documents"]}
    for document in documents:
        document["edition"] = editions[document["converted_path"]]
    select_editions(documents)
    selected = {d["converted_path"] for d in documents if d["development_selected"]}
    return [i for i in prior.independent(report) if i["converted_path"] in selected]


def reviewer_rows(path):
    blocks = re.split(r"### (S\d+) ", path.read_text(encoding="utf-8"))
    result = {}
    for index in range(1, len(blocks), 2):
        rows = []
        for line in blocks[index + 1].splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if (not line.startswith("|") or len(cells) != 7 or cells[0] == "제목"
                    or cells[0].startswith(("---", "판독 불가"))):
                continue
            codes = standard_values([{"raw": cells[5], "text": cells[5],
                                      "locator": {"start": 0, "end": len(cells[5])}}])["value"]
            ranges = [(int(a), int(b)) for a, b in re.findall(
                r"(\d{2,})\s*[–—~〜∼-]\s*(\d{2,})", cells[6])]
            rows.append({"title": cells[0], "standards": codes, "source_lines": ranges,
                         "raw_cells": cells})
        result[blocks[index]] = rows
    return result


def compare_cell(rows, report, cell):
    items = [i for i in representative_items(report)
             if i["school"] == cell["school"] and i["grade"] == cell["grade"]
             and i["semester"] == cell["semester"] and i["extraction_status"] == "bounded"]
    cache = {}
    edges = []
    range_use = {span: sum(span in row["source_lines"] for row in rows)
                 for row in rows for span in row["source_lines"]}
    for ri, row in enumerate(rows):
        title = normalize(re.sub(r"〔.*?〕", "", row["title"]))
        for ii, item in enumerate(items):
            f = item["fields"]
            names = [f["title"]["value"], *f["title"].get("aliases", [])]
            exact = any(normalize(n) == title for n in names)
            codes = set(f["standards"]["value"])
            codes.update(c for o in f["standards"].get("source_observations", [])
                         for c in o["value"])
            path = item["converted_path"]
            if path not in cache:
                cache[path] = prior.read(path)["text"]
            text = cache[path]
            source_lines = text.splitlines()
            # Reviewer-specific detail ranges can name the literal summary
            # area even when its standards cell is genuinely shared. Common
            # overview ranges cannot establish this correspondence.
            unique_source = normalize(source_visible("\n".join(
                "\n".join(source_lines[lo - 1:hi]) for lo, hi in row["source_lines"]
                if range_use[lo, hi] == 1)))
            source_title = any(title_gate(n)["accepted"] and len(normalize(n)) >= 3
                               and normalize(n) in unique_source
                               for n in names if n)
            observations = [o for name in ("title", "task_text", "standards")
                            for o in f[name]["evidence"]]
            source_overlap = any(
                lo <= text.count("\n", 0, o["locator"]["start"]) + 1 <= hi
                for o in observations for lo, hi in row["source_lines"]
            )
            # Reviewer paraphrases require both source-line and code evidence.
            # No semantic title inference, school binding or code->grade map.
            if exact or source_title or source_overlap and codes & set(row["standards"]):
                score = int(exact) * 10 + int(source_title) * 5 + int(source_overlap)
                edges.append((score, ri, ii))
    chosen, used_rows, used_items = [], set(), set()
    for score, ri, ii in sorted(edges, reverse=True):
        if ri in used_rows or ii in used_items:
            continue
        used_rows.add(ri)
        used_items.add(ii)
        chosen.append({"reviewer": rows[ri], "item_id": items[ii]["item_id"],
                       "pipeline_title": items[ii]["fields"]["title"]["value"],
                       "basis": "normalized_title" if score >= 10 else
                       "literal_title_in_reviewer_specific_source" if score >= 5 else
                       "source_lines_and_codes"})
    return {"found": len(chosen), "missed": len(rows) - len(chosen),
            "wrong_or_duplicate": len(items) - len(chosen), "bounded": len(items),
            "matches": chosen, "missed_items": [r for n, r in enumerate(rows)
                                                if n not in used_rows],
            "unmatched_bounded": [prior.coordinate(i) for n, i in enumerate(items)
                                  if n not in used_items]}


def recheck(reports):
    result = {"metric_type": "개발 지표·대표 판본 하나", "cells": []}
    lines = ["# S6d-2e 개발 참고 64칸 재대조", "",
             "전후 모두 동일한 일반 판본 선택 규칙을 적용한다. astra의 요약 제목은 "
             "원문 줄과 성취기준 교집합, 또는 다른 과제와 겹치지 않는 원문 줄의 문자 그대로인 "
             "제목으로 대응한다. 공유 성취기준을 항목 확정값으로 사용하지 않는다. 대응 근거는 "
             "JSON에 구분했다. 미매칭 bounded는 잠정 잘못·중복이다. "
             "판독 불가 세 칸은 분모에서 제외한다.", "",
             "| 회차·칸 | astra | bounded 전→후 | 찾음 전→후 | 놓침 전→후 | 잘못·중복 전→후 |",
             "|---|---:|---:|---:|---:|---:|"]
    for prefix in REVIEW_PREFIXES:
        sample = prior.read(f"docs/dev/{prefix}-review-sample.json")
        reviewer = ROOT / ("docs/dev/2026-11-09-s6d2b-astra-review.md"
                           if prefix == "2026-11-08-s6d2b"
                           else f"docs/dev/{prefix}-astra-review.md")
        reviews = reviewer_rows(reviewer)
        for cell in sample["source_review"]:
            rows = reviews[cell["cell_id"]]
            entry = {"sample": prefix, "cell": cell, "reviewer_count": len(rows),
                     "unreadable": not rows}
            for phase in ("before", "after"):
                entry[phase] = compare_cell(rows, reports[phase][cell["round"]], cell)
            result["cells"].append(entry)
            a, b = entry["before"], entry["after"]
            lines.append(f"| {prefix} {cell['cell_id']} {cell['school']} "
                         f"중{cell['grade']} {cell['semester']}학기 | "
                         f"{len(rows) if rows else '판독 불가'} | " + " | ".join(
                             f"{a[k]}→{b[k]}" for k in
                             ("bounded", "found", "missed", "wrong_or_duplicate")) + " |")
    result["totals"] = {
        phase: {k: sum(c[phase][k] for c in result["cells"] if not c["unreadable"])
                for k in ("found", "missed", "wrong_or_duplicate", "bounded")}
        for phase in ("before", "after")
    }
    result["by_sample"] = {
        prefix: {phase: {k: sum(c[phase][k] for c in result["cells"]
                              if c["sample"] == prefix and not c["unreadable"])
                         for k in ("found", "missed", "wrong_or_duplicate", "bounded")}
                 for phase in ("before", "after")} for prefix in REVIEW_PREFIXES
    }
    lines += ["", "```json", json.dumps(result["totals"], ensure_ascii=False, indent=2), "```", ""]
    save(ROOT / f"docs/dev/{PREFIX}-recheck.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-recheck.md", "\n".join(lines))
    return result


def split_merges(before, after):
    """Count removed leaf candidates with source-cell continuity, not title guesses."""
    result = []
    for item in after["items"]:
        cols = item["boundary_evidence"].get("merged_columns", [])
        if len(cols) < 2:
            continue
        old = [i for i in before["items"]
               if i["converted_path"] == item["converted_path"]
               and (i["grade"], i["semester"]) == (item["grade"], item["semester"])
               and i["layout_position"]["table"] == item["layout_position"]["table"]
               and i["layout_position"].get("col") in cols]
        if len(old) > 1:
            result.append({"item_id": item["item_id"], "columns": cols,
                           "before_item_ids": [i["item_id"] for i in old],
                           "removed_split_candidates": len(old) - 1})
    return result


def sample(reports):
    excluded = {(c["round"], c["school"], c["grade"], c["semester"])
                for prefix in REVIEW_PREFIXES
                for c in prior.read(f"docs/dev/{prefix}-review-sample.json")["source_review"]}
    population = [(r, school, grade, term)
                  for r, term in zip(prior.ROUNDS[1:], (2, 1), strict=True)
                  for school in sorted({d["school"] for d in reports[r]["documents"]})
                  for grade in (1, 2) if (r, school, grade, term) not in excluded]
    chosen = sorted(population)
    sources, pipeline = [], []
    for n, (r, school, grade, term) in enumerate(chosen, 1):
        report = reports[r]
        cell_id = f"S{n:02}"
        sources.append({"cell_id": cell_id, "round": r, "school": school, "grade": grade,
                        "semester": term, "science_ranges": prior.source_ranges(
                            report, grade, term, school),
                        "source_documents": [{k: d.get(k) for k in
                                              ("document_id", "child_id", "original_path",
                                               "converted_path", "filename", "grades")}
                                             for d in report["documents"]
                                             if d["school"] == school and d["development_selected"]
                                             and (not d.get("grades") or grade in d["grades"])],
                        "unreadable_documents": [{k: d.get(k) for k in
                                                  ("original_path", "converted_path", "status",
                                                   "grades")}
                                                 for d in report["documents"]
                                                 if d["school"] == school
                                                 and d["development_selected"]
                                                 and d["status"] == "image_only"],
                        "reviewer_items": []})
        bounded = [i for i in representative_items(report) if i["school"] == school
                   and i["grade"] == grade and i["extraction_status"] == "bounded"]
        pipeline.append({"cell_id": cell_id,
                         "bounded_items": [prior.pipeline_item(i) for i in bounded
                                           if i["semester"] == term],
                         "semester_unresolved_bounded_items": [prior.pipeline_item(i)
                                                                for i in bounded
                                                                if i["semester"] is None]})
    return {"seed": None, "population_size": len(population), "sample_size": len(chosen),
            "excluded_cell_count": len(excluded), "sampling": "앞선 64칸 제외 잔여 전수·판본 하나",
            "source_review": sources, "pipeline_comparison": pipeline}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {"before": {}, "after": {}}
    result = {"rounds": {}}
    lines = ["# S6d-2e 전후 비교", "", "| 회차 | bounded 전→후 | 검토 전→후 | "
             "판본 제거 bounded | 요약·세부 묶음 전→후 | 합쳐진 쪼개짐 |",
             "|---|---:|---:|---:|---:|---:|"]
    for r in prior.ROUNDS:
        for ext in ("json", "md"):
            current = ROOT / f"data/derived/items/{r}.{ext}"
            previous = current.with_name(f"{r}.prev-s6d3c.{ext}")
            if not previous.exists():
                shutil.copyfile(current, previous)
        before = prior.read(f"data/derived/items/{r}.prev-s6d3c.json")
        after = audit(ROOT / f"data/derived/subjects/{r}.json", roster_path(ROOT, r, None))
        save(ROOT / f"data/derived/items/{r}.json", after)
        write(ROOT / f"data/derived/items/{r}.md", markdown(after))
        reports["before"][r], reports["after"][r] = before, after
        row = {"before": prior.metrics(before), "after": prior.metrics(after),
               "edition_history_bounded": sum(h["removed_bounded"]
                                             for h in after["edition_history"]),
               "edition_removed_documents": len(after["edition_history"]),
               "audit": prior.safety_counts(after) | prior.column_audit(after) | field_audit(after)}
        selected = {d["converted_path"] for d in after["documents"]
                    if d["development_selected"]}
        row["edition_removed_bounded"] = sum(
            i["extraction_status"] == "bounded" and i["converted_path"] not in selected
            for i in prior.independent(before)
        )
        result["rounds"][r] = row
        a, b = before["summary"]["summary_duplicates"], after["summary"]["summary_duplicates"]
        row["summary_links"] = {"before": a, "after": b}
        row["split_merges"] = split_merges(before, after)
        row["removed_split_candidates"] = sum(
            m["removed_split_candidates"] for m in row["split_merges"])
        lines.append(f"| {r} | {row['before']['bounded']}→{row['after']['bounded']} | "
                     f"{row['before']['review']}→{row['after']['review']} | "
                     f"{row['edition_removed_bounded']} | {a}→{b} | "
                     f"{row['removed_split_candidates']} |")
        print(r, row["before"]["bounded"], row["after"]["bounded"], row["audit"], flush=True)
    development = recheck(reports)
    holdout = sample(reports["after"])
    md = prior.sample_markdown(holdout).replace("S6d-2 독립", "S6d-2e 마지막 독립")
    heading = "## 1. 원문만 보고 독립 목록 작성"
    md = md.replace(heading, heading + "\n\n과학 구간 밖 평가표가 있을 수 있으므로 "
                    "문서 전체를 확인한다.", 1)
    md = md.replace(f"seed={prior.SEED}", "잔여 칸 전수")
    md = re.sub(r"모집단 \d+칸 중 16칸 단순무작위 추출\.",
                f"앞선 64칸을 뺀 잔여 {holdout['sample_size']}칸 전체.", md)
    md = md.replace("판본별 후보를 보존한다.",
                    "일반 판본 선택 규칙으로 선택한 대표 판본 하나만 싣는다.")
    md = re.sub(r", 경계 검증 (?:True|False)", "", md)
    for cell in holdout["source_review"]:
        cell["instruction"] = "과학 구간 밖 평가표가 있을 수 있으므로 문서 전체를 확인한다."
        marker = (f"### {cell['cell_id']} {cell['school']} "
                  f"중{cell['grade']} {cell['semester']}학기\n")
        documents = "\n문서 전체 확인 목록(범위 참고와 별개):\n\n" + "\n".join(
            f"- 원문 `{d['original_path']}` · 자식 `{d['filename']}` · 변환 `{d['converted_path']}`"
            for d in cell["source_documents"]) + "\n"
        md = md.replace(marker, marker + documents, 1)
        for source in cell["science_ranges"]:
            for key in ("boundary_verified", "document_status", "section_id"):
                source.pop(key, None)
    save(ROOT / f"docs/dev/{PREFIX}-review-sample.json", holdout)
    write(ROOT / f"docs/dev/{PREFIX}-review-sample.md", md)
    result.update(access_violations=VIOLATIONS, development_totals=development["totals"])
    save(ROOT / f"docs/dev/{PREFIX}-comparison.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-comparison.md", "\n".join(lines) + "\n")
    if VIOLATIONS or any(v for row in result["rounds"].values() for v in row["audit"].values()):
        raise SystemExit("S6d-2e audit violations")


if __name__ == "__main__":
    main()
