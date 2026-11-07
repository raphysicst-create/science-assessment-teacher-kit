"""S4 regression tests use synthetic text only, never preserved school originals."""

import hashlib
import importlib
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))
    return importlib.import_module("middle_segments")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail("S4 tests must never use the network")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def source(name="2026학년도 2학기 평가계획.hwp", seq="1"):
    return {
        "candidate_name": name,
        "sha256": hashlib.sha256(name.encode()).hexdigest(),
        "school_code": "synthetic",
        "year": 2026,
        "file_seq": seq,
        "disclosure_round": 3,
        "collected_at": "2026-11-07T00:00:00Z",
    }


def conversion(text):
    return {"text": text, "converter": "kordoc", "conversion_status": "ok"}


def science_segments(module, text, name="2026학년도 2학기 평가계획.hwp"):
    return [
        s
        for s in module.segment_document(source(name), conversion(text))
        if "과학" in (s["subject_heading_raw"] or "")
    ]


@pytest.mark.parametrize(
    ("text", "middle", "high"),
    [
        ("1학년 평가 계획", [1], [1]),
        ("중1 평가 계획", [1], []),
        ("중학교 2학년 평가 계획", [2], []),
        ("중학교 1학년 2학기", [1], []),
        ("<td>3학년</td><td>2학기</td>", [3], [3]),
        ("| 학년 | 1학년 | 2학년 |", [1, 2], [1, 2]),
        ("고등학교 1학년 평가 계획", [], [1]),
        ("고2 평가 계획", [], [2]),
        ("중요1 참고2 21학년 2026학년도 과학고", [], []),
        ("중3과 고3의 평가", [3], [3]),
    ],
)
def test_ten_grade_sentences(module, text, middle, high):
    assert module.extract_grades(text, "middle") == middle
    assert module.extract_grades(text, "high") == high


def test_subject_then_three_grade_tables_and_ids(module):
    text = "과학과 교수학습 및 평가 운영 계획\n" + "\n".join(
        f"<table>\n<tr><td>{grade}학년</td><td>2학기</td></tr>\n"
        "<tr><td>합성 평가 내용</td></tr>\n</table>"
        for grade in (1, 2, 3)
    )
    segments = science_segments(module, text)
    assert len(segments) == 3
    assert [s["grade"] for s in segments] == [1, 2, 3]
    assert len({s["segment_id"] for s in segments}) == 3
    assert (
        len({module.segment_case_identifier(s["segment_id"], "2022", "과학") for s in segments})
        == 3
    )
    assert "grade3_quarantined" in segments[-1]["statuses"]
    assert all(s["grade_evidence"][0]["source"] == "table_cell" for s in segments)
    assert all(s["semester"] == 2 for s in segments)
    assert segments == science_segments(module, text)
    assert all(
        a["locator"]["end"] == b["locator"]["start"]
        for a, b in zip(segments, segments[1:], strict=False)
    )


@pytest.mark.parametrize("html", [False, True])
def test_pdf_title_with_school_footer_keeps_exact_span(module, html):
    title = "2026학년도 1학년 2학기 과학과 교수·학습 및 평가 계획가상중학교"
    if html:
        title = f'<tr><th colspan="6">{title}</th></tr>'
    text = title + "\n합성 과학\n2026학년도 1학년 2학기 국어과 평가 계획가상중학교\n국어"
    segments = science_segments(module, text, "2026학년도 1학년 2학기 평가계획.pdf")
    assert len(segments) == 1
    assert segments[0]["grade"] == 1
    assert text[:segments[0]["subject_heading_locator"]["end"]] == title
    assert "국어" not in text[segments[0]["locator"]["start"]:segments[0]["locator"]["end"]]


def test_pdf_combined_cover_target_and_teacher(module):
    text = ("과학과 교과교육과정 대상 : 1학년 담당교사 : ***(인)\n합성 과학\n"
            "국어과 교과교육과정 대상 : 1학년 담당교사 : ***(인)\n합성 국어")
    segments = science_segments(module, text, "2026학년도 2학기 평가계획.pdf")
    assert len(segments) == 1
    assert segments[0]["grade"] == 1
    assert segments[0]["subject_heading_raw"] == text.splitlines()[0]
    # Policy prose containing target/teacher terms is not a title.
    assert module.subject_heading_key(
        "과학과 평가는 계획에 따라 대상 : 1학년 담당교사 : ***",
    ) is None


def test_pdf_metadata_before_subject_heading_resets_grade_at_cover(module):
    def cover(grade, subject):
        return ("| 학교명 | 학년 | 학기 | 과목 | 학급 | 지도교사 |\n"
                "| --- | --- | --- | --- | --- | --- |\n"
                f"| 가상중 | {grade}학년 | 2학기 | {subject} | 1반 | *** |\n\n"
                f"# 1 {subject}과 교수학습 운영 계획\n합성 {subject}\n")
    text = cover(3, "수학") + cover(1, "과학") + cover(2, "과학") + cover(3, "국어")
    segments = science_segments(module, text, "2026학년도 2학기 평가계획.pdf")
    assert [s["grade"] for s in segments] == [1, 2]
    for s in segments:
        raw = text[s["locator"]["start"]:s["locator"]["end"]]
        assert "| 수학 |" not in raw and "| 국어 |" not in raw
    assert segments[0]["locator"]["end"] == segments[1]["locator"]["start"]


def test_grade_then_subject_order(module):
    text = "\n".join(
        f"{g}학년\n국어과 평가 계획\n합성 국어\n과학과 교수학습 및 평가 계획\n합성 과학"
        for g in (1, 2, 3)
    )
    segments = science_segments(module, text)
    assert [s["grade"] for s in segments] == [1, 2, 3]
    assert all(s["grade_evidence"][0]["source"] == "body_heading" for s in segments)


def test_repeated_subject_headers_and_grade_cycles(module):
    text = "과학과 교수학습 및 평가 계획\n1학년\n내용\n2학년\n내용\n3학년\n내용\n"
    text += (
        "과학과 평가 계획\n1학년\n평가\n2학년\n평가\n3학년\n평가\n"
        "기술⦁가정과 평가 계획\n1학년\n내용"
    )
    segments = science_segments(module, text)
    assert [s["grade"] for s in segments] == [1, 2, 3, 1, 2, 3]
    assert len({s["segment_id"] for s in segments}) == 6
    assert (
        "기술⦁가정" not in text[segments[-1]["locator"]["start"] : segments[-1]["locator"]["end"]]
    )


def test_grade_unknown_conflict_and_subject_reset(module):
    segments = module.segment_document(
        source(),
        conversion(
            "과학과 평가 계획\n중1\n내용\n국어과 평가 계획\n학년 근거 없음",
        ),
    )
    assert segments[0]["grade"] == 1
    assert segments[1]["grade"] is None
    assert "grade_unresolved" in segments[1]["statuses"]
    conflict = science_segments(module, "과학과 평가 계획\n2학년\n내용", "1학년 2학기.hwp")
    assert conflict[0]["grade"] is None
    assert conflict[0]["grade_conflict"]


def test_free_semester_retained(module):
    segments = science_segments(module, "과학과 평가 계획\n1학년\n자유학기\nP\n과정 중심 평가")
    assert len(segments) == 1
    assert "free_semester_marker" in segments[0]["statuses"]
    assert [e["text"] for e in segments[0]["free_semester_markers"]] == [
        "자유학기",
        "P",
        "과정 중심 평가",
    ]
    assert segments[0]["grade"] == 1


def test_pdf_page_offsets_and_next_header_not_fixed_window(module):
    page1 = "과학과 평가 계획\n1학년\n" + "합성 내용\n" * 2000
    page2 = "과학 계속\n국어과 평가 계획\n2학년\n국어"
    text = page1 + "\n\n" + page2
    result = {
        "text": text,
        "converter": "pymupdf",
        "conversion_status": "ok",
        "pages": [{"page": 1, "char_count": len(page1)}, {"page": 2, "char_count": len(page2)}],
    }
    segments = module.segment_document(source(), result)
    assert segments[0]["locator"]["pages"] == [1, 2]
    assert segments[0]["locator"]["end"] == text.index("국어과")
    heading = segments[0]["subject_heading_locator"]
    assert text[heading["start"] : heading["end"]] == segments[0]["subject_heading_raw"]


def version_document(module, name, text, seq):
    src = source(name, seq)
    return {
        "document_id": module.document_identifier(src["sha256"]),
        "source": src,
        "text": text,
        "segments": module.segment_document(src, conversion(text)),
    }


BASE = "과학과 교수학습 및 평가 계획\n1학년\n2학기\n평가 점수 10점"


@pytest.mark.parametrize(
    ("names", "texts", "seqs", "expected"),
    [
        (
            ["1학년 2학기(수정).pdf", "1학년 2학기(최종).pdf"],
            [BASE, BASE],
            ["1", "2"],
            ["superseded", "representative"],
        ),
        (
            ["1학년 2학기(수정).pdf", "1학년 2학기(최종).pdf"],
            [BASE, BASE.replace("10점", "9점")],
            ["1", "2"],
            ["version_conflict", "version_conflict"],
        ),
        (
            ["1학년 2학기(최종).pdf", "1학년 2학기(수정).pdf"],
            [BASE, BASE],
            ["1", "2"],
            ["superseded", "representative"],
        ),
        (
            [f"{g}학년 2학기.pdf" for g in (1, 2, 3)],
            [BASE.replace("1학년", f"{g}학년") for g in (1, 2, 3)],
            ["1", "2", "3"],
            ["single", "single", "single"],
        ),
        (
            ["1학년 2학기 합철본.hwp", "1학년 2학기 합철본-정정.hwp"],
            [BASE, BASE],
            ["1", "2"],
            ["superseded", "representative"],
        ),
    ],
)
def test_five_edition_scenarios(module, names, texts, seqs, expected):
    documents = [
        version_document(module, n, t, s) for n, t, s in zip(names, texts, seqs, strict=True)
    ]
    comparisons = module.resolve_versions(documents)
    assert [d["version_status"] for d in documents] == expected
    if "version_conflict" in expected:
        assert comparisons[0]["differences"]
        assert all("version_conflict" in d["segments"][0]["statuses"] for d in documents)


def test_unknown_disclosure_order_and_whitespace_equivalence(module):
    docs = [
        version_document(module, f"1학년 2학기({name}).hwp", BASE, "") for name in ("최종", "수정")
    ]
    module.resolve_versions(docs)
    assert all(d["version_status"] == "version_conflict" for d in docs)
    assert module.compare_versions(BASE, BASE.replace(" ", "  "))["equivalent"]
    assert not module.compare_versions("", "")["equivalent"]


def test_zip_children_distinct_and_locator_local(module):
    parent = source("평가계획.zip")
    children = [
        {"member_index": i, "member_name": f"{i}/1학년 2학기.hwp", "sha256": "a" * 64}
        for i in (0, 1)
    ]
    segments = [module.segment_document(parent, conversion(BASE), c)[0] for c in children]
    assert segments[0]["document_id"] == segments[1]["document_id"]
    assert segments[0]["child_id"] != segments[1]["child_id"]
    assert segments[0]["segment_id"] != segments[1]["segment_id"]
    assert all(s["locator"]["start"] == 0 for s in segments)


def test_legacy_high_school_and_math_case_regression(module, monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT))
    catalog = importlib.import_module("build_school_subject_assessment_catalog")
    detail = importlib.import_module("scripts.build_math_assessment_detail_db")
    assert catalog.extract_grades("고등학교 1학년 고2 고3") == [1, 2, 3]
    assert catalog.extract_grades("2026학년도1학년") == [1]
    assert catalog.extract_grades("중1 중학교 2학년") == [1, 2]
    sha = "b" * 64
    expected = hashlib.sha256(f"{sha}|2022|공통수학1".encode()).hexdigest()[:24]
    row = detail.compact_catalog_row(
        {"sha256": sha, "subject": "공통수학1", "resolved_curriculum": "2022"}
    )
    assert row["case_id"] == expected


def test_filename_evidence_and_body_prose_do_not_create_grade_sections(module):
    text = "과학과 평가 계획\n1학년 학생은 기초 내용을 복습한다.\n고2 평가를 언급한 일반 문장"
    segments = science_segments(module, text, "중학교 2학년 2학기.hwp")
    assert len(segments) == 1
    assert segments[0]["grade"] == 2
    assert segments[0]["grade_evidence"][0]["source"] == "filename"


@pytest.mark.parametrize("grade_label", ["대    상 : 2학년", "대상 학년：2학년"])
def test_spaced_grade_labels(module, grade_label):
    assert science_segments(module, f"과학과 교과교육과정\n{grade_label}\n합성")[0]["grade"] == 2


def test_multiline_cover_and_subject_without_suffix_end_science(module):
    text = (
        "과학과 1학년\n과학과 1학년\n교수․학습 및 평가 운영 계획\n합성 본문\n"
        "인공지능과 문제해결 교수학습 및 평가계획\n2학년\n다른 교과"
    )
    segments = science_segments(module, text)
    assert len(segments) == 1
    assert segments[0]["grade"] == 1
    assert segments[0]["locator"]["end"] == text.index("인공지능")
    h = segments[0]["subject_heading_locator"]
    assert segments[0]["subject_heading_raw"] == text[h["start"] : h["end"]]


def test_parenthesized_grade_and_non_subject_section_titles(module):
    text = (
        "과학과 평가 계획\n1학년\n5. 수행평가 세부 계획\n점수\n"
        "기술․가정과 (2)학년 (2)학기 교수․학습 및 평가 계획\n다른 교과"
    )
    segments = module.segment_document(source(), conversion(text))
    assert len(segments) == 2
    assert [s["grade"] for s in segments] == [1, 2]
    assert segments[1]["subject_heading_key"] == "기술․가정"


def test_header_table_grade_disagreement_and_parallel_grade_cells_are_held(module):
    conflict = science_segments(
        module, "과학과 1학년 평가 계획\n<table>\n<tr><td>2학년</td></tr>\n</table>"
    )
    assert len(conflict) == 1
    assert conflict[0]["grade"] is None
    assert conflict[0]["grade_conflict"]
    parallel = science_segments(
        module, "과학과 평가 계획\n<table>\n<tr><td>1학년</td><td>2학년</td></tr>\n</table>"
    )
    assert len(parallel) == 1
    assert parallel[0]["grade"] is None


def test_table_grade_with_semester_and_subject_in_same_cell(module):
    text = (
        "과학과 평가 계획\n<table>\n<tr><td>1학년<br>사회</td></tr>\n"
        "<tr><td>2학년(1학기)</td></tr>\n</table>"
    )
    segments = science_segments(module, text)
    assert [s["grade"] for s in segments] == [1, 2]
    assert segments[1]["semester"] is None
    assert segments[1]["semester_status"] == "mixed_or_conflicting"
    assert "semester_unresolved" in segments[1]["statuses"]


def test_grade_in_evaluation_overview_heading(module):
    segments = science_segments(
        module, "과학과 평가 계획\n합성 수업 내용\n### 3. 평가 개요(1학년)\n합성 평가"
    )
    assert len(segments) == 1
    assert segments[0]["grade"] == 1
    assert segments[0]["grade_evidence"][0]["source"] == "body_heading"


def test_all_source_evidence_and_unicode_locators(module):
    text = "과학과 1학년 2학기 평가 계획\n😀 합성 본문\n기술․가정과 (2)학년 2학기 평가 계획\n합성"
    src = source()
    segments = module.segment_document(src, conversion(text))
    assert segments[0]["locator"]["end"] == text.index("기술")
    for segment in segments:
        for e in segment["grade_evidence"] + segment["semester_evidence"]:
            value = src["candidate_name"] if e["source"] == "filename" else text
            assert value[e["start"] : e["end"]] == e["text"]
        assert not segment["public_eligible"]


def test_high_similarity_is_not_equivalence_and_table_structure_is_retained(module):
    left = BASE + "\n공통 합성 내용" * 1000
    result = module.compare_versions(left, left.replace("10점", "9점"))
    assert result["line_similarity"] > 0.99
    assert not result["equivalent"]
    assert not module.compare_versions('<td colspan="2">내용</td>', "<td>내용</td>")["equivalent"]


def test_different_document_kinds_do_not_supersede(module):
    docs = [version_document(module, f"1학년 2학기({i}).hwp", BASE, str(i)) for i in (1, 2)]
    docs[0]["document_kind"] = "summary"
    docs[1]["document_kind"] = "assessment_plan"
    assert module.resolve_versions(docs) == []
    assert all(d["version_status"] == "single" for d in docs)


def test_markdown_audit_with_synthetic_conversion_only(module, monkeypatch, tmp_path):
    audit = importlib.import_module("audit_middle_segments")
    raw = tmp_path / "synthetic.hwp"
    raw.write_bytes(b"synthetic bytes, not a school document")
    src = {
        **source("1학년 2학기.hwp"),
        "saved_path": raw.name,
        "school_name": "합성학교",
        "size_bytes": raw.stat().st_size,
        "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
    }
    out = tmp_path / "converted"
    out.mkdir()
    monkeypatch.setattr(audit, "convert_kordoc", lambda *args: conversion(BASE))
    document = audit.audit_document(src, tmp_path, out)
    module.resolve_versions([document])
    report = {
        "documents": [document],
        "summary": audit.aggregate([document]),
        "science_heading_candidates": audit.science_heading_candidates([document]),
        "version_comparisons": [],
    }
    markdown = audit.markdown_report(report)
    assert "합성학교" in markdown
    assert document["segments"][0]["segment_id"] in markdown
    stored = audit.json.loads((tmp_path / document["converted_path"]).read_text(encoding="utf-8"))
    assert stored["text"] == BASE
    assert raw.read_bytes() == b"synthetic bytes, not a school document"
