"""Extract bounded batches of filename-confirmed math assessment plans.

The extractor is deterministic and produces provenance-rich JSONL for a later
model pass. It intentionally skips ``unknown`` and generic ``수학`` filename
matches until a content scan is designed for mixed all-subject documents.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from assessment_method_checks import compare_method_rows, pdf_method_rows, structured_method_rows
from math_subject_aliases import curriculum_from_codes, subject_hits

CHECKED_SYMBOLS = frozenset("■☑☒✓✔✅þ▣●√")
EMPTY_SYMBOLS = frozenset("□☐○")
# Union of parser CHECKED_* near METHOD_TERMS and evidence_index SELECTED_BOXES,
# plus the requested radical-shaped check. These are glyph counts, not decisions
# about whether a method was selected. Legacy gfedc font tokens are counted apart.
STATUS_DEFINITIONS = {
    "ok": "변환 완료. PDF는 모든 페이지에 비공백 텍스트층이 있음. 보존 정확도 확정 아님",
    "partial_image": "PDF 일부 페이지에 비공백 텍스트층이 없음(빈 페이지도 포함)",
    "image_only": "PDF 모든 페이지에 비공백 텍스트층이 없음(빈 문서도 포함)",
    "partial": "ZIP에서 일부 자식만 ok. 정상 자식 본문과 개별 상태를 보존",
    "short": "비PDF 변환 결과의 비공백 글자 수가 300 미만(기존 호환 상태)",
    "coverage_unknown": "kordoc PDF 변환은 완료됐으나 PyMuPDF 페이지층 검사가 실패",
    "fallback_text_only": "kordoc PDF 실패 후 PyMuPDF 평문 사용. 표 구조 없음·경계 검토 필요",
    "failed": "원문 읽기 또는 변환 실패. 오류는 error에 기록",
}


def text_metrics(text: str) -> dict:
    return {
        "char_count": len(text),
        "check_count": sum(text.count(symbol) for symbol in CHECKED_SYMBOLS),
        "empty_check_count": sum(text.count(symbol) for symbol in EMPTY_SYMBOLS),
        "check_symbols": {symbol: text.count(symbol) for symbol in sorted(CHECKED_SYMBOLS)},
        "empty_check_symbols": {symbol: text.count(symbol) for symbol in sorted(EMPTY_SYMBOLS)},
        "legacy_checked_tokens": len(re.findall(r"gfedcb", text, re.I)),
        "legacy_empty_tokens": len(re.findall(r"gfedc(?!b)", text, re.I)),
        "science_code_count": text.count("[9과"),
        "science_word_count": text.count("과학"),
    }


def pdf_conversion_status(page_count: int, textless_pages: int) -> str:
    # Textless is an OCR-review proxy, not proof that a page is a scanned image.
    if not page_count:
        return "failed"
    if textless_pages == page_count:
        return "image_only"
    return "partial_image" if textless_pages else "ok"


def convert_pdf(path: Path) -> dict:
    """Read every page. Table/cell counts are unknown for this text-layer reader."""
    try:
        import fitz

        fitz.TOOLS.mupdf_warnings(reset=True)
        pages = []
        texts = []
        method_rows = []
        with fitz.open(path) as document:
            for number, page in enumerate(document, 1):
                text = page.get_text("text")
                has_image = bool(page.get_image_info())
                texts.append(text)
                method_rows.extend(pdf_method_rows(page, number))
                pages.append(
                    {
                        "page": number,
                        **text_metrics(text),
                        "textless": not text.strip(),
                        "has_raster_image": has_image,
                    }
                )
            if __package__:
                from .middle_physical import pdf_surfaces
            else:
                from middle_physical import pdf_surfaces
            surfaces = pdf_surfaces(document)
        text = "\n\n".join(texts)
        textless = sum(page["textless"] for page in pages)
        return {
            "converter": "pymupdf",
            "text": text,
            **text_metrics(text),
            "conversion_status": pdf_conversion_status(len(pages), textless),
            "page_count": len(pages),
            "image_page_count": textless,
            "textless_page_count": textless,
            "raster_image_page_count": sum(page["has_raster_image"] for page in pages),
            "textless_raster_page_count": sum(
                page["textless"] and page["has_raster_image"] for page in pages
            ),
            "table_count": None,
            "cell_count": None,
            "pages": pages,
            "method_rows": method_rows,
            "surfaces": surfaces,
            "warnings": fitz.TOOLS.mupdf_warnings(reset=True),
        }
    except Exception as exc:
        return failed_conversion("pymupdf", exc)


def failed_conversion(converter: str, error: object) -> dict:
    return {
        "converter": converter, "conversion_status": "failed", "text": "",
        **text_metrics(""), "page_count": None, "image_page_count": None,
        "table_count": None, "cell_count": None, "error": str(error),
    }


def extract_pdf_text(path: Path) -> str:
    """Compatibility entry point for callers needing only the PDF text layer."""
    return convert_pdf(path)["text"]


def table_metrics(value: object) -> tuple[int, int]:
    """Count IR table elements (including nested tables), never markdown pipes."""
    tables = cells = 0
    if isinstance(value, dict):
        if value.get("type") == "table":
            tables = 1
            cells = sum(len(row) for row in value.get("table", {}).get("cells", []))
        for child in value.values():
            child_tables, child_cells = table_metrics(child)
            tables += child_tables
            cells += child_cells
    elif isinstance(value, list):
        for child in value:
            child_tables, child_cells = table_metrics(child)
            tables += child_tables
            cells += child_cells
    return tables, cells


def convert_kordoc(
    path: Path, kordoc: Path, cwd: Path, pdf_observation: dict | None = None,
) -> dict:
    with tempfile.TemporaryDirectory(prefix="math_plan_batch_") as temp:
        output = Path(temp) / "parsed.json"
        try:
            command = [str(kordoc), str(path), "--silent", "--format", "json", "-o", str(output)]
            if kordoc.suffix.lower() in {".js", ".mjs"}:
                command.insert(0, "node")
            elif kordoc.name.lower() == "kordoc-fixed.cmd":
                local_cli = cwd / "node_modules" / "kordoc" / "dist" / "cli.js"
                if not local_cli.exists():
                    return failed_conversion("kordoc", f"CLI missing: {local_cli}")
                command = [
                    "node",
                    str(local_cli),
                    str(path),
                    "--silent",
                    "--format", "json",
                    "-o",
                    str(output),
                ]
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            if completed.returncode or not output.exists():
                return failed_conversion(
                    "kordoc", f"exit={completed.returncode}: {completed.stderr[:500]}",
                )
            parsed = json.loads(output.read_text(encoding="utf-8"))
            if not parsed.get("success"):
                return failed_conversion("kordoc", parsed.get("error", "unsuccessful parse"))
            text = parsed["markdown"]
            tables, cells = table_metrics(parsed["blocks"])
            coverage = {}
            status = "ok" if len(text.strip()) >= 300 else "short"
            if path.suffix.lower() == ".pdf":
                observed = pdf_observation if pdf_observation is not None else convert_pdf(path)
                status = observed["conversion_status"]
                if status == "failed":
                    status = "coverage_unknown"
                coverage = {key: observed.get(key) for key in (
                    "page_count", "image_page_count", "textless_page_count",
                    "raster_image_page_count", "textless_raster_page_count",
                )}
                coverage["page_coverage_source"] = "pymupdf"
            return {
                "converter": "kordoc", "text": text, **text_metrics(text),
                "conversion_status": status,
                # HWP/HWPX pageCount means sections, not physical pages.
                "page_count": parsed.get("pageCount") if path.suffix.lower() == ".pdf" else None,
                "section_count": parsed.get("pageCount") if path.suffix.lower() != ".pdf" else None,
                "image_page_count": None, "table_count": tables, "cell_count": cells,
                "warnings": parsed.get("warnings", []), **coverage,
                "method_rows": structured_method_rows(text, parsed["blocks"])
                if path.suffix.lower() == ".pdf" else [],
            }
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError) as exc:
            return failed_conversion("kordoc", exc)


def source_provenance(path: Path, source: dict | None = None) -> dict:
    source = source or {}
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if source.get("sha256") and source["sha256"] != digest:
        raise ValueError(f"source hash mismatch: {path}")
    return {
        "sha256": digest, "original_path": source.get("saved_path", path.as_posix()),
        "edition": {
            key: source[key] for key in (
                "candidate_name", "year", "disclosure_round", "file_seq", "collected_at",
                "source_url", "final_url",
            ) if key in source
        },
    }


def extract_document(
    path: Path, kordoc: Path, cwd: Path, source: dict | None = None,
    *, pdf_converter: str = "pymupdf",
) -> dict:
    """Safe reproduction with additive quality metadata and child provenance.

    extract_status keeps the legacy ok/short/failed vocabulary. conversion_status
    distinguishes PDF coverage and ZIP partial results. Neither certifies layout.
    """
    if pdf_converter not in {"pymupdf", "kordoc"}:
        raise ValueError(f"unknown PDF converter: {pdf_converter}")
    provenance = source_provenance(path, source)
    if path.suffix.lower() == ".zip":
        result = extract_zip(path, kordoc, cwd, pdf_converter=pdf_converter)
    elif path.suffix.lower() == ".pdf":
        result = convert_pdf(path)
        structured = convert_kordoc(path, kordoc, cwd, pdf_observation=result)
        source_provenance(path, {"sha256": provenance["sha256"]})
        if pdf_converter == "kordoc":
            if structured["conversion_status"] != "failed":
                result = {
                    **structured, "pymupdf": result,
                    "method_check_comparison": compare_method_rows(
                        result, structured, provenance["sha256"],
                    ),
                    "table_structure": "html_or_markdown" if structured["table_count"] else (
                        "not_detected"
                    ),
                }
            else:
                result["kordoc"] = structured
                result["text_layer_status"] = result["conversion_status"]
                if result["conversion_status"] != "failed":
                    result["conversion_status"] = "fallback_text_only"
                result["table_structure"] = "unavailable"
            return {
                **result, **provenance,
                "extract_status": "ok" if result["conversion_status"] == "ok" else (
                    "failed" if result["conversion_status"] == "failed" else "short"
                ),
            }
        result["kordoc"] = {key: value for key, value in structured.items() if key != "text"}
        result["table_count"] = structured["table_count"]
        result["cell_count"] = structured["cell_count"]
        # Keep the existing low-text fallback selection. This threshold never
        # decides PDF success, which is based on observed page coverage above.
        if len(result["text"].strip()) < 300 and (
            len(structured["text"].strip()) > len(result["text"].strip())
        ):
            result["text_layer_metrics"] = text_metrics(result["text"])
            result["text"] = structured["text"]
            result["converter"] = "kordoc"
            result.update(text_metrics(result["text"]))
            if result["conversion_status"] == "failed":
                result["conversion_status"] = "coverage_unknown"
    else:
        result = convert_kordoc(path, kordoc, cwd)
    status = result["conversion_status"]
    legacy = "short" if status in {
        "partial", "partial_image", "image_only", "coverage_unknown",
    } else status
    for child in result.get("children", []):
        child["original_path"] = f"{provenance['original_path']}!/{child['member_name']}"
        child["parent_sha256"] = provenance["sha256"]
    return {**result, **provenance, "extract_status": legacy}


def extract_zip(
    path: Path, kordoc: Path, cwd: Path, *, pdf_converter: str = "pymupdf",
) -> dict:
    children = []
    archive_error = None
    with tempfile.TemporaryDirectory(prefix="math_plan_zip_") as temp:
        try:
            with zipfile.ZipFile(path) as archive:
                members = [
                    info for info in archive.infolist()
                    if not info.is_dir()
                    and Path(info.filename).suffix.lower() in {
                        ".hwp", ".hwpx", ".pdf", ".docx", ".xlsx",
                    }
                ]
                if len(members) > 400 or sum(info.file_size for info in members) > 512 * 1024**2:
                    raise ValueError("zip extraction limit exceeded")
                for index, info in enumerate(members):
                    target = Path(temp) / f"{index:05}{Path(info.filename).suffix.lower()}"
                    try:
                        target.write_bytes(archive.read(info))
                        child = extract_document(target, kordoc, cwd, pdf_converter=pdf_converter)
                    except (
                        OSError, RuntimeError, ValueError, NotImplementedError, zipfile.BadZipFile,
                    ) as exc:
                        child = failed_conversion("zip", exc)
                        child["extract_status"] = "failed"
                    child.update(
                        original_path=f"{path.as_posix()}!/{info.filename}",
                        member_name=info.filename, member_index=index,
                        edition={"candidate_name": info.filename},
                    )
                    children.append(child)
        except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
            archive_error = str(exc)
    parts = [
        f"[zip:{child['member_name']}][{child['extract_status']}]\n{child['text']}"
        for child in children if child["text"]
    ]
    status = "failed"
    if parts:
        status = "ok" if not archive_error and all(
            child["conversion_status"] == "ok" for child in children
        ) else "partial"
    text = "\n\n".join(parts)
    return {
        "converter": "zip", "conversion_status": status,
        "text": text, **text_metrics(text), "children": children,
        "error": archive_error,
    }


def extract(path: Path, kordoc: Path, cwd: Path) -> tuple[str, str]:
    """Preserve the tuple interface used by existing math extraction scripts."""
    result = extract_document(path, kordoc, cwd)
    return result["text"], result["extract_status"]


def conversion_metadata(value):
    """Remove text recursively for index-only output, including ZIP children."""
    if isinstance(value, dict):
        return {key: conversion_metadata(child) for key, child in value.items() if key != "text"}
    if isinstance(value, list):
        return [conversion_metadata(child) for child in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--kordoc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--include-generic", action="store_true",
        help="include generic all-subject/grade plan filenames",
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--pdf-converter", choices=("pymupdf", "kordoc"), default="pymupdf")
    parser.add_argument(
        "--index-only", action="store_true",
        help="store subject/status metadata without full text",
    )
    args = parser.parse_args()

    candidates: list[dict[str, str]] = []
    with args.manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("subject_canonical") in {"unknown", "수학"}:
                if not args.include_generic:
                    continue
                if not re.search(
                    r"교수|평가.?계획|전과목|교과별|학년별", row.get("candidate_name", ""),
                ):
                    continue
            if not args.include_generic and row.get("match_type") != "filename_alias":
                continue
            candidates.append(row)
    candidates.sort(key=lambda r: (r["subject_canonical"], r["school_name"], r["candidate_name"]))
    selected = candidates[args.offset : args.offset + args.limit]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    def process(row: dict[str, str]) -> dict[str, object]:
        path = args.project_root / row["saved_path"]
        result = {}
        if not path.exists():
            text, status, digest = f"[missing: {path}]", "missing", ""
        else:
            result = extract_document(
                path, args.kordoc, args.project_root, row, pdf_converter=args.pdf_converter,
            )
            text, status, digest = result["text"], result["extract_status"], result["sha256"]
        hits = subject_hits(text)
        codes = curriculum_from_codes(text)
        return {
            **(conversion_metadata(result) if args.index_only else result),
            "source": row,
            "sha256": digest,
            "extract_status": status,
            "char_count": len(text),
            "subject_hits": hits,
            "curriculum_code_hints": codes,
            "text": "" if args.index_only else text,
        }

    with args.output.open("w", encoding="utf-8") as handle:
        if args.workers > 1:
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                records = pool.map(process, selected)
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        else:
            for row in selected:
                handle.write(json.dumps(process(row), ensure_ascii=False) + "\n")
    print(f"candidate_total={len(candidates)} selected={len(selected)} offset={args.offset}")


if __name__ == "__main__":
    main()
