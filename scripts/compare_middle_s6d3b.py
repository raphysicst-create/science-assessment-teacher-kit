"""Replay cached S6 inputs, preserve S6d-2c outputs and draw a fresh field sample."""

from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

from audit_middle_items import audit, markdown
from compare_middle_items import safety_counts
from compare_middle_performance_items import ROUNDS, column_audit, independent, metrics, read
from compare_middle_s6d3 import source_entry, states
from middle_identity import title_key
from middle_rounds import roster_path
from verify_middle_s6d3b import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "2026-11-09-s6d3b"
SEED = 2026110933


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
    previous = read("docs/dev/2026-11-08-s6d3-field-sample.json")
    excluded = {entry["item_id"] for entry in previous["pipeline_fields"]}
    # Exclude an old item's linked summary/detail identity as well as its ID.
    old_ranges = [(entry["converted_path"], obs["locator"])
                  for entry, values in zip(previous["source_review"], previous["pipeline_fields"],
                                           strict=True)
                  for name in ("title", "task_no")
                  for obs in values["fields"][name]["evidence"]]
    population = []
    for round_key in ROUNDS[1:]:
        for item in independent(reports[round_key]):
            if item["extraction_status"] != "bounded" or item["item_id"] in excluded:
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


def sample(reports):
    population = sample_population(reports)
    chosen = random.Random(SEED).sample(population, 14)
    result = {"seed": SEED, "population_size": len(population), "sample_size": 14,
              "sampling": "보충 독립 bounded 항목·기존 14항목과 연결 원문 범위 제외·비복원 무작위",
              "source_review": [], "pipeline_fields": []}
    lines = ["# S6d-3b 새 필드 독립 표본", "",
             f"seed {SEED}, 모집단 {len(population)}항목에서 14개 비복원 무작위 추출.", "",
             "1절은 원문 위치만 담았다. 연결 미확정 쪽은 같은 문서 구간의 표·열 후보 "
             "범위를 별도로 명시했다. 후보가 없으면 학년·학기 구간을 표시했다.", "",
             "## 1. 원문 위치만", ""]
    for number, (round_key, item) in enumerate(chosen, 1):
        label = f"B{number:02}"
        entry = {"sample_id": label, "round": round_key, **source_entry(item)}
        text = read(item["converted_path"])["text"]
        for role in ("summary", "detail"):
            if any(loc["source_role"] == role for loc in entry["source_ranges"]):
                continue
            scope = item["boundary_evidence"]["section_locator"]
            candidates = [i for i in reports[round_key]["items"]
                          if i["converted_path"] == item["converted_path"]
                          and scope["start"] <= i["locator"]["start"] < scope["end"]
                          and (i.get("table_role") == "summary" if role == "summary"
                               else i["layout"] == "form")]
            key = title_key(item["fields"]["title"]["value"])
            exact = [i for i in candidates if key and key == title_key(
                i["fields"]["title"]["value"])]
            candidates = exact or candidates
            locators = {(i["locator"]["start"], i["locator"]["end"])
                        for i in candidates} or {(scope["start"], scope["end"])}
            for start, end in sorted(locators):
                entry["source_ranges"].append({
                    "source_role": role, "start": start, "end": end,
                    "line_start": text.count("\n", 0, start) + 1,
                    "line_end": text.count("\n", 0, max(start, end - 1)) + 1,
                    "range_kind": ("literal_title_candidate" if exact else "scoped_table_candidate"
                                   if candidates else "same_grade_semester_lookup_scope"),
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
    lines = ["# S6d-3b 필드 상태 전후", "",
             "독립 bounded 항목만 집계. 상태 순서는 "
             "present / source_absent / unconfirmed / conflict.",
             "", "| 회차 | bounded 전→후 | 검토 전→후 |", "|---|---:|---:|"]
    for round_key in ROUNDS:
        for extension in ("json", "md"):
            current = ROOT / f"data/derived/items/{round_key}.{extension}"
            previous = current.with_name(f"{round_key}.prev-s6d2c.{extension}")
            if not previous.exists():
                shutil.copyfile(current, previous)
        before = read(f"data/derived/items/{round_key}.prev-s6d2c.json")
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
        raise SystemExit("S6d-3b audit violations")


if __name__ == "__main__":
    main()
