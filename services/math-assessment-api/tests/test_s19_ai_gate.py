"""Verify science warning/privacy/AI publication gates using persisted synthetic inputs.

Run: .venv/Scripts/python.exe -m pytest -q
     services/math-assessment-api/tests/test_s19_ai_gate.py
"""

import csv
import json
import os
import sqlite3
import subprocess
import sys
import zlib
from pathlib import Path

import pytest
from scripts import science_card_check as check
from scripts import science_rules as rules

ROOT = Path(__file__).resolve().parents[3]
TITLE = "·동물세포, 식물세포를 관찰하고 탐구하기"


def database(tmp_path, title=TITLE, codes=("[9과010-02]", "[9과11-01]"), extra=""):
    path = tmp_path / "science.sqlite"
    source = f"<table><tr><td>{title}</td><td>{' '.join(codes)} {extra}</td></tr></table>"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE cases (case_id TEXT, school_name TEXT, source_sha256 TEXT);
            CREATE TABLE assessment_items (
                item_id TEXT, case_id TEXT, extraction_status TEXT, title TEXT,
                title_basis TEXT, standards_json TEXT, source_html_zlib BLOB,
                rubric_html_zlib BLOB, locator TEXT, method TEXT, item_order INTEGER,
                grade INTEGER, semester INTEGER, task_no TEXT, score TEXT, weight TEXT,
                timing TEXT, source_html_char_count INTEGER);
        """)
        db.execute("INSERT INTO cases VALUES ('case', '가상학교', 'source-hash')")
        db.execute("INSERT INTO assessment_items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "card", "case", "bounded", title, "section", json.dumps(codes),
            zlib.compress(source.encode()), zlib.compress(b""),
            json.dumps({"start": 0, "end": len(source), "sha256": "fragment-hash"}),
            "관찰", 1, 1, 1, "1", "100", "30", "5월", len(source),
        ))
    return path


def invoke(tmp_path, db, script, extra=()):
    output, queue = tmp_path / "report.json", tmp_path / "queue.csv"
    flag = "--summary" if "titles_full" in script else "--output"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), "--database", str(db),
         flag, str(output), "--queue", str(queue), *extra],
        cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert output.is_file(), result.stderr
    with queue.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return result, json.loads(output.read_text(encoding="utf-8")), rows


@pytest.mark.parametrize("script", ["audit_math_assessment_publication_gate.py",
                                    "audit_math_assessment_titles_full.py"])
def test_b3_is_warning_and_publication_passes(tmp_path, script):
    result, report, rows = invoke(tmp_path, database(tmp_path), script)
    assert result.returncode == 0, result.stderr
    assert report["passed"] and report["blocking_public_items"] == 0
    assert len(rows) == 1
    assert rows[0]["blocking_codes"] == "B3" and rows[0]["severity"] == "warning"
    if "item_counts" in report:
        assert report["item_counts"]["blocking_public_item"] == 0
        assert report["case_counts"]["blocking_public_case"] == 0


@pytest.mark.parametrize("codes,blocked", [
    (("[9국01-01]",), True),
    (("[9과010-02]", "[9과11-01]"), False),
    (("[9과학01-01]",), True),
    (("[9과0010-02]",), True),
    (("[9과010-2]",), True),
])
def test_b1_normalizes_exactly_one_extra_zero(tmp_path, codes, blocked):
    result, report, rows = invoke(tmp_path, database(tmp_path, codes=codes),
                                  "audit_math_assessment_publication_gate.py")
    blocking = [row for row in rows if row["severity"] == "blocking"]
    assert (result.returncode == 1) == blocked
    assert report["blocking_public_items"] == int(blocked)
    assert any("B1" in row["blocking_codes"].split("|") for row in blocking) == blocked
    if not blocked:
        assert "B5" not in rules.blocking_errors(rules.public_items(tmp_path / "science.sqlite")[0])


@pytest.mark.parametrize("field", ["source_html_zlib", "rubric_html_zlib", "title", "method"])
@pytest.mark.parametrize("value", ["010-1234-5678", "901010-1234567", "test@example.com"])
def test_b6_blocks_personal_data_in_each_public_field(tmp_path, field, value):
    db = database(tmp_path)
    stored = zlib.compress(f"<p>{value}</p>".encode()) if field.endswith("_zlib") else value
    with sqlite3.connect(db) as connection:
        connection.execute(f"UPDATE assessment_items SET {field}=?", (stored,))
    result, report, rows = invoke(tmp_path, db, "audit_math_assessment_publication_gate.py")
    assert result.returncode == 1
    assert report["blocking_public_items"] == 1
    blocking = [row for row in rows if row["severity"] == "blocking"]
    assert len(blocking) == 1 and "B6" in blocking[0]["blocking_codes"].split("|")
    assert value not in blocking[0]["reasons"]


def verdict(**changes):
    return {"item_id": "card", "checked": True, "quote": TITLE, "is_task": True,
            "not_task_kind": None, "duplicate_of": None, "merged": False, "evidence": [],
            **changes}


@pytest.mark.parametrize("judgment,codes", [
    (None, ["AI0:unchecked"]),
    (verdict(checked=False), ["AI0:unchecked"]),
    (verdict(quote=None), ["AI0:unchecked"]),
    (verdict(), []),
    (verdict(is_task=False, not_task_kind="방법칸"), ["AI1:not_task:방법칸"]),
    (verdict(duplicate_of="other"), ["AI2:duplicate_of:other"]),
    (verdict(merged=True), ["AI3:merged"]),
])
def test_exclusions_and_ai_audit_share_fail_closed_gate(tmp_path, monkeypatch, judgment, codes):
    db = database(tmp_path)
    report = {"cards": [judgment] if judgment is not None else []}
    monkeypatch.setattr(check, "verify_targets", lambda *_: report)
    destination = tmp_path / "excluded.csv"
    result = check.write_exclusions(tmp_path, db, destination)
    with destination.open(encoding="utf-8-sig", newline="") as stream:
        excluded = list(csv.DictReader(stream))
    assert result["excluded"] == int(bool(codes))
    if codes:
        assert excluded[0]["blocking_codes"].split(" | ") == codes
    verified = tmp_path / "verified.json"
    verified.write_text(json.dumps(report), encoding="utf-8")
    outcome, audit, rows = invoke(tmp_path, db, "audit_science_ai_gate.py",
                                  ["--verified", str(verified)])
    assert outcome.returncode == int(bool(codes)), outcome.stderr
    assert audit["blocking_public_items"] == int(bool(codes))
    if codes:
        assert rows[0]["blocking_codes"].split("|") == [code.split(":")[0] for code in codes]
        assert rows[0]["severity"] == "blocking"


def test_runner_optional_ai_gate_merges_codes_and_keeps_warnings_out(tmp_path, monkeypatch):
    from scripts import run_science_audits as runner

    def fake_run(command, **kwargs):
        flag = next(flag for flag in ("--report", "--summary", "--output") if flag in command)
        Path(command[command.index(flag) + 1]).write_text("{}", encoding="utf-8")
        if "--queue" in command:
            name = Path(command[1]).stem
            codes = {"audit_math_assessment_publication_gate": ["B6"],
                     "audit_science_ai_gate": ["AI0"],
                     "audit_math_assessment_titles_full": ["B3"]}.get(name, [])
            with Path(command[command.index("--queue") + 1]).open(
                "w", encoding="utf-8-sig", newline=""
            ) as stream:
                writer = csv.DictWriter(stream, fieldnames=rules.QUEUE_FIELDS)
                writer.writeheader()
                if codes:
                    writer.writerow({"item_id": "card", "blocking_codes": codes[0],
                                     "reasons": codes[0],
                                     "severity": "warning" if codes == ["B3"] else "blocking"})
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    verified = tmp_path / "verified.json"
    monkeypatch.setattr(sys, "argv", ["run_science_audits", "--database",
                                     str(tmp_path / "unused.sqlite"), "--out-dir",
                                     str(tmp_path / "out"), "--card-verified", str(verified)])
    assert runner.main() == 0
    report = json.loads((tmp_path / "out/summary.json").read_text(encoding="utf-8"))
    assert len(report["commands"]) == 7
    assert "--verified" in report["commands"][-1]["command"]
    with Path(report["risk_queue"]).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and rows[0]["blocking_codes"] == "B6|AI0"
