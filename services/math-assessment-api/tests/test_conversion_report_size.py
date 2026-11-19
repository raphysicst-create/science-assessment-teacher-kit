"""The conversion report keeps PDF line layout only as a count; checks still see it.

Run: .venv/Scripts/python.exe -m pytest -q \
    services/math-assessment-api/tests/test_conversion_report_size.py
Why: PDF line layout (`surfaces`) was 94% of the report and passed 4 GB per round
on nw5/nw6 (11-19). Nothing reads it back from the report.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import audit_middle_conversion as audit  # noqa: E402

SURFACES = [{"height": 841, "lines": [{"text": "가. 과제", "bbox": [1, 2, 3, 4]}]}] * 3


def observation(converter):
    return {
        "converter": converter, "text": "본문", "conversion_status": "ok", "char_count": 2,
        "check_count": 1, "empty_check_count": 0, "science_code_count": 0,
        "check_symbols": {s: 0 for s in audit.CHECKED_SYMBOLS},
        "empty_check_symbols": {s: 0 for s in audit.EMPTY_SYMBOLS},
        "method_rows": [], "surfaces": SURFACES,
    }


def test_report_converter_drops_text_and_counts_surfaces():
    kept = audit.report_converter(observation("pymupdf"))
    assert "text" not in kept and "surfaces" not in kept
    assert kept["surface_count"] == 3 and kept["check_count"] == 1


def test_report_converter_without_surfaces_adds_no_count():
    assert "surface_count" not in audit.report_converter({"text": "x", "char_count": 1})


def test_pdf_document_record_has_count_and_method_check_saw_surfaces(tmp_path, monkeypatch):
    pdf = tmp_path / "plan.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    seen = []

    def compare(direct, structured, sha):
        seen.append(len(direct["surfaces"]))
        return {"rows": []}

    monkeypatch.setattr(audit, "convert_pdf", lambda path: observation("pymupdf"))
    monkeypatch.setattr(audit, "convert_kordoc", lambda *a, **k: observation("kordoc"))
    monkeypatch.setattr(audit, "compare_method_rows", compare)
    row = {"saved_path": "plan.pdf", "school_name": "가중", "school_code": "S1",
           "candidate_name": "2026 평가계획.pdf", "size_bytes": pdf.stat().st_size}
    record = audit.audit_document(row, tmp_path, Path("kordoc.js"))
    assert seen == [3]
    for converter in record["converters"].values():
        assert "surfaces" not in converter and converter["surface_count"] == 3
    assert record["pdf_comparison"]["available"] is True
