"""Development-only comparison of the two previously opened field samples."""

from __future__ import annotations

import re
import sys
from collections import Counter

from compare_middle_performance_items import ROUNDS, read
from compare_middle_s6d3c import PREFIX, ROOT, save, write
from middle_items import standard_values
from verify_middle_s6d3c import VIOLATIONS, guard

FIELDS = {"title": "제목", "timing": "시기", "standards": "성취기준", "score": "만점",
          "weight": "비율", "method": "방법", "task_text": "과제 설명",
          "sub_scores": "세부 배점", "rubric": "채점기준(있음·없음)", "free_semester": "자유학기"}
# These are manual development judgments about coverage of the reviewer prose.
# They never enter extraction or item identity. Partial coverage counts as wrong.
PARTIAL_DESCRIPTIONS = {
    "A02": "모둠 실험 결과 보고서 작성 단계가 빠짐",
    "A10": "뒤쪽 SDGs·개념지 활동이 빠짐",
    "B01": "탐구보고서의 잠긴 부피·부력 관계 설명이 빠짐",
    "B13": "원소의 개념 서술·실생활 사용 예시 연결 활동이 빠짐",
}
EXCLUDED = {"A07": "두 과제를 덮는 요약 열·단일 대상 불명",
            "B07": "A07과 같은 다과제 요약 열·단일 대상 불명",
            "A13": "중3 일반 단원별 성취기준표·수행 과제 아님",
            "A14": "요청 학년과 원문 학년 충돌·대표 외 판본·필드 전용 금지"}


def reviewer_rows(path):
    blocks = re.split(r"### (F\d+) ", (ROOT / path).read_text(encoding="utf-8"))
    result = {}
    for index in range(1, len(blocks), 2):
        rows = {}
        for line in blocks[index + 1].splitlines():
            cells = [v.strip() for v in line.strip("|").split("|")]
            if line.startswith("|") and len(cells) == 3 and cells[0] in FIELDS.values():
                rows[cells[0]] = {"value": cells[1], "source_lines": cells[2]}
        result[blocks[index]] = rows
    return result


def item_for_sample(report, sampled):
    by_id = {i["item_id"]: i for i in report["items"]}
    item = by_id.get(sampled["item_id"])
    if item and item["candidate_role"] == "summary_duplicate":
        return by_id[item["identity_relation"]["detail_item_id"]], "linked_detail"
    return item, "same_source_item_id" if item else "no_corresponding_item"


def key(value):
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", str(value))


def method_key(value):
    value = key(value)
    value = re.sub(r"(?:형)?평가$|형$", "", value)
    value = value.replace("서술논술", "서논술").replace("토론토의", "토의토론")
    return value


def methods(raw):
    # Named methods, evaluator and organization are checked independently.
    terms = re.findall(
        r"서[·ㆍ]?논술형?|서술[·ㆍ]?논술형?|논술형|실험[·ㆍ]실습|구술[·ㆍ]발표|"
        r"토[론의][·ㆍ]토[의론]|교사\s*관찰\s*및\s*기록|프로젝트|포트폴리오|"
        r"보고서|관찰|교사평가|동료평가|자기평가|개별수행", raw,
    )
    return {method_key(v) for v in terms}


def judge(case_id, name, expected, field):
    raw = expected["value"]
    absent = raw.startswith("없음") and name in {"score", "weight", "sub_scores"}
    if absent:
        return ("맞음" if field and field["status"] == "source_absent" else
                "틀림" if field and field["value"] not in ("", [], None) else "누락")
    if not field or field["value"] in ("", [], None):
        return "누락"
    value = field["value"]
    if name != "title" and field["status"] != "present":
        return "누락"
    if name == "title":
        raw = re.sub(r"〔.*?〕|\(특성화영역\)", "", raw)
        value = re.sub(r"\(특성화영역\)", "", value)
        value = re.sub(r"^탐구\s*활동\((.*)\)$", r"\1", value)
        equal = key(raw) == key(value)
    elif name == "timing":
        actual = re.split(r"/|\(\s*\d+회\s*\)", value)[0]
        equal = key(actual) == key(raw)
    elif name == "standards":
        parsed = standard_values([{"raw": raw, "text": raw,
                                   "locator": {"start": 0, "end": len(raw)}}])
        equal = set(value) == set(parsed["value"])
    elif name in {"score", "weight"}:
        number = re.match(r"(\d+(?:\.\d+)?)", raw)
        equal = bool(number and value == float(number[1]))
    elif name == "method":
        actual = {method_key(v) for v in value} - {"기타"}
        expected_methods = methods(raw)
        # A03's reviewer left converted checkmarks uncertain. The previously
        # documented marker dictionary confirms evaluator/organization choices.
        if "불명" in raw:
            actual -= {"교사", "개별수행"}
        equal = actual == expected_methods
    elif name == "sub_scores":
        points = [float(v) for v in re.findall(r",\s*(\d+(?:\.\d+)?)점", raw)]
        # Element names are semantically checked against the saved literal pairs.
        # Reviewer abbreviations and the original question wording are retained.
        equal = sorted(v["score"] for v in value) == sorted(points)
    elif name == "task_text":
        equal = case_id not in PARTIAL_DESCRIPTIONS
    elif name == "rubric":
        equal = bool(value) == raw.startswith("있음")
    else:
        equal = value == raw.startswith("true")
    return "맞음" if equal else "틀림"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {phase: {r: read(f"data/derived/items/{r}{suffix}.json") for r in ROUNDS}
               for phase, suffix in (("before", ".prev-s6d2d"), ("after", ""))}
    cases = []
    for prefix, sample_path, reference in (
        ("A", "docs/dev/2026-11-08-s6d3-field-sample.json",
         "docs/dev/2026-11-09-s6d3-astra-field.md"),
        ("B", "docs/dev/2026-11-09-s6d3b-field-sample.json",
         "docs/dev/2026-11-09-s6d3b-astra-field.md"),
    ):
        sample, expected = read(sample_path), reviewer_rows(reference)
        for number, (source, sampled) in enumerate(zip(
            sample["source_review"], sample["pipeline_fields"], strict=True
        ), 1):
            case_id = f"{prefix}{number:02}"
            row = {"sample_id": case_id, "reference": reference, "source": source,
                   "expected": expected[f"F{number:02}"],
                   "excluded_reason": EXCLUDED.get(case_id),
                   "manual_coverage_note": PARTIAL_DESCRIPTIONS.get(case_id)}
            for phase in reports:
                item, basis = item_for_sample(reports[phase][source["round"]], sampled)
                fields = item["fields"] if item else {}
                row[phase] = {"item_id": item["item_id"] if item else None,
                              "match_basis": basis,
                              "extraction_status": item["extraction_status"] if item else None,
                              "fields": fields,
                              "judgments": {name: ("제외" if case_id in EXCLUDED else judge(
                                  case_id, name, row["expected"][label], fields.get(name)
                              )) for name, label in FIELDS.items()}}
            cases.append(row)
    totals = {phase: {name: dict(Counter(c[phase]["judgments"][name] for c in cases))
                      for name in FIELDS} for phase in reports}
    result = {"baseline": "S6d-2d .prev-s6d2d", "case_count": len(cases),
              "comparable_count": len(cases) - len(EXCLUDED), "fields": FIELDS,
              "method": "개발 재대조·부분 누락은 틀림·부재 확정은 source_absent 필요",
              "semantic_review": "과제 설명의 활동 포괄·요소별 이름/점수 쌍은 수동 대조. "
                                 "A05는 축약어 대신 원문의 평가 질문을 허용. "
                                 "제목 충돌의 대표값은 표시값으로 대조하고 conflict 상태도 보존.",
              "cases": cases, "totals": totals, "access_violations": VIOLATIONS}
    save(ROOT / f"docs/dev/{PREFIX}-field-recheck.json", result)
    lines = ["# S6d-3c 개발 28항목 필드 재대조", "",
             "첫 표본 F01~F14를 A01~A14, 두 번째 표본 B01~B14를 그대로 표기했다.", "",
             "S6d-2d 현재 결과 보관본과 이번 결과를 비교했다. 28건 모두 기록하고, "
             "다과제 2건·일반 기준표 1건·학년/판본 불일치 1건을 제외한 24건을 집계했다. "
             "원문 부재도 분모에 포함하며 source_absent와 근거가 있어야 맞음이다. "
             "설명의 부분 누락은 틀림으로 엄격하게 세었다.", "",
             "| 필드 | 맞음 전→후 | 누락 전→후 | 틀림 전→후 | 제외 |",
             "|---|---:|---:|---:|---:|"]
    for name, label in FIELDS.items():
        cells = [f"{totals['before'][name].get(k, 0)}→{totals['after'][name].get(k, 0)}"
                 for k in ("맞음", "누락", "틀림")]
        lines.append(f"| {label} | " + " | ".join(cells) + " | 4 |")
    lines += ["", "## 원문 부재 필드만", "",
              "| 필드 | 원문 부재 수 | 맞음 전→후 | 누락 전→후 | 틀림 전→후 |",
              "|---|---:|---:|---:|---:|"]
    for name in ("score", "weight", "sub_scores"):
        absent = [c for c in cases if not c["excluded_reason"]
                  and c["expected"][FIELDS[name]]["value"].startswith("없음")]
        cells = [f"{sum(c['before']['judgments'][name] == k for c in absent)}→"
                 f"{sum(c['after']['judgments'][name] == k for c in absent)}"
                 for k in ("맞음", "누락", "틀림")]
        lines.append(f"| {FIELDS[name]} | {len(absent)} | " + " | ".join(cells) + " |")
    for case in cases:
        lines += ["", f"## {case['sample_id']}", "",
                  case["excluded_reason"] or case["manual_coverage_note"] or "원문 값과 대조.",
                  "", "| 필드 | Astra 값 | 근거 줄 | 전 | 후 |",
                  "|---|---|---|---|---|"]
        for name, label in FIELDS.items():
            expected = case["expected"].get(label, {})
            lines.append(f"| {label} | {expected.get('value', '')} | "
                         f"{expected.get('source_lines', '')} | "
                         f"{case['before']['judgments'][name]} | "
                         f"{case['after']['judgments'][name]} |")
        lines += ["", "실제 전후 값·상태·소유 근거·연결 항목 ID는 같은 이름의 JSON에 보존했다."]
    write(ROOT / f"docs/dev/{PREFIX}-field-recheck.md", "\n".join(lines) + "\n")
    print(totals)


if __name__ == "__main__":
    main()
