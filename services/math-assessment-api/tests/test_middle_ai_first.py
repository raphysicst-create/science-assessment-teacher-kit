"""Synthetic AI-first pipeline checks; no AI process, network or gold fixtures.

Run: .venv/Scripts/python.exe -m pytest -q
     services/math-assessment-api/tests/test_middle_ai_first.py
"""

import copy
import json
from pathlib import Path

import pytest
from middle_ai_first_detail_cases import (
    test_bad_detail_is_dropped_without_discarding_task,
    test_deduplicate_unions_detail_and_methods,
    test_detail_accepts_other_occurrence_with_same_title_key,
    test_detail_can_link_by_declared_evidence_line_range,
    test_detail_can_link_by_title_text_without_overlapping_evidence,
    test_detail_neighbor_check_requires_same_document_and_scope,
    test_detail_rejects_neighbor_title_and_accepts_erased_mutation,
    test_detail_standards_expand_validate_locate_and_repeat,
    test_detail_validation_runs_after_duplicate_ranges_are_unioned,
    test_methods_command_fills_standards_preserves_existing_values_and_repeats,
    test_methods_inside_evidence_without_detail,
    test_methods_literal_scope_scorers_and_check_state,
    test_verify_fail_closed_and_detail_locator,
)
from middle_ai_first_fixtures import (
    PROJECT,
    ROUND,
    TEXT,
    fake_responses,
    install_documents,
    pipeline,
    rule_item,
    task,
)
from middle_ai_first_fixtures import offline as offline
from middle_ai_first_fixtures import root as root
from scripts import middle_ai_first as first
from scripts import middle_ai_first_merge as merge
from scripts import middle_ai_read as ai
from scripts.middle_ai_fields import is_ai, item_slices

# Re-export split cases so the focused test command still collects every case.
__all__ = [
    'test_verify_fail_closed_and_detail_locator',
    'test_bad_detail_is_dropped_without_discarding_task',
    'test_detail_can_link_by_title_text_without_overlapping_evidence',
    'test_detail_can_link_by_declared_evidence_line_range',
    'test_methods_literal_scope_scorers_and_check_state',
    'test_methods_inside_evidence_without_detail',
    'test_deduplicate_unions_detail_and_methods',
    'test_detail_rejects_neighbor_title_and_accepts_erased_mutation',
    'test_detail_validation_runs_after_duplicate_ranges_are_unioned',
    'test_detail_accepts_other_occurrence_with_same_title_key',
    'test_detail_neighbor_check_requires_same_document_and_scope',
    'test_detail_standards_expand_validate_locate_and_repeat',
    'test_methods_command_fills_standards_preserves_existing_values_and_repeats',
]


def test_filename_without_science_signal_and_other_subject_exclusion(root):
    text = "1학년 1학기\n관찰 보고서\n"
    install_documents(root, [("science", "과학 (수학 수정) 평가계획.hwp", text),
                             ("math", "수학 평가계획.hwp", text),
                             ("unknown", "평가계획.hwp", text),
                             ("empty", "과학 평가계획.hwp", "")])
    summary = first.build_targets(root, ROUND)
    targets = ai.load_targets(ai.round_dir(root, ROUND) / "first")
    assert summary["documents"] == summary["chunks"] == 1
    assert summary["selection_modes"] == {"f_filename": 1}
    assert {d["document_id"] for d in summary["excluded"]} == {"math", "unknown", "empty"}
    assert targets[0]["line_start"] == 1 and targets[0]["line_end"] == 2
    assert targets[0]["char_count"] == len(text)
    assert targets[0]["target_id"] == first.digest_id(
        "aif_", first.VERSION, ROUND, "science", 1, 2, ai.sha(text))


def test_filename_overrides_b_marker_window(root):
    text = "과학\n" + "본문\n" * 160 + "마지막 과제\n"
    assert ai.target_windows(text, "과학 평가계획.hwp", [])[0] == "b_marker"
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    first.build_targets(root, ROUND)
    target = ai.load_targets(ai.round_dir(root, ROUND) / "first")[0]
    assert target["mode"] == "f_filename"
    assert target["line_end"] == 162


@pytest.mark.parametrize("mode", ["a_full", "a_context", "b_marker", "plaintext_fallback"])
def test_remaining_window_modes(root, mode, monkeypatch):
    install_documents(root, [("science", "전과목 평가계획.hwp", TEXT)])
    monkeypatch.setattr(ai, "target_windows", lambda *a: (
        (mode, [(1, 7)], "") if mode != "plaintext_fallback" else ("excluded", [], "없음")))
    monkeypatch.setattr(ai, "plaintext_fallback_window", lambda *a: [
        {"line_start": 1, "line_end": 7}])
    assert first.build_targets(root, ROUND)["selection_modes"] == {mode: 1}


def test_skip_nonplan_and_grade_three(root):
    docs = install_documents(root, [("science", "과학 평가계획.hwp", TEXT),
                                    ("notice", "과학 공고.hwp", TEXT)])
    docs[0]["grades"], docs[0]["segments"] = [3], [{"grade": 3}]
    docs[1]["document_kind"] = "notice"
    ai.save_json(root / f"data/derived/segments/{ROUND}.json", {"documents": docs})
    summary = first.build_targets(root, ROUND)
    assert summary["chunks"] == 0 and len(summary["excluded"]) == 2


def test_chunking_limits_overlap_and_original_line_numbers(root):
    text = "1학년 1학기\n" + ("가" * 999 + "\n") * 125
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    summary = first.build_targets(root, ROUND)
    output = ai.round_dir(root, ROUND) / "first"
    targets = ai.load_targets(output)
    assert summary["chunks"] == 3
    assert all(t["char_count"] <= 60_000 for t in targets)
    assert all(a["end"] - b["start"] >= 3_000
               for a, b in zip(targets, targets[1:], strict=False))
    last = targets[-1]
    prompt = ai.read_text(output / f"prompts/{last['target_id']}.md")
    assert f"{last['line_start']}\t" in prompt
    assert ai.sha(prompt) == last["prompt_sha256"]


def test_scope_three_is_separated_and_invalid_run_discarded(root):
    text = TEXT.replace("1학년", "3학년")
    install_documents(root, [("science", "과학 평가계획.hwp", text)])
    output, report = pipeline(root, [task(grade=3, grade_evidence={"line": 1, "quote": "3학년"})])
    assert not report["kept"] and len(report["out_of_scope"]) == 1
    target = ai.load_targets(output)[0]
    ai.write_text(output / f"responses/{target['target_id']}.events.jsonl", "")
    assert first.verify_targets(root, ROUND)["summary"]["discarded"] == 1


def test_conversion_hash_change_fails_closed(root):
    output, _ = pipeline(root, [task()])
    target = ai.load_targets(output)[0]
    ai.save_json(root / target["converted_path"], {"text": "변경됨"})
    with pytest.raises(ValueError, match="해시"):
        first.verify_targets(root, ROUND)


@pytest.mark.parametrize("case, expected, added", [
    ("title", "agrees_by_title", 0), ("one_bounded", "agrees", 0),
    ("two_bounded", "conflict", 0), ("two_unbounded", "replaces_unbounded", 1),
    ("conversion_loss", "agrees", 0), ("overview_rule", "overview_only_held", 0),
    ("overview_ai", "overview_only_held", 1), ("new", "new", 1),
])
def test_merge_five_rules(root, case, expected, added):
    _, verified = pipeline(root, [task()])
    candidate = verified["kept"][0]
    far = {**candidate["locator"], "start": 1000, "end": 2000}
    rules = []
    if case == "title":
        rules = [rule_item(candidate, title="온도관찰보고서!", locator=far)]
        rules[0]["document_id"] = "same-school-other-document"
    elif case in {"one_bounded", "two_bounded"}:
        rules = [rule_item(candidate)]
        if case == "two_bounded":
            rules.append(rule_item(candidate, "rule-2"))
    elif case in {"two_unbounded", "conversion_loss"}:
        rules = [rule_item(candidate, "rule-1", "review"),
                 rule_item(candidate, "rule-2", "review")]
        if case == "conversion_loss":
            rules[1]["review_reasons"] = ["변환 손실 확인 필요"]
    elif case.startswith("overview_"):
        candidate["seen_in"] = "overview"
        if case == "overview_rule":
            rules = [rule_item(candidate, locator=far)]
        else:
            other = copy.deepcopy(candidate)
            other.update(ai_task_id="detail-peer", seen_in="detail", locator=far)
            other["title"] = "다른 세부 과제"
            verified["kept"].append(other)
    source = {"round": ROUND, "items": rules}
    before = copy.deepcopy(source)
    result = first.merge_report(source, verified)
    assert source == before and result["items"][:len(rules)] == rules
    assert result["ai_read_summary"]["added_items"] == added
    assert result["ai_relations"][expected]
    if case == "two_unbounded":
        assert result["ai_relations"][expected][0]["rule_item_ids"] == ["rule-1", "rule-2"]
        assert is_ai(result["items"][-1])
        assert result["items"][-1]["rule_version"] == first.VERSION
        assert result["ai_first_matches"][candidate["ai_task_id"]] == candidate["ai_task_id"]


def test_merge_uses_all_anchors_and_one_bounded_wins_over_unbounded(root):
    _, verified = pipeline(root, [task()])
    candidate = verified["kept"][0]
    rules = [rule_item(candidate, "bounded", locator=candidate["title_locator"]),
             rule_item(candidate, "review", "review")]
    result = first.merge_report({"items": rules}, verified)
    assert result["ai_relations"]["agrees"][0]["rule_item_ids"] == ["bounded"]
    assert result["ai_read_summary"]["added_items"] == 0


@pytest.mark.parametrize("field, value", [("document_id", "other"), ("child_id", "other"),
                                        ("grade", 2), ("semester", 2)])
def test_merge_overlap_requires_document_child_grade_semester(root, field, value):
    _, verified = pipeline(root, [task()])
    rule = rule_item(verified["kept"][0])
    rule[field] = value
    result = first.merge_report({"items": [rule]}, verified)
    assert result["ai_read_summary"]["added_items"] == 1


def test_merge_accepts_wildcard_scope_and_holds_only_same_document(root):
    _, verified = pipeline(root, [task()])
    candidate = verified["kept"][0]
    rule = rule_item(candidate)
    rule.update(grade=None, semester=None)
    assert first.merge_report({"items": [rule]}, verified)["ai_relations"]["agrees"]
    candidate["seen_in"] = "overview"
    rule["document_id"] = "another-document"
    assert first.merge_report({"items": [rule]}, verified)["ai_read_summary"]["added_items"] == 1


def test_merge_file_preserves_rule_bytes_and_fields_compatibility(root):
    _, verified = pipeline(root, [task()])
    rule = rule_item(verified["kept"][0], status="review")
    raw = '{"round":"' + ROUND + '","items": [\n' + json.dumps(rule, ensure_ascii=True) + '\n]}'
    ai.write_text(root / f"data/derived/items/{ROUND}.json", raw)
    result = first.merge_targets(root, ROUND)
    merged = ai.read_text(root / f"data/derived/items_ai/{ROUND}.json")
    assert [raw[s:e] for _, s, e in item_slices(raw)] == [
        merged[s:e] for _, s, e in item_slices(merged)][:1]
    assert is_ai(result["items"][-1]) and result["ai_read_summary"]["simulated"]


@pytest.mark.parametrize("change", ["targets", "prompt", "answer", "events", "binding"])
def test_merge_rejects_changed_bindings(root, change):
    output, _ = pipeline(root, [task()])
    target = ai.load_targets(output)[0]
    identity = target["target_id"]
    paths = {"targets": output / "targets.jsonl", "prompt": output / f"prompts/{identity}.md",
             "answer": output / f"responses/{identity}.json",
             "events": output / f"responses/{identity}.events.jsonl"}
    if change == "binding":
        path = output / f"responses/{identity}.status.json"
        status = ai.read_json(path)
        status["fake"] = False
        ai.save_json(path, status)
    else:
        ai.write_text(paths[change], ai.read_text(paths[change]) + "\n")
    with pytest.raises(ValueError):
        first.merge_targets(root, ROUND)


def test_methods_fill_only_empty_no_options_preserves_other_fields_and_idempotent(root):
    _, verified = pipeline(root, [task()])
    first.merge_targets(root, ROUND)
    path = root / f"data/derived/items_ai/{ROUND}.json"
    report = ai.read_json(path)
    base = report["items"][0]
    variants = [base]
    for identity, field in [("present", {"value": ["보고서"]}),
                            ("unchecked", {"value": [], "options": [{"state": "unchecked"}]}),
                            ("unknown", {"value": [], "state": "unknown"}),
                            ("loss", {"value": [], "state": "conversion_loss"})]:
        item = copy.deepcopy(base)
        item["item_id"], item["fields"]["method"] = identity, field
        variants.append(item)
    report["items"] = variants
    report["ai_first_matches"][verified["kept"][0]["ai_task_id"]] = [i["item_id"] for i in variants]
    ai.save_json(path, report)
    before = copy.deepcopy(report)
    assert first.fill_methods(root, ROUND)["changed_items"] == 1
    after = ai.read_json(path)
    method = after["items"][0]["fields"]["method"]
    assert method["value"] == ["실험"] and method["status"] == "present"
    assert method["state"] == "ai_first_literal" and method["fill_method"] == "ai_first"
    assert method["evidence"][0]["locator"] == verified["kept"][0]["methods_verified"][0]["locator"]
    after["items"][0]["fields"]["method"] = before["items"][0]["fields"]["method"]
    assert after == before
    raw = ai.read_text(path)
    assert first.fill_methods(root, ROUND)["changed_items"] == 0
    assert ai.read_text(path) == raw


def test_methods_rejects_verified_changed_since_merge(root):
    output, _ = pipeline(root, [task()])
    first.merge_targets(root, ROUND)
    verified = ai.read_json(output / "verified.json")
    verified["kept"][0]["methods_verified"] = []
    ai.save_json(output / "verified.json", verified)
    with pytest.raises(ValueError, match="verified"):
        first.fill_methods(root, ROUND)


def test_run_retries_once_same_arguments_and_skips_valid(root, monkeypatch):
    install_documents(root, [("science", "과학 평가계획.hwp", TEXT),
                             ("science2", "과학 평가계획.hwp", TEXT)])
    first.build_targets(root, ROUND)
    output = ai.round_dir(root, ROUND) / "first"
    targets = ai.load_targets(output)
    fake = fake_responses(root, targets[:1])
    real_run, calls = ai.run_targets, []

    def run(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 2:
            fake_responses(root, targets[1:])
        report = real_run(*args, **kwargs)
        for result in report["results"]:
            if "elapsed_seconds" in result:
                result["elapsed_seconds"] = len(calls)
        report["mean_elapsed_seconds"] = len(calls)
        return report

    monkeypatch.setattr(ai, "run_targets", run)
    report = first.run_targets(root, ROUND, root, fake_responses=fake, model="synthetic-model")
    assert calls[0] == calls[1] and calls[0][1]["workers"] == 6
    assert report["first_pass"]["called"] == 2 and report["first_pass"]["valid"] == 1
    assert report["retry_pass"]["called"] == 1 and report["retry_pass"]["valid"] == 2
    assert report["elapsed_seconds"] == 4
    assert report["first_pass"]["mean_elapsed_seconds"] == 1
    assert report["retry_pass"]["mean_elapsed_seconds"] == 2
    assert report["valid"] == report["total"] == 2 and not report["all_failed"]
    assert ai.read_json(output / "run_summary.json") == report
    assert first.run_targets(root, ROUND, root, fake_responses=fake,
                             model="synthetic-model")["called"] == 0


def test_run_never_retries_more_than_once_and_cli_all_failed(root, monkeypatch, capsys):
    first.build_targets(root, ROUND)
    monkeypatch.setattr(first, "ROOT", root)
    with pytest.raises(SystemExit) as error:
        first.main(["run", "--round-key", ROUND, "--isolated-cwd", str(root),
                    "--fake-responses", str(root / "missing")])
    assert error.value.code == 3
    report = json.loads(capsys.readouterr().out)
    assert report["called"] == 2 and report["all_failed"]


@pytest.mark.parametrize("workers", [0, 9])
def test_run_rejects_workers_outside_one_to_eight(root, workers):
    with pytest.raises(ValueError, match="workers"):
        first.run_targets(root, ROUND, root, workers=workers)


def test_dry_run_and_no_targets_do_not_retry_or_fail(root, monkeypatch):
    first.build_targets(root, ROUND)
    monkeypatch.setattr(ai, "codex_command", lambda *a, **k: ["fake-codex", "exec"])
    report = first.run_targets(root, ROUND, root, dry_run=True)
    assert report["retry_pass"] is None and not report["all_failed"]
    output = ai.round_dir(root, ROUND) / "first"
    ai.write_text(output / "targets.jsonl", "")
    report = first.run_targets(root, ROUND, root, fake_responses=root / "missing")
    assert report["total"] == 0 and not report["all_failed"]


@pytest.mark.parametrize("command", ["targets", "run", "verify", "merge", "methods"])
def test_gold_round_locked(root, command):
    arguments = [command, "--round-key", "syntheticgold"]
    if command == "run":
        arguments.extend(["--isolated-cwd", str(root), "--fake-responses", str(root / "fake")])
    with pytest.raises(ValueError, match="회차"):
        first.main(arguments)


def test_prompt_keeps_v2_task_unit_and_exclusion_sentences():
    v2 = ai.read_text(PROJECT / "scripts/prompts/middle_ai_read_v2.md")
    prompt = ai.read_text(PROJECT / "scripts/prompts/middle_ai_first_v1.md")
    start, end = v2.index("- 정기시험"), v2.index("- 제목은")
    assert v2[start:end].replace("\r\n", "\n") in prompt
    example = next(line for line in prompt.splitlines() if line.startswith('{"tasks":'))
    assert {"detail_lines", "methods"} <= json.loads(example)["tasks"][0].keys()


def test_source_size_and_function_limits():
    import ast

    test_path = Path(__file__)
    paths = (Path(first.__file__), Path(merge.__file__), test_path,
             test_path.with_name("middle_ai_first_detail_cases.py"),
             test_path.with_name("middle_ai_first_fixtures.py"))
    for path in paths:
        source = ai.read_text(path)
        assert len(source.splitlines()) <= 400
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.end_lineno - node.lineno + 1 <= 50, node.name
