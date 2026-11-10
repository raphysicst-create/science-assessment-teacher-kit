"""N2b: lone surrogates from converter output must not break hashing, saving or AI input.

Real failure: 2026-round-3-nw2, 대전대신중학교 "2026학년도 2학기 3학년 교수학습 계획.pdf",
kordoc text position 21693: "창의U+DFB3융합" (a middle-dot glyph decoded as a lone surrogate).
Run: pytest -q services/math-assessment-api/tests/test_n2b_surrogates.py
"""

import hashlib
import importlib
import json
import subprocess
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]
REAL_FRAGMENT = "r>▶ 문제해결, 창의\udfb3융합, 의사소"


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    return (importlib.import_module("text_clean"),
            importlib.import_module("extract_math_assessment_batch"),
            importlib.import_module("assessment_method_checks"))


def test_real_fragment_fails_before_and_encodes_after(modules):
    text_clean, _, checks = modules
    with pytest.raises(UnicodeEncodeError):
        REAL_FRAGMENT.encode("utf-8")
    cleaned = text_clean.clean_text(REAL_FRAGMENT)
    assert cleaned == "r>▶ 문제해결, 창의�융합, 의사소"
    cleaned.encode("utf-8")
    result = checks.compare_method_rows({"method_rows": []},
                                        {"text": cleaned, "method_rows": []}, "sha")
    assert result["structured_text_sha256"] == hashlib.sha256(cleaned.encode()).hexdigest()


def test_text_without_surrogates_is_the_same_object_and_hash(modules):
    # Bundle 1 caches stay valid: unchanged text keeps its identity and SHA-256.
    text_clean = modules[0]
    text = "주기율표 작성하기 ■서술·논술 □구술·발표 😀 (valid pair)"
    assert text_clean.clean_text(text) is text
    tree = {"markdown": text, "blocks": [{"text": text}]}
    assert text_clean.clean_tree(tree) == tree


def test_kordoc_json_escape_is_cleaned_in_converter(modules, tmp_path, monkeypatch):
    _, extract, _ = modules
    source = tmp_path / "plan.hwpx"
    source.write_bytes(b"not used")
    payload = '{"success": true, "markdown": "' + "가" * 300 + ' 창의\\udfb3융합", "blocks": []}'

    def fake_run(command, **kwargs):
        Path(command[command.index("-o") + 1]).write_text(payload, encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(extract.subprocess, "run", fake_run)
    result = extract.convert_kordoc(source, tmp_path / "cli.js", tmp_path)
    assert result.get("conversion_status") != "failed", result
    assert "창의�융합" in result["text"]
    hashlib.sha256(result["text"].encode("utf-8")).hexdigest()
    json.dumps(result, ensure_ascii=False).encode("utf-8")


def test_reused_conversion_cache_is_cleaned(modules):
    text_clean = modules[0]
    cached = json.loads('{"text": "창의\\udfb3융합", "sha256": "x"}')
    assert text_clean.clean_tree(cached)["text"].encode("utf-8") == "창의�융합".encode()
