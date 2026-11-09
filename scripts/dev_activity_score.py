"""개발 활동 라벨과 분류 결과를 item_id로 짝지어 JSON/MD/CSV 지표를 쓴다.

Run: .venv/Scripts/python.exe scripts/dev_activity_score.py --axes A.json B.json
     --labels LABELS.jsonl --out-dir DIR --name NAME
Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
        services/math-assessment-api/tests/test_dev_activity_score.py
표준 라이브러리만 사용한다. gold 경로는 입력과 출력 모두 거부한다.
"""

import argparse
import csv
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path

ACTIVITIES = (
    "탐구",
    "실험평가",
    "작성",
    "제작",
    "분석",
    "추론·설명",
    "발표·토론",
    "계산·측정",
    "과정평가",
    "문제해결",
)
ABSTAIN = "기권"
CSV_FIELDS = (
    "item_id",
    "round",
    "school",
    "title",
    "label_primary",
    "predicted_primary",
    "result",
    "label_secondary",
    "predicted_secondary",
    "predicted_rule",
    "abstain_reason",
)
VOTE_FIELDS = ("votes", "votes_e", "votes_s")


def guard_path(path):
    if "gold" in str(path).casefold() or "gold" in str(Path(path).resolve()).casefold():
        raise ValueError(f"gold 경로 거부: {path}")


def metric(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "fraction": f"{numerator}/{denominator}",
        "rate": numerator / denominator if denominator else None,
    }


def average_metric(values):
    if not values:
        return metric(0, 0) | {"count": 0}
    average = sum(values, Fraction()) / len(values)
    return metric(average.numerator, average.denominator) | {"count": len(values)}


def validate_activity(activity):
    if not isinstance(activity, dict) or "primary" not in activity:
        raise ValueError("활동 객체에 primary 필요")
    primary = activity["primary"]
    if primary is not None and primary not in ACTIVITIES:
        raise ValueError(f"primary 값 오류: {primary}")
    secondary = activity.get("secondary", [])
    if not isinstance(secondary, list) or any(name not in ACTIVITIES for name in secondary):
        raise ValueError("secondary는 활동 이름 배열이어야 함")


def unique_index(rows):
    indexed = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("item_id"), str)
            or not row["item_id"]
        ):
            raise ValueError("항목에 문자열 item_id 필요")
        key = row["item_id"]
        if key in indexed:
            raise ValueError(f"item_id 중복: {key}")
        indexed[key] = row
    return indexed


def load_axes(paths):
    rows = []
    for path in paths:
        guard_path(path)
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError(f"분류 결과 형식 오류: {path}")
        for item in data["items"]:
            if not isinstance(item, dict):
                raise ValueError(f"분류 항목은 객체여야 함: {path}")
            validate_activity(item.get("activity"))
            rows.append(dict(item, round=item.get("round", data.get("round"))))
    return unique_index(rows)


def read_labels(path):
    guard_path(path)
    rows = []
    for number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if line.strip():
            row = json.loads(line)
            try:
                validate_activity(row)
            except ValueError as error:
                raise ValueError(f"{path} {number}행: {error}") from error
            rows.append(row)
    return list(unique_index(rows).values())


def make_row(label, prediction):
    item = prediction or {}
    activity = item.get("activity", {})
    result = "짝 없음"
    if prediction is not None:
        result = "일치" if label["primary"] == activity["primary"] else "불일치"
    return {
        "item_id": label["item_id"],
        "round": item.get("round", label.get("round")),
        "school": item.get("school", label.get("school")),
        "grade": item.get("grade", label.get("grade")),
        "semester": item.get("semester", label.get("semester")),
        "title": item.get("title", label.get("title")),
        "result": result,
        "label_primary": label["primary"],
        "predicted_primary": activity.get("primary"),
        "label_secondary": sorted(set(label.get("secondary", []))),
        "predicted_secondary": sorted(set(activity.get("secondary", []))),
        "label_rule": label.get("rule_applied"),
        "predicted_rule": activity.get("rule_applied"),
        "label_abstain_reason": label.get("abstain_reason"),
        "predicted_abstain_reason": activity.get("abstain_reason"),
        "candidates": activity.get("candidates", []),
        "votes_e": activity.get("votes_e", {}),
        "votes_s": activity.get("votes_s", {}),
        "label_votes": {key: label[key] for key in VOTE_FIELDS if key in label},
        "label_evidence_quotes": [
            e["quote"] for e in label.get("evidence", []) if isinstance(e, dict) and "quote" in e
        ],
        "label_note": label.get("note"),
    }


def per_activity_metrics(rows):
    scores = {}
    for name in ACTIVITIES:
        support = sum(row["label_primary"] == name for row in rows)
        predicted = sum(row["predicted_primary"] == name for row in rows)
        true_positive = sum(
            row["label_primary"] == name == row["predicted_primary"] for row in rows
        )
        scores[name] = {
            "label_positive": support,
            "predicted_positive": predicted,
            "true_positive": true_positive,
            "precision": metric(true_positive, predicted),
            "recall": metric(true_positive, support),
            "f1": metric(2 * true_positive, support + predicted),
        }
    return scores


def macro_f1(scores, minimum):
    activities = [name for name in ACTIVITIES if scores[name]["label_positive"] >= minimum]
    values = []
    for name in activities:
        f1 = scores[name]["f1"]
        values.append(
            Fraction(f1["numerator"], f1["denominator"]) if f1["denominator"] else Fraction()
        )
    return average_metric(values) | {"activities": activities}


def secondary_jaccard(rows):
    values = []
    for row in rows:
        label, predicted = set(row["label_secondary"]), set(row["predicted_secondary"])
        union = label | predicted
        values.append(Fraction(len(label & predicted), len(union)) if union else Fraction(1))
    return average_metric(values)


def evaluate(axes, labels):
    labels = list(unique_index(labels).values())
    rows = [make_row(label, axes.get(label["item_id"])) for label in labels]
    paired = [row for row in rows if row["result"] != "짝 없음"]
    labeled = [row for row in paired if row["label_primary"] is not None]
    scores = per_activity_metrics(paired)
    columns = (*ACTIVITIES, ABSTAIN)
    confusion = {name: dict.fromkeys(columns, 0) for name in columns}
    for row in paired:
        confusion[row["label_primary"] or ABSTAIN][row["predicted_primary"] or ABSTAIN] += 1
    metrics = {
        "paired": metric(len(paired), len(labels)),
        "unmatched": metric(len(rows) - len(paired), len(labels)),
        "primary_accuracy_all": metric(sum(row["result"] == "일치" for row in paired), len(paired)),
        "primary_accuracy_labeled": metric(
            sum(row["result"] == "일치" for row in labeled), len(labeled)
        ),
        "classifier_abstain_rate": metric(
            sum(row["predicted_primary"] is None for row in paired), len(paired)
        ),
        "label_abstain_rate": metric(
            sum(row["label_primary"] is None for row in paired), len(paired)
        ),
        "coverage": metric(
            sum(row["predicted_primary"] is not None for row in labeled), len(labeled)
        ),
        "macro_f1_all": macro_f1(scores, 1),
        "macro_f1_min5": macro_f1(scores, 5),
        "secondary_jaccard": secondary_jaccard(paired),
    }
    return {
        "label_count": len(labels),
        "metrics": metrics,
        "per_activity": scores,
        "confusion": confusion,
        "items": rows,
        "mismatches": [
            {key: value for key, value in row.items() if key != "result"}
            for row in paired
            if row["result"] == "불일치"
        ],
    }


def metric_text(value):
    rate = value["rate"]
    return f"{value['fraction']} ({rate:.2%})" if rate is not None else f"{value['fraction']} (—)"


def table_row(values):
    cells = []
    for value in values:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        cells.append(str(value).replace("|", "\\|").replace("\r", " ").replace("\n", "<br>"))
    return "| " + " | ".join(cells) + " |"


def markdown(report):
    lines = ["# 개발 활동 채점 결과", "", "| 지표 | 분수 및 비율 |", "|---|---|"]
    lines += [table_row([key, metric_text(value)]) for key, value in report["metrics"].items()]
    for key in ("macro_f1_all", "macro_f1_min5"):
        value = report["metrics"][key]
        lines += [
            "",
            f"{key} 대상 {value['count']}개 · " + (", ".join(value["activities"]) or "없음"),
        ]
    lines += [
        "",
        "| 활동 | 라벨 양성 | 분류 양성 | 참 양성 | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for name, scores in report["per_activity"].items():
        lines.append(
            table_row(
                [
                    name,
                    scores["label_positive"],
                    scores["predicted_positive"],
                    scores["true_positive"],
                    *[metric_text(scores[key]) for key in ("precision", "recall", "f1")],
                ]
            )
        )
    columns = (*ACTIVITIES, ABSTAIN)
    lines += [
        "",
        "## 혼동표",
        "",
        table_row(["라벨 주 / 분류 주", *columns]),
        "|---|" + "---:|" * len(columns),
    ]
    lines += [
        table_row([name, *[counts[column] for column in columns]])
        for name, counts in report["confusion"].items()
    ]
    lines += mismatch_markdown(report["mismatches"])
    return "\n".join(lines) + "\n"


def mismatch_markdown(rows):
    lines = [
        "",
        "## 불일치 항목",
        "",
        "| 학교 | 제목 | 라벨→분류 | 규칙(라벨→분류) | E표 | S표 | 라벨 메모 |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            table_row(
                [
                    row["school"],
                    row["title"],
                    f"{row['label_primary'] or ABSTAIN}→{row['predicted_primary'] or ABSTAIN}",
                    f"{row['label_rule']}→{row['predicted_rule']}",
                    row["votes_e"],
                    row["votes_s"],
                    row["label_note"],
                ]
            )
        )
    return lines


def input_metadata(path):
    guard_path(path)
    return {"path": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def write_report(report, out_dir, name):
    guard_path(out_dir)
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("name은 파일 접두여야 함")
    prefix = Path(out_dir) / name
    guard_path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(str(prefix) + ".json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(str(prefix) + ".md").write_text(markdown(report), encoding="utf-8")
    with Path(str(prefix) + ".csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in report["items"]:
            values = row | {"abstain_reason": row["predicted_abstain_reason"]}
            writer.writerow(
                {
                    key: " | ".join(values[key]) if isinstance(values[key], list) else values[key]
                    for key in CSV_FIELDS
                }
            )


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axes", nargs="+", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    try:
        for path in [*args.axes, args.labels, args.out_dir]:
            guard_path(path)
        report = evaluate(load_axes(args.axes), read_labels(args.labels))
        report["inputs"] = {
            "axes": [input_metadata(path) for path in args.axes],
            "labels": input_metadata(args.labels),
        }
        write_report(report, args.out_dir, args.name)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
