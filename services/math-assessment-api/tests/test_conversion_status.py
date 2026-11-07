"""Offline conversion checks using generated documents, never school originals."""

import csv
import hashlib
import importlib
import json
import struct
import zipfile
import zlib
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

PROJECT = Path(__file__).resolve().parents[3]


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    return SimpleNamespace(
        extract=importlib.import_module("extract_math_assessment_batch"),
        semester=importlib.import_module("build_schoolinfo_4ga_semester"),
        collector=importlib.import_module("collect_schoolinfo_4ga_round"),
        audit=importlib.import_module("audit_middle_conversion"),
    )


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("conversion tests must never use the network")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def png_pixel():
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
            + chunk(b"IEND", b""))


def make_pdf(path, page_types):
    with fitz.open() as document:
        for kind in page_types:
            page = document.new_page()
            if kind == "text":
                page.insert_text((50, 60), "Synthetic assessment plan")
            elif kind == "image":
                page.insert_image(fitz.Rect(0, 0, 100, 100), stream=png_pixel())
        document.save(path)


def mock_kordoc(monkeypatch, modules):
    def run(command, **kwargs):
        path = Path(command[command.index("-o") + 1])
        source = Path(command[2])
        if source.suffix == ".hwp":
            return SimpleNamespace(returncode=1, stderr="synthetic broken HWP")
        path.write_text(json.dumps({
            "success": True, "markdown": "Synthetic assessment plan",
            "blocks": [], "pageCount": 1,
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(modules.extract.subprocess, "run", run)


def test_zip_keeps_successful_children_and_semester_text(tmp_path, modules, monkeypatch):
    mock_kordoc(monkeypatch, modules)
    pdf = tmp_path / "plan.pdf"
    make_pdf(pdf, ["text"])
    archive = tmp_path / "plans.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("2026학년도 2학기 평가계획.pdf", pdf.read_bytes())
        output.writestr("학업성적관리규정.hwp", b"broken synthetic HWP")
        output.writestr("another.pdf", pdf.read_bytes())
    source = {
        "saved_path": str(archive), "candidate_name": "2026학년도 2학기 평가계획.zip",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "year": 2026, "disclosure_round": 3, "file_seq": "42",
    }
    result = modules.extract.extract_document(archive, Path("cli.js"), tmp_path, source)
    assert result["conversion_status"] == "partial"
    assert result["extract_status"] == "short"
    assert [child["extract_status"] for child in result["children"]] == ["ok", "failed", "ok"]
    assert result["text"].count("Synthetic assessment plan") == 2
    child = result["children"][0]
    assert child["sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert child["member_name"] in child["original_path"]
    assert child["parent_sha256"] == source["sha256"]
    assert child["text"]
    assert result["sha256"] == source["sha256"]
    assert result["edition"]["file_seq"] == "42"
    preserved = modules.semester.confirmed_extraction(source, result)
    assert preserved["text"] == result["text"]
    assert preserved["sha256"] == source["sha256"]
    assert preserved["edition"]["candidate_name"] == source["candidate_name"]
    assert modules.semester.semester_status(
        source["candidate_name"], preserved["text"], 2, 2026,
    ) == "confirmed"
    text, legacy_status = modules.extract.extract(archive, Path("cli.js"), tmp_path)
    assert text == result["text"]
    assert legacy_status == "short"


@pytest.mark.parametrize(("page_types", "status", "textless", "raster"), [
    (["text"], "ok", 0, 0),
    (["text", "image"], "partial_image", 1, 1),
    (["image"], "image_only", 1, 1),
    (["text", "blank"], "partial_image", 1, 0),
])
def test_pdf_page_coverage(tmp_path, modules, page_types, status, textless, raster):
    path = tmp_path / "synthetic.pdf"
    make_pdf(path, page_types)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result = modules.extract.convert_pdf(path)
    assert result["conversion_status"] == status
    assert result["page_count"] == len(page_types)
    assert result["image_page_count"] == textless
    assert result["textless_raster_page_count"] == raster
    assert result["raster_image_page_count"] == raster
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    if status == "ok":
        assert result["char_count"] < 300  # Coverage, not the old character threshold.


def test_partial_pdf_status_through_normal_entry_point(tmp_path, modules, monkeypatch):
    mock_kordoc(monkeypatch, modules)
    path = tmp_path / "partial.pdf"
    make_pdf(path, ["text", "image"])
    result = modules.extract.extract_document(path, Path("cli.js"), tmp_path)
    assert result["conversion_status"] == "partial_image"
    assert result["extract_status"] == "short"
    assert result["text"]
    assert result["table_count"] == 0


def test_pdf_preserves_kordoc_low_text_fallback(tmp_path, modules, monkeypatch):
    path = tmp_path / "recoverable.pdf"
    make_pdf(path, ["blank"])
    text = "Recovered synthetic PDF text " * 20
    structured = {
        "text": text, **modules.extract.text_metrics(text),
        "conversion_status": "image_only", "table_count": 2, "cell_count": 4,
    }
    monkeypatch.setattr(modules.extract, "convert_kordoc", lambda *a, **kw: structured)
    result = modules.extract.extract_document(path, Path("cli.js"), tmp_path)
    assert result["text"] == text
    assert result["converter"] == "kordoc"
    assert result["text_layer_metrics"]["char_count"] == 0
    assert result["conversion_status"] == "image_only"
    assert result["extract_status"] == "short"


def test_science_pdf_prefers_tables_and_keeps_text_layer(tmp_path, modules, monkeypatch):
    path = tmp_path / "science.pdf"
    make_pdf(path, ["text"])
    html = '<table><tr><td>☑ 실험</td><td>[9과01-01]</td></tr></table>'

    def run(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_text(json.dumps({
            "success": True, "markdown": html, "pageCount": 1,
            "blocks": [{"type": "table", "table": {"cells": [[{}, {}]]}}],
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(modules.extract.subprocess, "run", run)
    result = modules.extract.extract_document(
        path, Path("cli.js"), tmp_path, pdf_converter="kordoc",
    )
    assert result["text"] == html
    assert result["converter"] == "kordoc"
    assert result["conversion_status"] == "ok"
    assert result["table_count"] == 1
    assert result["cell_count"] == 2
    assert result["pymupdf"]["text"].startswith("Synthetic")
    assert result["pymupdf"]["pages"][0]["page"] == 1
    assert result["science_code_count"] == result["check_count"] == 1
    # Above the legacy 300-character threshold math keeps the text layer.
    direct = {**result["pymupdf"], "text": "Synthetic assessment plan " * 20}
    direct.update(modules.extract.text_metrics(direct["text"]))
    monkeypatch.setattr(modules.extract, "convert_pdf", lambda *a: dict(direct))
    legacy = modules.extract.extract_document(path, Path("cli.js"), tmp_path)
    assert legacy["converter"] == "pymupdf"
    assert legacy["text"] == direct["text"]


@pytest.mark.parametrize("corrupt", [False, True])
def test_science_pdf_fallback_distinguishes_flat_text_and_total_failure(
    tmp_path, modules, monkeypatch, corrupt,
):
    path = tmp_path / "science.pdf"
    if corrupt:
        path.write_bytes(b"synthetic corrupt PDF")
    else:
        make_pdf(path, ["text"])
    monkeypatch.setattr(modules.extract.subprocess, "run", lambda *a, **kw: (
        SimpleNamespace(returncode=1, stderr="synthetic kordoc failure")
    ))
    result = modules.extract.extract_document(
        path, Path("cli.js"), tmp_path, pdf_converter="kordoc",
    )
    assert result["converter"] == "pymupdf"
    assert result["conversion_status"] == ("failed" if corrupt else "fallback_text_only")
    assert result["extract_status"] == ("failed" if corrupt else "short")
    assert result["table_structure"] == "unavailable"
    assert result["table_count"] is None
    assert "synthetic kordoc failure" in result["kordoc"]["error"]


def test_science_pdf_selection_propagates_into_zip(tmp_path, modules, monkeypatch):
    path = tmp_path / "science.pdf"
    make_pdf(path, ["text"])
    archive = tmp_path / "science.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("science.pdf", path.read_bytes())
    mock_kordoc(monkeypatch, modules)
    result = modules.extract.extract_document(
        archive, Path("cli.js"), tmp_path, pdf_converter="kordoc",
    )
    child = result["children"][0]
    assert child["converter"] == "kordoc"
    assert child["pymupdf"]["text"]
    assert child["original_path"].endswith("!/science.pdf")
    assert child["parent_sha256"] == result["sha256"]


def test_hash_mismatch_rejected_before_conversion(tmp_path, modules):
    path = tmp_path / "synthetic.hwp"
    path.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="source hash mismatch"):
        modules.extract.extract_document(path, Path("cli.js"), tmp_path, {"sha256": "0" * 64})


@pytest.mark.parametrize("filename", [
    "2026학년도 양평중 제규정집_0421(최종).pdf", "2026 규정집.pdf",
    "제 규정집.pdf", "학업성적관리규정.hwp",
])
def test_non_plan_filename_excluded(modules, filename):
    assert modules.collector.plan_status(filename) == "non_plan_filename"


def test_combined_plan_filename_still_supported(modules):
    assert modules.collector.plan_status("2학기 평가계획 및 학업성적관리규정.pdf") == (
        "second_semester_filename"
    )


def test_downloaded_regulations_marked_without_conversion(tmp_path, modules, monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("non-plan originals must be excluded before conversion")

    monkeypatch.setattr(modules.audit, "convert_pdf", fail)
    monkeypatch.setattr(modules.audit, "convert_kordoc", fail)
    path = tmp_path / "regulations.pdf"
    path.write_bytes(b"synthetic regulations")
    row = {
        "saved_path": path.name, "candidate_name": "제규정집.pdf",
        "school_name": "가상중학교", "school_code": "SYNTHETIC",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }
    result = modules.audit.audit_document(row, tmp_path, Path("cli.js"))
    assert result["audit_status"] == "excluded_non_plan"
    assert result["reason"] == "비평가계획 문서"
    assert path.read_bytes() == b"synthetic regulations"


def test_ir_table_elements_include_nested_tables(modules):
    nested = {"type": "table", "table": {"cells": [[{"text": "nested"}]]}}
    blocks = [{"type": "table", "table": {"cells": [[{"blocks": [nested]}]]}}]
    assert modules.extract.table_metrics(blocks) == (2, 2)


def test_symbols_and_code_loss_comparison(modules):
    direct = {**modules.extract.text_metrics("☑ ■ ▣ √ ✔ ✓ ● ✅ þ ☒ □ ☐ ○ [9과01-01] 과학"),
              "conversion_status": "ok"}
    converted = {**modules.extract.text_metrics("□ ☐ [9과01-01] 과학"), "conversion_status": "ok"}
    assert direct["check_count"] == 10
    assert direct["empty_check_count"] == 3
    comparison = modules.audit.compare_pdf(direct, converted)
    assert comparison["delta"]["check_count"] == -10
    assert comparison["delta"]["science_code_count"] == 0
    assert comparison["suspected_loss"]
    # Equal aggregate counts can conceal substitutions, so compare each glyph too.
    converted = {**modules.extract.text_metrics("■"), "conversion_status": "ok"}
    direct = {**modules.extract.text_metrics("☑"), "conversion_status": "ok"}
    assert modules.audit.compare_pdf(direct, converted)["suspected_loss"]
    failed = modules.extract.failed_conversion("kordoc", "missing optional dependency")
    assert modules.audit.compare_pdf(direct, failed) == {
        "available": False, "delta": None, "suspected_loss": None,
    }


def test_corrupt_pdf_and_zip_are_failed(tmp_path, modules):
    for suffix in (".pdf", ".zip"):
        path = tmp_path / f"corrupt{suffix}"
        path.write_bytes(b"synthetic corrupt document")
        result = (modules.extract.convert_pdf(path) if suffix == ".pdf"
                  else modules.extract.extract_zip(path, Path("cli.js"), tmp_path))
        assert result["conversion_status"] == "failed"
        assert result["error"]


def test_zip_read_failure_does_not_stop_later_child(tmp_path, modules, monkeypatch):
    mock_kordoc(monkeypatch, modules)
    pdf = tmp_path / "plan.pdf"
    make_pdf(pdf, ["text"])
    archive = tmp_path / "read-error.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("broken.pdf", b"synthetic")
        output.writestr("good.pdf", pdf.read_bytes())
    original_read = zipfile.ZipFile.read

    def read(self, member, *args, **kwargs):
        if member.filename == "broken.pdf":
            raise zipfile.BadZipFile("synthetic CRC failure")
        return original_read(self, member, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "read", read)
    result = modules.extract.extract_document(archive, Path("cli.js"), tmp_path)
    assert result["conversion_status"] == "partial"
    assert result["children"][0]["extract_status"] == "failed"
    assert result["children"][1]["extract_status"] == "ok"
    assert "Synthetic assessment plan" in result["text"]


@pytest.mark.parametrize("index_only", [False, True])
def test_batch_entry_point_keeps_metadata_and_index_only_contract(
    tmp_path, modules, monkeypatch, index_only,
):
    mock_kordoc(monkeypatch, modules)
    pdf = tmp_path / "synthetic.pdf"
    make_pdf(pdf, ["text"])
    archive = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("plan.pdf", pdf.read_bytes())
        output.writestr("broken.hwp", b"broken")
    manifest = tmp_path / "manifest.csv"
    row = {
        "subject_canonical": "대수", "match_type": "filename_alias",
        "school_name": "가상중학교", "candidate_name": "2학기 평가계획.zip",
        "saved_path": archive.name,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    with manifest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    output = tmp_path / "result.jsonl"
    argv = [
        "extract", "--manifest", str(manifest), "--project-root", str(tmp_path),
        "--kordoc", str(tmp_path / "cli.js"), "--output", str(output),
    ]
    if index_only:
        argv.append("--index-only")
    monkeypatch.setattr("sys.argv", argv)
    modules.extract.main()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["sha256"] == row["sha256"]
    assert result["original_path"] == archive.name
    assert result["edition"]["candidate_name"] == row["candidate_name"]
    assert result["conversion_status"] == "partial"
    assert result["extract_status"] == "short"
    assert result["char_count"] > 0
    assert bool(result["text"]) != index_only
    assert ("text" in result["children"][0]) != index_only


def test_cached_child_provenance_rebound_per_source(tmp_path, modules):
    source = tmp_path / "same-content.zip"
    source.write_bytes(b"synthetic shared content")
    row = {
        "saved_path": str(source), "candidate_name": "별도 판본.zip", "file_seq": "99",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
    cached = {
        "text": "preserved", "extract_status": "short", "conversion_status": "partial",
        "children": [{"original_path": "other.zip!/plan.pdf", "member_name": "plan.pdf",
                      "text": "preserved", "sha256": "child-digest"}],
    }
    result = modules.semester.confirmed_extraction(row, cached)
    assert result["children"][0]["original_path"] == f"{source}!/plan.pdf"
    assert result["children"][0]["sha256"] == "child-digest"
    assert result["edition"]["file_seq"] == "99"
    assert cached["children"][0]["original_path"] == "other.zip!/plan.pdf"


@pytest.mark.parametrize(
    "converted_marker,status", [("", "loss"), ("[ ]", "conflict"), ("[V]", "matched")]
)
def test_pdf_method_comparison_reaches_s6_through_normal_conversion(
    tmp_path,
    modules,
    monkeypatch,
    converted_marker,
    status,
):
    path = tmp_path / "method.pdf"
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((40, 60), "평가방법", fontname="korea", fontsize=10)
        page.insert_text((100, 60), "[V] 논술형 [ ] 프로젝트", fontname="korea", fontsize=10)
        page.insert_text((40, 100), "평가시기", fontname="korea", fontsize=10)
        document.save(path)
    rows = [
        ["평가영역", "합성 탐구"],
        ["평가방법", f"{converted_marker} 논술형 [ ] 프로젝트"],
        ["평가시기", "10월"],
    ]
    html = (
        "<table>"
        + "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
        + "</table>"
    )

    def run(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_text(
            json.dumps(
                {
                    "success": True,
                    "markdown": html,
                    "pageCount": 1,
                    "blocks": [
                        {
                            "type": "table",
                            "pageNumber": 1,
                            "table": {
                                "cells": [[{"text": cell} for cell in row] for row in rows],
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(modules.extract.subprocess, "run", run)
    converted = modules.extract.extract_document(
        path, Path("cli.js"), tmp_path, pdf_converter="kordoc"
    )
    comparison = converted["method_check_comparison"]
    assert comparison["rows"][0]["status"] == status
    assert comparison["rows"][0]["one_to_one"]
    assert comparison["rows"][0]["source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    stored = tmp_path / "conversion.json"
    stored.write_text(json.dumps(converted), encoding="utf-8")
    middle = importlib.import_module("scripts.middle_items")
    section = {
        "document_id": "doc_synthetic",
        "segment_id": "seg_synthetic",
        "section_id": "subj_synthetic",
        "grade": 1,
        "semester": 2,
        "status": "target",
        "boundary_verified": True,
        "header": {"key": "과학", "raw": "과학"},
        "locator": {"start": 0, "end": len(html)},
    }
    item = middle.extract_middle_items(html, section, json.loads(stored.read_text("utf-8")))[0]
    method = item["fields"]["method"]
    assert method["conversion_comparison"][0]["status"] == status
    if status == "matched":
        assert method["value"] == ["논술형"]
        assert item["extraction_status"] == "bounded"
    else:
        assert method["state"] == "conversion_loss"
        assert method["value"] == []
        assert method["status"] == "unconfirmed"
        assert item["extraction_status"] == "review"


@pytest.mark.parametrize("problem", ["page", "duplicate_row", "duplicate_label", "label_conflict"])
def test_method_comparison_requires_unambiguous_same_page_labels(modules, problem):
    checks = importlib.import_module("assessment_method_checks")
    options = checks.row_options("[V] 논술형 [ ] 프로젝트")
    source = {"page": 1, "raw": "[V] 논술형 [ ] 프로젝트", "options": options}
    target = {
        "page": 1,
        "raw": "논술형 프로젝트",
        "options": checks.row_options("논술형 프로젝트"),
        "locator": {"start": 10, "end": 20},
    }
    sources = [source]
    if problem == "page":
        target["page"] = 2
    elif problem == "duplicate_row":
        sources = [source, dict(source)]
    elif problem == "duplicate_label":
        source["options"] = options + options
        target["options"] = options + options
    else:
        target["options"] = checks.row_options("논술형 실험·실습")
    comparison = checks.compare_method_rows(
        {"method_rows": sources}, {"method_rows": [target]}, "digest"
    )
    row = comparison["rows"][0]
    assert not row["one_to_one"]
    assert row["status"] in {"unmapped", "conflict"}
    assert row["action"] != "supplement"


def test_document_symbol_delta_does_not_create_method_loss(modules):
    checks = importlib.import_module("assessment_method_checks")
    direct = {**modules.extract.text_metrics("■" * 100), "method_rows": []}
    structured = {**modules.extract.text_metrics(""), "method_rows": []}
    assert checks.compare_method_rows(direct, structured, "digest")["rows"] == []
