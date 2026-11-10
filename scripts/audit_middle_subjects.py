"""Produce the offline S5 development-corpus review index, never publication data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path

from middle_rounds import roster_codes, roster_path
from middle_subjects import (
    MIDDLE_SUBJECT_PREFIXES,
    RULE_VERSION,
    SCIENCE_EXCLUSION_RE,
    code_evidence,
    subject_sections,
    table_diagnostics,
    table_spans,
)
from text_clean import read_conversion

ROOT = Path(__file__).resolve().parents[1]
STATES = ("target", "other", "mixed", "unknown", "image_only")
STATE_LABELS = {
    "target": "과학", "other": "타 교과", "mixed": "혼합", "unknown": "미확정",
    "image_only": "읽을 수 없음",
}
REASONS = {
    "target_and_other_codes": "과학·타 교과 코드 동시 존재",
    "unknown_code": "공통 사전에 없는 접두",
    "science_code": "과학 코드 앵커",
    "other_subject_code": "타 교과 코드",
    "verified_science_section_without_code": "과학 머리글과 구조 경계 확인, 무코드",
    "other_subject_heading": "타 교과 머리글",
    "no_code_or_verified_subject_boundary": "코드·검증된 과학 경계 없음",
    "heading_code_conflict": "머리글·코드 교과 불일치",
}


def science_candidate(section: dict) -> bool:
    return bool(
        "과" in section["code_counts"] or (section["header"] and section["header"]["key"] == "과학")
    )


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.stem + "_", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def document_status(decisions: list[dict], conversion: dict) -> str:
    if conversion.get("conversion_status") == "image_only":
        return "image_only"
    states = {s["status"] for s in decisions}
    if "mixed" in states or {"target", "other"} <= states:
        return "mixed"
    for state in ("target", "other"):
        if state in states:
            return state
    return "unknown"


def audit(input_path: Path, roster: Path | None = None) -> dict:
    s4 = json.loads(input_path.read_text(encoding="utf-8"))
    schools = roster_codes(roster) if roster else None
    prefix_counts = Counter()
    sections, excluded_examples, documents = [], [], []
    pre_grade_conflicts = []
    for document in s4["documents"]:
        if schools is not None and str(document["source"]["school_code"]) not in schools:
            continue
        path = ROOT / document["converted_path"]
        conversion = read_conversion(path)
        text = conversion["text"]
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_sha != document["text_sha256"]:
            raise ValueError(f"S4 text hash mismatch: {path}")
        physical_path = None
        if (Path(document["original_path"]).suffix.lower() == ".pdf"
                and conversion.get("conversion_status") != "image_only"):
            from middle_physical import add_column_geometry, physical_index

            physical = physical_index(text, conversion, ROOT / document["original_path"])
            add_column_geometry(physical, ROOT / document["original_path"])
            conversion["physical"] = physical
            physical_path = f"data/derived/subjects/physical/{document['sha256']}.json"
            atomic_write(
                ROOT / physical_path,
                json.dumps(
                    {"source_sha256": document["sha256"], "text_sha256": text_sha, **physical},
                    ensure_ascii=False,
                ),
            )
        prefix_counts.update(c["prefix"] for c in code_evidence(text))
        decisions = subject_sections(text, document["segments"], conversion)
        pre_grade_conflicts.extend(
            {
                "converted_path": document["converted_path"],
                "section_id": s["section_id"],
                "grade": s["grade"],
                "locator": s["locator"],
                "header": s["header"],
                "codes": s["codes"],
                "appendix_boundary_evidence": s.get("appendix_boundary_evidence"),
                "appendix_review": s.get("appendix_review"),
            }
            for s in decisions
            if "heading_code_conflict" in s["reasons"]
        )
        source_tables = table_spans(text)
        metadata = {
            "school": document["source"]["school_name"],
            "school_code": document["source"]["school_code"],
            "filename": document["edition"]["candidate_name"],
            "document_id": document["document_id"],
            "converted_path": document["converted_path"],
            "original_path": document["original_path"],
            "text_sha256": text_sha,
            "version_status": document.get("version_status", "single"),
            "physical_path": physical_path,
            "child_id": document.get("child_id"),
            "parent_document_id": document.get("parent_document_id"),
            "conversion_status": conversion.get("conversion_status"),
            "status": document_status(decisions, conversion),
            "grades": sorted({s["grade"] for s in document["segments"] if s["grade"]}),
            "review_reason": (
                "읽을 수 없음(image_only): PDF 글자층 없음. OCR·원문 확인 필요"
                if conversion.get("conversion_status") == "image_only" else None
            ),
        }
        documents.append(metadata)
        for section in decisions:
            if section["grade"] not in {1, 2}:
                continue
            tables = table_diagnostics(text, section, source_tables)
            sections.append(
                {
                    **section,
                    **metadata,
                    "status": section["status"],
                    "document_status": metadata["status"],
                    "science_candidate": science_candidate(section),
                    "tables": tables,
                }
            )
        for match in SCIENCE_EXCLUSION_RE.finditer(text):
            owner = next(
                (
                    s
                    for s in decisions
                    if s["locator"]["start"] <= match.start() < s["locator"]["end"]
                ),
                None,
            )
            if not owner or owner["grade"] not in {1, 2} or owner["status"] != "other":
                continue
            # Keep an exact source slice <=20 characters. Never copy full prose.
            excerpt = text[match.start() : min(match.start() + 20, owner["locator"]["end"])]
            excluded_examples.append(
                {
                    **metadata,
                    "grade": owner["grade"],
                    "section_id": owner["section_id"],
                    "excerpt": excerpt,
                    "locator": {"start": match.start(), "end": match.end()},
                    "excluded_term": match.group(),
                    "code_counts": owner["code_counts"],
                    "header": owner["header"],
                    "reason": "非과목 복합어 및 타 교과 근거",
                }
            )
    school_grades = []
    for school in sorted({d["school"] for d in documents}):
        for grade in (1, 2):
            group = [s for s in sections if s["school"] == school and s["grade"] == grade]
            candidates = [s for s in group if s["science_candidate"]]
            counts = Counter(s["status"] for s in group)
            school_grades.append(
                {
                    "school": school,
                    "grade": grade,
                    "science_candidate_count": len(candidates),
                    "science_target_count": sum(s["status"] == "target" for s in candidates),
                    "science_parent_segment_count": len({s["segment_id"] for s in candidates}),
                    "state_counts": {state: counts[state] for state in STATES},
                    "science_state_counts": dict(Counter(s["status"] for s in candidates)),
                }
            )
    unresolved = [s["section_id"] for s in sections if s["status"] in {"mixed", "unknown"}]
    no_codes = [
        s["section_id"]
        for s in sections
        if s["science_candidate"] and s["status"] == "target" and not s["codes"]
    ]
    unresolved_grades = []
    for document in s4["documents"]:
        for segment in document["segments"]:
            if segment["grade"] is None:
                unresolved_grades.append(
                    {
                        "school": document["source"]["school_name"],
                        "filename": document["edition"]["candidate_name"],
                        "segment_id": segment["segment_id"],
                        "locator": segment["locator"],
                        "reason": segment["review_reason"],
                    }
                )
    return {
        "pre_grade_conflicts": pre_grade_conflicts,
        "schema_version": 1,
        "rule_version": RULE_VERSION,
        "round": s4["round"],
        "roster": str(roster) if roster else s4.get("roster"),
        "scope": (
            f"정답 {len(schools) if schools is not None else 10}개교, "
            "보존된 전체 문서의 S4 중1·중2 구간. 판본 합산"
            if "-gold" in s4["round"] else
            "개발 명단의 S4 중1·중2 구간. 판본을 합산하며 원문 항목 수와 구별"
        ),
        "curriculum_status": "미확정. S7에서 검토",
        "public_eligible": False,
        "known_prefixes": MIDDLE_SUBJECT_PREFIXES,
        "prefix_counts_all_grades": dict(sorted(prefix_counts.items())),
        "unknown_prefix_counts": {
            p: n for p, n in sorted(prefix_counts.items()) if p not in MIDDLE_SUBJECT_PREFIXES
        },
        "school_grades": school_grades,
        "documents": documents,
        "sections": sections,
        "mixed_unknown_section_ids": unresolved,
        "no_code_science_section_ids": no_codes,
        "false_positive_exclusions": excluded_examples,
        "grade_unresolved": unresolved_grades,
        "s4_incomplete_source_count": len(s4["incomplete_sources"]),
        "summary": {
            "document_states": dict(Counter(d["status"] for d in documents)),
            "schools": len(school_grades) // 2,
            "documents": len(documents),
            "observed_prefix_types": len(prefix_counts),
            "prefix_occurrences": prefix_counts.total(),
            "section_states": dict(Counter(s["status"] for s in sections)),
            "science_candidate_states": dict(
                Counter(s["status"] for s in sections if s["science_candidate"])
            ),
            "science_parent_segments": len(
                {s["segment_id"] for s in sections if s["science_candidate"]}
            ),
            "table_states": dict(Counter(t["status"] for s in sections for t in s["tables"])),
            "no_code_science_sections": len(no_codes),
            "excluded_compound_occurrences": len(excluded_examples),
        },
    }


def location(item: dict) -> str:
    loc = item["locator"]
    pages = loc.get("pages")
    suffix = f" / 쪽 {','.join(map(str, pages))}" if pages else ""
    return f"문자 {loc['start']}–{loc['end']}" + suffix


def reason_text(item: dict) -> str:
    counts = ", ".join(f"[9{p} ×{n}" for p, n in item["code_counts"].items()) or "코드 없음"
    reasons = ", ".join(REASONS.get(r, r) for r in item["reasons"])
    header = (item.get("header") or {}).get("key", "없음")
    return f"{counts}. 머리글 {header}. {reasons}"


def escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def markdown(report: dict) -> str:
    summary = report["summary"]
    science = summary["science_candidate_states"]
    states = summary["section_states"]
    lines = [
        "# 중학교 과목 판정 실측 S5",
        "",
        f"개발 {report['summary']['schools']}개교의 중1·중2 S4 구간을 대상으로 한다. "
        "비공개 검토 자료이며 "
        "교육과정·단원·항목 제목·배점은 확정하지 않는다.",
        "",
        "구간 수는 구조 구간과 코드 앵커 후보 수이며 평가 항목 수와 다르다. "
        "수정·최종 판본을 각각 센다. 학년 미확정·중3은 본 집계에서 격리했다.",
        "",
        "위치는 변경하지 않은 변환본의 Unicode 문자 오프셋이며 끝은 미포함이다. "
        "원문 파일 경로와 변환본 해시는 JSON 문서 목록에 있다. "
        "고정 길이 발췌는 경계 확인에 사용하지 않았다.",
        "",
        "S4가 한 표 안의 학년 행에서 나눈 경우 표 조각 단위로 검사한다. "
        "표의 행·셀 진단과 caller가 제공하는 항목 단위 판정을 구별한다. "
        "실문서의 항목 소유권은 S6 확인 대상이다.",
        "",
        f"S4 과학 부모 구간 {summary['science_parent_segments']}개에서 "
        f"S5 후보 {sum(science.values())}개를 기록했다. "
        f"과학 {science.get('target', 0)}개, 혼합 {science.get('mixed', 0)}개, "
        f"미확정 {science.get('unknown', 0)}개다. "
        f"전 교과 전체 구간은 과학 {states.get('target', 0)}개, "
        f"타 교과 {states.get('other', 0)}개, 혼합 {states.get('mixed', 0)}개, "
        f"미확정 {states.get('unknown', 0)}개다.",
        "",
        "## 학교·학년별 구간 수",
        "",
        "| 학교 | 학년 | 과학 후보 | 과학 판정 | 과학 | 타 교과 | 혼합 | 미확정 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in report["school_grades"]:
        counts = row["state_counts"]
        lines.append(
            f"| {row['school']} | 중{row['grade']} | {row['science_candidate_count']} | "
            f"{row['science_target_count']} | " + " | ".join(str(counts[s]) for s in STATES) + " |"
        )
    lines.extend(
        [
            "",
            "## 관찰 접두와 출현 수",
            "",
            "전 학년 변환본 25건에서 중복 출현을 포함해 집계했다. "
            "코드 유효성·교육과정 연도 판정은 포함하지 않는다.",
            "",
            "| 접두 | 횟수 | 공통 사전 교과 |",
            "|---|---|---|",
        ]
    )
    for prefix, count in report["prefix_counts_all_grades"].items():
        label = report["known_prefixes"].get(prefix, "unknown_code · 원 교육과정 확인 필요")
        lines.append(f"| [9{prefix} | {count} | {label} |")
    lines.extend(
        [
            "",
            "## 사람이 대조할 우선순위",
            "",
            "1. 머리글·코드 충돌, 혼합 표, 머리글 없는 과학 코드 앵커의 시작·끝.",
            "2. 미확정 접두와 학년 미확정 구간. 전 교과 코드 부록·요약표 여부도 확인.",
            "3. 무코드 과학 구간과 다음 기술·가정 머리글 경계.",
            "4. 복수 판본의 대체 관계와 S4 판본 충돌. 과목 판정으로 공개를 승인하지 않음.",
            "",
            "## 혼합·미확정 구간 전부",
            "",
            "| 학교 | 학년 | 문서 | 위치 | 판정 | 근거 | 구간 ID |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for section in report["sections"]:
        if section["status"] in {"mixed", "unknown"}:
            lines.append(review_row(section))
    lines.extend(
        [
            "",
            "## 표 혼합·미확정 진단",
            "",
            "같은 셀에 두 교과 코드가 있으면 셀 내부 혼합으로 기록한다. "
            "같은 행의 서로 다른 셀은 항목 경계를 확정하지 않으며 행 혼합으로 기록한다.",
            "",
            "| 학교·학년 | 문서 | 표 위치 | 판정 | 행 간 혼합 | 혼합 행 수 | 혼합 셀 수 | 근거 |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for section in report["sections"]:
        for table in section["tables"]:
            if table["status"] not in {"mixed", "unknown"}:
                continue
            lines.append(
                "| "
                + " | ".join(
                    map(
                        escape,
                        (
                            f"{section['school']} 중{section['grade']}",
                            section["filename"],
                            location(table),
                            STATE_LABELS[table["status"]],
                            table["between_rows_mixed"],
                            len(table["mixed_rows"]),
                            len(table["mixed_cells"]),
                            reason_text(table),
                        ),
                    )
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "## 무코드 과학 구간",
            "",
            "과학 머리글과 구조 경계를 확인한 구간만 허용했다. 단원 매핑은 S10에서 수행한다.",
            "",
            "| 학교 | 학년 | 문서 | 위치 | 판정 | 근거 | 구간 ID |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for section in report["sections"]:
        if section["section_id"] in report["no_code_science_section_ids"]:
            lines.append(review_row(section))
    lines.extend(
        [
            "",
            "## 오탐 제외 문장 예시",
            "",
            "원문 발췌는 각각 20자 이내이며 같은 표현은 학교·학년별 첫 예시만 표시한다. "
            "전체 출현과 위치는 JSON에 있다.",
            "",
            "| 학교 | 학년 | 문서 | 위치 | 원문 발췌 | 타 교과 근거 |",
            "|---|---|---|---|---|---|",
        ]
    )
    seen = set()
    for example in report["false_positive_exclusions"]:
        key = example["school"], example["grade"], example["excluded_term"]
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        example["school"],
                        example["grade"],
                        example["filename"],
                        location(example),
                        example["excerpt"],
                        str(example["code_counts"]),
                    ),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 원문 대조 확인표",
            "",
            "체크 칸은 사람이 원문과 대조한 뒤 기록한다. 모든 중1·중2 구간을 열거한다. "
            "문서명과 문자 위치로 JSON의 원문 경로·해시·S4 부모 ID를 찾을 수 있다.",
            "",
            "| 확인 | 학교 | 학년 | 문서 | 위치 | 판정 | 근거 | 구간 ID |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for section in report["sections"]:
        lines.append("| ☐ " + review_row(section)[1:])
    lines.extend(
        ["", "## 학년 미확정 격리 구간", "", "| 학교 | 문서 | 위치 | 이유 |", "|---|---|---|---|"]
    )
    for item in report["grade_unresolved"]:
        lines.append(
            "| "
            + " | ".join(
                map(
                    escape,
                    (
                        item["school"],
                        item["filename"],
                        location(item),
                        item["reason"],
                    ),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def review_row(section: dict) -> str:
    return (
        "| "
        + " | ".join(
            map(
                escape,
                (
                    section["school"],
                    f"중{section['grade']}",
                    section["filename"],
                    location(section),
                    STATE_LABELS[section["status"]],
                    reason_text(section),
                    section["section_id"],
                ),
            )
        )
        + " |"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round-key", default="2026-round-3")
    parser.add_argument("--roster", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/derived/subjects")
    args = parser.parse_args()
    roster = roster_path(ROOT, args.round_key, args.roster)
    report = audit(args.input or ROOT / f"data/derived/segments/{args.round_key}.json", roster)
    atomic_write(
        args.output_dir / f"{args.round_key}.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    body = markdown(report)
    if "-gold" in args.round_key:
        body = body.replace("개발 12개교", f"정답 {len(roster_codes(roster))}개교")
    atomic_write(args.output_dir / f"{args.round_key}.md", body)
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
