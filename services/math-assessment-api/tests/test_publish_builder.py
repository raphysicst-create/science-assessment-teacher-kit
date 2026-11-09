"""Check catalog transformations. Run with pytest on this file."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.build_math_assessment_demo import build_demo, demo_records
from scripts.build_math_assessment_publish_db import (
    assessment_category,
    assessment_structure,
    derive_task_names,
    normalize_task_name,
    plain_text,
    task_name_is_rejected,
)
from scripts.package_math_assessment_vercel_data import (
    assert_bounded_html_privacy,
    package_catalog,
)

ROOT = Path(__file__).resolve().parents[3]


def validate_science(database, output):
    return subprocess.run(
        [
            sys.executable, str(ROOT / "scripts/validate_math_assessment_publish_db.py"),
            "--profile", "science", "--database", str(database), "--output", str(output),
        ],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
    )


def test_science_demo_preserves_axes_and_abstention(tmp_path) -> None:
    database = tmp_path / "science.sqlite"
    build_demo(database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM assessment_items").fetchone()[0] == 4
        axes = connection.execute(
            "SELECT basis, evidence, locator, rule_version FROM assessment_item_axes"
        ).fetchall()
        assert axes
        for basis, evidence, locator, rule_version in axes:
            assert all((basis, evidence, locator, rule_version))
            assert {"start", "end", "sha256", "segment_id"} <= json.loads(locator).keys()
        for title, unit, activity in (
            ("열의 이동 실험", "03", "experiment"),
            ("전기 회로 발표", "14", "presentation"),
        ):
            rows = connection.execute(
                "SELECT a.axis, a.value FROM assessment_item_axes a "
                "JOIN assessment_items i USING (item_id) WHERE i.title = ? AND a.rank = 1",
                (title,),
            ).fetchall()
            assert dict(rows) == {"unit": unit, "activity": activity}
        abstentions = connection.execute(
            "SELECT item_id, activity_abstain_reason FROM assessment_items "
            "WHERE activity_abstain_reason != ''"
        ).fetchall()
        assert len(abstentions) == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM assessment_item_axes "
            "WHERE item_id = ? AND axis = 'activity' AND rank = 1", (abstentions[0][0],),
        ).fetchone()[0] == 0
    result = validate_science(database, tmp_path / "validation.json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((tmp_path / "validation.json").read_text(encoding="utf-8"))["passed"]


@pytest.mark.parametrize("missing_field", ["evidence", "sha256"])
def test_science_validation_rejects_missing_axis_evidence(tmp_path, missing_field) -> None:
    database = tmp_path / "mutation.sqlite"
    build_demo(database)
    with sqlite3.connect(database) as connection:
        if missing_field == "evidence":
            connection.execute(
                "UPDATE assessment_item_axes SET evidence = '' WHERE (item_id, axis, value) = "
                "(SELECT item_id, axis, value FROM assessment_item_axes LIMIT 1)"
            )
        else:
            item_id, axis, value, locator = connection.execute(
                "SELECT item_id, axis, value, locator FROM assessment_item_axes LIMIT 1"
            ).fetchone()
            parsed = json.loads(locator)
            parsed["sha256"] = ""
            connection.execute(
                "UPDATE assessment_item_axes SET locator = ? WHERE item_id = ? AND axis = ? "
                "AND value = ?", (json.dumps(parsed), item_id, axis, value),
            )
    result = validate_science(database, tmp_path / "mutation.json")
    assert result.returncode == 1, result.stdout + result.stderr
    assert not json.loads((tmp_path / "mutation.json").read_text(encoding="utf-8"))["passed"]


@pytest.mark.parametrize("source_round", ["2026-round-3", "2026-round-1-gold"])
def test_science_writer_fills_real_input_locator_metadata(source_round) -> None:
    from scripts.build_science_catalog_db import load_science_records, write_science_catalog

    records = load_science_records(rounds=[source_round])[0:2]
    assert len(records) == 2
    reference = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    with sqlite3.connect(":memory:") as connection:
        write_science_catalog(connection, records, reference)
        for table in ("assessment_items", "assessment_item_axes", "assessment_item_methods"):
            rows = connection.execute(f"SELECT locator FROM {table}").fetchall()
            if table == "assessment_items":
                assert len(rows) == 2
            for (locator,) in rows:
                parsed = json.loads(locator)
                assert parsed["sha256"]
                assert parsed["segment_id"]


def test_science_writer_preserves_numeric_score_and_weight() -> None:
    from scripts.build_science_catalog_db import write_science_catalog

    records = demo_records()[:1]
    records[0]["item"]["fields"]["score"]["value"] = 0
    records[0]["item"]["fields"]["weight"]["value"] = 15.0
    reference = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    with sqlite3.connect(":memory:") as connection:
        write_science_catalog(connection, records, reference)
        assert connection.execute("SELECT score, weight FROM assessment_items").fetchone() == (
            "0", "15.0",
        )
        assert connection.execute("SELECT weight_summary FROM cases").fetchone()[0] == "15.0"


def test_science_writer_rejects_missing_source_hash() -> None:
    from scripts.build_science_catalog_db import write_science_catalog

    records = demo_records()[:1]
    records[0]["item"].pop("source_sha256")
    records[0]["document"].pop("source_sha256")
    reference = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
    with sqlite3.connect(":memory:") as connection, pytest.raises(ValueError, match="SHA-256"):
        write_science_catalog(connection, records, reference)


@pytest.mark.parametrize("include_source_html", [False, True])
def test_science_packaging_preserves_tables_columns_and_indexes(tmp_path, include_source_html):
    source = tmp_path / "source.sqlite"
    target = tmp_path / "packaged.sqlite"
    build_demo(source)
    package_catalog(source, target, include_source_html=include_source_html, review_item_ids=set())
    with sqlite3.connect(source) as original, sqlite3.connect(target) as packaged:
        for table in ("assessment_item_axes", "assessment_item_methods", "source_segments"):
            assert packaged.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall() == (
                original.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
            )
        columns = {row[1] for row in packaged.execute("PRAGMA table_info(assessment_items)")}
        assert {"segment_id", "source_item_id", "activity_abstain_reason", "locator"} <= columns
        assert packaged.execute(
            "SELECT name FROM sqlite_schema WHERE name = 'idx_axes_axis_value'"
        ).fetchone()
    assert_bounded_html_privacy(target)


@pytest.mark.parametrize("table,column", [
    ("assessment_item_axes", "evidence"), ("assessment_item_axes", "locator"),
    ("assessment_item_methods", "custom_text"), ("assessment_item_methods", "locator"),
])
def test_science_privacy_gate_scans_evidence_and_methods(tmp_path, table, column):
    database = tmp_path / "privacy.sqlite"
    build_demo(database)
    with sqlite3.connect(database) as connection:
        connection.execute(f"UPDATE {table} SET {column} = ?", ("010-1234-5678",))
    with pytest.raises(RuntimeError, match="personal-data release gate"):
        assert_bounded_html_privacy(database)


def test_plain_text_preserves_html_table_cells() -> None:
    text = plain_text(
        "<table><tr><td>수행평가</td><td>극한을 활용한 그래프 시각화</td>"
        "<td>미분과 적분을 활용한 문제 만들기</td></tr></table>"
    )

    assert "수행평가 | 극한을 활용한 그래프 시각화" in text
    assert "시각화 | 미분과 적분을 활용한 문제 만들기" in text


def test_derive_task_names_stays_inside_subject_section() -> None:
    evidence = """
    # 2026년도 미디어 영어과 교수학습 및 평가 운영 계획
    <table><tr><td>영어 미디어 스토리보드 보고서</td></tr></table>
    # 2026년도 (미적분Ⅰ)과 교수학습 및 평가 운영 계획
    <table><tr><td>고사/평가과제</td><td>극한을 활용한 그래프 시각화</td>
    <td>미분과 적분을 활용한 문제 만들기</td></tr></table>
    평가방법
    ☑ 서술·논술 □ 구술·발표 □ 토의·토론 □ 프로젝트
    """

    names, local_text, sources = derive_task_names(
        evidence,
        ["영어 미디어 스토리보드 보고서", "☑ 서술·논술 □ 구술·발표"],
        "미적분Ⅰ",
    )

    assert names[0] == "미분과 적분을 활용한 문제 만들기"
    assert "극한을 활용한 그래프 시각화" in names
    assert all("영어" not in name for name in names)
    assert all("서술·논술" not in name for name in names)
    assert "미디어 영어" not in local_text
    assert sources[names[0]] in {"table", "section"}


def test_assessment_method_option_rows_are_not_task_names() -> None:
    assert task_name_is_rejected("☑ 서술·논술 □ 구술·발표 □ 토의·토론 □ 프로젝트")
    assert task_name_is_rejected("◻조사·발표")
    assert task_name_is_rejected("평가방법 | 서술·논술 | 프로젝트")
    assert task_name_is_rejected(
        "발표 전달력이 현저히 낮으며 발표 준비가 부실하여 형식을 지키지 않음.(5점)"
    )


def test_vertical_task_label_does_not_capture_the_whole_rubric_column() -> None:
    evidence = """
    <table>
      <tr><td>수행평가과제명</td><td>경제 기사를 활용한 함수 분석 보고서</td></tr>
      <tr><td>평가 기준 3개 충족</td><td>우수</td></tr>
      <tr><td>개념 이해 및 적용이 부족함</td><td>미흡</td></tr>
    </table>
    """

    names, _, _ = derive_task_names(evidence, [], "경제 수학")

    assert names == ["경제 기사를 활용한 함수 분석 보고서"]


def test_horizontal_task_header_still_reads_task_name_column() -> None:
    evidence = """
    <table>
      <tr><th>수행평가명</th><th>반영 비율</th></tr>
      <tr><td>경제 기사를 활용한 함수 분석 보고서</td><td>20%</td></tr>
    </table>
    """

    names, _, _ = derive_task_names(evidence, [], "경제 수학")

    assert names == ["경제 기사를 활용한 함수 분석 보고서"]


def test_rowspan_grid_does_not_shift_rubric_cells_into_task_column() -> None:
    evidence = """
    <table>
      <tr><th>평가영역</th><th>평가요소</th><th colspan="2">채점 기준</th><th>부여점수</th></tr>
      <tr><td rowspan="4">융합 주제탐구발표</td><td rowspan="4">융합주제탐구</td>
      <td rowspan="4">주제 선정 및 탐구 목표 작성</td>
      <td>평가 기준 4개 모두 충족</td><td>50점</td></tr>
      <tr><td>평가 기준 3개 충족</td><td>40점</td></tr>
      <tr><td>평가 기준 2개 충족</td><td>30점</td></tr>
      <tr><td>평가 기준 1개 이하 충족</td><td>20점</td></tr>
    </table>
    """

    names, _, _ = derive_task_names(evidence, [], "경제 수학")

    assert names[0] == "융합 주제 탐구 발표"
    assert all("평가 기준" not in name for name in names)


def test_table_position_alone_does_not_publish_a_field_label() -> None:
    evidence = """
    <table>
      <tr><td>수행평가명</td><td>학기말 합계</td></tr>
      <tr><td>수행평가명</td><td>부정행위</td></tr>
      <tr><td>수행평가명</td><td>출제 의도</td></tr>
    </table>
    """

    names, _, _ = derive_task_names(evidence, [], "경제 수학")

    assert names == []


def test_only_the_cell_after_a_task_label_gets_label_confidence() -> None:
    evidence = (
        "평가영역 | 수학적 탐구 및 분석 | 서술·논술 | "
        "탐구 주제 선정 및 계획 | 실제 문제 해결 역량 평가"
    )

    names, _, sources = derive_task_names(evidence, [], "대수")

    assert names == ["수학적 탐구 및 분석"]
    assert sources == {"수학적 탐구 및 분석": "context"}


def test_rubric_count_and_truncated_sentence_are_rejected() -> None:
    assert task_name_is_rejected(
        "1학기 매 수업시간에 참여하고 올바르게 작성한 풀이과정을 확인한 총 횟수"
    )


def test_checkbox_and_html_attribute_artifacts_are_removed() -> None:
    evidence = """
    <table>
      <tr><td>수행평가명</td><td>gfedc 프로젝트</td></tr>
      <tr><td>수행평가명</td><td>rowspan="5">독서활동발표</td></tr>
      <tr><td>수행평가명</td><td>lspan="4">수학 문제 만들기</td></tr>
      <tr><td>수행평가명</td><td>포트폴리오 gfedc 발표</td></tr>
      <tr><td>수행평가명</td><td>td rowspan="3">변형 문제 제작</td></tr>
    </table>
    """

    names, _, _ = derive_task_names(evidence, [], "공통수학1")

    assert "프로젝트" not in names
    assert "독서 활동 발표" in names
    assert "수학 문제 만들기" in names
    assert "변형 문제 제작" in names
    assert "포트폴리오 발표" not in names
    assert all("span=" not in name and "gfedc" not in name for name in names)


def test_spacing_variants_are_merged_into_one_readable_title() -> None:
    evidence = """
    <table>
      <tr><td>수행평가명</td><td>나만의저축상품만들기</td></tr>
      <tr><td>수행평가명</td><td>나만의 저축상품 만들기</td></tr>
      <tr><td>수행평가명</td><td>환율을이용한여행보고서</td></tr>
      <tr><td>수행평가명</td><td>환율을 이용한 여행 보고서</td></tr>
    </table>
    """

    names, _, _ = derive_task_names(evidence, [], "경제 수학")

    assert set(names) == {"환율을 이용한 여행 보고서", "나만의 저축 상품 만들기"}
    assert task_name_is_rejected(
        "세 가지 개념을 정확히 이해하고 설명하지만, 상호 관계에 대한 증명 과"
    )


def test_common_pdf_spacing_breaks_are_repaired_without_rewriting_the_title() -> None:
    assert normalize_task_name("기하 문제분석 및 문제만들기") == (
        "기하 문제 분석 및 문제 만들기"
    )
    assert normalize_task_name("이차함수 수학적 모델링프로젝트") == (
        "이차함수 수학적 모델링 프로젝트"
    )
    assert normalize_task_name("독서기반 수학 탐구활동") == "독서 기반 수학 탐구 활동"
    assert normalize_task_name("경우의 수를 적 용한 문제풀이") == (
        "경우의 수를 적용한 문제 풀이"
    )


def test_concrete_short_task_names_are_still_publishable() -> None:
    evidence = """
    <table>
      <tr><td>수행평가명</td><td>수리논술</td></tr>
      <tr><td>수행평가명</td><td>학교 공간 배치하기</td></tr>
      <tr><td>수행평가명</td><td>수학칼럼쓰기</td></tr>
      <tr><td>수행평가명</td><td>인포그래픽</td></tr>
    </table>
    """

    names, _, _ = derive_task_names(evidence, [], "공통수학1")

    assert set(names) == {
        "수학칼럼쓰기",
        "학교 공간 배치하기",
        "수리논술",
        "인포그래픽",
    }


def test_score_and_policy_cells_are_not_task_names() -> None:
    assert task_name_is_rejected("반영 만점(비율) 10점")
    assert task_name_is_rejected("5점 x 2문제 =10점")
    assert task_name_is_rejected("19~20점 16.5~18.5점 12.5~16점 10점 이하")
    assert task_name_is_rejected("대수(3학점)")
    assert task_name_is_rejected("1학기 평가 내용 및 점수 부여 기준")
    assert task_name_is_rejected("평가 항목")
    assert task_name_is_rejected("학생 유의사항")
    assert task_name_is_rejected("1차시험(중간시험)")
    assert task_name_is_rejected("성취기준에 기반한 일관성 있는 평가")
    assert task_name_is_rejected("포트폴리오, 발표")
    assert task_name_is_rejected("과제탐구")
    assert task_name_is_rejected("실생활 문제 해결 중심의 역량 평가")
    assert task_name_is_rejected("실생활 데이터 분석 및 융합적 수행 역량 평가")
    assert task_name_is_rejected("토론 및 발표")
    assert task_name_is_rejected("서·논술형, 발표")
    assert task_name_is_rejected("관찰평가 포트폴리오")
    assert task_name_is_rejected("도서 기반 평가 방법 수학 탐구")
    assert task_name_is_rejected("추가적인 분량탐구활동")
    assert task_name_is_rejected("수학의 기본 개념 이해와 문제 해결 능력 신장")
    assert task_name_is_rejected("주제 선정,자료 수집 및 적용, 탐구 수행 및 결과물 제작")
    assert task_name_is_rejected("III. 창의적 사고와 문화 활동 (2) 문학의 소통과 문화 활동")
    assert task_name_is_rejected("근대 이전 한국사의 이해 2. 근대 이전 한국사의 탐구")
    assert task_name_is_rejected("공간정보와 지리탐구 2. 생활 속 지리탐구")
    assert task_name_is_rejected("화법과 작문 과정형 포트폴리오 제작")
    assert task_name_is_rejected("수학과제탐구")
    assert task_name_is_rejected("수학 과제 탐구")
    assert task_name_is_rejected(
        "I. 수학 과제 탐구의 이해 II. 수학 과제 탐구의 실행과 평가"
    )
    assert task_name_is_rejected("교수학습활동")
    assert task_name_is_rejected("III. 창의적 사고와 문화 활동")
    assert task_name_is_rejected("포트폴리오 ★사이버 어울림활동")
    assert task_name_is_rejected("I. 사회현상의 이해와 탐구")


def test_attached_field_labels_and_trailing_metadata_are_removed() -> None:
    assert normalize_task_name("평가영역도서기반수학탐구") == "도서 기반 수학 탐구"
    assert normalize_task_name("수행평가명 : 문제 해결 포트폴리오") == (
        "문제 해결 포트폴리오"
    )
    assert normalize_task_name("1. 수행평가명 : 문제해결 포트폴리오") == (
        "문제 해결 포트폴리오"
    )
    assert normalize_task_name("III.공간도형과 공간좌표 교과융합프로젝트") == (
        "공간도형과 공간좌표 교과 융합 프로젝트"
    )
    assert normalize_task_name("★수행평가-실생활 수학 탐구보고서") == (
        "실생활 수학 탐구 보고서"
    )
    assert normalize_task_name("수학 기사 작성 내용 (85)") == "수학 기사 작성 내용"
    assert normalize_task_name("탐구 보고서 2회") == "탐구 보고서"
    assert task_name_is_rejected(normalize_task_name("수학 기사 작성 내용 (85)"))
    assert task_name_is_rejected("기사문의 창의성 및 흥미도")


def test_trailing_score_metadata_is_removed_from_a_real_title() -> None:
    assert normalize_task_name("이항분포를 이용한 큰 수의 법칙 탐구 : 100점, 25%") == (
        "이항분포를 이용한 큰 수의 법칙 탐구"
    )


def test_mathematical_or_natural_language_is_not_overfiltered() -> None:
    assert not task_name_is_rejected(
        "공학적 도구를 사용하여 포물선, 타원, 쌍곡선 중 2종 이상을 적용한 독창적인 로고 만들기"
    )
    assert not task_name_is_rejected(
        "저작권을 밝힌 글과 그렇지 못한 글 찾아 분석하기"
    )
    assert not task_name_is_rejected("경우의 수를 활용한 실생활 문제 만들기")
    assert not task_name_is_rejected("환율을 고려한 나만의 해외여행 설계")
    assert not task_name_is_rejected("수학으로 보는 경제 기사")
    assert not task_name_is_rejected("문학 작품 속 수학적 구조 탐구")
    assert not task_name_is_rejected("미술 작품의 기하학적 대칭 탐구")


def test_subject_localization_stops_before_the_next_course() -> None:
    evidence = """
    수학적 증명을 바탕으로 현상 증명하기
    미적분Ⅰ 교과가 목표로 하는 세부 능력을 평가한다.
    # 영어과 교수학습 및 평가 운영 계획
    영어 비판적 사고 영문 저널 프로젝트
    """

    names, local_text, _ = derive_task_names(evidence, [], "미적분Ⅰ")

    assert names == ["수학적 증명을 바탕으로 현상 증명하기"]
    assert "영문 저널" not in local_text


def test_task_table_is_preferred_and_exposed_as_structured_fields() -> None:
    evidence = """
    ## 나. 수행평가 출제계획
    ## 1) 수학 독서 기반 사고 확장 글쓰기
    <table>
      <tr><th>수행평가과제명</th><th>수학 독서 기반<br>사고 확장 글쓰기</th></tr>
      <tr><td>평가 영역 (성취기준)</td><td>[12대수01-01] 지수의 뜻을 설명한다.</td></tr>
      <tr><td>평가 요소</td><td>문제 해결 능력 · 탐구 논리</td></tr>
      <tr><td>평가 방법</td><td>☑ 서술·논술 □ 구술·발표 ☑ 포트폴리오</td></tr>
      <tr><td>반영 비율</td><td>20점 / 20%</td></tr>
    </table>
    """

    names, _, sources = derive_task_names(evidence, [], "대수")
    assert names[0] == "수학 독서 기반 사고 확장 글쓰기"
    structure = assessment_structure(evidence, names[0], sources)
    assert structure["basis"] == "table"
    assert structure["standards"] == ["12대수01-01"]
    assert "서술·논술" in structure["methods"]
    assert structure["weight"] == "20점 · 20%"
    assert assessment_category(names[0], structure, evidence) == "reading"


def test_category_uses_the_displayed_task_not_a_neighboring_table_task() -> None:
    structure = {
        "overview": "문제 해결 과제와 수학 독서 보고서를 함께 운영한다.",
        "criteria": ["독서 결과물의 완성도를 평가한다."],
    }

    assert assessment_category("서술형 문제 해결력", structure, "") == ""
    assert assessment_category("수학 독서 탐구", structure, "") == "reading"


def test_colspan_values_are_not_repeated_in_the_public_overview() -> None:
    evidence = """
    <table>
      <tr><td>수행평가명</td><td colspan="3">함수 그래프 탐구 보고서</td></tr>
      <tr><td>평가개요</td><td colspan="3">함수의 변화를 관찰하고 보고서로 정리한다.</td></tr>
    </table>
    """

    names, _, sources = derive_task_names(evidence, [], "공통수학1")
    structure = assessment_structure(evidence, names[0], sources)

    assert structure["overview"] == "함수의 변화를 관찰하고 보고서로 정리한다."


def test_generic_colspan_label_is_not_used_as_an_overview() -> None:
    evidence = """
    <table>
      <tr><td>수행평가명</td><td colspan="3">함수 그래프 탐구 보고서</td></tr>
      <tr><td colspan="4">세부 평가 내용</td></tr>
    </table>
    """

    names, _, sources = derive_task_names(evidence, [], "공통수학1")
    structure = assessment_structure(evidence, names[0], sources)

    assert structure["overview"] == ""


def test_category_does_not_leak_from_unrelated_document_context() -> None:
    structure = {"overview": "문제 풀이 과정을 작성한다.", "criteria": []}
    assert assessment_category("문제 풀이 과정 작성하기", structure, "앞부분 독서 안내") == ""
