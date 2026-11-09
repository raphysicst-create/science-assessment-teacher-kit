"""활동 축 결합: AI 분류(axes_ai)를 쓰되 AI가 기권한 항목만 규칙 분류(axes)로 채운다.

무엇: 회차마다 data/derived/axes_ai/<회차>.json의 activity를 기본으로 쓰고,
      primary가 null이면 data/derived/axes/<회차>.json 같은 item_id의 규칙 activity로 바꿔
      data/derived/axes_hybrid/에 쓴다. rule_version은 science-axes-ai-v1+rule-fallback,
      바뀐 항목의 activity.rule_applied는 "AI 기권→규칙".
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
    summary = {**ai.get("summary", {}), "rule_fallback_filled": filled}
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
        report[round_key] = result["summary"]["rule_fallback_filled"]
    print(json.dumps({"rule_fallback_filled": report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
