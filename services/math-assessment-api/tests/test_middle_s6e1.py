"""Synthetic offline S6e-1 regressions. No AI process or school source is used."""

import copy
import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from scripts import middle_ai_read as ai

PROJECT = Path(__file__).resolve().parents[3]
ROUND = "2026-round-1-dev2"


@pytest.fixture
def directory(monkeypatch):
    parent = PROJECT / ".tmp/s6e1-tests"
    directory = parent / uuid4().hex
    directory.mkdir(parents=True)

    def forbidden(*args, **kwargs):
        pytest.fail("S6e-1 tests must never invoke Codex or the network")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    yield directory
    assert directory.resolve().is_relative_to(parent.resolve())
    shutil.rmtree(directory)


def source(text="1학년 1학기\r\n온도<br> 관찰 보고서\r\n수행평가 실험\r\n"):
    conversion = {"text": text, "converter": "kordoc"}
    target = {"document_id": "synthetic-document", "child_id": None, "school": "가상중학교",
              "school_code": "synthetic", "filename": "과학 평가계획.hwp", "round": ROUND,
              "converted_path": "data/derived/segments/synthetic.json", "original_path": None,
              "text_sha256": ai.sha(text), "target_id": "synthetic-target",
              "line_start": 1, "line_end": len(text.splitlines()),
              "grade_candidates": [1], "semester_candidates": [1]}
    task = {"grade": 1, "semester": 1, "title": "온도 관찰 보고서", "title_line": 2,
            "evidence": [{"line_start": 2, "line_end": 3, "quote": "온도 관찰 보고서"}],
            "grade_evidence": {"line": 1, "quote": "1학년"},
            "semester_evidence": {"line": 1, "quote": "1학기"}, "seen_in": "detail"}
    return conversion, target, task


@pytest.mark.parametrize("change", [
    {"title": "지어낸 제목"},
    {"evidence": [{"line_start": 2, "line_end": 3, "quote": "지어낸 인용"}]},
    {"evidence": [{"line_start": 1, "line_end": 1, "quote": "온도 관찰 보고서"}]},
    {"title_line": 4}, {"title_line": True}, {"title_line": 1},
    {"evidence": []}, {"evidence": [{"line_start": 2, "line_end": 2, "quote": ""}]},
    {"grade_evidence": None}, {"grade_evidence": {"line": 2, "quote": "관찰 보고서"}},
    {"grade_evidence": {"line": 1, "quote": "2학년"}}, {"semester_evidence": None},
    {"seen_in": "invented"}, {"grade": "1"},
])
def test_verify_rejects_fabrication_ranges_and_missing_scope(change):
    conversion, target, task = source()
    task.update(change)
    with pytest.raises(ValueError):
        ai.verify_task(task, target, conversion)


def test_verify_requires_title_within_cited_lines():
    conversion, target, task = source()
    task["evidence"] = [{"line_start": 3, "line_end": 3, "quote": "수행평가 실험"}]
    with pytest.raises(ValueError, match="제목이"):
        ai.verify_task(task, target, conversion)


@pytest.mark.parametrize("key", ["grade", "semester"])
@pytest.mark.parametrize("candidates", [[], [1, 2], [2]])
def test_verify_ambiguous_metadata(key, candidates):
    conversion, target, task = source()
    target[f"{key}_candidates"] = candidates
    task[f"{key}_evidence"] = "metadata"
    with pytest.raises(ValueError, match="메타데이터"):
        ai.verify_task(task, target, conversion)


def test_verify_normalization_offsets_and_metadata():
    conversion, target, task = source()
    task["grade_evidence"] = "metadata"
    task["semester_evidence"] = "metadata"
    verified = ai.verify_task(task, target, conversion)
    loc = verified["title_locator"]
    text = conversion["text"]
    assert text[loc["start"]:loc["end"]] == "온도<br> 관찰 보고서"
    assert loc["start"] == len("1학년 1학기\r\n")
    assert loc["end_exclusive"] and loc["offset_unit"] == "unicode_codepoint"
    assert ai.literal_span("앞🙂 Ａ\t <b>관찰</b>  뒤", "A 관찰", 7, conversion)["start"] == 10
    normalized, positions = ai.normalized_map("각 Ａ e\u0301")
    assert normalized == "각 A é"
    assert positions[0] == (0, 3)
    assert ai.normalize("ㄱㅏ 각") == "가 각"
    with pytest.raises(ValueError):
        ai.literal_span("½", "1", 0, conversion)
    assert ai.literal_span("½ 1", "1", 0, conversion)["start"] == 2


def test_verify_chunk_boundary_scope_and_duplicate():
    conversion, target, task = source()
    first = ai.verify_task(task, target, conversion)
    target["target_id"] = "overlapping-chunk"
    second = ai.verify_task(task, target, conversion)
    result = ai.deduplicate([first, second])
    assert len(result) == 1
    assert len(result[0]["target_ids"]) == 2
    target["line_start"] = 2
    with pytest.raises(ValueError, match="범위 밖"):
        ai.verify_task(task, target, conversion)


def test_nonoverlapping_same_title_remains_separate():
    conversion, target, task = source("1학년 1학기\n온도 관찰 보고서\n온도 관찰 보고서\n")
    first = ai.verify_task(task, target, conversion)
    task["title_line"] = 3
    task["evidence"] = [{"line_start": 3, "line_end": 3, "quote": task["title"]}]
    second = ai.verify_task(task, target, conversion)
    assert len(ai.deduplicate([first, second])) == 2


@pytest.mark.parametrize("key,quote", [("grade", "1·2학년"), ("semester", "1·2학기")])
def test_scope_rejects_combined_markers(key, quote):
    conversion, target, task = source(f"{quote}\n온도 관찰 보고서\n")
    task["evidence"][0]["line_end"] = 2
    task[f"{key}_evidence"] = {"line": 1, "quote": quote}
    task[f"{'semester' if key == 'grade' else 'grade'}_evidence"] = "metadata"
    with pytest.raises(ValueError, match="단일"):
        ai.verify_task(task, target, conversion)


def verified_tasks():
    text = "1학년 1학기 과학 평가계획\n관찰 보고서\n실험 보고서\n"
    conversion, target, base = source(text)
    result = []
    for line, title in [(2, "관찰 보고서"), (3, "실험 보고서")]:
        task = {**base, "title": title, "title_line": line,
                "evidence": [{"line_start": line, "line_end": line, "quote": title}]}
        result.append(ai.verify_task(task, target, conversion))
    return conversion, target, result


def rule_item(task, status="bounded"):
    item = ai.ai_item(task)
    item.update({"item_id": "rule-" + task["ai_task_id"], "extraction_status": status})
    item.pop("extraction_method")
    return item


def test_merge_agrees_new_split_and_conflict():
    _, _, tasks = verified_tasks()
    rule = rule_item(tasks[0])
    rules = {"schema_version": 1, "round": ROUND, "items": [rule]}
    before = copy.deepcopy(rules)
    merged = ai.merge_report(rules, {"kept": tasks})
    assert rules == before
    assert merged["items"][0] == rule
    assert len(merged["ai_relations"]["agrees"]) == 1
    assert len(merged["ai_relations"]["new"]) == 1
    added = merged["items"][-1]
    assert added["candidate_role"] == "performance"
    assert added["extraction_status"] == "ai_verified"
    assert added["extraction_method"] == "ai_read" and not added["public_eligible"]
    assert added["fields"]["title"]["status"] == "present"
    assert all(f["status"] == "unconfirmed" for n, f in added["fields"].items() if n != "title")
    rule["locator"]["end"] = tasks[1]["locator"]["end"]
    conflict = ai.merge_report(rules, {"kept": tasks})
    assert len(conflict["items"]) == 1
    assert len(conflict["ai_relations"]["conflict"]) == 1
    rule["extraction_status"] = "review"
    split = ai.merge_report(rules, {"kept": tasks})
    assert len(split["items"]) == 3
    assert split["ai_relations"]["ai_split_suggested"][0]["rule_item_id"] == rule["item_id"]
    assert split["items"][0] == rule


def test_merge_multiple_rule_overlaps_remains_conflict():
    _, _, tasks = verified_tasks()
    rules = {"items": [rule_item(tasks[0]), rule_item(tasks[0], "review")]}
    rules["items"][1]["item_id"] += "-second"
    merged = ai.merge_report(rules, {"kept": tasks[:1]})
    assert len(merged["items"]) == 2
    assert merged["ai_relations"]["conflict"]


def install_source(directory, text, *, filename="과학 평가계획.hwp", sections=None):
    conversion, target, _ = source(text)
    ai.save_json(directory / target["converted_path"], conversion)
    document = {"document_id": target["document_id"], "converted_path": target["converted_path"],
                "text_sha256": target["text_sha256"], "source": {
                    "school_name": target["school"], "school_code": target["school_code"],
                    "candidate_name": filename},
                "segments": [{"grade": 1, "semester": 1}]}
    ai.save_json(directory / f"data/derived/segments/{ROUND}.json", {"documents": [document]})
    ai.save_json(directory / f"data/derived/subjects/{ROUND}.json", {"sections": sections or []})
    ai.save_json(directory / f"data/derived/items/{ROUND}.json", {"round": ROUND, "items": []})
    ai.write_text(directory / "scripts/prompts/middle_ai_read_v2.md", "합성 원문 읽기")
    return document


def fake_files(directory, targets, response=None, events=None):
    fake = directory / "fake"
    for target in targets:
        identity = target["target_id"]
        ai.save_json(fake / f"{identity}.json", response or {"tasks": [], "uncertain": []})
        event_list = events or [{"type": "thread.started"}, {"type": "turn.started"},
                                {"type": "item.completed", "item": {"type": "agent_message"}},
                                {"type": "turn.completed"}]
        ai.write_text(fake / f"{identity}.events.jsonl", "".join(
            json.dumps(e) + "\n" for e in event_list))
    return fake


def test_targets_integrated_table_only_and_other_subject_exclusion(directory):
    text = ("전 과목 평가계획\n<table>\n<tr><td>국어</td><td>쓰기</td></tr>\n</table>\n\n"
            "<table>\n<tr><td>과학</td><td>관찰 보고서</td></tr>\n</table>\n\n"
            "<table>\n<tr><td>수학</td><td>계산</td></tr>\n</table>\n")
    install_source(directory, text, filename="전 과목 평가계획.hwp")
    summary = ai.build_targets(directory, ROUND, mode="all")
    output = ai.round_dir(directory, ROUND) / "all"
    targets = ai.load_targets(output)
    assert summary["documents"] == summary["chunks"] == 1
    assert targets[0]["mode"] == "b_marker"
    prompt = (output / f"prompts/{targets[0]['target_id']}.md").read_text(encoding="utf-8")
    assert "관찰 보고서" in prompt and "쓰기" not in prompt and "계산" not in prompt
    install_source(directory, text, filename="국어 평가계획.hwp")
    summary = ai.build_targets(directory, ROUND, mode="all")
    assert summary["documents"] == 0
    assert "다른 단일 교과" in summary["excluded"][0]["reason"]


def test_targets_multisubject_context_and_marker_fallback():
    lines = ["본문\n"] * 400
    lines[200] = "과학\n"
    text = "".join(lines)
    offset = len("".join(lines[:200]))
    sections = [{"science_candidate": True, "status": "mixed",
                 "locator": {"start": offset, "end": offset + len(lines[200])}}]
    mode, windows, _ = ai.target_windows(text, "전 과목 평가계획.hwp", sections)
    assert mode == "a_context" and windows == [(121, 281)]
    mode, windows, _ = ai.target_windows(text, "전 과목 평가계획.hwp", [])
    assert mode == "b_marker" and windows == [(141, 261)]
    assert not ai.science_markers("과학적 사고력을 기른다.\n과학기술을 활용한다.\n")
    assert ai.science_markers("국어, 수학, 과학, 영어\n") == [0]


def test_targets_large_document_overlap(directory):
    text = "과학 평가계획\n" + "한글🙂 자료 " * 100 + "\n"
    text += ("원문 글자 " * 100 + "\n") * 160
    install_source(directory, text, sections=[{
        "document_id": "synthetic-document", "science_candidate": True, "status": "target",
        "locator": {"start": 0, "end": len(text)}}])
    summary = ai.build_targets(directory, ROUND)
    targets = ai.load_targets(ai.round_dir(directory, ROUND))
    assert summary["chunks"] > 1
    assert all(t["char_count"] <= 60_000 for t in targets)
    assert targets[0]["start"] == 0 and targets[-1]["end"] == len(text)
    assert targets[0]["end"] - targets[1]["start"] >= 3_000
    assert targets[0]["line_end"] >= targets[1]["line_start"]
    with pytest.raises(ValueError, match="단일 줄"):
        ai.split_window(["x" * 60_001], 1, 1)


def test_targets_zip_children_use_independent_documents(directory):
    first = install_source(directory, "과학 평가계획\n1학년 1학기\n관찰 보고서\n")
    first.update({"document_id": "child-a", "child_id": "child-a", "member_name": "과학1.hwp"})
    second = copy.deepcopy(first)
    second.update({"document_id": "child-b", "child_id": "child-b", "member_name": "과학2.hwp",
                   "converted_path": "data/derived/segments/synthetic-child-b.json"})
    text = "과학 평가계획\n2학년 1학기\n실험 보고서\n"
    second["text_sha256"] = ai.sha(text)
    ai.save_json(directory / second["converted_path"], {"text": text, "converter": "kordoc"})
    ai.save_json(directory / f"data/derived/segments/{ROUND}.json", {"documents": [first, second]})
    summary = ai.build_targets(directory, ROUND)
    targets = ai.load_targets(ai.round_dir(directory, ROUND))
    assert summary["documents"] == 2
    assert {t["document_id"] for t in targets} == {"child-a", "child-b"}
    assert len({t["target_id"] for t in targets}) == 2
    assert all(t["start"] == 0 for t in targets)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_run_fake_resume_audit_and_dry_run(directory, monkeypatch, capsys, newline):
    text = "과학 평가계획\n1학년 1학기\n관찰 보고서\n".replace("\n", newline)
    install_source(directory, text)
    ai.build_targets(directory, ROUND)
    output = ai.round_dir(directory, ROUND)
    targets = ai.load_targets(output)
    fake = fake_files(directory, targets)
    # The real guard is tested independently. Fake runs never leave the project.
    monkeypatch.setattr(ai, "isolated_directory", lambda path: directory)
    first = ai.run_targets(directory, ROUND, directory, fake_responses=fake)
    assert first["valid"] == 1 and first["skipped"] == 0
    second = ai.run_targets(directory, ROUND, directory, fake_responses=fake)
    assert second["skipped"] == 1
    event_path = output / f"responses/{targets[0]['target_id']}.events.jsonl"
    ai.write_text(event_path, '{"type":"turn.completed"}\n')
    assert not ai.valid_run(output, targets[0])[0]
    third = ai.run_targets(directory, ROUND, directory, fake_responses=fake)
    assert third["valid"] == 1 and third["skipped"] == 0
    dry = ai.run_targets(directory, ROUND, directory, dry_run=True)
    command = dry["results"][0]["command"]
    assert "--strict-config" in command and "--json" in command and command.endswith(" -")
    assert "--model" not in command and "--workers" not in command
    assert ai.audit_events(event_path)["valid"]
    events = [{"type": "item.completed", "item": {"type": "command_execution"}},
              {"type": "new.version.event"}, {"type": "turn.completed"}]
    # Remove the valid status by changing its prompt binding, forcing a retry.
    status_path = event_path.with_name(targets[0]["target_id"] + ".status.json")
    status = ai.read_json(status_path)
    status["prompt_sha256"] = "stale"
    ai.save_json(status_path, status)
    fake_files(directory, targets, events=events)
    invalid = ai.run_targets(directory, ROUND, directory, fake_responses=fake)
    assert invalid["valid"] == 0 and invalid["unknown_events"] == 1
    assert "command_execution" in invalid["results"][0]["audit"]["violations"]
    assert ai.verify_targets(directory, ROUND)["summary"]["discarded"] == 1
    monkeypatch.setattr(ai, "ROOT", directory)
    ai.main(["run", "--round-key", ROUND, "--isolated-cwd", str(directory), "--dry-run"])
    assert "--skip-git-repo-check" in capsys.readouterr().out


@pytest.mark.parametrize("item_type", sorted(ai.TOOL_ITEMS) + ["future_tool"])
def test_audit_all_tools_and_unknown_types(directory, item_type):
    path = directory / "events.jsonl"
    ai.write_text(path, json.dumps({"type": "item.started", "item": {"type": item_type}})
                  + '\n{"type":"turn.completed"}\n')
    assert not ai.audit_events(path)["valid"]


@pytest.mark.parametrize("events", ['', '{}\n', 'not-json\n', '[]\n',
                                    '{"type":"turn.failed"}\n',
                                    '{"type":"turn.completed","model":"gpt-6-astra"}\n'])
def test_audit_incomplete_malformed_and_excluded_model(directory, events):
    path = directory / "events.jsonl"
    ai.write_text(path, events)
    assert not ai.audit_events(path)["valid"]


def test_audit_nested_tool_payload(directory):
    path = directory / "events.jsonl"
    ai.write_text(path, json.dumps({"type": "item.completed", "item": {
        "type": "reasoning", "payload": {"tool_calls": [{"name": "file-read"}]}}})
        + '\n{"type":"turn.completed"}\n')
    assert not ai.audit_events(path)["valid"]


@pytest.mark.parametrize("config", [
    'model = "gpt-6-astra"\n',
    'model = "allowed-default"\nprofile = "excluded"\n'
    '[profiles.excluded]\nmodel = "gpt-6-astra"\n',
])
def test_excluded_default_and_profile(directory, monkeypatch, config):
    ai.write_text(directory / "config.toml", config)
    monkeypatch.setenv("CODEX_HOME", str(directory))
    with pytest.raises(ValueError, match="gpt-6-astra"):
        ai.default_model_guard()


def test_run_timeout_is_invalid_without_calling_codex(directory, monkeypatch):
    install_source(directory, "과학 평가계획\n1학년 1학기\n관찰 보고서\n")
    ai.build_targets(directory, ROUND)
    monkeypatch.setattr(ai, "isolated_directory", lambda path: directory)
    monkeypatch.setattr(ai, "default_model_guard", lambda: None)

    def simulated_timeout(command, **kwargs):
        assert kwargs["timeout"] == 900
        assert kwargs["input"] and kwargs["cwd"] == directory
        kwargs["stdout"].write('{"type":"turn.started"}\n')
        raise ai.subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(ai.subprocess, "run", simulated_timeout)
    result = ai.run_targets(directory, ROUND, directory)
    assert result["valid"] == 0
    assert result["results"][0]["failure"] == "호출 실패 TimeoutExpired"


def test_isolation_and_blind_guards(directory):
    with pytest.raises(ValueError, match="workspace"):
        ai.isolated_directory(PROJECT)
    with pytest.raises(ValueError):
        ai.isolated_directory(directory)
    for key in ("../escape", "2026-round-1-gold", "gold"):
        with pytest.raises(ValueError):
            ai.round_dir(directory, key)
    for path in ("data/gold/never-open", "docs/gold/no", "data/derived/round-gold/file",
                 "data/.gold-before-acl-fix/file"):
        with pytest.raises(ValueError):
            ai.read_json(directory / path)


@pytest.mark.parametrize("round_key", ai.DEV_ROUNDS)
def test_evaluate_fake_end_to_end_preserves_rule_hash(directory, monkeypatch, round_key):
    monkeypatch.setitem(globals(), "ROUND", round_key)
    conversion, _, tasks = verified_tasks()
    install_source(directory, conversion["text"])
    ai.build_targets(directory, ROUND)
    output = ai.round_dir(directory, ROUND)
    target = ai.load_targets(output)[0]
    _, _, base = source(conversion["text"])
    response_tasks = []
    for task in tasks:
        response_tasks.append({**base, "title": task["title"], "title_line": task["title_line"],
                               "evidence": [{"line_start": task["title_line"],
                                             "line_end": task["title_line"],
                                             "quote": task["title"]}]})
    fake = fake_files(directory, [target], {"tasks": response_tasks, "uncertain": []})
    monkeypatch.setattr(ai, "isolated_directory", lambda path: directory)
    ai.run_targets(directory, ROUND, directory, fake_responses=fake)
    verified = ai.verify_targets(directory, ROUND)
    assert len(verified["kept"]) == 2
    rules = {"schema_version": 1, "round": ROUND, "items": [rule_item(verified["kept"][0])]}
    rules_path = directory / f"data/derived/items/{ROUND}.json"
    ai.save_json(rules_path, rules)
    original_hash = ai.sha(rules_path.read_text(encoding="utf-8"))
    merged = ai.merge_targets(directory, ROUND)
    assert merged["ai_read_summary"]["added_items"] == 1
    assert ai.sha(rules_path.read_text(encoding="utf-8")) == original_hash
    prefix = directory / "docs/dev/2026-11-09-s6d2"
    ai.save_json(prefix.with_name(prefix.name + "-review-sample.json"), {"source_review": [{
        "cell_id": "S01", "round": ROUND, "school": "가상중학교", "grade": 1, "semester": 1,
        "source_documents": [{"converted_path": tasks[0]["converted_path"]}]}]})
    ai.write_text(prefix.with_name(prefix.name + "-astra-review.md"),
                  "### S01 가상중학교\n| 제목 | 번호 | 만점 | 비율 | 시기 | 코드 | 근거 |\n"
                  "| 관찰 보고서 | — | — | — | — | — | 2 |\n"
                  "| 실험 보고서 | — | — | — | — | — | 3 |\n")
    ai.write_text(prefix.with_name(prefix.name + "-check.md"),
                  "| S01 가상 | 2 | 1 | 1 | 1 | 0 | 총괄 합성 판정 |\n")
    evaluation = ai.evaluate_targets(directory, ROUND)
    assert evaluation["totals"]["ai"]["found"] == 2
    assert evaluation["totals"]["ai"]["precision"] == 1
    assert evaluation["totals"]["bounded"]["found"] == 1
    assert evaluation["totals"]["union"]["found"] == 2
    assert evaluation["cells"][0]["chief"]["reference_count"] == 2
    assert len(evaluation["differences"]) == 1
    assert not evaluation["chief_confirmation"]
    assert (output / "evaluation.md").exists()
    assert evaluation["simulated"]
    ai.write_text(prefix.with_name(prefix.name + "-check.md"),
                  "| S01 가상 | 3 | 1 | 1 | 2 | 0 | 총괄이 참고 개수 수정 |\n")
    priority = ai.evaluate_targets(directory, ROUND)
    assert priority["totals"]["ai"]["reference"] == 3
    assert priority["chief_confirmation"][0]["kind"] == "총괄 판정 차이"
    status_path = output / f"responses/{target['target_id']}.status.json"
    status = ai.read_json(status_path)
    status["answer_sha256"] = "stale"
    ai.save_json(status_path, status)
    with pytest.raises(ValueError, match="응답이 변경됨"):
        ai.merge_targets(directory, ROUND)


def test_verify_outside_scope_and_stale_conversion(directory, monkeypatch):
    text = "과학 평가계획\n3학년 1학기\n관찰 보고서\n"
    install_source(directory, text)
    ai.build_targets(directory, ROUND)
    output = ai.round_dir(directory, ROUND)
    target = ai.load_targets(output)[0]
    _, _, task = source(text)
    task.update({"grade": 3, "title": "관찰 보고서", "title_line": 3,
                 "grade_evidence": {"line": 2, "quote": "3학년"},
                 "semester_evidence": {"line": 2, "quote": "1학기"},
                 "evidence": [{"line_start": 3, "line_end": 3, "quote": "관찰 보고서"}]})
    fake = fake_files(directory, [target], {"tasks": [task], "uncertain": []})
    monkeypatch.setattr(ai, "isolated_directory", lambda path: directory)
    ai.run_targets(directory, ROUND, directory, fake_responses=fake)
    verified = ai.verify_targets(directory, ROUND)
    assert len(verified["out_of_scope"]) == 1 and not verified["kept"]
    ai.save_json(directory / target["converted_path"], {"text": "changed"})
    with pytest.raises(ValueError, match="해시"):
        ai.verify_targets(directory, ROUND)
