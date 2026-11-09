"""S18 G5: DRM 평문 문서는 검토 표시로 끝내지 않고 문서 전체를 AI 읽기 대상으로 삼는다.

Verify: .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_s18_plaintext_fallback.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import middle_ai_read as ai  # noqa: E402

DRM_TEXT = "2026학년도 과학과 평가 계획\n수행평가 1 물질의 상태 변화 실험 보고서 30%\n[9과04-01]\n"


def test_drm_plaintext_document_becomes_whole_document_window():
    conversion = {"text": DRM_TEXT, "table_count": 0,
                  "warnings": [{"code": "DRM_COM_FALLBACK", "message": "한컴 COM 평문"}]}
    windows = ai.plaintext_fallback_window(conversion, sections=[])
    assert [(w["line_start"], w["line_end"], w["signals"]) for w in windows] == [(1, 3, ["G5"])]


def test_tableless_science_text_without_science_section_is_read():
    conversion = {"text": DRM_TEXT, "table_count": 0, "warnings": []}
    assert ai.plaintext_fallback_window(conversion, sections=[])


def test_documents_with_tables_or_detected_science_are_not_widened():
    with_tables = {"text": DRM_TEXT, "table_count": 4, "warnings": []}
    assert ai.plaintext_fallback_window(with_tables, sections=[]) == []
    detected = {"text": DRM_TEXT, "table_count": 0, "warnings": []}
    assert ai.plaintext_fallback_window(detected, sections=[{"science_candidate": True}]) == []
    other = {"text": "국어과 평가 계획\n", "table_count": 0, "warnings": []}
    assert ai.plaintext_fallback_window(other, sections=[]) == []
    empty = {"text": "  ", "table_count": 0, "warnings": [{"code": "DRM_COM_FALLBACK"}]}
    assert ai.plaintext_fallback_window(empty, sections=[]) == []
