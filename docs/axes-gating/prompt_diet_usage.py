"""AI 단계 4개(first-run, fields-run, ax-run, cc-run)의 호출당 토큰과 묶음 총량을 잰다(M3).

저장된 Codex 이벤트만 읽는다.

무엇: 각 단계 응답 폴더의 *.events.jsonl 마지막 turn.completed usage와 지시문(prompts/*.md) 크기를
      묶음(회차 접미사 nw1·nw2·nw3)별로 모은다. 호출하지 않는다(저장 파일만 읽음).
      - first-run / fields-run: data/derived/ai_read/<회차>/first|fields
      - ax-run: data/derived/axes_ai_run (targets.jsonl의 cards[].source_round로 묶음을 가른다)
      - cc-run: data/derived/card_check3 (card_ids를 ax 목표의 카드 회차로 묶음에 매긴다)
      지시문 크기 대 입력 토큰의 직선(최소제곱)으로 Codex 고정 부분(절편)을 추정한다.
Run:    .venv/Scripts/python.exe docs/axes-gating/prompt_diet_usage.py
Verify: 두 번 돌려 prompt-diet-usage.json sha256이 같은지 본다.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AI_READ = ROOT / "data/derived/ai_read"
AXES_RUN = ROOT / "data/derived/axes_ai_run"
CARD_RUN = ROOT / "data/derived/card_check3"
RESULTS = HERE / "prompt-diet-usage.json"
BUNDLE = re.compile(r"-(nw\d+)$")
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


def last_usage(events: Path) -> dict | None:
    usage = None
    for line in events.read_text(encoding="utf-8").splitlines():
        if '"turn.completed"' in line:
            usage = json.loads(line).get("usage")
    return usage


def bundle_of(source_round: str) -> str | None:
    match = BUNDLE.search(source_round)
    return match[1] if match else None


def record(stage_rows: dict, stage: str, bundle: str | None, run_dir: Path, target_id: str):
    events = run_dir / f"responses/{target_id}.events.jsonl"
    prompt = run_dir / f"prompts/{target_id}.md"
    if bundle is None or not events.exists() or not prompt.exists():
        return
    usage = last_usage(events)
    if usage:
        stage_rows[(stage, bundle)].append(
            {**{k: usage.get(k, 0) for k in USAGE_KEYS}, "prompt_bytes": prompt.stat().st_size})


def read_targets(run_dir: Path) -> list[dict]:
    path = run_dir / "targets.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def collect() -> tuple[dict, dict]:
    rows: dict = defaultdict(list)
    for round_dir in sorted(AI_READ.iterdir()):
        bundle = bundle_of(round_dir.name)
        for stage, sub in (("first-run", "first"), ("fields-run", "fields")):
            for target in read_targets(round_dir / sub):
                record(rows, stage, bundle, round_dir / sub, target["target_id"])
    card_round = {}
    for target in read_targets(AXES_RUN):
        for card in target.get("cards", []):
            card_round[card["item_id"]] = card["source_round"]
        rounds = {c["source_round"] for c in target.get("cards", [])}
        if len(rounds) == 1:
            record(rows, "ax-run", bundle_of(rounds.pop()), AXES_RUN, target["target_id"])
    pending = defaultdict(int)  # 목표는 있으나 응답이 아직 없는 cc 목표(묶음별)
    for target in read_targets(CARD_RUN):
        rounds = {card_round.get(i, "") for i in target["card_ids"]}
        bundle = bundle_of(rounds.pop()) if len(rounds) == 1 else None
        if bundle and not (CARD_RUN / f"responses/{target['target_id']}.events.jsonl").exists():
            pending[bundle] += 1
        record(rows, "cc-run", bundle, CARD_RUN, target["target_id"])
    return rows, dict(pending)


def summarize(items: list[dict]) -> dict:
    n = len(items)
    total = {k: sum(i[k] for i in items) for k in (*USAGE_KEYS, "prompt_bytes")}
    return {"calls": n,
            "mean": {k: round(v / n, 1) for k, v in total.items()},
            "total": total,
            "uncached_input_total": total["input_tokens"] - total["cached_input_tokens"]}


def fit(items: list[dict]) -> dict:
    """입력 토큰 = a + b × 지시문 바이트. 절편 a는 지시문 밖 Codex 고정 부분 추정."""
    xs = [i["prompt_bytes"] for i in items]
    ys = [i["input_tokens"] for i in items]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    return {"n": n, "intercept_tokens": round(my - b * mx), "tokens_per_kb": round(b * 1000, 1)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows, pending = collect()
    result = {"by_stage_bundle": {f"{s}|{b}": summarize(v) for (s, b), v in sorted(rows.items())},
              "cc_pending_targets_by_bundle": pending,
              "fit_all_stages": fit([i for v in rows.values() for i in v])}
    RESULTS.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for key, value in result["by_stage_bundle"].items():
        m = value["mean"]
        print(f"{key:18} calls {value['calls']:6} in {m['input_tokens']:8} cached "
              f"{m['cached_input_tokens']:8} out {m['output_tokens']:6} reas "
              f"{m['reasoning_output_tokens']:6} KB {m['prompt_bytes'] / 1000:6.1f}")
    print("cc pending", pending, "fit", result["fit_all_stages"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
