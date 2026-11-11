"""활동 축 AI 생략 게이트: 규칙 축 결과가 AI 판정과 거의 같을 카드를 고른다(M2 증류, 2026-11-11).

조건: 규칙 주활동이 있고, E층(제목·평가영역·평가요소·과제 설명) 투표에서
      (주활동 표 - 다른 활동 최다 표) >= 3, 또는 그 표 차이 >= 2 이면서 규칙 보조활동이 없다.
근거: 이미 받은 AI 판정 3,189장, 학교 단위 학습/평가 나누기에서 평가 쪽 일치 0.9935(하한 0.964),
      덮는 비율 약 16%. docs/axes-gating/2026-11-11-m2-distill.md, docs/axes-gating/distill.py.
쓰는 곳: science_axes_ai.build_targets(--skip-rule-confident), docs/axes-gating/distill.py.
Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_science_axes_gate.py
"""

from __future__ import annotations

SKIP_MARGIN = 3                # 표 차이가 이만큼이면 보조활동과 무관하게 생략
SKIP_MARGIN_NO_SECONDARY = 2   # 보조활동이 없으면 이 표 차이부터 생략


def e_margin(activity: dict) -> int | None:
    """E층 투표에서 주활동 표 - 다른 활동 최다 표. 주활동이나 투표가 없으면 None."""
    primary = activity.get("primary")
    votes = activity.get("votes_e") or {}
    if primary is None or not votes:
        return None
    others = [count for name, count in votes.items() if name != primary]
    return votes.get(primary, 0) - (max(others) if others else 0)


def should_skip(activity: dict) -> bool:
    """규칙 activity만 보고 AI 판정을 건너뛸지 정한다."""
    margin = e_margin(activity)
    if margin is None:
        return False
    if margin >= SKIP_MARGIN:
        return True
    return margin >= SKIP_MARGIN_NO_SECONDARY and not activity.get("secondary")
