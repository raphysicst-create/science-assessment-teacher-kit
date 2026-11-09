"""Aggregate existing science scores into audit.json, audit.md and per_school.csv.

Run: .venv/Scripts/python.exe scripts/audit_science_gold.py --help
Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
        services/math-assessment-api/tests/test_audit_science_gold.py
Only supplied reports are read. Matching and field scoring remain upstream.
"""

import argparse
import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

try:
    from . import gold_activity_score as activity_score
except ImportError:
    import gold_activity_score as activity_score

THRESHOLDS = {
    "item_precision": 0.99, "item_recall": 0.95, "item_contamination": 0,
    "item_title_fabrication": 0, "negative_as_science": 0,
    "public_misattribution": 0, "unit_dictionary_standards": 87,
    "unit_code_misattribution": 0, "activity_macro_f1": 0.90,
    "activity_min_positive": 10, "search_cross_item": 0,
}
EXPECTED_AREAS = 23
CONTAMINATION = ("다른 교과", "중3", "지필평가", "운영표·규정")
SELECTION_RULE = "method∈{정답,둘다없음} and task_text∈{정답,부분,둘다없음}"
PIPELINE_TYPES = {"pipeline", "unmatched", "pipeline_unmatched", "ai_unmatched"}
SCHOOL_RATIOS = ("recall", "precision", "activity_accuracy_all", "unit_exact", "abstention")


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def normalize(value):
    """Rename upstream rate metrics without repeating any scoring decisions."""
    if isinstance(value, dict):
        if "numerator" in value and "denominator" in value:
            result = ratio(value["numerator"], value["denominator"])
            if "ci95" in value:
                result["ci95"] = value["ci95"] if result["value"] is not None else None
            return result
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def minimum(metric, threshold):
    return None if metric["value"] is None else metric["value"] >= threshold


def activity_subset(rows, labels=()):
    """Reuse the scorer's primary-activity denominators and per-label counts."""
    scores = activity_score.per_activity_metrics(rows)
    for label in labels:
        scores.setdefault(label, {"gold_positive": 0, "predicted_positive": 0, "true_positive": 0,
                                  **dict.fromkeys(("precision", "recall", "f1"), ratio(0, 0))})
    metrics = activity_score.activity_metrics(rows, scores)
    eligible = {label: score["gold_positive"] for label, score in scores.items()
                if score["gold_positive"] >= THRESHOLDS["activity_min_positive"]}
    metrics["macro_f1_activities"] = eligible
    metrics["macro_f1"] = activity_score.average_metric([
        Fraction(scores[label]["f1"]["numerator"], scores[label]["f1"]["denominator"])
        for label in eligible])
    return normalize(metrics | {"per_activity": scores})


def selected_keys(cases):
    selected = set()
    for row in cases:
        if row["type"] != "gold":
            continue
        fields = json.loads(row.get("rule_ai_field_results") or "{}")
        if (fields.get("method") in {"정답", "둘다없음"}
                and fields.get("task_text") in {"정답", "부분", "둘다없음"}):
            selected.add(row["key"])
    return selected


def item_report(stage):
    counts = stage["unmatched_classification_counts"]
    contamination = sum(counts.get(name, 0) for name in CONTAMINATION)
    result = {key: normalize(stage[key]) for key in ("recall", "precision")}
    result.update(unmatched_classification_counts=counts, contamination=contamination,
                  title_fabrication=sum(row["classification"] == "제목 생성"
                                        for row in stage["unmatched_pipeline"]),
                  lost_confirmed_gold_keys=stage.get("lost_confirmed_gold_keys", []))
    result["pass"] = {
        "precision": minimum(result["precision"], THRESHOLDS["item_precision"]),
        "recall": minimum(result["recall"], THRESHOLDS["item_recall"]),
        "contamination": contamination == THRESHOLDS["item_contamination"],
    }
    return result


def field_report(stage):
    fields = stage["fields"]
    public = stage["public_misattributions"]
    return {"per_field": fields,
            "missing_rate": {key: ratio(counts.get("누락", 0),
                                       sum(counts.values()) - counts.get("둘다없음", 0))
                             for key, counts in fields.items()},
            "misattributions_by_field": stage.get("misattributions_by_field", {}),
            "public_misattributions": public,
            "pass": {"public_misattribution": public == THRESHOLDS["public_misattribution"]}}


def unit_report(metrics, check, fields):
    dictionary = None
    dictionary_pass = None
    if check is not None:
        problems = check["problems"]
        dictionary = {"areas": check["areas"], "standards": check["standards"],
                      "problems": len(problems) if isinstance(problems, list) else problems}
        dictionary_pass = (dictionary["areas"] == EXPECTED_AREAS
                           and dictionary["standards"] == THRESHOLDS["unit_dictionary_standards"]
                           and dictionary["problems"] == 0)
    codes = fields["misattributions_by_field"].get("standards", 0)
    return normalize(metrics) | {
        "dictionary": dictionary, "code_misattribution": codes,
        "pass": {"dictionary": dictionary_pass,
                 "code_misattribution": codes == THRESHOLDS["unit_code_misattribution"]}}


def conversion_ok(document):
    status = document.get("conversion_status")
    if status is None:
        converters = document.get("converters", {})
        for name in ("kordoc", "zip", "pymupdf"):
            if name in converters:
                status = converters[name].get("conversion_status")
                break
    return document.get("audit_status") != "excluded_non_plan" and status == "ok"


def school_gold(row, school):
    return row["key"].startswith(school["school_id"] + "-g")


def school_documents(documents, school):
    result = []
    for document in documents:
        source = document.get("source", {})
        identifier = source.get("school_id")
        belongs = identifier == school["school_id"] if identifier else (
            document.get("school_name", source.get("school_name")) == school["school_name"])
        if belongs:
            result.append(document)
    return result


def school_report(school, cases, stage, axes_items, documents):
    gold = [row for row in cases if row["type"] == "gold" and school_gold(row, school)]
    keys = {row["key"] for row in gold}
    pairs = [row for row in stage["pairs"] if row["gold_key"] in keys]
    matched = {row["pipeline_key"] for row in pairs}
    eligible = matched | {row["pipeline_key"] for row in stage["unmatched_pipeline"]}
    pipeline = {row["key"] for row in cases if row["type"] in PIPELINE_TYPES
                and row.get("school") == school["school_name"] and row["key"] in eligible}
    # Existing CSVs omit matched pipeline rows, recording their keys on gold rows.
    pipeline.update(matched)
    rows = [row for row in axes_items if row["item_key"] in keys]
    activity = activity_subset(rows)
    units = activity_score.unit_metrics([row for row in rows if row["result"] != "짝 없음"])
    docs = school_documents(documents, school)
    return {"school_id": school["school_id"], "school_name": school["school_name"],
            "gold_items": len(gold), "documents": len(docs),
            "conversion_ok": sum(conversion_ok(row) for row in docs),
            "rule_ai_found": sum(row.get("rule_ai_found", "").lower() == "true" for row in gold),
            "recall": ratio(len(pairs), len(gold)),
            "precision": ratio(len(matched), len(pipeline)),
            "activity_accuracy_all": activity["accuracy_all"],
            "unit_exact": normalize(units["exact"]), "abstention": activity["abstention"]}


def search_report(search):
    if search is None:
        return None
    result = {key: search[key] for key in (
        "cross_item_matches", "set_mismatches", "count_mismatches", "combinations_checked")}
    result["pass"] = (result["cross_item_matches"] == THRESHOLDS["search_cross_item"]
                      and result["set_mismatches"] == 0 and result["count_mismatches"] == 0)
    return result


def judgments(report):
    items, units = report["items"], report["units"]
    search = report["search"]
    checks = {
        "item_precision": items["pass"]["precision"], "item_recall": items["pass"]["recall"],
        "item_contamination": items["pass"]["contamination"],
        "item_title_fabrication": (
            items["title_fabrication"] == THRESHOLDS["item_title_fabrication"]),
        "negative_as_science": report["negatives"]["pass"],
        "public_misattribution": report["fields"]["pass"]["public_misattribution"],
        "unit_dictionary_standards": units["pass"]["dictionary"],
        "unit_code_misattribution": units["pass"]["code_misattribution"],
        "activity_macro_f1": report["activity"]["pass"]["macro_f1"],
        "search_cross_item": search["pass"] if search is not None else None,
    }
    if report["audit_summary"] is not None:
        summary = report["audit_summary"]
        checks["audit_summary"] = None
        if summary["passed"] is not None and summary["blocking_public_items"] is not None:
            checks["audit_summary"] = (summary["passed"] is True
                                       and summary["blocking_public_items"] == 0)
    return checks


def zero_notes(value, path=""):
    notes = []
    if isinstance(value, dict):
        if value.get("denominator") == 0:
            notes.append(f"{path} 분모 0, 판정 불가")
        for key, child in value.items():
            notes.extend(zero_notes(child, f"{path}.{key}".lstrip(".")))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            notes.extend(zero_notes(child, f"{path}.{index}"))
    return notes


def assemble(args, data, cases, roster):
    score, axes = data["score"], data["axes_score"]
    stage = score["stages"][args.publish_stage]
    documents = [row for report in data["conversion"] for row in report["documents"]]
    items, fields = item_report(stage), field_report(stage)
    keys = selected_keys(cases)
    subset = [row for row in axes["items"] if row["item_key"] in keys]
    activity = normalize(axes["metrics"]["activity"] | {"per_activity": axes["per_activity"]})
    report = {
        "set_name": args.set_name, "generated_at": datetime.now(UTC).isoformat(),
        "thresholds": THRESHOLDS.copy(),
        "stages": {"source_documents": len(documents),
                   "conversion_ok": sum(conversion_ok(row) for row in documents),
                   "conversion_failed": sum(not conversion_ok(row) for row in documents),
                   "loss_map_rule_only": score["loss_maps"]["rule_only"],
                   "loss_map_rule_ai": score["loss_maps"]["rule_ai"]},
        "items": items,
        "negatives": {"science_items_in_negative_sections": items["contamination"],
                      "pass": items["contamination"] == THRESHOLDS["negative_as_science"]},
        "fields": fields,
        "units": unit_report(axes["metrics"]["units"], data["axes_check"], fields),
        "activity": {"all": activity,
                     "fields_correct": {"item_count": len(subset), "selection_rule": SELECTION_RULE,
                                        **activity_subset(subset, axes["per_activity"])},
                     "secondary": normalize(axes["metrics"]["secondary"]),
                     "pass": {"macro_f1": minimum(
                         activity["macro_f1"], THRESHOLDS["activity_macro_f1"])}},
        "search": search_report(data["search"]),
        "audit_summary": None if data["audit_summary"] is None else {
            key: data["audit_summary"].get(key) for key in ("blocking_public_items", "passed")},
        "per_school": [school_report(school, cases, stage, axes["items"], documents)
                       for school in roster],
    }
    checks = judgments(report)
    report["verdict"] = {"all_pass": all(value is True for value in checks.values()),
                         "failed": [name for name, value in checks.items() if value is False]}
    report["notes"] = [f"publish_stage={args.publish_stage}",
                       "conversion은 원문 documents 단위. "
                       "대표 변환기 kordoc→zip→pymupdf의 ok만 성공. "
                       "제외·부분·미확정을 포함한 나머지를 conversion_failed로 집계."]
    report["notes"] += [f"{name} 입력 없음" for name in ("axes_check", "search", "audit_summary")
                        if data[name] is None]
    report["notes"] += [f"{name} 판정 불가" for name, value in checks.items() if value is None]
    report["notes"] += zero_notes(report)
    return report


def cell(value, path):
    if isinstance(value, dict) and "numerator" in value:
        value = f"{value['numerator']}/{value['denominator']} = {value['value']}"
    elif isinstance(value, dict):
        return ("<br>".join(cell(child, f"{path}.{key}") for key, child in value.items())
                or f"`{path}`")
    elif isinstance(value, list):
        return ("<br>".join(cell(child, f"{path}.{i}") for i, child in enumerate(value))
                or f"`{path}`")
    return f"{value} `{path}`".replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers),
            *["| " + " | ".join(row) + " |" for row in rows], ""]


def threshold_table(report):
    paths = {
        "item_precision": "items.precision", "item_recall": "items.recall",
        "item_contamination": "items.contamination",
        "item_title_fabrication": "items.title_fabrication",
        "negative_as_science": "negatives.science_items_in_negative_sections",
        "public_misattribution": "fields.public_misattributions",
        "unit_dictionary_standards": "units.dictionary",
        "unit_code_misattribution": "units.code_misattribution",
        "activity_macro_f1": "activity.all.macro_f1",
        "search_cross_item": "search.cross_item_matches",
    }
    rows = []
    for name, passed in judgments(report).items():
        path = paths.get(name, "audit_summary")
        value = report
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        threshold = report["thresholds"].get(name)
        limit = cell(threshold, f"thresholds.{name}") if threshold is not None else "—"
        operator = ">=" if name in {"item_precision", "item_recall", "activity_macro_f1"} else "=="
        rows.append([name, cell(value, path), f"{operator} {limit}", cell(passed, "verdict")])
    rows.append(["activity_min_positive", cell(report["activity"]["all"]["macro_f1_activities"],
                                              "activity.all.macro_f1_activities"),
                 ">= " + cell(THRESHOLDS["activity_min_positive"],
                              "thresholds.activity_min_positive"),
                 "—"])
    return table(["지표", "값", "합격선", "판정"], rows)


def stage_table(report):
    stages = report["stages"]
    maps = ("loss_map_rule_only", "loss_map_rule_ai")
    rows = [[key, cell(stages[key], f"stages.{key}"), cell(stages[key], f"stages.{key}")]
            for key in ("source_documents", "conversion_ok", "conversion_failed")]
    keys = dict.fromkeys(key for name in maps for key in stages[name])
    for key in keys:
        rows.append([key, *[cell(stages[name].get(key), f"stages.{name}.{key}") for name in maps]])
    return table(["단계별 손실", "규칙만 `stages.loss_map_rule_only`",
                  "규칙+AI `stages.loss_map_rule_ai`"], rows)


def activity_table(report):
    activity = report["activity"]
    lines = table(["활동 지표", "전체 항목", "방법·요소 필드 정답"], [
        [key, cell(value, f"activity.all.{key}"),
         cell(activity["fields_correct"][key], f"activity.fields_correct.{key}")]
        for key, value in activity["all"].items() if key != "per_activity"])
    rows = []
    for label, scores in activity["all"]["per_activity"].items():
        for key in ("gold_positive", "predicted_positive", "precision", "recall", "f1"):
            rows.append([label, key, cell(scores[key], f"activity.all.per_activity.{label}.{key}"),
                         cell(activity["fields_correct"]["per_activity"][label][key],
                              f"activity.fields_correct.per_activity.{label}.{key}")])
    lines += table(["활동", "지표", "전체 항목", "방법·요소 필드 정답"], rows)
    lines += table(["선택", "값"], [[key, cell(activity["fields_correct"][key],
                                             f"activity.fields_correct.{key}")]
                                  for key in ("item_count", "selection_rule")])
    return lines


def markdown(report):
    lines = threshold_table(report)
    lines += stage_table(report)
    lines += table(["필드", "결과", "누락률", "오귀속"], [
        [key, cell(value, f"fields.per_field.{key}"),
         cell(report["fields"]["missing_rate"][key], f"fields.missing_rate.{key}"),
         cell(report["fields"]["misattributions_by_field"].get(key),
              f"fields.misattributions_by_field.{key}")]
        for key, value in report["fields"]["per_field"].items()])
    lines += activity_table(report)
    school_keys = ("school_id", "school_name", "gold_items", "documents", "conversion_ok",
                   "rule_ai_found", *SCHOOL_RATIOS)
    lines += table(list(school_keys), [
        [cell(school[key], f"per_school.{index}.{key}") for key in school_keys]
        for index, school in enumerate(report["per_school"])])
    lines += table(["키", "값"], [[f"`{key}`", cell(report[key], key)]
                                  for key in ("units", "search", "audit_summary", "verdict")])
    lines += table(["키", "값"], [["`activity.secondary`",
                                   cell(report["activity"]["secondary"], "activity.secondary")]])
    return "\n".join(lines)


def write_outputs(report, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "audit.md").write_text(markdown(report), encoding="utf-8")
    columns = ["school_id", "school_name", "gold_items", "documents", "conversion_ok",
               "rule_ai_found"]
    columns += [f"{key}_{part}" for key in SCHOOL_RATIOS
                for part in ("numerator", "denominator", "value")]
    with (out_dir / "per_school.csv").open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        for school in report["per_school"]:
            row = {key: value for key, value in school.items() if key not in SCHOOL_RATIOS}
            row.update({f"{key}_{part}": value for key in SCHOOL_RATIOS
                        for part, value in school[key].items()})
            writer.writerow(row)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set-name", required=True)
    parser.add_argument("--publish-stage", default="rule_ai")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--conversion", type=Path, nargs="+", required=True)
    for name in ("roster", "score", "cases", "axes-score", "axes-check", "search", "audit-summary"):
        parser.add_argument(f"--{name}", type=Path,
                            required=name in {"roster", "score", "cases", "axes-score"})
    args = parser.parse_args(argv)
    paths = {name: getattr(args, name) for name in (
        "roster", "score", "cases", "axes_score", "axes_check", "search", "audit_summary")}
    supplied = [path for path in [*paths.values(), *args.conversion] if path is not None]
    contents = {path: path.read_bytes() for path in supplied}
    data = {key: json.loads(contents[path].decode("utf-8-sig")) if path else None
            for key, path in paths.items() if key not in {"roster", "cases"}}
    data["conversion"] = [json.loads(contents[path].decode("utf-8-sig"))
                          for path in args.conversion]
    cases = list(csv.DictReader(io.StringIO(contents[args.cases].decode("utf-8-sig"))))
    roster = list(csv.DictReader(io.StringIO(contents[args.roster].decode("utf-8-sig"))))
    if args.publish_stage not in data["score"]["stages"]:
        parser.error(f"unknown publish stage {args.publish_stage}")
    report = assemble(args, data, cases, roster)
    report["inputs"] = {str(path): hashlib.sha256(contents[path]).hexdigest() for path in supplied}
    write_outputs(report, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
