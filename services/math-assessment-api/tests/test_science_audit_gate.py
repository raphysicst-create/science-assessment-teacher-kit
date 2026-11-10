"""Exercise audit CLIs with synthetic science DBs; no waiver/history input exists.

Run: pytest -q services/math-assessment-api/tests/test_science_audit_gate.py
No audit accepts an exemption list or processing-history file. Unknown exemption
arguments are rejected by argparse; source diagnostics never authorize publication.
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
from scripts.build_math_assessment_demo import demo_records
from scripts.build_science_catalog_db import write_science_catalog
from scripts.promote_math_assessment_recovery_release import REQUIRED_REPORT_FIELDS

ROOT = Path(__file__).resolve().parents[3]
GATE = "audit_math_assessment_publication_gate.py"
POSITIVE_TITLES = [
    "화학 반응 전후 질량 측정 실험",
    "화학 변화와 물리 변화 구분 보고서",
    "화학 반응의 온도 변화 탐구",
    "화학 반응 모형 제작 보고서",
    "화학 반응의 기체 관찰 실험",
]
NEGATIVE_TITLES = [
    "수학 함수 탐구 보고서",
    "화학 반응과 도덕 토론 보고서",
    "국어 독서 감상문 쓰기",
    "체육 줄넘기 실기",
    "기술 가정 제품 설계 보고서",
]
NEGATIVE_CODES = ["[9수01-01]", "[9과03-01] [9도01-02]", "", "", "[9기가02-01]"]


def database(tmp_path, negative=False):
    """Reuse the science writer's complete schema, then inject test-owned rows."""
    path = tmp_path / "science.sqlite"
    axes = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    with sqlite3.connect(path) as connection:
        write_science_catalog(connection, demo_records(), axes)
        connection.row_factory = sqlite3.Row
        template = dict(connection.execute("SELECT * FROM assessment_items LIMIT 1").fetchone())
        for table in (
            "assessment_item_methods",
            "assessment_item_axes",
            "assessment_item_rankings",
        ):
            connection.execute(f"DELETE FROM {table}")
        connection.execute("DELETE FROM assessment_items")
        for number, title in enumerate(NEGATIVE_TITLES if negative else POSITIVE_TITLES):
            codes = NEGATIVE_CODES[number] if negative else f"[9과03-0{number % 3 + 1}]"
            source = f"<table><tr><td>수행평가명</td><td>{title}</td></tr>"
            source += f"<tr><td>성취기준</td><td>{codes}</td></tr></table>"
            row = {
                **template,
                "item_id": f"test-{number}",
                "item_order": number + 1,
                "title": title,
                "title_raw": title,
                "title_basis": "section",
                "standards_json": json.dumps([codes], ensure_ascii=False),
                "source_html_zlib": zlib.compress(source.encode("utf-8")),
                "source_html_char_count": len(source),
            }
            columns = list(row)
            connection.execute(
                f"INSERT INTO assessment_items ({','.join(columns)}) "
                f"VALUES ({','.join('?' for _ in columns)})",
                [row[key] for key in columns],
            )
    return path


def invoke(tmp_path, db, script=GATE, extra=()):
    output, queue = tmp_path / f"{script}.json", tmp_path / f"{script}.csv"
    flag = (
        "--report"
        if "subject_alignment" in script
        else ("--summary" if "titles_full" in script else "--output")
    )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / script),
            "--database",
            str(db),
            flag,
            str(output),
            "--queue",
            str(queue),
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        check=False,
    )
    rows = list(csv.DictReader(queue.open(encoding="utf-8-sig", newline="")))
    report = json.loads(output.read_text(encoding="utf-8"))
    return result, report, rows


@pytest.mark.parametrize("script", [GATE, "audit_math_assessment_subject_alignment.py"])
def test_five_other_subject_items_fail_and_all_enter_risk_queue(tmp_path, script):
    result, report, rows = invoke(tmp_path, database(tmp_path, negative=True), script)
    rows = [row for row in rows if row["severity"] != "warning"]
    assert result.returncode == 1, result.stderr
    assert report["blocking_public_items"] == 5
    assert {row["item_id"] for row in rows} == {f"test-{i}" for i in range(5)}
    assert all({"B1", "B2"} & set(row["blocking_codes"].split("|")) for row in rows)
    assert all(row["severity"] == "blocking" for row in rows)


@pytest.mark.parametrize(
    "script",
    [
        GATE,
        "audit_math_assessment_subject_alignment.py",
        "audit_math_assessment_titles_full.py",
        "audit_math_assessment_table_structure.py",
    ],
)
def test_five_chemistry_items_pass_without_blocking_rows(tmp_path, script):
    result, report, rows = invoke(tmp_path, database(tmp_path), script)
    assert result.returncode == 0, result.stderr
    assert report["blocking_public_items"] == 0
    # Review titles and warning-only geometry remain visible without blocking publication.
    assert not [row for row in rows if row["severity"] == "blocking"]


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("locator", "B4"),
        ("hash", "B4"),
        ("rowspan", "B5"),
        ("invisible_title", "B3"),
        ("standards_only", "B1"),
        ("title_code_only", "B1"),
    ],
)
def test_single_mutation_blocks_or_warns_and_only_that_item_is_queued(tmp_path, mutation, expected):
    db = database(tmp_path)
    with sqlite3.connect(db) as connection:
        if mutation == "locator":
            connection.execute("UPDATE assessment_items SET locator='{}' WHERE item_id='test-2'")
        elif mutation == "hash":
            connection.execute(
                "UPDATE assessment_items SET locator=? WHERE item_id='test-2'",
                (json.dumps({"start": 0, "end": 10}),),
            )
        elif mutation == "standards_only":
            connection.execute(
                "UPDATE assessment_items SET standards_json=? WHERE item_id='test-2'",
                ('["[9수01-01]"]',),
            )
        elif mutation == "title_code_only":
            connection.execute(
                "UPDATE assessment_items SET title=title || '[9수01-01]' WHERE item_id='test-2'"
            )
        else:
            source = (
                "<table><tr><td rowspan='4'>화학 반응의 온도 변화 탐구</td></tr></table>"
                if mutation == "rowspan"
                else "<p>원문에 다른 제목만 있음</p>"
            )
            connection.execute(
                "UPDATE assessment_items SET source_html_zlib=? WHERE item_id='test-2'",
                (zlib.compress(source.encode("utf-8")),),
            )
    result, report, rows = invoke(tmp_path, db)
    assert result.returncode == int(expected != "B3"), result.stderr
    assert report["blocking_public_items"] == int(expected != "B3")
    if expected != "B3":
        rows = [row for row in rows if row["severity"] != "warning"]
    assert len(rows) == 1 and rows[0]["item_id"] == "test-2"
    assert expected in rows[0]["blocking_codes"].split("|")
    assert rows[0]["severity"] == ("warning" if expected == "B3" else "blocking")


def test_nonpublic_items_do_not_block(tmp_path):
    db = database(tmp_path)
    with sqlite3.connect(db) as connection:
        # Keep five public positives alongside five nonpublic negatives.
        connection.execute(
            "INSERT INTO assessment_items SELECT "
            "'private-' || item_id, "
            + ", ".join(
                "'review'" if row[1] == "extraction_status" else
                "'[9수01-01]'" if row[1] == "title" else
                "item_order + 5" if row[1] == "item_order" else row[1]
                for row in connection.execute("PRAGMA table_info(assessment_items)")
                if row[1] != "item_id"
            )
            + " FROM assessment_items"
        )
        connection.executemany(
            "UPDATE assessment_items SET title=?, standards_json=? WHERE item_id=?",
            [(title, json.dumps([codes]), f"private-test-{number}")
             for number, (title, codes) in enumerate(
                 zip(NEGATIVE_TITLES, NEGATIVE_CODES, strict=True))],
        )
    result, report, rows = invoke(tmp_path, db)
    assert result.returncode == 0 and not rows
    assert report["public_item_count"] == 5


@pytest.mark.parametrize("empty", [True, False])
def test_no_public_items_fails_audits_and_runner(tmp_path, empty):
    db = database(tmp_path)
    with sqlite3.connect(db) as connection:
        if empty:
            for table in ("assessment_item_methods", "assessment_item_axes",
                          "assessment_item_rankings", "assessment_items"):
                connection.execute(f"DELETE FROM {table}")
        else:
            connection.execute("UPDATE assessment_items SET extraction_status='review'")
    for script in (GATE, "audit_math_assessment_subject_alignment.py"):
        result, report, rows = invoke(tmp_path, db, script)
        assert result.returncode == 1, result.stderr
        assert not report["passed"] and report["errors"] == ["no_public_items"]
        assert report["public_item_count"] == 0 and not rows
    output = tmp_path / "out"
    expectations = tmp_path / "axes.json"
    expectations.write_text('{"items": []}', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_science_audits.py"),
         "--database", str(db), "--out-dir", str(output),
         "--axes-json", str(expectations)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    )
    assert result.returncode == 1, result.stderr
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert not summary["passed"]
    for name in ("publication", "subject"):
        assert next(row for row in summary["commands"] if row["name"] == name)["exit_code"] == 1
        report = json.loads((output / f"{name}.json").read_text(encoding="utf-8"))
        assert report["errors"] == ["no_public_items"]


@pytest.mark.parametrize("field", ["source_html_zlib", "rubric_html_zlib"])
@pytest.mark.parametrize("script", [GATE, "audit_math_assessment_table_structure.py"])
def test_escaped_single_row_table_is_restored_before_b5(tmp_path, field, script):
    db = database(tmp_path)
    source = ("<p>&lt;tr&gt;&lt;td rowspan=4&gt;화학 반응의 온도 변화 탐구 "
              "[9과03-01]&lt;/td&gt;&lt;/tr&gt;</p>")
    with sqlite3.connect(db) as connection:
        connection.execute(
            f"UPDATE assessment_items SET {field}=? WHERE item_id='test-2'",
            (zlib.compress(source.encode("utf-8")),),
        )
    result, report, rows = invoke(tmp_path, db, script)
    assert result.returncode == 1, result.stderr
    assert report["blocking_public_items"] == 1
    assert len(rows) == 1 and rows[0]["blocking_codes"] == "B5"
    assert "rowspan_overflows_table" in rows[0]["reasons"]


def test_no_processing_or_waiver_file_can_exempt_an_item(tmp_path):
    db = database(tmp_path, negative=True)
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE manual_approvals (item_id TEXT)")
        connection.executemany(
            "INSERT INTO manual_approvals VALUES (?)", [(f"test-{i}",) for i in range(5)]
        )
    result, _, rows = invoke(tmp_path, db)
    rows = [row for row in rows if row["severity"] != "warning"]
    assert result.returncode == 1 and len(rows) == 5


def test_missing_evidence_locator_is_blocking_even_with_valid_item_locator(tmp_path):
    db = database(tmp_path)
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO assessment_item_methods VALUES (?, ?, ?, ?, ?)",
                           ("test-2", "관찰", "plain", "", "{}"))
    result, _, rows = invoke(tmp_path, db)
    assert result.returncode == 1
    assert len(rows) == 1 and rows[0]["blocking_codes"] == "B4"


@pytest.mark.parametrize("script", [GATE, "audit_math_assessment_table_structure.py"])
def test_warning_geometry_does_not_block_but_invalid_span_does(tmp_path, script):
    db = database(tmp_path)
    source = ("<table><tr><td colspan='14'>화학 반응의 온도 변화 탐구 "
              "[9과03-01]</td></tr></table>")
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='test-2'",
                           (zlib.compress(source.encode("utf-8")),))
    result, report, rows = invoke(tmp_path, db, script)
    assert result.returncode == 0
    assert not [row for row in rows if row["severity"] == "blocking"]
    if script != GATE:
        assert report["warning_flag_counts"]["very_wide_table"] == 1
        assert report["blocking_flag_count"] == 0
        assert len(rows) == 1 and rows[0]["severity"] == "warning"
        assert "very_wide_table" in rows[0]["reasons"]
    source = source.replace("colspan='14'", "colspan='bad'")
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE assessment_items SET source_html_zlib=? WHERE item_id='test-2'",
                           (zlib.compress(source.encode("utf-8")),))
    result, _, rows = invoke(tmp_path, db, script)
    assert result.returncode == 1
    assert len(rows) == 1 and rows[0]["blocking_codes"] == "B5"


@pytest.mark.parametrize(
    "standards",
    [
        ["[9수01-01]"],
        ["[12수학01-01]"],
        ["[10공수1-01-01]"],
        ["[9과03-01]", "[12국어01-01]"],
        ["[12물리01-01]"],
        ["[12물리Ⅰ01-01]"],
        ["[12수학Ⅰ01-01]"],
    ],
)
def test_json_escaped_and_other_school_level_standards_block(tmp_path, standards):
    db = database(tmp_path)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE assessment_items SET standards_json=? WHERE item_id='test-2'",
            (json.dumps(standards),),
        )
    result, report, rows = invoke(tmp_path, db)
    assert result.returncode == 1, result.stderr
    assert report["blocking_public_items"] == 1
    assert len(rows) == 1 and rows[0]["item_id"] == "test-2"
    assert rows[0]["severity"] == "blocking"
    assert "B1" in rows[0]["blocking_codes"].split("|")


@pytest.mark.parametrize("raw", ['["[9수01-01]"', "broken", '{"code": "[9과03-01]"}'])
def test_invalid_standards_json_retains_b1_reason(tmp_path, raw):
    db = database(tmp_path)
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE assessment_items SET standards_json=? WHERE item_id='test-2'", (raw,)
        )
    result, _, rows = invoke(tmp_path, db)
    assert result.returncode == 1
    assert len(rows) == 1 and "B1:invalid_standards_json" in rows[0]["reasons"]


@pytest.mark.parametrize(
    ("title", "basis", "severity"),
    [
        # Fixed legacy queue inputs, independent of the original audit implementation.
        ("물질의 성질", "heading", "review"),
        ("물질의 성질", "context", "review"),
        ("물질의 성질 탐구", "unverified", "review"),
        ("평가 결과 분석 및 활용", "heading", "warning"),
        ("탐구 과정이 적절한가?", "table", "warning"),
    ],
)
def test_legacy_title_queue_inputs_keep_their_severity(tmp_path, title, basis, severity):
    db = database(tmp_path)
    source = f"<h3>{title}</h3><p>[9과03-01]</p>"
    with sqlite3.connect(db) as connection:
        connection.execute(
            "UPDATE assessment_items SET title=?, title_basis=?, source_html_zlib=? "
            "WHERE item_id='test-2'",
            (title, basis, zlib.compress(source.encode("utf-8"))),
        )
    result, report, rows = invoke(tmp_path, db, "audit_math_assessment_titles_full.py")
    assert result.returncode == int(severity == "blocking"), result.stderr
    assert report["blocking_public_items"] == int(severity == "blocking")
    assert len(rows) == 1 and rows[0]["severity"] == severity
    assert "no_task_signal" in rows[0]["reasons"] or severity == "warning" or basis == "unverified"


def promotion_inputs(tmp_path, db, gate_path):
    """Keep unrelated legacy release reports synthetic; use real science gate output."""
    with sqlite3.connect(db) as connection:
        cases = connection.execute("SELECT case_id FROM cases").fetchall()
        # The injection helper intentionally clears rankings. Restore them for promotion.
        connection.execute(
            "INSERT INTO assessment_item_rankings "
            "SELECT item_id, 'experiment', 1, '[]' FROM assessment_items"
        )
    base = tmp_path / "base.sqlite"
    with sqlite3.connect(base) as connection:
        connection.execute("CREATE TABLE cases (case_id TEXT PRIMARY KEY)")
        connection.executemany("INSERT INTO cases VALUES (?)", cases)
    reports = {
        "base-manifest": {},
        "detail-manifest": {},
        "title-audit": {"passed": True, "blocking_public_items": 0},
        "subject-audit": {"passed": True, "blocking_public_items": 0},
        "detail-audit": {"gates": {"synthetic_fixture": True}},
        "recovery-table-audit": {"blocking_public_items": 0, "warning_items": 0},
        "combined-table-audit": {"blocking_public_items": 0, "warning_items": 0},
        "completeness-summary": {"checks": {"synthetic_fixture": True}},
    }
    arguments = ["--base-db", str(base), "--detail-db", str(db)]
    for name, report in reports.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        arguments += [f"--{name}", str(path)]
    return [
        *arguments,
        "--publication-gate", str(gate_path),
        "--publish-dir", str(tmp_path / "promoted"),
    ]


@pytest.mark.parametrize(
    "failure", [None, "database", "fresh_blocker", "report", "item_count", "case_count",
                "table_warning"]
)
def test_promotion_checks_new_gate_report_and_database(tmp_path, failure):
    db = database(tmp_path)
    result, report, _ = invoke(tmp_path, db)
    assert result.returncode == 0
    assert report["item_counts"] == {"confirmed_public_item": 5, "blocking_public_item": 0}
    assert report["case_counts"] == {"confirmed_public_case": 1, "blocking_public_case": 0}
    assert list(report["per_case_counts"].values()) == [{"public_items": 5, "blocking_items": 0}]
    gate_path = tmp_path / f"{GATE}.json"
    arguments = promotion_inputs(tmp_path, db, gate_path)
    if failure in {"database", "fresh_blocker"}:
        with sqlite3.connect(db) as connection:
            connection.execute("UPDATE assessment_items SET locator='{}' WHERE item_id='test-2'")
        if failure == "fresh_blocker":
            audit_result, blocked, _ = invoke(tmp_path, db)
            assert audit_result.returncode == 1
            assert blocked["item_counts"]["blocking_public_item"] == 1
            assert blocked["case_counts"]["blocking_public_case"] == 1
            assert list(blocked["per_case_counts"].values()) == [
                {"public_items": 5, "blocking_items": 1}
            ]
    elif failure == "table_warning":
        # Obtain a real warning-only audit, rather than imitating its JSON shape.
        with sqlite3.connect(db) as connection:
            source = ("<table><tr><td colspan='14'>화학 반응의 온도 변화 탐구 "
                      "[9과03-01]</td></tr></table>")
            connection.execute(
                "UPDATE assessment_items SET source_html_zlib=? WHERE item_id='test-2'",
                (zlib.compress(source.encode("utf-8")),),
            )
        audit_result, table_report, _ = invoke(
            tmp_path, db, "audit_math_assessment_table_structure.py"
        )
        assert audit_result.returncode == 0 and table_report["warning_items"] == 1
        (tmp_path / "recovery-table-audit.json").write_text(
            json.dumps(table_report), encoding="utf-8"
        )
    elif failure:
        if failure == "report":
            report.update(passed=False, blocking_public_items=1)
        elif failure == "item_count":
            report["item_counts"]["blocking_public_item"] = 1
        else:
            report["case_counts"]["blocking_public_case"] = 1
        gate_path.write_text(json.dumps(report), encoding="utf-8")
    # Adapt only the historical release size constants to this five-item fixture.
    code = (
        "from scripts import promote_math_assessment_recovery_release as p; "
        "p.EXPECTED.update(cases=2, items=5, public_cases=1, public_items=5); p.main()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, *arguments],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"), check=False,
    )
    assert result.returncode == int(failure is not None), (result.stdout, result.stderr)
    if failure == "table_warning":
        assert "recovery release still has structural table flags" in result.stderr
    promoted = tmp_path / "promoted/math_assessment_catalog_detail.sqlite"
    assert promoted.exists() == (failure is None)


@pytest.mark.parametrize(
    ("name", "script"),
    [
        ("publication", GATE),
        ("subject", "audit_math_assessment_subject_alignment.py"),
        ("title", "audit_math_assessment_titles_full.py"),
        ("table", "audit_math_assessment_table_structure.py"),
        ("detail", "audit_math_assessment_detail_db.py"),
    ],
)
def test_real_audit_reports_satisfy_promotion_contract(tmp_path, name, script):
    db = tmp_path / "clean.sqlite"
    axes = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    with sqlite3.connect(db) as connection:
        write_science_catalog(connection, demo_records(), axes)
    result, report, _ = invoke(tmp_path, db, script)
    assert result.returncode == 0, (result.stderr, report)
    for field in REQUIRED_REPORT_FIELDS[name]:
        value = report
        for key in field.split("."):
            assert key in value, (name, field, report)
            value = value[key]


@pytest.mark.parametrize(
    ("name", "field"),
    [(name, field) for name, fields in REQUIRED_REPORT_FIELDS.items() for field in fields],
)
def test_promotion_refuses_every_missing_required_report_field(tmp_path, name, field):
    db = database(tmp_path)
    result, _, _ = invoke(tmp_path, db)
    assert result.returncode == 0
    arguments = promotion_inputs(tmp_path, db, tmp_path / f"{GATE}.json")
    flag = {
        "publication": "--publication-gate", "title": "--title-audit",
        "subject": "--subject-audit", "detail": "--detail-audit",
        "table": "--recovery-table-audit", "completeness": "--completeness-summary",
    }[name]
    path = Path(arguments[arguments.index(flag) + 1])
    report = json.loads(path.read_text(encoding="utf-8"))
    parent = report
    keys = field.split(".")
    for key in keys[:-1]:
        parent = parent[key]
    del parent[keys[-1]]
    path.write_text(json.dumps(report), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/promote_math_assessment_recovery_release.py"),
         *arguments],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
    )
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert f"report missing field: {name}.{field}" in result.stderr
    assert not (tmp_path / "promoted").exists()


def test_runner_combines_only_blocking_severity(tmp_path, monkeypatch):
    from scripts import run_science_audits as runner
    from scripts.science_rules import QUEUE_FIELDS

    def fake_run(command, **kwargs):
        flag = next(flag for flag in ("--report", "--summary", "--output") if flag in command)
        Path(command[command.index(flag) + 1]).write_text("{}", encoding="utf-8")
        if "--queue" in command:
            queue = Path(command[command.index("--queue") + 1])
            with queue.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS)
                writer.writeheader()
                for severity in ("blocking", "review", "warning"):
                    writer.writerow({
                        "item_id": severity, "severity": severity,
                        # Codes alone must never turn review/warning into blocking.
                        "blocking_codes": "B3",
                    })
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    report = runner.run(tmp_path / "unused.sqlite", tmp_path / "reports")
    with Path(report["risk_queue"]).open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert report["blocking_public_items"] == 1
    assert len(rows) == 1 and rows[0]["item_id"] == "blocking"


def test_runner_continues_after_failure_and_writes_only_to_out_dir(tmp_path, monkeypatch):
    from scripts import run_science_audits as runner

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        flag = (
            "--report"
            if "--report" in command
            else ("--summary" if "--summary" in command else "--output")
        )
        Path(command[command.index(flag) + 1]).write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1 if len(calls) == 1 else 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    report = runner.run(tmp_path / "input.sqlite", tmp_path / "reports")
    assert not report["passed"] and len(calls) == 6
    assert "--profile" in calls[0] and "science" in calls[0]
    assert all("check-mobile-overflow" not in " ".join(command) for command in calls)
    assert (tmp_path / "reports/summary.json").is_file()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["reports"]


def test_complete_runner_on_independent_synthetic_search_expectations(tmp_path):
    db = tmp_path / "demo.sqlite"
    records = demo_records()
    axes = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    with sqlite3.connect(db) as connection:
        write_science_catalog(connection, records, axes)
    expectations = tmp_path / "axes.json"
    expectations.write_text(json.dumps({"items": [
        {"item_id": record["item"]["item_id"], "grade": record["item"]["grade"],
         **record["axes"]} for record in records
    ]}, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_science_audits.py"),
         "--database", str(db), "--out-dir", str(tmp_path / "out"),
         "--axes-json", str(expectations)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"), check=False,
    )
    summary = json.loads((tmp_path / "out/summary.json").read_text(encoding="utf-8"))
    assert result.returncode == 0, (result.stdout, result.stderr, summary)
    assert summary["passed"] and len(summary["commands"]) == 6
    assert summary["blocking_public_items"] == 0
    for script in ("audit_math_assessment_detail_db.py",
                   "audit_math_assessment_release_precision.py"):
        audit_result, report, rows = invoke(tmp_path, db, script)
        assert audit_result.returncode == 0, (audit_result.stderr, report)
        assert report["blocking_public_items"] == 0 and not rows
    with sqlite3.connect(db) as connection:
        changed_id = connection.execute(
            "SELECT item_id FROM assessment_items LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "UPDATE assessment_items SET locator='{}' WHERE item_id=?", (changed_id,)
        )
    for script in ("audit_math_assessment_detail_db.py",
                   "audit_math_assessment_release_precision.py"):
        audit_result, report, rows = invoke(tmp_path, db, script)
        assert audit_result.returncode == 1, (audit_result.stderr, report)
        assert len(rows) == 1 and rows[0]["blocking_codes"] == "B4"
