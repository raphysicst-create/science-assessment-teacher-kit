"""Synthetic S9 labels and conversion packs. Never read school gold text."""

import copy
import csv
import hashlib
import importlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

PROJECT = Path(__file__).resolve().parents[3]
DOC_A, DOC_B = "a" * 12, "b" * 12


@pytest.fixture
def modules(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))

    def network_forbidden(*args, **kwargs):
        pytest.fail("S9 tests must remain offline")

    monkeypatch.setattr("socket.socket.connect", network_forbidden)
    return SimpleNamespace(
        validate=importlib.import_module("gold_validate"),
        diff=importlib.import_module("gold_diff"),
        source=importlib.import_module("gold_source_pack"),
        extract=importlib.import_module("extract_math_assessment_batch"),
    )


@pytest.fixture
def pack(tmp_path):
    directory = tmp_path / "pack"
    directory.mkdir()
    rows = []
    for doc_id in (DOC_A, DOC_B):
        text = "\n".join(f"Synthetic source line {n}" for n in range(1, 41)) + "\n"
        (directory / f"{doc_id}.md").write_text(text, encoding="utf-8")
        rows.append({"doc_id": doc_id, "school_id": "school", "school_name": "가상학교",
                     "line_count": 40, "sha256": hashlib.sha256(text.encode()).hexdigest()})
    (directory / "index.json").write_text(json.dumps(rows), encoding="utf-8")
    return directory


def loc(start=5, end=8, doc=DOC_A):
    return {"doc_id": doc, "line_start": start, "line_end": end}


def field(raw=None, status=None, norm=None):
    values = [] if raw is None else [{"raw": raw, "loc": loc()}]
    if norm is not None:
        values[0]["norm"] = norm
    return {"status": status or ("source_absent" if raw is None else "present"), "values": values}


def item(key="01", start=5, end=8, doc=DOC_A, labeler="claude"):
    fields = {name: field() for name in (
        "title", "task_text", "task_no", "period", "method", "max_score",
        "sub_scores", "ratio", "rubric",
    )}
    return {
        "type": "item", "school_id": "school", "labeler": labeler,
        "item_key": f"school-g1-s1-{key}", "grade": 1, "semester": 1,
        "occurrences": [loc(start, end, doc)], "identity_basis": "동일한 과제번호",
        "free_semester": False, **fields,
        "title": {**field("가상 과제"), "role": "과제명"},
        "standards": [{**field(), "codes": []}],
    }


def documents(labeler="claude"):
    return [{
        "type": "document", "doc_id": doc, "school_id": "school", "labeler": labeler,
        "edition": "valid", "edition_note": "가상 근거", "notes": "",
        "science_sections": [{"grade": 1, "semester": 1, "line_start": 3, "line_end": 35}],
    } for doc in (DOC_A, DOC_B)]


def write_labels(path, rows):
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
                    encoding="utf-8")
    return path


def test_validate_positive_and_cli(tmp_path, pack, modules):
    record = item()
    record["method"] = {
        **field("☑ 실험 □ 관찰"),
        "options": [{"text": "실험", "state": "checked", "mark": "☑"},
                    {"text": "관찰", "state": "unchecked", "mark": "□"}],
    }
    record["standards"] = [{**field("[9과01-01]"), "codes": ["[9과01-01]"]}]
    record["ratio"] = {"status": "conflict", "values": [
        {"raw": "20%", "norm": 20, "loc": {"doc_id": DOC_A, "line": 5, "page": 1}},
        {"raw": "30%", "norm": 30, "loc": loc(8, 9, DOC_B)},
    ]}
    path = write_labels(tmp_path / "labels.jsonl", documents() + [record])
    assert modules.validate.validate_file(path, pack) == []
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT / "scripts/gold_validate.py"), str(path),
         "--pack-dir", str(pack)], capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def school_pack(pack):
    index_path = pack / "index.json"
    rows = json.loads(index_path.read_text(encoding="utf-8"))
    rows[1]["school_id"] = "other"
    index_path.write_text(json.dumps(rows), encoding="utf-8")
    return pack


@pytest.mark.parametrize("schools", [["school"], ["other"], ["school", "other"]])
def test_validate_school_scope_positive_and_cli(tmp_path, school_pack, modules, schools):
    rows = documents()
    rows[1]["school_id"] = "other"
    rows = [row for row in rows if row["school_id"] in schools]
    if "school" in schools:
        rows.append(item())
    path = write_labels(tmp_path / "scoped.jsonl", rows)
    assert modules.validate.validate_file(path, school_pack, schools=schools) == []
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT / "scripts/gold_validate.py"), str(path),
         "--pack-dir", str(school_pack), "--schools", *schools],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(("change", "message"), [
    (lambda rows: rows.pop(0), "document 줄 0개"),
    (lambda rows: rows.append(copy.deepcopy(rows[0])), "document 줄 2개"),
    (lambda rows: rows.append({**documents()[1], "school_id": "other"}), "학교 범위 밖"),
    (lambda rows: rows.append({**item(doc=DOC_B), "school_id": "other",
                               "item_key": "other-g1-s1-01"}), "학교 범위 밖"),
    (lambda rows: rows.append(documents()[1]), "INDEX의 학교와 school_id가 다름"),
    (lambda rows: rows[-1]["occurrences"][0].update(doc_id=DOC_B), "위치의 학교"),
])
def test_validate_school_scope_negative(change, message, tmp_path, school_pack, modules):
    rows = [documents()[0], item()]
    change(rows)
    path = write_labels(tmp_path / "scoped.jsonl", rows)
    errors = modules.validate.validate_file(path, school_pack, schools=["school"])
    assert any(message in error for error in errors), errors


def test_validate_school_scope_unknown_and_default(tmp_path, school_pack, modules):
    path = write_labels(tmp_path / "scoped.jsonl", [documents()[0]])
    errors = modules.validate.validate_file(path, school_pack, schools=["missing"])
    assert any("INDEX에 없는 school_id: missing" in error for error in errors), errors
    assert any("학교 범위 밖" in error for error in errors), errors
    errors = modules.validate.validate_file(path, school_pack)
    assert any(f"문서 {DOC_B}: document 줄 0개" in error for error in errors), errors


@pytest.mark.parametrize(("change", "message"), [
    (lambda rows: rows.pop(0), "document 줄 0개"),
    (lambda rows: rows.append(copy.deepcopy(rows[0])), "document 줄 2개"),
    (lambda rows: rows.append(copy.deepcopy(rows[-1])), "item_key 중복"),
    (lambda rows: rows[-1]["occurrences"][0].update(line_end=41), "줄 범위"),
    (lambda rows: rows[-1]["occurrences"][0].update(line_start=9), "줄 범위"),
    (lambda rows: rows[-1]["occurrences"][0].update(doc_id="c" * 12), "존재하지 않는"),
    (lambda rows: rows[-1].update(grade=3), "스키마"),
    (lambda rows: rows[-1].update(labeler="other"), "스키마"),
    (lambda rows: rows[-1].update(activity="실험"), "스키마"),
    (lambda rows: rows[-1]["title"].update(values=[]), "present values"),
    (lambda rows: rows[-1]["title"].update(status="conflict"), "conflict values"),
    (lambda rows: rows[-1]["title"].update(status="ambiguous"), "스키마"),
    (lambda rows: rows[-1]["title"]["values"][0]["loc"].update(line=5), "스키마"),
    (lambda rows: rows[-1]["standards"][0].update(codes=["[9과1-01]"]), "스키마"),
    (lambda rows: rows[-1]["method"].update(options=[{"text": "실험", "state": "lost"}]), "스키마"),
    (lambda rows: rows[-1].update(item_key="wrong-g1-s1-01"), "item_key의"),
    (lambda rows: rows[0]["science_sections"][0].update(line_end=41), "줄 범위"),
    (lambda rows: rows[-1]["title"].update(status="other"), "스키마"),
    (lambda rows: rows[-1]["ratio"].update(status="present", values=[
        {"raw": "20", "norm": "20", "loc": loc()}]), "스키마"),
    (lambda rows: rows[-1].pop("identity_basis"), "스키마"),
])
def test_validate_negative(change, message, tmp_path, pack, modules):
    rows = documents() + [item()]
    change(rows)
    errors = modules.validate.validate_file(write_labels(tmp_path / "bad.jsonl", rows), pack)
    assert any(message in error for error in errors), errors


def test_validate_malformed_json_and_exit(tmp_path, pack, modules):
    path = tmp_path / "bad.jsonl"
    path.write_text("{bad}\n\nnull\n", encoding="utf-8")
    errors = modules.validate.validate_file(path, pack)
    assert sum("JSON 오류" in error for error in errors) == 2
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT / "scripts/gold_validate.py"), str(path),
         "--pack-dir", str(pack)], capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 1


def test_pairing_overlap_largest_unmatched_and_ties(modules):
    match = modules.diff.match_items
    assert match([item()], [item("99", 6, 9)]) == ([(0, 0)], [], [])
    assert match([item()], [item("02", 7, 8), item("03", 5, 8)]) == (
        [(0, 1)], [], [0],
    )
    assert match([item()], [item("02", 5, 6), item("03", 7, 8)]) == ([], [0], [0, 1])
    assert match([item(), item("02")], [item("03")]) == ([], [0, 1], [0])
    assert match([item()], [item("03", 10, 15)]) == ([(0, 0)], [], [])
    assert match([item()], [item("03", doc=DOC_B)]) == ([(0, 0)], [], [])
    assert match([item()], [item("03", 10, 15)], strict=True) == ([], [0], [0])
    assert match([item()], [item("03", doc=DOC_B)], strict=True) == ([], [0], [0])
    for key, value in (("school_id", "elsewhere"), ("grade", 2), ("semester", 2)):
        other = item()
        other[key] = value
        assert match([item()], [other]) == ([], [0], [0])


def test_overlap_counts_union_once(modules):
    assert modules.diff.overlap([loc(1, 5), loc(3, 7)], [loc(2, 6), loc(3, 5)]) == 5


def test_pack_line_numbers_use_only_lf(tmp_path, modules):
    path = tmp_path / "synthetic.md"
    path.write_bytes("one\finside\u2028line\nsecond\n".encode())
    assert modules.validate.pack_lines(path) == ["one\finside\u2028line", "second"]
    labels = write_labels(tmp_path / "label.jsonl", [{"raw": "source\u2028text"}])
    assert modules.validate.read_labels(labels) == ([{"raw": "source\u2028text"}], [1], [])


def test_empty_agreement_has_explicit_denominators(pack, modules):
    rows, summary = modules.diff.compare_labels(documents(), documents("astra"), pack)
    assert rows == []
    assert summary["item_pairing"]["ratio"] is None
    assert summary["fields"]["title"] == {"matched": 0, "total": 0, "agreement": None}


def test_diff_fields_conflicts_and_document_sections(pack, modules):
    left, right = item(), item("99", labeler="astra")
    conflict = {"status": "conflict", "values": [
        {"raw": "20%", "norm": 20, "loc": loc()},
        {"raw": "30%", "norm": 30, "loc": loc(doc=DOC_B)},
    ]}
    left["ratio"] = copy.deepcopy(conflict)
    right["ratio"] = copy.deepcopy(conflict)
    right["ratio"]["values"].reverse()
    left["standards"] = [{**field("[9과01-01,02]"), "codes": ["[9과01-01]", "[9과01-02]"]}]
    right["standards"] = copy.deepcopy(left["standards"])
    right["standards"][0]["codes"].reverse()
    right["title"]["values"][0]["raw"] = " 가상  \n 과제 "
    left["max_score"], right["max_score"] = field("20", norm=20), field("20", norm=20.0)
    docs_a, docs_b = documents(), documents("astra")
    docs_b[0]["science_sections"][0].update(line_start=4, line_end=34)
    assert modules.diff.compare_labels(docs_a + [left], docs_b + [right], pack)[0] == []
    right["ratio"]["values"][0]["norm"] = 40
    right["title"]["values"][0]["raw"] = "다른 과제"
    right["standards"][0]["codes"] = ["[9과02-01]"]
    right["period"]["status"] = "ambiguous"
    right["period"]["note"] = "가상 이유"
    docs_b[0]["edition"] = "conflict"
    docs_b[1]["science_sections"][0].update(grade=2)
    rows, summary = modules.diff.compare_labels(docs_a + [left], docs_b + [right], pack)
    assert {row["필드"] for row in rows} == {
        "ratio", "title", "standards", "period", "edition", "science_sections",
    }
    assert len(rows) == 6
    assert summary["fields"]["ratio"]["agreement"] == 0
    assert summary["fields"]["document.edition"]["agreement"] == 0.5
    assert summary["item_pairing"]["ratio"] == 1
    assert all(len(row["원문 발췌"]) <= 400 for row in rows)
    ratio_row = next(r for r in rows if r["필드"] == "ratio")
    assert "3 | Synthetic source line 3" in ratio_row["원문 발췌"]


def test_disjoint_document_ranges(pack, modules):
    left, right = documents(), documents("astra")
    left[0]["science_sections"][0].update(line_end=10)
    right[0]["science_sections"][0].update(line_start=11)
    rows, _ = modules.diff.compare_labels(left, right, pack)
    assert [row["필드"] for row in rows] == ["science_sections"]


def test_unmatched_reports_and_cli(tmp_path, pack, modules):
    left = documents() + [item(), item("02", 15, 18)]
    right = documents("astra") + [item("99", labeler="astra"), item("03", 25, 28)]
    right[-1]["title"] = field("별도 과제")
    a_path = write_labels(tmp_path / "a.jsonl", left)
    b_path = write_labels(tmp_path / "b.jsonl", right)
    output = tmp_path / "out/disagreements.csv"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT / "scripts/gold_diff.py"),
         str(a_path), str(b_path),
         "--pack-dir", str(pack), "--out", str(output)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output.read_bytes().startswith(b"\xef\xbb\xbf")
    with output.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert all(row["종류"] == "항목존재" for row in rows)
    markdown = output.with_suffix(".md").read_text(encoding="utf-8")
    assert markdown.count("판정: A · B · 둘 다 아님") == 2
    summary = json.loads((output.parent / "agreement.json").read_text(encoding="utf-8"))
    assert summary["v2"]["item_pairing"]["ratio"] == 0.5
    assert summary["v1"]["item_pairing"]["ratio"] == 0.5
    assert sum(t["count"] for t in summary["v2"]["disagreement_types"]) == 2
    assert {row["A상태"] for row in rows} == {"present", "missing"}
    assert all(len(row[side + "값요약"]) <= 150 for row in rows for side in ("A", "B"))


def test_content_pairing_same_line_uses_title_and_task_text(modules):
    left = [item("01"), item("02")]
    right = [item("98"), item("99")]
    left[0]["title"] = field("용수철 (실험)")
    left[1]["title"] = field("행성, 탐구!")
    right[0]["title"] = field("다른 평가영역")
    right[0]["task_text"] = field(" 행성<br/>탐구 ")
    right[1]["title"] = field("용수철<br>실험")
    match = modules.diff.match_items
    assert match(left, right) == ([(0, 1), (1, 0)], [], [])
    assert match(left, right, strict=True) == ([], [0, 1], [0, 1])
    assert match(list(reversed(left)), right) == ([(0, 0), (1, 1)], [], [])


def test_content_pairing_reconsiders_candidates_after_confirmed_pair(modules):
    left = [item("01", 1, 10), item("02", 1, 2)]
    right = [item("98", 1, 10), item("99", 1, 5)]
    for records in (left, right):
        records[0]["title"] = field("첫 과제")
        records[1]["title"] = field("둘째 과제")
    assert modules.diff.match_items(left, right) == ([(0, 0), (1, 1)], [], [])
    assert modules.diff.match_items(left, right, strict=True) == ([(0, 0)], [1], [1])


def test_content_pairing_title_fallback_unique_and_empty_titles(modules):
    left, right = item(), item("99", 30, 35)
    left["title"] = field(" Task (A) ")
    right["title"] = field()
    right["task_text"] = field("task<br>A!")
    assert modules.diff.match_items([left], [right]) == ([(0, 0)], [], [])
    assert modules.diff.match_items([left], [right, copy.deepcopy(right)]) == ([], [0], [0, 1])
    left["title"], right["task_text"] = field("()"), field(" \n")
    assert modules.diff.match_items([left], [right]) == ([], [0], [0])


@pytest.mark.parametrize("name", ["title", "task_text", "task_no", "period",
                                 "max_score", "ratio", "sub_scores"])
def test_content_value_sets_ignore_duplicate_locations(pack, modules, name):
    left, right = item(), item("99")
    sample = field("4월 (5월)") if name in {"title", "task_text", "task_no", "period"} else (
        field("20점", norm=20)
    )
    if name == "sub_scores":
        sample["values"][0]["name"] = "실험 (수행)"
    left[name], right[name] = copy.deepcopy(sample), copy.deepcopy(sample)
    right[name]["values"] += [
        {**copy.deepcopy(sample["values"][0]), "loc": {**loc(20, 22), "page": 2}},
        {**copy.deepcopy(sample["values"][0]), "loc": loc(30, 32, DOC_B)},
    ]
    rows, _ = modules.diff.compare_labels([left], [right], pack)
    assert rows == []
    strict_rows, _ = modules.diff.compare_labels([left], [right], pack, strict=True)
    assert [r["필드"] for r in strict_rows] == [name]


def test_content_ignores_notes_identity_and_link_basis(pack, modules):
    left, right = item(), item("99")
    for name in modules.diff.FIELDS:
        if isinstance(right[name], dict):
            left[name]["note"], right[name]["note"] = "설명 A", "설명 B"
    left["rubric"] = {**field("표 A"), "link_basis": "근거 A"}
    right["rubric"] = {**field("표 B"), "link_basis": "근거 B"}
    right["identity_basis"], right["notes"] = "다른 설명", "다른 메모"
    assert modules.diff.compare_labels([left], [right], pack)[0] == []


def test_content_role_is_separate_and_summary_is_bounded(pack, modules):
    left, right = item(), item("99")
    right["title"]["role"] = "평가영역"
    rows, summary = modules.diff.compare_labels([left], [right], pack)
    assert [r["필드"] for r in rows] == ["title_role"]
    assert summary["fields"]["title"]["agreement"] == 1
    assert rows[0]["A상태"] == rows[0]["B상태"] == "present"
    assert summary["disagreement_types"] == [
        {"field": "title_role", "a_status": "present", "b_status": "present", "count": 1},
    ]
    assert len(modules.diff.value_summary("period", field("가" * 200), "present")) == 150


@pytest.mark.parametrize("name", ["title", "task_text", "task_no", "period", "max_score",
                                 "ratio", "sub_scores", "standards", "method", "rubric"])
def test_content_preserves_status_disagreements(pack, modules, name):
    left, right = item(), item("99")
    target = right[name][0] if name == "standards" else right[name]
    target.update(status="ambiguous", note="검토 필요")
    rows, _ = modules.diff.compare_labels([left], [right], pack)
    assert [r["필드"] for r in rows] == [name]
    assert rows[0]["B상태"] == "ambiguous"


def test_content_numbers_sub_scores_and_real_changes(pack, modules):
    left, right = item(), item("99")
    left["ratio"], right["ratio"] = field("(20%)"), field("20", norm=20.0)
    left["max_score"], right["max_score"] = field("1,000.5점"), field("1000.5", norm=1000.5)
    left["sub_scores"] = field("(10점)")
    left["sub_scores"]["values"][0]["name"] = "실험 (수행)"
    right["sub_scores"] = field("10", norm=10)
    right["sub_scores"]["values"][0]["name"] = "실험<br>수행"
    assert modules.diff.compare_labels([left], [right], pack)[0] == []
    right["ratio"]["values"][0]["norm"] = 30
    right["sub_scores"]["values"][0]["name"] = "다른 요소"
    right["free_semester"] = True
    rows, _ = modules.diff.compare_labels([left], [right], pack)
    assert {r["필드"] for r in rows} == {"ratio", "sub_scores", "free_semester"}
    assert json.loads(next(r["B값"] for r in rows if r["필드"] == "ratio")) == right["ratio"]


def test_content_standards_union_and_group_statuses(pack, modules):
    left, right = item(), item("99")
    first = {**field("코드 묶음"), "codes": ["[9과01-01]", "[9과01-02]"],
             "area_name_raw": "물질 (성질)", "text": "설명 A"}
    left["standards"] = [first]
    right["standards"] = [
        {**copy.deepcopy(first), "codes": [code], "text": "설명 B",
         "area_name_raw": "물질<br>성질"} for code in first["codes"]
    ]
    assert modules.diff.compare_labels([left], [right], pack)[0] == []
    right["standards"][0]["status"] = "conflict"
    rows, _ = modules.diff.compare_labels([left], [right], pack)
    assert [r["필드"] for r in rows] == ["standards"]
    assert rows[0]["B상태"] == "conflict | present"
    right["standards"][0]["status"] = "present"
    right["standards"][0]["area_name_raw"] = "다른 영역"
    assert [r["필드"] for r in modules.diff.compare_labels([left], [right], pack)[0]] == [
        "standards",
    ]


def test_content_method_options_text_and_marks(pack, modules):
    left, right = item(), item("99")
    left["method"] = {**field("표기 A"), "plain_text": "서술 (평가)", "other_text": "보고서!",
                      "options": [{"text": "실험 (평가)", "state": "checked", "mark": "■"}]}
    right["method"] = {**field("표기 B"), "plain_text": "서술<br>평가", "other_text": "보고서",
                       "options": [{"text": "실험평가", "state": "checked", "mark": "☑"}] * 2}
    assert modules.diff.compare_labels([left], [right], pack)[0] == []
    right["method"]["options"][0] = {"text": "실험평가", "state": "unchecked"}
    assert [r["필드"] for r in modules.diff.compare_labels([left], [right], pack)[0]] == ["method"]
    right["method"] = copy.deepcopy(left["method"])
    right["method"]["other_text"] = "다른 내용"
    assert [r["필드"] for r in modules.diff.compare_labels([left], [right], pack)[0]] == ["method"]


@pytest.mark.parametrize(("status", "other_loc", "equal"), [
    ("present", loc(8, 12), True),
    ("present", loc(9, 12), False),
    ("present", loc(doc=DOC_B), False),
    ("ambiguous", loc(20, 22), True),
    ("conflict", loc(20, 22), True),
])
def test_content_rubric_requires_any_same_document_overlap(pack, modules, status, other_loc, equal):
    left, right = item(), item("99")
    left["rubric"] = field("기준 A", status=status)
    right["rubric"] = field("기준 B", status=status)
    right["rubric"]["values"][0]["loc"] = other_loc
    rows, _ = modules.diff.compare_labels([left], [right], pack)
    assert [r["필드"] for r in rows] == ([] if equal else ["rubric"])


def test_content_document_ignores_pymupdf_and_clips_crossing_range(pack, modules):
    path = pack / f"{DOC_A}.md"
    lines = modules.validate.pack_lines(path)
    lines[19] = "## pymupdf"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    left, right = documents(), documents("astra")
    left[0]["science_sections"][0].update(line_end=19)
    right[0]["science_sections"] += [
        {"grade": 2, "semester": 2, "line_start": 21, "line_end": 40},
    ]
    assert modules.diff.compare_labels(left, right, pack)[0] == []
    assert [r["필드"] for r in modules.diff.compare_labels(left, right, pack, strict=True)[0]] == [
        "science_sections",
    ]
    right[0]["science_sections"][0].update(line_start=20)
    assert [r["필드"] for r in modules.diff.compare_labels(left, right, pack)[0]] == [
        "science_sections",
    ]


def test_content_report_groups_fields_per_item_and_atomic_files(
    tmp_path, pack, modules, monkeypatch,
):
    left, right = item(), item("99")
    right["period"], right["ratio"] = field("5월"), field("30%")
    rows, metrics = modules.diff.compare_labels([left], [right], pack)
    output = tmp_path / "reports/disagreements.csv"

    def forbidden(*args, **kwargs):
        pytest.fail("report directories must use ordinary mkdir for inherited ACLs")

    monkeypatch.setattr("tempfile.mkdtemp", forbidden)
    modules.diff.write_reports(rows, {"v2": metrics}, output)
    markdown = output.with_suffix(".md").read_text(encoding="utf-8")
    assert markdown.count("## 가상학교\n") == 1
    assert markdown.count("### 1학년 1학기\n") == 1
    assert markdown.count("#### 가상 과제\n") == 1
    assert markdown.count("판정: A · B · 둘 다 아님") == 2
    excerpts = markdown.split("원문 발췌:\n\n")[1:]
    assert all(len(part.split("\n\n판정:")[0].replace("> ", "").replace("\\|", "|")) <= 300
               for part in excerpts)
    assert not list(output.parent.glob(".*.tmp"))


def test_strict_cli_keeps_v1_and_v2_metrics(tmp_path, pack, modules):
    left, right = item(), item("99")
    right["title"]["values"] *= 2
    a_path = write_labels(tmp_path / "a.jsonl", documents() + [left])
    b_path = write_labels(tmp_path / "b.jsonl", documents("astra") + [right])
    output = tmp_path / "strict.csv"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT / "scripts/gold_diff.py"),
         str(a_path), str(b_path), "--strict", "--pack-dir", str(pack), "--out", str(output)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((output.parent / "agreement.json").read_text(encoding="utf-8"))
    assert summary["v1"]["difference_count"] == 1
    assert summary["v2"]["difference_count"] == 0
    with output.open(encoding="utf-8-sig", newline="") as handle:
        assert [r["필드"] for r in csv.DictReader(handle)] == ["title"]


def test_conversion_only_never_calls_semantic_modules(tmp_path, modules, monkeypatch):
    pdf = tmp_path / "fake.pdf"
    with fitz.open() as document:
        document.new_page().insert_text((50, 60), "Synthetic page one")
        document.new_page().insert_text((50, 60), "Synthetic page two")
        document.save(pdf)

    def forbidden(*args, **kwargs):
        pytest.fail("conversion-only must not call item/method/physical interpretation")

    for name in ("pdf_method_rows", "structured_method_rows", "compare_method_rows"):
        monkeypatch.setattr(modules.extract, name, forbidden)
    physical = importlib.import_module("middle_physical")
    monkeypatch.setattr(physical, "pdf_surfaces", forbidden)

    def run(command, **kwargs):
        output = Path(command[command.index("-o") + 1])
        output.write_text(json.dumps({
            "success": True, "markdown": "Full synthetic kordoc text", "blocks": [], "pageCount": 2,
        }), encoding="utf-8")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(modules.extract.subprocess, "run", run)
    archive = tmp_path / "fake.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.write(pdf, "fake.pdf")
        handle.writestr("fake.hwp", b"synthetic hwp")
    result = modules.extract.extract_document(
        archive, Path("fake.js"), tmp_path, pdf_converter="kordoc", conversion_only=True,
    )
    assert len(result["children"]) == 2
    converted = result["children"][0]
    assert converted["text"] == "Full synthetic kordoc text"
    assert "Synthetic page two" in converted["pymupdf"]["pages"][1]["text"]
    text = modules.source.pack_text("a" * 12, {
        "school_id": "school", "school_name": "가상", "disclosure_round": 1,
        "candidate_name": "fake.zip",
    }, converted, "pdf")
    assert "## kordoc\n\nFull synthetic kordoc text" in text
    assert "<<<PAGE 1>>>" in text and "<<<PAGE 2>>>" in text


def test_pack_copy_index_and_seal(tmp_path, modules, monkeypatch):
    root = tmp_path / "project"
    originals = []
    for round_no, extension in ((1, "hwp"), (3, "zip")):
        raw = root / f"original.{extension}"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(f"Synthetic {extension}".encode())
        digest = modules.source.sha256(raw)
        originals.append((raw, digest))
        manifest = root / (
            f"data/derived/schoolinfo_4ga/2026-round-{round_no}-gold/attachments.jsonl"
        )
        manifest.parent.mkdir(parents=True)
        row = {"result": "downloaded", "saved_path": raw.name, "sha256": digest,
               "school_id": "school", "school_name": "가상학교", "disclosure_round": round_no,
               "candidate_name": raw.name}
        write_labels(manifest, [row, {"result": "excluded_non_plan_filename"}])
    for name in (modules.source.GUIDE, modules.source.SCHEMA):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic specification", encoding="utf-8")

    def extract(path, *args, **kwargs):
        assert kwargs["conversion_only"] is True
        child = {"converter": "kordoc", "conversion_status": "ok", "text": "Synthetic text\n"}
        if path.suffix == ".zip":
            return {"children": [{**child, "member_name": "one.hwp"},
                                 {**child, "member_name": "two.hwp"}]}
        return child

    monkeypatch.setattr(modules.source, "extract_document", extract)

    def forbidden(*args, **kwargs):
        pytest.fail("published source pack must use ordinary mkdir for inherited ACLs")

    monkeypatch.setattr("tempfile.mkdtemp", forbidden)
    output = root / "data/gold"
    summary = modules.source.build_pack(root, output, Path("fake.js"))
    assert list(output.parent.glob(".source-build-*")) == []
    assert summary["documents"] == 3
    assert summary["sources"] == 2
    index = json.loads((output / "pack/index.json").read_text(encoding="utf-8"))
    assert [row["doc_id"] for row in index[1:]] == [
        originals[1][1][:12] + "-c01", originals[1][1][:12] + "-c02",
    ]
    seal = json.loads((output / "SEAL.json").read_text(encoding="utf-8"))
    assert len(seal["pack_files"]) == 5
    for record in seal["pack_files"]:
        assert modules.source.sha256(output / record["path"]) == record["sha256"]
    for path, digest in originals:
        assert modules.source.sha256(path) == digest
        assert modules.source.sha256(output / "raw" / f"{digest}{path.suffix}") == digest
    with pytest.raises(FileExistsError):
        modules.source.build_pack(root, output, Path("fake.js"))


def test_failed_pack_build_is_retryable(tmp_path, modules, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    for name in (modules.source.GUIDE, modules.source.SCHEMA):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic specification", encoding="utf-8")
    raw = root / "fake.hwp"
    raw.write_bytes(b"Synthetic original")
    monkeypatch.setattr(modules.source, "sources", lambda _: [{
        "saved_path": raw.name, "sha256": modules.source.sha256(raw),
        "school_id": "school", "school_name": "fake", "disclosure_round": 1,
        "candidate_name": raw.name,
    }])

    def fail(*args, **kwargs):
        raise RuntimeError("Synthetic conversion interruption")

    monkeypatch.setattr(modules.source, "extract_document", fail)
    output = root / "data/gold"
    output.mkdir()
    with pytest.raises(RuntimeError, match="interruption"):
        modules.source.build_pack(root, output, Path("fake.js"))
    assert list(output.iterdir()) == []
    assert list(output.parent.glob(".source-build-*")) == []
    monkeypatch.setattr(modules.source, "extract_document", lambda *args, **kwargs: {
        "converter": "kordoc", "conversion_status": "ok", "text": "Synthetic text",
    })
    assert modules.source.build_pack(root, output, Path("fake.js"))["documents"] == 1
