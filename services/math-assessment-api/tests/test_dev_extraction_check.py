"""tmp_path의 합성 표본·항목·Markdown으로 개발 대조기의 CLI와 집계를 검사한다.

Run/Verify: .venv/Scripts/python.exe -m pytest -q
            services/math-assessment-api/tests/test_dev_extraction_check.py
Lint: .venv/Scripts/python.exe -m ruff check scripts/dev_extraction_check.py
      services/math-assessment-api/tests/test_dev_extraction_check.py
"""

import copy
import json

import pytest
from scripts import dev_extraction_check as check


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8-sig")
    return path


def item(identifier, title, method=None, school="합성중", **changes):
    result = {
        "item_id": identifier, "school": school, "grade": 1, "semester": 2,
        "candidate_role": "performance", "extraction_status": "bounded",
        "layout": "table", "layout_position": {"table": 1, "row": 2},
        "fields": {"title": {"value": title}, "method": {"value": method}},
    }
    result.update(changes)
    return result


def section(cell, rows, school="합성중", ending=None):
    lines = [f"### {cell} {school} 중1 2학기", "",
             "| 제목 | 만점 | 비율 | 평가 방법 | 평가 주체·형태 | 근거(줄) |",
             "|---|---|---|---|---|---|"]
    lines += [f"| {title} | 100 | 20 | {method} | 교사 | 12 |" for title, method in rows]
    lines += [ending if ending is not None else f"개수: {len(rows)}", "확신이 낮은 점: 없음"]
    return "\n".join(lines)


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(check, "ROOT", tmp_path)
    cells = [{"cell_id": "S01", "round": "test-round", "school": school,
              "grade": 1, "semester": 2} for school in ("합성중", "다른중")]
    samples = [write_json(tmp_path / f"sample-{prefix}.json", {"source_review": [cell]})
               for prefix, cell in zip(("A", "B"), cells, strict=True)]
    items = [item("exact", "실험 평가", ["관찰", "보고서"]),
             item("spaces", "탐구발표", ["관찰", "보고서"]),
             item("summary", "자료 해석", []),
             item("unknown", "자유 탐구", ["관찰"]),
             item("extra", "추가 항목", [])]
    items[3]["fields"]["method"]["state"] = "unknown"
    write_json(tmp_path / "data/derived/items/test-round.json", {"items": items})
    rows = [("실험 평가", "보고서/관찰"), ("탐구 발표", "관찰"),
            ("포스터 만들기 (자료 해석)", "보고서"), ("자유 탐구", "확실하지 않음")]
    result = tmp_path / "review.md"
    result.write_text(section("A-S01", rows) + "\n" + section("B-S01", [], "다른중"),
                      encoding="utf-8-sig")
    args = ["--result", str(result), "--sample", f"A={samples[0]}",
            "--sample", f"B={samples[1]}", "--out-prefix", str(tmp_path / "output")]
    return {"root": tmp_path, "items": items, "result": result, "args": args}


def run(data, extra=()):
    assert check.main([*data["args"], *extra]) == 0
    return json.loads((data["root"] / "output.json").read_text(encoding="utf-8"))


def test_cli_two_cells_and_metrics(synthetic):
    result = run(synthetic)
    assert list(result["cells"]) == ["A-S01", "B-S01"]
    assert result["items"] == {"precision": {"num": 4, "den": 5},
                               "recall": {"num": 4, "den": 4}}
    assert result["method"]["accuracy"] == {"num": 2, "den": 4}
    assert result["method"]["outcomes"] == {
        "정답": 2, "오값-여러값": 1, "오값-한값": 0, "누락": 1, "허위": 0}
    assert result["unmatched_pipeline"] == [{"cell": "A-S01", "item_id": "extra",
        "title": "추가 항목", "layout": "table", "layout_position": {"table": 1, "row": 2}}]
    assert result["unmatched_astra"] == []
    assert [row["outcome"] for row in result["method_wrong"]] == ["오값-여러값", "누락"]
    md = (synthetic["root"] / "output.md").read_text(encoding="utf-8")
    for text in ("4/5", "4/4", "2/4", "items.precision.num", "items.recall.den",
                 "method.accuracy.num", "method.outcomes.누락", "추가 항목", "탐구 발표"):
        assert text in md


def test_filtering_and_snapshot_ai_preference(synthetic):
    items = copy.deepcopy(synthetic["items"])
    items[0]["extraction_status"] = "ai_verified"
    for changes in ({"extraction_status": "review"}, {"candidate_role": "teaching_plan"},
                    {"grade": 2}, {"semester": 1}, {"school": "표본밖중"}):
        items.append(item(str(changes), "추가 항목", [], **changes))
    root = synthetic["root"]
    write_json(root / "data/derived/items/test-round.prev-s18.json", {"items": []})
    write_json(root / "data/derived/items_ai/test-round.prev-s18.json", {"items": items})
    assert run(synthetic, ["--suffix", ".prev-s18"])["items"]["precision"] == {"num": 4, "den": 5}
    write_json(root / "data/derived/items/test-round.fallback.json", {"items": []})
    result = run(synthetic, ["--suffix", ".fallback"])
    assert result["items"]["precision"] == {"num": 0, "den": 0}
    assert len(result["unmatched_astra"]) == 4


@pytest.mark.parametrize(("expected", "actual", "state", "outcome"), [
    ("", [], None, "정답"), ("없음", "", None, "정답"),
    ("관찰;보고서/발표", ["발표", "보고서,관찰"], None, "정답"),
    ("관 찰", "관찰", None, "정답"), ("관찰", "보고서", None, "오값-한값"),
    ("관찰", ["보고서", "발표"], None, "오값-여러값"),
    ("관찰", [], "unknown", "누락"), ("없음", ["관찰"], None, "허위"),
    ("확실하지 않음", [], None, "정답"),
    ("확실하지 않음", ["관찰"], "unknown", "정답"),
    ("확실하지 않음", ["관찰"], "known", "오값-한값"),
    ("확실하지 않음", ["관찰", "보고서"], "known", "오값-여러값"),
    ("확실하지 않음", "확실하지 않음", None, "오값-한값"),
])
def test_method_rules(expected, actual, state, outcome):
    pipeline = item("id", "제목", actual)
    pipeline["fields"]["method"]["state"] = state
    assert check.method_outcome(expected, pipeline) == outcome


def test_pair_priority_and_alternate_fields():
    astra = [{"제목": t} for t in ("에너지탐구", "기체실험", "질량측정", "물질분석", "짧음")]
    pipeline = [item("contains", "에너지탐구수행"), item("exact", "에너지 탐구"),
                item("area", "일반 제목"), item("task", "다른 제목"),
                item("top-area", "별도 제목", assessment_area="물질분석"),
                item("short", "짧음평가")]
    pipeline[0]["fields"]["assessment_area"] = {"value": "에너지탐구"}
    pipeline[2]["fields"]["assessment_area"] = {"value": "기체실험"}
    pipeline[3]["fields"]["task_text"] = {"value": "질량측정과기록"}
    pairs, only_a, only_p, _, _ = check.pair_items(astra, pipeline, [])
    assert {(a, pipeline[p]["item_id"]) for a, p, _ in pairs} == {
        (0, "exact"), (1, "area"), (2, "task"), (3, "top-area")}
    assert only_a == [4]
    assert only_p == [0, 5]
    # Exact edges are considered across the whole cell before containment edges.
    pairs, _, _, _, _ = check.pair_items(
        [{"제목": "에너지탐구수행"}, {"제목": "에너지탐구"}], pipeline[:2], [])
    assert {(a, p) for a, p, _ in pairs} == {(0, 0), (1, 1)}


def test_normalization_and_parenthesis_keys():
    assert check.normalize(" Ab <BR />실험·‘평가’! ") == "ab실험평가"
    for text in ("포스터 (자료 해석)", "포스터（자료 해석）"):
        assert "자료해석" in check.candidate_keys(text)
        assert "포스터" in check.candidate_keys(text)


def test_overrides_take_precedence(synthetic):
    overrides = [
        {"cell": "A-S01", "astra_title": "실험 평가", "pipeline_item_id": "extra",
         "verdict": "same", "note": "독립 판정"},
        {"cell": "A-S01", "pipeline_item_id": "exact", "verdict": "pipeline_extra_ok"},
        {"cell": "A-S01", "astra_title": "탐구 발표", "verdict": "astra_extra_ok"},
    ]
    path = write_json(synthetic["root"] / "overrides.json", overrides)
    result = run(synthetic, ["--overrides", str(path)])
    cell = result["cells"]["A-S01"]
    assert cell["pairs"][0]["pipeline_item_id"] == "extra"
    assert cell["pairs"][0]["reason"] == "override"
    assert cell["accepted_pipeline"] == ["exact"]
    assert cell["accepted_astra"][0]["제목"] == "탐구 발표"
    assert result["items"] == {"precision": {"num": 4, "den": 5},
                               "recall": {"num": 4, "den": 4}}
    assert result["method"]["accuracy"]["den"] == 3
    assert result["unmatched_pipeline"][0]["item_id"] == "spaces"


def test_conflicting_override_is_error(synthetic):
    override = {"cell": "A-S01", "astra_title": "실험 평가",
                "pipeline_item_id": "exact", "verdict": "same"}
    path = write_json(synthetic["root"] / "overrides.json", [override, override])
    with pytest.raises(SystemExit, match="2"):
        run(synthetic, ["--overrides", str(path)])


def test_unreadable_cells_excluded_but_low_confidence_kept(synthetic):
    result_path = synthetic["result"]
    result_path.write_text(section("A-S01", [], ending="개수: 판독 불가") + "\n" +
                           section("B-S01", [], "다른중").replace(
                               "확신이 낮은 점: 없음", "확신이 낮은 점: 한 문서 판독 불가"),
                           encoding="utf-8")
    result = run(synthetic)
    assert result["unreadable_cells"] == ["A-S01"]
    assert result["items"]["precision"] == {"num": 0, "den": 0}
    assert result["method"]["accuracy"] == {"num": 0, "den": 0}
    assert result["unmatched_pipeline"] == []


@pytest.mark.parametrize("text", ["### A-S01 합성중 중1 2학기\n0건",
                                      section("A-S01", [])])
def test_zero_cell_forms(tmp_path, text):
    path = tmp_path / "result.md"
    path.write_text(text, encoding="utf-8")
    assert check.parse_result(path)["A-S01"]["astra"] == []


@pytest.mark.parametrize("kind", ["missing", "count", "coordinate", "duplicate"])
def test_invalid_markdown_rejected(synthetic, kind):
    path = synthetic["result"]
    text = path.read_text(encoding="utf-8-sig")
    if kind == "missing":
        text = text.split("### B-S01")[0]
    elif kind == "count":
        text = text.replace("개수: 4", "개수: 5")
    elif kind == "coordinate":
        text = text.replace("합성중 중1", "잘못된중 중1")
    else:
        text += "\n" + section("A-S01", [])
    path.write_text(text, encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        run(synthetic)
    assert not (synthetic["root"] / "output.json").exists()


@pytest.mark.parametrize("option", ["--result", "--sample", "--overrides", "--suffix",
                                    "--out-prefix"])
def test_forbidden_paths_rejected_before_access(synthetic, option, capsys):
    value = ".GoLd" if option == "--suffix" else str(synthetic["root"] / "GoLd-forbidden")
    args = list(synthetic["args"])
    if option == "--sample":
        args[args.index(option) + 1] = f"A={value}"
    elif option in args:
        args[args.index(option) + 1] = value
    else:
        args.extend((option, value))
    with pytest.raises(SystemExit, match="2"):
        check.main(args)
    assert "gold 경로 거부" in capsys.readouterr().err
    assert not (synthetic["root"] / "output.json").exists()
