"""묶음 하나(묶음 3 실측 기준)의 단계별 토큰 총량과 M2·M3 적용 뒤 감소 %를 계산한다(M3).

무엇: prompt-diet-usage.json(단계·묶음별 호출당 usage 평균)과 m3-f1-<판>.json(같은 카드 266장의
      full·줄인 판 호출당 usage)을 읽어, 묶음 3의 호출 수(아래 상수, 출처는
      2026-11-11-prompt-diet.md 1절)에 곱한다.
      - cc-run은 묶음 3이 아직 안 돌아 묶음 2의 '카드당 cc 호출 비'(600/1331)와 호출당 평균을 쓴다.
      - M2: ax-run 새 호출 12% 감소(2026-11-11-m2-distill.md, 전국 카드 12.0%).
      - M3: ax-run 호출당 토큰을 full→줄인 판 비율(같은 카드 짝, run1·run2 평균)로 줄인다.
        두 판 모두 품질 기준 미달로 실행 코드에 적용하지 않았다(적용했다면의 추정).
      토큰은 '입력 전체(캐시 포함)+출력'과 '캐시 안 된 입력+출력' 두 가지로 낸다.
Run:    .venv/Scripts/python.exe docs/axes-gating/m3_effect.py
Verify: 두 번 돌려 m3-effect.json sha256이 같은지 본다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
USAGE = json.loads((HERE / "prompt-diet-usage.json").read_text(encoding="utf-8"))["by_stage_bundle"]
RESULTS = HERE / "m3-effect.json"
VARIANTS = ("lean", "compact")
AX_CARDS_BUNDLE3 = 6915          # 묶음 3 ax-run 대상 카드(M2 기록 기준 1)
FIRST_CALLS, FIELDS_CALLS = 2834, 703  # 묶음 3 status called(두 회차 합)
M2_AX_CUT = 0.12                 # M2 게이트가 새 ax-run 호출에서 빼는 몫
STAGE_KEYS = {"first-run": "first-run|nw3", "fields-run": "fields-run|nw3",
              "ax-run": "ax-run|nw3", "cc-run": "cc-run|nw2"}


def per_call(key: str) -> dict:
    m = USAGE[key]["mean"]
    return {"all": m["input_tokens"] + m["output_tokens"],
            "uncached": m["input_tokens"] - m["cached_input_tokens"] + m["output_tokens"]}


def ratio(variant: str) -> dict:
    """줄인 판 ÷ full, 같은 카드 짝의 호출당 평균(run1·run2 평균)."""
    runs = json.loads((HERE / f"m3-f1-{variant}.json").read_text(encoding="utf-8"))
    out = {"all": [], "uncached": []}
    for run in ("run1", "run2"):
        mean = runs[run]["tokens"]["mean"]
        for metric, field in (("all", "input_tokens"), ("uncached", "uncached_input")):
            full = mean["full"][field] + mean["full"]["output_tokens"]
            small = mean["compact"][field] + mean["compact"]["output_tokens"]
            out[metric].append(small / full)
    return {metric: round(sum(v) / len(v), 4) for metric, v in out.items()}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cc_calls = round(AX_CARDS_BUNDLE3 * USAGE["cc-run|nw2"]["calls"] / USAGE["ax-run|nw2"]["calls"])
    calls = {"first-run": FIRST_CALLS, "fields-run": FIELDS_CALLS, "ax-run": AX_CARDS_BUNDLE3,
             "cc-run": cc_calls}
    ratios = {variant: ratio(variant) for variant in VARIANTS}
    result = {"calls_bundle": calls, "ax_per_call_ratio": ratios, "metrics": {}}
    for metric in ("all", "uncached"):
        base = {s: calls[s] * per_call(STAGE_KEYS[s])[metric] for s in calls}
        m2 = {**base, "ax-run": base["ax-run"] * (1 - M2_AX_CUT)}
        before, after_m2 = sum(base.values()), sum(m2.values())
        entry = {"stage_tokens_before_millions": {s: round(v / 1e6, 1) for s, v in base.items()},
                 "stage_share_before": {s: round(v / before, 3) for s, v in base.items()},
                 "total_before_millions": round(before / 1e6, 1),
                 "cut_m2": round(1 - after_m2 / before, 3)}
        for variant in VARIANTS:
            m3 = {**m2, "ax-run": m2["ax-run"] * ratios[variant][metric]}
            entry[variant] = {"total_millions": round(sum(m3.values()) / 1e6, 1),
                              "cut_m2_plus_m3": round(1 - sum(m3.values()) / before, 3),
                              "cut_m3_vs_m2": round(1 - sum(m3.values()) / after_m2, 3)}
        result["metrics"][metric] = entry
    RESULTS.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
