"""활동 축 결합: AI 분류(axes_ai)를 쓰되 AI가 기권한 항목만 규칙 분류(axes)로 채운다.

무엇: 회차마다 data/derived/axes_ai/<회차>.json의 activity를 기본으로 쓰고,
      primary가 null이면 data/derived/axes/<회차>.json 같은 item_id의 규칙 activity로 바꿔
      data/derived/axes_hybrid/에 쓴다. rule_version은 science-axes-ai-v1+rule-fallback,
      바뀐 항목의 activity.rule_applied는 "AI 기권→규칙".
      AI 파일의 rule_skipped(규칙이 확실해 AI를 부르지 않은 item_id)는 규칙 activity로 넣고
      rule_applied를 "규칙 확신→AI 생략"으로 둔다(빠지면 공개판에서 버전 표시 없는 규칙 값이 된다).
Run: .venv/Scripts/python.exe scripts/science_axes_hybrid.py --rounds <회차 ...>
Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_science_axes_hybrid.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "science-axes-ai-v1+rule-fallback"
# science_axes_ai targets --skip-rule-confident로 AI를 부르지 않은 카드
SKIPPED_LABEL = "규칙 확신→AI 생략"


def combine(ai: dict, rule: dict) -> dict:
    rules = {item["item_id"]: item for item in rule["items"]}
    items, filled = [], 0
    for item in ai["items"]:
        fallback = rules.get(item["item_id"])
        if item["activity"].get("primary") is None and fallback and \
                fallback["activity"].get("primary") is not None:
            item = {**item, "activity": {**fallback["activity"], "rule_applied": "AI 기권→규칙"}}
            filled += 1
        items.append(item)
    present = {item["item_id"] for item in items}
    skipped = [item_id for item_id in ai.get("rule_skipped", []) if item_id not in present]
    for item_id in skipped:
        if item_id not in rules:
            raise ValueError(f"rule_skipped item missing from rule axes: {item_id}")
        item = rules[item_id]
        items.append({**item, "activity": {**item["activity"], "rule_applied": SKIPPED_LABEL}})
    summary = {**ai.get("summary", {}), "rule_fallback_filled": filled,
               "rule_skipped_filled": len(skipped)}
    return {**ai, "rule_version": VERSION, "items": items, "summary": summary}


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", nargs="+", required=True)
    parser.add_argument("--ai-dir", type=Path, default=ROOT / "data/derived/axes_ai")
    parser.add_argument("--rule-dir", type=Path, default=ROOT / "data/derived/axes")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data/derived/axes_hybrid")
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for round_key in args.rounds:
        ai = json.loads((args.ai_dir / f"{round_key}.json").read_text(encoding="utf-8"))
        rule = json.loads((args.rule_dir / f"{round_key}.json").read_text(encoding="utf-8"))
        result = combine(ai, rule)
        (args.out_dir / f"{round_key}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        report[round_key] = {key: result["summary"][key]
                             for key in ("rule_fallback_filled", "rule_skipped_filled")}
    print(json.dumps({"filled": report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
