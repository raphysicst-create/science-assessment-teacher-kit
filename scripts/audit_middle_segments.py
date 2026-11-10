"""Audit every preserved development plan offline and write Korean S4 reports."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

from collect_schoolinfo_4ga_historical import atomic_bytes, atomic_json
from collect_schoolinfo_4ga_round import plan_status
from extract_math_assessment_batch import (
    convert_kordoc,
    extract_document,
    source_provenance,
)
from middle_rounds import roster_codes, roster_path
from middle_segments import (
    RULE_VERSION,
    STATUS_DEFINITIONS,
    child_identifier,
    document_identifier,
    resolve_versions,
    segment_document,
)
from text_clean import clean_tree

ROOT = Path(__file__).resolve().parents[1]


def audit_document(source: dict, root: Path, output: Path, *, reuse: bool = False) -> dict:
    path = root / source["saved_path"]
    provenance = source_provenance(path, source)
    if path.stat().st_size != source["size_bytes"]:
        raise ValueError(f"original size mismatch: {path}")
    kordoc = root / "node_modules/kordoc/dist/cli.js"
    text_path = output / f"{source['sha256']}.json"
    if reuse and text_path.exists():
        conversion = clean_tree(json.loads(text_path.read_text(encoding="utf-8")))
        if conversion.get("sha256", source["sha256"]) != source["sha256"]:
            raise ValueError("cached conversion source hash mismatch")
    elif path.suffix.lower() in {".pdf", ".zip"}:
        conversion = extract_document(path, kordoc, root, source, pdf_converter="kordoc")
    else:
        conversion = convert_kordoc(path, kordoc, root)
    if not reuse or not text_path.exists():
        atomic_json(text_path, conversion)
    document = {
        **provenance,
        "document_id": document_identifier(source["sha256"]),
        "source": source,
        "format": path.suffix.lower().lstrip("."),
        "document_kind": "assessment_plan",
        "conversion_status": conversion["conversion_status"],
        "converted_path": text_path.relative_to(root).as_posix(),
        "converter": conversion.get("converter"),
        "conversion_error": conversion.get("error"),
        "text_sha256": hashlib.sha256(conversion["text"].encode("utf-8")).hexdigest(),
        "text": conversion["text"],
        "segments": [],
        "children": [],
    }
    if "children" in conversion:
        for child in conversion["children"]:
            document["children"].append(
                {
                    "child_id": child_identifier(source["sha256"], child),
                    **{
                        k: child.get(k)
                        for k in (
                            "sha256",
                            "member_index",
                            "member_name",
                            "original_path",
                            "conversion_status",
                        )
                    },
                }
            )
            document["segments"].extend(segment_document(source, child, child))
    else:
        document["segments"] = segment_document(source, conversion)
    # Empty/failed conversions still appear at document level for manual review.
    if not document["segments"]:
        document["review_reason"] = "변환 본문 없음. 원문 확인 필요"
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != source["sha256"]:
            raise ValueError(f"original changed: {path}")
    document["summary"] = summarize_segments(document["segments"])
    return document


def independent_documents(document: dict, root: Path) -> list[dict]:
    """Materialize each ZIP member in its own coordinate system for S4–S6."""
    if not document["children"]:
        return [document]
    conversion_path = root / document["converted_path"]
    conversion = json.loads(conversion_path.read_text(encoding="utf-8"))
    result = []
    for child in conversion["children"]:
        identity = child_identifier(document["sha256"], child)
        path = conversion_path.with_name(identity + ".json")
        atomic_json(path, child)
        segments = segment_document(document["source"], child, child)
        for segment in segments:
            segment["document_id"] = identity
            segment["locator"]["text_field"] = "text"
        result.append({
            **document, "document_id": identity, "child_id": identity,
            "parent_document_id": document["document_id"],
            "parent_sha256": document["sha256"], "sha256": child.get("sha256"),
            "member_index": child["member_index"], "member_name": child["member_name"],
            "source": {**document["source"], "candidate_name": child["member_name"]},
            "edition": {**document["edition"], "candidate_name": child["member_name"]},
            "converted_path": path.relative_to(root).as_posix(),
            "text": child["text"],
            "text_sha256": hashlib.sha256(child["text"].encode("utf-8")).hexdigest(),
            "conversion_status": child["conversion_status"],
            "converter": child.get("converter"),
            "format": Path(child["member_name"]).suffix.lower().lstrip("."),
            "children": [], "segments": segments,
            "summary": summarize_segments(segments),
        })
    return result


def science_heading_candidates(documents: list[dict]) -> list[dict]:
    return [
        {
            "school_name": d["source"]["school_name"],
            "filename": d["source"]["candidate_name"],
            "document_id": d["document_id"],
            **s,
        }
        for d in documents
        for s in d["segments"]
        if "과학" in (s["subject_heading_raw"] or "")
    ]


def summarize_segments(segments: list[dict]) -> dict:
    return {
        "segment_count": len(segments),
        "grades": dict(Counter(str(s["grade"]) if s["grade"] else "unresolved" for s in segments)),
        "statuses": dict(Counter(status for s in segments for status in s["statuses"])),
    }


def aggregate(documents: list[dict]) -> dict:
    candidates = science_heading_candidates(documents)
    schools = {}
    for name in sorted({d["source"]["school_name"] for d in documents}):
        rows = [s for s in candidates if s["school_name"] == name]
        schools[name] = {
            "grade1_candidates": sum(s["grade"] == 1 for s in rows),
            "grade2_candidates": sum(s["grade"] == 2 for s in rows),
            "grade3_candidates": sum(s["grade"] == 3 for s in rows),
            "grade_unresolved_candidates": sum(s["grade"] is None for s in rows),
            "active_grade1_2_candidates": sum(
                s["grade"] in {1, 2}
                and not ({"superseded", "version_conflict"} & set(s["statuses"]))
                for s in rows
            ),
        }
    return {
        **summarize_segments([s for d in documents for s in d["segments"]]),
        "documents": len(documents),
        "schools": schools,
        "formats": dict(Counter(d["format"] for d in documents)),
        "versions": dict(Counter(d["version_status"] for d in documents)),
    }


def cell(value: object) -> str:
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")


def locator_label(locator: dict) -> str:
    label = f"[{locator['start']}, {locator['end']})"
    if "pages" in locator:
        label += f" / p.{locator['page_start']}–{locator['page_end']}"
    return label


def markdown_report(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# 중학교 문서·구간 식별 실측",
        "",
        f"{'정답용' if '-gold' in report.get('round', '') else '개발용'} "
        f"{len(summary['schools'])}개교 평가계획 {summary['documents']}개. "
        f"구간 후보 {summary['segment_count']}개.",
        "과목 머리글 후보의 원문 표기를 기록했다. "
        "모든 구간은 S5 이후 검토 대기이며 공개 상태는 비공개다.",
        "시작·끝은 저장한 변환 JSON의 text에 대한 Unicode 문자 오프셋이며 끝은 배타적이다. "
        "PyMuPDF 페이지는 대조용 변환 메타데이터에 보존한다. "
        "kordoc 본문 문자와 PDF 페이지의 대응은 미측정이다. HWP/HWPX 물리 페이지도 미측정이다.",
        "본문 머리글·표 셀·다음 구조 머리글로 경계를 잡았다. 경계는 candidate 상태이며 "
        "공통 표 머리글은 학년 구간 앞에 있을 수 있다. subject_heading_locator로 함께 찾는다.",
        "동일 과목에서 학년이 반복되면 위치별 별도 구간으로 남긴다. "
        "교수학습부·평가부가 반복되면 후보 수가 학년 수보다 클 수 있다.",
        "목차·표지·미식별 머리글 구간도 누락시키지 않고 검토 상태로 기록한다. "
        "과학 후보 목록은 머리글의 문자열 포함 검사 결과다.",
        "판본은 공백·페이지 번호 줄을 제거한 본문이 같을 때만 자동 대체한다. "
        "표 태그·병합 속성은 비교에 유지한다. "
        "유사도가 높아도 남은 문자 차이는 충돌로 보류한다. "
        "file_seq는 공시 목록 순서, collected_at은 수집 시각이다. 게시 시각은 미제공이다.",
        "",
        "## 상태 정의",
        "",
        *[f"- `{key}` — {value}" for key, value in STATUS_DEFINITIONS.items()],
        "",
        "## 문서별 집계",
        "",
        "| 학교 | 파일명 | 형식 | 구간 | 학년별 수 | 판본 | 변환 |",
        "|---|---|---|---:|---|---|---|",
    ]
    for d in report["documents"]:
        values = [
            d["source"]["school_name"],
            d["source"]["candidate_name"],
            d["format"],
            d["summary"]["segment_count"],
            d["summary"]["grades"],
            d["version_status"],
            d["conversion_status"],
        ]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    lines.extend(
        [
            "",
            "## 학교별 과학 머리글 후보",
            "",
            "동일 판본·반복 구간을 포함한 수다. 충돌·대체 제외 수는 마지막 칸에 기록했다.",
            "",
            "| 학교 | 중1 | 중2 | 중3 | 학년 미확정 | 충돌·대체 제외 중1·중2 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, counts in summary["schools"].items():
        lines.append("| " + " | ".join(map(cell, [name, *counts.values()])) + " |")
    lines.extend(
        [
            "",
            "## 과학 포함 머리글 구간 목록",
            "",
            "| 학교·파일 | 구간 ID | 학년 | 학기 | 머리글 원문 | locator | 상태 |",
            "|---|---|---:|---:|---|---|---|",
        ]
    )
    for s in report["science_heading_candidates"]:
        values = [
            f"{s['school_name']} · {s['filename']}",
            s["segment_id"],
            s["grade"],
            s["semester"],
            s["subject_heading_raw"],
            locator_label(s["locator"]),
            ", ".join(s["statuses"]),
        ]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    lines.extend(["", "## 판본 대체·충돌", ""])
    versions = [d for d in report["documents"] if d["version_status"] != "single"]
    for d in versions:
        lines.append(
            f"- {d['source']['school_name']} · {d['source']['candidate_name']} — "
            f"{d['version_status']}. {d['version_reason']}."
        )
    if not versions:
        lines.append("판본 비교 대상 없음.")
    for comparison in report["version_comparisons"]:
        lines.append(
            f"- 본문 줄 유사도 {comparison['line_similarity']:.8f}. "
            f"차이 블록 {len(comparison['differences'])}개. "
            "양쪽 변환본 차이 locator와 발췌는 JSON version_comparisons에 기록했다."
        )
    lines.extend(["", "## 전체 문서별 구간", ""])
    for d in report["documents"]:
        lines.extend(
            [
                f"### {d['source']['school_name']} · {d['source']['candidate_name']}",
                "",
                f"문서 ID `{d['document_id']}`",
                "",
                f"변환본 `{d['converted_path']}`",
                "",
                "| 구간 ID | 학년·근거 | 학기 | 머리글 원문 | locator | 상태 |",
                "|---|---|---|---|---|---|",
            ]
        )
        for s in d["segments"]:
            evidence = (
                ", ".join(dict.fromkeys(f"{e['source']}={e['text']}" for e in s["grade_evidence"]))
                or "근거 없음"
            )
            values = [
                s["segment_id"],
                f"{s['grade']} / {evidence}",
                s["semester"],
                s["subject_heading_raw"],
                locator_label(s["locator"]),
                ", ".join(s["statuses"]),
            ]
            lines.append("| " + " | ".join(map(cell, values)) + " |")
    lines.extend(["", "## 학년 미확정 구간 목록", ""])
    for d in report["documents"]:
        for s in d["segments"]:
            if s["grade"] is None:
                lines.append(
                    f"- {d['source']['school_name']} · {d['source']['candidate_name']} — "
                    f"`{s['segment_id']}`. {locator_label(s['locator'])}. "
                    f"{cell(s['subject_heading_raw'])}. {s['review_reason']}."
                )
    lines.extend(["", "## 학기 미확정·충돌 구간 목록", ""])
    for d in report["documents"]:
        for s in d["segments"]:
            if s["semester"] is None:
                evidence = (
                    ", ".join(
                        dict.fromkeys(f"{e['source']}={e['text']}" for e in s["semester_evidence"])
                    )
                    or "학기 근거 없음"
                )
                lines.append(
                    f"- {d['source']['school_name']} · `{s['segment_id']}` — "
                    f"{s['semester_status']}. {evidence}. {locator_label(s['locator'])}."
                )
    lines.extend(["", "## 사람 원문 확인 대상", ""])
    for d in report["documents"]:
        unresolved = [
            s["segment_id"]
            for s in d["segments"]
            if s["grade"] is None or "subject_heading_unresolved" in s["statuses"]
        ]
        if unresolved or d["conversion_status"] != "ok":
            lines.append(
                f"- {d['source']['school_name']} · {d['source']['candidate_name']} — "
                f"학년 또는 머리글 미식별 {len(unresolved)}구간. "
                f"변환 상태 {d['conversion_status']}. 구간 ID·위치는 위 문서 표 참조."
            )
    lines.extend(
        [
            "",
            "정정 표지만 있고 같은 학년의 이전 판이 없는 문서는 single로 보존했다. "
            "비교할 원문 없이 대체 관계를 생성하지 않았다.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round-key", default="2026-round-3")
    parser.add_argument("--roster", type=Path)
    parser.add_argument("--reuse-conversions", action="store_true")
    args = parser.parse_args()
    if not all(c.isalnum() or c == "-" for c in args.round_key):
        parser.error("round key must contain only letters, digits and hyphens")
    manifest = ROOT / "data/derived/schoolinfo_4ga" / args.round_key / "attachments.jsonl"
    rows = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sources = {r["saved_path"]: r for r in rows if r["result"] == "downloaded"}
    raw = ROOT / "data/raw/schoolinfo/4ga_rounds" / args.round_key
    observed = {p.relative_to(ROOT).as_posix() for p in raw.rglob("*") if p.is_file()}
    if observed != set(sources):
        raise ValueError("raw originals and attachment manifest do not reconcile")
    schools = roster_codes(roster_path(ROOT, args.round_key, args.roster))
    sources = {p: r for p, r in sources.items() if str(r["school_code"]) in schools}
    excluded = [
        r for r in sources.values()
        if "-gold" not in args.round_key
        and plan_status(r["candidate_name"]) == "non_plan_filename"
    ]
    plans = [r for r in sources.values() if r not in excluded]
    output = ROOT / "data/derived/segments"
    texts = output / f"{args.round_key}-conversions"
    texts.mkdir(parents=True, exist_ok=True)
    documents = []
    for index, source in enumerate(plans, 1):
        document = audit_document(source, ROOT, texts, reuse=args.reuse_conversions)
        documents.extend(independent_documents(document, ROOT))
        print(f"segments={index}/{len(plans)} {source['school_name']}", flush=True)
    comparisons = resolve_versions(documents)
    for d in documents:
        d.pop("text")
        d["summary"] = summarize_segments(d["segments"])
    report = {
        "schema_version": 1,
        "rule_version": RULE_VERSION,
        "round": args.round_key,
        "roster": roster_path(ROOT, args.round_key, args.roster).relative_to(ROOT).as_posix(),
        "status_definitions": STATUS_DEFINITIONS,
        "documents": documents,
        "excluded_non_plan": excluded,
        "incomplete_sources": [r for r in rows if r["result"] not in {"downloaded", "skipped"}],
        "version_comparisons": comparisons,
        "science_heading_candidates": science_heading_candidates(documents),
        "summary": aggregate(documents),
    }
    atomic_json(output / f"{args.round_key}.json", report)
    atomic_bytes(output / f"{args.round_key}.md", markdown_report(report).encode("utf-8"))
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
