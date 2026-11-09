"""S18 개발 재현 사례(T1 방법 값·T3 AI 중복)를 저장 형식 그대로 모으고, 다시 돌린 출력과 대조한다.

Run:
  .venv/Scripts/python.exe scripts/s18_dev_cases.py build --out docs/dev-cases/2026-11-10-extraction-types.json
  .venv/Scripts/python.exe scripts/s18_dev_cases.py check --cases docs/dev-cases/2026-11-10-extraction-types.json
Verify: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_s18_dev_cases.py

입력은 개발 회차(2026-round-3, 2026-round-3-dev2, 2026-round-1-dev2) 산출물만 읽는다. gold 경로는 거부한다.
기대 출력 규칙(사례마다 같은 규칙, 학교별 예외 없음):
- T1: 방법 값 = 그 항목 자기 세부표에서 체크된 '평가 방법' 선택지의 원문 표기(공백만 하나로).
  평가 주체·기록(교사 관찰 및 기록·교사평가·자기평가·동료평가·상호평가)과 수행 형태(개별·모둠)는 값이 아니다.
  체크란이 있는 세부표가 있으면 요약표 평문은 값에 더하지 않는다. 기타에 괄호 내용이 있으면 '기타'와 내용 두 값.
- T3: AI 읽기가 더한 항목의 제목이 같은 문서·학년·학기 규칙 수행 항목 제목과 공백·문장부호만 다르면 그 AI 항목은 없어야 한다.
"""

# ruff: noqa: E501, RUF001, RUF002, RUF003  (한국어 문서 줄·가운뎃점 기호)

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUNDS = (
    ("2026-round-3", "items"),
    ("2026-round-3-dev2", "items_ai"),
    ("2026-round-1-dev2", "items_ai"),
)
DB_STATUSES = ("bounded", "ai_verified")
EVALUATOR_RE = re.compile(
    r"^(?:교사\s*관찰\s*(?:및\s*기록|평가)?|교사\s*평가|관찰\s*및\s*기록|자기\s*평가|동료\s*평가|상호\s*평가)$"
)
ORGANIZATION_RE = re.compile(r"^(?:개별|개인별|모둠별|모둠)\s*(?:수행)?$")
DOTS = str.maketrans({c: "·" for c in "ㆍ･・‧⋅•"})


def guard(path: Path) -> Path:
    if "gold" in path.as_posix().casefold():
        raise ValueError(f"gold 경로 금지: {path}")
    return path


def read_round(round_key: str, folder: str, suffix: str = "") -> dict:
    path = guard(ROOT / f"data/derived/{folder}/{round_key}{suffix}.json")
    return json.loads(path.read_text(encoding="utf-8"))


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text or "")).strip(" ,，/|:：")


def compare_key(text: str) -> str:
    """gold_diff.normalize와 같은 비교 키: 공백·문장부호 제거, 글자는 유지."""
    text = re.sub(r"<br\s*/?\s*>", "", text or "", flags=re.I)
    return "".join(c for c in text.lower()
                   if not c.isspace() and not unicodedata.category(c).startswith("P"))


def is_scorer(text: str) -> bool:
    """값 전체가 평가 주체·기록·수행 형태 어휘뿐이면 참(쉼표·슬래시 나열 포함)."""
    parts = [squash(p).translate(DOTS) for p in re.split(r"[,，/;]", text or "")]
    parts = [p for p in parts if p]
    return bool(parts) and all(EVALUATOR_RE.match(p) or ORGANIZATION_RE.match(p) for p in parts)


def expected_method(method: dict) -> list[str] | None:
    """체크란이 있는 항목만 기대 값을 만든다. 체크란이 없으면 None(대상 아님)."""
    options = [o for o in method.get("options", []) if isinstance(o, dict)]
    if method.get("state") in ("unknown", "conversion_loss"):
        return None
    if not options:
        # 체크란 없는 평문: 평가 주체·형태 칸(method_kind)과 주체·형태 어휘만 뺀다.
        plain = [p for p in method.get("plain", []) if isinstance(p, dict)]
        if not plain or any(o.get("source_role") == "detail" and o.get("options")
                            for o in method.get("source_observations") or []):
            return None
        values = [squash(p.get("text", "")) for p in plain
                  if p.get("method_kind", "method") == "method" and not is_scorer(p.get("text", ""))]
        return list(dict.fromkeys(v for v in values if v))
    values = []
    for option in options:
        if option.get("state") != "checked" or option.get("kind", "method") != "method":
            continue
        text = squash(option.get("option_text", ""))
        if not text or is_scorer(text):
            continue
        other = option.get("other_content")
        if text.startswith("기타"):
            values.append("기타")
            if other and squash(other):
                values.append(squash(other))
        else:
            values.append(text)
    return list(dict.fromkeys(values))


def method_case(round_key: str, item: dict) -> dict | None:
    method = item["fields"]["method"]
    expected = expected_method(method)
    if expected is None:
        return None
    current = method.get("value") or []
    current = current if isinstance(current, list) else [current]
    if {compare_key(v) for v in current} == {compare_key(v) for v in expected}:
        return None
    reasons = []
    if any(is_scorer(v) for v in current):
        reasons.append("평가 주체·형태가 값에 들어감")
    observations = method.get("source_observations") or []
    summary_plain = [v for o in observations if o.get("source_role") == "summary"
                     for v in (o.get("value") or [])]
    if any(compare_key(v) in {compare_key(s) for s in summary_plain} for v in current) and \
            any(compare_key(v) not in {compare_key(e) for e in expected} for v in summary_plain):
        reasons.append("요약표 평문이 세부표 체크 값에 더해짐")
    if any(compare_key(v) not in {compare_key(e) for e in expected} and not is_scorer(v)
           and v not in summary_plain for v in current):
        reasons.append("선택지 원문 표기를 바꿔 씀(서술·논술→서·논술 등)")
    evidence = [{"raw": e.get("raw", ""), "locator": e.get("locator", {}),
                 "method_kind": e.get("method_kind")} for e in method.get("evidence", [])]
    return {
        "type": "T1",
        "case_id": f"T1-{round_key}-{item['item_id'][5:17]}",
        "round": round_key,
        "school": item["school"],
        "grade": item["grade"],
        "semester": item["semester"],
        "item_id": item["item_id"],
        "title": item["fields"]["title"]["value"],
        "source": {"converted_path": item["converted_path"],
                   "locators": [e["locator"] for e in evidence]},
        "input": {"method_evidence": evidence,
                  "summary_observations": [
                      {"value": o.get("value"), "state": o.get("state"),
                       "evidence": [{"raw": e.get("raw", ""), "locator": e.get("locator", {})}
                                    for e in o.get("evidence", [])]}
                      for o in observations if o.get("source_role") == "summary"]},
        "current": current,
        "expected": expected,
        "reasons": reasons,
    }


def duplicate_cases(round_key: str, items: list[dict]) -> list[dict]:
    rules = [i for i in items if i.get("extraction_method") != "ai_read"
             and i.get("candidate_role") == "performance" and i.get("extraction_status") == "bounded"]
    cases = []
    for item in items:
        if item.get("extraction_method") != "ai_read" or item.get("extraction_status") not in DB_STATUSES:
            continue
        key = compare_key(item["fields"]["title"]["value"])
        twins = [r for r in rules if (r["document_id"], r["grade"], r["semester"]) ==
                 (item["document_id"], item["grade"], item["semester"])
                 and compare_key(r["fields"]["title"]["value"]) == key]
        if not twins:
            continue
        cases.append({
            "type": "T3",
            "case_id": f"T3-{round_key}-{item['item_id'][7:19]}",
            "round": round_key,
            "school": item["school"],
            "grade": item["grade"],
            "semester": item["semester"],
            "item_id": item["item_id"],
            "title": item["fields"]["title"]["value"],
            "source": {"converted_path": item["converted_path"], "locators": [item["locator"]],
                       "rule_twin_locators": [t["locator"] for t in twins]},
            "input": {"ai_title_evidence": item["fields"]["title"]["evidence"],
                      "rule_twins": [{"item_id": t["item_id"], "title": t["fields"]["title"]["value"],
                                      "layout_position": t["layout_position"]} for t in twins]},
            "current": "AI 항목이 규칙 세부표 항목과 별도 카드로 남음",
            "expected": "AI 항목 없음(규칙 항목과 같은 과제)",
            "reasons": ["요약표 행에서 AI가 더한 과제가 세부표 규칙 항목과 같은 과제"],
        })
    return cases


def collect(suffix: str = "") -> list[dict]:
    cases = []
    for round_key, folder in ROUNDS:
        data = read_round(round_key, folder, suffix)
        db_items = [i for i in data["items"] if i.get("candidate_role") == "performance"
                    and i.get("extraction_status") in DB_STATUSES]
        cases += [c for i in db_items if (c := method_case(round_key, i))]
        cases += duplicate_cases(round_key, data["items"])
    return cases


def check(cases_path: Path) -> dict:
    """저장된 사례 id를 현재 산출물에서 다시 찾아 남은 사례와 이유를 센다."""
    cases = json.loads(guard(cases_path).read_text(encoding="utf-8"))["cases"]
    current = {(c["type"], c["round"], c["item_id"]): c for c in collect()}
    present = {}
    for round_key, folder in ROUNDS:
        for item in read_round(round_key, folder)["items"]:
            present[(round_key, item["item_id"])] = item
    rows = []
    for case in cases:
        item = present.get((case["round"], case["item_id"]))
        if case["type"] == "T3":
            alive = item is not None and item.get("extraction_status") in DB_STATUSES
            status, why = ("남음", "AI 중복 항목이 여전히 공개 대상") if alive else ("해결", "")
        elif item is None:
            status, why = "확인 불가", "항목 id가 사라짐(규칙 재생성으로 id 변경)"
        else:
            left = current.get(("T1", case["round"], case["item_id"]))
            value = item["fields"]["method"].get("value") or []
            status = "남음" if left else "해결"
            why = "; ".join(left["reasons"]) if left else ""
            case = {**case, "now": value}
        rows.append({"case_id": case["case_id"], "type": case["type"], "school": case["school"],
                     "title": case["title"], "status": status, "reason": why,
                     "now": case.get("now")})
    new = [c for c in current.values()
           if not any(c["item_id"] == r["case_id"] for r in rows)
           and c["case_id"] not in {r["case_id"] for r in rows}]
    return {"total": len(rows),
            "resolved": sum(r["status"] == "해결" for r in rows),
            "remaining": sum(r["status"] == "남음" for r in rows),
            "unknown": sum(r["status"] == "확인 불가" for r in rows),
            "new_cases_not_in_list": len(new),
            "rows": rows,
            "new_cases": [{k: c[k] for k in ("case_id", "school", "title", "current", "expected")}
                          for c in new]}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--suffix", default="", help="예: .prev-s18 (수정 전 스냅숏)")
    chk = sub.add_parser("check")
    chk.add_argument("--cases", type=Path, required=True)
    chk.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.command == "build":
        cases = collect(args.suffix)
        payload = {"schema_version": 1, "rounds": [r for r, _ in ROUNDS],
                   "rule": __doc__.split("기대 출력 규칙")[1].strip(),
                   "counts": {t: sum(c["type"] == t for c in cases) for t in ("T1", "T3")},
                   "cases": cases}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(payload["counts"], ensure_ascii=False))
        return 0
    result = check(args.cases)
    if args.out:
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("total", "resolved", "remaining", "unknown",
                                             "new_cases_not_in_list")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
