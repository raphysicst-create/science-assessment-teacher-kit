"""정답 세트 보조 지표: 합침·과분할·중복, 방법·제목 오값 유형, 공개 단계, 코드 P/R, 종단 일치율.

무엇을 하는가: gold_score 출력(JSON)·활동 채점 출력(JSON)·과학 DB·위험 큐를 읽어
`audit_science_gold.py`가 내지 않는 Q2-2 보조 지표를 `public-stage.json`으로 낸다.
채점을 다시 하지 않는다.
돌리기:
  .venv/Scripts/python.exe scripts/audit_science_gold_public_stage.py     --score S.json --axes-score X.json     --database data/publish/science/math_assessment_catalog_detail.sqlite     --risk-queue data/derived/science_audit/risk-queue.csv --out OUT.json     [--merged-title-substring 문구]
검증: 출력의 public_stage.confirmed가 S.json stages.rule_ai.pairs 길이와 같다.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sqlite3
from pathlib import Path

UNIT_OK = ("완전 일치", "정답 단원 없음")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def db_status_fn(database: Path, risk_queue: Path):
    con = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    ids = {r[0]: r[1] for r in con.execute("SELECT source_item_id, item_id FROM assessment_items")}
    with risk_queue.open(encoding="utf-8-sig", newline="") as handle:
        blocked = {row["item_id"] for row in csv.DictReader(handle)}

    def status(pipeline_key: str) -> str:
        item_id = ids.get(pipeline_key.split("/")[-1])
        if item_id is None:
            return "DB 없음"
        return "차단" if item_id in blocked else "공개"
    return status


def build(score: dict, axes: dict, status, merged_substring: str) -> dict:
    stage = score["stages"]["rule_ai"]
    pairs = stage["pairs"]
    method_types: collections.Counter = collections.Counter()
    method_schools: collections.Counter = collections.Counter()
    title_types: collections.Counter = collections.Counter()
    field_ok = {}
    for pair in pairs:
        method = pair["fields"]["method"]
        title = pair["fields"]["title"]
        if method["result"] == "오값":
            value = method["pipeline_value"]
            count = len(value) if isinstance(value, list) else 1
            method_types["선택지 2개 이상" if count > 1 else "선택지 1개"] += 1
            method_schools[pair["gold_key"].rsplit("-g", 1)[0]] += 1
        if title["result"] == "오값":
            value = str(title["pipeline_value"])
            title_types["평가 영역명: 접두" if value.startswith("평가 영역명") else value] += 1
        field_ok[pair["gold_key"]] = (method["result"] in ("정답", "둘다없음")
                                      and title["result"] == "정답")
    pair_status = collections.Counter(status(p["pipeline_key"]) for p in pairs)
    extras = collections.Counter(
        f"{u['classification']}|{status(u['pipeline_key'])}" for u in stage["unmatched_pipeline"])
    merged = (sum(1 for u in stage["unmatched_pipeline"]
                  if merged_substring in (u.get("title") or ""))
              if merged_substring else None)  # 합침 표지가 없으면 세지 않음(null)
    pair_key = {p["gold_key"]: p["pipeline_key"] for p in pairs}
    items = axes["items"]
    total = axes["gold_total"]
    e2e = [i for i in items if i["result"] == "일치" and i["unit_result"] in UNIT_OK]
    e2e_fields = [i for i in e2e if field_ok.get(i["item_key"])]
    e2e_public = [i for i in e2e if status(pair_key.get(i["item_key"], "")) == "공개"]
    standards = stage["fields"]["standards"]
    return {
        "method_wrong_value_types": dict(method_types),
        "method_wrong_value_schools": dict(method_schools),
        "title_wrong_value_types": dict(title_types),
        "matched_pairs_public_status": dict(pair_status),
        "unmatched_pipeline_public_status": dict(extras),
        "merged_items": merged, "split_items": 0,
        "duplicate_items": stage["unmatched_classification_counts"].get("요약·중복", 0),
        "public_stage": {"confirmed": len(pairs), "public": pair_status.get("공개", 0),
                         "blocked": pair_status.get("차단", 0),
                         "not_in_db": pair_status.get("DB 없음", 0)},
        "pair_activity_unit_match": {
            "numerator": len(e2e), "denominator": total,
            "definition": "짝·주활동 일치·단원(완전 일치 또는 정답 코드 없음). 필드는 보지 않음"},
        "end_to_end_correct_with_fields": {
            "numerator": len(e2e_fields), "denominator": total,
            "definition": "위 조건 + 방법 필드 정답(또는 둘다없음) + 제목 필드 정답"},
        "pair_activity_unit_match_public": {"numerator": len(e2e_public), "denominator": total},
        "standards_code": {
            "recall": {"numerator": standards["정답"],
                       "denominator": standards["정답"] + standards["누락"] + standards["오값"]},
            "precision": {"numerator": standards["정답"],
                          "denominator": standards["정답"] + standards["오값"]},
            "definition": "항목 단위. fields.per_field.standards: 정답/(정답+누락+오값), 정답/(정답+오값)"},
        "overall_primary_accuracy": axes["metrics"]["overall_primary_accuracy"]["fraction"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--axes-score", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--risk-queue", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--merged-title-substring", default="")
    args = parser.parse_args()
    result = build(load(args.score), load(args.axes_score),
                   db_status_fn(args.database, args.risk_queue), args.merged_title_substring)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    keys = ("public_stage", "pair_activity_unit_match", "end_to_end_correct_with_fields",
            "standards_code", "method_wrong_value_schools")
    print(json.dumps({k: result[k] for k in keys}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
