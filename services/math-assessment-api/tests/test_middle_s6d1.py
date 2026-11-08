"""S6d-1 structural recovery, using synthetic documents and no network."""

import hashlib
import importlib
import json
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))

    def fail(*args, **kwargs):
        pytest.fail("network is forbidden in S6d-1")

    monkeypatch.setattr("socket.socket.connect", fail)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", fail)


def sections(text, filename="1학년 2학기 전과목 평가계획.hwp"):
    segments = importlib.import_module("middle_segments")
    subjects = importlib.import_module("middle_subjects")
    conversion = {"text": text, "converter": "synthetic", "conversion_status": "ok"}
    source = {"sha256": hashlib.sha256(text.encode()).hexdigest(), "candidate_name": filename}
    parents = segments.segment_document(source, conversion)
    return subjects.subject_sections(text, parents, conversion)


@pytest.mark.parametrize(
    "heading",
    [
        "( 과학 )과 1학년",
        "2026학년도 2학기 [과학]과 평가계획서",
        "# 과학 평가",
        "<tr><td>2026학년도 2학기<br>1학년 [과학]과 교수학습 및 평가 운영계획</td></tr>",
    ],
)
def test_integrated_uncoded_summary_with_next_subject_boundary(heading):
    text = (
        "( 국어 )과 1학년\n[9국01-01]\n" + heading + "\n"
        "| 평가영역 | 평가과제 |\n| --- | --- |\n| 관찰 | 상태 변화 기록 |\n"
        "( 기술·가정 )과 1학년\n| 설계 | 생활 설계 |\n"
    )
    found = sections(text)
    science = [s for s in found if s["status"] == "target"]
    assert len(science) == 1 and science[0]["boundary_verified"]
    assert not science[0]["codes"]
    assert science[0]["locator"]["end"] == text.index("( 기술·가정 )")
    assert science[0]["next_subject"] == "기술·가정"
    assert science[0]["boundary_evidence"]["end"]["raw"]
    assert found[-1]["status"] == "other"


def test_negative_compounds_and_mixed_document_keep_only_science():
    text = (
        "체육과 평가계획\n[9체01-01] 과학적 원리\n"
        "도덕과 평가계획\n[9도01-01] 과학기술 윤리, 과학고, 과학실, 과학의 날\n"
        "과학과 평가계획\n[9과01-01] 관찰\n"
        "기술·가정과 평가계획\n| 무코드 | 설계 |\n"
    )
    found = sections(text)
    audit = importlib.import_module("audit_middle_subjects")
    assert audit.document_status(found, {}) == "mixed"
    targets = [s for s in found if s["status"] == "target"]
    assert len(targets) == 1 and targets[0]["header"]["key"] == "과학"
    assert all(s["status"] == "other" for s in found if s not in targets)


def test_explicit_subject_column_bounds_uncoded_summary_rows():
    text = (
        "<table>\n<tr><th>교과</th><th>평가과제</th></tr>\n"
        "<tr><td>체육</td><td>과학적 움직임</td></tr>\n"
        "<tr><td>과학</td><td>관찰 기록</td></tr>\n"
        "<tr><td>기술·가정</td><td>생활 설계</td></tr>\n</table>\n무소속 후속 내용"
    )
    found = sections(text)
    target = next(s for s in found if s["status"] == "target")
    assert target["header"]["basis"] == "subject_column"
    assert "생활 설계" not in text[target["locator"]["start"] : target["locator"]["end"]]
    assert found[-1]["status"] == "unknown"


@pytest.mark.parametrize("separator", ["·", ".", ","])
def test_combined_grade_title_uses_local_grade_chapters(separator):
    text = (
        f"과학과 1{separator}2학년 교수학습 및 평가 계획\n"
        "### 가. 1학년 교수학습-평가 방법\n[9과01-01] 합성 관찰\n"
        "### 나. 2학년 교수학습-평가 방법\n[9과11-01] 합성 실험\n"
    )
    found = sections(text, f"1{separator}2학년 2학기 과학 평가계획.pdf")
    targets = [s for s in found if s["status"] == "target"]
    assert {s["grade"] for s in targets} == {1, 2}
    assert all(
        not s["parent_statuses"] or "grade_unresolved" not in s["parent_statuses"] for s in targets
    )


@pytest.mark.parametrize(
    "body",
    [
        "| 학년 | 학기 | 과목 |\n| --- | --- | --- |\n| 1 | 2학기 | 과학 |\n",
        "| 학교명 | 과목 | 학년 |\n| --- | --- | --- |\n| 가상중 | 과학 | 1 |\n",
        "| 학년 | 1 | 담당 학급 | 1반 |\n",
    ],
)
def test_numeric_grade_requires_a_grade_column_or_field(body):
    found = sections("과학과 평가계획\n" + body + "관찰 기록\n", "2학기 과학.hwp")
    assert any(s["grade"] == 1 and s["status"] == "target" for s in found)


def test_zip_children_have_independent_text_hashes_and_coordinates(tmp_path):
    s4 = importlib.import_module("audit_middle_segments")
    s5 = importlib.import_module("middle_subjects")
    s6 = importlib.import_module("middle_items")
    parent_sha = "a" * 64
    children = []
    for index, grade in enumerate((1, 2)):
        text = f"과학과 {grade}학년 평가계획\n[9과01-01] 관찰 기록\n"
        children.append(
            {
                "member_index": index,
                "member_name": f"{grade}학년 과학.hwp",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "text": text,
                "converter": "synthetic",
                "conversion_status": "ok",
            }
        )
    path = tmp_path / "conversion.json"
    path.write_text(json.dumps({"children": children}), encoding="utf-8")
    source = {"sha256": parent_sha, "candidate_name": "평가계획.zip"}
    document = {
        "sha256": parent_sha,
        "document_id": "doc_" + parent_sha,
        "converted_path": path.name,
        "children": children,
        "source": source,
        "edition": {"candidate_name": "평가계획.zip"},
    }
    independent = s4.independent_documents(document, tmp_path)
    assert len({d["document_id"] for d in independent}) == 2
    for child in independent:
        conversion = json.loads((tmp_path / child["converted_path"]).read_text(encoding="utf-8"))
        assert conversion["text"] == child["text"]
        found = s5.subject_sections(child["text"], child["segments"], conversion)
        assert len(found) == 1 and found[0]["status"] == "target"
        found[0].update(school="가상중", filename=child["source"]["candidate_name"])
        assert s6.extract_middle_items(child["text"], found[0], conversion)
        assert found[0]["locator"]["start"] == 0
        assert found[0]["locator"]["end"] == len(child["text"])
        assert child["segments"][0]["locator"]["text_field"] == "text"


def test_image_only_survives_s5_document_report(tmp_path, monkeypatch):
    audit = importlib.import_module("audit_middle_subjects")
    monkeypatch.setattr(audit, "ROOT", tmp_path)
    conversion = {"text": "", "conversion_status": "image_only", "converter": "synthetic"}
    (tmp_path / "conversion.json").write_text(json.dumps(conversion), encoding="utf-8")
    document = {
        "converted_path": "conversion.json",
        "text_sha256": hashlib.sha256(b"").hexdigest(),
        "original_path": "scan.pdf",
        "segments": [],
        "sha256": "c" * 64,
        "source": {"school_name": "가상중", "school_code": "1"},
        "edition": {"candidate_name": "1학년 스캔.pdf"},
        "document_id": "scan",
    }
    path = tmp_path / "s4.json"
    path.write_text(
        json.dumps(
            {"documents": [document], "round": "2026-round-3-dev2", "incomplete_sources": []}
        ),
        encoding="utf-8",
    )
    report = audit.audit(path)
    assert report["summary"]["document_states"] == {"image_only": 1}
    assert "읽을 수 없음" in report["documents"][0]["review_reason"]
    assert report["sections"] == []


def test_round_roster_selection_is_shared_and_overridable(tmp_path):
    rounds = importlib.import_module("middle_rounds")
    for round_key in ("2026-round-1-dev2", "2026-round-3-dev2"):
        assert rounds.roster_path(tmp_path, round_key).name == "middle-dev2-20.csv"
    assert rounds.roster_path(tmp_path, "2026-round-3").name == "middle-dev12.csv"
    path = tmp_path / "custom.csv"
    path.write_text("school_code,school_name\n11,synthetic\n", encoding="utf-8-sig")
    assert rounds.roster_path(tmp_path, "2026-round-3", Path("custom.csv")) == path
    assert rounds.roster_codes(path) == {"11"}


@pytest.mark.parametrize("title", ["## 3. 자유학기 평가 계획", "각 학년별 평가 계획"])
def test_generic_free_semester_title_is_not_a_new_subject(title):
    found = sections(
        "과학과 평가계획\n[9과01-01] 관찰\n"
        + title + "\n무코드 관찰 기록\n기술·가정과 평가계획\n설계"
    )
    assert [s["status"] for s in found] == ["target", "other"]
    assert found[0]["boundary_verified"]


def test_split_method_heading_ends_previous_subject():
    found = sections(
        "사회과 평가계획\n[9사01-01]\n# 과학과 교수학습\n\n# 및 평가 방법\n"
        "[9과01-01] 관찰\n기술·가정과 평가계획\n설계"
    )
    assert [s["status"] for s in found] == ["other", "target", "other"]
    assert found[1]["boundary_verified"]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_metadata_grade_evidence_preserves_converter_offsets(newline):
    text = newline.join([
        "과학과 평가계획", "| 학년 | 학기 | 과목 |", "| --- | --- | --- |",
        "| 1 | 2학기 | 과학 |", "관찰 기록",
    ])
    found = sections(text, "2학기 과학.hwp")
    target = next(s for s in found if s["status"] == "target" and s["grade"] == 1)
    assert target["grade_evidence"]
    for evidence in target["grade_evidence"]:
        assert text[evidence["start"]:evidence["end"]] == evidence["text"]
