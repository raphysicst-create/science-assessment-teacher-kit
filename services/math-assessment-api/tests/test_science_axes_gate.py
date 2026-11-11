"""규칙 activity만 보고 AI 활동 판정을 건너뛸지 정하는 게이트(science_axes_gate) 경계값.

Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_science_axes_gate.py
"""

from scripts import science_axes_gate as gate


def act(primary, votes, secondary=()):
    return {"primary": primary, "votes_e": votes, "secondary": list(secondary)}


def test_margin_three_skips_even_with_secondary():
    assert gate.should_skip(act("탐구", {"탐구": 4, "분석": 1}, ["분석"]))


def test_margin_two_skips_only_without_secondary():
    assert gate.should_skip(act("탐구", {"탐구": 3, "분석": 1}))
    assert not gate.should_skip(act("탐구", {"탐구": 3, "분석": 1}, ["분석"]))


def test_small_margin_missing_primary_or_votes_never_skip():
    assert not gate.should_skip(act("탐구", {"탐구": 2, "분석": 1}))
    assert not gate.should_skip(act(None, {"탐구": 5}))
    assert not gate.should_skip(act("탐구", {}))
    assert gate.e_margin(act("탐구", {"탐구": 3})) == 3
