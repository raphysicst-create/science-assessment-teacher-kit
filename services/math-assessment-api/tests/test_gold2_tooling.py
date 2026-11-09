"""Exercise gold2 tooling only with synthetic inputs under pytest tmp_path.

Run/Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
            services/math-assessment-api/tests/test_gold2_tooling.py
"""

import copy
import csv
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

PROJECT = Path(__file__).resolve().parents[3]
SCHOOL = "ms-gold2-synthetic-city"
DOCS = ("a" * 12, "b" * 12)


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                    encoding="utf-8")
    return path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def cli(script, *args):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT / "scripts" / script), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", check=False,
    )


@pytest.fixture
def gold2_modules(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))

    def no_network(*args, **kwargs):
        pytest.fail("gold2 tests must remain offline")

    monkeypatch.setattr("socket.socket.connect", no_network)
    names = ("middle_rounds", "gold_source_pack", "gold_validate", "gold_diff",
             "gold_adjudicate", "gold_activity_merge", "gold_activity_pack",
             "gold_activity_validate", "gold_activity_diff", "gold_activity_score", "gold_score")
    return SimpleNamespace(**{name: importlib.import_module(name) for name in names})


def activity(primary="탐구", secondary=(), line=5, doc=DOCS[0]):
    return {"definition_version": "activity-def-v2", "primary": primary,
            "secondary": list(secondary), "evidence": [
                {"type": "method_text", "quote": "가짜 활동 근거",
                 "loc": {"doc_id": doc, "line": line}}]}


@pytest.fixture
def bundle(tmp_path):
    pack = tmp_path / "pack"
    pack.mkdir()
    index, documents = [], []
    for doc in DOCS:
        text = "## 수행평가\n" + "가짜 항목 근거\n" * 23
        (pack / f"{doc}.md").write_text(text, encoding="utf-8")
        index.append({"doc_id": doc, "school_id": SCHOOL, "school_name": "가상학교",
                      "line_count": 24, "sha256": hashlib.sha256(text.encode()).hexdigest()})
        documents.append({"type": "document", "doc_id": doc, "school_id": SCHOOL,
                          "labeler": "claude", "edition": "valid", "edition_note": "합성",
                          "notes": "", "science_sections": []})
    (pack / "index.json").write_text(json.dumps(index), encoding="utf-8")
    items = []
    for number in range(1, 5):
        doc, line = DOCS[number % 2], number * 4
        loc = {"doc_id": doc, "line": line}
        fields = {name: {"status": "source_absent", "values": []} for name in (
            "task_text", "task_no", "period", "method", "max_score", "sub_scores", "ratio",
            "rubric")}
        items.append({"type": "item", "school_id": SCHOOL, "labeler": "claude",
                      "grade": 1, "semester": 1, "item_key": f"{SCHOOL}-g1-s1-{number:02d}",
                      "occurrences": [loc], "identity_basis": "합성 번호", "free_semester": False,
                      "title": {"status": "present",
                                "values": [{"raw": f"가상 과제 {number}", "loc": loc}],
                                "role": "과제명"},
                      "standards": [{"status": "source_absent", "values": [], "codes": []}],
                      **fields})
    left = documents + items
    right = copy.deepcopy(left)
    for row in right:
        row["labeler"] = "astra"
    for i in range(3):
        loc = items[i]["occurrences"][0]
        items[i]["activity"] = activity(secondary=["작성", "분석"] if i == 0 else [],
                                        line=loc["line"], doc=loc["doc_id"])
    right[2]["activity"] = copy.deepcopy(items[0]["activity"])
    right[2]["activity"]["secondary"].reverse()
    right[2]["activity"]["evidence"][0]["quote"] = "B의 다른 인용"
    right[3]["activity"] = activity("작성", ["분석"], line=8, doc=DOCS[0])
    right[3]["item_key"] = f"{SCHOOL}-g1-s1-99"
    a, b = write_jsonl(tmp_path / "a.jsonl", left), write_jsonl(tmp_path / "b.jsonl", right)
    return SimpleNamespace(pack=pack, a=a, b=b, left=left, right=right, items=items)


def test_roster_mapping_and_override(tmp_path, gold2_modules):
    select = gold2_modules.middle_rounds.roster_path
    for round_no in (1, 3):
        for suffix, filename in (("gold2", "middle-gold2-5.csv"), ("gold", "middle-gold10.csv"),
                                 ("dev2", "middle-dev2-20.csv")):
            assert select(tmp_path, f"2026-round-{round_no}-{suffix}").name == filename
    assert select(tmp_path, "2026-round-3").name == "middle-dev12.csv"
    assert select(tmp_path, "2026-round-3-gold2", Path("custom.csv")) == tmp_path / "custom.csv"
    absolute = tmp_path / "absolute.csv"
    assert select(tmp_path, "2026-round-3-gold2", absolute) == absolute


def test_gold2_audit_scopes_use_roster_size(tmp_path, gold2_modules, monkeypatch):
    round_key = "2026-round-3-gold2"
    segments = tmp_path / f"data/derived/segments/{round_key}.json"
    segments.parent.mkdir(parents=True)
    segments.write_text(json.dumps({"round": round_key, "documents": [], "incomplete_sources": []}),
                        encoding="utf-8")
    roster = tmp_path / "roster.csv"
    roster.write_text("school_code\n1\n2\n3\n4\n5\n", encoding="utf-8")
    subjects = importlib.import_module("audit_middle_subjects")
    items = importlib.import_module("audit_middle_items")
    monkeypatch.setattr(subjects, "ROOT", tmp_path)
    monkeypatch.setattr(items, "ROOT", tmp_path)
    report = subjects.audit(segments, roster)
    assert report["scope"].startswith("정답 5개교")
    input_path = tmp_path / "subjects.json"
    input_path.write_text(json.dumps(report), encoding="utf-8")
    assert items.audit(input_path, roster)["scope"].startswith("정답 5개교")


def test_gold2_segments_keep_gold_sources_and_custom_roster(tmp_path, gold2_modules, monkeypatch):
    module = importlib.import_module("audit_middle_segments")
    round_key = "2026-round-3-gold2"
    raw = tmp_path / f"data/raw/schoolinfo/4ga_rounds/{round_key}/synthetic.hwp"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"synthetic")
    manifest = tmp_path / f"data/derived/schoolinfo_4ga/{round_key}/attachments.jsonl"
    manifest.parent.mkdir(parents=True)
    write_jsonl(manifest, [{"result": "downloaded",
                           "saved_path": raw.relative_to(tmp_path).as_posix(),
                           "school_code": "selected", "candidate_name": "가짜 규정.hwp"}])
    roster = tmp_path / "custom.csv"
    roster.write_text("school_code\nselected\n", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "plan_status", lambda _: "non_plan_filename")

    def reached_conversion(*args, **kwargs):
        raise RuntimeError("selected gold2 source reached conversion")

    monkeypatch.setattr(module, "audit_document", reached_conversion)
    monkeypatch.setattr(sys, "argv", ["audit", "--round-key", round_key,
                                     "--roster", roster.name])
    with pytest.raises(RuntimeError, match="selected gold2 source reached conversion"):
        module.main()


@pytest.mark.parametrize("rounds", [(1, 3), (3,)])
def test_source_pack_run_label_and_cli(tmp_path, gold2_modules, monkeypatch, rounds):
    source = gold2_modules.gold_source_pack
    for number in rounds:
        raw = tmp_path / f"original-{number}.hwp"
        raw.write_bytes(f"synthetic {number}".encode())
        manifest = tmp_path / (
            f"data/derived/schoolinfo_4ga/2026-round-{number}-gold2/attachments.jsonl")
        manifest.parent.mkdir(parents=True)
        write_jsonl(manifest, [{"result": "downloaded", "saved_path": raw.name,
                               "sha256": source.sha256(raw), "school_id": SCHOOL,
                               "school_name": "가상학교", "disclosure_round": number,
                               "candidate_name": raw.name}, {"result": "excluded"}])
    guide, schema, out = tmp_path / "guide.md", tmp_path / "schema.json", tmp_path / "sealed"
    guide.write_text("Synthetic guide", encoding="utf-8")
    schema.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(source, "extract_document", lambda *a, **kw: {
        "converter": "kordoc", "conversion_status": "ok", "text": "Synthetic conversion\n"})
    monkeypatch.setattr(sys, "argv", ["gold_source_pack.py", "--project-root", str(tmp_path),
                                     "--output", str(out), "--run-label", "gold2",
                                     "--guide", str(guide), "--schema", str(schema),
                                     "--rounds", *map(str, rounds)])
    source.main()
    seal = json.loads((out / "SEAL.json").read_text(encoding="utf-8"))
    assert seal["run_label"] == "gold2" and seal["rounds"] == list(rounds)
    assert seal["source_count"] == len(rounds)
    assert seal["guide"]["sha256"] == source.sha256(guide)
    assert seal["schema"]["sha256"] == source.sha256(schema)
    assert gold2_modules.gold_score.seal_check(tmp_path, out)["mismatches"] == []


@pytest.mark.parametrize("bad", [None, "primary", "secondary", "extra"])
def test_gold2_validate_schema(tmp_path, bundle, gold2_modules, bad):
    rows = copy.deepcopy(bundle.left)
    if bad == "primary":
        rows[2]["activity"]["primary"] = "허용되지 않는 활동"
    elif bad == "secondary":
        rows[2]["activity"]["secondary"] = ["작성", "작성"]
    elif bad == "extra":
        rows[2]["activity"]["invented"] = True
    labels = write_jsonl(tmp_path / "labels.jsonl", rows)
    schema = PROJECT / "data/reference/gold2_label_schema.json"
    errors = gold2_modules.gold_validate.validate_file(labels, bundle.pack, schema)
    assert bool(errors) == (bad is not None), errors
    result = cli("gold_validate.py", labels, "--pack-dir", bundle.pack, "--schema", schema)
    assert result.returncode == (1 if bad else 0), result.stdout + result.stderr


def test_diff_activity_rows_summary_and_cli(bundle, gold2_modules):
    diff = gold2_modules.gold_diff
    rows, summary = diff.compare_labels(bundle.left, bundle.right, bundle.pack)
    assert [row["필드"] for row in rows] == [
        "activity.primary", "activity.secondary", "activity.missing"]
    assert summary["activity"] == {"pairs_with_both": 2, "primary_agree": 1, "secondary_agree": 1}
    assert all(row[col] == "" for row in rows for col in ("A값", "B값", "원문 위치", "원문 발췌"))
    strict_rows, strict_summary = diff.compare_labels(
        bundle.left, bundle.right, bundle.pack, strict=True)
    assert strict_rows == [] and "activity" not in strict_summary
    result = cli("gold_diff.py", bundle.a, bundle.b, "--pack-dir", bundle.pack,
                 "--schema", PROJECT / "data/reference/gold2_label_schema.json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (bundle.pack.parent / "disagreements.csv").is_file()
    summary = json.loads((bundle.pack.parent / "agreement.json").read_text(encoding="utf-8"))
    assert summary["v2"]["activity"]["pairs_with_both"] == 2


def test_null_primary_and_secondary_sets(bundle, gold2_modules):
    left, right = copy.deepcopy(bundle.left), copy.deepcopy(bundle.right)
    left[2]["activity"].update(primary=None, abstain_reason="근거 없음")
    right[2]["activity"].update(primary=None, abstain_reason="근거 동률")
    rows, summary = gold2_modules.gold_diff.compare_labels(left, right, bundle.pack)
    assert summary["activity"]["primary_agree"] == 1
    assert all(row["A항목키"] != left[2]["item_key"] for row in rows)


@pytest.fixture
def adjudicated(tmp_path, bundle, gold2_modules):
    diff, rules = gold2_modules.gold_diff, gold2_modules.gold_adjudicate
    rows, summary = diff.compare_labels(bundle.left, bundle.right, bundle.pack)
    disagreements = tmp_path / "disagreements.csv"
    diff.write_reports(rows, summary, disagreements)
    answers = tmp_path / "answers.csv"
    answers.write_text("질문번호,답\n", encoding="utf-8-sig")
    out = tmp_path / "adjudicated"
    result = rules.run(bundle.a, bundle.b, disagreements, bundle.pack, out, answers)
    assert result["remaining_questions"] == result["input_disagreements"] == 0
    return out / "gold_v1.jsonl"


def test_adjudicate_preserves_activity_and_pack_omits_it(
    adjudicated, bundle, gold2_modules, tmp_path,
):
    for name in ("gold_v1.jsonl", "gold_v1_draft.jsonl"):
        rows = read_jsonl(adjudicated.parent / name)
        items = [row for row in rows if row["type"] == "item"]
        assert len(items) == 4
        for i, row in enumerate(items):
            assert "activity" not in row
            assert row["activity_a"] == bundle.left[i + 2].get("activity")
            assert row["activity_b"] == bundle.right[i + 2].get("activity")
    out = tmp_path / "activity-items.jsonl"
    result = gold2_modules.gold_activity_pack.main(["--gold", str(adjudicated), "--out", str(out)])
    assert result == 0
    assert len(read_jsonl(out)) == 4
    assert all(not {"activity", "activity_a", "activity_b"} & row.keys() for row in read_jsonl(out))


def test_ib_rule_does_not_apply_to_gold2(bundle, gold2_modules):
    merged = copy.deepcopy(bundle.items[0])
    merged["school_id"] = "ms-gold2-jeonbuk-gun"
    merged["sub_scores"] = {"status": "present", "values": [
        {"raw": "15점", "name": f"평가기준{letter}", "norm": 15,
         "loc": merged["occurrences"][0]} for letter in ("A", "B")]}
    split = [copy.deepcopy(merged) for _ in range(2)]
    for row, letter in zip(split, ("A", "B"), strict=True):
        row["title"]["values"][0]["raw"] = f"평가기준{letter}"
    assert gold2_modules.gold_adjudicate.ib_groups([merged], split, object()) == ({}, {})


def test_activity_merge_pending_agreement_single_and_hashes(adjudicated, tmp_path, bundle):
    out = tmp_path / "activity"
    result = cli("gold_activity_merge.py", "--gold", adjudicated, "--out-dir", out)
    assert result.returncode == 2, result.stdout + result.stderr
    meta = json.loads((out / "gold_activity.meta.json").read_text(encoding="utf-8"))
    assert meta["sources"] == {"합의": 1, "결정": 0, "단독": 1, "미결": 2}
    assert meta["pending"] == [bundle.items[i]["item_key"] for i in (1, 3)]
    labels = read_jsonl(out / "gold_activity.jsonl")
    assert len(labels) == 2
    assert labels[0]["evidence"] == bundle.items[0]["activity"]["evidence"]
    assert meta["sha256"] == hashlib.sha256((out / "gold_activity.jsonl").read_bytes()).hexdigest()
    assert meta["inputs"]["gold"]["sha256"] == hashlib.sha256(adjudicated.read_bytes()).hexdigest()


def test_activity_merge_decisions_abstention_alias_and_validation(adjudicated, bundle, tmp_path):
    decisions = tmp_path / "decisions.csv"
    with decisions.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["item_key", "primary", "secondary", "source",
                                                   "note", "abstain_reason"])
        writer.writeheader()
        writer.writerows([
            {"item_key": bundle.items[0]["item_key"], "primary": "작성", "secondary": "",
             "source": "A", "note": "합의 항목의 결정은 합의를 덮지 않음"},
            {"item_key": bundle.right[3]["item_key"], "primary": "작성", "secondary": "분석;탐구",
             "source": "B", "note": "가짜 결정"},
            {"item_key": bundle.items[3]["item_key"], "primary": "(기권)", "secondary": "",
             "source": "결정", "note": "합성", "abstain_reason": "근거 없음"}])
    out = tmp_path / "merged"
    result = cli("gold_activity_merge.py", "--gold", adjudicated, "--decisions", decisions,
                 "--out-dir", out)
    assert result.returncode == 0, result.stdout + result.stderr
    labels = read_jsonl(out / "gold_activity.jsonl")
    assert labels[0]["primary"] == "탐구"
    assert labels[1]["evidence"] == bundle.right[3]["activity"]["evidence"]
    assert labels[1]["secondary"] == ["분석", "탐구"]
    assert labels[3]["primary"] is None and labels[3]["abstain_reason"] == "근거 없음"
    items = tmp_path / "activity-items.jsonl"
    result = cli("gold_activity_pack.py", "--gold", adjudicated, "--out", items)
    assert result.returncode == 0, result.stderr
    result = cli("gold_activity_validate.py", out / "gold_activity.jsonl", "--items", items,
                 "--expect-version", "activity-def-v2")
    assert result.returncode == 0, result.stdout + result.stderr
    result = cli("gold_activity_diff.py", "--a", out / "gold_activity.jsonl", "--b",
                 out / "gold_activity.jsonl", "--items", items, "--out", out / "diff")
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("total", [None, 9])
def test_activity_score_total_cli(tmp_path, gold2_modules, total):
    items = write_jsonl(tmp_path / "items.jsonl", [
        {"type": "item", "item_key": f"fake-{i}"} for i in range(3)])
    labels = write_jsonl(tmp_path / "labels.jsonl", [
        {"item_key": f"fake-{i}", "primary": "탐구"} for i in range(3)])
    pairs = tmp_path / "pairs.csv"
    pairs.write_text("type,key,rule_ai_found,rule_ai_pipeline_key\n", encoding="utf-8")
    axes = tmp_path / "axes.json"
    axes.write_text('{"round": "fake", "items": []}', encoding="utf-8")
    out = tmp_path / "score"
    args = ["--axes", axes, "--gold-activity", labels, "--gold-items", items,
            "--pairs", pairs, "--out-dir", out]
    if total is not None:
        args += ["--gold-total", total]
    result = cli("gold_activity_score.py", *args)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((out / "gold-axes-v1.json").read_text(encoding="utf-8"))
    assert report["gold_total"] == (3 if total is None else total)
    assert report["metrics"]["paired"]["denominator"] == report["gold_total"]


def test_score_reads_alternate_gold_directory(tmp_path, bundle, gold2_modules):
    root = tmp_path
    selected = tmp_path / "alternative"
    selected.mkdir()
    pack = selected / "pack"
    pack.mkdir()
    for path in bundle.pack.iterdir():
        (pack / path.name).write_bytes(path.read_bytes())
    raw = selected / "raw"
    raw.mkdir()
    (raw / "source.hwp").write_bytes(b"fake original")
    (root / "original.hwp").write_bytes(b"fake original")
    for name in ("guide.md", "schema.json"):
        (root / name).write_bytes(b"synthetic specification")
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    seal = {"sources": [{"sha256": digest(raw / "source.hwp"), "original_path": "original.hwp",
                         "raw_path": "raw/source.hwp"}],
            "pack_files": [{"path": f"pack/{p.name}", "sha256": digest(p)} for p in pack.iterdir()],
            "guide": {"path": "guide.md", "sha256": digest(root / "guide.md")},
            "schema": {"path": "schema.json", "sha256": digest(root / "schema.json")}}
    (selected / "SEAL.json").write_text(json.dumps(seal), encoding="utf-8")
    mapper = gold2_modules.gold_score.SourceMap(root, [], selected)
    assert set(mapper.pack) == set(DOCS)
    assert gold2_modules.gold_score.seal_check(root, selected) == {"checked": 7, "mismatches": []}
    (raw / "source.hwp").write_bytes(b"changed")
    assert gold2_modules.gold_score.seal_check(root, Path("alternative"))["mismatches"] == [
        str(Path("alternative/raw/source.hwp"))]


def test_legacy_diff_and_adjudication_bytes(tmp_path, bundle, gold2_modules, monkeypatch):
    baseline = {}
    for name in ("gold_diff", "gold_adjudicate"):
        result = subprocess.run(["git", "show", f"HEAD:scripts/{name}.py"], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", check=True)
        module = ModuleType(f"baseline_{name}")
        monkeypatch.setitem(sys.modules, module.__name__, module)
        exec(compile(result.stdout, f"baseline_{name}.py", "exec"), module.__dict__)
        baseline[name] = module
    for rows in (bundle.left, bundle.right):
        for row in rows:
            row.pop("activity", None)
    write_jsonl(bundle.a, bundle.left)
    write_jsonl(bundle.b, bundle.right)
    old_rows, old_summary = baseline["gold_diff"].compare_labels(
        bundle.left, bundle.right, bundle.pack)
    rows, summary = gold2_modules.gold_diff.compare_labels(bundle.left, bundle.right, bundle.pack)
    assert (rows, summary) == (old_rows, old_summary)
    outputs = [tmp_path / name for name in ("before", "after")]
    for module, out in zip((baseline["gold_diff"], gold2_modules.gold_diff), outputs, strict=True):
        module.write_reports(rows, summary, out / "differences.csv")
    for path in outputs[0].iterdir():
        assert path.read_bytes() == (outputs[1] / path.name).read_bytes()
    answers = tmp_path / "answers.csv"
    answers.write_text("질문번호,답\n", encoding="utf-8-sig")
    for module, out in zip((baseline["gold_adjudicate"], gold2_modules.gold_adjudicate),
                           outputs, strict=True):
        module.run(bundle.a, bundle.b, out / "differences.csv", bundle.pack, out, answers)
    for path in outputs[0].iterdir():
        assert path.read_bytes() == (outputs[1] / path.name).read_bytes()
