"""Replay only S6 on three cached development rounds; deterministic field holdout."""

from __future__ import annotations

import json
import random
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

from audit_middle_items import audit, markdown
from compare_middle_items import safety_counts
from compare_middle_performance_items import ROUNDS, column_audit, independent, metrics, read
from middle_items import FIELD_STATUSES, FIELDS, field_status
from middle_rounds import roster_path
from recheck_middle_s6d2b import cell_items, match, normalize, reviewer_rows
from verify_middle_s6d3 import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "2026-11-08-s6d3"
SEED = 202611083


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def save(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def states(items):
    result = {name: dict.fromkeys(FIELD_STATUSES, 0) for name in FIELDS}
    for item in items:
        for name in FIELDS:
            f = item["fields"].get(name)
            result[name][f.get("status", field_status(f)) if f else "unconfirmed"] += 1
    return result


def extra_audit(report):
    counts = dict.fromkeys(("자유학기 문맥 근거 추적 오류", "범위 코드 참조 밖 값",
                            "세부배점 근거 추적 오류", "성취기준 공통·충돌 값 오류"), 0)
    cache = {}
    for item in report["items"]:
        path = item["converted_path"]
        if path not in cache:
            cache[path] = read(path)["text"]
        text = cache[path]
        f = item["fields"]["free_semester"]
        scope = f["scope_locator"]
        for obs in f["reference_evidence"]:
            loc = obs["locator"]
            counts["자유학기 문맥 근거 추적 오류"] += (
                text[loc["start"]:loc["end"]] != obs["raw"]
                or not scope["start"] <= loc["start"] <= loc["end"] <= scope["end"]
            )
        standards = item["fields"]["standards"]
        if standards.get("confirmed_values") is not None:
            snapshots = standards["source_observations"]
            a, b = (set(s["value"]) for s in snapshots)
            counts["성취기준 공통·충돌 값 오류"] += (
                set(standards["value"]) != a & b
                or set(standards["conflict_values"]) != a ^ b
            )
        from middle_fields import reference_codes
        for occurrence in standards.get("occurrences", []):
            if occurrence["expansion_status"] == "reference_validated":
                counts["범위 코드 참조 밖 값"] += bool(
                    set(occurrence["expanded"]) - set(reference_codes()))
        for value in item["fields"]["sub_scores"]["value"]:
            for obs in value["evidence"]:
                loc = obs["locator"]
                counts["세부배점 근거 추적 오류"] += text[loc["start"]:loc["end"]] != obs["raw"]
    return counts


def source_entry(item):
    text = read(item["converted_path"])["text"]
    observations = [
        {"source_role": "detail" if item["layout"] == "form" else "summary",
         "item_id": item["item_id"], "locator": item["locator"]},
    ]
    seen = {(item["item_id"], item["locator"]["start"], item["locator"]["end"])}
    for f in item["fields"].values():
        for source in f.get("source_observations", []):
            for obs in source["evidence"]:
                key = (source["source_item_id"], obs["locator"]["start"], obs["locator"]["end"])
                if key not in seen:
                    seen.add(key)
                    observations.append({"source_role": source["source_role"],
                                         "item_id": source["source_item_id"],
                                         "locator": obs["locator"]})
    ranges = []
    for role in ("summary", "detail"):
        local = [o["locator"] for o in observations if o["source_role"] == role]
        if local:
            start, end = min(o["start"] for o in local), max(o["end"] for o in local)
            ranges.append({"source_role": role, "start": start, "end": end,
                           "line_start": text.count("\n", 0, start) + 1,
                           "line_end": text.count("\n", 0, max(start, end - 1)) + 1})
    return {k: item.get(k) for k in ("document_id", "child_id", "original_path",
                                     "converted_path", "grade", "semester")} | {
        "source_ranges": ranges,
    }


def sample(reports):
    population = sorted(
        [(r, i) for r in ROUNDS[1:] for i in independent(reports[r])
         if i["extraction_status"] == "bounded"],
        key=lambda pair: (pair[0], pair[1]["item_id"]),
    )
    chosen = random.Random(SEED).sample(population, 14)
    result = {"seed": SEED, "sampling": "보충 두 회차 독립 bounded 항목 단순무작위·비복원",
              "population_size": len(population), "sample_size": 14,
              "source_review": [], "pipeline_fields": []}
    for n, (r, item) in enumerate(chosen, 1):
        label = f"F{n:02}"
        result["source_review"].append({"sample_id": label, "round": r, **source_entry(item)})
        result["pipeline_fields"].append({"sample_id": label, "item_id": item["item_id"],
                                          "title_role": item["title_role"],
                                          "fields": item["fields"]})
    save(ROOT / f"docs/dev/{PREFIX}-field-sample.json", result)
    lines = ["# S6d-3 필드 독립 확인 표본", "",
             f"seed={SEED}, 모집단 {len(population)}항목, 14항목 비복원 무작위. "
             "1절을 먼저 검토하고 2절의 파이프라인 값과 대조한다.", "",
             "## 1. 원문 경로·위치만", ""]
    for entry in result["source_review"]:
        lines += [f"### {entry['sample_id']}", "",
                  f"- 문서: `{entry['original_path']}`",
                  f"- 변환: `{entry['converted_path']}`",
                  f"- 문서 구분: `{entry['document_id']}` / child `{entry['child_id']}`",
                  f"- 범위: 중{entry['grade']} {entry['semester']}학기"]
        for loc in entry["source_ranges"]:
            lines.append(f"- {loc['source_role']}: text {loc['line_start']}–{loc['line_end']}줄 "
                         f"/ 문자 [{loc['start']}, {loc['end']})")
        lines.append("")
    lines += ["## 2. 파이프라인 필드 값·상태·근거 전부", ""]
    for entry in result["pipeline_fields"]:
        lines += [f"### {entry['sample_id']}", "", "```json",
                  json.dumps(entry, ensure_ascii=False, indent=2), "```", ""]
    write(ROOT / f"docs/dev/{PREFIX}-field-sample.md", "\n".join(lines))
    return result


def expected_value(row, name):
    raw = row[name]
    if name in {"score", "weight"}:
        number = re.fullmatch(r"(\d+(?:\.\d+)?)\s*[점%]?", raw)
        return float(number[1]) if number else ""
    return row["standards"] if name == "standards" else raw


def recheck(reports):
    cells = read("docs/dev/2026-11-08-s6d2-review-sample.json")["source_review"]
    reviews = reviewer_rows()
    result = {"metric_type": "개발 16칸 값 일치·공식 정확도 아님", "cells": []}
    lines = ["# S6d-3 개발 참고 16칸 필드 일치", "",
             "동일 제목 정규화로 매칭된 bounded만 비교. 의미 대응을 자동 확정하지 않음. "
             "S09 판독 불가는 제외. 시기 ※는 진도표 참고이므로 목표에서 제외. "
             "성취기준의 ※/요약·세부 충돌 주석은 자동 정답 확정 없이 별도 표시. "
             "값 없음 일치는 source_absent와 unconfirmed를 구분해 표시한다.", "",
             "| 칸 | 항목 매칭 전→후 / astra | 만점 전→후 | 비율 전→후 | "
             "시기 전→후 | 성취기준 전→후 |",
             "|---|---:|---|---|---|---|"]
    for cell in cells:
        label = cell["cell_id"]
        rows = reviews[label]
        entry = {"cell_id": label, "reviewer_count": len(rows), "phases": {}}
        for phase in ("before", "after"):
            report = reports[phase][cell["round"]]
            items = cell_items(report, cell)
            matches = match(rows, items)
            by_id = {i["item_id"]: i for i in items}
            counts, details = {}, []
            for name in ("score", "weight", "timing", "standards"):
                counts[name] = Counter()
            for m in matches["matches"]:
                row = m["reviewer"]
                item = by_id.get(m.get("item_id"))
                detail = {"reviewer": row, "item_id": m.get("item_id"), "fields": {}}
                for name in counts:
                    f = item["fields"][name] if item else None
                    raw = row["standards_raw"] if name == "standards" else row[name]
                    if "※" in raw or (name == "standards" and "요약" in raw):
                        state = "reference_or_conflict_note"
                    elif f is None:
                        state = "item_unmatched"
                    elif expected_value(row, name) in ("", []):
                        state = ("empty_value_match_" + f["status"]
                                 if f["value"] in ("", []) else "different")
                    elif (set(f["value"]) == set(row["standards"]) if name == "standards"
                          else normalize(f["value"]) == normalize(expected_value(row, name))):
                        state = ("equal" if f["status"] == "present"
                                 else "value_equal_" + f["status"])
                    else:
                        state = "different"
                    counts[name][state] += 1
                    detail["fields"][name] = {"reviewer_raw": raw, "comparison": state,
                                               "pipeline": f}
                details.append(detail)
            entry["phases"][phase] = {"found": matches["found"], "counts": counts,
                                        "items": details}
        result["cells"].append(entry)
        a, b = (entry["phases"][p] for p in ("before", "after"))
        summaries = []
        for name in ("score", "weight", "timing", "standards"):
            summaries.append(f"{a['counts'][name].get('equal', 0)}→"
                             f"{b['counts'][name].get('equal', 0)} / {len(rows)}")
        denominator = len(rows) if rows else "판독불가"
        lines.append(f"| {label} | {a['found']}→{b['found']} / {denominator} | "
                     + " | ".join(summaries) + " |")
    result["totals"] = {
        phase: {name: dict(sum((c["phases"][phase]["counts"][name] for c in result["cells"]),
                              Counter())) for name in ("score", "weight", "timing", "standards")}
        for phase in ("before", "after")
    }
    lines += ["", "위 표는 present 확정값의 완전 일치 건수 / astra 항목 수. "
              "값 없음·참고 주석·미매칭은 아래 합계와 항목별 표에서 별도 확인한다.",
              "", "```json", json.dumps(result["totals"], ensure_ascii=False, indent=2), "```", ""]
    for cell in result["cells"]:
        lines += [f"## {cell['cell_id']}", "",
                  "| 전후 | astra 제목 | 필드 | astra 원문 값 | 파이프라인 값·상태 | 대조 |",
                  "|---|---|---|---|---|---|"]
        for phase, data in cell["phases"].items():
            for item in data["items"]:
                for name, f in item["fields"].items():
                    pipeline = f["pipeline"]
                    actual = (f"{pipeline['value']} ({pipeline['status']})" if pipeline
                              else "항목 미매칭")
                    line = (f"| {phase} | {item['reviewer']['title']} | {name} | "
                            f"{f['reviewer_raw']} | {actual} | {f['comparison']} |")
                    lines.append(line.replace("\n", " "))
        lines.append("")
    save(ROOT / f"docs/dev/{PREFIX}-field-recheck.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-field-recheck.md", "\n".join(lines))
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {"before": {}, "after": {}}
    result = {"rounds": {}}
    lines = ["# S6d-3 전후 비교", "", "중복 요약을 제외한 독립 항목 기준. "
             "새 필드는 이전 unconfirmed로 표시. "
             "P/A/U/C = present/source_absent/unconfirmed/conflict.",
             "", "| 회차 | bounded 전→후 | 검토 전→후 |", "|---|---:|---:|"]
    for r in ROUNDS:
        for ext in ("json", "md"):
            current = ROOT / f"data/derived/items/{r}.{ext}"
            previous = current.with_name(f"{r}.prev-s6d2b.{ext}")
            if not previous.exists():
                shutil.copyfile(current, previous)
        before = read(f"data/derived/items/{r}.prev-s6d2b.json")
        after = audit(ROOT / f"data/derived/subjects/{r}.json", roster_path(ROOT, r, None))
        save(ROOT / f"data/derived/items/{r}.json", after)
        write(ROOT / f"data/derived/items/{r}.md", markdown(after))
        reports["before"][r], reports["after"][r] = before, after
        row = {"before": metrics(before), "after": metrics(after),
               "audit": safety_counts(after) | column_audit(after) | extra_audit(after),
               "field_states": {}, "bounded_field_states": {}}
        for phase, report in (("before", before), ("after", after)):
            items = independent(report)
            row["field_states"][phase] = states(items)
            row["bounded_field_states"][phase] = states([
                i for i in items if i["extraction_status"] == "bounded"])
        result["rounds"][r] = row
        lines.append(f"| {r} | {row['before']['bounded']}→{row['after']['bounded']} | "
                     f"{row['before']['review']}→{row['after']['review']} |")
        print(r, row["before"]["bounded"], row["after"]["bounded"], row["audit"], flush=True)
    for r, row in result["rounds"].items():
        for key, label in (("field_states", "전체 독립 후보"), ("bounded_field_states", "bounded")):
            lines += ["", f"## {r} — {label}", "", "| 필드 | 전 P/A/U/C | 후 P/A/U/C |",
                      "|---|---|---|"]
            for name in FIELDS:
                a, b = (row[key][p][name] for p in ("before", "after"))
                lines.append(f"| {name} | " + "/".join(str(a[s]) for s in FIELD_STATUSES)
                             + " | " + "/".join(str(b[s]) for s in FIELD_STATUSES) + " |")
    holdout = sample(reports["after"])
    development = recheck(reports)
    result.update(access_violations=VIOLATIONS, sample_size=holdout["sample_size"],
                  development_totals=development["totals"])
    save(ROOT / f"docs/dev/{PREFIX}-comparison.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-comparison.md", "\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
