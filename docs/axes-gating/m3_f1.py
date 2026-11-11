"""줄인 정의(compact·lean) 활동 AI의 개발 F1(255짝, 공개판 입력)과 호출당 토큰을 full과 잰다(M3).

무엇: 개발 F1 회차 3개를 같은 DB·문맥으로 줄인 지시문(판 VARIANT)으로 2회 부른 실행 폴더
      (data/derived/m3_<VARIANT>_run1, run2; 만든 명령은 2026-11-11-prompt-diet.md 2절)를
      science_axes_ai export → science_axes_hybrid → N1 devcheck와 같은 채점
      (docs/axes-gating/m2_f1_onoff.measure)으로 잰다. 지금 공개판 혼합 축(full 지시문)도 같이 잰다.
      토큰은 같은 카드 266장의 full 응답(data/derived/axes_ai_run, 목표 id는
      data/derived/m3_check_full)과
      줄인 판 응답의 마지막 turn.completed usage를 짝지어 평균한다(키 이름은 compact).
Run:    .venv/Scripts/python.exe docs/axes-gating/m3_f1.py compact|lean
Verify: 두 번 돌려 m3-f1-<VARIANT>.json sha256이 같은지 본다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import m2_f1_onoff as m2  # noqa: E402
import prompt_diet_usage as usage  # noqa: E402

PY = str(ROOT / ".venv/Scripts/python.exe")
DATABASE = "data/publish/science/math_assessment_catalog_detail.sqlite"
RUNS = ("run1", "run2")
FULL_TARGETS = ROOT / "data/derived/m3_check_full/targets.jsonl"
FULL_RESPONSES = ROOT / "data/derived/axes_ai_run/responses"
BAR_ABS, BAR_DROP, BASELINE = 0.905, 0.005, 0.9115  # 브리프 완료 기준 2
# compact(라운드 1, 기준 미달)는 실행 코드에서 뺐다.
# 그 판은 저장된 export·hybrid 결과만 다시 채점한다.
SAVED_ONLY = ("compact",)


def cli(*args: str) -> dict:
    done = subprocess.run([PY, *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", check=True)
    return json.loads(done.stdout.strip().splitlines()[-1]) if done.stdout.strip() else {}


def score_run(variant: str, name: str) -> dict:
    run = f"data/derived/m3_{variant}_{name}"
    axes = f"data/derived/m3_{variant}_axes_{name}"
    mixed = f"data/derived/m3_{variant}_hybrid_{name}"
    if variant in SAVED_ONLY:  # 라운드 1 코드가 만든 export·hybrid 파일을 그대로 채점한다
        verified = json.loads((ROOT / run / "verified.json").read_text(encoding="utf-8"))["summary"]
        return {"export": {"saved_round1_outputs": True}, "verified": verified,
                "f1": m2.measure(ROOT / mixed)}
    exported = cli("scripts/science_axes_ai.py", "export", "--database", DATABASE,
                   "--out-dir", run, "--axes-out", axes)
    cli("scripts/science_axes_hybrid.py", "--rounds", *m2.ROUNDS, "--ai-dir", axes,
        "--out-dir", mixed)
    verified = json.loads((ROOT / run / "verified.json").read_text(encoding="utf-8"))["summary"]
    return {"export": exported, "verified": verified, "f1": m2.measure(ROOT / mixed)}


def token_pairs(variant: str, name: str) -> dict:
    """같은 카드의 full 응답과 compact 응답 usage(카드 id로 짝짓기)."""
    full = {json.loads(line)["card_ids"][0]: json.loads(line)["target_id"]
            for line in FULL_TARGETS.read_text(encoding="utf-8").splitlines() if line}
    run = ROOT / f"data/derived/m3_{variant}_{name}"
    rows = {"full": [], "compact": []}
    for line in (run / "targets.jsonl").read_text(encoding="utf-8").splitlines():
        target = json.loads(line)
        sides = (("full", FULL_RESPONSES.parent, full[target["card_ids"][0]]),
                 ("compact", run, target["target_id"]))
        if not all((d / f"responses/{i}.events.jsonl").exists() for _, d, i in sides):
            continue
        for side, run_dir, identity in sides:
            rows[side].append({**usage.last_usage(run_dir / f"responses/{identity}.events.jsonl"),
                               "prompt_bytes": (run_dir / f"prompts/{identity}.md").stat().st_size})
    keys = (*usage.USAGE_KEYS, "prompt_bytes")
    mean = {side: {k: round(sum(r[k] for r in v) / len(v), 1) for k in keys}
            for side, v in rows.items()}
    for side in mean:
        mean[side]["uncached_input"] = round(
            mean[side]["input_tokens"] - mean[side]["cached_input_tokens"], 1)
    return {"pairs": len(rows["full"]), "mean": mean}


def full_abstained() -> int:
    """같은 266장의 full 저장 응답을 verify와 같은 함수로 검증했을 때 기권 수."""
    from scripts import middle_ai_read as ai
    from scripts import science_axes_ai as axes
    names = axes.definition_sections("full")[1]
    count = 0
    for line in FULL_TARGETS.read_text(encoding="utf-8").splitlines():
        target = json.loads(line)
        response = ai.parse_response(FULL_RESPONSES / f"{target['target_id']}.json")
        verdict = axes.verify_group(target["cards"], response, target["target_id"], names)[0]
        count += verdict["primary"] is None
    return count


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    variant = sys.argv[1]
    if variant not in ("compact", "lean"):
        raise SystemExit("판은 compact 또는 lean")
    result = {"variant": variant, "public_hybrid_full_now": m2.measure(m2.PUBLIC_HYBRID),
              "full_same_cards_ai_abstained": full_abstained()}
    for name in RUNS:
        result[name] = {**score_run(variant, name), "tokens": token_pairs(variant, name)}
        f1 = result[name]["f1"]["macro_f1_paired"]["rate"]
        result[name]["passes"] = f1 >= BAR_ABS and BASELINE - f1 <= BAR_DROP
    result["all_pass"] = all(result[name]["passes"] for name in RUNS)
    text = json.dumps(result, ensure_ascii=False, indent=1, default=str) + "\n"
    (HERE / f"m3-f1-{variant}.json").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
