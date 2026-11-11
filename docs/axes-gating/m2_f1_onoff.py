"""활동 축 게이트 켠 판·끈 판의 개발 활동 F1(255짝, 공개판 입력)을 같은 채점 명령으로 잰다(M2).

무엇: 개발 F1 회차 3개의 공개판 AI 축(data/derived/axes_ai)과 규칙 축(data/derived/axes)으로
      끈 판 = science_axes_hybrid.combine(ai, rule),
      켠 판 = science_axes_gate.should_skip이 고른 카드를 AI 결과에서 빼고 rule_skipped로
      넘긴 뒤 같은 combine을 만들어 data/derived/axes_gating/m2-hybrid-{off,on}/에 쓰고,
      N1 devcheck와 같은 채점
      (scripts/dev_activity_score.py, 라벨 data/dev_labels/labels/claude-dev-all.jsonl)으로 잰다.
      지금 공개판 혼합 축(data/derived/axes_hybrid)도 같은 채점으로 함께 잰다(끈 판 재현 확인).
      켠 판은 이 회차 카드에 저장된 응답이 없다고 가정한다(묶음 4~6에서 실제로 일어나는 일).
      라벨 파일은 채점 함수만 읽는다. 결과는 docs/axes-gating/m2-f1.json.
Run:    .venv/Scripts/python.exe docs/axes-gating/m2_f1_onoff.py
Verify: 두 번 돌려 m2-f1.json sha256이 같은지 본다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import dev_activity_score as score  # noqa: E402
import science_axes_hybrid as hybrid  # noqa: E402
from scripts import science_axes_gate as gate  # noqa: E402

ROUNDS = ("2026-round-3", "2026-round-3-dev2", "2026-round-1-dev2")  # N1 devcheck와 같은 순서
LABELS = ROOT / "data/dev_labels/labels/claude-dev-all.jsonl"
AI_DIR, RULE_DIR = ROOT / "data/derived/axes_ai", ROOT / "data/derived/axes"
PUBLIC_HYBRID = ROOT / "data/derived/axes_hybrid"
OUT = ROOT / "data/derived/axes_gating"
RESULTS = HERE / "m2-f1.json"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def gated(ai: dict, rule: dict) -> tuple[dict, dict]:
    rules = {item["item_id"]: item for item in rule["items"]}
    skip = [i["item_id"] for i in ai["items"]
            if i["item_id"] in rules and gate.should_skip(rules[i["item_id"]]["activity"])]
    changed = sum(i["activity"].get("primary") not in
                  (None, rules[i["item_id"]]["activity"]["primary"])
                  for i in ai["items"] if i["item_id"] in skip)
    kept = [i for i in ai["items"] if i["item_id"] not in skip]
    return {**ai, "items": kept, "rule_skipped": skip}, {"skipped": len(skip),
                                                         "ai_primary_differs": changed}


def build() -> dict:
    counts = {}
    for round_key in ROUNDS:
        ai, rule = read(AI_DIR / f"{round_key}.json"), read(RULE_DIR / f"{round_key}.json")
        ai_on, counts[round_key] = gated(ai, rule)
        for name, doc in (("off", hybrid.combine(ai, rule)), ("on", hybrid.combine(ai_on, rule))):
            path = OUT / f"m2-hybrid-{name}/{round_key}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return counts


def measure(directory: Path) -> dict:
    """N1 devcheck.sh의 활동 지표 계산과 같은 식."""
    axes = score.load_axes([directory / f"{r}.json" for r in ROUNDS])
    labels = score.read_labels(LABELS)
    report = score.evaluate(axes, labels)
    rows = [score.make_row(label, axes.get(label["item_id"]))
            for label in score.unique_index(labels).values()]
    all_rows = [dict(r, predicted_primary=r["predicted_primary"] if r["result"] != "짝 없음"
                     else None) for r in rows]
    m = report["metrics"]
    paired = m["macro_f1_all"]
    return {"labels": report["label_count"], "paired": m["paired"],
            "macro_f1_paired": paired.get("value", paired) if isinstance(paired, dict) else paired,
            "macro_f1_all_labels": score.macro_f1(score.per_activity_metrics(all_rows), 1),
            "primary_accuracy_all": m["primary_accuracy_all"],
            "classifier_abstain": m["classifier_abstain_rate"]}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    counts = build()
    result = {"gate_skipped_by_round": counts,
              "public_hybrid_now": measure(PUBLIC_HYBRID),
              "off": measure(OUT / "m2-hybrid-off"),
              "on": measure(OUT / "m2-hybrid-on")}
    RESULTS.write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str) + "\n",
                       encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
