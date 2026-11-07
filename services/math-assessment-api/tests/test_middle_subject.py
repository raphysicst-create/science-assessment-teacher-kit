"""S5 subject boundaries and compatibility, using synthetic inputs only."""

import hashlib
import importlib
import json
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT))
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))

    def fail(*args, **kwargs):
        pytest.fail("S5 tests must never use the network")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


@pytest.fixture
def subjects():
    return importlib.import_module("scripts.middle_subjects")


def record(text, filename="2026학년도 중1 2학기 평가계획.hwp"):
    return {
        "text": text,
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "extract_status": "ok",
        "source": {"candidate_name": filename},
    }


def sections(text, filename="2026학년도 중1 2학기 평가계획.hwp"):
    segmenter = importlib.import_module("scripts.middle_segments")
    subjects = importlib.import_module("scripts.middle_subjects")
    source_record = record(text, filename)
    parents = segmenter.segment_document(
        {**source_record["source"], "sha256": source_record["sha256"]},
        {"text": text, "converter": "synthetic", "conversion_status": "ok"},
    )
    return subjects.subject_sections(text, parents)


@pytest.mark.parametrize(
    "text",
    [
        "과학",
        "# 과학",
        "## 과학",
        "<과학>",
        "[과학]",
        "(과학)",
        "과목: 과학",
        "과목명: 과학",
        "교과: 과학",
        "1. 과학",
        "과학과 평가 계획",
        "과학 교수·학습 및 평가 계획",
        "2026학년도 1학년 2학기 과학과 교수학습 및 평가 계획",
        "[9과01-01] 합성 성취기준",
        "[ 9 과 01-01 ] 합성 기준",
    ],
)
def test_fifteen_positive_subject_sentences(subjects, text):
    assert subjects.science_hits(text)[0]["subject"] == "과학"


@pytest.mark.parametrize(
    "text",
    [
        "[9체01-01] 운동의 과학적 원리를 설명한다.",
        "[9도01-01] 과학기술의 윤리적 쟁점을 토론한다.",
        "과학의 날 행사 계획",
        "과학실 안전",
        "과학관 견학",
        "과학 동아리 계획",
        "과학고 진학 안내",
        "과학적인 태도",
        "과학기술 발달",
        "과학실험 동아리",
        "체육에서 과학을 활용한다.",
        "도덕 시간에 과학의 역할을 토론한다.",
        "생활 속 과학적 원리",
        "기술·가정과 교수학습 및 평가 계획",
        "교수학습 평가 계획",
    ],
)
def test_fifteen_negative_subject_sentences(subjects, text):
    assert subjects.science_hits(text) == []


def test_all_middle_prefixes_and_unknown_are_visible(subjects):
    text = " ".join(f"[9{p}01-01]" for p in subjects.MIDDLE_SUBJECT_PREFIXES)
    codes = subjects.code_evidence(text + " [9가상01-01]", 100)
    assert {c["prefix"] for c in codes[:-1]} == set(subjects.MIDDLE_SUBJECT_PREFIXES)
    assert codes[-1]["kind"] == "unknown_code"
    assert codes[0]["start"] == 100
    assert subjects.classify_subject("[9가상01-01]")["status"] == "unknown"
    assert subjects.classify_subject("[9과01-01] [9가상01-01]")["status"] == "unknown"
    mixed = subjects.classify_subject("[9과01-01] [9도01-01] [9가상01-01]")
    assert mixed["status"] == "mixed" and "unknown_code" in mixed["reasons"]


def test_same_item_mixed_and_between_item_mixed_are_distinct(subjects):
    science = subjects.classify_subject("[9과01-01]")
    moral = subjects.classify_subject("[9도01-01]")
    mixed = subjects.classify_subject("[9과01-01] [9도01-01]")
    assert mixed["status"] == "mixed"
    between = subjects.classify_table([science, moral])
    within = subjects.classify_table([mixed])
    assert between["status"] == within["status"] == "mixed"
    assert between["between_items_mixed"] and not between["within_item_mixed"]
    assert within["within_item_mixed"] and not within["between_items_mixed"]


def test_other_subject_codes_only(subjects):
    assert subjects.classify_subject("<table>[9체01-01] [9도01-01]</table>")["status"] == "other"


def test_science_then_uncoded_technology_table_is_other():
    text = (
        "과학과 교수학습 및 평가 계획\n[9과01-01] 관찰\n"
        "기술·가정과 교수학습 및 평가 계획\n"
        "<table><tr><td>합성 생활 설계</td></tr></table>"
    )
    decisions = sections(text)
    assert [s["status"] for s in decisions] == ["target", "other"]
    assert decisions[0]["locator"]["end"] == text.index("기술·가정과")
    assert not decisions[1]["codes"]


def test_bare_other_heading_also_ends_science():
    decisions = sections("과학\n[9과01-01]\n기술·가정\n| 설계 | 활동 |\n")
    assert [s["status"] for s in decisions] == ["target", "other"]


def test_uncoded_science_requires_verified_boundary(subjects):
    assert subjects.classify_subject("관찰 기록 P")["status"] == "unknown"
    decision = sections("과학과 평가 계획\n관찰 기록 P")[0]
    assert decision["status"] == "target" and decision["boundary_verified"]


def test_valid_bare_boundary_with_other_codes_keeps_uncoded_science():
    decisions = sections("과학\n관찰 기록 P\n기술·가정\n[9기가01-01]\n")
    assert [s["status"] for s in decisions] == ["target", "other"]


def test_prose_line_break_subject_word_does_not_become_heading():
    text = "과학과 평가 계획\n과학과 지속가능한\n사회\n과학적 탐구 방법\n[9과01-01]"
    decisions = sections(text)
    assert len(decisions) == 1 and decisions[0]["boundary_verified"]


def test_html_subject_label_and_uncoded_next_subject(subjects):
    text = (
        "<table><tr><th>교과</th><td>과학</td></tr></table>\n관찰 기록 P\n"
        "<table><tr><th>교과</th><td>기술·가정</td></tr></table>\n설계 활동"
    )
    decisions = sections(text)
    assert [s["status"] for s in decisions] == ["target", "other"]
    assert subjects.science_hits(text)


def test_headerless_anchor_and_uncoded_tail_review():
    text = "1학년\n<table><tr><td>[9과01-01] 관찰</td></tr></table>\n설계 활동\n"
    decisions = sections(text)
    target = [s for s in decisions if s["status"] == "target"]
    assert len(target) == 1
    assert target[0]["boundary_method"] == "code_anchor_candidate"
    assert not target[0]["boundary_verified"]
    assert decisions[-1]["status"] == "unknown"


def test_missing_science_heading_after_other_heading():
    text = (
        "국어과 평가 계획\n<table><tr><td>[9국01-01]</td></tr></table>\n"
        "<table><tr><td>[9과01-01]</td></tr></table>\n무코드 후속 표\n"
    )
    decisions = sections(text)
    target = [s for s in decisions if s["status"] == "target"]
    assert len(target) == 1 and not target[0]["boundary_verified"]


def test_all_science_sections_indexed_and_s4_ids_linked():
    indexer = importlib.import_module("scripts.build_math_assessment_evidence_index")
    text = (
        "1학년\n과학과 평가 계획\n[9과01-01]\n"
        "2학년\n과학과 평가 계획\n[9과02-01]\n"
        "3학년\n과학과 평가 계획\n[9과03-01]\n"
    )
    rows = indexer.evidence_records(record(text, "2026학년도 2학기 합본.hwp"), "science")
    assert [r["subject_decision"]["grade"] for r in rows] == [1, 2, 3]
    assert len({r["section_id"] for r in rows}) == 3
    assert all(r["segment_id"].startswith("seg_") for r in rows)
    assert all(r["public_eligible"] is False for r in rows)
    assert "grade3_quarantined" in rows[-1]["subject_decision"]["parent_statuses"]


@pytest.mark.parametrize("marker", ["자유학기", "과정 중심 평가", "관찰 기록", "P"])
def test_free_semester_survives_index_and_shortlist(marker):
    indexer = importlib.import_module("scripts.build_math_assessment_evidence_index")
    shortlist = importlib.import_module("scripts.build_strict_math_shortlist")
    rows = indexer.evidence_records(record(f"과학과 평가 계획\n{marker}\n"), "science")
    assert len(rows) == 1
    assert rows[0]["marker_counts"]["performance_assessment"] == 0
    assert rows[0]["free_semester_markers"]
    assert shortlist.evidence_strength(rows[0], "science")[0] >= 4
    assert shortlist.assessment_markers(rows[0]) == ["free_semester_marker"]


def test_index_uses_supplied_s4_and_preserves_raw_offsets():
    indexer = importlib.import_module("scripts.build_math_assessment_evidence_index")
    text = "합성@example.test\n과학과 평가 계획\n[9과01-01]\n"
    parent = {
        "segment_id": "seg_supplied",
        "document_id": "doc_supplied",
        "grade": 2,
        "subject_heading_key": "과학",
        "subject_heading_raw": "과학과 평가 계획",
        "locator": {"start": text.index("과학과"), "end": len(text)},
    }
    rows = indexer.evidence_records({**record(text), "segments": [parent]}, "science")
    assert rows[0]["segment_id"] == "seg_supplied"
    assert rows[0]["section_locator"]["start"] == text.index("과학과")
    assert rows[0]["subject_decision"]["codes"][0]["start"] == text.index("[9과")
    parent["text_sha256"] = "stale"
    with pytest.raises(ValueError, match="hash mismatch"):
        indexer.evidence_records({**record(text), "segments": [parent]}, "science")


def test_pdf_anchor_candidate_has_its_own_page_locator(subjects):
    text = "1학년\n설명\n\n[9과01-01]\n"
    parent = {
        "segment_id": "seg_synthetic",
        "grade": 1,
        "locator": {"start": 0, "end": len(text), "pages": [1, 2]},
    }
    conversion = {
        "converter": "pymupdf",
        "pages": [{"page": 1, "char_count": 6}, {"page": 2, "char_count": len(text) - 8}],
    }
    decisions = subjects.subject_sections(text, [parent], conversion)
    target = next(s for s in decisions if s["status"] == "target")
    assert target["locator"]["pages"] == [2]


def test_table_mixed_cells_and_mixed_rows(subjects):
    text = (
        "과학과 평가 계획\n<table>"
        "<tr><td>[9과01-01]</td></tr><tr><td>[9도01-01]</td></tr>"
        "<tr><td>[9과02-01] [9도02-01]</td></tr></table>"
    )
    diagnostics = [t for s in sections(text) for t in subjects.table_diagnostics(text, s)]
    table = next(t for t in diagnostics if t["status"] == "mixed")
    assert table["between_rows_mixed"]
    assert len(table["mixed_cells"]) == 1
    assert table["item_ownership"] == "unresolved_until_S6"


def test_grade_boundary_table_fragment_is_not_lost(subjects):
    text = (
        "과학과 평가 계획\n<table>\n<tr><td>1학년</td><td>[9과01-01]</td></tr>\n"
        "<tr><td>2학년</td><td>[9과02-01]</td></tr>\n</table>\n"
        "<table><tr><td>[9과03-01]</td></tr></table>"
    )
    decisions = sections(text, "2026학년도 2학기 합본.hwp")
    grade2 = next(s for s in decisions if s["grade"] == 2)
    diagnostics = subjects.table_diagnostics(text, grade2)
    assert len(diagnostics) == 2
    assert diagnostics[0]["code_counts"] == {"과": 1}


def test_math_defaults_and_science_configuration():
    aliases = importlib.import_module("scripts.math_subject_aliases")
    manifest = importlib.import_module("scripts.build_math_assessment_manifest")
    catalog = importlib.import_module("scripts.build_school_subject_assessment_catalog")
    parser = importlib.import_module("scripts.math_assessment_detail_parser")
    publish = importlib.import_module("scripts.build_math_assessment_publish_db")
    shortlist = importlib.import_module("scripts.build_strict_math_shortlist")
    assert aliases.subject_hits("과학과 평가 계획") == []
    assert aliases.subject_hits("과학과 평가 계획", "science")[0]["subject"] == "과학"
    assert aliases.subject_hits("# 공통수학1")[0]["subject"] == "공통수학1"
    assert aliases.curriculum_from_codes("[10공수1-01-01]") == ["2022"]
    assert aliases.curriculum_from_codes("[9과01-01]", "science") == ["undetermined"]
    assert manifest.classify("공통수학1 평가계획.hwp")[1] == "공통수학1"
    assert manifest.classify("과학 평가계획.hwp", "science")[1] == "과학"
    assert manifest.classify("과학의 날 계획.hwp", "science")[1] == "unknown"
    assert manifest.classify("과학 실험 평가 계획.hwp", "science")[1] == "과학"
    assert catalog.subjects_for() is catalog.SUBJECTS
    assert catalog.subjects_for("science")["2022"] == ("과학",)
    assert parser.segment_subject_alignment("[10공수1-01-01]", "공통수학1") == "expected"
    assert parser.segment_subject_alignment("[9과01-01]", "과학") == "target"
    assert parser.segment_subject_alignment("[9과01-01] [9도01-01]", "과학") == "mixed"
    assert publish.task_name_is_rejected("화학 반응 탐구 보고서")
    assert not publish.task_name_is_rejected("화학 반응 탐구 보고서", "science")
    other, context = publish.subject_context_patterns("science")
    assert not other.search("물리 화학 생명 지구") and context.search("물리 화학 생명 지구")
    assert shortlist.subject_pattern("공통수학1")
    assert shortlist.key({"subject": "수학"}) == ("", "", "수학")
    assert shortlist.key({"subject": "과학", "section_id": "a"}) != shortlist.key(
        {"subject": "과학", "section_id": "b"}
    )


def test_shortlist_cli_keeps_free_semester_and_distinct_sections(tmp_path, monkeypatch):
    indexer = importlib.import_module("scripts.build_math_assessment_evidence_index")
    shortlist = importlib.import_module("scripts.build_strict_math_shortlist")
    text = "1학년\n과학과 평가 계획\n관찰 기록 P\n2학년\n과학과 평가 계획\n과정 중심 평가\n"
    rows = indexer.evidence_records(record(text, "2026학년도 2학기 합본.hwp"), "science")
    source_path = tmp_path / "input.jsonl"
    source_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    strict = tmp_path / "strict.jsonl"
    short = tmp_path / "short.jsonl"
    summary = tmp_path / "summary.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "shortlist",
            "--input",
            str(source_path),
            "--strict-output",
            str(strict),
            "--shortlist-output",
            str(short),
            "--summary-output",
            str(summary),
            "--subject-family",
            "science",
        ],
    )
    shortlist.main()
    strict_rows = [json.loads(line) for line in strict.read_text(encoding="utf-8").splitlines()]
    assert len(strict_rows) == 2
    assert all(
        row["assessment_retention_reasons"] == ["free_semester_marker"] for row in strict_rows
    )
    assert all(row["public_eligible"] is False for row in strict_rows)


def test_audit_synthetic_corpus_outputs_and_hash_guard(tmp_path, monkeypatch):
    audit = importlib.import_module("audit_middle_subjects")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    text = "과학과 평가 계획\n관찰 기록 P\n"
    decisions = sections(text)
    # The audit consumes S4 source segments, not S5 decisions.
    segmenter = importlib.import_module("scripts.middle_segments")
    source_record = record(text)
    parents = segmenter.segment_document(
        {**source_record["source"], "sha256": source_record["sha256"]},
        {"text": text, "converter": "synthetic", "conversion_status": "ok"},
    )
    converted = tmp_path / "converted.json"
    converted.write_text(json.dumps({"text": text}), encoding="utf-8")
    corpus = {
        "round": "synthetic",
        "documents": [
            {
                "converted_path": "converted.json",
                "text_sha256": source_record["sha256"],
                "source": {"school_name": "가상학교", "school_code": "synthetic"},
                "document_id": "doc_synthetic",
                "edition": {"candidate_name": "합성.hwp"},
                "original_path": "synthetic.hwp",
                "segments": parents,
            }
        ],
        "incomplete_sources": [],
    }
    input_path = tmp_path / "segments.json"
    input_path.write_text(json.dumps(corpus), encoding="utf-8")
    result = audit.audit(input_path)
    assert result["summary"]["no_code_science_sections"] == len(decisions) == 1
    assert "원문 대조 확인표" in audit.markdown(result)
    converted.write_text(json.dumps({"text": text + "changed"}), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        audit.audit(input_path)
