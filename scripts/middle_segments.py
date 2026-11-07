"""Offline, source-bounded document segmentation. Subject decisions belong to S5.

Offsets are Python Unicode character offsets into the *unaltered* converter text,
with an exclusive end. A segment is a review candidate, never a publication grant.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import defaultdict
from difflib import SequenceMatcher

RULE_VERSION = "middle-segments-v2"
STATUS_DEFINITIONS = {
    "normal": "중1·중2 학년 식별. 과목·교육과정·공개 여부는 후속 단계 검토",
    "grade3_quarantined": "중3 구간 격리",
    "grade_unresolved": "학년 근거 없음 또는 충돌. 비공개 검토",
    "semester_unresolved": "구간 학기 근거 없음 또는 충돌. 비공개 검토",
    "superseded": "본문 동일 판본 중 공시 파일 순번에 따른 대표 외 판본",
    "single": "같은 범위의 비교 가능한 다른 판본 없음",
    "representative": "정규화 본문 동일 판본 중 공시 파일 순번에 따른 대표",
    "version_conflict": "실질 본문 차이 또는 공시 순서 불명. 양쪽 비공개 검토",
    "free_semester_marker": "자유학기·P·과정 중심 평가 표지. 구간 유지",
    "subject_heading_unresolved": "과목 머리글 미식별. 비공개 검토",
    "conversion_review": "변환 실패·텍스트층 없는 페이지 포함. 비공개 검토",
}
GRADE_RE = re.compile(
    r"(?<![가-힣A-Za-z\d])(?P<level>중학교|고등학교|초등학교|중|고)\s*"
    r"(?P<explicit>[123])(?!\d)(?:\s*학년)?|(?<!\d)(?P<bare>[123])\s*학년|"
    r"(?<!\d)\(\s*(?P<parenthesized>[123])\s*\)\s*학년"
)
SEMESTER_RE = re.compile(r"(?<!\d)\(?\s*([12])\s*\)?\s*학기")
PLAN_RE = re.compile(r"교수\s*[·ㆍ‧･⦁⋅․-]?\s*학습|평가\s*(?:운영|세부)?\s*계획|교과\s*교육\s*과정")
CELL_RE = re.compile(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>", re.S | re.I)
FREE_RE = re.compile(r"자유\s*학기|과정\s*중심\s*평가|(?<![A-Za-z])P(?![A-Za-z])")


def digest_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return prefix + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def document_identifier(sha256: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ValueError("document identity requires a full SHA-256")
    return "doc_" + sha256


def child_identifier(parent_sha256: str, child: dict) -> str:
    return digest_id(
        "child_",
        document_identifier(parent_sha256),
        child["member_index"],
        child["member_name"],
        child.get("sha256"),
    )


def segment_case_identifier(segment_id: str, curriculum: str, subject: str) -> str:
    """Opt-in case identity. The existing math case_identifier stays unchanged."""
    if not segment_id.startswith("seg_"):
        raise ValueError("segment case requires a segment ID")
    return digest_id("case_", segment_id, curriculum, subject)


def extract_grade_evidence(
    text: str,
    source: str = "body_heading",
    school_level: str | None = None,
    offset: int = 0,
) -> list[dict]:
    evidence = []
    for match in GRADE_RE.finditer(text):
        label = match["level"] or ""
        level = {
            "중": "middle",
            "중학교": "middle",
            "고": "high",
            "고등학교": "high",
            "초등학교": "elementary",
        }.get(label)
        if school_level and level and school_level != level:
            continue
        evidence.append(
            {
                "grade": int(match["explicit"] or match["bare"] or match["parenthesized"]),
                "source": source,
                "school_level": level,
                "text": match.group(),
                "start": offset + match.start(),
                "end": offset + match.end(),
            }
        )
    return evidence


def extract_grades(text: str, school_level: str | None = None) -> list[int]:
    return sorted(
        {
            item["grade"]
            for item in extract_grade_evidence(
                text,
                school_level=school_level,
            )
        }
    )


def visible(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]*>", " ", value)).strip().strip("*#| ")


def subject_heading_key(clean: str) -> str | None:
    """Require a title-shaped complete line, including subjects without 과 suffix."""
    # PDF layout can concatenate a school footer or explicit cover metadata
    # onto the title. Recognition strips these only; raw text/offsets stay intact.
    clean = re.sub(r"(?<=계획)\s*[가-힣]{2,20}중학교$", "", clean)
    clean = re.sub(
        r"\s*대상\s*[:：]\s*[123]\s*학년(?:\s+담당\s*교사\s*[:：].*)?$", "", clean,
    )
    plan = PLAN_RE.search(clean)
    if (
        not plan
        or not re.search(r"계획|교과\s*교육\s*과정", clean)
        or re.search(r"(?:[.·…]{3,}|\t)\s*\d+\s*$", clean)
    ):
        return None
    # Only title words may follow the subject. This excludes policy sentences
    # such as '기술·가정과 평가는 ... 교수·학습 ... 계획하여 ...'.
    tail = re.sub(r"[\s·ㆍ‧･⦁⋅․-]+", "", clean[plan.start() :])
    tail = re.sub(r"교수|학습|지도|및|평가|운영|세부|계획|교과|교육|과정|[ABC]", "", tail)
    if tail:
        return None
    label = clean[: plan.start()]
    label = re.sub(r"20\d{2}\s*(?:학년도?|년도)", "", label)
    label = SEMESTER_RE.sub("", label)
    label = GRADE_RE.sub("", label)
    label = re.sub(r"^[\s\d|.()ⅠⅡⅢⅣⅤ\uf000]+", "", label)
    label = label.replace("(", "").replace(")", "").strip()
    if re.search(r"수행|지필|평가|영역별|비율|교과별|전과목|세부|학습|지도|및", label):
        return None
    if not re.fullmatch(r"[가-힣A-Za-z\s·ㆍ‧･⦁⋅․/•\[\]]{1,40}", label):
        return None
    label = re.sub(r"(?:\[[ABC]\]|[ABC])(?=과?$)", "", label)
    return re.sub(r"\s+", "", label).removesuffix("과")


def metadata_events(text: str) -> tuple[list[dict], list[dict]]:
    """Use explicit school/grade/term/subject columns as cover boundaries."""
    headings, grades = [], []
    pattern = re.compile(
        r"(?m)^\|[^\n]*학교명[^\n]*\|[^\n]*\n"
        r"\|[ :|\-]+\n\|[^\n]*\|[^\S\n]*(?:\n|$)"
    )
    for match in pattern.finditer(text):
        lines = match.group().splitlines()
        headers = [visible(c) for c in lines[0].strip().strip("|").split("|")]
        values = [visible(c) for c in lines[2].strip().strip("|").split("|")]
        if len(headers) != len(values) or not {"학교명", "학년", "학기", "과목"} <= set(headers):
            continue
        row = dict(zip(headers, values, strict=True))
        if not re.fullmatch(r"[123]\s*학년", row["학년"]):
            continue
        if not re.fullmatch(r"[12]\s*학기", row["학기"]):
            continue
        if not re.fullmatch(r"[가-힣·ㆍ･\s]{1,20}", row["과목"]):
            continue
        headings.append({
            "start": match.start(), "end": match.end(), "raw": match.group(),
            "key": re.sub(r"\s+", "", row["과목"]).removesuffix("과"),
        })
        grades.extend(
            {**g, "role": "subject_heading", "boundary_start": match.start()}
            for g in extract_grade_evidence(match.group(), "table_cell", "middle", match.start())
        )
    return headings, grades


def structural_events(text: str) -> tuple[list[dict], list[dict]]:
    """Recognize entire heading lines and grade cells, retaining raw positions."""
    headings, grades = [], []
    offset = 0
    previous_lines = []
    for line in text.splitlines(keepends=True):
        clean = visible(line)
        key = subject_heading_key(clean)
        heading_start = offset
        heading_raw = line.rstrip("\r\n")
        # PDF covers can place the subject/grade and the plan title on separate
        # lines, with duplicated text layers. Join only adjacent title-shaped
        # lines, preserving the entire original span and exact offsets.
        if not key and PLAN_RE.match(clean) and previous_lines:
            previous = previous_lines[-1]
            title = previous["clean"]
            if not PLAN_RE.search(title) and re.search(r"과\s*$|[123]\s*학년\s*$", title):
                key = subject_heading_key(title + " " + clean)
                if key:
                    first = len(previous_lines) - 1
                    while first and previous_lines[first - 1]["clean"] == title:
                        first -= 1
                    heading_start = previous_lines[first]["start"]
                    heading_raw = text[heading_start : offset + len(line.rstrip("\r\n"))]
        if key:
            headings.append(
                {
                    "start": heading_start,
                    "end": offset + len(line.rstrip("\r\n")),
                    "raw": heading_raw,
                    "key": key,
                }
            )
            grades.extend(
                {**g, "role": "subject_heading", "boundary_start": heading_start}
                for g in extract_grade_evidence(
                    heading_raw,
                    offset=heading_start,
                    school_level="middle",
                )
            )
        elif CELL_RE.search(line):
            for cell in CELL_RE.finditer(line):
                cell_text = cell[1]
                if re.fullmatch(
                    r"\s*(?:중학교\s*|중\s*)?[123]\s*학년"
                    r"(?:\s*\([12]\s*학기\)|\s+[가-힣]+)?\s*",
                    visible(cell_text),
                ):
                    grades.extend(
                        {
                            **g,
                            "boundary_start": offset,
                            "cell_text": cell_text,
                            "cell_start": offset + cell.start(1),
                        }
                        for g in extract_grade_evidence(
                            cell_text,
                            "table_cell",
                            "middle",
                            offset + cell.start(1),
                        )
                    )
        else:
            # A whole short grade label is structural. Sentences mentioning a
            # different grade are not grade boundaries.
            label = re.sub(r"^(?:[가-힣]|\d+)\s*[.)]\s*", "", clean)
            label = re.sub(r"^(?:대\s*상(?:\s*학년)?|학\s*년)\s*[:：]\s*", "", label)
            grade_label = re.fullmatch(r"(?:중학교\s*|중\s*)?[123]\s*(?:학년)?", label)
            overview = re.fullmatch(r"평가\s*개요\s*\(\s*[123]\s*학년\s*\)", label)
            if grade_label or overview:
                grades.extend(
                    {**g, "role": "grade_heading", "boundary_start": offset}
                    for g in extract_grade_evidence(
                        line,
                        offset=offset,
                        school_level="middle",
                    )
                )
            elif line.lstrip().startswith("|"):
                for cell in re.finditer(r"(?<=\|)[^|]*(?=\|)", line):
                    if re.fullmatch(r"\s*[123]\s*학년\s*", cell.group()):
                        grades.extend(
                            {**g, "boundary_start": offset}
                            for g in extract_grade_evidence(
                                cell.group(),
                                "table_cell",
                                "middle",
                                offset + cell.start(),
                            )
                        )
        if clean:
            previous_lines.append({"clean": clean, "start": offset})
        offset += len(line)
    metadata_heads, metadata_grades = metadata_events(text)
    grades = [g for g in grades if not any(
        h["start"] <= g["start"] < h["end"] for h in metadata_heads
    )]
    return (
        sorted(headings + metadata_heads, key=lambda h: h["start"]),
        sorted(grades + metadata_grades, key=lambda g: g["start"]),
    )


def text_locator(start: int, end: int, conversion: dict) -> dict:
    locator = {
        "start": start,
        "end": end,
        "offset_unit": "unicode_codepoint",
        "end_exclusive": True,
        "converter": conversion.get("converter", "unknown"),
    }
    if conversion.get("converter") == "pymupdf":
        cursor = 0
        overlaps = []
        for page in conversion.get("pages", []):
            page_end = cursor + page["char_count"]
            if start < page_end and end > cursor:
                overlaps.append(page["page"])
            cursor = page_end + 2  # convert_pdf joins pages with two newlines.
        locator["pages"] = overlaps
        locator["page_start"] = overlaps[0] if overlaps else None
        locator["page_end"] = overlaps[-1] if overlaps else None
    return locator


def split_subject_run(start: int, end: int, grades: list[dict]) -> list[dict]:
    """Split on changing structural grade labels, including repeated grade cycles."""
    local_grades = [grade for grade in grades if start <= grade["start"] < end]
    spans = [{"start": start, "end": end, "grade": None, "grade_evidence": []}]
    for grade in local_grades:
        current = spans[-1]
        if current["grade"] is None:
            current["grade"] = grade["grade"]
        elif current["grade"] != grade["grade"]:
            previous = current["grade_evidence"][-1]
            if previous.get("boundary_start") == grade.get("boundary_start") or (
                grade["source"] == "table_cell"
                and grade.get("role") != "subject_heading"
                and previous.get("role") == "subject_heading"
            ):
                current["grade_evidence"].append(grade)
                continue
            boundary = grade.get("boundary_start", grade["start"])
            current["end"] = boundary
            current = {"start": boundary, "end": end, "grade": grade["grade"], "grade_evidence": []}
            spans.append(current)
        current["grade_evidence"].append(grade)
    return spans


def segment_document(source: dict, conversion: dict, child: dict | None = None) -> list[dict]:
    """Create all structural candidates, with quarantine and immutable provenance."""
    text = conversion["text"]
    document_id = document_identifier(source["sha256"])
    container_id = child_identifier(source["sha256"], child) if child else document_id
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    filename = child["member_name"] if child else source["candidate_name"]
    file_grades = extract_grade_evidence(filename, "filename", "middle")
    headings, grade_events = structural_events(text)
    # Standalone grade chapters before the first subject establish grade-major
    # order. Subject-major documents instead reset grade at a new subject.
    grade_major = bool(
        headings
        and grade_events
        and grade_events[0].get("role") == "grade_heading"
        and grade_events[0]["start"] < headings[0]["start"]
    )
    chapter_starts = [0]
    if grade_major:
        chapter_starts.extend(
            g["boundary_start"] for g in grade_events if g.get("role") == "grade_heading"
        )
    chapter_starts = sorted(set(chapter_starts + [len(text)]))
    segments = []
    for chapter_start, chapter_end in zip(chapter_starts, chapter_starts[1:], strict=False):
        chapter_heads = [h for h in headings if chapter_start <= h["start"] < chapter_end]
        chapter_grade = (
            [
                g
                for g in grade_events
                if g.get("boundary_start") == chapter_start and g.get("role") == "grade_heading"
            ]
            if grade_major
            else []
        )
        runs = []
        for heading in chapter_heads:
            if runs and runs[-1]["key"] == heading["key"]:
                runs[-1]["headings"].append(heading)
            else:
                runs.append(
                    {"start": heading["start"], "key": heading["key"], "headings": [heading]}
                )
        if not runs or runs[0]["start"] > chapter_start:
            runs.insert(0, {"start": chapter_start, "key": None, "headings": []})
        for index, run in enumerate(runs):
            run_end = runs[index + 1]["start"] if index + 1 < len(runs) else chapter_end
            spans = split_subject_run(run["start"], run_end, grade_events)
            for span in spans:
                start, end = span["start"], span["end"]
                if not text[start:end].strip():
                    continue
                body_evidence = span["grade_evidence"] or chapter_grade
                evidence = body_evidence + file_grades if body_evidence else file_grades
                values = {g["grade"] for g in evidence}
                grade = next(iter(values)) if len(values) == 1 else None
                conflicts = len(values) > 1
                local_heads = [h for h in run["headings"] if start <= h["start"] < end]
                # A shared subject heading can precede a grade's own table.
                primary = local_heads[0] if local_heads else (run["headings"] or [None])[0]
                term_evidence = []
                for h in local_heads or ([primary] if primary else []):
                    term_evidence.extend(
                        {
                            "semester": int(m[1]),
                            "source": "body_heading",
                            "text": m.group(),
                            "start": h["start"] + m.start(),
                            "end": h["start"] + m.end(),
                        }
                        for m in SEMESTER_RE.finditer(h["raw"])
                    )
                for e in body_evidence:
                    term_evidence.extend(
                        {
                            "semester": int(m[1]),
                            "source": "table_cell",
                            "text": m.group(),
                            "start": e["cell_start"] + m.start(),
                            "end": e["cell_start"] + m.end(),
                        }
                        for m in SEMESTER_RE.finditer(e.get("cell_text", ""))
                    )
                line_offset = start
                for line in text[start:end].splitlines(keepends=True):
                    if SEMESTER_RE.fullmatch(line.strip()):
                        term_evidence.extend(
                            {
                                "semester": int(m[1]),
                                "source": "body_heading",
                                "text": m.group(),
                                "start": line_offset + m.start(),
                                "end": line_offset + m.end(),
                            }
                            for m in SEMESTER_RE.finditer(line)
                        )
                    line_offset += len(line)
                # Table rows may carry the semester, and stay within the span.
                for match in re.finditer(
                    r"<(?:td|th)\b[^>]*>\s*([12]\s*학기)\s*</", text[start:end]
                ):
                    term_evidence.append(
                        {
                            "semester": int(match[1][0]),
                            "source": "table_cell",
                            "text": match[1],
                            "start": start + match.start(1),
                            "end": start + match.end(1),
                        }
                    )
                term_evidence.extend(
                    {
                        "semester": int(m[1]),
                        "source": "filename",
                        "text": m.group(),
                        "start": m.start(),
                        "end": m.end(),
                    }
                    for m in SEMESTER_RE.finditer(filename)
                )
                terms = {e["semester"] for e in term_evidence}
                semester = next(iter(terms)) if len(terms) == 1 else None
                free = [
                    {"text": m.group(), "start": start + m.start(), "end": start + m.end()}
                    for m in FREE_RE.finditer(text[start:end])
                ]
                status = (
                    "normal"
                    if grade in {1, 2}
                    else ("grade3_quarantined" if grade == 3 else "grade_unresolved")
                )
                statuses = [status]
                if not primary:
                    statuses.append("subject_heading_unresolved")
                if semester is None:
                    statuses.append("semester_unresolved")
                if free:
                    statuses.append("free_semester_marker")
                if conversion.get("conversion_status") not in {"ok", "short"}:
                    statuses.append("conversion_review")
                review_reason = "S5 이후 과목·교육과정 검토 필요"
                if conflicts:
                    review_reason = "학년 근거 충돌"
                elif grade is None:
                    review_reason = "학년 머리글·표 셀의 단일 학년 연결 미확정"
                    if not primary:
                        review_reason = "표지·목차 등 과목 머리글 미식별 구간"
                    elif re.search(r"전\s*학년", text[start:end]):
                        review_reason = "전학년 표기. 단일 학년 구간 분리 근거 미확정"
                segment_id = digest_id(
                    "seg_",
                    RULE_VERSION,
                    container_id,
                    text_sha,
                    conversion.get("converter"),
                    grade,
                    semester,
                    start,
                    end,
                    primary["raw"] if primary else None,
                )
                segments.append(
                    {
                        "segment_id": segment_id,
                        "document_id": document_id,
                        "child_id": container_id if child else None,
                        "grade": grade,
                        "grade_evidence": evidence,
                        "grade_conflict": conflicts,
                        "semester": semester,
                        "semester_evidence": term_evidence,
                        "semester_status": "confirmed"
                        if semester
                        else ("mixed_or_conflicting" if terms else "unconfirmed"),
                        "subject_heading_raw": primary["raw"] if primary else None,
                        "subject_heading_text": visible(primary["raw"]) if primary else None,
                        "subject_heading_key": run["key"],
                        "subject_heading_locator": {
                            "start": primary["start"],
                            "end": primary["end"],
                        }
                        if primary
                        else None,
                        "heading_candidates": local_heads,
                        "locator": {
                            **text_locator(start, end, conversion),
                            "text_field": f"children[{child['member_index']}].text"
                            if child
                            else "text",
                        },
                        "text_sha256": text_sha,
                        "boundary_status": "candidate",
                        "end_basis": "next_structural_heading_or_grade"
                        if end < len(text)
                        else "document_end",
                        "statuses": statuses,
                        "free_semester_markers": free,
                        "public_eligible": False,
                        "review_reason": review_reason,
                    }
                )
    return segments


def normalized_lines(text: str) -> list[dict]:
    lines = []
    offset = 0
    for raw in text.splitlines(keepends=True):
        # Keep table tags/attributes because merged-cell changes can alter scope.
        value = re.sub(r"\s+", "", html.unescape(raw))
        if value and not re.fullmatch(r"-\d+-", value):
            lines.append({"value": value, "start": offset, "end": offset + len(raw)})
        offset += len(raw)
    return lines


def compare_versions(left: str, right: str) -> dict:
    a, b = normalized_lines(left), normalized_lines(right)
    av, bv = [line["value"] for line in a], [line["value"] for line in b]
    equivalent = bool(av and bv) and "".join(av) == "".join(bv)
    matcher = SequenceMatcher(None, av, bv, autojunk=False)
    differences = []
    for kind, i, j, k, m in matcher.get_opcodes():
        if kind == "equal":
            continue

        def location(lines, start, end, text_length):
            return {
                "start": lines[start]["start"] if start < len(lines) else text_length,
                "end": lines[end - 1]["end"]
                if end > start
                else (lines[start]["start"] if start < len(lines) else text_length),
            }

        differences.append(
            {
                "kind": kind,
                "left": location(a, i, j, len(left)),
                "right": location(b, k, m, len(right)),
                "left_excerpt": " ".join(av[i:j])[:240],
                "right_excerpt": " ".join(bv[k:m])[:240],
            }
        )
    return {
        "equivalent": equivalent,
        "line_similarity": matcher.ratio(),
        "normalization": "Whitespace/page-number lines removed. Table tags/attributes retained",
        "differences": differences,
    }


def resolve_versions(documents: list[dict]) -> list[dict]:
    """Conservative same-scope edition resolution, no filename priority rule.

    Input documents include text transiently. Output comparisons carry locators,
    never whole originals. Incompletely identified scopes cannot supersede peers.
    """
    groups = defaultdict(list)
    for document in documents:
        source = document["source"]
        known = {s["grade"] for s in document["segments"] if s["grade"] is not None}
        semesters = {s["semester"] for s in document["segments"] if s["semester"] is not None}
        document["version_status"] = "single"
        document["edition_markers"] = re.findall(r"최종|수정|정정", source["candidate_name"])
        if not known or len(semesters) != 1:
            continue
        key = (
            source["school_code"],
            source.get("year"),
            next(iter(semesters)),
            tuple(sorted(known)),
            document.get("document_kind", "assessment_plan"),
        )
        groups[key].append(document)
    comparisons = []
    for key, group in groups.items():
        if len(group) < 2:
            continue
        # Compare every pair so a near-duplicate cannot bridge two conflicting editions.
        pair_results = []
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                comparison = compare_versions(left["text"], right["text"])
                pair_results.append(comparison)
                comparisons.append(
                    {
                        "scope": key,
                        "left_document_id": left["document_id"],
                        "right_document_id": right["document_id"],
                        **comparison,
                        "disclosure_evidence": [
                            {
                                k: d["source"].get(k)
                                for k in (
                                    "candidate_name",
                                    "disclosure_round",
                                    "file_seq",
                                    "published_at",
                                    "collected_at",
                                )
                            }
                            for d in (left, right)
                        ],
                    }
                )
        sequences = [str(d["source"].get("file_seq", "")) for d in group]
        ordered = (
            all(s.isdigit() for s in sequences)
            and len(set(sequences)) == len(group)
            and len({d["source"].get("disclosure_round") for d in group}) == 1
        )
        equivalent = all(c["equivalent"] for c in pair_results)
        representative = max(group, key=lambda d: int(d["source"]["file_seq"])) if ordered else None
        for document in group:
            status = "version_conflict"
            if equivalent and representative:
                status = "representative" if document is representative else "superseded"
            document["version_status"] = status
            document["version_reason"] = (
                "정규화 본문 동일. 같은 공시 회차의 큰 파일 순번을 대표로 선택"
                if equivalent and ordered
                else "본문 실질 차이"
                if not equivalent
                else "공시 순서 불명"
            )
            document["representative_document_id"] = (
                representative["document_id"] if (equivalent and representative) else None
            )
            document["order_caveat"] = (
                "file_seq는 목록 순서 근거. collected_at은 수집 시각이며 게시 시각 아님"
            )
            if status in {"superseded", "version_conflict"}:
                for segment in document["segments"]:
                    segment["statuses"].append(status)
    return comparisons
