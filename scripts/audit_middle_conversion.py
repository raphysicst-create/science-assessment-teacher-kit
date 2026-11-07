"""Audit preserved middle-school originals offline, without modifying them."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from collect_schoolinfo_4ga_historical import atomic_bytes, atomic_json
from collect_schoolinfo_4ga_round import plan_status
from extract_math_assessment_batch import (
    CHECKED_SYMBOLS,
    EMPTY_SYMBOLS,
    STATUS_DEFINITIONS,
    convert_kordoc,
    convert_pdf,
    source_provenance,
)

ROOT = Path(__file__).resolve().parents[1]
COMPARISON_FIELDS = ("check_count", "empty_check_count", "science_code_count")


def compare_pdf(direct: dict, structured: dict) -> dict:
    """A failed converter has unknown counts, not evidence of zero source ink."""
    if "failed" in {direct["conversion_status"], structured["conversion_status"]}:
        return {"available": False, "delta": None, "suspected_loss": None}
    delta = {key: structured[key] - direct[key] for key in COMPARISON_FIELDS}
    symbol_delta = {
        symbol: structured["check_symbols"][symbol] - direct["check_symbols"][symbol]
        for symbol in sorted(CHECKED_SYMBOLS)
    }
    empty_delta = {
        symbol: structured["empty_check_symbols"][symbol] - direct["empty_check_symbols"][symbol]
        for symbol in sorted(EMPTY_SYMBOLS)
    }
    return {
        "available": True, "delta": delta,
        "check_symbol_delta": symbol_delta, "empty_check_symbol_delta": empty_delta,
        "suspected_loss": any(value < 0 for value in (
            *delta.values(), *symbol_delta.values(), *empty_delta.values(),
        )),
    }


def audit_document(row: dict, root: Path, kordoc: Path) -> dict:
    path = root / row["saved_path"]
    provenance = source_provenance(path, row)
    record = {
        "school_name": row["school_name"], "school_code": row["school_code"],
        "filename": row["candidate_name"], "format": path.suffix.lower().lstrip("."),
        "size_bytes": path.stat().st_size, **provenance,
        "sha256_prefix": provenance["sha256"][:12],
        "source": row, "reproduction_kind": "안전 변환 재현본",
    }
    if record["size_bytes"] != row["size_bytes"]:
        raise ValueError(f"source size mismatch: {path}")
    if plan_status(row["candidate_name"]) == "non_plan_filename":
        return {**record, "audit_status": "excluded_non_plan", "reason": "비평가계획 문서"}
    converters = {}
    if record["format"] == "pdf":
        converters["pymupdf"] = convert_pdf(path)
    converters["kordoc"] = convert_kordoc(
        path, kordoc, root, pdf_observation=converters.get("pymupdf"),
    )
    if record["format"] == "pdf":
        direct, structured = converters["pymupdf"], converters["kordoc"]
        record["pdf_comparison"] = compare_pdf(direct, structured)
    record["converters"] = {
        name: {key: value for key, value in result.items() if key != "text"}
        for name, result in converters.items()
    }
    # Re-hash after both converters, verifying that originals stayed intact.
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != provenance["sha256"]:
            raise ValueError(f"original changed during conversion: {path}")
    return {**record, "audit_status": "converted"}


def aggregate(documents: list[dict]) -> dict:
    summary = {}
    for kind in sorted({document["format"] for document in documents}):
        rows = [document for document in documents if document["format"] == kind]
        included = [document for document in rows if document["audit_status"] == "converted"]
        summary[kind] = {
            "documents": len(included), "excluded_non_plan": len(rows) - len(included),
            "converters": {
                name: dict(Counter(
                    row["converters"][name]["conversion_status"] for row in included
                    if name in row["converters"]
                )) for name in sorted({name for row in included for name in row["converters"]})
            },
        }
    return summary


def metric_line(result: dict) -> str:
    def value(key):
        observed = result.get(key)
        return "미측정" if observed is None else str(observed)

    return "/".join(value(key) for key in (
        "conversion_status", "char_count", "page_count", "image_page_count",
        "table_count", "check_count", "empty_check_count", "science_code_count",
        "science_word_count",
    ))


def markdown_report(report: dict) -> str:
    lines = [
        "# 중학교 원문 안전 변환 검수", "",
        f"개발용 {report['school_count']}개교. 원문 {len(report['documents'])}개를 대조했다.",
        f"PDF 비교 완료 {report['pdf_comparisons_available']}/{report['pdf_comparison_total']}개. "
        f"전체 변환 완료 여부 {report['conversion_complete']}.",
        "원문과 구별되는 안전 변환 재현본의 관찰 수치이며, 원문에 없는 값은 채우지 않았다.",
        "판본은 수집 목록의 파일명·회차·파일 순번·시각을 그대로 보존했다. "
        "판본 우선순위는 미판정이다.",
        "PDF 이미지 페이지 수는 비공백 텍스트층이 없는 페이지 수로 정의하며 빈 페이지도 포함한다.",
        "JSON의 raster_image_page_count와 textless_raster_page_count는 실제 이미지 개체 관찰 수다.",
        "표·셀 수는 kordoc IR의 중첩 포함 table 요소·셀 개수다. PyMuPDF 표·셀 수는 미측정이다.",
        "HWP/HWPX의 section_count는 물리 페이지 수로 환산하지 않았다.",
        "체크 기호는 방법 선택 여부와 무관한 문서 전체의 문자 출현 수다.",
        "gfedcb/gfedc 글꼴 토큰은 JSON에 별도 기록했다. 코드 수는 정확한 `[9과` 출현 수다.",
        "실패한 변환기의 0자는 추출 결과의 길이이며 원문 문자 수가 아니다. "
        "비교 차이는 미측정 처리한다.",
        "", "## 상태 정의", "",
        *[f"- `{name}` — {definition}" for name, definition in STATUS_DEFINITIONS.items()],
        "", "## 문서별 결과", "",
        "변환기 칸 순서는 상태/글자/페이지/이미지페이지/표/체크/빈체크/[9과/과학이다.",
        "차이는 kordoc − PyMuPDF이며 체크·빈체크·코드 순서다.", "",
        "| 학교 | 파일명 | 형식 | bytes | SHA-256 앞 12자 | PyMuPDF | kordoc | 차이/검수 |",
        "|---|---|---|---:|---|---|---|---|",
    ]
    suspects = []
    unavailable = []
    image_documents = []
    warnings = []
    for document in report["documents"]:
        converters = document.get("converters", {})
        comparison = document.get("pdf_comparison", {})
        decision = document.get("reason", "—")
        identity = f"{document['school_name']} · {document['filename']}"
        if comparison:
            if comparison["available"]:
                decision = "/".join(str(comparison["delta"][key]) for key in COMPARISON_FIELDS)
                if comparison["suspected_loss"]:
                    direct, structured = converters["pymupdf"], converters["kordoc"]
                    evidence = ", ".join(
                        f"{key} {direct[key]}→{structured[key]}" for key in COMPARISON_FIELDS
                    )
                    suspects.append(f"- {identity} — {evidence}. 기호별 차이는 JSON 참조.")
            else:
                decision = "비교 불가"
                errors = [f"{key} {value['error']}" for key, value in converters.items()
                          if value.get("error")]
                baseline = converters.get("pymupdf", {})
                numbers = (
                    f"텍스트층 체크 {baseline.get('check_count', '미측정')}, "
                    f"빈체크 {baseline.get('empty_check_count', '미측정')}, "
                    f"[9과 {baseline.get('science_code_count', '미측정')}. "
                )
                error_text = " / ".join(errors).strip().replace("\n", " ")
                unavailable.append(f"- {identity} — {numbers}{error_text}")
        direct = converters.get("pymupdf", {})
        if direct.get("warnings"):
            warning_text = direct["warnings"].replace("\n", " / ")
            warnings.append(f"- {identity} — {warning_text}")
        if direct.get("image_page_count"):
            image_documents.append(
                f"- {identity} — 전체 {direct['page_count']}, 텍스트층 없음 "
                f"{direct['image_page_count']}, 그중 이미지 개체 있음 "
                f"{direct['textless_raster_page_count']}페이지."
            )
        columns = [
            document["school_name"], document["filename"], document["format"],
            str(document["size_bytes"]), document["sha256_prefix"],
            metric_line(converters["pymupdf"]) if "pymupdf" in converters else "—",
            metric_line(converters["kordoc"]) if "kordoc" in converters else "—", decision,
        ]
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in columns) + " |")
    lines.extend([
        "", "## 손실 의심 목록", "",
        *(suspects or ["수치 감소에 따른 손실 의심 판정 없음. "
                       "비교 미완료 문서는 아래에 열거했다."]),
        "", "## 비교 미완료 목록", "",
        *(unavailable or ["없음."]), "", "## 이미지·빈 페이지 점검", "",
        *(image_documents or ["검수한 PDF에 텍스트층 없는 페이지가 없다."]),
        "", "## 변환기 경고", "", *(warnings or ["기록된 PyMuPDF 경고 없음."]),
        "", "## 형식별 집계", "",
        "| 형식 | 평가계획 문서 | 비평가계획 제외 | 변환기별 상태 |",
        "|---|---:|---:|---|",
    ])
    for kind, counts in report["summary"].items():
        lines.append(
            f"| {kind} | {counts['documents']} | {counts['excluded_non_plan']} | "
            f"{json.dumps(counts['converters'], ensure_ascii=False)} |"
        )
    lines.extend([
        "", "## 해석 범위", "",
        "PDF 텍스트층과 kordoc 사이의 감소는 손실 의심 신호다. "
        "같은 개수도 위치·의미 보존을 입증하지 않는다.",
        "HWP/HWPX는 독립 원문 텍스트 기준이 없어 체크·코드의 보존 여부를 확정할 수 없다.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round-key", default="2026-round-3")
    args = parser.parse_args()
    if args.round_key != Path(args.round_key).name or args.round_key in {".", ".."}:
        parser.error("round key must be a directory name")
    manifest = ROOT / "data/derived/schoolinfo_4ga" / args.round_key / "attachments.jsonl"
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    files = {row["saved_path"]: row for row in rows if row["result"] == "downloaded"}
    raw = ROOT / "data/raw/schoolinfo/4ga_rounds" / args.round_key
    observed = {path.relative_to(ROOT).as_posix() for path in raw.rglob("*") if path.is_file()}
    if observed != set(files):
        raise ValueError("raw originals and attachment manifest do not reconcile")
    kordoc = ROOT / "node_modules/kordoc/dist/cli.js"
    documents = []
    for index, row in enumerate(files.values(), 1):
        documents.append(audit_document(row, ROOT, kordoc))
        print(
            f"audit={index}/{len(files)} {row['school_name']} {row['candidate_name']}", flush=True,
        )
    import fitz

    comparisons = [document["pdf_comparison"] for document in documents
                   if "pdf_comparison" in document]
    report = {
        "schema_version": 1, "round": args.round_key,
        "reproduction_kind": "안전 변환 재현본",
        "school_count": len({row["school_code"] for row in files.values()}),
        "conversion_complete": all(
            result["conversion_status"] != "failed"
            for document in documents for result in document.get("converters", {}).values()
        ),
        "pdf_comparisons_available": sum(comparison["available"] for comparison in comparisons),
        "pdf_comparison_total": len(comparisons),
        "versions": {
            "pymupdf": fitz.VersionBind,
            "kordoc": json.loads(
                (ROOT / "node_modules/kordoc/package.json").read_text(encoding="utf-8"),
            )["version"],
        },
        "status_definitions": STATUS_DEFINITIONS,
        "check_symbols": sorted(CHECKED_SYMBOLS), "empty_check_symbols": sorted(EMPTY_SYMBOLS),
        "documents": documents, "summary": aggregate(documents),
    }
    output = ROOT / "data/derived/conversion_audit"
    output.mkdir(parents=True, exist_ok=True)
    atomic_json(output / f"{args.round_key}.json", report)
    atomic_bytes(output / f"{args.round_key}.md", markdown_report(report).encode("utf-8"))
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
