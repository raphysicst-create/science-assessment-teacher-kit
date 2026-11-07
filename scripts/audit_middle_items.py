"""Offline S6 development review, with a human/source comparison checklist."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from audit_middle_subjects import atomic_write, escape, location
from middle_items import FIELDS, RULE_VERSION, extract_middle_items, ownership_errors, visible

ROOT = Path(__file__).resolve().parents[1]


def audit(input_path: Path) -> dict:
    subjects = json.loads(input_path.read_text(encoding="utf-8"))
    s4 = json.loads((ROOT / "data/derived/segments/2026-round-3.json").read_text(encoding="utf-8"))
    parents = {s["segment_id"]: s for d in s4["documents"] for s in d["segments"]}
    source_documents = {d["converted_path"]: d for d in s4["documents"]}
    items, documents, excluded, sections = [], [], [], []
    trace_errors = []
    for document in subjects["documents"]:
        chosen = not (document["school"] == "영통중학교" and "(최종)" not in document["filename"])
        documents.append({**document, "development_selected": chosen})
        if not chosen:
            excluded.append({**document, "reason": "총괄 결정·영통 (최종) 판으로 개발"})
            continue
        conversion = json.loads((ROOT / document["converted_path"]).read_text(encoding="utf-8"))
        source_document = source_documents[document["converted_path"]]
        text = conversion["text"]
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != document["text_sha256"]:
            raise ValueError(f"S4 text hash mismatch: {document['converted_path']}")
        for section in subjects["sections"]:
            if section["converted_path"] != document["converted_path"]:
                continue
            if section["status"] != "target" or section["grade"] not in {1, 2}:
                if section["science_candidate"]:
                    excluded.append(
                        {
                            **document,
                            "section_id": section["section_id"],
                            "reason": "S5 " + section["status"],
                            "locator": section["locator"],
                        }
                    )
                continue
            parent = parents[section["segment_id"]]
            section = {
                **section,
                "semester": parent["semester"],
                "semester_evidence": parent["semester_evidence"],
            }
            found = extract_middle_items(text, section, conversion)
            for item in found:
                for name, field in item["fields"].items():
                    observations = (
                        field["evidence"] + field.get("options", []) + field.get("occurrences", [])
                    )
                    for obs in observations:
                        loc = obs["locator"]
                        if text[loc["start"] : loc["end"]] != obs["raw"]:
                            trace_errors.append(
                                {"item_id": item["item_id"], "field": name, "locator": loc}
                            )
                title = item["fields"]["title"]
                item["title_generated"] = bool(
                    title["value"]
                    and (
                        not title["evidence"]
                        or any(
                            visible(obs["raw"]) != title["value"]
                            or text[obs["locator"]["start"] : obs["locator"]["end"]] != obs["raw"]
                            for obs in title["evidence"]
                        )
                    )
                )
            sections.append(
                {
                    "section_id": section["section_id"],
                    "school": section["school"],
                    "grade": section["grade"],
                    "locator": section["locator"],
                    "candidate_count": len(found),
                    "bounded_count": sum(i["extraction_status"] == "bounded" for i in found),
                }
            )
            items.extend(
                {
                    **i,
                    **document,
                    "edition": source_document["edition"],
                    "source_sha256": source_document["sha256"],
                    "semester_evidence": section["semester_evidence"],
                }
                for i in found
            )
    errors = ownership_errors(items)
    # Cross-section checks also guard repeated source cells in S4 table fragments.
    conflict_ids = {key for error in errors for key in error["item_ids"]}
    trace_ids = {error["item_id"] for error in trace_errors}
    for item in items:
        if item["item_id"] in conflict_ids:
            item["ownership_status"] = "conflict"
            item["extraction_status"] = "review"
            item["review_reasons"].append("구간 간 필드 소유 충돌")
        if item["item_id"] in trace_ids or item["title_generated"]:
            item["extraction_status"] = "review"
            item["review_reasons"].append("근거 오프셋·제목 원문 불일치")
    bounded = [i for i in items if i["extraction_status"] == "bounded"]
    review = [i for i in items if i["extraction_status"] != "bounded"]
    school_grades = []
    for school in sorted({d["school"] for d in documents}):
        for grade in (1, 2):
            selected = [i for i in items if i["school"] == school and i["grade"] == grade]
            school_grades.append(
                {
                    "school": school,
                    "grade": grade,
                    "bounded": sum(i["extraction_status"] == "bounded" for i in selected),
                    "review": sum(i["extraction_status"] != "bounded" for i in selected),
                }
            )
    field_counts = {
        name: sum(i["fields"][name]["value"] not in ("", [], None) for i in bounded)
        for name in FIELDS
    }
    reasons = Counter(
        f["reason"] for i in bounded for f in i["fields"].values() if f["value"] in ("", [], None)
    )
    return {
        "schema_version": 1,
        "rule_version": RULE_VERSION,
        "round": subjects["round"],
        "scope": "개발 12개교 S5 target 중1·중2. 영통 (최종) 판. 원문 정답 대조 전",
        "public_eligible": False,
        "documents": documents,
        "sections": sections,
        "items": items,
        "excluded": excluded,
        "ownership_errors": errors,
        "source_trace_errors": trace_errors,
        "school_grades": school_grades,
        "summary": {
            "bounded": len(bounded),
            "review": len(review),
            "target_sections": len(sections),
            "title_generated": sum(i["title_generated"] for i in items),
            "ownership_errors": len(errors),
            "source_trace_errors": len(trace_errors),
            "field_filled": field_counts,
            "field_fill_rates": {
                k: round(v / len(bounded), 4) if bounded else 0 for k, v in field_counts.items()
            },
            "empty_reasons": dict(reasons),
            "empty_reasons_by_field": {
                name: dict(
                    Counter(
                        i["fields"][name]["reason"]
                        for i in bounded
                        if i["fields"][name]["value"] in ("", [], None)
                    )
                )
                for name in FIELDS
            },
            "review_reasons": dict(Counter(r for i in review for r in i["review_reasons"])),
        },
    }


def values(item: dict) -> str:
    labels = {
        "title": "제목",
        "assessment_area": "영역",
        "task_no": "번호",
        "task_text": "평가과제 원문",
        "method": "방법",
        "timing": "시기",
        "score": "만점",
        "points": "배점",
        "weight": "비율",
        "standards": "코드",
        "rubric": "채점기준",
        "criteria": "평가준거",
        "elements": "평가요소",
    }
    fields = item["fields"]
    output = []
    for name in FIELDS:
        field = fields[name]
        value = field["value"]
        if name == "standards":
            value = " / ".join(o["raw"] for o in field["occurrences"])
        if name in {"rubric", "criteria"} and value:
            value = f"근거 {len(field['evidence'])}개"
        elif name == "elements" and value:
            value = f"근거 {len(field['evidence'])}개"
        if name == "method":
            checks = " / ".join(o["raw"] for o in field["options"])
            value = f"{value} ({field['state']}) {checks}"
        has_evidence = "근거 있음" if field["evidence"] else "근거 없음"
        output.append(
            f"{labels[name]}={value if value != '' and value != [] else '빈값'} "
            f"[{has_evidence}]{' · ' + field['reason'] if field['reason'] else ''}"
        )
    return " / ".join(output)


def markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# 중학교 과학 항목·필드 추출 S6",
        "",
        report["scope"],
        "",
        "원문 정답 세트를 대조하기 전의 추출 관찰치다. 정밀도·재현율은 미측정이다. "
        "bounded는 표 구조·소유 범위 확인 상태이며 모든 항목의 공개 여부는 False다.",
        "",
        "Unicode 문자 오프셋은 변경하지 않은 S4 변환본 기준이며 끝은 미포함이다. "
        "표·행·열은 0부터 센다. 원문 경로·해시·판본·S4/S5 ID는 JSON에 보존한다. "
        "신목형 표는 같은 표의 학년 행이 입증한 머리글을 S4 경계 밖에서도 참조한다.",
        "",
        "PDF는 kordoc HTML/Markdown 표를 사용한다. 평문 폴백은 행·열 경계를 "
        "입증하지 못해 검토 후보로 남긴다. "
        "후보 수는 실제 항목 수와 다르며 표 전체 후보와 라벨 후보가 포함된다. "
        "코드 범위는 문법적으로만 펼치며 87개 유효성·교육과정은 S7 미검증이다.",
        "",
        f"bounded {summary['bounded']}개, 검토 후보 {summary['review']}개, "
        f"제목 생성 {summary['title_generated']}개, 소유 충돌 {summary['ownership_errors']}개.",
        "",
        "## 학교·학년별 항목 수",
        "",
        "| 학교 | 학년 | bounded | 검토 후보 |",
        "|---|---|---|---|",
    ]
    for row in report["school_grades"]:
        lines.append(f"| {row['school']} | 중{row['grade']} | {row['bounded']} | {row['review']} |")
    lines.extend(
        [
            "",
            "## 문서별 항목 수",
            "",
            "| 학교 | 문서 | 개발 선택 | bounded | 검토 |",
            "|---|---|---|---|---|",
        ]
    )
    for doc in report["documents"]:
        items = [i for i in report["items"] if i["converted_path"] == doc["converted_path"]]
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        doc["school"],
                        doc["filename"],
                        doc["development_selected"],
                        sum(i["extraction_status"] == "bounded" for i in items),
                        sum(i["extraction_status"] != "bounded" for i in items),
                    ),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 필드 채움률",
            "",
            "분모는 bounded 항목이다. 채움률은 정확도와 별도다.",
            "",
            "| 필드 | 채움 수 | 채움률 | 빈값 이유 |",
            "|---|---|---|---|",
        ]
    )
    for name, count in summary["field_filled"].items():
        lines.append(
            f"| {name} | {count}/{summary['bounded']} | "
            f"{summary['field_fill_rates'][name]:.1%} | "
            f"{escape(summary['empty_reasons_by_field'][name])} |"
        )
    lines.extend(["", "## 검토 사유 분포", "", "한 후보에 여러 사유가 있을 수 있다.", ""])
    lines.extend(f"- {reason} — {count}개" for reason, count in summary["review_reasons"].items())
    lines.extend(
        [
            "",
            "## 사람이 원문과 대조할 우선순위",
            "",
            "1. 항목 구조 미식별·변환 셀 병합 의심 구간. 실제 항목 수·경계를 전수 대조한다.",
            "2. 번호형 요약행·상세표 중복 후보와 연결되지 않은 루브릭·성취수준 표.",
            "3. S5 경계 미확정 공주중1, 신목중 학년 경계 및 공통 비율 병합셀.",
            "4. 체크 선택지·기타 괄호·코드 범위와 빈 필드. 미기재 사유는 소유 범위 내 관찰이다.",
            "",
            "## 원문 대조 확인표",
            "",
            "추출 값·각 필드 근거 유무와 빈값 이유를 모두 표시한다. "
            "필드별 정확 위치는 다음 표와 JSON의 evidence에 있다.",
            "",
            "| 확인 | 학교 | 학년 | 문서 | 항목 ID | 상태 | 원문 위치 | 추출 값 | 사유 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in report["items"]:
        lines.append(
            "| ☐ | "
            + " | ".join(
                map(
                    escape,
                    (
                        item["school"],
                        item["grade"],
                        item["filename"],
                        item["item_id"],
                        item["extraction_status"],
                        location(item),
                        values(item),
                        " / ".join(item["review_reasons"]),
                    ),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 필드별 원문 위치",
            "",
            "| 학교·학년 | 항목 ID | 필드 | 원문 위치 | 표·행·열 | 원문 값 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in report["items"]:
        for name, field in item["fields"].items():
            for obs in field["evidence"]:
                loc = obs["locator"]
                raw = (
                    obs["raw"]
                    if name not in {"rubric", "elements", "standards"}
                    else obs["raw"][:80]
                )
                lines.append(
                    "| "
                    + " | ".join(
                        map(
                            escape,
                            (
                                f"{item['school']} 중{item['grade']}",
                                item["item_id"],
                                name,
                                location(obs),
                                "/".join(str(loc.get(k, "—")) for k in ("table", "row", "col")),
                                raw,
                            ),
                        )
                    )
                    + " |"
                )
    lines.extend(["", "## 대상 제외·보류", "", "| 학교 | 문서 | 이유 |", "|---|---|---|"])
    for row in report["excluded"]:
        lines.append(
            "| " + " | ".join(map(escape, (row["school"], row["filename"], row["reason"]))) + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path, default=ROOT / "data/derived/subjects/2026-round-3.json"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/derived/items")
    args = parser.parse_args()
    report = audit(args.input)
    atomic_write(
        args.output_dir / "2026-round-3.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write(args.output_dir / "2026-round-3.md", markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
