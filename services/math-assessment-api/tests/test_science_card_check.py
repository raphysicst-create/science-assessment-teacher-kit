"""Synthetic offline card checking and publication exclusion regressions.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_science_card_check.py
Verify .venv/Scripts/python.exe -m ruff check
    services/math-assessment-api/tests/test_science_card_check.py
"""

import csv
import json
import sqlite3
import zlib

import pytest
from scripts import apply_science_publication_exclusions as exclusions
from scripts import middle_ai_read as ai
from scripts import science_card_check as check

SCHEMA = """
CREATE TABLE cases (case_id TEXT PRIMARY KEY, school_name TEXT, source_sha256 TEXT);
CREATE TABLE assessment_items (
    item_id TEXT PRIMARY KEY, case_id TEXT, grade INTEGER, semester INTEGER,
    title TEXT, task_no TEXT, score TEXT, weight TEXT, method TEXT, timing TEXT,
    item_order INTEGER, source_html_char_count INTEGER, source_html_zlib BLOB,
    extraction_status TEXT);
"""
SOURCES = {
    "detail": "<table><tr><td>온도 측정하기</td><td>100점</td></tr>"
              "<tr><td>변인을 통제하여 온도를 측정한다</td><td>30%</td></tr></table>",
    "other": "<p>생태 지도 만들기</p><p>80점 20%</p>",
    "summary": "<tr><td>온도 측정하기</td><td>100점</td><td>30%</td></tr>",
    "exam": "<p>지필평가 정기시험 계획 100점</p>",
}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("This test must use fake responses without Codex or network access")

    monkeypatch.setattr(ai.subprocess, "run", forbidden)
    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr(ai, "find_codex", forbidden)
    monkeypatch.setattr(ai, "default_model_guard", forbidden)
    # All temporary files stay under tmp_path even when pytest's base is in the repo.
    isolated = tmp_path / "empty"
    isolated.mkdir()
    monkeypatch.setattr(ai, "isolated_directory", lambda path: isolated)
    database = tmp_path / "science.sqlite"
    with sqlite3.connect(database) as db:
        db.executescript(SCHEMA)
        db.execute("INSERT INTO cases VALUES ('case', '가상학교', 'source-sha')")
        for order, (identity, source) in enumerate(SOURCES.items(), 1):
            db.execute("INSERT INTO assessment_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (identity, "case", 1, 1, identity, str(order), "100", "30", "실험", "5월",
                        order, len(source), zlib.compress(source.encode()), "bounded"))
    return {"database": database, "output": tmp_path / "out", "fake": tmp_path / "fake",
            "isolated": isolated, "csv": tmp_path / "exclusions.csv"}


def response():
    tasks = [{"card_id": identity, "is_task": True, "not_task_kind": None,
              "duplicate_of": None, "merged": False, "quote": ""} for identity in SOURCES]
    tasks[0].update(duplicate_of="summary", quote="온도 측정하기")
    tasks[1]["quote"] = "생태 지도 만들기"
    tasks[2]["quote"] = "온도 측정하기"
    tasks[3].update(is_task=False, not_task_kind="지필", quote="지필평가 정기시험 계획")
    return {"tasks": tasks, "uncertain": []}


def fake_run(workspace, answer=None, tool=False):
    check.build_targets(workspace["database"], workspace["output"])
    targets = ai.load_targets(workspace["output"])
    for target in targets:
        identity = target["target_id"]
        ai.save_json(workspace["fake"] / f"{identity}.json", answer or response())
        events = [{"type": "thread.started"}, {"type": "turn.started"},
                  {"type": "item.completed", "item": {"type": "agent_message"}},
                  {"type": "turn.completed"}]
        if tool:
            events.insert(2, {"type": "item.completed", "item": {"type": "command_execution"}})
        ai.write_text(workspace["fake"] / f"{identity}.events.jsonl",
                      "".join(json.dumps(event) + "\n" for event in events))
    return check.main(["run", "--out-dir", str(workspace["output"]), "--isolated-cwd",
                       str(workspace["isolated"]), "--fake-responses", str(workspace["fake"])])


def read_queue(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {row["item_id"]: row for row in csv.DictReader(stream)}


def test_pipeline_deterministic_reuse_and_detail_wins(workspace):
    args = ["--database", str(workspace["database"]), "--out-dir", str(workspace["output"])]
    assert check.main(["targets", *args]) == 0
    targets = ai.load_targets(workspace["output"])
    assert check.main(["targets", *args]) == 0
    assert ai.load_targets(workspace["output"]) == targets
    target = targets[0]
    prompt = ai.read_text(workspace["output"] / f"prompts/{target['target_id']}.md")
    assert ai.sha(prompt) == target["prompt_sha256"]
    assert target["target_id"] == ai.sha(prompt)[:16]
    assert "온도 측정하기 | 100점" in prompt
    assert fake_run(workspace) == 0
    assert fake_run(workspace, tool=True) == 0  # A saved valid response is reused.
    assert ai.read_json(workspace["output"] / "run.json")["skipped"] == 1
    assert check.main(["verify", *args]) == 0
    report = ai.read_json(workspace["output"] / "verified.json")
    cards = {card["item_id"]: card for card in report["cards"]}
    assert cards["detail"]["duplicate_of"] is None
    assert cards["summary"]["duplicate_of"] == "detail"
    assert cards["exam"]["is_task"] is False
    assert cards["other"]["quote"] == "생태 지도 만들기"
    assert report["summary"]["excluded"] == 2
    assert check.main(["exclusions", *args, "--out", str(workspace["csv"])]) == 0
    queue = read_queue(workspace["csv"])
    assert set(queue) == {"summary", "exam"}
    assert queue["summary"]["blocking_codes"] == "AI2:duplicate_of:detail"
    assert queue["exam"]["blocking_codes"] == "AI1:not_task:지필"
    assert queue["exam"]["reasons"] == "지필평가 정기시험 계획"
    assert all(row["severity"] == "blocking" for row in queue.values())


def test_bad_quotes_are_discarded_per_negative_decision(workspace):
    answer = response()
    answer["tasks"][1].update(is_task=False, merged=True, duplicate_of="detail",
                              quote="원문에 없는 구절")
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    assert report["summary"]["discarded_quote_mismatch"] == 3
    other = next(card for card in report["cards"] if card["item_id"] == "other")
    assert other["is_task"] and not other["merged"] and other["duplicate_of"] is None
    check.write_exclusions(workspace["output"], workspace["database"], workspace["csv"])
    assert read_queue(workspace["csv"])["other"]["blocking_codes"] == "AI0:unchecked"


def test_tool_events_invalidate_run_and_cached_audit(workspace):
    assert fake_run(workspace, tool=True) == 3
    report = check.verify_targets(workspace["output"], workspace["database"])
    assert report["summary"]["valid_targets"] == 0
    assert report["cards"] == []
    assert fake_run(workspace) == 0
    identity = ai.load_targets(workspace["output"])[0]["target_id"]
    path = workspace["output"] / f"responses/{identity}.events.jsonl"
    ai.write_text(path, ai.read_text(path) + json.dumps(
        {"type": "item.completed", "item": {"type": "mcp_tool_call"}}) + "\n")
    assert check.verify_targets(workspace["output"], workspace["database"])["cards"] == []


@pytest.mark.parametrize("duplicate", ["foreign", "other", ["detail"]])
def test_invalid_duplicate_references(workspace, duplicate):
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET grade=2 WHERE item_id='other'")
    answer = response()
    answer["tasks"][0].update(duplicate_of=duplicate)
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    detail = next(card for card in report["cards"] if card["item_id"] == "detail")
    assert detail["duplicate_of"] is None
    assert report["summary"]["discarded_invalid_duplicate"] >= 1


def test_ties_cycles_and_whitespace_quotes(workspace):
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET source_html_char_count=100")
    answer = response()
    answer["tasks"][2].update(duplicate_of="detail", quote="온도  측정하기")
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    duplicates = {card["item_id"]: card["duplicate_of"] for card in report["cards"]}
    assert duplicates == {"detail": None, "other": None, "summary": "detail", "exam": None}


def test_merged_drm_and_multiple_risk_queues(workspace, monkeypatch):
    answer = response()
    answer["tasks"][1].update(merged=True, quote="생태 지도 만들기")
    assert fake_run(workspace, answer) == 0
    check.write_exclusions(workspace["output"], workspace["database"], workspace["csv"])
    assert read_queue(workspace["csv"])["other"]["blocking_codes"] == "AI3:merged"
    drm = workspace["fake"] / "drm.json"
    ai.save_json(drm, {"source_sha256": ["source-sha"]})
    drm_csv = workspace["fake"] / "drm.csv"
    check.write_exclusions(workspace["output"], workspace["database"], drm_csv, drm)
    queue = read_queue(drm_csv)
    assert set(queue) == set(SOURCES)
    assert queue["detail"]["blocking_codes"] == "T4:unsupported_format"
    assert queue["detail"]["reasons"] == "검토(형식 미지원)"
    public = workspace["fake"] / "public.sqlite"
    report_path = workspace["fake"] / "applied.json"
    # Cover both repeated --risk-queue and multiple values following one flag.
    for queue_args in ([str(workspace["csv"]), str(drm_csv)],
                       [str(workspace["csv"]), "--risk-queue", str(drm_csv)]):
        monkeypatch.setattr("sys.argv", ["apply", "--source", str(workspace["database"]),
                            "--risk-queue", *queue_args, "--output", str(public),
                            "--report", str(report_path)])
        assert exclusions.main() == 0
        report = ai.read_json(report_path)
        assert report["excluded"] == 4
        assert report["public_bounded_after"] == 0
        assert report["remaining_bounded_blocking"] == 0
    report = exclusions.apply(workspace["database"], workspace["csv"], public, report_path)
    assert report["risk_queue"] == workspace["csv"].as_posix()
    assert report["excluded"] == 3 and report["public_bounded_after"] == 1
    with sqlite3.connect(workspace["database"]) as db:
        assert db.execute("SELECT COUNT(*) FROM assessment_items WHERE extraction_status='bounded'"
                          ).fetchone()[0] == 4


def test_stale_database_and_answer_tampering(workspace):
    assert fake_run(workspace) == 0
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET title='변경됨' WHERE item_id='detail'")
    report = check.verify_targets(workspace["output"], workspace["database"])
    assert report["cards"] == []
    assert report["summary"]["discarded_target_mismatch"] == 1
    assert fake_run(workspace) == 0
    identity = ai.load_targets(workspace["output"])[0]["target_id"]
    ai.save_json(workspace["output"] / f"responses/{identity}.json", response())
    # Identical bytes remain valid. Changing any answer bytes invalidates its stored hash.
    path = workspace["output"] / f"responses/{identity}.json"
    ai.write_text(path, ai.read_text(path) + "\n")
    assert check.verify_targets(workspace["output"], workspace["database"])["cards"] == []


def test_window_limits_and_html_text_only():
    source = ('<style>비공개</style><p>A &amp; B</p>'
              '<table><tr><td>실험</td><td>100점</td></tr></table>')
    assert check.visible_window(zlib.compress(source.encode())) == "A & B\n실험 | 100점"
    text = "가" * (check.WINDOW_CHARS + 20)
    window = check.visible_window(zlib.compress(text.encode()))
    assert window == text[:check.WINDOW_CHARS] + "…(생략)"


def test_cases_and_empty_targets(workspace):
    result = check.build_targets(workspace["database"], workspace["output"], ["missing"])
    assert result == {"targets": 0, "cards": 0}
    assert check.main(["run", "--out-dir", str(workspace["output"]), "--isolated-cwd",
                       str(workspace["isolated"]), "--fake-responses", str(workspace["fake"])]) == 0


def test_missing_fake_response_is_failure(workspace):
    check.build_targets(workspace["database"], workspace["output"])
    assert check.main(["run", "--out-dir", str(workspace["output"]), "--isolated-cwd",
                       str(workspace["isolated"]), "--fake-responses", str(workspace["fake"])]) == 3
    check.write_exclusions(workspace["output"], workspace["database"], workspace["csv"])
    queue = read_queue(workspace["csv"])
    assert set(queue) == set(SOURCES)
    assert all(row["blocking_codes"] == "AI0:unchecked" for row in queue.values())


def test_duplicate_chain_keeps_one_and_rejects_repeated_answers(workspace):
    answer = response()
    answer["tasks"][1].update(duplicate_of="summary")
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    duplicates = {card["item_id"]: card["duplicate_of"] for card in report["cards"]}
    assert duplicates["other"] == duplicates["summary"] == "detail"
    # Repeated, contradictory entries for one card cannot remove that card.
    answer["tasks"].append({**answer["tasks"][3], "is_task": True})
    identity = ai.load_targets(workspace["output"])[0]["target_id"]
    (workspace["output"] / f"responses/{identity}.status.json").unlink()
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    exam = next(card for card in report["cards"] if card["item_id"] == "exam")
    assert exam["is_task"] and not exam["checked"]


@pytest.mark.parametrize("title,cell,discarded", [
    ("과제 B", "과제B", True),
    ("생태 지도 만들기", "생태·지도 만들기!", True),
    ("생태 지도 만들기", "생태 지도 만들기 (100점)", True),
    ("생태 지도 만들기 보고서", "생태 지도 만들기", True),
    ("실험", "실험 보고서", False),
])
def test_merged_summary_row_uses_sibling_database_title(workspace, title, cell, discarded):
    quote = "온도 측정하기 | " + cell
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET title=? WHERE item_id='other'", (title,))
        db.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='detail'",
                   (zlib.compress(quote.encode()),))
    answer = response()
    answer["tasks"][0].update(duplicate_of=None, merged=True, quote=quote)
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    card = next(c for c in report["cards"] if c["item_id"] == "detail")
    assert card["merged"] is not discarded
    assert check.blocking_codes(card) == ([] if discarded else ["AI3:merged"])
    reasons = [e["reason"] for e in card["discarded"]]
    assert reasons == (["discarded_merged_sibling_row"] if discarded else [])
    assert all(e in report["discarded"] for e in card["discarded"])


def test_merged_own_cell_with_two_separate_scores_still_blocks(workspace):
    quote = "온도 측정 100점 + 기체 탐구 100점 | 별도 만점"
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='detail'",
                   (zlib.compress(quote.encode()),))
    answer = response()
    answer["tasks"][0].update(duplicate_of=None, merged=True, quote=quote)
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    card = next(c for c in report["cards"] if c["item_id"] == "detail")
    assert check.blocking_codes(card) == ["AI3:merged"]
    assert card["discarded"] == []


@pytest.mark.parametrize("scope", ["grade", "semester", "case_id"])
def test_merged_sibling_title_in_another_group_does_not_override(workspace, scope):
    quote = "온도 측정하기 | 생태 지도 만들기"
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("INSERT INTO cases VALUES ('second', '다른학교', 'second-sha')")
        db.execute(f"UPDATE assessment_items SET {scope}=? WHERE item_id!='detail'",
                   ("second" if scope == "case_id" else 2,))
        db.execute("UPDATE assessment_items SET title='생태 지도 만들기' WHERE item_id='other'")
        db.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='detail'",
                   (zlib.compress(quote.encode()),))
    answer = response()
    answer["tasks"][0].update(duplicate_of=None, merged=True, quote=quote)
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    card = next(c for c in report["cards"] if c["item_id"] == "detail")
    assert check.blocking_codes(card) == ["AI3:merged"]
    assert card["discarded"] == []


def test_sibling_row_discards_only_merged_decision(workspace):
    quote = "온도 측정하기 | 생태 지도 만들기"
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET title='생태 지도 만들기' WHERE item_id='other'")
        db.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='detail'",
                   (zlib.compress((quote * 5).encode()),))
    answer = response()
    answer["tasks"][0].update(is_task=False, not_task_kind="기타", duplicate_of="other",
                              merged=True, quote=quote)
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    cards = {c["item_id"]: c for c in report["cards"]}
    assert not cards["detail"]["is_task"] and not cards["detail"]["merged"]
    assert cards["other"]["duplicate_of"] == "detail"
    assert [e["reason"] for e in report["discarded"]] == ["discarded_merged_sibling_row"]


def test_summary_column_card_numeric_row_does_not_block(workspace):
    # N2 검수 변이: 요약표 열 카드(첫 줄이 이웃 카드 제목과 나란한 머리 행)는 자기 세부표가 없으므로
    # 요약표 숫자 줄("만점 | 100 | 100")을 합친 근거로 내도 막지 않는다.
    window = "온도 측정하기 | 생태 지도 만들기\n만점 | 100 | 100\n비율 | 20% | 20%"
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET title='생태 지도 만들기' WHERE item_id='other'")
        db.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='detail'",
                   (zlib.compress(window.encode()),))
    answer = response()
    answer["tasks"][0].update(duplicate_of=None, merged=True, quote="만점 | 100 | 100")
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    card = next(c for c in report["cards"] if c["item_id"] == "detail")
    assert check.blocking_codes(card) == []
    assert [e["reason"] for e in card["discarded"]] == ["discarded_merged_summary_column"]


@pytest.mark.parametrize("quote,discarded", [
    ("만점 | 100 | 100", True), ("비율 | 20% | (30%)", True), ("배점 | 40점 | 60점", True),
    ("만점 | 100", False), ("온도 측정 | 생태 지도 | 100", False),
])
def test_merged_score_only_row_does_not_block(workspace, quote, discarded):
    # N3(N2 재검수 ①): 요약표 → 과제별 요약표 → 세부표 순서라 창 첫 줄이 이웃 제목 머리 행이
    # 아니어도, 과제 이름 없이 점수만 있는 줄은 합친 근거가 아니다.
    window = "\n".join(["## 가. 온도 측정하기", quote, "채점 기준 | 상 | 중"])
    with sqlite3.connect(workspace["database"]) as db:
        db.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='detail'",
                   (zlib.compress(window.encode()),))
    answer = response()
    answer["tasks"][0].update(duplicate_of=None, merged=True, quote=quote)
    assert fake_run(workspace, answer) == 0
    report = check.verify_targets(workspace["output"], workspace["database"])
    card = next(c for c in report["cards"] if c["item_id"] == "detail")
    assert check.blocking_codes(card) == ([] if discarded else ["AI3:merged"])
    assert [e["reason"] for e in card["discarded"]] == (
        ["discarded_merged_score_row"] if discarded else [])


def test_score_only_row_shapes():
    assert check.score_only_row("| 비율 | 20% | (30%) |")
    assert not check.score_only_row("만점 100 100")  # not a table row
    assert not check.score_only_row("온도 측정 100점 + 기체 탐구 100점 | 별도 만점")
