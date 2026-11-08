"""Compare all three opened development field samples against saved Astra values."""

from __future__ import annotations

import re
import sys
from collections import Counter

from compare_middle_performance_items import ROUNDS, read
from compare_middle_s6d3d import PREFIX, ROOT, save, write
from recheck_middle_s6d3c import (
    EXCLUDED,
    FIELDS,
    item_for_sample,
    judge,
    method_key,
    methods,
    reviewer_rows,
)
from verify_middle_s6d3d import VIOLATIONS, guard

# Development-only semantic coverage review. These notes never enter extraction.
PARTIAL = {
    "before": {"A02": "모둠 실험 결과 보고서 작성 단계 누락",
               "A10": "뒤쪽 두 활동 누락", "B01": "잠긴 부피·부력 관계 설명 누락",
               "B13": "개념·실생활 사례 연결 누락", "C10": "태도·실천도 설명 누락"},
    "after": {"A02": "모둠 실험 결과 보고서 작성 단계 누락",
              "A10": "뒤쪽 두 활동 누락"},
}
EXCLUSIONS = EXCLUDED | {"C01": "공유 요약 범위의 네 과제 중 단일 대상 불명",
                         "C14": "Astra가 표본의 탐구 보고서와 다른 과학 논술을 판독"}


def resolve_item(report, source, sampled):
    item, basis = item_for_sample(report, sampled)
    if item:
        return item, basis
    starts = {o["locator"]["start"] for name in ("title", "assessment_area")
              for o in sampled["fields"][name]["evidence"]}
    candidates = []
    for item in report["items"]:
        if any(item.get(k) != source.get(k) for k in ("converted_path", "grade", "semester")):
            continue
        observations = [o for name in ("title", "assessment_area")
                        for o in item["fields"][name]["evidence"]]
        observations += [o for name in ("title", "assessment_area")
                         for value in item["fields"][name].get("source_observations", [])
                         for o in value["evidence"]]
        if starts & {o["locator"]["start"] for o in observations}:
            candidates.append(item)
    by_id = {i["item_id"]: i for i in report["items"]}
    targets = {i.get("identity_relation", {}).get("detail_item_id", i["item_id"])
               if i["candidate_role"] == "summary_duplicate" else i["item_id"] for i in candidates}
    if len(targets) == 1:
        return by_id[targets.pop()], "same_scope_literal_title_offset"
    return None, "source_correspondence_unconfirmed"


def judgments(case_id, phase, expected, fields):
    result = {name: judge("", name, expected[label], fields.get(name))
              for name, label in FIELDS.items()}
    if case_id in PARTIAL[phase] and result["task_text"] == "맞음":
        result["task_text"] = "틀림"
    method = fields.get("method", {})
    if method.get("status") == "present":
        raw = expected["방법"]["value"]
        actual = {method_key(v).replace("실헙실험", "실험") for v in method["value"]} - {"기타"}

        def tokens(value):
            found = methods(value)
            found.update(method_key(v) for v in re.findall(r"서술형|단답형|탐구보고서", value))
            if "탐구보고서" in found:
                found.discard("보고서")
            return found

        required = tokens(raw.split("세부 체크:")[-1].split("—")[0])
        permitted = tokens(raw.split("—")[0])
        if "불명" in raw:
            actual -= {"교사", "개별수행"}
        result["method"] = "맞음" if required <= actual <= permitted else "틀림"
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {phase: {r: read(f"data/derived/items/{r}{suffix}.json") for r in ROUNDS}
               for phase, suffix in (("before", ".prev-s6d2f"), ("after", ""))}
    cases = []
    for prefix, sample_prefix, reference_prefix in (
        ("A", "2026-11-08-s6d3", "2026-11-09-s6d3"),
        ("B", "2026-11-09-s6d3b", "2026-11-09-s6d3b"),
        ("C", "2026-11-09-s6d3c", "2026-11-09-s6d3c"),
    ):
        sample = read(f"docs/dev/{sample_prefix}-field-sample.json")
        expected = reviewer_rows(f"docs/dev/{reference_prefix}-astra-field.md")
        for n, (source, sampled) in enumerate(zip(
            sample["source_review"], sample["pipeline_fields"], strict=True
        ), 1):
            case_id = f"{prefix}{n:02}"
            row = {"sample_id": case_id, "source": source,
                   "reference": f"docs/dev/{reference_prefix}-astra-field.md",
                   "expected": expected[f"F{n:02}"],
                   "excluded_reason": EXCLUSIONS.get(case_id)}
            for phase in reports:
                item, basis = resolve_item(reports[phase][source["round"]], source, sampled)
                fields = item["fields"] if item else {}
                checked = dict.fromkeys(FIELDS, "제외") if case_id in EXCLUSIONS else judgments(
                    case_id, phase, row["expected"], fields)
                row[phase] = {"item_id": item["item_id"] if item else None, "match_basis": basis,
                              "fields": fields,
                              "coverage_note": PARTIAL[phase].get(case_id),
                              "judgments": checked}
            cases.append(row)
    totals = {phase: {name: dict(Counter(c[phase]["judgments"][name] for c in cases))
                      for name in FIELDS} for phase in reports}
    regressions = [{"sample_id": c["sample_id"], "field": name,
                    "before": c["before"]["judgments"][name],
                    "after": c["after"]["judgments"][name]}
                   for c in cases for name in FIELDS
                   if c["before"]["judgments"][name] == "맞음"
                   and c["after"]["judgments"][name] != "맞음"]
    result = {"case_count": len(cases), "comparable_count": len(cases) - len(EXCLUSIONS),
              "baseline": "S6d-2f", "totals": totals, "cases": cases,
              "regressions": regressions, "access_violations": VIOLATIONS}
    save(ROOT / f"docs/dev/{PREFIX}-field-recheck.json", result)
    lines = ["# S6d-3d 개발 42항목 재대조", "",
             "첫·둘째·셋째 14개 표본을 A/B/C로 구분했다. 42건을 모두 기록하고 기존 "
             "범위 불명 6건을 제외한 36건을 집계했다. 세부 배점은 저장된 Astra의 점수 목록과 "
             "비교하며 요소명·설명 활동 포괄은 별도 수동 대조했다. 원문 부재는 source_absent "
             "근거가 있어야 맞음이다. 부분 누락은 틀림이다. "
             "과거 독립 확인의 분모·시점과 다르다.", "",
             "| 필드 | 맞음 전→후 | 누락 전→후 | 틀림 전→후 | 제외 |",
             "|---|---:|---:|---:|---:|"]
    for name, label in FIELDS.items():
        cells = [f"{totals['before'][name].get(k, 0)}→{totals['after'][name].get(k, 0)}"
                 for k in ("맞음", "누락", "틀림")]
        lines.append(f"| {label} | " + " | ".join(cells) + " | 6 |")
    for c in cases:
        lines += ["", f"## {c['sample_id']}", "", c["excluded_reason"] or "원문 값 대조.", "",
                  "| 필드 | Astra 값 | 근거 줄 | 전 | 후 |", "|---|---|---|---|---|"]
        for name, label in FIELDS.items():
            e = c["expected"][label]
            lines.append(f"| {label} | {e['value']} | {e['source_lines']} | "
                         f"{c['before']['judgments'][name]} | {c['after']['judgments'][name]} |")
        lines += ["", f"활동 포괄 전 {c['before']['coverage_note'] or '추가 누락 확인 없음'} / "
                  f"후 {c['after']['coverage_note'] or '추가 누락 확인 없음'}."]
    write(ROOT / f"docs/dev/{PREFIX}-field-recheck.md", "\n".join(lines) + "\n")
    print(totals)
    print("regressions", regressions)


if __name__ == "__main__":
    main()
