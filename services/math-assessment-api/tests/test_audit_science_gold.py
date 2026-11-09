"""Exercise the report CLI using synthetic upstream reports under pytest tmp_path.

Run/Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
            services/math-assessment-api/tests/test_audit_science_gold.py
The six-item fixture covers aggregation, with a larger fixture for ten-positive F1.
"""

import copy
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from scripts import audit_science_gold as audit
from scripts import gold_activity_score as scorer

ROOT = Path(__file__).resolve().parents[3]
SCHOOLS = (("synthetic-a", "가상 학교 A"), ("synthetic-a-extra", "가상 학교 B"))


def write_csv(path, rows):
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def metric(numerator, denominator):
    result = audit.ratio(numerator, denominator)
    result["ci95"] = [0.1, 0.9] if denominator else None
    return result


def make_rows(size, perfect):
    cases, pairs, axes_items = [], [], []
    for index in range(size):
        school_id, school_name = SCHOOLS[index >= size // 2]
        key = f"{school_id}-g1-s1-{index:02}"
        found = perfect or index < 4
        primary = "활동 A" if index < size - 2 else "활동 B"
        predicted = primary
        method, task = "정답", "정답"
        if not perfect:
            primary = ["활동 A", "활동 A", "활동 A", "활동 B", "활동 A", None][index]
            predicted = ["활동 A", None, "활동 B", "활동 B", None, None][index]
            method = ["정답", "둘다없음", "부분", "정답", "정답", "둘다없음"][index]
            task = ["부분", "둘다없음", "정답", "오값", "누락", "정답"][index]
        elif index == size - 1:
            primary, predicted = None, None
        pipeline_key = f"synthetic-round/item-{index}"
        cases.append({"type": "gold", "key": key, "school": school_name,
                      "rule_ai_found": str(found), "confirmed_found": str(index == 0),
                      "rule_ai_pipeline_key": pipeline_key if found else "",
                      "rule_ai_field_results": json.dumps({"method": method, "task_text": task}),
                      "title": "가상 제목\n둘째 줄"})
        if found:
            pairs.append({"gold_key": key, "pipeline_key": pipeline_key})
            cases.append({"type": "pipeline", "key": pipeline_key, "school": school_name})
        axes_items.append({"item_key": key, "item_id": pipeline_key if found else "",
                           "gold_primary": primary, "predicted_primary": predicted,
                           "result": "짝 없음" if not found else (
                               "일치" if primary == predicted else "불일치"),
                           "gold_unit": ["01"], "predicted_unit": ["01"] if found else [],
                           "unit_result": "완전 일치" if found else "짝 없음",
                           "gold_secondary": [], "predicted_secondary": []})
    return cases, pairs, axes_items


def make_inputs(size=6, perfect=False):
    cases, pairs, axes_items = make_rows(size, perfect)
    unmatched = []
    if not perfect:
        for index, category in enumerate(("다른 교과", "운영표·규정", "제목 생성")):
            school = SCHOOLS[index != 0][1]
            row = {"pipeline_key": f"synthetic-round/extra-{index}",
                   "school": school, "classification": category}
            unmatched.append(row)
            cases.append({"type": "unmatched", "key": row["pipeline_key"], "school": school})
    counts = {name: sum(row["classification"] == name for row in unmatched)
              for name in (*audit.CONTAMINATION, "제목 생성", "짝짓기 보류", "요약·중복")}
    field_counts = dict.fromkeys(("정답", "부분", "누락", "오값", "허위값", "둘다없음"), 1)
    stage = {"recall": metric(len(pairs), size),
             "precision": metric(len(pairs), len(pairs) + len(unmatched)), "pairs": pairs,
             "unmatched_classification_counts": counts, "unmatched_pipeline": unmatched,
             "fields": {"method": field_counts, "task_text": field_counts.copy(),
                        "standards": field_counts.copy()},
             "misattributions_by_field": {} if perfect else {"standards": 1, "method": 2},
             "public_misattributions": 0 if perfect else 1,
             "lost_confirmed_gold_keys": [] if perfect else [cases[0]["key"]]}
    loss = {"gold": size, "document": size, "section": size, "candidate": size,
            "matched": len(pairs), "confirmed": len(pairs)}
    score = {"stages": {"rule_ai": stage, "confirmed": copy.deepcopy(stage)},
             "loss_maps": {"rule_only": loss, "rule_ai": loss.copy()}}
    paired = [row for row in axes_items if row["result"] != "짝 없음"]
    scores = scorer.per_activity_metrics(paired)
    axes = {"gold_total": size, "label_count": size, "items": axes_items,
            "per_activity": scores,
            "metrics": {"activity": scorer.activity_metrics(paired, scores),
                        "units": scorer.unit_metrics(paired),
                        "secondary": scorer.secondary_metrics(paired)}}
    documents = []
    for index, status in enumerate(("ok", "failed", "ok", "partial")):
        school_id, school_name = SCHOOLS[index // 2]
        documents.append({"school_name": school_name, "filename": f"fake-{index}.pdf",
                          "source": {"school_id": school_id, "school_name": school_name},
                          "audit_status": "converted",
                          "converters": {"kordoc": {"conversion_status": status}}})
    return {"score": score, "axes_score": axes, "cases": cases,
            "roster": [{"school_id": key, "school_name": name} for key, name in SCHOOLS],
            "conversion": [{"round": "fake-a", "documents": documents[:2]},
                           {"round": "fake-b", "documents": documents[2:]}],
            "axes_check": {"areas": 23, "standards": 87, "problems": []},
            "search": {"cross_item_matches": 0, "set_mismatches": 0,
                       "count_mismatches": 0, "combinations_checked": 12},
            "audit_summary": {"blocking_public_items": 0, "passed": True}}


def run_report(tmp_path, data, *, omit=(), stage="rule_ai", subprocess_cli=False):
    args = ["--set-name", "synthetic", "--out-dir", str(tmp_path / "out"),
            "--publish-stage", stage]
    paths = []
    for name in ("roster", "cases", "score", "axes_score", "axes_check", "search", "audit_summary"):
        if name in omit:
            continue
        path = tmp_path / (name + (".csv" if name in {"roster", "cases"} else ".json"))
        if name in {"roster", "cases"}:
            write_csv(path, data[name])
        else:
            path.write_text(json.dumps(data[name], ensure_ascii=False), encoding="utf-8")
        args += ["--" + name.replace("_", "-"), str(path)]
        paths.append(path)
    args.append("--conversion")
    for index, conversion in enumerate(data["conversion"]):
        path = tmp_path / f"conversion-{index}.json"
        path.write_text(json.dumps(conversion, ensure_ascii=False), encoding="utf-8")
        paths.append(path)
        args.append(str(path))
    if subprocess_cli:
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/audit_science_gold.py"),
                                    *args], cwd=ROOT, capture_output=True, text=True, check=False)
        assert completed.returncode == 0, completed.stderr
    else:
        assert audit.main(args) == 0
    output = tmp_path / "out"
    report = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    return report, output, paths


def test_aggregate_existing_scores_and_hash_inputs(tmp_path):
    data = make_inputs()
    report, output, paths = run_report(tmp_path, data, subprocess_cli=True)
    assert report["items"]["recall"] == metric(4, 6)
    assert report["items"]["precision"] == metric(4, 7)
    assert report["items"]["contamination"] == 2
    assert report["items"]["title_fabrication"] == 1
    assert report["items"]["lost_confirmed_gold_keys"] == [data["cases"][0]["key"]]
    assert report["negatives"] == {"science_items_in_negative_sections": 2, "pass": False}
    assert report["fields"]["missing_rate"]["method"] == audit.ratio(1, 5)
    assert report["units"]["code_misattribution"] == 1
    assert report["units"]["dictionary"] == {"areas": 23, "standards": 87, "problems": 0}
    assert report["stages"]["source_documents"] == 4
    assert report["stages"]["conversion_ok"] == 2
    assert report["stages"]["conversion_failed"] == 2
    assert report["stages"]["loss_map_rule_ai"] == data["score"]["loss_maps"]["rule_ai"]
    assert report["inputs"] == {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in paths}
    assert datetime.fromisoformat(report["generated_at"]).tzinfo is not None
    with (output / "per_school.csv").open(encoding="utf-8-sig", newline="") as source:
        schools = list(csv.DictReader(source))
    assert len(schools) == 2
    assert schools[0]["precision_denominator"] == "4"


def test_fields_correct_selection_and_abstention_denominators(tmp_path):
    report, _, _ = run_report(tmp_path, make_inputs())
    subset = report["activity"]["fields_correct"]
    assert subset["selection_rule"] == audit.SELECTION_RULE
    assert subset["item_count"] == 3
    assert subset["accuracy_all"] == audit.ratio(1, 2)
    assert subset["accuracy_classified"] == audit.ratio(1, 1)
    assert subset["coverage"] == audit.ratio(1, 2)
    assert subset["abstention"] == audit.ratio(2, 3)
    assert subset["gold_abstention_agreement"] == audit.ratio(1, 1)
    assert subset["per_activity"]["활동 A"]["gold_positive"] == 2
    assert subset["macro_f1"]["value"] is None
    assert report["activity"]["all"]["accuracy_all"] == audit.ratio(2, 4)


def test_macro_f1_only_includes_at_least_ten_positives(tmp_path):
    data = make_inputs(12, perfect=True)
    # Ten A positives, one B positive and one gold abstention.
    data["axes_score"]["items"][10]["predicted_primary"] = "활동 A"
    data["axes_score"]["items"][10]["result"] = "불일치"
    report, _, _ = run_report(tmp_path, data)
    subset = report["activity"]["fields_correct"]
    assert subset["macro_f1_activities"] == {"활동 A": 10}
    assert subset["per_activity"]["활동 B"]["gold_positive"] == 1
    assert subset["per_activity"]["활동 B"]["f1"]["value"] == 0
    assert subset["macro_f1"] == audit.ratio(20, 21)
    assert subset["accuracy_all"] == audit.ratio(10, 11)
    # The all-items metrics are copied from the supplied report, never rescored.
    assert report["activity"]["all"]["macro_f1"]["value"] == 1


def test_school_separation_and_legacy_cases(tmp_path):
    data = make_inputs()
    # Match the actual scorer CSV, which omits matched pipeline rows.
    data["cases"] = [row for row in data["cases"] if row["type"] != "pipeline"]
    for row in data["cases"]:
        if row["type"] == "unmatched":
            row["type"] = "ai_unmatched" if row["school"] == SCHOOLS[1][1] else "pipeline_unmatched"
    data["cases"] += [{"type": "pipeline_nonperformance", "school": SCHOOLS[0][1], "key": "skip"},
                      {"type": "pipeline_unmatched", "school": SCHOOLS[0][1], "key": "other-stage"},
                      {"type": "ai_field", "school": SCHOOLS[0][1], "key": "skip-field"}]
    report, _, _ = run_report(tmp_path, data)
    first, second = report["per_school"]
    assert [first["gold_items"], second["gold_items"]] == [3, 3]
    assert [first["rule_ai_found"], second["rule_ai_found"]] == [3, 1]
    assert first["recall"] == audit.ratio(3, 3)
    assert second["recall"] == audit.ratio(1, 3)
    assert first["precision"] == audit.ratio(3, 4)
    assert second["precision"] == audit.ratio(1, 3)
    assert [first["documents"], second["documents"]] == [2, 2]
    assert [first["conversion_ok"], second["conversion_ok"]] == [1, 1]
    assert first["activity_accuracy_all"] == audit.ratio(1, 3)
    assert second["activity_accuracy_all"] == audit.ratio(1, 2)
    assert first["unit_exact"] == audit.ratio(3, 3)
    assert second["unit_exact"] == audit.ratio(1, 1)


def test_verdict_failure_paths_and_markdown_keys(tmp_path):
    report, output, _ = run_report(tmp_path, make_inputs())
    assert report["verdict"]["all_pass"] is False
    assert set(report["verdict"]["failed"]) == {
        "item_precision", "item_recall", "item_contamination", "item_title_fabrication",
        "negative_as_science", "public_misattribution", "unit_code_misattribution"}
    markdown = (output / "audit.md").read_text(encoding="utf-8")
    for path in ("items.recall", "thresholds.item_recall", "stages.loss_map_rule_ai",
                 "fields.missing_rate.method", "activity.all.macro_f1",
                 "activity.fields_correct.macro_f1", "per_school.0.precision"):
        assert f"`{path}`" in markdown
    assert all(not line.strip() or line.startswith("|") for line in markdown.splitlines())


def test_all_pass_and_inclusive_thresholds(tmp_path):
    data = make_inputs(12, perfect=True)
    report, _, _ = run_report(tmp_path, data)
    assert report["verdict"] == {"all_pass": True, "failed": []}
    assert audit.minimum(audit.ratio(99, 100), 0.99) is True
    assert audit.minimum(audit.ratio(95, 100), 0.95) is True
    assert audit.minimum(audit.ratio(9, 10), 0.90) is True


@pytest.mark.parametrize("field,value,failure", [
    ("standards", 86, "unit_dictionary_standards"),
    ("areas", 22, "unit_dictionary_standards"),
    ("problems", ["fake problem"], "unit_dictionary_standards"),
    ("cross_item_matches", 1, "search_cross_item"),
    ("set_mismatches", 1, "search_cross_item"),
    ("count_mismatches", 1, "search_cross_item"),
    ("blocking_public_items", 1, "audit_summary"),
    ("passed", False, "audit_summary"),
])
def test_optional_audit_failures(tmp_path, field, value, failure):
    data = make_inputs(12, perfect=True)
    section = {"standards": "axes_check", "areas": "axes_check", "problems": "axes_check",
               "blocking_public_items": "audit_summary",
               "passed": "audit_summary"}.get(field, "search")
    data[section][field] = value
    report, _, _ = run_report(tmp_path, data)
    assert report["verdict"] == {"all_pass": False, "failed": [failure]}


def test_missing_optional_inputs_are_unknown(tmp_path):
    report, _, _ = run_report(tmp_path, make_inputs(12, perfect=True),
                               omit=("axes_check", "search", "audit_summary"))
    assert report["units"]["dictionary"] is None
    assert report["units"]["pass"]["dictionary"] is None
    assert report["search"] is None
    assert report["audit_summary"] is None
    assert report["verdict"] == {"all_pass": False, "failed": []}
    assert any("axes_check" in note for note in report["notes"])


def test_zero_denominators(tmp_path):
    data = make_inputs()
    for stage in data["score"]["stages"].values():
        stage.update(recall=metric(0, 0), precision=metric(0, 0), pairs=[],
                     unmatched_pipeline=[], unmatched_classification_counts={})
        stage["fields"] = {"method": {"누락": 0, "둘다없음": 4}}
    data["cases"] = []
    data["axes_score"].update(items=[], per_activity={})
    data["axes_score"]["metrics"] = {
        "activity": scorer.activity_metrics([], {}), "units": scorer.unit_metrics([]),
        "secondary": scorer.secondary_metrics([])}
    report, _, _ = run_report(tmp_path, data)
    assert report["items"]["recall"] == metric(0, 0)
    assert report["items"]["pass"]["recall"] is None
    assert report["items"]["pass"]["precision"] is None
    assert report["fields"]["missing_rate"]["method"] == audit.ratio(0, 0)
    assert report["activity"]["all"]["macro_f1"] == audit.ratio(0, 0)
    assert report["activity"]["pass"]["macro_f1"] is None
    assert report["activity"]["fields_correct"]["item_count"] == 0
    assert report["per_school"][0]["precision"] == audit.ratio(0, 0)
    assert any("items.recall 분모 0" in note for note in report["notes"])
    assert report["verdict"]["all_pass"] is False


def test_publish_stage_selects_supplied_stage(tmp_path):
    data = make_inputs()
    stage = data["score"]["stages"]["confirmed"]
    stage["pairs"] = stage["pairs"][:1]
    stage["recall"] = metric(1, 6)
    stage["precision"] = metric(1, 4)
    report, _, _ = run_report(tmp_path, data, stage="confirmed")
    assert report["items"]["recall"] == metric(1, 6)
    assert report["items"]["precision"] == metric(1, 4)
    assert report["per_school"][0]["recall"] == audit.ratio(1, 3)


def test_low_f1_fails_using_upstream_aggregate(tmp_path):
    data = make_inputs(12, perfect=True)
    data["axes_score"]["metrics"]["activity"]["macro_f1"] = scorer.metric(8, 10)
    report, _, _ = run_report(tmp_path, data)
    assert report["activity"]["pass"]["macro_f1"] is False
    assert report["verdict"] == {"all_pass": False, "failed": ["activity_macro_f1"]}


def test_nullable_audit_summary_remains_unknown(tmp_path):
    data = make_inputs(12, perfect=True)
    data["audit_summary"] = {"blocking_public_items": None, "passed": None}
    report, _, _ = run_report(tmp_path, data)
    assert report["verdict"] == {"all_pass": False, "failed": []}
    assert "audit_summary 판정 불가" in report["notes"]


def test_conversion_prefers_structured_observation_and_parent_document_count(tmp_path):
    data = make_inputs(12, perfect=True)
    document = data["conversion"][0]["documents"][0]
    document["converters"] = {"kordoc": {"conversion_status": "failed"},
                              "pymupdf": {"conversion_status": "ok"}}
    document["children"] = [{"conversion_status": "ok"}]
    report, _, _ = run_report(tmp_path, data)
    assert report["stages"]["source_documents"] == 4
    assert report["stages"]["conversion_ok"] == 1
    assert report["stages"]["conversion_failed"] == 3
