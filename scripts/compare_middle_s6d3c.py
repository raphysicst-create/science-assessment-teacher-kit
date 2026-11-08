"""Replay cached S6 inputs, preserve S6d-2c outputs and draw a fresh field sample."""

from __future__ import annotations

import json
import random
import re
import shutil
import sys
from pathlib import Path

from audit_middle_items import audit, markdown
from compare_middle_items import safety_counts
from compare_middle_performance_items import ROUNDS, column_audit, independent, metrics, read
from compare_middle_s6d3 import source_entry, states
from middle_identity import title_key
from middle_items import label_role, source_tables, standard_values, standards_table, teaching_table
from middle_rounds import roster_path
from verify_middle_s6d3c import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "2026-11-09-s6d3c"
SEED = 2026110961


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def save(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def field_audit(report):
    from middle_fields import reference_codes

    checks = dict.fromkeys(("policy_trace", "policy_scope", "outside_reference",
                            "sub_score_trace", "option_trace", "rubric_trace"), 0)
    cache = {}
    for item in report["items"]:
        path = item["converted_path"]
        if path not in cache:
            cache[path] = read(path)["text"]
        text = cache[path]
        fields = item["fields"]
        scope = fields["free_semester"]["scope_locator"]
        for obs in fields["free_semester"]["reference_evidence"]:
            loc = obs["locator"]
            checks["policy_trace"] += text[loc["start"]:loc["end"]] != obs["raw"]
            if obs["scope"] == "document_grade_policy":
                checks["policy_scope"] += (obs["grade"] != item["grade"]
                                           or obs["semester"] not in {None, item["semester"]}
                                           or loc["end"] > scope["start"])
            else:
                checks["policy_scope"] += not (
                    scope["start"] <= loc["start"] <= loc["end"] <= scope["end"]
                )
        checks["outside_reference"] += bool(set(fields["standards"]["value"])
                                            - set(reference_codes()))
        for key, observations in (
            ("sub_score_trace", [o for v in fields["sub_scores"]["value"] for o in v["evidence"]]),
            ("option_trace", fields["method"]["options"]),
            ("rubric_trace", fields["rubric"]["evidence"]),
        ):
            for obs in observations:
                loc = obs["locator"]
                checks[key] += text[loc["start"]:loc["end"]] != obs["raw"]
    return checks


def sample_population(reports):
    samples = [read(path) for path in (
        "docs/dev/2026-11-08-s6d3-field-sample.json",
        "docs/dev/2026-11-09-s6d3b-field-sample.json",
    )]
    excluded = {e["item_id"] for sample in samples for e in sample["pipeline_fields"]}
    old_ranges = [(entry["converted_path"], obs["locator"])
                  for sample in samples
                  for entry, values in zip(sample["source_review"], sample["pipeline_fields"],
                                           strict=True)
                  for name in ("title", "task_no")
                  for obs in values["fields"][name]["evidence"]]
    old_titles = [(entry, {title_key(o["text"])
                           for name in ("title", "assessment_area")
                           for o in values["fields"][name]["evidence"] if o["text"]})
                  for sample in samples
                  for entry, values in zip(sample["source_review"], sample["pipeline_fields"],
                                           strict=True)]
    population = []
    for round_key in ROUNDS[1:]:
        for item in independent(reports[round_key]):
            if item["extraction_status"] != "bounded" or item["item_id"] in excluded:
                continue
            keys = {title_key(item["fields"][name]["value"])
                    for name in ("title", "assessment_area")
                    if isinstance(item["fields"][name]["value"], str)
                    and item["fields"][name]["value"]}
            if any(all(item.get(k) == entry.get(k) for k in (
                "converted_path", "grade", "semester"
            )) and keys & previous for entry, previous in old_titles):
                continue
            observations = [o for name in ("title", "task_no")
                            for o in item["fields"][name]["evidence"]]
            observations += [o for name in ("title", "task_no")
                             for source in item["fields"][name].get("source_observations", [])
                             for o in source["evidence"]]
            if any(item["converted_path"] == path and any(
                a["locator"]["start"] < b["end"] and b["start"] < a["locator"]["end"]
                for a in observations
            ) for path, b in old_ranges):
                continue
            population.append((round_key, item))
    return sorted(population, key=lambda pair: (pair[0], pair[1]["item_id"]))


def raw_counterparts(item, role, text):
    """Locate actual source tables even when their item boundaries are unresolved.

    Candidate locations never establish a production identity or certify grade.
    All tied best tables are retained for the independent source reader.
    """
    keys = {title_key(item["fields"][name]["value"])
            for name in ("title", "assessment_area")
            if isinstance(item["fields"][name]["value"], str)
            and item["fields"][name]["value"]}
    codes = set(item["fields"]["standards"]["value"])
    candidates = []
    for table in source_tables(text):
        if teaching_table(table) or standards_table(table):
            continue
        if table["start"] <= item["locator"]["start"] < table["end"]:
            continue
        roles = {label_role(c["text"]) for c in table["cells"]}
        summary = "timing" in roles and not roles & {"rubric", "elements"}
        detail = bool(roles & {"rubric", "elements"}) and not summary
        if not (summary if role == "summary" else detail):
            continue
        values = [title_key(c["text"]) for c in table["cells"] if c["text"]]
        literal = any(len(k) >= 4 and (k in v or v in k and len(v) >= 4)
                      for k in keys for v in values)
        observations = [{"raw": c["raw"], "text": c["text"],
                         "locator": {"start": c["start"], "end": c["end"]}}
                        for c in table["cells"]]
        local_codes = set(standard_values(observations)["value"])
        overlap = bool(codes & local_codes)
        if codes and local_codes and not overlap:
            continue
        if literal or overlap:
            score = 4 * literal + 3 * bool(codes and codes == local_codes) + overlap
            candidates.append((score, table))
    if not candidates:
        return []
    best = max(score for score, _ in candidates)
    return [{"source_role": role, "start": t["start"], "end": t["end"],
             "line_start": text.count("\n", 0, t["start"]) + 1,
             "line_end": text.count("\n", 0, t["end"] - 1) + 1,
             "range_kind": "raw_table_candidate_scope_unconfirmed"}
            for score, t in candidates if score == best]


def sample(reports):
    population = sample_population(reports)
    chosen = random.Random(SEED).sample(population, 14)
    result = {"seed": SEED, "population_size": len(population), "sample_size": 14,
              "sampling": "보충 독립 bounded 항목·기존 14항목과 연결 원문 범위 제외·비복원 무작위",
              "source_review": [], "pipeline_fields": []}
    lines = ["# S6d-3c 새 필드 독립 표본", "",
             f"seed {SEED}, 모집단 {len(population)}항목에서 14개 비복원 무작위 추출.", "",
             "1절은 원문 위치만 담았다. 연결 미확정 쪽은 실제 표의 문자 범위를 후보로 "
             "표시했다. 후보의 학년·학기·과제 동일성은 독립 확인이 필요하다. "
             "별도 요약표를 찾지 못한 항목은 평가계획 개요 범위와 그 사실을 표시했다.", "",
             "## 1. 원문 위치만", ""]
    for number, (round_key, item) in enumerate(chosen, 1):
        label = f"C{number:02}"
        entry = {"sample_id": label, "round": round_key, **source_entry(item)}
        text = read(item["converted_path"])["text"]
        for role in ("summary", "detail"):
            if any(loc["source_role"] == role for loc in entry["source_ranges"]):
                continue
            scope = item["boundary_evidence"]["section_locator"]
            candidates = [i for i in reports[round_key]["items"]
                          if i["converted_path"] == item["converted_path"]
                          and i["grade"] == item["grade"]
                          and i["semester"] == item["semester"]
                          and (i.get("table_role") == "summary" if role == "summary"
                               else i["layout"] == "form")]
            key = title_key(item["fields"]["title"]["value"])
            exact = [i for i in candidates if key and key == title_key(
                i["fields"]["title"]["value"])]
            candidates = exact or candidates
            raw_ranges = raw_counterparts(item, role, text)
            if raw_ranges and not exact:
                entry["source_ranges"].extend(raw_ranges)
                continue
            locators = {(i["locator"]["start"], i["locator"]["end"])
                        for i in candidates}
            missing_kind = "same_grade_semester_lookup_scope"
            if not locators and role == "summary":
                headings = list(re.finditer(
                    r"(?m)^[^<\r\n]*(?:평가\s*계획|평가의\s*영역)[^\r\n]*$",
                    text[:item["locator"]["start"]],
                ))
                if headings:
                    begin = headings[-1].start()
                    stop = text.find("<table", headings[-1].end())
                    locators = {(begin, stop if stop > begin else headings[-1].end())}
                    missing_kind = "summary_table_not_identified_assessment_overview"
            locators = locators or {(scope["start"], scope["end"])}
            for start, end in sorted(locators):
                entry["source_ranges"].append({
                    "source_role": role, "start": start, "end": end,
                    "line_start": text.count("\n", 0, start) + 1,
                    "line_end": text.count("\n", 0, max(start, end - 1)) + 1,
                    "range_kind": ("literal_title_candidate" if exact else "scoped_table_candidate"
                                   if candidates else missing_kind),
                })
        result["source_review"].append(entry)
        result["pipeline_fields"].append({
            "sample_id": label, "item_id": item["item_id"],
            "title_role": item["title_role"], "fields": item["fields"],
        })
        lines += [f"### {label}", "", f"- 원문 `{entry['original_path']}`",
                  f"- 변환 `{entry['converted_path']}`",
                  f"- 문서 `{entry['document_id']}` / child `{entry['child_id']}`",
                  f"- 중{entry['grade']} {entry['semester']}학기"]
        for loc in entry["source_ranges"]:
            kind = f" · 연결 미확정 {loc['range_kind']}" if loc.get("range_kind") else ""
            lines.append(f"- {loc['source_role']}{kind} 문자 [{loc['start']}, {loc['end']}) · "
                         f"{loc['line_start']}–{loc['line_end']}줄")
        lines.append("")
    lines += ["## 2. 파이프라인 값", ""]
    for entry in result["pipeline_fields"]:
        lines += [f"### {entry['sample_id']}", "", "```json",
                  json.dumps(entry, ensure_ascii=False, indent=2), "```", ""]
    save(ROOT / f"docs/dev/{PREFIX}-field-sample.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-field-sample.md", "\n".join(lines))
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {}
    result = {"rounds": {}}
    lines = ["# S6d-3c 필드 상태 전후", "",
             "독립 bounded 항목만 집계. 상태 순서는 "
             "present / source_absent / unconfirmed / conflict.",
             "", "| 회차 | bounded 전→후 | 검토 전→후 |", "|---|---:|---:|"]
    for round_key in ROUNDS:
        for extension in ("json", "md"):
            current = ROOT / f"data/derived/items/{round_key}.{extension}"
            previous = current.with_name(f"{round_key}.prev-s6d2d.{extension}")
            if not previous.exists():
                shutil.copyfile(current, previous)
        before = read(f"data/derived/items/{round_key}.prev-s6d2d.json")
        after = audit(ROOT / f"data/derived/subjects/{round_key}.json",
                      roster_path(ROOT, round_key, None))
        save(ROOT / f"data/derived/items/{round_key}.json", after)
        write(ROOT / f"data/derived/items/{round_key}.md", markdown(after))
        reports[round_key] = after
        row = {"before": metrics(before), "after": metrics(after),
               "audit": safety_counts(after) | column_audit(after) | field_audit(after),
               "field_states": {phase: states([i for i in independent(report)
                                               if i["extraction_status"] == "bounded"])
                                for phase, report in (("before", before), ("after", after))}}
        result["rounds"][round_key] = row
        lines.append(f"| {round_key} | {row['before']['bounded']}→{row['after']['bounded']} | "
                     f"{row['before']['review']}→{row['after']['review']} |")
        print(round_key, row["before"]["bounded"], row["after"]["bounded"],
              row["audit"], flush=True)
    for round_key, row in result["rounds"].items():
        lines += ["", f"## {round_key}", "", "| 필드 | 전 | 후 |", "|---|---|---|"]
        for name in row["field_states"]["before"]:
            lines.append(f"| {name} | " + " | ".join(
                " / ".join(str(v) for v in row["field_states"][phase][name].values())
                for phase in ("before", "after")) + " |")
    holdout = sample(reports)
    result.update(access_violations=VIOLATIONS, sample_population=holdout["population_size"])
    save(ROOT / f"docs/dev/{PREFIX}-comparison.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-comparison.md", "\n".join(lines) + "\n")
    if VIOLATIONS or any(v for row in result["rounds"].values() for v in row["audit"].values()):
        raise SystemExit("S6d-3c audit violations")


if __name__ == "__main__":
    main()
