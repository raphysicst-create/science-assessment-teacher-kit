"""AI 기권 항목만 규칙 활동으로 채우는지 확인한다.

Verify: .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_science_axes_hybrid.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import science_axes_hybrid as hybrid  # noqa: E402


def axes(*pairs):
    return {"rule_version": "x", "items": [
        {"item_id": i, "activity": {"primary": p, "rule_applied": "r"}} for i, p in pairs]}


def test_only_ai_abstentions_take_rule_activity():
    ai = axes(("a", "탐구"), ("b", None), ("c", None))
    rule = axes(("a", "작성"), ("b", "실험평가"), ("c", None))
    result = hybrid.combine(ai, rule)
    primaries = {i["item_id"]: i["activity"]["primary"] for i in result["items"]}
    assert primaries == {"a": "탐구", "b": "실험평가", "c": None}
    assert result["summary"]["rule_fallback_filled"] == 1
    assert result["rule_version"] == hybrid.VERSION


def test_rule_skipped_cards_stay_with_rule_activity_and_mark():
    ai = {**axes(("a", "탐구")), "rule_skipped": ["b"]}
    rule = axes(("a", "작성"), ("b", "실험평가"), ("c", "분석"))
    result = hybrid.combine(ai, rule)
    by_id = {i["item_id"]: i["activity"] for i in result["items"]}
    assert set(by_id) == {"a", "b"}
    assert by_id["b"] == {"primary": "실험평가", "rule_applied": hybrid.SKIPPED_LABEL}
    assert result["summary"]["rule_skipped_filled"] == 1


def test_files_without_rule_skipped_are_unchanged():
    ai = axes(("a", "탐구"))
    result = hybrid.combine(ai, axes(("a", "작성"), ("b", "분석")))
    assert [i["item_id"] for i in result["items"]] == ["a"]
    assert result["summary"]["rule_skipped_filled"] == 0
