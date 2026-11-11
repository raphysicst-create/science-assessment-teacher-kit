"""Test DB-only activity classification and optional catalog overrides offline.

Per-card targets retain prompt hashes and saved responses when peer cards change.
Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_science_axes_ai.py
Verify .venv/Scripts/python.exe -m ruff check
    services/math-assessment-api/tests/test_science_axes_ai.py
All generated inputs, outputs and isolated directories live under tmp_path.
"""

import copy
import json
import sqlite3
import zlib
from pathlib import Path

import pytest
from scripts import build_science_catalog_db as builder
from scripts import middle_ai_read as ai
from scripts import science_axes_ai as axes
from scripts import science_catalog_inputs as inputs
from scripts.build_math_assessment_demo import demo_records
from scripts.dev_activity_score import load_axes

ROUNDS = ("synthetic_demo", "synthetic_second")
EVENTS = ({"type": "thread.started"}, {"type": "turn.started"},
          {"type": "item.completed", "item": {"type": "agent_message"}},
          {"type": "turn.completed"})


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Only fake responses are allowed: no Codex or network calls")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(ai, "find_codex", forbidden)
    monkeypatch.setattr(ai, "default_model_guard", forbidden)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    records = demo_records()
    for record in records[2:]:
        record["source_round"] = ROUNDS[1]
    missing = copy.deepcopy(records[0])
    missing["item"]["item_id"] = "missing-rule-item"
    reference = inputs.read_json(inputs.ROOT / "data/reference/science_axes.json")
    database = tmp_path / "science.sqlite"
    with sqlite3.connect(database) as db:
        builder.write_science_catalog(db, records + [missing], reference)
    rules = tmp_path / "rules"
    monkeypatch.setattr(axes, "RULE_AXES_DIR", rules)
    for source_round in ROUNDS:
        items = [{**record["axes"], **{key: record["item"][key] for key in (
            "item_id", "school", "school_code", "grade", "semester", "extraction_status")},
                  "title": record["item"]["fields"]["title"]["value"]}
                 for record in records if record["source_round"] == source_round]
        save(rules / f"{source_round}.json", {"rule_version": "science-axes-v3",
             "definition_version": "fixture-def", "round": source_round, "items": items})
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    # Reuse the real run/audit path; only the external empty-directory boundary is stubbed.
    monkeypatch.setattr(ai, "isolated_directory", lambda path: isolated)
    return {"database": database, "output": tmp_path / "run", "fake": tmp_path / "fake",
            "isolated": isolated, "rules": rules, "axes_out": tmp_path / "axes_ai"}


def fake_answers(workspace, *, bad_event=False):
    cards = {card["item_id"]: card for card in axes.load_cards(workspace["database"])}
    for target in ai.load_targets(workspace["output"]):
        tasks = []
        for identity in target["card_ids"]:
            card = cards[identity]
            task = {"card_id": identity, "primary": "실험평가", "secondary": ["계산·측정"],
                    "abstain_reason": None, "quote": "온도  측정 및 기록"}
            if card["source_item_id"] == "demo-item-2":
                task.update(quote="온도 측정 및 기록")  # Other card's text cannot justify this one.
            elif card["source_item_id"] == "demo-item-3":
                task.update(primary="알 수 없는 활동", quote="탐구를 설계함")
            elif card["source_item_id"] == "demo-item-4":
                task.update(primary=None, secondary=[], abstain_reason="채점 근거 부족",
                            quote="수업에서 배운 내용을 기록한다.")
            tasks.append(task)
        save(workspace["fake"] / f"{target['target_id']}.json",
             {"tasks": tasks, "uncertain": [{"reason": "검토 필요"}]})
        events = list(EVENTS)
        if bad_event:
            events.insert(2, {"type": "item.completed", "item": {"type": "command_execution"}})
        path = workspace["fake"] / f"{target['target_id']}.events.jsonl"
        path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")


def run_args(workspace):
    return ["run", "--out-dir", str(workspace["output"]), "--isolated-cwd",
            str(workspace["isolated"]), "--fake-responses", str(workspace["fake"])]


def prepare_run(workspace):
    axes.build_targets(workspace["database"], workspace["output"])
    fake_answers(workspace)
    assert axes.main(run_args(workspace)) == 0


@pytest.mark.parametrize("per_card", [False, True])
def test_targets_run_verify_export_and_source_identity(workspace, per_card):
    common = ["--database", str(workspace["database"]), "--out-dir", str(workspace["output"])]
    flags = ["--per-card"] if per_card else []
    assert axes.main(["targets", *common, *flags]) == 0
    targets = ai.load_targets(workspace["output"])
    assert len(targets) == (5 if per_card else 2)
    assert sum(len(t["card_ids"]) for t in targets) == 5
    assert ai.read_json(workspace["output"] / "selection.json") == (
        {"rounds": None, "per_card": True} if per_card else {"rounds": None})
    assert axes.main(["targets", *common, *flags]) == 0
    assert ai.load_targets(workspace["output"]) == targets
    definitions = axes.DEFINITIONS.read_text(encoding="utf-8")
    sections = definitions[definitions.index("## 2. "):definitions.index("## 4. ")]
    for target in targets:
        prompt = ai.read_text(workspace["output"] / f"prompts/{target['target_id']}.md")
        assert prompt.startswith(sections)
        assert target["target_id"] == ai.sha(prompt)[:16]
        assert target["prompt_sha256"] == ai.sha(prompt)
        content = json.loads(prompt.split(axes.INSTRUCTIONS + "\n", 1)[1])
        assert set(content) == {"case_id", "grade", "semester", "cards"}
        assert [card["item_id"] for card in content["cards"]] == target["card_ids"]
        if per_card:
            assert len(content["cards"]) == 1
        assert all(set(axes.CARD_FIELDS) == set(card) for card in content["cards"])
        assert all(len(card["window"]) <= 3000 for card in content["cards"])
    fake_answers(workspace)
    assert axes.main(run_args(workspace)) == 0
    fake_answers(workspace, bad_event=True)
    assert axes.main(run_args(workspace)) == 0  # Saved valid responses are reused.
    assert ai.read_json(workspace["output"] / "run.json")["skipped"] == len(targets)
    assert axes.main(["verify", *common]) == 0
    assert axes.main(["export", *common, "--axes-out", str(workspace["axes_out"])]) == 0
    predictions = load_axes([workspace["axes_out"] / f"{r}.json" for r in ROUNDS])
    assert set(predictions) == {f"demo-item-{number}" for number in range(1, 5)}
    assert predictions["demo-item-1"]["activity"]["primary"] == "실험평가"
    for number, reason in ((2, "근거 원문 불일치"), (3, "정의 밖 활동"), (4, "채점 근거 부족")):
        assert predictions[f"demo-item-{number}"]["activity"]["primary"] is None
        assert predictions[f"demo-item-{number}"]["activity"]["abstain_reason"] == reason
    for source_round in ROUNDS:
        exported = ai.read_json(workspace["axes_out"] / f"{source_round}.json")
        rules = ai.read_json(workspace["rules"] / f"{source_round}.json")
        assert exported["rule_version"] == axes.VERSION
        assert exported["definition_version"] == rules["definition_version"]
        assert exported["summary"]["item_count"] == 2
        for actual, original in zip(exported["items"], rules["items"], strict=True):
            assert {k: v for k, v in actual.items() if k != "activity"} == {
                k: v for k, v in original.items() if k != "activity"}
            activity = actual["activity"]
            assert activity["rule_applied"] == "AI" and activity["candidates"] == []
            assert activity["candidate_classes"] == [] and activity["votes_e"] == {}
            assert activity["votes_s"] == {} and activity["evidence"][0]["type"] == "ai_quote"
    assert axes.export_axes(workspace["output"], workspace["database"], workspace["axes_out"])[
        "missing_rule_items"] == 1


def test_round_filter_and_bounded_only(workspace):
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET extraction_status='unbounded' "
                   "WHERE source_item_id='demo-item-2'")
    assert axes.main(["targets", "--database", str(workspace["database"]), "--out-dir",
                      str(workspace["output"]), "--rounds", ROUNDS[0]]) == 0
    assert len(ai.load_targets(workspace["output"])) == 1
    fake_answers(workspace)
    assert axes.main(run_args(workspace)) == 0
    report = axes.verify_targets(workspace["output"], workspace["database"])
    assert report["summary"]["cards"] == 2 and report["summary"]["valid_targets"] == 1


def test_run_failures_and_audit_tampering(workspace):
    axes.build_targets(workspace["database"], workspace["output"])
    assert axes.main(run_args(workspace)) == 3  # Missing fake answers.
    fake_answers(workspace, bad_event=True)
    assert axes.main(run_args(workspace)) == 3
    assert axes.verify_targets(workspace["output"], workspace["database"])["cards"] == []
    fake_answers(workspace)
    assert axes.main(run_args(workspace)) == 0
    target = ai.load_targets(workspace["output"])[0]
    events = workspace["output"] / f"responses/{target['target_id']}.events.jsonl"
    events.write_text(events.read_text(encoding="utf-8") + json.dumps(
        {"type": "item.completed", "item": {"type": "mcp_tool_call"}}) + "\n", encoding="utf-8")
    report = axes.verify_targets(workspace["output"], workspace["database"])
    assert report["summary"]["valid_targets"] == 1
    assert report["summary"]["discarded_invalid_run"] == 1


def test_stale_db_answer_and_definition_are_rejected(workspace, monkeypatch):
    prepare_run(workspace)
    target = ai.load_targets(workspace["output"])[0]
    answer = workspace["output"] / f"responses/{target['target_id']}.json"
    answer.write_text(answer.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert axes.verify_targets(workspace["output"], workspace["database"])["summary"][
        "discarded_invalid_run"] == 1
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET overview='변경됨'")
    assert axes.verify_targets(workspace["output"], workspace["database"])["cards"] == []
    prepare_run(workspace)
    definitions = workspace["output"] / "definitions.md"
    definitions.write_text(axes.DEFINITIONS.read_text(encoding="utf-8").replace(
        "## 2. 활동", "## 2. 변경된 활동"), encoding="utf-8")
    monkeypatch.setattr(axes, "DEFINITIONS", definitions)
    assert axes.verify_targets(workspace["output"], workspace["database"])["cards"] == []


def test_missing_duplicate_malformed_and_truncated_evidence(workspace):
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET source_html_zlib=? WHERE source_item_id=?",
                   (zlib.compress(("<p>" + "가" * 3000 + "끝근거</p>").encode()), "demo-item-1"))
    card = next(c for c in axes.load_cards(workspace["database"])
                if c["source_item_id"] == "demo-item-1")
    assert card["window"] == "가" * 3000
    _, names = axes.definition_sections()
    task = {"card_id": card["item_id"], "primary": "탐구", "quote": "끝근거"}
    assert axes.verify_task(task, card, names)["abstain_reason"] == "근거 원문 불일치"
    for tasks in ([], [task, task], [None, {"card_id": []}]):
        verdict = axes.verify_group([card], {"tasks": tasks}, "target", names)[0]
        assert verdict["primary"] is None and not verdict["checked"]
    for primary in ([], {}, "정의 밖"):
        task.update(primary=primary, quote="가가")
        assert axes.verify_task(task, card, names)["primary"] is None
    task.update(primary="탐구", quote="가가", secondary=[[], "탐구", "분석", "분석", "없는 활동"])
    assert axes.verify_task(task, card, names)["secondary"] == ["분석"]


def synthetic_builder_inputs(tmp_path, monkeypatch):
    """Reuse demo records, supplying the existing loader with synthetic round files."""
    records = demo_records()
    for record in records[2:]:
        record["source_round"] = ROUNDS[1]
    monkeypatch.setattr(inputs, "ROOT", tmp_path)
    monkeypatch.setattr(builder, "ROOT", tmp_path)
    original_loader = inputs.load_science_records
    monkeypatch.setattr(builder, "load_science_records",
                        lambda rounds, **kwargs: original_loader(rounds, root=tmp_path, **kwargs))
    reference = {"activities": [{"name": "실험평가", "id": "experiment"},
                               {"name": "계산·측정", "id": "measurement"},
                               {"name": "발표·토론", "id": "presentation"},
                               {"name": "탐구", "id": "inquiry"}]}
    save(tmp_path / "data/reference/science_axes.json", reference)
    for source_round in ROUNDS:
        selected = [record for record in records if record["source_round"] == source_round]
        for record in selected:
            record["item"]["converted_path"] = f"converted/{record['item']['document_id']}.json"
            save(tmp_path / record["item"]["converted_path"], {"text": record["text"]})
        save(tmp_path / f"data/derived/items/{source_round}.json", {
            "rule_version": "items-fixture", "items": [r["item"] for r in selected],
            "documents": [{"document_id": r["item"]["document_id"], **r["document"]}
                          for r in selected]})
        save(tmp_path / f"data/derived/axes/{source_round}.json", {
            "rule_version": "science-axes-v3",
            "items": [{"item_id": r["item"]["item_id"], **r["axes"]} for r in selected]})


def test_build_science_activity_override_preserves_units_and_fallback(
    tmp_path, monkeypatch, capsys,
):
    synthetic_builder_inputs(tmp_path, monkeypatch)
    activity_dir = tmp_path / "overrides"
    save(activity_dir / f"{ROUNDS[0]}.json", {"rule_version": axes.VERSION, "items": [{
        "item_id": "demo-item-1", "unit": {"status": "wrong", "areas": []},
        "activity": axes.activity_for({"primary": "탐구",
            "secondary": ["계산·측정"], "abstain_reason": None, "quote": "온도 측정 및 기록"})}]})
    baseline = tmp_path / "baseline.sqlite"
    modified = tmp_path / "modified.sqlite"
    original = builder.build_catalog(baseline, rounds=ROUNDS)
    assert "activity_axes" not in original
    monkeypatch.setattr("sys.argv", ["build", "--output", str(modified), "--rounds", *ROUNDS,
                                    "--activity-axes-dir", str(activity_dir)])
    builder.main()
    result = json.loads(capsys.readouterr().out)
    assert result["activity_axes"] == {
        "overridden_items": 1, "missing_rounds": 1, "missing_items": 3}
    with sqlite3.connect(baseline) as before, sqlite3.connect(modified) as after:
        query = "SELECT * FROM assessment_item_axes WHERE axis='unit' ORDER BY item_id, value"
        assert before.execute(query).fetchall() == after.execute(query).fetchall()
        changed_id = after.execute("SELECT item_id FROM assessment_items WHERE source_item_id=?",
                                   ("demo-item-1",)).fetchone()[0]
        query = "SELECT value, rank, rule_version, basis, evidence FROM assessment_item_axes "
        rows = after.execute(query + "WHERE item_id=? AND axis='activity' ORDER BY rank",
                             (changed_id,)).fetchall()
        assert rows == [("inquiry", 1, axes.VERSION, "ai_quote", "온도 측정 및 기록"),
                        ("measurement", 2, axes.VERSION, "ai_quote", "온도 측정 및 기록")]
        query = ("SELECT * FROM assessment_item_axes "
                 "WHERE axis='activity' AND item_id!=? ORDER BY 1,3")
        assert before.execute(query, (changed_id,)).fetchall() == after.execute(
            query, (changed_id,)).fetchall()
        assert after.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert after.execute("PRAGMA foreign_key_check").fetchall() == []


def test_axes_paths_and_round_names_are_guarded(tmp_path):
    for path in ("data/gold2/labels.json", "data/derived/items_ai/round.json", "round-gold.json"):
        with pytest.raises(ValueError):
            axes.checked_path(tmp_path / path)
    for source_round in ("../elsewhere", "C:/absolute", ""):
        with pytest.raises(ValueError):
            axes.round_filename(source_round)
    assert axes.round_filename("round-gold") == "round-gold.json"
    assert isinstance(axes.DEFAULT_OUT_DIR, Path)


def test_source_round_names_in_db_and_missing_rule_round(workspace):
    source_round = "2026-round-1-gold"
    rules = ai.read_json(workspace["rules"] / f"{ROUNDS[0]}.json")
    save(workspace["rules"] / f"{source_round}.json", rules)
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET source_round=? WHERE source_round=?",
                   (source_round, ROUNDS[0]))
    prepare_run(workspace)
    report = axes.verify_targets(workspace["output"], workspace["database"])
    assert report["summary"]["cards"] == 5  # Gold-round DB cards stay in scope.
    (workspace["rules"] / f"{ROUNDS[1]}.json").unlink()
    result = axes.export_axes(workspace["output"], workspace["database"], workspace["axes_out"])
    assert result == {"rounds": 2, "exported": 2, "missing_rule_items": 3,
                      "missing_rule_rounds": 1, "unverified_items": 0}
    assert (workspace["axes_out"] / f"{source_round}.json").is_file()
    assert not (workspace["axes_out"] / f"{ROUNDS[1]}.json").exists()


def test_empty_targets_and_export_rechecks_run(workspace):
    axes.build_targets(workspace["database"], workspace["output"], ["missing"])
    assert axes.main(run_args(workspace)) == 0
    assert axes.export_axes(workspace["output"], workspace["database"], workspace["axes_out"])[
        "exported"] == 0
    prepare_run(workspace)
    for target in ai.load_targets(workspace["output"]):
        answer = workspace["output"] / f"responses/{target['target_id']}.json"
        answer.write_text("{}", encoding="utf-8")
    # A prior verified.json cannot authorize an answer that no longer passes valid_run.
    result = axes.export_axes(workspace["output"], workspace["database"], workspace["axes_out"])
    assert result["exported"] == 0 and result["unverified_items"] == 4


@pytest.mark.parametrize("per_card", [False, True])
def test_peer_card_changes_preserve_only_per_card_hashes_and_saved_runs(workspace, per_card):
    database, output = workspace["database"], workspace["output"]
    axes.build_targets(database, output, per_card=per_card)
    before = ai.load_targets(output)
    target = before[0]
    identity = target["card_ids"][0]
    prompt = (output / f"prompts/{target['target_id']}.md").read_bytes()
    fake_answers(workspace)
    assert axes.main(run_args(workspace)) == 0
    with sqlite3.connect(database) as db:
        db.row_factory = sqlite3.Row
        row = dict(db.execute("SELECT * FROM assessment_items WHERE item_id=?",
                              (identity,)).fetchone())
        row.update(item_id="added-card", source_item_id="added-source-item", item_order=100)
        db.execute(f"INSERT INTO assessment_items ({','.join(row)}) "
                   f"VALUES ({','.join('?' for _ in row)})", list(row.values()))
    axes.build_targets(database, output, per_card=per_card)
    after = ai.load_targets(output)
    changed = next(t for t in after if identity in t["card_ids"])
    assert len(after) == len(before) + int(per_card)
    assert (changed["target_id"] == target["target_id"]) == per_card
    if per_card:
        assert changed == target
        assert (output / f"prompts/{changed['target_id']}.md").read_bytes() == prompt
    fake_answers(workspace)
    assert axes.main(run_args(workspace)) == 0
    assert ai.read_json(output / "run.json")["skipped"] == len(before) - int(not per_card)
    assert axes.verify_targets(output, database)["summary"]["cards"] == 6


def test_export_writes_a_selected_round_left_without_cards(workspace):
    # A round whose documents were all dropped as repeats still needs a file for hybrid.
    empty_round = "synthetic_emptied"
    rules = ai.read_json(workspace["rules"] / f"{ROUNDS[0]}.json")
    save(workspace["rules"] / f"{empty_round}.json", {**rules, "items": []})
    axes.build_targets(workspace["database"], workspace["output"], [*ROUNDS, empty_round])
    fake_answers(workspace)
    assert axes.main(run_args(workspace)) == 0
    result = axes.export_axes(workspace["output"], workspace["database"], workspace["axes_out"])
    assert result["rounds"] == 3
    assert ai.read_json(workspace["axes_out"] / f"{empty_round}.json")["items"] == []
