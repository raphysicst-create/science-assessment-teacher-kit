"""Replay stored T1 evidence and checkbox mutations for method value rules.

Run .venv/Scripts/python.exe -m pytest -q
services/math-assessment-api/tests/test_s18_method_value.py.
"""

import copy
import importlib
import json
import sys
from pathlib import Path

import pytest
from scripts.middle_ai_fields import value_from_cells
from scripts.middle_identity import merge_method
from scripts.middle_items import METHOD_BOX_RE, method_values, scorer_text, visible

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

normalize = importlib.import_module("gold_diff").normalize

CASES = [case for case in json.loads(
    (ROOT / "docs/dev-cases/2026-11-10-extraction-types.json").read_text(encoding="utf-8")
)["cases"] if case["type"] == "T1"]


def observations(evidence):
    return [{**copy.deepcopy(obs), "text": visible(obs["raw"])} for obs in evidence]


def value_keys(values):
    return {normalize(value) for value in values}


def replay(case):
    target = method_values(observations(case["input"]["method_evidence"]))
    target["status"] = "present" if target["value"] else "unconfirmed"
    for summary in case["input"]["summary_observations"]:
        source = method_values(observations(summary["evidence"]))
        merge_method(source, target, "summary")
    return target


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_stored_t1_method_values(case):
    # Stored S18 expectations predate S19's observation/recording exclusion.
    expected = [value for value in case["expected"] if value != "관찰⋅기록"]
    assert value_keys(replay(case)["value"]) == value_keys(expected)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_ai_fields_share_method_values(case):
    source = observations(case["input"]["method_evidence"])
    assert value_from_cells("method", source, [], {}) == method_values(source)["value"]


def uncheck(evidence, options):
    """Replace selected source markers, leaving stored locators untouched."""
    mutated = copy.deepcopy(evidence)
    for obs in mutated:
        replacements = []
        for option in options:
            start = option["locator"]["start"] - obs["locator"]["start"]
            end = option["locator"]["end"] - obs["locator"]["start"]
            if 0 <= start < end <= len(obs["raw"]):
                marker = METHOD_BOX_RE.search(obs["raw"], start, end)
                assert marker is not None
                replacements.append((marker.start(), marker.end()))
        for start, end in sorted(replacements, reverse=True):
            obs["raw"] = obs["raw"][:start] + "□" + obs["raw"][end:]
    return mutated


def test_unchecking_scorers_keeps_method_values():
    changed = 0
    for case in CASES:
        evidence = case["input"]["method_evidence"]
        original = method_values(observations(evidence))
        scorers = [option for option in original["options"]
                   if option["state"] == "checked"
                   and scorer_text(option["option_text"], option["kind"])]
        if not scorers:
            continue
        mutated = method_values(observations(uncheck(evidence, scorers)))
        assert mutated["value"] == original["value"], case["case_id"]
        assert mutated["scorer_values"] == []
        changed += 1
    assert changed > 0


def test_unchecking_one_method_removes_its_values():
    changed = 0
    for case in CASES:
        evidence = case["input"]["method_evidence"]
        original = method_values(observations(evidence))
        methods = [option for option in original["options"]
                   if option["state"] == "checked" and option["option_text"]
                   and not scorer_text(option["option_text"], option["kind"])]
        if not methods:
            continue
        removed = methods[0]
        removed_values = method_values(observations([{
            "raw": removed["raw"], "locator": removed["locator"],
            "method_kind": removed["kind"],
        }]))["value"]
        retained_values = method_values(observations([
            {"raw": option["raw"], "locator": option["locator"],
             "method_kind": option["kind"]} for option in methods[1:]
        ]))["value"]
        mutated = method_values(observations(uncheck(evidence, [removed])))
        assert value_keys(mutated["value"]) == value_keys(retained_values), case["case_id"]
        assert not (value_keys(removed_values) - value_keys(retained_values)) & value_keys(
            mutated["value"]
        )
        changed += 1
    assert changed > 0
