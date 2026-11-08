"""Compare offline development S4–S6 artifacts and sample new science spans."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from functools import lru_cache
from pathlib import Path

from middle_rounds import roster_path
from middle_subjects import MIDDLE_SUBJECT_PREFIXES, canonical_subject, code_evidence

ROOT = Path(__file__).resolve().parents[1]
STATES = ("target", "other", "mixed", "unknown", "image_only")


@lru_cache(maxsize=64)
def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def artifacts(round_key: str, previous: bool) -> dict:
    suffix = ".prev-s6d0" if previous else ""
    return {
        kind: read(ROOT / f"data/derived/{kind}/{round_key}{suffix}.json")
        for kind in ("segments", "subjects", "items")
    }


def document_states(data: dict) -> dict:
    """Use the same whole-text evidence for both snapshots, including grade 3.

    Historical S5 did not emit a document status. Reconstruct it from all code
    prefixes and its scoped section decisions; do not call it an observed field.
    """
    result = Counter()
    sections = data["subjects"]["sections"]
    for document in data["subjects"]["documents"]:
        if "status" in document:
            result[document["status"]] += 1
            continue
        conversion = read(ROOT / document["converted_path"])
        codes = code_evidence(conversion["text"])
        science = any(c["prefix"] == "과" for c in codes)
        other = any(c["subject"] and c["prefix"] != "과" for c in codes)
        states = {
            s["status"] for s in sections if s["converted_path"] == document["converted_path"]
        }
        # Reconstruct the old visible state: image_only was silently unknown.
        state = (
            "mixed"
            if science and other or "mixed" in states or {"target", "other"} <= states
            else "target"
            if science or "target" in states
            else "other"
            if other or "other" in states
            else "unknown"
        )
        result[state] += 1
    return {state: result[state] for state in STATES}


def coverage(data: dict, roster: Path) -> list[dict]:
    with roster.open(encoding="utf-8-sig", newline="") as handle:
        schools = list(csv.DictReader(handle))
    documents = data["segments"]["documents"]
    subjects = data["subjects"]["sections"]
    parents = {s["segment_id"]: s for d in documents for s in d["segments"]}
    result = []
    for school in schools:
        docs = [
            d for d in documents if str(d["source"]["school_code"]) == str(school["school_code"])
        ]
        for grade in (1, 2):
            candidates = [
                s
                for s in subjects
                if str(s["school_code"]) == str(school["school_code"])
                and s["grade"] == grade
                and s["status"] == "target"
            ]
            valid = [
                s for s in candidates if parents[s["segment_id"]]["text_sha256"] == s["text_sha256"]
            ]
            images = [d for d in docs if d["conversion_status"] == "image_only"]
            readable = [d for d in docs if d["conversion_status"] not in {"image_only", "failed"}]
            if valid:
                state, reason = "찾음", "S5 target 과학 구간과 S4 본문 해시 일치"
            elif not readable and images:
                state, reason = "읽을 수 없음", "image_only: 평가계획은 있으나 글자층 없음"
            elif not docs:
                state, reason = "못 찾음", "평가계획 문서 없음 또는 명단·수집 매칭 미확인"
            elif candidates:
                state, reason = "못 찾음", "ZIP 자식 S4 좌표와 S5 부모 본문 해시 불일치"
            else:
                unresolved = [s for d in docs for s in d["segments"] if s["grade"] is None]
                mixed = [
                    s
                    for s in subjects
                    if s["school_code"] == school["school_code"]
                    and s["grade"] == grade
                    and s["status"] in {"mixed", "unknown"}
                    and s.get("science_candidate")
                ]
                reason = (
                    "학년 연결 미확정"
                    if unresolved
                    else "과학 후보 mixed/unknown 경계 미확정"
                    if mixed
                    else "과학 머리글·코드 구간 미식별"
                )
                state = "못 찾음"
            result.append(
                {
                    "school": school["school_name"],
                    "school_code": school["school_code"],
                    "grade": grade,
                    "state": state,
                    "reason": reason,
                    "target_sections": len(valid),
                    "legacy_target_sections": len(candidates),
                }
            )
    return result


def span_key(section: dict) -> tuple:
    return section["original_path"], section.get("child_id"), section["grade"]


def new_sections(before: dict, after: dict, round_key: str) -> list[dict]:
    old = [s for s in before["subjects"]["sections"] if s["status"] == "target"]
    old_parents = {
        s["segment_id"]: s for d in before["segments"]["documents"] for s in d["segments"]
    }
    old = [s for s in old if old_parents[s["segment_id"]]["text_sha256"] == s["text_sha256"]]
    result = []
    for section in after["subjects"]["sections"]:
        if section["status"] != "target":
            continue
        start, end = section["locator"]["start"], section["locator"]["end"]
        if any(
            span_key(s) == span_key(section)
            and s["locator"]["start"] <= start
            and end <= s["locator"]["end"]
            for s in old
        ):
            continue
        text = read(ROOT / section["converted_path"])["text"]
        boundary = section.get("boundary_evidence") or {}
        next_parent = boundary.get("next_s4_boundary") or {}
        next_subject = section.get("next_subject")
        if not next_subject and next_parent.get("subject_heading_key"):
            next_subject = canonical_subject(next_parent["subject_heading_key"])
        next_grade = next_parent.get("grade")
        if next_grade and next_grade != section["grade"]:
            end_description = f"학년 표지/학년 칸: 중{next_grade}"
        elif boundary.get("end"):
            end_description = f"다음 교과 머리글: {next_subject}"
        else:
            end_description = section["end_basis"]
        result.append(
            {
                "round": round_key,
                "school": section["school"],
                "grade": section["grade"],
                "filename": section["filename"],
                "converted_path": section["converted_path"],
                "section_id": section["section_id"],
                "locator": section["locator"],
                "line_start": text.count("\n", 0, start) + 1,
                "line_end": text.count("\n", 0, max(start, end - 1)) + 1,
                "heading": section["header"]["raw"] if section["header"] else "코드 앵커",
                "end_basis": section["end_basis"],
                "next_subject": next_subject,
                "end_description": end_description,
                "boundary_evidence": section.get("boundary_evidence"),
                "boundary_verified": section["boundary_verified"],
            }
        )
    return result


def audit(data: dict) -> dict:
    docs = {d["converted_path"]: d for d in data["segments"]["documents"]}
    sections = data["subjects"]["sections"]
    parents = {s["segment_id"]: s for d in docs.values() for s in d["segments"]}
    errors = Counter()
    suspected = []
    for section in sections:
        document = docs[section["converted_path"]]
        conversion = read(ROOT / section["converted_path"])
        text = conversion["text"]
        start, end = section["locator"]["start"], section["locator"]["end"]
        errors["locator_out_of_bounds"] += not 0 <= start <= end <= len(text)
        errors["parent_text_mismatch"] += (
            parents[section["segment_id"]]["text_sha256"] != section["text_sha256"]
        )
        errors["child_identity_mismatch"] += section.get("child_id") != document.get("child_id")
        if section["status"] != "target":
            continue
        header = section.get("header")
        unsupported = not section["codes"] and not (
            section["boundary_verified"] and header and header["key"] == "과학"
        )
        errors["uncoded_without_science_heading"] += unsupported
        if unsupported or header and header["key"] != "과학":
            suspected.append(
                {
                    "section_id": section["section_id"],
                    "school": section["school"],
                    "filename": section["filename"],
                    "locator": section["locator"],
                    "reason": (
                        "무코드 머리글 미입증" if unsupported else
                        "타 교과 머리글·과학 코드 충돌"
                        if header["key"] in set(MIDDLE_SUBJECT_PREFIXES.values()) else
                        f"사전 밖 과목명({header['key']})·과학 코드: 경계 검토 필요"
                    ),
                }
            )
    for key in ("ownership_errors", "source_trace_errors", "title_generated"):
        errors[key] = data["items"]["summary"][key]
    return {"violations": dict(errors), "suspected_false_positives": suspected}


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", "")


def markdown(report: dict) -> str:
    lines = [
        "# S6d-1 개발 자료 전후 비교",
        "",
        "네트워크·정답 자료 사용 없음. S6 항목 규칙은 변경하지 않았다. "
        "찾음은 중1·2 S5 target 구간과 S4 본문 해시가 일치하는 칸이다. "
        "ZIP의 이전 target 중 부모 본문을 잘못 참조한 것은 찾음에서 제외했다. "
        "읽을 수 없음은 S3 image_only이며 평가계획 없음과 구별한다.",
        "",
        "과거 S5에 문서 상태 필드가 없어 이전 문서 상태는 보관 본문의 코드 및 "
        "이전 구간 결정으로 재구성했다. 이전 image_only는 당시처럼 unknown으로 집계했다. "
        "후속 표는 ZIP을 자식 독립 문서로 세므로 문서 분모가 달라진다.",
        "",
        "| 회차 | 찾음 전→후 | 못 찾음 전→후 | 읽을 수 없음 전→후 | bounded 전→후 | 검토 전→후 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["rounds"]:
        a, b = row["coverage_counts_before"], row["coverage_counts_after"]
        counts = [f"{a.get(k, 0)}→{b.get(k, 0)}" for k in ("찾음", "못 찾음", "읽을 수 없음")]
        counts.extend(f"{row['s6_before'][k]}→{row['s6_after'][k]}" for k in ("bounded", "review"))
        lines.append("| " + " | ".join([row["round"], *counts]) + " |")
    for row in report["rounds"]:
        lines.extend(
            [
                "",
                f"## {row['round']} 기대 범위표",
                "",
                "| 학교 | 중1 전→후 | 중2 전→후 | 미발견·판독 사유(전·후) |",
                "|---|---|---|---|",
            ]
        )
        before, after = row["coverage_before"], row["coverage_after"]
        for index in range(0, len(after), 2):
            pair = after[index : index + 2]
            reasons = "; ".join(
                f"{phase} 중{x['grade']}: {x['reason']}"
                for phase, group in (("전", before[index:index + 2]), ("후", pair))
                for x in group if x["state"] != "찾음"
            )
            transitions = [f"{before[index + i]['state']}→{x['state']}" for i, x in enumerate(pair)]
            lines.append(
                "| "
                + " | ".join(map(cell, [pair[0]["school"], *transitions, reasons or "—"]))
                + " |"
            )
        lines.extend(["", "| S5 문서 상태 | 전 | 후 |", "|---|---:|---:|"])
        for state in STATES:
            lines.append(f"| {state} | {row['s5_before'][state]} | {row['s5_after'][state]} |")
        lines.extend(["", "감사 위반: " + cell(row["audit"]["violations"]), ""])
    lines.extend(
        [
            "## 총괄 확인용 신규 과학 구간 12개",
            "",
            f"보충 두 회차의 신규 구간 {report['new_section_count']}개에서 "
            f"seed={report['seed']}로 단순 무작위 추출. "
            "줄은 자식 독립 변환 JSON의 text 기준(1부터). "
            "코드 앵커 후보는 구조 검증 여부를 별도로 표시한다.",
            "",
            "| 회차·학교·학년 | 문서 | 줄 | 시작 머리글 | 끝 경계 근거 | 다음 과목 | 구조 검증 |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for s in report["sample"]:
        values = [
            f"{s['round']} {s['school']} 중{s['grade']}",
            s["filename"],
            f"{s['line_start']}–{s['line_end']}",
            s["heading"],
            s["end_description"],
            s["next_subject"] or "없음/학년·표·문서 끝",
            s["boundary_verified"],
        ]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    lines.extend(["", "## 오탐 의심", ""])
    suspects = [s for r in report["rounds"] for s in r["audit"]["suspected_false_positives"]]
    lines.extend(f"- {cell(s)}" for s in suspects)
    if not suspects:
        lines.append(
            "구조·코드 충돌 자동 점검에서 발견 없음. "
            "의미상 오탐률은 미측정이며 표본 원문 대조가 필요하다."
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--round-keys",
        nargs="+",
        default=["2026-round-3", "2026-round-3-dev2", "2026-round-1-dev2"],
    )
    parser.add_argument("--seed", type=int, default=202611081)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/dev/2026-11-08-s6d1-comparison.md"
    )
    args = parser.parse_args()
    rows, additions = [], []
    for round_key in args.round_keys:
        if "gold" in round_key:
            parser.error("development rounds only")
        roster = roster_path(ROOT, round_key)
        before, after = artifacts(round_key, True), artifacts(round_key, False)
        ca, cb = coverage(before, roster), coverage(after, roster)
        rows.append(
            {
                "round": round_key,
                "coverage_before": ca,
                "coverage_after": cb,
                "coverage_counts_before": dict(Counter(x["state"] for x in ca)),
                "coverage_counts_after": dict(Counter(x["state"] for x in cb)),
                "s5_before": document_states(before),
                "s5_after": document_states(after),
                "s6_before": before["items"]["summary"],
                "s6_after": after["items"]["summary"],
                "audit": audit(after),
            }
        )
        if round_key.endswith("-dev2"):
            additions.extend(new_sections(before, after, round_key))
    additions.sort(key=lambda s: (s["round"], s["converted_path"], s["locator"]["start"]))
    report = {
        "seed": args.seed,
        "rounds": rows,
        "new_section_count": len(additions),
        "sample": random.Random(args.seed).sample(additions, min(12, len(additions))),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown(report), encoding="utf-8")
    args.output.with_suffix(".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)


if __name__ == "__main__":
    main()
