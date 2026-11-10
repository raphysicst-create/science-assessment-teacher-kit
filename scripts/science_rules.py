"""Shared science subject, code, publication and audit rules.

Run: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_science_rules.py
Removed math-only MATH_CONTEXT_RE, common-math/course names and math task signals:
science is the target; method/activity signals come from METHOD_RE and science_axes.json.
Other-subject title names derive solely from MIDDLE_SUBJECT_PREFIXES. Neutral legacy
heading/rubric/policy/fragment rules remain, even for explicit source labels.

공개 항목(`assessment_items.extraction_status = 'bounded'`, 과학판 API가 화면에 싣는 조건과 같다)에
차단 오류가 1건이라도 있으면 감사 명령은 종료 코드 1로 끝난다. 차단 오류 =
(B1) 항목의 원문 HTML·제목·성취기준 칸에 있는 성취기준 코드 접두가 과학(`[9과`) 외 교과이거나
과학과 다른 교과가 섞임,
(B2) 제목에 과학 외 교과 이름이 있고 항목에 `[9과` 코드가 없음,
(B4) 제목·근거의 원문 위치(locator)나 원문 조각 해시가 없음,
(B5) 표 구조 차단 플래그. 수행과제 표지 여럿은 warning, AI3(합친 카드)이 막는다.
(B6) 원문 HTML·채점표 HTML·제목·방법 칸의 고위험 개인정보 패턴.
B3 제목 규칙은 이유를 유지한 warning이며 공개를 차단하지 않는다.
카드 AI 판정은 선택 감사에서 AI0 미확인·AI1 비과제·AI2 중복·AI3 합침을 차단한다.
처리 기록·면제 목록·수동 승인 파일로 차단 오류를 통과시키지 않는다.
차단 오류가 있는 항목은 위험 큐 CSV에
`item_id, case_id, school_name, title, blocking_codes, reasons, severity`로 들어간다.
B3는 개별 감사 큐의 별도 warning 행이며 합친 차단 큐에는 들어가지 않는다.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import zlib
from pathlib import Path

from scripts.math_assessment_detail_parser import _exact_fields
from scripts.middle_fields import reference_codes
from scripts.middle_items import CODE_RE
from scripts.middle_subjects import code_evidence as code_evidence
from scripts.package_math_assessment_vercel_data import HIGH_RISK_PERSONAL_DATA_PATTERNS
from scripts.science_title_rules import (
    ACTIVITY_RE as ACTIVITY_RE,
)
from scripts.science_title_rules import (
    METHOD_RE as METHOD_RE,
)
from scripts.science_title_rules import (
    OTHER_SUBJECT_TITLE_RE,
    SCIENCE_EXCLUSION_RE,
    SCIENCE_WORD_RE,
    title_rejection,
    visible_text,
)
from scripts.science_title_rules import (
    SCIENCE_ACTIVITY_IDS as SCIENCE_ACTIVITY_IDS,
)
from scripts.science_title_rules import (
    audit_flags as audit_flags,
)
from scripts.science_title_rules import (
    compact as compact,
)
from scripts.science_title_rules import (
    confidence as confidence,
)

OTHER_SUBJECT_SOURCE_RE = re.compile(
    r"기본권|시민의\s*복지|사회적\s*연대|타인의\s*고통|"
    r"사회문제\s*주제\s*탐구|민주주의\s*방식|다문화\s*사회"
)

TARGET_PREFIX = "과"
PUBLIC_ITEM_SQL = "extraction_status = 'bounded'"
ROOT = Path(__file__).resolve().parents[1]
QUEUE_FIELDS = [
    "item_id", "case_id", "school_name", "title", "blocking_codes", "reasons", "severity"
]
STANDARD_TOKEN_RE = re.compile(r"\[\s*\d{1,2}(?!\d)[^\[\]]*-\s*\d[^\[\]]*\]")
# In-bracket science ranges/lists stay science: [9과11-01~04], [9과11-01,02], [9과04-01~9과04-04].
TARGET_CODE_RE = re.compile(r"\[9과\d{2}-\d{2}(?:[~∼〜,·ㆍ](?:9과\d{2}-)?\d{1,2})*\]")
STANDARD_PREFIX_RE = re.compile(r"\[(?P<grade>\d{1,2})(?P<prefix>[^\d-]+)")
BLOCKING_TABLE_FLAGS = frozenset(
    {
        "invalid_span_value",
        "rowspan_overflows_table",
        "multiple_course_code_prefixes",
        "multiple_distinct_assessment_areas",
        "likely_unbounded_public_item",
        "whole_plan_policy_leak",
        "html_decode_failed",
        "html_parse_failed",
    }
)
WARNING_TABLE_FLAGS = frozenset(
    {
        "multiple_performance_task_labels",
        "oversized_html",
        "excessive_table_count",
        "orphan_achievement_codes",
        "many_orphan_achievement_codes",
        "multiple_assessment_area_labels",
        "split_standards_tables",
        "many_split_standards_tables",
        "adjacent_compatible_table_fragments",
        "achievement_level_page_break",
        "section_local_trailing_blank_columns",
        "inconsistent_effective_columns",
        "high_blank_cell_ratio",
        "large_table_without_header_signal",
        "very_wide_table",
    }
)
# Recovery proposals retain their stricter geometry screening without changing B5.
RECOVERY_BLOCKING_TABLE_FLAGS = BLOCKING_TABLE_FLAGS | frozenset(
    {
        "multiple_performance_task_labels",
        "excessive_table_count",
        "inconsistent_effective_columns",
        "multiple_assessment_area_labels",
        "oversized_html",
    }
)


def default_database() -> Path:
    return Path(
        os.environ.get("MATH_ASSESSMENT_DETAIL_DB")
        or ROOT / "data/publish/science/math_assessment_catalog_detail.sqlite"
    )


def standard_code_prefixes(text: str) -> list[str]:
    """Allow only normalized middle-school science codes; unknown code tokens stay other."""
    prefixes = set()
    for token in STANDARD_TOKEN_RE.findall(text):
        normalized = re.sub(r"\s+", "", token)
        # Remove exactly one extra leading zero in an area number, then recheck the allowlist.
        candidate = re.sub(r"^\[9과0(?=\d{2}-)", "[9과", normalized, count=1)
        if TARGET_CODE_RE.fullmatch(candidate):
            prefixes.add(TARGET_PREFIX)
            continue
        match = STANDARD_PREFIX_RE.match(normalized)
        prefix = normalized
        if match:
            prefix = match["prefix"]
            if match["grade"] != "9":
                prefix = match["grade"] + prefix
        # A malformed science token must never become the allowed prefix.
        prefixes.add(normalized if prefix == TARGET_PREFIX else prefix)
    return sorted(prefixes)


def science_standard_codes(text: str) -> list[str]:
    codes = []
    valid = reference_codes()
    for match in CODE_RE.finditer(text):
        area, first, end_area, last = match.groups()
        candidates = [f"[9과{int(area):02d}-{int(first):02d}]"]
        if last and (not end_area or int(end_area) == int(area)):
            candidates += [
                f"[9과{int(area):02d}-{number:02d}]"
                for number in range(int(first) + 1, int(last) + 1)
                if f"[9과{int(area):02d}-{number:02d}]" in valid
            ]
        codes.extend(code for code in candidates if code not in codes)
    return codes


def science_exact_fields(segment: str) -> dict[str, object]:
    """Reuse subject-neutral fields, then supply normalized science standards."""
    fields = _exact_fields(segment, subject_family="science")
    fields["standards"] = science_standard_codes(visible_text(segment))
    return fields


def source_is_other_subject(text: str) -> bool:
    alignment = subject_alignment(text)
    return alignment in {"other", "mixed"} or bool(
        (OTHER_SUBJECT_TITLE_RE.search(text) or OTHER_SUBJECT_SOURCE_RE.search(text))
        and alignment != "target"
        and not (SCIENCE_WORD_RE.search(text) and not SCIENCE_EXCLUSION_RE.search(text))
    )


def subject_alignment(text: str) -> str:
    """Classify all code-like tokens against the science allowlist, including unknown forms."""
    prefixes = set(standard_code_prefixes(text))
    if not prefixes:
        return "none"
    if TARGET_PREFIX in prefixes:
        return "mixed" if prefixes - {TARGET_PREFIX} else "target"
    return "other"


def decoded_html(item: dict, field: str = "source_html_zlib") -> str:
    if field == "source_html_zlib" and "source_html" in item:
        return str(item["source_html"])
    try:
        return zlib.decompress(bytes(item.get(field) or b"")).decode("utf-8")
    except (zlib.error, UnicodeDecodeError, TypeError):
        return ""


def standard_texts(item: dict) -> tuple[list[str], bool]:
    """Decode persisted standards before matching; retain malformed raw evidence."""
    raw = item.get("standards_json", "[]")
    try:
        values = json.loads(raw)
    except (ValueError, TypeError):
        return [str(raw)], False
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        return [str(raw)], False
    return values, True


def subject_errors(item: dict) -> list[str]:
    standards, valid_standards = standard_texts(item)
    text = " ".join(
        (
            decoded_html(item),
            visible_text(decoded_html(item)),
            str(item.get("title") or ""),
            *standards,
        )
    )
    errors = []
    if not valid_standards or subject_alignment(text) in {"other", "mixed"}:
        errors.append("B1")
    if OTHER_SUBJECT_TITLE_RE.search(
        str(item.get("title") or "")
    ) and TARGET_PREFIX not in standard_code_prefixes(text):
        errors.append("B2")
    return errors


def valid_locator(value) -> bool:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return False
    return (
        isinstance(value, dict)
        and type(value.get("start")) is int
        and type(value.get("end")) is int
        and 0 <= value["start"] < value["end"]
        and any(isinstance(value.get(key), str) and value[key].strip()
                for key in ("sha256", "source_sha256", "fragment_sha256"))
    )


def table_flags(item: dict) -> set[str]:
    # Import lazily: the geometry auditor itself imports this module's rule API.
    from scripts.audit_math_assessment_table_structure import audit_html, restore_escaped_table_rows

    flags = set(item.get("table_flags") or [])
    for field in ("source_html_zlib", "rubric_html_zlib"):
        text = decoded_html(item, field)
        if not text.strip():
            if field == "rubric_html_zlib":
                try:
                    # An encoded empty rubric is legitimate, corrupt data is not.
                    zlib.decompress(bytes(item.get(field) or b"")).decode("utf-8")
                    continue
                except (zlib.error, UnicodeDecodeError, TypeError):
                    if not item.get(field):
                        continue
            flags.add("html_decode_failed")
            continue
        flags.update(audit_html(restore_escaped_table_rows(text))["flags"])
    return flags


def blocking_errors(item: dict) -> list[str]:
    if item.get("extraction_status") != "bounded":
        return []
    errors = subject_errors(item)
    if not valid_locator(item.get("locator")) or any(
        not valid_locator(value) for value in item.get("evidence_locators", [])
    ):
        errors.append("B4")
    if table_flags(item) & BLOCKING_TABLE_FLAGS:
        errors.append("B5")
    if personal_data_patterns(item):
        errors.append("B6")
    return errors


def personal_data_patterns(item: dict) -> list[str]:
    """Return pattern names so diagnostic reasons do not repeat matched personal data."""
    fields = (
        decoded_html(item), decoded_html(item, "rubric_html_zlib"),
        str(item.get("title") or ""), str(item.get("method") or ""),
    )
    texts = (*fields, *(visible_text(value) for value in fields))
    return [name for name, pattern in HIGH_RISK_PERSONAL_DATA_PATTERNS.items()
            if any(pattern.search(text) for text in texts)]


def public_items(database: Path) -> list[dict]:
    with sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        rows = [
            dict(row)
            for row in connection.execute(
                f"SELECT item.*, cases.school_name FROM assessment_items item "
                f"JOIN cases USING (case_id) WHERE item.{PUBLIC_ITEM_SQL} "
                "ORDER BY item.case_id, item.item_order"
            )
        ]
        by_id = {row["item_id"]: row for row in rows}
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type='table'")}
        for table in ("assessment_item_axes", "assessment_item_methods"):
            if table not in tables:
                continue
            for evidence in connection.execute(f"SELECT item_id, locator FROM {table}"):
                if evidence["item_id"] in by_id:
                    by_id[evidence["item_id"]].setdefault("evidence_locators", []).append(
                        evidence["locator"])
        return rows


def risk_record(
    item: dict, codes: list[str], *, severity: str = "blocking", reasons: str | None = None
) -> dict:
    code_reasons = {
        "B1": (
            "other_or_mixed_subject_codes"
            if standard_texts(item)[1] else "invalid_standards_json"
        ),
        "B2": "other_subject_title_without_science_code",
        "B3": title_rejection(str(item.get("title") or ""), decoded_html(item)) or "",
        "B4": "missing_locator_or_source_hash",
        "B5": "|".join(sorted(table_flags(item) & BLOCKING_TABLE_FLAGS)) if "B5" in codes else "",
        "B6": "|".join(personal_data_patterns(item)) if "B6" in codes else "",
    }
    return {
        **{key: item.get(key, "") for key in QUEUE_FIELDS[:4]},
        "blocking_codes": "|".join(codes),
        "reasons": (
            ";".join(f"{code}:{code_reasons[code]}" for code in codes)
            if reasons is None else reasons
        ),
        "severity": severity,
    }


def write_audit(report: dict, queue: list[dict], output: Path, queue_path: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    blocking_count = sum(row["severity"] == "blocking" for row in queue)
    report.update(
        queue=str(queue_path.resolve()),
        passed=blocking_count == 0 and report["public_item_count"] > 0,
        blocking_public_items=blocking_count,
    )
    if report["public_item_count"] == 0:
        report["errors"] = ["no_public_items"]
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with queue_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(queue)
    print(json.dumps(report, ensure_ascii=False))
