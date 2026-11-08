"""S6 offline science items with cell ownership and immutable S4 offsets.

Only explicit row/column/form structures establish bounds. Title hints and
flattened PDF text remain review candidates. No curriculum or activity inference.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

if __package__:
    from .assessment_symbols import BOX_RE, marker_state
    from .middle_segments import digest_id, text_locator, visible
    from .middle_subjects import classify_subject, table_spans
else:
    from assessment_symbols import BOX_RE, marker_state
    from middle_segments import digest_id, text_locator, visible
    from middle_subjects import classify_subject, table_spans

RULE_VERSION = "middle-items-v7"
IDENTITY_VERSION = "middle-items-v2"  # Field-only changes retain source identities.
FIELDS = (
    "title",
    "assessment_area",
    "task_no",
    "task_text",
    "method",
    "timing",
    "score",
    "points",
    "weight",
    "essay_weight",
    "standards",
    "rubric",
    "criteria",
    "elements",
)
LABELS = {
    "평가영역": "assessment_area",
    "평가영역명": "assessment_area",
    "영역명": "assessment_area",
    "영역": "assessment_area",
    "평가/영역": "assessment_area",
    "유형/평가영역": "assessment_area",
    "평가과제": "task",
    "평가과제명": "task",
    "수행과제": "task",
    "과제명": "task",
    "수행평가명": "title",
    "수행평가과제명": "title",
    "제목": "title",
    "평가제목": "title",
    "고사명/평가과제명": "task",
    "횟수/영역": "assessment_area",
    "영역및방법": "area_method",
    "방법·영역": "area_method",
    "평가방법(과제명)": "task",
    "평가방법/과제명": "task",
    "평가횟수": "frequency",
    "과제번호": "task_no",
    "평가방법": "method",
    "평가유형": "method",
    "관련단원": "unit",
    "단원명": "unit",
    "단원": "unit",
    "평가주체": "evaluator",
    "평가방식": "organization",
    "평가시기": "timing",
    "평가시기/횟수": "timing",
    "시기": "timing",
    "만점": "score",
    "영역만점": "score",
    "평가만점": "score",
    "영역별만점": "score",
    "만점점수": "score",
    "배점": "points",
    "세부배점": "points",
    "기본점수": "base_score",
    "반영비율": "weight",
    "비율": "weight",
    "영역별반영비율": "weight",
    "영역반영비율": "weight",
    "세부반영비율": "weight",
    "성취기준": "standards",
    "교육과정성취기준": "standards",
    "관련성취기준": "standards",
    "평가준거성취기준": "criteria",
    "채점기준": "rubric",
    "평가기준": "rubric",
    "평가요소": "elements",
    "평가구분": "kind",
    "평가종류": "kind",
    "학년": "grade",
    "학기": "semester",
    "성취기준별성취수준": "levels",
    "성취수준": "levels",
    "명칭,영역": "assessment_area",
    "영역·횟수": "assessment_area",
    "방법(평가유형)": "method",
    "관련성취기준코드": "standards",
    "단원내용": "unit",
    "평가영역명(관련단원명)": "unit",
    "평가영역(단원)": "assessment_area",
    "핵심역량": "competency",
    "교과역량": "competency",
    "평가요소(배점)": "elements",
    "평가요소및배점": "elements",
}
TITLE_ROLES = {"title", "task", "task_no", "assessment_area"}
TASK_NO_RE = re.compile(
    r"(?:(?:수행\s*평가|실험|서[·ㆍ･・]?논술형?|서술형|논술형|과제|탐구)\s*\d+"
    r"|\d+\s*(?:차|회)|[①-⑳])"
)
AREA_TITLE_RE = re.compile(
    r"(?:실험(?:[·ㆍ･‧]실습)?|탐구(?:활동)?|(?:실험|탐구)\s*보고서|실험\s*탐구|서[·ㆍ･‧]?논술형?"
    r"|서술형|논술형|구술[·ㆍ･‧]?발표|발표|보고서|프로젝트|포트폴리오)(?:\s*평가)?"
)
CODE_RE = re.compile(
    r"\[\s*9\s*과\s*(\d{2})\s*-\s*(\d{2})\s*\]"
    r"(?:(?:\s|<br\s*/?>)*[~∼～–](?:\s|<br\s*/?>)*"
    r"(?:\[\s*9\s*과\s*(\d{2})\s*-\s*)?(\d{2})\s*\]?)?"
)
ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr\s*>", re.S | re.I)
CELL_RE = re.compile(r"<(?:td|th)\b([^>]*)>(.*?)</(?:td|th)\s*>", re.S | re.I)
METHOD_BOX_RE = re.compile(BOX_RE.pattern + r"|\[[^\[\]\r\n]{0,5}\]|[\uFFFD\uF000-\uF8FF]", re.I)
NUMERIC_FIELDS = {"score", "points", "weight", "essay_weight"}
COMPOUND_NUMBER_RE = re.compile(
    r"\s*(?:\d+(?:\.\d+)?\s*점)?(?:\s|<br\s*/?>)*"
    r"(?:\(\s*\d+(?:\.\d+)?\s*[%％]\s*\))?\s*",
    re.I,
)
FIELD_STATUSES = ("present", "source_absent", "unconfirmed", "conflict")
ROLE_LABELS = {
    "performance": "실제 수행 항목",
    "summary_duplicate": "요약표의 중복 행",
    "teaching_plan": "교수학습 운영표",
    "general_standards": "일반 성취기준·성취수준표",
    "affective": "정의적·비수치 평가표",
    "other": "기타",
}


def label_role(text: str) -> str | None:
    key = re.sub(r"\s+", "", text)
    if key in {"영역만점(반영비율)", "만점(반영비율)", "영역만점(학기말반영비율)"}:
        return "score_weight"
    if "반영비율" in key and re.search(r"논술", key):
        return "essay_weight"
    key = re.sub(r"\((?:점|(?:100)?[%％]|퍼센트)\)", "", key)
    return LABELS.get(key)


def title_gate(value: str) -> dict:
    """Authenticity comes from the caller's source cell, never this score."""
    rejected = bool(
        not value
        or label_role(value)
        or len(value) > 120
        or re.search(r"성취수준|성취기준|수행평가\s*(?:세부|운영|계획)|결시|전입생", value)
        or re.search(r"수\s*있다\.?$|한다\.?$|하십시오|다음\s*과제|유의사항", value)
        or re.fullmatch(
            r"[\d.]+\s*(?:점|[%％]|학년|학기)?|[ABCDE]|수행평가|정기시험|중간고사|기말고사", value
        )
        or "[9" in value
        or BOX_RE.search(value)
        or re.match(r"^(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+|[IVX]+)\s*[.．]", value)
        or re.fullmatch(r"과학적\s*(?:사고력|탐구\s*능력|문제\s*해결력|의사소통\s*능력)", value)
        or method_only(value)
        or re.fullmatch(r"[가-힣]{2,}에", value)
        or re.fullmatch(r"\d{1,2}월(?:\s*\d주)?(?:\s*[~∼～-]\s*\d{1,2}월(?:\s*\d주)?)?", value)
    )
    numbered = bool(TASK_NO_RE.fullmatch(value))
    method_like = bool(re.fullmatch(r"포트폴리오|프로젝트|실험|서[·ㆍ･・]?논술형?", value))
    return {
        "accepted": not rejected,
        "specificity_score": 0 if rejected else 1 if numbered or method_like else 2,
        "reason": "구조어·운영문·성취수준·장문 지시" if rejected else "원문 제목 셀",
    }


def method_only(value: str) -> bool:
    """Lists of methods/organization/competencies never name an activity."""
    parts = re.split(r"\s*[,，/·ㆍ･‧]\s*", value)
    return bool(parts) and all(re.fullmatch(
        r"실험|실습|보고서|모둠|개별|서논술형|서술형|논술형|평가|수업\s*참여도"
        r"|과학적\s*(?:사고력|탐구\s*능력)", p,
    ) for p in parts) and (len(parts) > 1 or value in {"수업 참여도", "서논술형"})


def title_content_role(value: str, source_role: str) -> str:
    """Use literal activity/category/number content before the source label."""
    if TASK_NO_RE.fullmatch(value) or source_role == "task_no":
        return "task_no"
    if AREA_TITLE_RE.fullmatch(value):
        return "assessment_area"
    if re.search(
        r"하기|만들기|쓰기|보고서|관찰|측정|분류|설계|설명|비교|관계|원리"
        r"|모형|특징|적용|법칙", value
    ):
        return "task"
    return "task" if source_role in {"task", "title"} else "assessment_area"


def source_tables(text: str) -> list[dict]:
    """Expand a grid while keeping a single source object for each merged cell."""
    tables = []
    for number, span in enumerate(table_spans(text)):
        raw = text[span["start"] : span["end"]]
        rows, cells, occupied = [], [], {}
        verified = (
            span["format"] != "html"
            or len(re.findall(r"<table\b", raw, re.I)) == 1
            and len(re.findall(r"<tr\b", raw, re.I)) == len(ROW_RE.findall(raw))
            and len(re.findall(r"<(?:td|th)\b", raw, re.I)) == len(CELL_RE.findall(raw))
        )
        if span["format"] == "markdown" and "\\|" in raw:
            verified = False
        matches = list(ROW_RE.finditer(raw))
        if span["format"] == "markdown":
            matches = list(re.finditer(r"(?m)^[ \t]*\|[^\n]*\|[^\S\n]*(?:\n|$)", raw))
        for row_index, row in enumerate(matches if verified else []):
            found = list(CELL_RE.finditer(row.group()))
            if span["format"] == "markdown":
                found = list(re.finditer(r"(?<=\|)([^|]*)(?=\|)", row.group()))
            column = 0
            row_cells = []
            for match in found:
                while (row_index, column) in occupied:
                    column += 1
                attrs, content = (
                    (match[1], match[2]) if span["format"] == "html" else ("", match[1])
                )
                rs = re.search(r'\browspan\s*=\s*["\']?(\d+)', attrs, re.I)
                cs = re.search(r'\bcolspan\s*=\s*["\']?(\d+)', attrs, re.I)
                rowspan, colspan = int(rs[1]) if rs else 1, int(cs[1]) if cs else 1
                if not 1 <= rowspan <= 500 or not 1 <= colspan <= 100:
                    verified = False
                    break
                group = 2 if span["format"] == "html" else 1
                left = span["start"] + row.start() + match.start(group)
                cell = {
                    "raw": content,
                    "text": visible(content),
                    "start": left,
                    "end": left + len(content),
                    "table": number,
                    "row": row_index,
                    "col": column,
                    "rowspan": rowspan,
                    "colspan": colspan,
                }
                cells.append(cell)
                row_cells.append(cell)
                for r in range(row_index, row_index + rowspan):
                    for c in range(column, column + colspan):
                        if (r, c) in occupied:
                            verified = False
                        occupied[r, c] = cell
                column += colspan
            rows.append(row_cells)
        tables.append(
            {
                **span,
                "table": number,
                "rows": rows,
                "cells": cells,
                "grid": occupied,
                "structure_verified": verified,
            }
        )
    return tables


def evidence(cell: dict, conversion: dict, header: dict | None = None) -> dict:
    loc = text_locator(cell["start"], cell["end"], conversion)
    loc.update({k: cell[k] for k in ("table", "row", "col", "rowspan", "colspan") if k in cell})
    result = {"raw": cell["raw"], "text": cell["text"], "locator": loc}
    if cell.get("source_cell_proof"):
        result["source_cell_proof"] = cell["source_cell_proof"]
    if cell.get("shared_columns"):
        result["shared_columns"] = cell["shared_columns"]
        result["sharing_basis"] = "원문 colspan 병합셀·열 범위 공통값"
    if header:
        result["header_raw"] = header["raw"]
        result["header_locator"] = text_locator(header["start"], header["end"], conversion)
        result["header_unit"] = (
            "%"
            if re.search(r"[%％]", header["text"])
            else ("점" if re.search(r"\(\s*점\s*\)", header["text"]) else "")
        )
    if cell.get("cell_raw") is not None:
        result["cell_raw"] = cell["cell_raw"]
        result["cell_locator"] = text_locator(cell["cell_start"], cell["cell_end"], conversion)
    return result


def method_values(observations: list[dict], *, conversion_loss: bool = False) -> dict:
    options, plain = [], []
    for obs in observations:
        # Split in the *raw* cell so every option locator addresses original text.
        raw = obs["raw"]
        markers = list(METHOD_BOX_RE.finditer(raw))
        if not markers:
            if obs["text"]:
                plain.append(obs)
            continue
        for index, marker in enumerate(markers):
            end = markers[index + 1].start() if index + 1 < len(markers) else len(raw)
            option_raw = raw[marker.start() : end]
            text = visible(raw[marker.end() : end]).strip()
            normalized = re.sub(r"[ㆍ･・‧]", "·", re.sub(r"\s+", "", text))
            normalized = re.sub(r"^서술·논술", "서·논술", normalized)
            other = re.search(r"기타\s*\((.*?)\)", text, re.S)
            loc = {
                **obs["locator"],
                "start": obs["locator"]["start"] + marker.start(),
                "end": obs["locator"]["start"] + end,
            }
            options.append(
                {
                    "raw": option_raw,
                    "option_text": text,
                    "marker": marker.group(),
                    "state": marker_state(marker.group()),
                    "other_content": other[1] if other else None,
                    "normalized": "기타" if other else normalized,
                    "locator": loc,
                }
            )
    selected = [o["normalized"] for o in options if o["state"] == "checked"]
    if conversion_loss:
        state, reason, selected = "conversion_loss", "변환 손실", []
    elif any(o["state"] == "unknown" for o in options):
        state, reason, selected = "unknown", "체크 상태 불명", []
    elif selected:
        state, reason = "checked", ""
    elif options:
        state, reason = "all_unselected", "모두 미선택"
    elif plain:
        state, reason = "plain", ""
        selected = [p["text"] for p in plain]
    else:
        state, reason = "no_check", "체크 없음"
    return {
        "value": list(dict.fromkeys(selected)),
        "state": state,
        "reason": reason,
        "options": options,
        "plain": plain,
        "evidence": observations,
    }


def standard_values(observations: list[dict]) -> dict:
    occurrences, expanded = [], []
    for obs in observations:
        for match in CODE_RE.finditer(obs["raw"]):
            area, first, last_area, last = match.groups()
            stop = int(last or first)
            valid_range = last_area in {None, area} and int(first) <= stop <= 99
            codes = (
                [f"[9과{area}-{n:02}]" for n in range(int(first), stop + 1)] if valid_range else []
            )
            loc = {
                **obs["locator"],
                "start": obs["locator"]["start"] + match.start(),
                "end": obs["locator"]["start"] + match.end(),
            }
            occurrences.append(
                {
                    "raw": match.group(),
                    "expanded": codes,
                    "locator": loc,
                    "expansion_status": "syntactic_unvalidated" if codes else "review",
                }
            )
            expanded.extend(codes)
    return {
        "value": list(dict.fromkeys(expanded)),
        "occurrences": occurrences,
        "evidence": observations,
        "reason": ""
        if expanded
        else ("코드 범위 펼침 미확정" if occurrences else "코드 추출·원문 기재 여부 미확인"),
        "curriculum_status": "undetermined",
        "validity": "S7 미검증",
    }


def numeric_spans(name: str, obs: dict) -> list[dict]:
    """Split only explicit compound numeric cells, preserving immutable offsets."""
    if not obs.get("compound_numeric"):
        return [obs]
    unit = "%" if name == "weight" else "점"
    # A compound header can span two rows, one containing points and one percent.
    pattern = re.compile(r"\d+(?:\.\d+)?\s*" + (r"[%％]" if unit == "%" else unit))
    if not COMPOUND_NUMBER_RE.fullmatch(obs["raw"]):
        return [obs]
    return [
        {
            **obs,
            "raw": match.group(),
            "text": visible(match.group()),
            "locator": {
                **obs["locator"],
                "start": obs["locator"]["start"] + match.start(),
                "end": obs["locator"]["start"] + match.end(),
            },
            "cell_raw": obs["raw"],
            "cell_locator": obs["locator"],
            "header_unit": unit,
        }
        for match in pattern.finditer(obs["raw"])
    ]


def field_value(name: str, observations: list[dict]) -> dict:
    if name in NUMERIC_FIELDS:
        observations = [part for obs in observations for part in numeric_spans(name, obs)]
    result = {"value": "", "evidence": observations, "reason": "필드 추출·원문 기재 여부 미확인"}
    values = []
    for obs in observations:
        value = obs["text"]
        if name in NUMERIC_FIELDS:
            numeric = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(점|[%％])?\s*", value)
            obs["value_unit"] = numeric[2] or "" if numeric else ""
            if numeric:
                expected_unit = "%" if name in {"weight", "essay_weight"} else "점"
                units = {u.replace("％", "%") for u in (numeric[2], obs.get("header_unit")) if u}
                if units - {expected_unit}:
                    obs["normalization_status"] = "unit_conflict"
                    result["reason"] = "원문 값·머리글 단위 충돌"
                    continue
                obs["normalized"] = float(numeric[1])
                obs["unit"] = expected_unit
                obs["unit_basis"] = "value_or_header" if units else "field_label"
                values.append(obs["normalized"])
            elif value in {"P", "미산출"}:
                obs["normalized"] = value
                values.append(value)
        elif name == "timing" and value:
            if label_role(visible(obs.get("header_raw", ""))) == "timing":
                values.append(value)
                continue
            timing = re.search(
                r"\d{1,2}월(?:\s*\d주)?(?:\s*[~∼～-]\s*\d{1,2}월(?:\s*\d주)?)?"
                r"|\d{1,2}\s*[~∼～-]\s*\d{1,2}월|수시|상시|학기\s*(?:중|말)",
                value,
            )
            if timing:
                values.append(timing.group())
        elif value:
            values.append(value)
    unique = list(dict.fromkeys(values))
    if any(obs.get("normalization_status") == "unit_conflict" for obs in observations):
        return result
    if len(unique) == 1:
        result.update(value=unique[0], reason="")
    elif len(unique) > 1 and name in {"points", "rubric", "criteria", "elements", "task_text"}:
        result.update(value=unique, reason="")
    elif len(unique) > 1:
        result["reason"] = "동일 항목 필드 값 충돌"
        result["status"] = "conflict"
        result["observed_values"] = unique
    elif observations and result["reason"] != "원문 값·머리글 단위 충돌":
        result["reason"] = "원문 값 판독·단위 확인 필요"
    return result


def new_structure(table: dict, cells: list[dict], claims: dict, layout: str) -> dict:
    return {
        "table": table["table"],
        "cells": cells,
        "claims": claims,
        "layout": layout,
        "links": [],
        "review_reasons": [],
        "shared_fields": [],
    }


def candidate_role(structure: dict, tables: list[dict], text: str) -> tuple[str, str]:
    if structure.get("candidate_role") in {"teaching_plan", "general_standards"}:
        return structure["candidate_role"], structure["role_basis"]
    if structure["layout"] in {"row", "column", "form"}:
        return "performance", "수행평가 그룹 또는 항목 라벨 구조"
    number = structure["table"]
    if number is None:
        return "other", "표 역할 미확인"
    table = tables[number]
    labels = [re.sub(r"\s+", "", c["text"]) for c in table["cells"]]
    gap_start = tables[number - 1]["end"] if number else 0
    context = text[gap_start : table["start"]]
    if any(v in {"정의적영역", "정의적능력평가요소"} for v in labels) or re.search(
        r"(?m)^\s*(?:#{1,6}\s*)?\d*\s*정의적\s*(?:능력|평가)", context
    ):
        return "affective", "정의적 평가 머리글·절 문맥"
    if any("단원명" in v for v in labels[:8]) and any(
        re.search(r"시기|시수|^월|^주", v) for v in labels[:8]
    ):
        return "teaching_plan", "단원·시기·시수 운영 머리글"
    if any(v in {"평가요소", "채점기준"} or v.startswith("수행과제") for v in labels):
        return "performance", "항목 평가요소·채점기준 또는 수행과제 라벨"
    if any(v in {"성취기준", "성취기준별성취수준", "성취수준"} for v in labels[:4]):
        return "general_standards", "일반 성취기준·수준 머리글, 항목별 연결 근거 없음"
    return "other", "표 역할 미확인"


def teaching_table(table: dict) -> bool:
    """Header structure establishes teaching context, including repeated headers."""
    for row in table["rows"]:
        labels = [re.sub(r"\s+", "", c["text"]) for c in row]
        unit = any("단원명" in v for v in labels)
        schedule = any(re.search(r"시수|누계|^월$|^주$|^시기$", v) for v in labels)
        linkage = any(re.search(r"수업.*평가.*연계|수업방법|교수.*학습.*방법", v) for v in labels)
        if unit and (schedule or linkage) or linkage and any(
            label_role(v) in {"method", "standards"} for v in labels
        ):
            return True
    return False


def standards_table(table: dict) -> bool:
    return any(
        {"unit", "standards", "levels"} <= {label_role(c["text"]) for c in row}
        for row in table["rows"]
    )


def field_status(field: dict) -> str:
    """Absence requires positive source evidence. Missing extraction is unknown."""
    if field.get("status") == "conflict":
        return "conflict"
    if field.get("state") in {"unknown", "conversion_loss"}:
        return "unconfirmed"
    if field["value"] not in ("", [], None):
        return "present"
    if field.get("state") == "all_unselected" or (
        field["evidence"]
        and all(
            o["text"].strip() in {"미기재", "없음", "해당 없음", "해당없음", "미실시"}
            for o in field["evidence"]
        )
    ):
        return "source_absent"
    return "unconfirmed"


def field_state_counts(items: list[dict], *, legacy: bool = False) -> dict:
    counts = {name: dict.fromkeys(FIELD_STATUSES, 0) for name in FIELDS}
    for item in items:
        for name, field in item["fields"].items():
            status = field.get("status")
            if not status:
                status = field_status(field)
                if legacy and status == "unconfirmed" and "미기재" in field.get("reason", ""):
                    status = "source_absent"
            counts[name][status] += 1
    return counts


def cell_part(cell: dict, start: int, end: int) -> dict:
    """A subcell always addresses the unchanged converter cell."""
    raw = cell["raw"][start:end]
    return {**cell, "raw": raw, "text": visible(raw),
            "start": cell["start"] + start, "end": cell["start"] + end}


def title_cell(cell: dict) -> dict:
    """Remove only literal terminal annotations, preserving full source cell."""
    raw = cell["raw"]
    suffix = re.search(
        r"\s*\(\s*(?:\d+(?:\.\d+)?\s*점|\d+\s*회|"
        r"(?:프로젝트|실험[·ㆍ]실습|서[·ㆍ]논술형?)\s*평가)\s*\)\s*$", raw,
    )
    if not suffix:
        return cell
    end = suffix.start()
    while end and raw[end - 1].isspace():
        end -= 1
    return {**cell_part(cell, 0, end), "cell_raw": raw,
            "cell_start": cell["start"], "cell_end": cell["end"]}


def preceding_task(table: dict, tables: list[dict], text: str, section: dict) -> dict | None:
    """Only an adjacent numbered task heading plus an assessment form licenses it."""
    previous_end = tables[table["table"] - 1]["end"] if table["table"] else 0
    start = max(previous_end, section["locator"]["start"])
    gap = text[start:table["start"]]
    lines = list(re.finditer(r"(?m)^([^\r\n]*\S[^\r\n]*)$", gap))
    if not lines:
        return None
    line = lines[-1]
    if len(lines) > 1:
        previous = lines[-2]
        other = re.fullmatch(r"[\s#*\-]*(?:[가-하]|\d+)\s*[.)]\s*(.+)", previous[1])
        if (other and title_gate(visible(other[1]))["accepted"]
                and not re.search(r"학년\s*$|계획\s*$|세부기준\s*$", previous[1])):
            return None  # Multiple task headings require physical correspondence.
    match = re.fullmatch(
        r"[\s#*\-]*(?:[가-하]|\d+)\s*[.)]\s*(?:\(\s*(.+?)\s*\)"
        r"\s*영역\s*세부\s*평가\s*기준|(.+?))\s*", line[1],
    )
    if not match:
        return None
    group = 1 if match[1] else 2
    lo, hi = match.span(group)
    raw = line[1][lo:hi]
    if not title_gate(visible(raw))["accepted"]:
        return None
    roles = {label_role(c["text"]) for c in table["cells"]}
    if "standards" not in roles or not roles & {"elements", "rubric", "method"}:
        return None
    return {"raw": raw, "text": visible(raw), "start": start + line.start(1) + lo,
            "end": start + line.start(1) + hi, "table": table["table"],
            "row": -1, "col": 0, "rowspan": 1, "colspan": 1}


def split_form_labels(table: dict, conversion: dict) -> dict:
    rows = []
    for row in table["rows"]:
        expanded = []
        for cell in row:
            raw = cell["raw"]
            # Only this complete, ordered form grammar licenses a collapsed
            # title. Dates/method choices cannot supply the title slot.
            match = re.fullmatch(
                r"\s*(수행\s*과제)\s+(.+?)\s+(반영\s*비율)\s+(\d+(?:\.\d+)?\s*%)\s*",
                raw, re.S,
            )
            parts = []
            if match and title_gate(visible(match[2]))["accepted"] and not re.fullmatch(
                r"실험[·ㆍ･]?실습|서술[·ㆍ･]?논술|구술[·ㆍ･]?발표|프로젝트", visible(match[2])
            ):
                parts = [cell_part(cell, *match.span(n)) for n in (1, 2, 3, 4)]
            unit = re.fullmatch(r"\s*(관련\s*단원)\s+(.+?)\s*", raw, re.S)
            if unit:
                parts = [cell_part(cell, *unit.span(n)) for n in (1, 2)]
            verified = conversion.get("verified_cell_splits", {}).get(str(cell["start"]))
            if verified and verified["cell_raw"] == raw:
                parts = [cell_part(cell, p["start"], p["end"]) for p in verified["parts"]]
                for part in parts:
                    part["source_cell_proof"] = verified["proof"]
            expanded.extend(parts or [cell])
        rows.append(expanded)
    return {**table, "rows": rows, "cells": [c for row in rows for c in row]}


def form_structures(table: dict) -> list[dict]:
    """Label/value forms, possibly several vertically stacked forms per table."""
    pairs = []
    for row in table["rows"]:
        for index, header in enumerate(row[:-1]):
            role = label_role(header["text"])
            if role == "task" and "성취수준별" in row[index + 1]["text"]:
                continue  # This is a column header, not a task value.
            if role and not label_role(row[index + 1]["text"]):
                pairs.append((header, row[index + 1], role))
    starts = []
    active_roles = set()
    for header, _, role in pairs:
        if role in TITLE_ROLES:
            if not starts or role in active_roles:
                if starts and starts[-1] == header["row"]:
                    structure = new_structure(
                        table, table["cells"], defaultdict(list), "text_candidate"
                    )
                    structure["review_reasons"].append("동일 행 복수 제목 셀·열 소유 미확정")
                    return [structure]
                starts.append(header["row"])
                active_roles = set()
            active_roles.add(role)
    if not starts:
        return []
    output = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(table["rows"])
        cells = [c for c in table["cells"] if start <= c["row"] < end]
        claims = defaultdict(list)
        for header, value, role in pairs:
            if not start <= header["row"] < end:
                continue
            # Include all value cells, including the next row of a rowspan label.
            for cell in cells:
                if (
                    header["row"] <= cell["row"] < header["row"] + header["rowspan"]
                    and cell["start"] > header["start"]
                    and cell["row"] == value["row"]
                    and cell["start"] >= value["start"]
                ):
                    if label_role(cell["text"]):
                        break
                    claims[role].append((cell, header))
            if header["rowspan"] > 1:
                claims[role].extend(
                    (c, header)
                    for c in cells
                    if header["row"] < c["row"] < header["row"] + header["rowspan"]
                    and c["col"] > header["col"]
                    and not label_role(c["text"])
                )
        # Codes below an explicit standards column belong to this form. Codes
        # mentioned in unrelated instruction/elements cells are not code fields.
        standard_headers = [c for c in cells if label_role(c["text"]) == "standards"]
        for header in standard_headers:
            claims["standards"].extend(
                (c, header)
                for c in cells
                if c["row"] > header["row"]
                and c["col"] == header["col"]
                and c["colspan"] == header["colspan"]
                and CODE_RE.search(c["raw"])
            )
        rubric_headers = [c for c in cells if label_role(c["text"]) == "rubric"]
        for header in rubric_headers:
            claims["rubric"].extend(
                (c, header)
                for c in cells
                if c["row"] > header["row"]
                and c["col"] == header["col"]
                and c["colspan"] == header["colspan"]
                and not label_role(c["text"])
            )
        structure = new_structure(table, cells, claims, "form")
        for header in cells:
            if re.fullmatch(r"평가과제(?:\s*\(배점\))?", re.sub(r"\s+", "", header["text"])):
                below = [
                    c
                    for c in cells
                    if c["row"] == header["row"] + 1
                    and c["col"] == header["col"]
                    and c["rowspan"] > 1
                ]
                if len(below) == 1:
                    claims["task"].append((below[0], header))
                    amount = re.search(r"\(\s*(\d+(?:\.\d+)?\s*점)\s*\)\s*$", below[0]["raw"])
                    if amount:
                        claims["score"].append((cell_part(below[0], *amount.span(1)), header))
        for role in TITLE_ROLES:
            titles = {c["text"] for c, _ in claims.get(role, []) if c["text"]}
            if len(titles) > 1:
                structure["review_reasons"].append("동일 제목 라벨 복수 값·항목 경계 미확정")
                break
        output.append(structure)
    return output


def row_structures(table: dict) -> list[dict]:
    for row in table["rows"]:
        headers = {c["col"]: c for c in row if label_role(c["text"])}
        roles = {label_role(c["text"]) for c in headers.values()}
        if len(roles) < 2 or not roles & TITLE_ROLES:
            continue
        if any(c["text"] and not label_role(c["text"]) for c in row):
            continue
        output = []
        for row_number in range(row[0]["row"] + 1, len(table["rows"])):
            cells = list(
                {c["start"]: c for (r, _), c in table["grid"].items() if r == row_number}.values()
            )
            if not cells or all(label_role(c["text"]) for c in cells):
                continue
            if all(re.fullmatch(r"[:\-\s]*", c["text"]) for c in cells):
                continue
            claims = defaultdict(list)
            for col, header in headers.items():
                cell = table["grid"].get((row_number, col))
                if cell and cell["rowspan"] == 1 and cell["text"]:
                    claims[label_role(header["text"])].append((cell, header))
            kinds = [c["text"] for c, _ in claims.get("kind", [])]
            # Kind rowspans are context, never copied as item fields.
            for col, header in headers.items():
                if label_role(header["text"]) == "kind":
                    cell = table["grid"].get((row_number, col))
                    if cell:
                        kinds.append(cell["text"])
            if kinds and not any("수행" in kind for kind in kinds):
                continue
            if any(claims.get(r) for r in TITLE_ROLES):
                structure = new_structure(table, cells, claims, "row")
                structure["row"] = row_number
                structure["table_role"] = (
                    "summary"
                    if ({"score", "weight"} <= roles or "score_weight" in roles)
                    else "row_item"
                )
                output.append(structure)
        return output
    return []


def column_structures(table: dict, section: dict) -> list[dict]:
    """The explicit performance group licenses leaf columns, never exam columns."""
    groups = [c for c in table["cells"] if re.fullmatch(
        r"(?:수행평가(?:\((?:\d+(?:\.\d+)?[%％]|과정중심평가)\))?|과정중심평가)",
        re.sub(r"\s+", "", c["text"]),
    )]
    groups = [c for c in groups if not any(
        other["row"] < c["row"] and other["col"] <= c["col"]
        and c["col"] + c["colspan"] <= other["col"] + other["colspan"]
        for other in groups
    )]
    output = []
    grade_cells = [
        c for c in table["cells"] if re.fullmatch(r"[123]학년", c["text"].replace(" ", ""))
    ]
    matching_grades = [c for c in grade_cells if c["text"].startswith(str(section["grade"]))]
    if grade_cells and not matching_grades:
        return []
    for group in groups:
        headers = [c for c in table["cells"] if c["col"] + c["colspan"] <= group["col"]]
        combined = any(
            re.sub(r"\s+", "", c["text"]) in {"학기영역", "시기/영역"} for c in headers
        )
        for col in range(group["col"], group["col"] + group["colspan"]):
            column = list({
                c["start"]: c for (r, ccol), c in table["grid"].items()
                if ccol == col and (r > group["row"] or matching_grades)
                and c is not group
            }.values())
            if not column:
                continue
            claims, shared = defaultdict(list), []
            for cell in column:
                if cell["row"] <= group["row"]:
                    continue
                left = sorted(
                    (h for h in headers if h["row"] <= cell["row"] < h["row"] + h["rowspan"]),
                    key=lambda h: h["col"],
                )
                labeled = [h for h in left if label_role(h["text"])]
                header = labeled[-1] if labeled else None
                role = label_role(header["text"]) if header else None
                if role == "weight" and any(
                    re.fullmatch(r"서[·ㆍ･・]?논술형?|논술형", re.sub(r"\s+", "", h["text"]))
                    for h in left
                ):
                    role = "essay_weight"
                if role == "area_method":
                    role = "method" if (AREA_TITLE_RE.fullmatch(cell["text"])
                                        or header["rowspan"] > 1
                                        and cell["row"] == header["row"]) else "assessment_area"
                # A method/type header spanning two rows supplies a type first,
                # followed by the literal task in the next row of that column.
                if (role == "method" and header["rowspan"] > 1
                        and header["row"] < cell["row"]
                        and title_gate(cell["text"])["accepted"]):
                    if title_content_role(cell["text"], "assessment_area") == "task":
                        role = "task"
                    else:
                        role = "task"  # Literal title subrow, including portfolio.
                if role is None and combined:
                    if cell["row"] == group["row"] + 1 or any(
                        re.sub(r"\s+", "", h["text"]) == "시기/영역"
                        and h["row"] == cell["row"] for h in left
                    ):
                        if not (AREA_TITLE_RE.fullmatch(cell["text"]) and any(
                            re.sub(r"\s+", "", h["text"]) == "시기/영역" for h in left
                        )):
                            role, header = "assessment_area", group
                    elif any(
                        t["rowspan"] == 1 and cell["row"] == t["row"] + 1
                        for t, _ in claims.get("assessment_area", [])
                    ):
                        claims["method"].append((cell, group))
                        role, header = "timing", group
                if not role:
                    continue
                if (role == "points" and cell["colspan"] == 1
                        and not any(label_role(h["text"]) in {"score", "score_weight"}
                                    for h in headers)):
                    claims["points"].append((cell, header))
                    role = "score"  # Maximum of this explicit performance leaf.
                if cell["colspan"] > 1:
                    shared.append((role, cell, header))
                    # Aggregated numeric values cannot be allocated to items.
                    if role in NUMERIC_FIELDS | {"score_weight"}:
                        continue
                    # Never inherit a value spanning outside the performance group.
                    if not (group["col"] <= cell["col"] and
                            cell["col"] + cell["colspan"] <= group["col"] + group["colspan"]):
                        continue
                    cell = {**cell, "shared_columns": list(
                        range(cell["col"], cell["col"] + cell["colspan"])
                    )}
                claims[role].append((cell, header))
            title_cells = [c for role in TITLE_ROLES for c, _ in claims.get(role, [])]
            anchor = matching_grades[0] if matching_grades else (
                title_cells[0] if title_cells else column[0]
            )
            if not section["locator"]["start"] <= anchor["start"] < section["locator"]["end"]:
                continue
            structure = new_structure(table, column, claims, "column")
            structure.update(anchor=anchor, column=col, shared_fields=shared)
            # Column ownership is explicit even when merged title cells overlap.
            structure["group"] = group
            output.append(structure)
    return output


def task_number(structure: dict) -> str:
    for role in ("task_no", "task", "title", "assessment_area"):
        for cell, _ in structure["claims"].get(role, []):
            if TASK_NO_RE.fullmatch(cell["text"]) or (
                role == "task_no" and re.fullmatch(r"\d+", cell["text"])
            ):
                return cell["text"]
    return ""


def connect_tables(
    structures: list[dict],
    tables: list[dict],
    text: str,
    section: dict,
    conversion: dict | None = None,
) -> list[dict]:
    """Join an immediately following rubric only with an explicit matching number."""
    used = {s["table"] for s in structures}
    pending = []
    physical = (conversion or {}).get("physical", {})
    if __package__:
        from .middle_physical import continuation_proof
    else:
        from middle_physical import continuation_proof
    for table in tables:
        if not (
            section["locator"]["start"]
            <= table["start"]
            < table["end"]
            <= section["locator"]["end"]
        ):
            continue
        if table["table"] in used:
            continue
        cells = table["cells"]
        physical_owners = []
        for s in structures:
            if s["layout"] != "form":
                continue
            last = s["links"][-1]["table"] if s["links"] else s["table"]
            if last + 1 == table["table"]:
                proof = continuation_proof(tables[last], table, text, physical)
                if proof:
                    physical_owners.append((s, proof))
        if len(physical_owners) == 1:
            owner, proof = physical_owners[0]
            owner["cells"].extend(cells)
            owner["links"].append(
                {"table": table["table"], "start": table["start"], "end": table["end"], **proof}
            )
            continuation_claims(owner, table)
            used.add(table["table"])
            continue
        if not cells or not any(label_role(c["text"]) in {"rubric", "standards"} for c in cells):
            continue
        numbers = {
            row[index + 1]["text"]
            for row in table["rows"]
            for index, cell in enumerate(row[:-1])
            if label_role(cell["text"]) in {"task_no", "task"}
            and TASK_NO_RE.fullmatch(row[index + 1]["text"])
        }
        previous = [
            s for s in structures if s["table"] == table["table"] - 1 and task_number(s) in numbers
        ]
        table_start = table["start"]
        gap_start = tables[table["table"] - 1]["end"] if table["table"] else 0
        gap = text[gap_start:table_start]
        continuous = not re.sub(r"\s|\f|<!--\s*page\s*\d+\s*-->", "", gap)
        in_section = (
            section["locator"]["start"] <= table_start < table["end"] <= section["locator"]["end"]
        )
        if len(previous) == 1 and len(numbers) == 1 and continuous and in_section:
            owner = previous[0]
            owner["cells"].extend(cells)
            owner["links"].append(
                {
                    "table": table["table"],
                    "task_no": task_number(owner),
                    "basis": "같은 구간·과제번호 일치·인접 표 행 연속",
                    "start": table["start"],
                    "end": table["end"],
                }
            )
            owner["claims"]["standards"].extend(
                (c, None) for c in cells if CODE_RE.search(c["raw"])
            )
            headers = [c for c in cells if label_role(c["text"]) == "rubric"]
            for header in headers:
                owner["claims"]["rubric"].extend(
                    (c, header)
                    for c in cells
                    if c["row"] > header["row"] and c["col"] == header["col"]
                )
        else:
            candidate = new_structure(table, cells, defaultdict(list), "unlinked_table")
            candidate["review_reasons"].append("별도 표 연결 미확정")
            pending.append(candidate)
    return pending


def continuation_claims(owner: dict, table: dict) -> None:
    """Read cells only after physical ownership is established."""
    claims = owner["claims"]
    for row in table["rows"]:
        for n, header in enumerate(row[:-1]):
            role = label_role(header["text"])
            if role and role not in TITLE_ROLES and not label_role(row[n + 1]["text"]):
                claims[role].append((row[n + 1], header))
    if claims.get("standards"):
        claims["standards"].extend((c, None) for c in table["cells"] if CODE_RE.search(c["raw"]))
    else:
        headers = [
            c
            for c in table["cells"]
            if label_role(c["text"]) == "standards"
            or re.fullmatch(r"성취기준\s+성취기준별\s*성취수준", c["text"])
        ]
        if headers:
            first = min(c["row"] for c in headers)
            stop = min(
                (
                    c["row"]
                    for c in table["cells"]
                    if c["row"] > first
                    and label_role(c["text"]) in {"method", "elements", "rubric"}
                ),
                default=len(table["rows"]),
            )
            claims["standards"].extend(
                (c, headers[0])
                for c in table["cells"]
                if first < c["row"] < stop and CODE_RE.search(c["raw"])
            )
    for c in table["cells"]:
        match = re.fullmatch(
            r"(영역\s*만점)\s*\((반영\s*비율)\)\s*(\d+)\s*\((\d+%)\)\s*기본\s*점수",
            c["raw"],
        )
        if match:
            claims["score"].append((cell_part(c, *match.span(3)), cell_part(c, *match.span(1))))
            claims["weight"].append((cell_part(c, *match.span(4)), cell_part(c, *match.span(2))))
        wrap = re.fullmatch(
            r"영역\s*<br\s*/?>\s*(\d+)\s*\((\d+%)\)\s*<br\s*/?>\s*"
            r"(만점)\s*\((반영\s*비율)\)",
            c["raw"],
            re.I,
        )
        if wrap:
            claims["score"].append((cell_part(c, *wrap.span(1)), cell_part(c, *wrap.span(3))))
            claims["weight"].append((cell_part(c, *wrap.span(2)), cell_part(c, *wrap.span(4))))
    # The fragment preserves all original level/criterion rows as a rubric. It
    # does not turn qualitative scales into points or sum numeric row maxima.
    claims["rubric"].extend(
        (c, None) for c in table["cells"] if c["text"] and not label_role(c["text"])
    )


def finalize(structure: dict, section: dict, conversion: dict) -> dict:
    claims = structure["claims"]
    # Terminal points are a maximum only in a title slot, never rubric elements.
    for role in ("task", "title", "assessment_area"):
        for cell, header in list(claims.get(role, [])):
            amount = re.search(r"\(\s*(\d+(?:\.\d+)?\s*점)\s*\)\s*$", cell["raw"])
            if amount and title_gate(title_cell(cell)["text"])["accepted"]:
                part = cell_part(cell, *amount.span(1))
                if not any(c["start"] == part["start"] for c, _ in claims["score"]):
                    claims["score"].append((part, header))
    observations = {name: [] for name in FIELDS}
    for role, pairs in claims.items():
        field = "task_text" if role == "task" else role
        if field not in observations and role != "score_weight":
            continue
        seen = set()
        for cell, header in pairs:
            if cell["start"] in seen:
                continue
            seen.add(cell["start"])
            obs = evidence(cell, conversion, header)
            compound = role == "score_weight" or (
                role in {"score", "weight"}
                and "점" in cell["raw"]
                and re.search(r"[%％]", cell["raw"])
                and COMPOUND_NUMBER_RE.fullmatch(cell["raw"])
            )
            if compound:
                obs["compound_numeric"] = True
                observations["score"].append(obs)
                observations["weight"].append(dict(obs))
            else:
                observations[field].append(obs)
    title_candidates = []
    for role in ("task", "title", "assessment_area", "task_no"):
        for cell, header in claims.get(role, []):
            cell = title_cell(cell)
            if title_gate(cell["text"])["accepted"]:
                content_role = title_content_role(cell["text"], role)
                title_candidates.append((content_role, cell, header, role))
    title = None
    title_role = None
    if title_candidates:
        title_role, cell, header, source_role = min(
            title_candidates, key=lambda c: ("task", "assessment_area", "task_no").index(c[0])
        )
        title = evidence(cell, conversion, header)
    if title:
        observations["title"] = [
            evidence(c, conversion, h) for content, c, h, role in title_candidates
            if content == title_role and role == source_role
        ]
    identity_title = next(
        (
            c for role in ("title", "assessment_area", "task", "task_no")
            for c, _ in claims.get(role, []) if title_gate(c["text"])["accepted"]
        ), None,
    )
    fields = {name: field_value(name, obs) for name, obs in observations.items()}
    checks = [
        row
        for row in conversion.get("method_check_comparison", {}).get("rows", [])
        if row.get("source_sha256") == conversion.get("sha256")
        and conversion.get("method_check_comparison", {}).get("structured_text_sha256")
        == conversion.get("text_sha256")
        and any(
            row.get("start") == obs["locator"]["start"] and row.get("end") == obs["locator"]["end"]
            for obs in observations["method"]
        )
    ]
    fields["method"] = method_values(
        observations["method"],
        conversion_loss=bool(any(row["status"] in {"loss", "conflict"} for row in checks)),
    )
    fields["method"]["conversion_comparison"] = checks
    fields["standards"] = standard_values(observations["standards"])
    if not fields["task_no"]["value"] and task_number(structure):
        fields["task_no"] = field_value(
            "task_no",
            [
                evidence(c, conversion, h)
                for pairs in claims.values()
                for c, h in pairs
                if c["text"] == task_number(structure)
            ][:1],
        )
    cells = structure["cells"]
    anchor = structure.get("anchor") or (cells[0] if cells else section["locator"])
    left, right = min(c["start"] for c in cells), max(c["end"] for c in cells)
    reasons = list(structure["review_reasons"])
    if conversion.get("conversion_status") == "fallback_text_only":
        reasons.append("PDF 평문 폴백·표 구조 미보존")
    if any(
        re.search(r"(?:영역\s*만점|반영\s*비율|평가\s*시기)\s*[:：]?\s*\d", c["text"])
        for role in TITLE_ROLES
        for c, _ in claims.get(role, [])
    ):
        reasons.append("제목 셀에 필드 라벨 혼입·경계 미확정")
    if not title:
        reasons.append("원문 제목 셀 미확정")
    if structure["layout"] in {"text_candidate", "unlinked_table"}:
        reasons.append("행·열·셀 소유 범위 미입증")
    if not section.get("boundary_verified"):
        reasons.append("S5 과목 경계 미확정")
    if fields["method"]["state"] in {"conversion_loss", "unknown"}:
        reasons.append(fields["method"]["reason"])
    # Inspect only the item's owned cells, never a complete multi-item table.
    subject = classify_subject(
        "\n".join(c["raw"] for c in cells),
        verified_science=section.get("boundary_verified", False),
        header=section.get("header"),
    )
    if subject["status"] != "target":
        reasons.append("항목 과목 판정 " + subject["status"])
    item_id = digest_id(
        "item_",
        section.get("document_id"),
        section.get("child_id"),
        section["segment_id"],
        section.get("section_id"),
        section.get("grade"),
        section.get("semester"),
        fields["task_no"]["value"],
        anchor["start"],
        identity_title["start"] if identity_title else left,
        structure.get("row"),
        structure.get("column"),
        IDENTITY_VERSION,
    )
    for field in fields.values():
        for obs in field["evidence"]:
            obs["owner_item_id"] = item_id
    if structure["layout"] in {"text_candidate", "unlinked_table"}:
        for field in fields.values():
            if not field["value"]:
                field["reason"] = "항목 경계·필드 소유 미확정"
    for role, _, _ in structure["shared_fields"]:
        if role in fields and not fields[role]["value"]:
            fields[role]["reason"] = "다항목 병합셀 공통값·항목별 배분 불가"
    for field in fields.values():
        field["status"] = field_status(field)
        if field["status"] == "source_absent":
            field["reason"] = "원문에 부재·미선택 명시"
    if any(field["status"] == "conflict" for field in fields.values()):
        reasons.append("동일 항목 필드 복수 관측값·확정 보류")
    return {
        "item_id": item_id,
        "document_id": section.get("document_id"),
        "child_id": section.get("child_id"),
        "segment_id": section["segment_id"],
        "section_id": section.get("section_id"),
        "grade": section.get("grade"),
        "semester": section.get("semester"),
        "rule_version": RULE_VERSION,
        "layout": structure["layout"],
        "table_role": structure.get(
            "table_role",
            "summary"
            if structure["layout"] == "column"
            else "detail"
            if structure["layout"] == "form"
            else "unresolved",
        ),
        "candidate_role": structure.get("candidate_role", "other"),
        "role_basis": structure.get("role_basis", "표 역할 미확인"),
        "layout_position": {
            "table": structure["table"],
            "row": structure.get("row"),
            "col": structure.get("column"),
        },
        "boundary_evidence": {
            "section_locator": section["locator"],
            "adjacent_task_heading": evidence(structure["adjacent_task_heading"], conversion)
            if structure.get("adjacent_task_heading") else None,
            "performance_group": evidence(structure["group"], conversion)
            if structure.get("group") else None,
            "appendix": section.get("appendix_boundary_evidence"),
            "grade_anchor": evidence(structure["anchor"], conversion)
            if structure.get("anchor")
            else None,
        },
        "locator": text_locator(left, right, conversion),
        "fields": fields,
        "title_role": title_role,
        "title_authenticity": (
            "source_text_candidate"
            if title and structure["layout"] == "text_candidate"
            else "source_cell"
            if title
            else "unresolved"
        ),
        "title_specificity_score": title_gate(title["text"])["specificity_score"] if title else 0,
        "title_generated": False,
        "links": structure["links"],
        "completeness_status": "continuation_linked_not_certified_complete"
        if structure["links"]
        else "completion_unconfirmed",
        "owned_ranges": [evidence(c, conversion)["locator"] for c in cells],
        "shared_fields": [
            {
                "field": role,
                **evidence(c, conversion, h),
                "shared_columns": list(range(c["col"], c["col"] + c["colspan"])),
                "reason": "다항목 병합셀 공통값·항목별 배분 불가",
            }
            for role, c, h in structure["shared_fields"]
        ],
        "extraction_status": "review" if reasons else "bounded",
        "review_reasons": list(dict.fromkeys(reasons)),
        "subject_status": subject["status"],
        "public_eligible": False,
    }


def ownership_errors(items: list[dict]) -> list[dict]:
    owners = defaultdict(set)
    field_names = defaultdict(set)
    invalid_shared = []
    for item in items:
        if item.get("candidate_role") == "summary_duplicate" and item.get("identity_relation"):
            continue  # Alias of its detail, not an independent source owner.
        for name, field in item["fields"].items():
            for obs in field["evidence"]:
                loc = obs["locator"]
                if obs.get("shared_columns") and any(
                    s["locator"]["start"] <= loc["start"] <= loc["end"] <= s["locator"]["end"]
                    and s.get("shared_columns") == obs["shared_columns"]
                    and item["layout_position"]["col"] in s["shared_columns"]
                    and s["shared_columns"] == list(range(
                        loc["col"], loc["col"] + loc.get("colspan", 1)
                    )) and loc.get("colspan", 1) > 1
                    for s in item["shared_fields"]
                ):
                    continue
                if obs.get("shared_columns"):
                    invalid_shared.append({
                        "field": [name], "start": loc["start"], "end": loc["end"],
                        "item_ids": [item["item_id"]], "reason": "병합셀 공유 범위 미입증",
                    })
                key = (item["document_id"], item["child_id"], loc["start"], loc["end"])
                owners[key].add(item["item_id"])
                field_names[key].add(name)
    return invalid_shared + [
        {"field": sorted(field_names[key]), "start": key[2], "end": key[3], "item_ids": sorted(ids)}
        for key, ids in owners.items()
        if len(ids) > 1
    ]


def extract_middle_items(
    text: str,
    section: dict,
    conversion: dict | None = None,
    title_hints: tuple[str, ...] = (),
) -> list[dict]:
    """Explicit science entry point. Existing math parser callers are unchanged."""
    conversion = conversion or {"text": text, "converter": "synthetic"}
    conversion = {**conversion, "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    start, end = section["locator"]["start"], section["locator"]["end"]
    if not 0 <= start <= end <= len(text):
        raise ValueError("S4/S5 locator outside converter text")
    if section.get("grade") not in {1, 2} or section.get("status") != "target":
        return []
    all_tables = source_tables(text)
    tables = [t for t in all_tables if t["start"] < end and t["end"] > start]
    structures = []
    for table in tables:
        if not table["structure_verified"]:
            cell = {
                "raw": "",
                "text": "",
                "start": max(start, table["start"]),
                "end": min(end, table["end"]),
            }
            structure = new_structure(table, [cell], defaultdict(list), "text_candidate")
            structure["review_reasons"].append("중첩·불완전 표 구조 미확정")
            structures.append(structure)
            continue
        if teaching_table(table) or standards_table(table):
            role, basis = (
                ("teaching_plan", "단원·일정 또는 수업·평가 연계 머리글·방법은 참고")
                if teaching_table(table) else
                ("general_standards", "단원·성취기준·성취수준 머리글·항목 근거 제외")
            )
            structure = new_structure(table, table["cells"], defaultdict(list), "unlinked_table")
            structure.update(candidate_role=role, role_basis=basis)
            structure["review_reasons"].append(basis)
            structures.append(structure)
            continue
        columns = column_structures(table, section)
        if columns:
            structures.extend(columns)
            continue
        # Form/row bounds must fit inside their S4/S5 section.
        if not start <= table["start"] < table["end"] <= end:
            continue
        found = row_structures(table) or form_structures(split_form_labels(table, conversion))
        external = conversion.get("physical", {}).get("titles", {}).get(str(table["table"]))
        heading = preceding_task(table, all_tables, text, section)
        external = external or heading
        if (
            external
            and not found
            and all(label_role(c["text"]) not in TITLE_ROLES for c in table["cells"])
        ):
            # A virtual label supplies structure only; the title value and all
            # locators still address literal converter text verified in the PDF.
            claims = defaultdict(list)
            claims["title"].append((external, None))
            structure = new_structure(table, [external, *table["cells"]], claims, "form")
            continuation_claims(structure, table)
            found = [structure]
        elif external and len(found) == 1 and (
            external is not heading or not any(
                title_gate(c["text"])["accepted"]
                for role in ("task", "title") for c, _ in found[0]["claims"].get(role, [])
            )
        ):
            found[0]["cells"].append(external)
            found[0]["external_task"] = external
            found[0]["claims"]["task"].append((external, None))
        if heading and len(found) == 1:
            found[0]["adjacent_task_heading"] = heading
        for structure in found:
            title_roles = set(structure["claims"]) & TITLE_ROLES
            if title_roles == {"task_no"}:
                continue
            structures.append(structure)
    structures.extend(connect_tables(structures, all_tables, text, section, conversion))
    # A summary row and a detailed form can repeat a numbered task. Without
    # explicit row continuity they remain separate review candidates.
    by_number = defaultdict(list)
    for structure in structures:
        if task_number(structure):
            by_number[task_number(structure)].append(structure)
    for group in by_number.values():
        if len(group) > 1:
            for structure in group:
                if structure["layout"] == "row":
                    structure["review_reasons"].append(
                        "동일 과제번호 상세표와 동일성·연속성 확인 필요"
                    )
    occupied = [(t["start"], t["end"]) for t in tables]
    # Flat PDF labels and hints locate candidates only. Do not infer cell edges.
    pattern = re.compile(r"(?m)^\s*(?:수행\s*과제|평가\s*영역(?:명)?|평가\s*과제)\s*[:：]?\s*$")
    candidates = [(m.start(), m.end()) for m in pattern.finditer(text, start, end)]
    for hint in title_hints:
        if hint:
            candidates.extend(
                (m.start(), m.end())
                for m in re.finditer(re.escape(hint), text)
                if start <= m.start() < m.end() <= end
            )
    for left, right in sorted(set(candidates)):
        if any(a <= left < b for a, b in occupied):
            continue
        after = re.match(r"[^\S\n]*\n([^\n]+)", text[right:end])
        candidate_left, candidate_right = left, right
        if after and title_gate(after[1].strip())["accepted"]:
            candidate_left = right + after.start(1)
            candidate_right = right + after.end(1)
        cell = {
            "raw": text[candidate_left:candidate_right],
            "text": visible(text[candidate_left:candidate_right]),
            "start": candidate_left,
            "end": candidate_right,
        }
        claims = defaultdict(list)
        if title_gate(cell["text"])["accepted"]:
            claims["title"].append((cell, None))
        structure = new_structure({"table": None}, [cell], claims, "text_candidate")
        structure["review_reasons"].append("평문 변환·표 구조 미보존")
        structures.append(structure)
    if not structures:
        cell = {"raw": "", "text": "", "start": start, "end": end}
        structure = new_structure({"table": None}, [cell], defaultdict(list), "text_candidate")
        structure["review_reasons"].append("구간 내 수행 항목 구조 미식별·전수 대조 필요")
        structures.append(structure)
    by_identity = {}
    for structure in structures:
        structure["candidate_role"], structure["role_basis"] = candidate_role(
            structure, all_tables, text
        )
        if "동일 과제번호 상세표와 동일성·연속성 확인 필요" in structure["review_reasons"]:
            structure["candidate_role"] = "summary_duplicate"
            structure["role_basis"] = "동일 과제번호 상세와 반복되는 요약행·동일성 추가 검토"
        item = finalize(structure, section, conversion)
        by_identity.setdefault(item["item_id"], item)
    results = list(by_identity.values())
    errors = ownership_errors(results)
    invalid = {i for e in errors for i in e["item_ids"]}
    for item in results:
        item["ownership_status"] = "conflict" if item["item_id"] in invalid else "passed"
        if item["ownership_status"] == "conflict":
            item["extraction_status"] = "review"
            item["review_reasons"].append("항목 간 필드 소유 충돌")
    return results
