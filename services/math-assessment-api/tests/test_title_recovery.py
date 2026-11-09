from scripts.audit_unresolved_math_assessment_titles import (
    TITLE_FRAGMENT_RE,
    candidate_rows,
    explicit_name_label,
    split_concatenated_titles,
)
from scripts.promote_recovered_math_assessment_titles import candidates_by_case
from scripts.propose_math_assessment_explicit_item_recovery import (
    source_course_identity_evidence,
)
from scripts.science_rules import science_exact_fields, subject_alignment, title_rejection


def test_assessment_task_field_is_an_explicit_title_field() -> None:
    """2022 plan tables use 평가 과제 for the original task name."""

    assert explicit_name_label("평가 과제")
    assert explicit_name_label("평가과제")
    # A long 수행 과제 cell frequently describes directions, not the title.
    assert not explicit_name_label("수행 과제")
    assert TITLE_FRAGMENT_RE.fullmatch("・포트폴리오")


def test_task_name_is_not_split_before_a_connective_continuation() -> None:
    title = "실험 모형 만들기 및 관찰하기"
    assert split_concatenated_titles(title) == [title]


def test_adjacent_complete_task_names_can_still_be_split() -> None:
    assert split_concatenated_titles("생태계 탐구하기 운동 분석하기") == [
        "생태계 탐구하기",
        "운동 분석하기",
    ]


def test_performance_task_cell_preserves_the_complete_source_value() -> None:
    value = "생태계 탐구하기 보고서 작성하기 발표하기"
    assert candidate_rows(f"수행 과제\t{value}") == [
        ("수행 과제", value, "table_row", 0)
    ]


def test_recovery_alignment_accepts_grade_course_separator_variant() -> None:
    assert subject_alignment("[ 9과 03 - 01 ]") == "target"
    assert subject_alignment("[9수01-01]") == "other"


def test_source_title_can_prove_a_specific_course_without_codes() -> None:
    assert source_course_identity_evidence(
        alignment="none",
        title="물리 법칙의 원리를 실험으로 탐구하기",
        subject="물리",
    )
    assert not source_course_identity_evidence(
        alignment="none",
        title="과학적 사실을 바탕으로 탐구하기",
        subject="과학",
    )
    assert not source_course_identity_evidence(
        alignment="other",
        title="생물의 구조를 관찰하기",
        subject="생물",
    )


def test_title_recovery_promotes_only_direct_source_verified_titles() -> None:
    audit = {
        "candidates": [
            {
                "case_id": "case-1",
                "candidate": "화학 반응 모형 제작 보고서",
                "confidence": "high",
                "detection": "table_row",
                "subject_alignment": "target",
                "explicit_name_label": True,
                "title_looks_complete": True,
                "other_subject_signal": False,
            },
            {
                "case_id": "case-1",
                "candidate": "화학 반응 모형 제작 보고서",
                "confidence": "high",
                "detection": "table_row",
                "subject_alignment": "target",
                "explicit_name_label": True,
                "title_looks_complete": True,
                "other_subject_signal": False,
            },
            {
                "case_id": "case-2",
                "candidate": "문학 비평문 작성",
                "confidence": "high",
                "detection": "table_row",
                "subject_alignment": "target",
                "explicit_name_label": True,
                "title_looks_complete": True,
                "other_subject_signal": True,
            },
            {
                "case_id": "case-3",
                "candidate": "수행평가 원문 구간",
                "confidence": "high",
                "detection": "table_row",
                "subject_alignment": "target",
                "explicit_name_label": True,
                "title_looks_complete": True,
                "other_subject_signal": False,
            },
            {
                "case_id": "case-4",
                "candidate": "표가 무너진 후보",
                "confidence": "review",
                "detection": "flattened_line",
                "subject_alignment": "none",
                "explicit_name_label": False,
                "title_looks_complete": False,
                "other_subject_signal": False,
            },
        ]
    }

    selected, skipped = candidates_by_case(audit)

    assert selected == {"case-1": ["화학 반응 모형 제작 보고서"]}
    assert skipped == {
        "missing_case_or_title": 1,
        "not_source_verified_high": 1,
        "other_subject_signal": 1,
    }


def test_recovery_fields_keep_neutral_values_and_normalize_science_codes() -> None:
    fields = science_exact_fields(
        "<table><tr><td>만점</td><td>20점</td></tr>"
        "<tr><td>성취기준</td><td>[ 9과 03 - 01 ] [9수01-01]</td></tr></table>"
    )
    assert fields["score"] == "20점"
    assert fields["standards"] == ["[9과03-01]"]


def test_release_promotion_exits_one_for_blocking_item(tmp_path) -> None:
    """A forged passing report cannot exempt an item or create release outputs."""
    import json
    import os
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path

    from scripts.build_math_assessment_demo import build_demo

    database = tmp_path / "detail.sqlite"
    build_demo(database, tmp_path / "axes.json")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE assessment_items SET locator = '{}' WHERE item_id = "
            "(SELECT item_id FROM assessment_items WHERE extraction_status = 'bounded' LIMIT 1)"
        )
    report = tmp_path / "passing.json"
    report.write_text(json.dumps({"passed": True, "blocking_public_items": 0}), encoding="utf-8")
    output = tmp_path / "publish"
    arguments = [
        sys.executable, "scripts/promote_math_assessment_recovery_release.py",
        "--detail-db", str(database), "--base-db", str(database),
        "--publish-dir", str(output),
    ]
    for flag in (
        "base-manifest", "detail-manifest", "title-audit", "subject-audit",
        "detail-audit", "publication-gate", "recovery-table-audit",
        "combined-table-audit", "completeness-summary",
    ):
        arguments.extend(["--" + flag, str(report)])
    result = subprocess.run(
        arguments, cwd=Path(__file__).resolve().parents[3], capture_output=True,
        text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"},
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "promotion blocked by science errors" in result.stderr
    assert "B4" in result.stderr
    assert not output.exists()


def test_recovery_preserves_subject_neutral_title_rejections() -> None:
    for title in (
        "관찰", "과학 탐구 준수 여부", "생태계 프로젝트 포트폴리오",
        "평가 횟수 (2)", "과학 탐구 [9과03-01] 보고서",
    ):
        assert title_rejection(title), title
