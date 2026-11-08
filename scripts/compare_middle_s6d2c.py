"""Offline S6d-2c snapshots, development comparisons and third cell sample."""

from __future__ import annotations

import copy
import json
import random
import re
import shutil
import sys
from pathlib import Path

import compare_middle_performance_items as prior
from audit_middle_items import audit, markdown
from compare_middle_s6d3 import extra_audit
from middle_item_editions import select_editions
from middle_items import standard_values
from middle_rounds import roster_path
from recheck_middle_s6d2b import normalize
from verify_middle_s6d2c import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "2026-11-09-s6d2c"
SEED = 2026110927
REVIEW_PREFIXES = ("2026-11-08-s6d2", "2026-11-08-s6d2b")


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def representative_items(report):
    documents = copy.deepcopy(report["documents"])
    source = prior.read(f"data/derived/segments/{report['round']}.json")
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
            observations = [o for name in ("title", "task_text", "standards")
                            for o in f[name]["evidence"]]
            source_overlap = any(
                lo <= text.count("\n", 0, o["locator"]["start"]) + 1 <= hi
                for o in observations for lo, hi in row["source_lines"]
            )
            # Reviewer paraphrases require both source-line and code evidence.
            # No semantic title inference, school binding or code->grade map.
            if exact or source_overlap and codes & set(row["standards"]):
                edges.append((int(exact) * 10 + int(source_overlap), ri, ii))
    chosen, used_rows, used_items = [], set(), set()
    for score, ri, ii in sorted(edges, reverse=True):
        if ri in used_rows or ii in used_items:
            continue
        used_rows.add(ri)
        used_items.add(ii)
        chosen.append({"reviewer": rows[ri], "item_id": items[ii]["item_id"],
                       "pipeline_title": items[ii]["fields"]["title"]["value"],
                       "basis": "normalized_title" if score >= 10 else "source_lines_and_codes"})
    return {"found": len(chosen), "missed": len(rows) - len(chosen),
            "wrong_or_duplicate": len(items) - len(chosen), "bounded": len(items),
            "matches": chosen, "missed_items": [r for n, r in enumerate(rows)
                                                if n not in used_rows],
            "unmatched_bounded": [prior.coordinate(i) for n, i in enumerate(items)
                                  if n not in used_items]}


def recheck(reports):
    result = {"metric_type": "개발 지표·대표 판본 하나", "cells": []}
    lines = ["# S6d-2c 개발 참고 32칸 재대조", "",
             "전후 모두 동일한 일반 판본 선택 규칙을 적용한다. astra의 요약 제목은 "
             "원문 줄과 성취기준 교집합이 함께 맞을 때 대응한다. 제목 정규화 일치와 "
             "원문 근거 대응을 JSON에 구분했다. 미매칭 bounded는 잠정 잘못·중복이다. "
             "판독 불가 두 칸은 분모에서 제외한다.", "",
             "| 회차·칸 | astra | bounded 전→후 | 찾음 전→후 | 놓침 전→후 | 잘못·중복 전→후 |",
             "|---|---:|---:|---:|---:|---:|"]
    for prefix in REVIEW_PREFIXES:
        sample = prior.read(f"docs/dev/{prefix}-review-sample.json")
        reviewer = ROOT / (f"docs/dev/{prefix}-astra-review.md" if prefix == REVIEW_PREFIXES[0]
                           else "docs/dev/2026-11-09-s6d2b-astra-review.md")
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


def sample(reports):
    excluded = {(c["round"], c["school"], c["grade"], c["semester"])
                for prefix in REVIEW_PREFIXES
                for c in prior.read(f"docs/dev/{prefix}-review-sample.json")["source_review"]}
    population = [(r, school, grade, term)
                  for r, term in zip(prior.ROUNDS[1:], (2, 1), strict=True)
                  for school in sorted({d["school"] for d in reports[r]["documents"]})
                  for grade in (1, 2) if (r, school, grade, term) not in excluded]
    chosen = random.Random(SEED).sample(population, 16)
    sources, pipeline = [], []
    for n, (r, school, grade, term) in enumerate(chosen, 1):
        report = reports[r]
        cell_id = f"S{n:02}"
        sources.append({"cell_id": cell_id, "round": r, "school": school, "grade": grade,
                        "semester": term, "science_ranges": prior.source_ranges(
                            report, grade, term, school),
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
    return {"seed": SEED, "population_size": len(population), "sample_size": 16,
            "excluded_cell_count": len(excluded), "sampling": "잔여 칸 단순무작위·판본 하나",
            "source_review": sources, "pipeline_comparison": pipeline}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {"before": {}, "after": {}}
    result = {"rounds": {}}
    lines = ["# S6d-2c 전후 비교", "", "| 회차 | bounded 전→후 | 검토 전→후 | "
             "판본 제거 bounded | 요약·세부 묶음 전→후 |", "|---|---:|---:|---:|---:|"]
    for r in prior.ROUNDS:
        for ext in ("json", "md"):
            current = ROOT / f"data/derived/items/{r}.{ext}"
            previous = current.with_name(f"{r}.prev-s6d3.{ext}")
            if not previous.exists():
                shutil.copyfile(current, previous)
        before = prior.read(f"data/derived/items/{r}.prev-s6d3.json")
        after = audit(ROOT / f"data/derived/subjects/{r}.json", roster_path(ROOT, r, None))
        save(ROOT / f"data/derived/items/{r}.json", after)
        write(ROOT / f"data/derived/items/{r}.md", markdown(after))
        reports["before"][r], reports["after"][r] = before, after
        row = {"before": prior.metrics(before), "after": prior.metrics(after),
               "edition_history_bounded": sum(h["removed_bounded"]
                                             for h in after["edition_history"]),
               "edition_removed_documents": len(after["edition_history"]),
               "audit": prior.safety_counts(after) | prior.column_audit(after) | extra_audit(after)}
        selected = {d["converted_path"] for d in after["documents"]
                    if d["development_selected"]}
        row["edition_removed_bounded"] = sum(
            i["extraction_status"] == "bounded" and i["converted_path"] not in selected
            for i in prior.independent(before)
        )
        result["rounds"][r] = row
        a, b = before["summary"]["summary_duplicates"], after["summary"]["summary_duplicates"]
        row["summary_links"] = {"before": a, "after": b}
        lines.append(f"| {r} | {row['before']['bounded']}→{row['after']['bounded']} | "
                     f"{row['before']['review']}→{row['after']['review']} | "
                     f"{row['edition_removed_bounded']} | {a}→{b} |")
        print(r, row["before"]["bounded"], row["after"]["bounded"], row["audit"], flush=True)
    development = recheck(reports)
    holdout = sample(reports["after"])
    md = prior.sample_markdown(holdout).replace("S6d-2 독립", "S6d-2c 세 번째 독립")
    md = md.replace(f"seed={prior.SEED}", f"seed={SEED}")
    md = md.replace("판본별 후보를 보존한다.",
                    "일반 판본 선택 규칙으로 선택한 대표 판본 하나만 싣는다.")
    md = re.sub(r", 경계 검증 (?:True|False)", "", md)
    for cell in holdout["source_review"]:
        for source in cell["science_ranges"]:
            for key in ("boundary_verified", "document_status", "section_id"):
                source.pop(key, None)
    save(ROOT / f"docs/dev/{PREFIX}-review-sample.json", holdout)
    write(ROOT / f"docs/dev/{PREFIX}-review-sample.md", md)
    result.update(access_violations=VIOLATIONS, development_totals=development["totals"])
    save(ROOT / f"docs/dev/{PREFIX}-comparison.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-comparison.md", "\n".join(lines) + "\n")
    if VIOLATIONS or any(v for row in result["rounds"].values() for v in row["audit"].values()):
        raise SystemExit("S6d-2c audit violations")


if __name__ == "__main__":
    main()
