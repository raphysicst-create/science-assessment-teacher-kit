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
    assert match([item()], [item("03", 10, 15)]) == ([], [0], [0])
    assert match([item()], [item("03", doc=DOC_B)]) == ([], [0], [0])
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
    assert markdown.count("판정: A / B / 둘 다 아님(직접 입력)") == 2
    summary = json.loads((output.parent / "agreement.json").read_text(encoding="utf-8"))
    assert summary["item_pairing"]["ratio"] == 0.5


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
