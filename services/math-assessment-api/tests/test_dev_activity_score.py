"""합성 라벨만으로 개발 채점기의 분수·진단·출력을 검사한다.

Run/Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
            services/math-assessment-api/tests/test_dev_activity_score.py
실제 개발 자료와 맹검 자료는 읽지 않는다.
"""

import csv
import hashlib
import json
from fractions import Fraction
from pathlib import Path

import pytest
from scripts import dev_activity_score as score


def synthetic_data():
    truth = ["탐구"] * 5 + ["작성", "작성", "분석", None, None]
    predicted = ["탐구", "탐구", "작성", None, "탐구", "작성", "탐구", None, None, "제작"]
    labels, axes = [], {}
    for number, (label, prediction) in enumerate(zip(truth, predicted, strict=True)):
        key = f"item-{number}"
        secondary = ["작성", "분석", "작성"] if number == 0 else (["분석"] if number == 1 else [])
        predicted_secondary = ["작성"] if number < 2 else (["제작"] if number == 2 else [])
        labels.append(
            {
                "item_id": key,
                "primary": label,
                "secondary": secondary,
                "rule_applied": "L1",
                "votes": {"탐구": 2},
                "votes_e": {"탐구": 1},
                "votes_s": {"작성": 1},
                "evidence": [{"quote": "합성 근거", "type": "rubric"}],
                "abstain_reason": "근거 없음" if label is None else None,
                "note": "확인 | 메모\n둘째 줄",
            }
        )
        axes[key] = {
            "item_id": key,
            "round": "synthetic-a" if number < 5 else "synthetic-b",
            "school": "합성학교",
            "grade": 1,
            "semester": 2,
            "title": f"합성 과제 {number}",
            "activity": {
                "primary": prediction,
                "secondary": predicted_secondary,
                "rule_applied": "R2",
                "candidates": ["탐구", "작성"],
                "abstain_reason": "동률" if prediction is None else None,
                "votes_e": {"탐구": 2},
                "votes_s": {"작성": 1},
            },
        }
    labels.append({"item_id": "missing", "primary": "분석", "secondary": []})
    return axes, labels


def assert_metric(actual, numerator, denominator):
    assert actual["numerator"] == numerator
    assert actual["denominator"] == denominator
    assert actual["fraction"] == f"{numerator}/{denominator}"
    if denominator:
        assert Fraction(actual["fraction"]) == Fraction(numerator, denominator)
        assert actual["rate"] == pytest.approx(float(Fraction(numerator, denominator)))
    else:
        assert actual["rate"] is None


@pytest.fixture
def report():
    return score.evaluate(*synthetic_data())


def test_accuracy_abstention_coverage_and_unmatched(report):
    expected = {
        "paired": (10, 11),
        "unmatched": (1, 11),
        "primary_accuracy_all": (5, 10),
        "primary_accuracy_labeled": (4, 8),
        "classifier_abstain_rate": (3, 10),
        "label_abstain_rate": (2, 10),
        "coverage": (6, 8),
    }
    for name, (numerator, denominator) in expected.items():
        assert_metric(report["metrics"][name], numerator, denominator)
    assert report["label_count"] == 11
    assert report["items"][-1]["result"] == "짝 없음"


def test_precision_recall_f1_and_macro_means(report):
    inquiry = report["per_activity"]["탐구"]
    assert (inquiry["label_positive"], inquiry["predicted_positive"], inquiry["true_positive"]) == (
        5,
        4,
        3,
    )
    assert_metric(inquiry["precision"], 3, 4)
    assert_metric(inquiry["recall"], 3, 5)
    assert_metric(inquiry["f1"], 6, 9)
    assert_metric(report["per_activity"]["작성"]["f1"], 2, 4)
    assert_metric(report["per_activity"]["분석"]["precision"], 0, 0)
    assert_metric(report["per_activity"]["분석"]["f1"], 0, 1)
    assert_metric(report["per_activity"]["제작"]["recall"], 0, 0)
    assert_metric(report["per_activity"]["문제해결"]["f1"], 0, 0)
    assert_metric(report["metrics"]["macro_f1_all"], 7, 18)
    assert report["metrics"]["macro_f1_all"]["activities"] == ["탐구", "작성", "분석"]
    assert report["metrics"]["macro_f1_all"]["count"] == 3
    assert_metric(report["metrics"]["macro_f1_min5"], 2, 3)
    assert report["metrics"]["macro_f1_min5"]["activities"] == ["탐구"]
    assert report["metrics"]["macro_f1_min5"]["count"] == 1


def test_jaccard_uses_sets_and_empty_sets_score_one(report):
    assert_metric(report["metrics"]["secondary_jaccard"], 3, 4)
    assert report["metrics"]["secondary_jaccard"]["count"] == 10
    assert_metric(score.average_metric([Fraction(1, 3), Fraction(1, 2)]), 5, 12)


def test_empty_pairs_and_empty_macro_targets():
    _, labels = synthetic_data()
    report = score.evaluate({}, labels)
    for name, value in report["metrics"].items():
        if name not in {"paired", "unmatched"}:
            assert_metric(value, 0, 0)
    assert report["metrics"]["macro_f1_all"]["activities"] == []
    assert_metric(score.evaluate({}, [])["metrics"]["paired"], 0, 0)


def test_mismatch_diagnostics_preserve_all_label_votes_and_quotes(report):
    assert len(report["mismatches"]) == 5
    row = report["mismatches"][0]
    assert set(row) == {
        "item_id",
        "round",
        "school",
        "grade",
        "semester",
        "title",
        "label_primary",
        "predicted_primary",
        "label_secondary",
        "predicted_secondary",
        "label_rule",
        "predicted_rule",
        "label_abstain_reason",
        "predicted_abstain_reason",
        "candidates",
        "votes_e",
        "votes_s",
        "label_votes",
        "label_evidence_quotes",
        "label_note",
    }
    assert row["item_id"] == "item-2"
    assert row["label_evidence_quotes"] == ["합성 근거"]
    assert row["label_votes"] == {
        "votes": {"탐구": 2},
        "votes_e": {"탐구": 1},
        "votes_s": {"작성": 1},
    }
    assert row["label_rule"] == "L1"
    assert row["predicted_rule"] == "R2"


def write_inputs(tmp_path):
    axes, labels = synthetic_data()
    paths = []
    for round_name in ("synthetic-a", "synthetic-b"):
        path = tmp_path / f"{round_name}.json"
        items = [
            {key: value for key, value in item.items() if key != "round"}
            for item in axes.values()
            if item["round"] == round_name
        ]
        path.write_text(
            json.dumps({"round": round_name, "items": items}, ensure_ascii=False),
            encoding="utf-8-sig",
        )
        paths.append(path)
    label_path = tmp_path / "labels.jsonl"
    label_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in labels), encoding="utf-8-sig"
    )
    return [
        "--axes",
        *map(str, paths),
        "--labels",
        str(label_path),
        "--out-dir",
        str(tmp_path / "output"),
        "--name",
        "synthetic",
    ]


def test_cli_outputs_hashes_and_confusion_row_column_totals(tmp_path):
    assert score.main(write_inputs(tmp_path)) == 0
    report = json.loads((tmp_path / "output/synthetic.json").read_text(encoding="utf-8-sig"))
    confusion = report["confusion"]
    assert len(confusion) == 11
    assert all(len(counts) == 11 for counts in confusion.values())
    row_totals = {name: sum(counts.values()) for name, counts in confusion.items()}
    column_totals = {name: sum(counts[name] for counts in confusion.values()) for name in confusion}
    assert sum(row_totals.values()) == sum(column_totals.values()) == 10
    assert row_totals["탐구"] == 5 and row_totals["기권"] == 2
    assert column_totals["탐구"] == 4 and column_totals["기권"] == 3
    assert report["items"][0]["round"] == "synthetic-a"
    for metadata in [*report["inputs"]["axes"], report["inputs"]["labels"]]:
        assert metadata["sha256"] == hashlib.sha256(Path(metadata["path"]).read_bytes()).hexdigest()
    md = (tmp_path / "output/synthetic.md").read_text(encoding="utf-8-sig")
    assert "## 혼동표" in md and "## 불일치 항목" in md
    assert "7/18" in md and "확인 \\| 메모<br>둘째 줄" in md
    with (tmp_path / "output/synthetic.csv").open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert list(rows[0]) == list(score.CSV_FIELDS)
    assert len(rows) == 11
    assert rows[-1]["result"] == "짝 없음"


def test_duplicate_ids_across_axes_files_return_input_error(tmp_path, capsys):
    args = write_inputs(tmp_path)
    path = tmp_path / "synthetic-b.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["items"][0]["item_id"] = "item-0"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert score.main(args) == 2
    assert "item_id 중복" in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--axes", "--labels", "--out-dir"])
def test_rejects_blind_paths_before_reading(tmp_path, option, capsys):
    args = write_inputs(tmp_path)
    args[args.index(option) + 1] = str(tmp_path / "GOLD-blocked")
    assert score.main(args) == 2
    assert "gold 경로 거부" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "content",
    [
        "[]",
        "{bad",
        '{"item_id":"a","primary":"unknown"}',
        '{"item_id":"a","primary":null,"secondary":null}',
    ],
)
def test_malformed_labels_return_input_error(tmp_path, content, capsys):
    args = write_inputs(tmp_path)
    (tmp_path / "labels.jsonl").write_text(content, encoding="utf-8")
    assert score.main(args) == 2
    assert capsys.readouterr().err
