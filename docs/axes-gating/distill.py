"""활동 축 증류(M2): 이미 받은 AI 판정을 정답 삼아 AI를 건너뛸 카드를 고르는 게이트를 잰다.

무엇: snapshot은 axes_ai_run 카드별 응답(마감 이전 파일)과 규칙 축을 이어 고정본
      data/derived/axes_gating/m2-joined.jsonl을 만든다(M1 rule_vs_ai.snapshot과 같은 판정 함수,
      학교 이름·case_id를 더함). analyze는 학교 단위로 학습(70%)/평가(30%)를 나누고
      (1) M1 기준선 E표차>=3, (2) 미리 적은 규칙 후보 중 학습 쪽에서 고른 것,
      (3) 순수 파이썬 로지스틱 회귀(학습 쪽 교차검증으로 문턱)를 평가 쪽에서 잰다.
      채택 게이트는 실행 코드 scripts/science_axes_gate.should_skip을 그대로 import해 잰다.
      결과는 docs/axes-gating/m2-results.json. 정답 세트(-gold)는 읽지 않는다.
      개발 F1 회차(2026-round-3, -dev2)와 fresh 회차는 학습·평가에서 뺀다.
      새 의존성 없음(numpy·sklearn 없이 표준 라이브러리만).
Run:  .venv/Scripts/python.exe docs/axes-gating/distill.py snapshot --cutoff 2026-11-11T12:06:00
      .venv/Scripts/python.exe docs/axes-gating/distill.py analyze
Verify: analyze를 두 번 돌려 m2-results.json sha256이 같은지 본다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import rule_vs_ai as m1  # noqa: E402
from scripts import middle_ai_read as ai  # noqa: E402  (읽기 전용 사용)
from scripts import science_axes_ai as axes_ai  # noqa: E402
from scripts import science_axes_gate as gate  # noqa: E402

SNAPSHOT = ROOT / "data/derived/axes_gating/m2-joined.jsonl"
MANIFEST = ROOT / "data/derived/axes_gating/m2-manifest.json"
RESULTS = HERE / "m2-results.json"
HELD_OUT_ROUNDS = ("2026-round-3", "2026-round-3-dev2", "2026-round-1-dev2")  # 개발 F1 회차
TEST_SHARE = 30          # 학교 해시 % 100 < 30 이면 평가 쪽
FOLDS = 5                # 학교 단위 교차검증 겹 수
TRAIN_RATE, TRAIN_LOWER = 0.98, 0.96   # 학습 쪽에서 고르는 기준(평가 기준보다 엄격하게)
TEST_RATE, TEST_LOWER = 0.97, 0.96     # 완료 기준 2(평가 쪽)
L2, EPOCHS, STEP = 1.0, 300, 0.5


# ---------- 고정본 ----------

def snapshot(cutoff_text: str) -> dict:
    cutoff = datetime.fromisoformat(cutoff_text).timestamp()
    _, names = axes_ai.definition_sections()
    cache: dict = {}
    rows, counts = [], Counter()
    for target in ai.load_targets(m1.RUN_DIR):
        card = target["cards"][0]
        counts["targets"] += 1
        if m1.is_gold(card["source_round"]):
            counts["gold_excluded"] += 1
            continue
        rule = m1.rule_items(card["source_round"], cache).get(card["source_item_id"])
        if rule is None:
            counts["no_rule_item"] += 1
            continue
        act = rule["activity"]
        verdict = m1.ai_verdict(target, card, cutoff, names)
        counts["with_response" if verdict else "no_response"] += 1
        rows.append({
            "item_id": card["item_id"], "source_round": card["source_round"],
            "school": card["school_name"], "case_id": card["case_id"],
            "title": card["title"], "method": card["method"],
            "rule": {k: act.get(k) for k in ("primary", "secondary", "candidates",
                                             "candidate_classes", "votes_e", "votes_s",
                                             "rule_applied")},
            "rule_evidence_types": sorted({e["type"] for e in act.get("evidence", [])}),
            "ai": verdict,
        })
    rows.sort(key=lambda row: row["item_id"])
    data = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_bytes(data.encode("utf-8"))
    manifest = {"cutoff": cutoff_text, "counts": dict(sorted(counts.items())),
                "joined_sha256": m1.sha256_bytes(data.encode("utf-8"))}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest


# ---------- 특징 (규칙 출력 + 제목·방법 낱말, 실행 시점에 다 있는 값) ----------

def margin(votes: dict, primary: str) -> int:
    others = [v for k, v in votes.items() if k != primary]
    return votes.get(primary, 0) - (max(others) if others else 0)


def clip(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def features(row: dict) -> list[str]:
    """로지스틱 회귀용 이진 특징 이름들."""
    rule = row["rule"]
    p = rule["primary"]
    ve, vs = rule.get("votes_e") or {}, rule.get("votes_s") or {}
    de, ds = clip(margin(ve, p), -2, 4), clip(margin(vs, p), -2, 4)
    classes = [c for c in rule.get("candidate_classes") or [] if c != "scorer_marker"]
    feats = [f"p={p}", f"me={de}", f"ms={ds}", f"p|me={p}|{de}", f"p|ms={p}|{ds}",
             f"ra={rule.get('rule_applied')}", f"pe={clip(ve.get(p, 0), 0, 5)}",
             f"ps={clip(vs.get(p, 0), 0, 5)}", f"nc={min(len(classes), 3)}",
             f"ns={min(len(rule.get('secondary') or []), 3)}",
             f"cand_has_p={p in (rule.get('candidates') or [])}",
             f"me_ms={clip(de, -1, 3)}|{clip(ds, -1, 3)}"]
    feats += [f"cls={c}" for c in classes]
    feats += [f"ev={e}" for e in row["rule_evidence_types"]]
    feats += [f"tw={w}" for w in set((row["title"] or "").replace("·", " ").split())]
    feats.append(f"m={(row.get('method') or '')[:12]}")
    return feats


# ---------- 나누기 ----------

def school_bucket(school: str, salt: str = "") -> int:
    return int(hashlib.sha256((salt + school).encode("utf-8")).hexdigest(), 16) % 100


def usable(rows):
    """학습·평가 대상: 개발 F1·fresh 회차가 아니고 규칙·AI 모두 주활동이 있는 카드."""
    return [r for r in m1.compared(rows)
            if r["source_round"] not in HELD_OUT_ROUNDS and "fresh" not in r["source_round"]]


def label(row) -> int:
    return int(row["rule"]["primary"] == row["ai"]["primary"])


# ---------- 규칙 후보 (사람이 읽는 조건, 학습 쪽에서 하나 고른다) ----------

def e_gap(r):
    return gate.e_margin(r["rule"])


def s_gap(r):
    return margin(r["rule"].get("votes_s") or {}, r["rule"]["primary"])


def n_sec(r):
    return len(r["rule"].get("secondary") or [])


RULE_CANDIDATES = {
    "E>=3": lambda r: e_gap(r) >= 3,
    "E>=3 | E>=2&보조0": lambda r: e_gap(r) >= 3 or (e_gap(r) >= 2 and n_sec(r) == 0),
    "E>=3 | E>=2&보조<=1": lambda r: e_gap(r) >= 3 or (e_gap(r) >= 2 and n_sec(r) <= 1),
    "E>=3 | E>=2&S>=2": lambda r: e_gap(r) >= 3 or (e_gap(r) >= 2 and s_gap(r) >= 2),
    "E>=2&S>=1": lambda r: e_gap(r) >= 2 and s_gap(r) >= 1,
    "보조0&E>=1": lambda r: n_sec(r) == 0 and e_gap(r) >= 1,
    "E>=3 | 보조0&E>=1&S>=1": lambda r: e_gap(r) >= 3 or (
        n_sec(r) == 0 and e_gap(r) >= 1 and s_gap(r) >= 1),
    "E>=3 | E>=2&보조0 | 보조0&E>=1&S>=1": lambda r: e_gap(r) >= 3 or (
        e_gap(r) >= 2 and n_sec(r) == 0) or (n_sec(r) == 0 and e_gap(r) >= 1 and s_gap(r) >= 1),
}


def guarded(fn):
    return lambda r: r["rule"]["primary"] is not None and e_gap(r) is not None and fn(r)


def gate_fn(r) -> bool:
    return gate.should_skip(r["rule"])


def stats(rows, chosen_fn) -> dict:
    chosen = [r for r in rows if chosen_fn(r)]
    agree = sum(label(r) for r in chosen)
    return {"n": len(chosen), "agree": agree, "rate": m1.rate(agree, len(chosen)),
            "wilson95_lower": m1.wilson_lower(agree, len(chosen)),
            "coverage": m1.rate(len(chosen), len(rows))}


def meets(s, rate, lower) -> bool:
    return bool(s["n"]) and s["agree"] / s["n"] >= rate and (s["wilson95_lower"] or 0) >= lower


# ---------- 로지스틱 회귀 (순수 파이썬, 전체 배치 경사 하강) ----------

def fit(rows, vocab_min=5):
    counts = Counter(f for r in rows for f in set(features(r)))
    vocab = sorted(f for f, c in counts.items() if c >= vocab_min)
    index = {f: i for i, f in enumerate(vocab)}
    xs = [[index[f] for f in set(features(r)) if f in index] for r in rows]
    ys = [label(r) for r in rows]
    w, b, n = [0.0] * len(vocab), 0.0, len(rows)
    for _ in range(EPOCHS):
        gw, gb = [0.0] * len(vocab), 0.0
        for x, y in zip(xs, ys, strict=True):
            err = 1 / (1 + math.exp(-(b + sum(w[i] for i in x)))) - y
            gb += err
            for i in x:
                gw[i] += err
        b -= STEP * gb / n
        for i in range(len(w)):
            w[i] -= STEP * (gw[i] / n + L2 * w[i] / n)
    return {"bias": b, "weights": {f: w[i] for f, i in index.items()}}


def prob(model, row) -> float:
    z = model["bias"] + sum(model["weights"].get(f, 0.0) for f in set(features(row)))
    return 1 / (1 + math.exp(-z))


def oof_scores(rows):
    """학습 쪽 안에서 학교 단위 FOLDS겹 교차검증 확률(평가 나누기와 다른 해시 소금)."""
    out = []
    for fold in range(FOLDS):
        inner = [r for r in rows if school_bucket(r["school"], "inner") % FOLDS != fold]
        held = [r for r in rows if school_bucket(r["school"], "inner") % FOLDS == fold]
        model = fit(inner)
        out += [(prob(model, r), label(r)) for r in held]
    return out


def pick_threshold(scored):
    """덮는 카드가 TRAIN_RATE·TRAIN_LOWER를 만족하는 가장 낮은 확률 문턱(커버리지 최대)."""
    best, agree = None, 0
    for k, (score, y) in enumerate(sorted(scored, key=lambda s: -s[0]), 1):
        agree += y
        if k >= 30 and agree / k >= TRAIN_RATE and m1.wilson_lower(agree, k) >= TRAIN_LOWER:
            best = score
    return best


# ---------- 보고 ----------

def nationwide_coverage(rows, fn) -> dict:
    """전국 회차 카드(AI 응답 유무와 무관) 중 게이트가 건너뛰는 비율."""
    groups = defaultdict(list)
    for r in rows:
        if "-nw" in r["source_round"]:
            groups[r["source_round"]].append(r)
    by_round = {k: m1.rate(sum(bool(r["rule"]["primary"]) and fn(r) for r in v), len(v))
                for k, v in sorted(groups.items())}
    cards = [r for v in groups.values() for r in v]
    hit = sum(bool(r["rule"]["primary"]) and fn(r) for r in cards)
    return {"cards": len(cards), "skipped": hit, "share": m1.rate(hit, len(cards)),
            "by_round": by_round}


def output_changed(rows, fn) -> dict:
    """유효 AI 응답이 있는 카드 중 건너뛰면 최종 주활동이 바뀌는 카드(AI 기권은 지금도 규칙)."""
    responded = [r for r in rows if r["ai"] and r["ai"].get("valid") and r["rule"]["primary"]
                 and r["source_round"] not in HELD_OUT_ROUNDS and "fresh" not in r["source_round"]]
    chosen = [r for r in responded if fn(r)]
    changed = sum(bool(r["ai"]["primary"]) and r["ai"]["primary"] != r["rule"]["primary"]
                  for r in chosen)
    return {"skipped": len(chosen), "changed": changed, "rate": m1.rate(changed, len(chosen))}


def analyze() -> dict:
    rows = [json.loads(line) for line in SNAPSHOT.read_text(encoding="utf-8").splitlines()]
    data = usable(rows)
    train = [r for r in data if school_bucket(r["school"]) >= TEST_SHARE]
    test = [r for r in data if school_bucket(r["school"]) < TEST_SHARE]
    leak = sorted({r["school"] for r in train} & {r["school"] for r in test})

    candidates = {}
    for name, fn in RULE_CANDIDATES.items():
        train_stats = stats(train, guarded(fn))
        candidates[name] = {"train": train_stats, "test": stats(test, guarded(fn)),
                            "train_selectable": meets(train_stats, TRAIN_RATE, TRAIN_LOWER)}
    selectable = [n for n, v in candidates.items() if v["train_selectable"]]
    chosen = max(selectable, key=lambda n: candidates[n]["train"]["n"]) if selectable else None
    same = chosen is not None and all(gate_fn(r) == guarded(RULE_CANDIDATES[chosen])(r)
                                      for r in rows if r["rule"]["primary"])

    threshold = pick_threshold(oof_scores(train))
    model = fit(train)

    def lr_fn(r):
        return threshold is not None and prob(model, r) >= threshold

    def report(fn):
        test_stats = stats(test, fn)
        return {"train": stats(train, fn), "test": test_stats,
                "passes_test": meets(test_stats, TEST_RATE, TEST_LOWER),
                "nationwide": nationwide_coverage(rows, fn)}

    folds = {str(k): stats([r for r in data if school_bucket(r["school"], "fold") % FOLDS == k],
                           gate_fn) for k in range(FOLDS)}
    result = {
        "snapshot_sha256": json.loads(MANIFEST.read_text(encoding="utf-8"))["joined_sha256"],
        "split": {"usable_cards": len(data), "train_cards": len(train), "test_cards": len(test),
                  "train_schools": len({r["school"] for r in train}),
                  "test_schools": len({r["school"] for r in test}),
                  "schools_in_both": len(leak),
                  "train_agreement_all": m1.rate(sum(map(label, train)), len(train)),
                  "test_agreement_all": m1.rate(sum(map(label, test)), len(test))},
        "rule_candidates": candidates,
        "chosen_rule": chosen,
        "gate_equals_chosen_rule": same,
        "compare": {
            "M1 E>=3 (기준선)": report(guarded(RULE_CANDIDATES["E>=3"])),
            "채택 게이트 science_axes_gate": report(gate_fn),
            "로지스틱 회귀(학습 OOF 문턱)": {**report(lr_fn),
                                        "threshold": None if threshold is None
                                        else round(threshold, 6)},
        },
        "gate_school_folds_all_usable": folds,
        "gate_output_changed": output_changed(rows, gate_fn),
        "lr_top_weights": sorted(((f, round(w, 3)) for f, w in model["weights"].items()),
                                 key=lambda t: (-abs(t[1]), t[0]))[:15],
    }
    RESULTS.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return result


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("snapshot").add_argument("--cutoff", required=True)
    sub.add_parser("analyze")
    args = parser.parse_args(argv)
    out = snapshot(args.cutoff) if args.command == "snapshot" else analyze()
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
