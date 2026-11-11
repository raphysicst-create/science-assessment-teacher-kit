"""활동 축: 규칙 주활동과 AI 주활동을 비교해 AI 호출을 건너뛸 조건을 잰다(측정 전용).

무엇: snapshot은 axes_ai_run의 카드별 지시문·응답(마감 시각 이전 파일만)과 규칙 축
      data/derived/axes/<회차>.json을 source_item_id로 이어 한 줄 한 카드로 고정한다.
      analyze는 그 고정본에서 일치율(전체·활동별·확신 신호별)과 건너뛰기 조건을 계산해
      docs/axes-gating/results.json에 쓴다. 정답 세트 회차(-gold)는 읽지 않고 뺀다.
      실행기가 import하지 않는 곳에 두었고 scripts/의 기존 파일은 읽기만 한다.
Run:  .venv/Scripts/python.exe docs/axes-gating/rule_vs_ai.py snapshot --cutoff 2026-11-11T11:50:00
      (--cutoff는 이미 지난 시각이어야 한다. 실행기가 응답을 계속 쓴다.)
      .venv/Scripts/python.exe docs/axes-gating/rule_vs_ai.py analyze
Verify: analyze를 두 번 돌려 results.json sha256이 같은지, snapshot을 같은 --cutoff로
        다시 돌려 manifest의 joined_sha256이 같은지 본다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import middle_ai_read as ai  # noqa: E402  (읽기 전용 사용)
from scripts import science_axes_ai as axes_ai  # noqa: E402

RUN_DIR = ROOT / "data/derived/axes_ai_run"
RULE_DIR = ROOT / "data/derived/axes"
SNAPSHOT_DIR = ROOT / "data/derived/axes_gating"
RESULTS = Path(__file__).resolve().parent / "results.json"
MIN_CELL = 30            # 확신 신호 칸을 표에 낼 최소 카드 수
TARGET_AGREEMENT = 0.97  # 건너뛰기 조건의 기준 일치율
EXAMPLES = 10            # 불일치 예 수


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_gold(round_key: str) -> bool:
    return "gold" in round_key.casefold()


def rule_items(round_key: str, cache: dict) -> dict:
    if round_key not in cache:
        path = RULE_DIR / f"{round_key}.json"
        data = json.loads(ai.read_text(path)) if path.exists() else {"items": []}
        cache[round_key] = {item["item_id"]: item for item in data["items"]}
    return cache[round_key]


def ai_verdict(target: dict, card: dict, cutoff: float, names) -> dict | None:
    answer = RUN_DIR / f"responses/{target['target_id']}.json"
    if not answer.exists() or answer.stat().st_mtime > cutoff:
        return None
    if not ai.valid_run(RUN_DIR, target)[0]:
        return {"valid": False}
    response = ai.parse_response(answer)
    verdict = axes_ai.verify_group([card], response, target["target_id"], names)[0]
    keys = ("primary", "secondary", "abstain_reason", "quote")
    return {"valid": True, **{key: verdict[key] for key in keys}}


def snapshot(cutoff_text: str) -> dict:
    cutoff = datetime.fromisoformat(cutoff_text).timestamp()
    _, names = axes_ai.definition_sections()
    cache: dict = {}
    rows, counts = [], Counter()
    for target in ai.load_targets(RUN_DIR):
        card = target["cards"][0]
        counts["targets"] += 1
        if is_gold(card["source_round"]):
            counts["gold_excluded"] += 1
            continue
        rule = rule_items(card["source_round"], cache).get(card["source_item_id"])
        if rule is None:
            counts["no_rule_item"] += 1
            continue
        act = rule["activity"]
        verdict = ai_verdict(target, card, cutoff, names)
        counts["with_response" if verdict else "no_response"] += 1
        rows.append({
            "item_id": card["item_id"], "source_round": card["source_round"],
            "title": card["title"], "method": card["method"], "window": card["window"],
            "rule": {k: act.get(k) for k in ("primary", "secondary", "abstain_reason",
                                             "candidates", "candidate_classes", "votes_e",
                                             "votes_s", "rule_applied")},
            "rule_evidence_types": sorted({e["type"] for e in act.get("evidence", [])}),
            "ai": verdict,
        })
    rows.sort(key=lambda row: row["item_id"])
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    (SNAPSHOT_DIR / "joined.jsonl").write_bytes(data.encode("utf-8"))
    manifest = {"cutoff": cutoff_text, "counts": dict(sorted(counts.items())),
                "joined_sha256": sha256_bytes(data.encode("utf-8"))}
    (SNAPSHOT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest


# ---------- 확신 신호 ----------

def margin_e(rule: dict) -> int | None:
    """E층에서 주활동 표 - 다른 활동 최다 표."""
    votes = rule.get("votes_e") or {}
    primary = rule["primary"]
    if not votes or primary is None:
        return None
    others = [v for k, v in votes.items() if k != primary]
    return votes.get(primary, 0) - (max(others) if others else 0)


def bucket(value: int | None) -> str:
    if value is None:
        return "없음"
    return "≤-1" if value < 0 else ("0" if value == 0 else ("1" if value == 1 else "≥2"))


def signals(row: dict) -> dict:
    rule = row["rule"]
    classes = rule.get("candidate_classes") or []
    content = [c for c in classes if c != "scorer_marker"]
    return {
        "rule_applied": rule.get("rule_applied") or "-",
        "n_classes": str(min(len(content), 2)) + ("+" if len(content) >= 2 else ""),
        "class": content[0] if len(content) == 1 else ("여럿" if content else "없음"),
        "primary_e_votes": bucket((rule.get("votes_e") or {}).get(rule["primary"])),
        "margin_e": bucket(margin_e(rule)),
        "n_secondary": str(min(len(rule.get("secondary") or []), 2)),
        "basis": ("checkbox" if "checkbox" in row["rule_evidence_types"] else
                  "method_text" if "method_text" in row["rule_evidence_types"] else "기타"),
    }


# ---------- 건너뛰기 조건 (사람이 읽는 규칙 하나) ----------

SKIP_MARGIN = 3        # 채택: E층 주활동 표 - 다른 활동 최다 표 >= 3
ALT_MARGIN = 2         # 대안(더 넓음): >=2 이면서 전환·다중 체크가 아닌 판정
ALT_RULES = ("R5", "R5-②", "R7")


def skip_condition(row: dict) -> bool:
    """규칙을 그대로 쓰고 AI를 부르지 않는 조건(채택안)."""
    value = margin_e(row["rule"])
    return row["rule"]["primary"] is not None and value is not None and value >= SKIP_MARGIN


def alt_condition(row: dict) -> bool:
    value = margin_e(row["rule"])
    if row["rule"]["primary"] is None or value is None:
        return False
    rule_applied = row["rule"].get("rule_applied")
    return skip_condition(row) or (value >= ALT_MARGIN and rule_applied in ALT_RULES)


# ---------- 집계 ----------

def rate(agree: int, total: int) -> float | None:
    return round(agree / total, 4) if total else None


def compared(rows):
    """규칙·AI 모두 주활동이 있는 카드(엄격 일치율 대상)."""
    return [r for r in rows if r["ai"] and r["ai"].get("valid") and r["ai"]["primary"]
            and r["rule"]["primary"]]


def agreement(rows) -> dict:
    pairs = compared(rows)
    agree = sum(r["rule"]["primary"] == r["ai"]["primary"] for r in pairs)
    return {"n": len(pairs), "agree": agree, "rate": rate(agree, len(pairs))}


def by_key(rows, key_fn) -> dict:
    groups = defaultdict(list)
    for r in compared(rows):
        groups[key_fn(r)].append(r)
    return {k: agreement(v) for k, v in sorted(groups.items()) if len(v) >= MIN_CELL}


def half(row) -> str:
    return "A" if int(hashlib.sha256(row["item_id"].encode()).hexdigest(), 16) % 2 == 0 else "B"


def wilson_lower(agree: int, n: int, z: float = 1.96) -> float | None:
    if not n:
        return None
    p = agree / n
    centre = p + z * z / (2 * n)
    spread = z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5
    return round((centre - spread) / (1 + z * z / n), 4)


def example(row: dict, where: str) -> dict:
    return {"where": where, "item_id": row["item_id"], "round": row["source_round"],
            "title": row["title"], "method": row["method"], "rule": row["rule"]["primary"],
            "rule_applied": row["rule"].get("rule_applied"), "votes_e": row["rule"]["votes_e"],
            "ai": row["ai"]["primary"], "ai_quote": row["ai"]["quote"],
            "margin_e": margin_e(row["rule"]), "window": row["window"]}


def disagreements(rows) -> list:
    return sorted((r for r in compared(rows) if r["rule"]["primary"] != r["ai"]["primary"]),
                  key=lambda r: sha256_bytes(r["item_id"].encode()))


def condition_report(rows, responded, nationwide, condition, with_examples) -> dict:
    chosen = [r for r in responded if condition(r)]
    agree = agreement(chosen)
    changed = disagreements(chosen)
    report = {
        "agreement": agree,
        "wilson95_lower": wilson_lower(agree["agree"], agree["n"]),
        "by_half": {h: agreement([r for r in chosen if half(r) == h]) for h in "AB"},
        "by_rule_primary": by_key(chosen, lambda r: r["rule"]["primary"]),
        "share_all_cards": rate(sum(map(condition, rows)), len(rows)),
        "share_nationwide_cards": rate(sum(map(condition, nationwide)), len(nationwide)),
        "share_responded": rate(len(chosen), len(responded)),
        "output_changed_if_skipped": {"n": len(changed), "of_responded": len(chosen),
                                      "rate": rate(len(changed), len(chosen))},
        "disagreement_pairs": dict(Counter(
            f"{r['rule']['primary']}→AI {r['ai']['primary']}" for r in changed).most_common()),
    }
    if with_examples:
        # 조건 안 불일치 전부, 모자라면 경계(표 차이 = SKIP_MARGIN-1)에서 해시 순으로 채운다.
        border = [r for r in responded
                  if r["rule"]["primary"] and margin_e(r["rule"]) == SKIP_MARGIN - 1]
        picked = [example(r, "조건 안") for r in changed]
        picked += [example(r, f"경계(표 차이 {SKIP_MARGIN - 1})")
                   for r in disagreements(border)][:max(0, EXAMPLES - len(picked))]
        report["examples"] = picked
    return report


def analyze() -> dict:
    lines = (SNAPSHOT_DIR / "joined.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    manifest = json.loads((SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8"))
    responded = [r for r in rows if r["ai"] and r["ai"].get("valid")]
    signal_names = list(signals(rows[0]).keys())
    nationwide = [r for r in rows if "-nw" in r["source_round"]]
    result = {
        "snapshot": manifest,
        "cards": len(rows), "responded_valid": len(responded),
        "rule_abstained": sum(r["rule"]["primary"] is None for r in rows),
        "ai_abstained_among_responded": sum(r["ai"]["primary"] is None for r in responded),
        "overall": agreement(rows),
        "by_rule_primary": by_key(rows, lambda r: r["rule"]["primary"]),
        "by_ai_primary": by_key(rows, lambda r: r["ai"]["primary"]),
        "by_signal": {name: by_key(rows, lambda r, n=name: signals(r)[n]) for name in signal_names},
        "by_rule_applied_x_class": by_key(
            rows, lambda r: signals(r)["rule_applied"] + "|" + signals(r)["class"]),
        "by_r5_class_margin": by_key(
            [r for r in rows if signals(r)["rule_applied"] == "R5"],
            lambda r: signals(r)["class"] + "|margin " + signals(r)["margin_e"]),
        "margin_e_exact": by_key(rows, lambda r: str(margin_e(r["rule"]))),
        "skip_condition": condition_report(rows, responded, nationwide, skip_condition, True),
        "alt_condition": condition_report(rows, responded, nationwide, alt_condition, False),
    }
    text = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    RESULTS.write_bytes(text.encode("utf-8"))
    result["results_sha256"] = sha256_bytes(text.encode("utf-8"))
    return result


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot")
    snap.add_argument("--cutoff", required=True, help="이 시각 이후에 쓴 응답은 무시(ISO, 현지)")
    sub.add_parser("analyze")
    args = parser.parse_args(argv)
    if args.command == "snapshot":
        print(json.dumps(snapshot(args.cutoff), ensure_ascii=False))
    else:
        out = analyze()
        brief = {k: out[k] for k in ("cards", "responded_valid", "overall", "results_sha256")}
        brief["skip"] = {k: out["skip_condition"][k] for k in
                         ("agreement", "wilson95_lower", "share_all_cards", "share_responded")}
        print(json.dumps(brief, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
