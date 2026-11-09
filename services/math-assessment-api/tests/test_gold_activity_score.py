"""가짜 두 회차 및 83개 라벨로 활동 채점기의 집계·출력을 검사한다.

Run/Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
            services/math-assessment-api/tests/test_gold_activity_score.py
실제 정답 파일을 읽지 않으며 임시 경로에 합성 입력만 작성한다.
"""

import csv
import json
from fractions import Fraction

import pytest
from scripts import gold_activity_score as score


def synthetic_data():
    labels, items, pairs, axes = [], [], [], {}
    for number in range(83):
        key = f"fake-{number}"
        primary = "탐구" if number < 10 else "작성"
        if number == 12:
            primary = None
        secondary = ["작성"] if number == 0 else (["분석"] if number == 1 else [])
        labels.append({"item_key": key, "primary": primary, "secondary": secondary})
        codes = ["[9과01-01]"] if number != 12 else ["[9과02-01]"]
        groups = [{"codes": codes, "status": "present"}]
        if number in (10, 11):
            groups = [{"codes": ["[9과03-01]"], "status": "source_absent"}]
        items.append({"type": "item", "item_key": key, "fields": {
            "standards": {"value": groups}, "title": {"value": {"role": "과제명"}}},
            "representative_title": {"raw": "가짜 제목"}})
        round_name = "synthetic-a" if number < 7 else "synthetic-b"
        pipeline_key = f"{round_name}/i{number}"
        pairs.append({"type": "gold", "key": key,
                      "rule_ai_found": "True" if number < 14 else "False",
                      "rule_ai_pipeline_key": pipeline_key})
        if number >= 13:
            continue
        predicted = "탐구" if number <= 7 or number == 10 else "작성"
        if number in (9, 11, 12):
            predicted = None
        areas = ["01"]
        if number == 8:
            areas = ["01", "02"]
        elif number in (9, 11):
            areas = []
        elif number == 12:
            areas = ["02"]
        predicted_secondary = ["작성", "분석"] if number == 0 else (["탐구"] if number == 1 else [])
        axes[pipeline_key] = {"item_id": f"i{number}",
            "unit": {"areas": [{"area_no": area} for area in areas],
                     "status": "confirmed" if areas else "undetermined"},
            "activity": {"primary": predicted, "secondary": predicted_secondary,
                         "abstain_reason": "동률" if predicted is None else None,
                         "rule_applied": "R6"}}
    items.append({"type": "header", "item_key": "ignored"})
    pairs.append({"type": "dev", "key": "ignored", "rule_ai_found": "True"})
    return axes, labels, items, pairs


@pytest.fixture
def report():
    return score.evaluate(*synthetic_data())


def assert_metric(actual, numerator, denominator):
    assert actual["numerator"] == numerator
    assert actual["denominator"] == denominator
    assert actual["fraction"] == f"{numerator}/{denominator}"
    assert (
        actual["rate"] == pytest.approx(numerator / denominator)
        if denominator else actual["rate"] is None
    )


def test_pairing_counts_missing_found_prediction_as_unmatched(report):
    assert_metric(report["metrics"]["paired"], 13, 83)
    assert_metric(report["metrics"]["unmatched"], 70, 83)
    assert len(report["items"]) == 83
    assert report["items"][13]["result"] == "짝 없음"
    assert report["items"][14]["item_id"] == ""
    assert_metric(report["metrics"]["overall_primary_accuracy"], 9, 83)


def test_unit_exact_partial_empty_and_source_absent(report):
    units = report["metrics"]["units"]
    assert_metric(units["exact"], 9, 11)
    assert_metric(units["partial"], 10, 11)
    assert_metric(units["undetermined"], 1, 11)
    assert_metric(units["gold_unit_absent"], 2, 13)
    assert_metric(units["prediction_without_gold"], 1, 2)
    assert report["items"][8]["unit_result"] == "부분 일치"
    assert report["items"][9]["unit_result"] == "미결정"


def test_activity_denominators_and_gold_abstention(report):
    activity = report["metrics"]["activity"]
    assert_metric(activity["accuracy_all"], 8, 12)
    assert_metric(activity["accuracy_classified"], 8, 10)
    assert_metric(activity["coverage"], 10, 12)
    assert_metric(activity["abstention"], 3, 13)
    assert_metric(activity["gold_abstention_agreement"], 1, 1)
    assert report["confusion"]["탐구"]["탐구"] == 8
    assert report["confusion"]["탐구"]["작성"] == 1
    assert report["confusion"]["탐구"]["기권"] == 1
    assert report["confusion"]["기권"]["기권"] == 1


def test_precision_recall_f1_and_macro_support_threshold(report):
    inquiry = report["per_activity"]["탐구"]
    assert inquiry["gold_positive"] == 10
    assert_metric(inquiry["precision"], 8, 9)
    assert_metric(inquiry["recall"], 8, 10)
    assert_metric(inquiry["f1"], 16, 19)
    activity = report["metrics"]["activity"]
    assert activity["macro_f1_activities"] == {"탐구": 10}
    assert_metric(activity["macro_f1"], 16, 19)


def test_secondary_jaccard_exact_and_subset(report):
    secondary = report["metrics"]["secondary"]
    assert_metric(secondary["jaccard_mean"], 23, 26)
    assert secondary["jaccard_mean"]["count"] == 13
    assert_metric(secondary["exact"], 11, 13)
    assert_metric(secondary["gold_subset"], 12, 13)


def test_multiple_standard_groups_and_deduplication():
    item = {"fields": {"standards": {"value": [
        {"codes": ["[9과01-01]", "[9과02-01]", "[9과01-02]"], "status": "present"},
        {"codes": ["[9과03-01]"], "status": "source_absent"},
        {"codes": [None, "bad", "[9과23-02]"], "status": "unresolved"}]}}}
    assert score.gold_areas(item) == {"01", "02", "23"}


def test_no_pairs_and_empty_denominators():
    axes, labels, items, pairs = synthetic_data()
    result = score.evaluate({}, labels, items, pairs)
    assert_metric(result["metrics"]["paired"], 0, 83)
    assert_metric(result["metrics"]["activity"]["accuracy_all"], 0, 0)
    assert_metric(result["metrics"]["secondary"]["jaccard_mean"], 0, 0)
    assert result["metrics"]["activity"]["macro_f1_activities"] == {}


def test_fraction_mean_preserves_exact_arithmetic():
    assert_metric(score.average_metric([Fraction(1, 3), Fraction(1, 2)]), 5, 12)


def write_synthetic_inputs(tmp_path):
    axes, labels, items, pairs = synthetic_data()
    paths = []
    for round_name in ("synthetic-a", "synthetic-b"):
        path = tmp_path / f"{round_name}.json"
        data = {"round": round_name, "items": [
            item for key, item in axes.items() if key.startswith(round_name + "/")
        ]}
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        paths.append(path)
    for name, data in (("labels", labels), ("items", items)):
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in data), encoding="utf-8"
        )
    with (tmp_path / "pairs.csv").open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(
            target, fieldnames=["type", "key", "rule_ai_found", "rule_ai_pipeline_key"]
        )
        writer.writeheader()
        writer.writerows(pairs)
    return ["--axes", *map(str, paths), "--gold-activity", str(tmp_path / "labels.jsonl"),
            "--gold-items", str(tmp_path / "items.jsonl"), "--pairs", str(tmp_path / "pairs.csv"),
            "--out-dir", str(tmp_path / "output")]


def test_synthetic_two_round_input_and_all_output_formats(tmp_path):
    args = write_synthetic_inputs(tmp_path)
    assert score.main(args + ["--name", "test.v1"]) == 0
    prefix = tmp_path / "output"
    data = json.loads((prefix / "test.v1.json").read_text(encoding="utf-8"))
    assert_metric(data["metrics"]["paired"], 13, 83)
    document = (prefix / "test.v1.md").read_text(encoding="utf-8")
    assert "16/19 (84.21%)" in document
    assert "탐구 10개" in document
    with (prefix / "test.v1.csv").open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 83
    assert rows[0]["item_id"] == "i0"
    assert rows[13]["result"] == "짝 없음"
    assert list(rows[0]) == list(score.CSV_FIELDS)


def test_input_error_and_duplicate_pipeline_key(tmp_path):
    args = write_synthetic_inputs(tmp_path)
    (tmp_path / "labels.jsonl").write_text("[]", encoding="utf-8")
    assert score.main(args) == 2
    path = tmp_path / "synthetic-a.json"
    with pytest.raises(ValueError, match="키 중복"):
        score.load_axes([path, path])


def test_missing_truth_item_and_duplicate_label_are_rejected():
    axes, labels, items, pairs = synthetic_data()
    with pytest.raises(ValueError, match="정답 항목 없음"):
        score.evaluate(axes, labels, [], pairs)
    with pytest.raises(ValueError, match="중복"):
        score.evaluate(axes, labels + [labels[0]], items, pairs)
