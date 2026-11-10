"""Verify source-bound activity contexts and saved quote windows entirely offline.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_activity_context.py
Verify .venv/Scripts/python.exe -m ruff check
    services/math-assessment-api/tests/test_activity_context.py
All generated files live under tmp_path; no protected data is read.
"""

import json
import sqlite3

import pytest
from scripts import activity_context as context
from scripts import build_science_catalog_db as builder
from scripts import middle_ai_read as ai
from scripts import science_axes_ai as axes
from scripts import science_card_check as check
from scripts.build_math_assessment_demo import demo_records

ROUND = "synthetic_demo"


def save(path, value):
    ai.save_json(path, value)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No AI or network calls are allowed")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(ai, "find_codex", forbidden)
    monkeypatch.setattr(ai, "default_model_guard", forbidden)


@pytest.fixture
def source_root(tmp_path, monkeypatch):
    monkeypatch.setattr(context, "ROOT", tmp_path)
    monkeypatch.delenv(ai.GOLD_MEASUREMENT_ENV, raising=False)
    return tmp_path


def task(root, identity, text, *, detail=None):
    converted = f"converted/{identity}.json"
    save(root / converted, {"text": text})
    return {"ai_task_id": identity, "converted_path": converted, "text_sha256": ai.sha(text),
            "detail_locator": detail if detail is not None else {"start": 0, "end": len(text)}}


def round_inputs(root, matches, tasks, round_key=ROUND):
    save(root / f"data/derived/items_ai/{round_key}.json", {"ai_first_matches": matches})
    save(ai.round_dir(root, round_key) / "first/verified.json", {"kept": tasks})


def test_build_matches_locators_hashes_and_ambiguity(source_root):
    raw = ("제외할 머리\r\n<p> 평가요소 &amp; 채점기준 </p>"
           "<script>숨김</script><p> 실험 설계 </p>꼬리")
    locator = {"start": raw.index("<p>"), "end": raw.index("꼬리")}
    first = task(source_root, "first", raw, detail=locator)
    second = task(source_root, "second", "서로 다른 세부표")
    bad_hash = task(source_root, "bad-hash", "변경된 원문")
    bad_hash["text_sha256"] = ai.sha("변경 전 원문")
    missing = task(source_root, "no-locator", "본문")
    del missing["detail_locator"]
    round_inputs(source_root, {
        "first": ["one", "ambiguous", "twin"], "second": ["ambiguous"],
        "bad-hash": ["bad"], "no-locator": ["missing"],
    }, [second, missing, bad_hash, first])
    output = source_root / "data/derived/activity_context.json"
    report = context.build([ROUND], output)
    assert list(report["contexts"]) == ["one", "twin"]
    assert report["contexts"]["one"] == {
        "text": "평가요소 & 채점기준\n실험 설계", "round": ROUND, "ai_task_id": "first",
        **locator, "text_sha256": ai.sha(raw),
    }
    assert report["summary"]["reasons"] == {
        "ambiguous_context": 1, "missing_detail_locator": 1, "text_sha256_mismatch": 1}
    assert ai.read_json(output) == report


@pytest.mark.parametrize("locator", [
    {"start": -1, "end": 1}, {"start": 1, "end": 1}, {"start": 0, "end": 4},
    {"start": False, "end": 1}, {"start": "0", "end": 1}, {},
])
def test_invalid_locator_is_skipped(source_root, locator):
    entry = task(source_root, "invalid", "본문", detail=locator)
    round_inputs(source_root, {"invalid": ["item"]}, [entry])
    report = context.build([ROUND], source_root / "out.json")
    assert report["contexts"] == {}
    assert report["skipped"][0]["reason"] == "invalid_detail_locator"


def test_truncation_same_context_and_different_tail(source_root):
    text = "가" * context.CONTEXT_CHARS
    tasks = [task(source_root, "a", text + "첫 끝"),
             task(source_root, "b", text + "다른 끝"),
             task(source_root, "c", "<p>같은 문맥</p>"),
             task(source_root, "d", "같은 문맥")]
    round_inputs(source_root, {"a": ["long", "ambiguous"], "b": ["ambiguous"],
                               "c": ["same"], "d": ["same"]}, tasks)
    report = context.build([ROUND], source_root / "out.json")
    assert report["contexts"]["long"]["text"] == text + check.OMITTED
    assert report["contexts"]["same"]["text"] == "같은 문맥"
    assert "ambiguous" not in report["contexts"]
    assert report["summary"]["reasons"] == {"ambiguous_context": 1}


def test_missing_round_inputs_and_deterministic_cli(source_root):
    first = task(source_root, "first", "첫 문맥")
    second = task(source_root, "second", "둘째 문맥")
    round_inputs(source_root, {"first": ["z"]}, [first], "round_a")
    round_inputs(source_root, {"second": ["a"]}, [second], "round_b")
    save(source_root / "data/derived/items_ai/no_matches.json", {"items": []})
    save(source_root / "data/derived/items_ai/no_verified.json", {"ai_first_matches": {}})
    output = source_root / "out.json"
    rounds = ["round_b", "missing", "no_verified", "round_a", "no_matches"]
    assert context.main(["build", "--rounds", *rounds, "--out", str(output)]) == 0
    before = output.read_bytes()
    context.build(list(reversed(rounds)) + ["round_a"], output)
    assert output.read_bytes() == before
    report = ai.read_json(output)
    assert list(report["contexts"]) == ["a", "z"]
    assert report["summary"]["reasons"] == {
        "missing_ai_first_matches": 1, "missing_items_ai": 1, "missing_verified": 1}


def test_round_lock_and_source_paths_are_checked_before_reading(source_root, monkeypatch):
    def forbidden_read(*args):
        pytest.fail("Locked or protected sources must never be read")

    monkeypatch.setattr(ai, "read_json", forbidden_read)
    for key in ("round-gold", "gold_round", "../outside"):
        with pytest.raises(ValueError):
            context.build([key], source_root / "out.json")
    for path in ("../outside.json", "data/gold2/labels.json", "docs/gold/answer.json",
                 "data/dev_labels/labels/a.json", "data/.gold-before-acl-fix/a", ".env"):
        entry = {"detail_locator": {"start": 0, "end": 1}, "converted_path": path}
        with pytest.raises(ValueError):
            context.task_context(entry, ROUND)


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "science.sqlite"
    reference = ai.read_json(axes.ROOT / "data/reference/science_axes.json")
    with sqlite3.connect(path) as db:
        builder.write_science_catalog(db, demo_records(), reference)
    return path


def test_targets_without_context_keep_legacy_bytes(database, tmp_path):
    output = tmp_path / "run"
    expected = []
    sections, _ = axes.definition_sections()
    for scope, _, group in check.grouped_targets(axes.load_cards(database)):
        content = {key: scope[key] for key in ("case_id", "grade", "semester")}
        content["cards"] = [{name: card[name] for name in (
            "item_id", "title", "method", "overview", "window")} for card in group]
        prompt = sections + axes.INSTRUCTIONS + "\n" + json.dumps(
            content, ensure_ascii=False, indent=2) + "\n"
        digest = ai.sha(prompt)
        expected.append({**{key: scope[key] for key in (
            "case_id", "grade", "semester", "card_ids")},
            "target_id": digest[:16], "prompt_sha256": digest})
        axes.build_targets(database, output)
        assert (output / f"prompts/{digest[:16]}.md").read_bytes() == prompt.encode("utf-8")
    assert (output / "targets.jsonl").read_bytes() == "".join(
        json.dumps(target, ensure_ascii=False) + "\n" for target in expected).encode("utf-8")
    assert (output / "selection.json").read_bytes() == b'{\n  "rounds": null\n}\n'


def test_context_changes_only_source_item_window(database, tmp_path):
    original = axes.load_cards(database)
    context_path = tmp_path / "activity_context.json"
    detail = "평가" * 1700 + " 새로운 평가기준"
    save(context_path, {"contexts": {"demo-item-1": {"text": detail}}})
    changed = axes.load_cards(database, context=context_path)
    for before, after in zip(original, changed, strict=True):
        basis = after.pop("window_basis")
        if before["source_item_id"] == "demo-item-1":
            assert basis == "ai_first_detail" and after["window"] == detail
            assert len(after["window"]) > check.WINDOW_CHARS
            before["window"] = detail
        else:
            assert basis == "card"
        assert before == after
    output = tmp_path / "run"
    assert axes.main(["targets", "--database", str(database), "--out-dir", str(output),
                      "--context", str(context_path)]) == 0
    saved = [c for target in ai.load_targets(output) for c in target["cards"]]
    assert next(c for c in saved if c["source_item_id"] == "demo-item-1")["window"] == detail
    assert axes.checked_path(axes.ROOT / "data/derived/activity_context.json")
    with pytest.raises(ValueError):
        axes.load_cards(database, context=tmp_path / "data/gold2/context.json")


def fake_run(output, tmp_path, monkeypatch, quote):
    fake = tmp_path / "fake"
    for target in ai.load_targets(output):
        tasks = [{"card_id": card["item_id"], "primary": "실험평가", "secondary": [],
                  "quote": quote if card["source_item_id"] == "demo-item-1"
                  else card["window"][:15]} for card in target["cards"]]
        save(fake / f"{target['target_id']}.json", {"tasks": tasks, "uncertain": []})
        ai.write_text(fake / f"{target['target_id']}.events.jsonl",
                      json.dumps({"type": "turn.completed"}) + "\n")
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    monkeypatch.setattr(ai, "isolated_directory", lambda path: isolated)
    assert axes.main(["run", "--out-dir", str(output), "--isolated-cwd", str(isolated),
                      "--fake-responses", str(fake)]) == 0


@pytest.mark.parametrize("use_detail_quote", [True, False])
def test_verify_uses_saved_windows_after_context_and_db_change(
    database, tmp_path, monkeypatch, use_detail_quote,
):
    card = next(c for c in axes.load_cards(database) if c["source_item_id"] == "demo-item-1")
    legacy_quote = card["window"][:15]
    detail_quote = "새 세부표에서만 찾을 수 있는 실험 설계 근거"
    detail = "가" * 3300 + "\n" + detail_quote
    context_path, output = tmp_path / "activity_context.json", tmp_path / "run"
    save(context_path, {"contexts": {"demo-item-1": {"text": detail}}})
    axes.build_targets(database, output, context=context_path)
    fake_run(output, tmp_path, monkeypatch, detail_quote if use_detail_quote else legacy_quote)
    save(context_path, {"contexts": {"demo-item-1": {"text": "바뀐 문맥"}}})
    with sqlite3.connect(database) as db:
        db.execute("UPDATE assessment_items SET overview='바뀐 DB'")

    def forbidden_reload(*args, **kwargs):
        pytest.fail("Verification must use the windows saved in targets")

    monkeypatch.setattr(axes, "load_cards", forbidden_reload)
    report = axes.verify_targets(output, database)
    verdict = next(c for c in report["cards"] if c["item_id"] == card["item_id"])
    if use_detail_quote:
        assert verdict["primary"] == "실험평가" and verdict["quote"] == detail_quote
    else:
        assert verdict["primary"] is None and verdict["abstain_reason"] == "근거 원문 불일치"
    # Saved windows are still tied to the prompt hash, rather than accepted on trust.
    targets = ai.load_targets(output)
    targets[0]["cards"][0]["window"] = "위조된 문맥"
    ai.write_text(output / "targets.jsonl", "".join(json.dumps(t) + "\n" for t in targets))
    assert axes.verify_targets(output, database)["summary"]["discarded_target_mismatch"] == 1


def test_string_match_from_old_merge_is_one_item(source_root):
    """S20 검수: 옛 병합은 새 항목 id를 문자열로 남겼다. 글자로 쪼개지 않고 항목 하나로 읽는다."""
    only = task(source_root, "new-task", "새 과제 세부표 글")
    round_inputs(source_root, {"new-task": "aitask_new"}, [only])
    result = context.build([ROUND], source_root / "out.json")
    assert list(result["contexts"]) == ["aitask_new"]
