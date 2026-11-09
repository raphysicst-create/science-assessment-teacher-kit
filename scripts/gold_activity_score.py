"""정답과 2축 분류 결과를 짝지어 지표 및 JSON/MD/CSV를 작성한다.

구현자는 돌리지 않는다. 정답 파일 실행은 부서장이 한다.
Run: .venv/Scripts/python.exe scripts/gold_activity_score.py --axes A.json B.json
     --gold-activity LABELS.jsonl --gold-items ITEMS.jsonl --pairs CASES.csv --out-dir OUT
Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
        services/math-assessment-api/tests/test_gold_activity_score.py
정답 83개를 전체 분모로 고정한다. 빈 보조 집합끼리의 Jaccard는 1이다.
"""

import argparse
import csv
import json
import re
import sys
from fractions import Fraction
from pathlib import Path

GOLD_TOTAL = 83
ACTIVITIES = ("탐구", "실험평가", "작성", "제작", "분석", "추론·설명", "발표·토론",
              "계산·측정", "과정평가", "문제해결")
ABSTAIN = "기권"
STANDARD_AREA = re.compile(r"\[9과(\d{2})-")
CSV_FIELDS = ("item_key", "item_id", "gold_unit", "predicted_unit", "unit_result",
              "gold_primary", "predicted_primary", "result", "gold_secondary",
              "predicted_secondary", "abstain_reason", "rule_applied")


def metric(numerator, denominator):
    """분모 0이면 비율을 null로 두고 분수를 보존한다."""
    return {"numerator": numerator, "denominator": denominator,
            "fraction": f"{numerator}/{denominator}",
            "rate": numerator / denominator if denominator else None}


def average_metric(values):
    total = sum(values, Fraction())
    average = total / len(values) if values else Fraction()
    result = metric(average.numerator, average.denominator)
    result["count"] = len(values)
    if not values:
        result = metric(0, 0) | {"count": 0}
    return result


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig") as source:
        for number, line in enumerate(source, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path} {number}행이 객체가 아님")
                rows.append(row)
    return rows


def unique_index(rows, key):
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{key} 없음")
        if value in result:
            raise ValueError(f"{key} 중복: {value}")
        result[value] = row
    return result


def load_axes(paths):
    indexed = {}
    for path in paths:
        with Path(path).open(encoding="utf-8-sig") as source:
            data = json.load(source)
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError(f"분류 결과 형식 오류: {path}")
        for item in data["items"]:
            key = f"{data.get('round')}/{item['item_id']}"
            if key in indexed:
                raise ValueError(f"분류 결과 키 중복: {key}")
            indexed[key] = item
    return indexed


def gold_areas(item):
    groups = item.get("fields", {}).get("standards", {}).get("value", [])
    areas = set()
    for group in groups:
        if not isinstance(group, dict) or group.get("status") == "source_absent":
            continue
        for code in group.get("codes", []):
            match = STANDARD_AREA.search(code) if isinstance(code, str) else None
            if match:
                areas.add(match.group(1))
    return areas


def predicted_areas(item):
    return {str(area["area_no"]).zfill(2) for area in item.get("unit", {}).get("areas", [])
            if isinstance(area, dict) and area.get("area_no") is not None}


def make_row(key, label, truth_item, prediction):
    truth_areas = gold_areas(truth_item)
    truth_secondary = set(label.get("secondary") or [])
    row = {"item_key": key, "item_id": "", "gold_unit": sorted(truth_areas),
           "predicted_unit": [], "unit_result": "짝 없음", "gold_primary": label.get("primary"),
           "predicted_primary": None, "result": "짝 없음", "gold_secondary": sorted(truth_secondary),
           "predicted_secondary": [], "abstain_reason": "", "rule_applied": ""}
    if prediction is None:
        return row
    activity = prediction.get("activity", {})
    areas = predicted_areas(prediction)
    unit_result = "불일치"
    if not truth_areas:
        unit_result = "정답 단원 없음"
    elif truth_areas == areas:
        unit_result = "완전 일치"
    elif truth_areas & areas:
        unit_result = "부분 일치"
    elif not areas:
        unit_result = "미결정"
    row.update(item_id=prediction.get("item_id", ""), predicted_unit=sorted(areas),
               unit_result=unit_result, predicted_primary=activity.get("primary"),
               result="일치" if label.get("primary") == activity.get("primary") else "불일치",
               predicted_secondary=sorted(set(activity.get("secondary") or [])),
               abstain_reason=activity.get("abstain_reason"), rule_applied=activity.get("rule_applied"))
    return row


def unit_metrics(rows):
    has_truth = [row for row in rows if row["gold_unit"]]
    no_truth = [row for row in rows if not row["gold_unit"]]
    exact = sum(row["gold_unit"] == row["predicted_unit"] for row in has_truth)
    partial = sum(bool(set(row["gold_unit"]) & set(row["predicted_unit"])) for row in has_truth)
    return {"exact": metric(exact, len(has_truth)), "partial": metric(partial, len(has_truth)),
            "undetermined": metric(sum(not row["predicted_unit"] for row in has_truth), len(has_truth)),
            "gold_unit_absent": metric(len(no_truth), len(rows)),
            "prediction_without_gold": metric(sum(bool(row["predicted_unit"]) for row in no_truth), len(no_truth))}


def per_activity_metrics(rows):
    labels = set(ACTIVITIES)
    labels.update(row["gold_primary"] for row in rows if row["gold_primary"] is not None)
    labels.update(row["predicted_primary"] for row in rows if row["predicted_primary"] is not None)
    scores = {}
    for label in sorted(labels):
        support = sum(row["gold_primary"] == label for row in rows)
        predicted = sum(row["predicted_primary"] == label for row in rows)
        true_positive = sum(row["gold_primary"] == label == row["predicted_primary"] for row in rows)
        scores[label] = {"gold_positive": support, "predicted_positive": predicted,
                         "true_positive": true_positive,
                         "precision": metric(true_positive, predicted),
                         "recall": metric(true_positive, support),
                         "f1": metric(2 * true_positive, support + predicted)}
    return scores


def activity_metrics(rows, scores):
    active = [row for row in rows if row["gold_primary"] is not None]
    classified = [row for row in active if row["predicted_primary"] is not None]
    gold_abstain = [row for row in rows if row["gold_primary"] is None]
    correct = sum(row["result"] == "일치" for row in active)
    eligible = {label: score["gold_positive"] for label, score in scores.items() if score["gold_positive"] >= 10}
    f1_values = [Fraction(scores[label]["f1"]["numerator"], scores[label]["f1"]["denominator"])
                 for label in eligible]
    return {"accuracy_all": metric(correct, len(active)),
            "accuracy_classified": metric(correct, len(classified)),
            "coverage": metric(len(classified), len(active)),
            "abstention": metric(sum(row["predicted_primary"] is None for row in rows), len(rows)),
            "gold_abstention_agreement": metric(sum(row["predicted_primary"] is None for row in gold_abstain), len(gold_abstain)),
            "macro_f1": average_metric(f1_values), "macro_f1_activities": eligible}


def secondary_metrics(rows):
    jaccards = []
    exact = subset = 0
    for row in rows:
        truth, prediction = set(row["gold_secondary"]), set(row["predicted_secondary"])
        union = truth | prediction
        jaccards.append(Fraction(len(truth & prediction), len(union)) if union else Fraction(1))
        exact += truth == prediction
        subset += truth <= prediction
    return {"jaccard_mean": average_metric(jaccards), "exact": metric(exact, len(rows)),
            "gold_subset": metric(subset, len(rows))}


def evaluate(axes, labels, items, pairs):
    label_index = unique_index(labels, "item_key")
    item_index = unique_index((row for row in items if row.get("type") == "item"), "item_key")
    pair_index = unique_index((row for row in pairs if row.get("type") == "gold"), "key")
    rows = []
    for key, label in label_index.items():
        pair = pair_index.get(key, {})
        prediction = None
        if pair.get("rule_ai_found") == "True":
            prediction = axes.get(pair.get("rule_ai_pipeline_key"))
        if key not in item_index:
            raise ValueError(f"정답 항목 없음: {key}")
        rows.append(make_row(key, label, item_index[key], prediction))
    paired = [row for row in rows if row["result"] != "짝 없음"]
    scores = per_activity_metrics(paired)
    confusion = {label: dict.fromkeys((*ACTIVITIES, ABSTAIN), 0) for label in (*ACTIVITIES, ABSTAIN)}
    for row in paired:
        truth, prediction = row["gold_primary"] or ABSTAIN, row["predicted_primary"] or ABSTAIN
        confusion.setdefault(truth, {}).setdefault(prediction, 0)
        confusion[truth][prediction] += 1
    metrics = {"paired": metric(len(paired), GOLD_TOTAL),
               "unmatched": metric(GOLD_TOTAL - len(paired), GOLD_TOTAL),
               "units": unit_metrics(paired), "activity": activity_metrics(paired, scores),
               "secondary": secondary_metrics(paired),
               "overall_primary_accuracy": metric(sum(row["result"] == "일치" for row in paired), GOLD_TOTAL)}
    return {"gold_total": GOLD_TOTAL, "label_count": len(rows), "metrics": metrics,
            "per_activity": scores, "confusion": confusion, "items": rows}


def metric_text(value):
    rate = value["rate"]
    return f"{value['fraction']} ({rate:.2%})" if rate is not None else f"{value['fraction']} (—)"


def markdown(report):
    lines = ["# 활동·단원 채점 결과", "", "| 지표 | 분수 및 비율 |", "|---|---|"]
    for name, value in report["metrics"].items():
        if "fraction" in value:
            lines.append(f"| {name} | {metric_text(value)} |")
        else:
            for subname, subvalue in value.items():
                if isinstance(subvalue, dict) and "fraction" in subvalue:
                    lines.append(f"| {name}.{subname} | {metric_text(subvalue)} |")
    eligible = report["metrics"]["activity"]["macro_f1_activities"]
    lines += ["", "macro-F1 대상(정답 양성 ≥10개) " + (", ".join(f"{k} {v}개" for k, v in eligible.items()) or "없음"),
              "", "| 활동 | 정답 양성 | Precision | Recall | F1 |", "|---|---|---|---|---|"]
    for label, scores in report["per_activity"].items():
        values = [label, str(scores["gold_positive"])] + [metric_text(scores[key]) for key in ("precision", "recall", "f1")]
        lines.append("| " + " | ".join(values) + " |")
    columns = list(dict.fromkeys(label for counts in report["confusion"].values() for label in counts))
    lines += ["", "## 혼동표", "", "| 정답 주 / 분류기 주 | " + " | ".join(columns) + " |",
              "|---|" + "---|" * len(columns)]
    for label, counts in report["confusion"].items():
        lines.append("| " + label + " | " + " | ".join(str(counts.get(column, 0)) for column in columns) + " |")
    return "\n".join(lines) + "\n"


def write_report(report, out_dir, name):
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("name은 파일 접두여야 함")
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    prefix = directory / name
    Path(str(prefix) + ".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(str(prefix) + ".md").write_text(markdown(report), encoding="utf-8")
    with Path(str(prefix) + ".csv").open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in report["items"]:
            writer.writerow({key: " | ".join(value) if isinstance(value, list) else value for key, value in row.items()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axes", nargs="+", required=True)
    parser.add_argument("--gold-activity", required=True)
    parser.add_argument("--gold-items", required=True)
    parser.add_argument("--pairs", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--name", default="gold-axes-v1")
    args = parser.parse_args(argv)
    try:
        with Path(args.pairs).open(encoding="utf-8-sig", newline="") as source:
            pairs = list(csv.DictReader(source))
        report = evaluate(load_axes(args.axes), read_jsonl(args.gold_activity), read_jsonl(args.gold_items), pairs)
        write_report(report, args.out_dir, args.name)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
