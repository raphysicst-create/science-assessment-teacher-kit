"""Offline S9 adjudication. Preserve input alternatives and never synthesize label values.

The draft is an adjudication envelope, not the sealed label schema: each field has
status/value/accepted/source, plus original A/B alternatives. Merged item slots are
kept as redirects for audit; gold_v1 omits these redirects. Neither means both
alternatives were rejected (ambiguous, no replacement value), not source_absent.
"""

from __future__ import annotations

import argparse
import copy
import csv
import html
import io
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

from gold_diff import (
    CONTENT_FIELDS,
    atomic_text,
    compare_labels,
    field_equal,
    item_title,
    json_text,
    locations,
    match_items,
    normalize,
    short,
    value_status,
)
from gold_validate import DEFAULT_PACK, line_range, pack_lines, read_labels, walk

ABSENT = {"status": "source_absent", "values": []}
RULE_COLUMNS = (
    "불일치ID",
    "학교",
    "학년",
    "학기",
    "필드",
    "적용규칙",
    "결과",
    "정답값요약",
    "근거위치",
    "근거발췌",
    "판정방식",
    "메모",
    "질문번호",
)
FIELD_NAMES = {
    "title": "대표 제목",
    "title_role": "제목의 역할",
    "task_text": "과제 설명",
    "task_no": "과제 번호",
    "period": "평가 시기",
    "method": "평가 방법",
    "standards": "성취기준",
    "max_score": "만점",
    "sub_scores": "채점 요소",
    "ratio": "반영 비율",
    "rubric": "채점기준",
    "free_semester": "자유학기 여부",
    "science_sections": "과학 부분의 범위",
    "edition": "문서 판본",
    "항목 존재": "항목을 나누는 방식",
    "문서 존재": "문서 포함 여부",
}
STATE_NAMES = {
    "source_absent": "원문에 없음",
    "ambiguous": "확실하지 않음",
    "conflict": "원문끼리 충돌",
    "missing": "항목 없음",
    "present": "",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def unique(values):
    return list({json_text(value): value for value in values}.values())


def merge(a, b):
    """Union existing objects only; scalar alternatives stay in accepted/A/B."""
    if a is None:
        return copy.deepcopy(b)
    if b is None or a == b:
        return copy.deepcopy(a)
    if isinstance(a, list) and isinstance(b, list):
        return unique(a + b)
    if isinstance(a, dict) and isinstance(b, dict):
        result = copy.deepcopy(a)
        for key, val in b.items():
            if key not in result:
                result[key] = copy.deepcopy(val)
            elif isinstance(val, list) and isinstance(result[key], list):
                result[key] = unique(result[key] + val)
        return result
    return copy.deepcopy(a)


def atoms(value) -> set:
    """Rule 0: existing raw spellings or explicit numeric normalizations overlap.

    Do not count shared option metadata, source locations, or note text as values.
    A score's name remains intact in the union even if just its number overlaps.
    """
    if not isinstance(value, dict):
        return set()
    result = set()
    for val in value.get("values", []):
        if val.get("raw"):
            result.add(("raw", normalize(val["raw"])))
        if "norm" in val:
            result.add(("norm", val["norm"]))
    return result


def rule0(a, b) -> bool:
    return value_status(a) == value_status(b) == "present" and bool(atoms(a) & atoms(b))


def title_core(text: str) -> str:
    text = clean(text)
    text = re.sub(r"^[#\s▪·]+", "", text)
    text = re.sub(r"^[가-하]\s*[.]\s*", "", text)
    text = re.sub(r"^\d+\s*[.]\s*", "", text)
    text = re.sub(r"\(?☞?수행평가\s*연계\)?", "", text)
    text = re.sub(r"^\(?수행평가\s*\d*\)?[_\s]*", "", text)
    text = re.sub(r"\(\s*총?\s*\d+\s*점\s*\)", "", text)
    return normalize(text)


def title_role(text: str) -> str | None:
    """Conservative content classifier; returns existing schema role vocabulary."""
    original = normalize(clean(text))
    if re.fullmatch(r"(?:\d+)?수행평가\d+|\d+|수행평가", original):
        return "번호" if original != "수행평가" else "기타"
    core = title_core(text)
    genres = {
        "실험",
        "탐구",
        "서논술형",
        "서술형",
        "논술형",
        "구술형",
        "서술논술",
        "구술발표",
        "실험실습",
        "프로젝트",
        "포트폴리오",
        "실험활동",
        "자유탐구",
        "탐구활동평가",
        "수업밀착형평가",
    }
    if core in genres or core.endswith("수행평가"):
        return "평가영역"
    if re.search(
        r"하기|쓰기|만들기|그리기|작성|보고서|제작|발표|설명|실험|탐구|측정|관찰|구술평가"
        r"|프로젝트|인포그래픽|해석|조사",
        core,
    ):
        return "과제명"
    if core and len(core) <= 35:
        return "평가영역"
    return None


def spelling_equivalent(a: str, b: str) -> bool:
    a, b = title_core(a), title_core(b)
    if a == b:
        return True
    # Nearby words can still describe different assessment modes.
    modes = ("구술", "글쓰기", "논술", "실험", "발표", "기체", "고체", "액체", "전기", "자기")
    if {x for x in modes if x in a} != {x for x in modes if x in b}:
        return False
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    changes = [(a[i:j], b[k:end]) for tag, i, j, k, end in matcher.get_opcodes() if tag != "equal"]
    particles = {"의", "와", "과", "을", "를", "이", "가", "로", "으로", ""}
    return (
        len(changes) == 1
        and len(a) >= 5
        and len(b) >= 5
        and (max(map(len, changes[0])) == 1 or all(x in particles for x in changes[0]))
        and matcher.ratio() >= 0.8
    )


@dataclass
class Evidence:
    doc_id: str
    line: int
    excerpt: str

    @property
    def position(self):
        return f"{self.doc_id}:L{self.line}"


class Pack:
    def __init__(self, path: Path):
        self.path = path
        self._lines = {}

    def lines(self, doc_id):
        if Path(doc_id).name != doc_id or "/" in doc_id or "\\" in doc_id:
            raise ValueError("잘못된 문서 ID")
        if doc_id not in self._lines:
            self._lines[doc_id] = pack_lines(self.path / f"{doc_id}.md")
        return self._lines[doc_id]

    def evidence(self, loc, number=None, needle=None):
        lines = self.lines(loc["doc_id"])
        n = number or line_range(loc)[0]
        if not 1 <= n <= len(lines):
            raise ValueError(f"원문 범위 밖: {loc}")
        text = clean(lines[n - 1])
        focus = text.find(clean(needle)) if needle else -1
        if focus > 24:
            text = "…" + text[max(0, focus - 12) :]
        return Evidence(loc["doc_id"], n, short(text, 80))

    def value_evidence(self, value):
        return unique_evidence(
            [
                self.evidence(obj["loc"], needle=obj.get("raw", obj.get("text")))
                for _, obj in walk(value)
                if isinstance(obj.get("loc"), dict)
            ]
        )

    def context(self, loc):
        """Containing HTML table plus preceding heading, or local plain-text block.

        A preceding, already closed table is never treated as containing the line.
        Plain PDF text requires explicit nearby headers; unknown stays unknown.
        """
        lines = self.lines(loc["doc_id"])
        start, end = line_range(loc)
        if not 1 <= start <= end <= len(lines):
            raise ValueError(f"원문 범위 밖: {loc}")
        opening = next((i for i in range(start - 1, -1, -1) if "<table" in lines[i]), None)
        closing = next((i for i in range(start - 2, -1, -1) if "</table>" in lines[i]), -1)
        if opening is not None and opening > closing:
            stop = next((i for i in range(end - 1, len(lines)) if "</table>" in lines[i]), end - 1)
            first = opening
            # Include the closest preceding nonempty heading, not a different table.
            for i in range(opening - 1, max(-1, opening - 15), -1):
                if lines[i].strip():
                    if "</table>" not in lines[i]:
                        first = i
                    break
            return [(i + 1, lines[i]) for i in range(first, stop + 1)]
        first = max(0, start - 14)
        stop = min(len(lines), end + 5)
        stop = next((i for i in range(end, stop) if lines[i].lstrip().startswith("#")), stop)
        return [(i + 1, lines[i]) for i in range(first, stop)]

    def classify(self, loc):
        context = self.context(loc)
        text = normalize(clean(" ".join(s for _, s in context)))
        # These are table/header facts, never a labeler's explanatory note.
        schedule = (
            "수업평가연계" in text
            or "수업평가연계의주안점" in text
            or ("시수" in text and ("누계" in text or "단원명" in text))
            or "진도표" in text
            or "주차별수업계획" in text
        )
        generic = (
            "성취기준별성취수준" in text
            or "학기단위성취수준" in text
            or (
                "성취수준" in text
                and "교육과정성취기준" in text
                and bool(re.search(r">\s*[ABCDE]\s*<", " ".join(s for _, s in context)))
            )
        )
        scoring = ("채점기준" in text or "채점요소" in text or "평가준거" in text) and (
            "배점" in text or "점수" in text or "평가기준" in text
        )
        # A task-specific table can contain both standards and A~E levels. Its
        # explicit scoring columns distinguish it from a semester-wide table.
        if scoring and "성취기준별성취수준" not in text and "학기단위성취수준" not in text:
            generic = False
        task_specific = "평가영역명" in text or "수행과제" in text
        if task_specific and (scoring or "수행수준" in text):
            generic, scoring = False, True
        plan = "수행평가" in text and (
            "평가시기" in text or "평가방법" in text or "반영비율" in text
        )
        kind = (
            "schedule"
            if schedule
            else "generic"
            if generic
            else "rubric"
            if scoring
            else "plan"
            if plan
            else "unknown"
        )
        terms = {
            "schedule": ("연계", "시수", "진도표", "주차별"),
            "generic": ("성취수준",),
            "rubric": ("채점기준", "채점요소", "평가준거", "배점"),
            "plan": ("평가시기", "평가방법", "반영비율"),
            "unknown": (),
        }[kind]
        header = next(
            (n for n, s in context if any(t in normalize(clean(s)) for t in terms)),
            line_range(loc)[0],
        )
        return kind, [self.evidence(loc, header), self.evidence(loc)]

    def supports(self, val):
        if not val.get("loc") or not val.get("raw"):
            return False
        lines = self.lines(val["loc"]["doc_id"])
        start, end = line_range(val["loc"])
        if not 1 <= start <= end <= len(lines):
            return False
        source = title_core(" ".join(lines[start - 1 : end]))
        raw = title_core(val["raw"])
        if not raw:
            raw, source = (
                normalize(clean(val["raw"])),
                normalize(clean(" ".join(lines[start - 1 : end]))),
            )
        return bool(raw and raw in source)


@dataclass
class Decision:
    result: str = "사용자판정"
    value: object = None
    rules: list[int] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    mode: str = "기계"
    memo: str = "규칙만으로 선택할 근거가 부족함"
    status: str | None = None
    accepted: list = field(default_factory=list)
    references: list = field(default_factory=list)
    question: str = ""
    candidates: dict | None = None


def select(a, b, result, rules, evidence, memo, mode="판단", status=None):
    values = (
        [a]
        if result == "A"
        else [b]
        if result == "B"
        else []
        if result == "없음(source_absent)"
        else [a, b]
    )
    values = [v for v in values if v is not None]
    value = (
        copy.deepcopy(ABSENT)
        if result == "없음(source_absent)"
        else merge(values[0], values[1])
        if len(values) == 2
        else copy.deepcopy(values[0])
        if values
        else None
    )
    state = status or ("conflict" if result == "충돌보존" else value_status(value))
    if isinstance(value, dict) and "status" in value:
        value["status"] = state
    return Decision(
        result,
        value,
        sorted(set(rules)),
        unique_evidence(evidence),
        mode,
        memo,
        state,
        unique(values),
    )


def unique_evidence(evidence):
    return list({(e.doc_id, e.line): e for e in evidence}.values())


def rule1(a, b, left, right, pack):
    candidates = [
        (side, v)
        for side, item in (("A", left), ("B", right))
        if item
        for v in item.get("title", {}).get("values", [])
    ]
    supported = [(side, v, title_role(v["raw"])) for side, v in candidates if pack.supports(v)]
    rank = {"과제명": 3, "평가영역": 2, "번호": 1, "기타": 0, None: -1}
    if not supported:
        return None
    best = max(supported, key=lambda x: rank[x[2]])
    if rank[best[2]] < 0 or best[2] not in (a, b):
        return None
    result = "둘다" if a == b else "A" if a == best[2] else "B"
    return select(
        a,
        b,
        result,
        [1],
        [pack.evidence(best[1]["loc"], needle=best[1]["raw"])],
        "제목 글의 내용으로 역할 선택; 다른 제목은 별명에 보존",
    )


def rule_titles(a, b, pack):
    vals = unique(a.get("values", []) + b.get("values", []))
    if not vals or not all(pack.supports(v) for v in vals):
        return None
    rank = {"과제명": 3, "평가영역": 2, "번호": 1, "기타": 0, None: -1}
    roles_a = [rank[title_role(v["raw"])] for v in a.get("values", [])]
    roles_b = [rank[title_role(v["raw"])] for v in b.get("values", [])]
    evidence = [pack.evidence(v["loc"], needle=v["raw"]) for v in vals]
    if roles_a and roles_b and max(roles_a) != max(roles_b):
        result = "A" if max(roles_a) > max(roles_b) else "B"
        top = [v for v in vals if rank[title_role(v["raw"])] == max(roles_a + roles_b)]
        rules = [1, 4] if len({title_core(v["raw"]) for v in top}) > 1 else [1]
        if any(not spelling_equivalent(x["raw"], y["raw"]) for x in top for y in top):
            return select(
                a,
                b,
                "충돌보존",
                rules,
                evidence,
                "대표 제목은 구체적인 글; 구체 제목끼리 뜻이 달라 충돌 보존",
            )
        return select(
            a,
            b,
            result,
            rules,
            evidence,
            "구체적인 제목을 대표로 선택; 다른 쪽 원문 제목은 별명에 보존",
        )
    same = all(spelling_equivalent(x["raw"], y["raw"]) for x in vals for y in vals)
    return select(
        a,
        b,
        "둘다" if same else "충돌보존",
        [4],
        evidence,
        "표기 차이를 모두 인정" if same else "뜻이 다른 원문 제목을 충돌로 보존",
        status="present" if same else "conflict",
        mode="기계" if len({title_core(v["raw"]) for v in vals}) == 1 else "판단",
    )


def filter_source(field_name, value, pack):
    """Return transformed value, rule, evidence, excluded original values, changed."""
    if not isinstance(value, dict) or value_status(value) == "source_absent":
        return value, [], [], [], False
    rule = {"rubric": 2, "method": 3, "period": 5}[field_name]
    excluded, kept, evidence = [], [], []
    if field_name == "rubric":
        kinds = []
        for val in value.get("values", []):
            if not val.get("loc"):
                kept.append(val)
                kinds.append("unknown")
                continue
            kind, es = pack.classify(val["loc"])
            evidence.extend(es)
            if kind == "generic":
                excluded.append(val)
            else:
                kept.append(val)
                kinds.append(kind)
        if excluded:
            result = copy.deepcopy(value) if kept else copy.deepcopy(ABSENT)
            if kept:
                result["values"] = kept
                if all(kind == "rubric" for kind in kinds):
                    result["status"] = "present"
            return result, [rule], evidence, excluded, True
        return value, [], [], [], False
    # A method may have options not covered by its raw values. All locations must
    # belong to a schedule before excluding the entire method field.
    if field_name == "method":
        locs = locations(value)
        kinds = [pack.classify(loc) for loc in locs]
        if locs and all(kind == "schedule" for kind, _ in kinds):
            return copy.deepcopy(ABSENT), [rule], [e for _, es in kinds for e in es], [value], True
        result = copy.deepcopy(value)
        kept_texts, excluded_texts = set(), set()
        for key in ("values", "options"):
            retained = []
            for val in value.get(key, []):
                kind, es = pack.classify(val["loc"]) if val.get("loc") else ("unknown", [])
                text = normalize(clean(val.get("raw", val.get("text", ""))))
                if kind == "schedule":
                    excluded.append(val)
                    excluded_texts.add(text)
                    evidence.extend(es)
                else:
                    retained.append(val)
                    kept_texts.add(text)
            if key in result:
                result[key] = retained
        if excluded:
            for key in ("plain_text", "other_text"):
                text = normalize(clean(value.get(key, "")))
                if text and text in excluded_texts and text not in kept_texts:
                    result.pop(key, None)
                elif text and text not in kept_texts:
                    # A combined scalar cannot be rewritten into a new string.
                    # Leave it visible for the user and keep the field uncertain.
                    result["status"] = "ambiguous"
            return result, [rule], evidence, excluded, True
        return value, [], [], [], False
    for val in value.get("values", []):
        if "loc" not in val:
            kept.append(val)
            continue
        kind, es = pack.classify(val["loc"])
        if kind == "schedule":
            excluded.append(val)
            evidence.extend(es)
        else:
            kept.append(val)
            if kind == "plan":
                evidence.extend(es)
    if not excluded:
        return value, [], [], [], False
    result = copy.deepcopy(value) if kept else copy.deepcopy(ABSENT)
    if kept:
        result["values"] = kept
        # Removing a schedule-only alternative can eliminate an old conflict.
        if len({normalize(v["raw"]) for v in kept}) == 1:
            result["status"] = "present"
    return result, [rule], evidence, excluded, True


def source_decision(field_name, a, b, pack):
    left, lr, le, lx, lc = filter_source(field_name, a, pack)
    right, rr, re_, rx, rc = filter_source(field_name, b, pack)
    if not (lc or rc):
        allowed_kind = {"rubric": "rubric", "method": "plan", "period": "plan"}[field_name]
        locs = locations([a, b])
        inspected = [pack.classify(loc) for loc in locs]
        if (
            inspected
            and all(kind == allowed_kind for kind, _ in inspected)
            and not rule0(a, b)
            and not field_equal(field_name, a, b)
        ):
            return Decision(
                rules=[{"rubric": 2, "method": 3, "period": 5}[field_name]],
                evidence=unique_evidence([e for _, es in inspected for e in es]),
                mode="판단",
                memo="표의 종류는 확인했으나 값·상태 차이가 남음; 확신 낮음",
            )
        return None
    rules, evidence = sorted(set(lr + rr)), le + re_
    if field_equal(field_name, left, right) or rule0(left, right):
        absent = value_status(left) == value_status(right) == "source_absent"
        decision = select(
            left,
            right,
            "없음(source_absent)" if absent else "둘다",
            rules,
            evidence,
            "성취수준 표/수업 연계표의 값을 정답에서 제외",
        )
    elif (
        field_name == "period"
        and all(
            value_status(v) == "source_absent"
            or all(pack.classify(x["loc"])[0] == "plan" for x in v.get("values", []) if "loc" in x)
            for v in (left, right)
        )
        and "source_absent" in (value_status(left), value_status(right))
    ):
        decision = select(
            left,
            right,
            "B" if value_status(left) == "source_absent" else "A",
            rules,
            evidence,
            "평가계획의 시기만 선택; 진도표 시기는 참고로 보존",
        )
    else:
        decision = Decision(
            rules=rules,
            evidence=evidence,
            mode="판단",
            memo="일부 값을 제외했으나 A·B가 여전히 다름; 확신 낮음",
        )
        decision.candidates = {"A": left, "B": right}
    decision.references = lx + rx
    return decision


def criterion_letters(value):
    return set(re.findall(r"평가기준([a-d])", normalize(json_text(value))))


def ib_groups(a, b, pack):
    """Map split criteria to already written merged tasks by criterion letters.

    No ordinal/item key assumptions and no total score or ratio arithmetic.
    Every split criterion must have one owner; the owner's summary table must
    actually contain its criteria. Shared occurrence spans alone are insufficient.
    """
    result, evidence = {}, {}
    for merged_side, merged_items, split_items in (("A", a, b), ("B", b, a)):
        for item in merged_items:
            if item["school_id"] != "ms-gold-jeonbuk-gun":
                continue
            letters = criterion_letters(item.get("sub_scores", {}))
            if len(letters) < 2:
                continue
            matches = [
                x
                for x in split_items
                if all(x[k] == item[k] for k in ("school_id", "grade", "semester"))
                and len(criterion_letters(x["title"])) == 1
                and criterion_letters(x["title"]) <= letters
            ]
            if set().union(*(criterion_letters(x["title"]) for x in matches)) != letters:
                continue
            # Require one split item per criterion and an explicit source table.
            if len(matches) != len(letters):
                continue
            es = []
            for loc in locations(item.get("sub_scores", {})):
                context = pack.context(loc)
                text = normalize(clean(" ".join(s for _, s in context)))
                if letters <= set(re.findall(r"평가기준([a-d])", text)) and "영역만점" in text:
                    header = next(n for n, s in context if "평가기준" in s)
                    es += [pack.evidence(loc, header), pack.evidence(loc)]
            if not es:
                continue
            key = (merged_side, item["item_key"])
            result[key] = item
            evidence[key] = unique_evidence(es)
            split_side = "B" if merged_side == "A" else "A"
            for x in matches:
                skey = (split_side, x["item_key"])
                if skey in result and result[skey]["item_key"] != item["item_key"]:
                    raise ValueError("IB 기준의 과제 연결이 중복됨")
                result[skey] = item
                evidence[skey] = evidence[key]
    return result, evidence


def adjudicate(row, left, right, pack, ib=None, ib_evidence=None):
    f, a, b = row["필드"], json.loads(row["A값"]), json.loads(row["B값"])
    base = (
        select(
            a,
            b,
            "둘다",
            [0],
            [],
            "present 값이 하나 이상 겹침; 두 표기 인정",
            mode="기계",
            status="present",
        )
        if rule0(a, b)
        else None
    )
    if base:
        base.evidence = [pack.evidence(loc) for loc in locations([a, b])]
    if ib:
        keys = [(side, item["item_key"]) for side, item in (("A", left), ("B", right)) if item]
        owners = {ib[key]["item_key"] for key in keys if key in ib}
        if len(owners) == 1 and all(key in ib for key in keys):
            key = next(k for k in keys if k in ib)
            owner = ib[key]
            side = (
                "A"
                if ("A", owner["item_key"]) in ib and ib[("A", owner["item_key"])] is owner
                else "B"
            )
            chosen = (
                owner["title"].get("role")
                if f == "title_role"
                else owner
                if f == "항목 존재"
                else owner[f]
            )
            decision = select(
                chosen if side == "A" else None,
                chosen if side == "B" else None,
                side,
                [6],
                ib_evidence[key],
                "과제 단위 구조 선택; 기준 칸은 기존 sub_scores로 보존. 합계 생성 안 함",
            )
            if f == "period":
                val, rules, es, excluded, changed = filter_source(f, chosen, pack)
                if changed:
                    decision = select(
                        val if side == "A" else None,
                        val if side == "B" else None,
                        side,
                        [5, 6],
                        es + ib_evidence[key],
                        "과제 단위 구조; 평가계획 시기만 정답",
                    )
                    decision.references = excluded
            if base:
                decision.rules = sorted(set([0] + decision.rules))
            return decision
    special = None
    if f == "title_role":
        special = rule1(a, b, left, right, pack)
    elif f == "title":
        special = rule_titles(a, b, pack)
    elif f in {"period", "method", "rubric"}:
        special = source_decision(f, a, b, pack)
    if special:
        if base:
            special.rules = sorted(set([0] + special.rules))
        return special
    if base:
        return base
    locs = locations([a, b]) or (left or right or {}).get("occurrences", [])
    return Decision(evidence=pack.value_evidence([a, b]) or [pack.evidence(loc) for loc in locs])


def human_value(f, value, limit=500):
    if value is None:
        return "항목 없음"
    status = value_status(value)
    if status == "source_absent":
        return "원문에 없음"
    if f in {"항목 존재", "문서 존재"}:
        return item_title(value) if f == "항목 존재" else value["doc_id"]
    if f == "science_sections":
        return short(
            " / ".join(
                f"{x['grade']}학년 {x['semester']}학기 {x['line_start']}~{x['line_end']}줄"
                for x in value
            ),
            limit,
        )
    if f == "standards":
        text = " / ".join(
            dict.fromkeys(
                (
                    STATE_NAMES.get(group["status"], "") + ": "
                    if group["status"] != "present"
                    else ""
                )
                + ", ".join(group.get("codes", []))
                for group in value
            )
        )
    elif isinstance(value, dict):
        if f == "method":
            names = {
                "checked": "선택",
                "unchecked": "미선택",
                "no_box": "체크칸 없음",
                "unreadable": "체크 판독 불가",
            }
            parts = [
                f"{clean(o['text'])}({names.get(o['state'], o['state'])})"
                for o in value.get("options", [])
            ]
            parts += [clean(value.get("plain_text", "")), clean(value.get("other_text", ""))]
            represented = {normalize(o["text"]) for o in value.get("options", [])}
            represented.update(normalize(clean(p)) for p in parts if p)
            parts += [
                clean(v["raw"])
                for v in value.get("values", [])
                if normalize(clean(v["raw"])) not in represented
            ]
        elif f == "rubric":
            parts = [
                f"{loc['doc_id']}:{line_range(loc)[0]}~{line_range(loc)[1]}줄"
                for loc in locations(value)
            ]
        else:
            parts = [
                (f"{clean(v['name'])}: " if v.get("name") else "") + clean(v["raw"])
                for v in value.get("values", [])
            ]
        text = " / ".join(dict.fromkeys(p for p in parts if p))
    elif isinstance(value, bool):
        text = "자유학기" if value else "일반학기"
    else:
        text = str(value)
    prefix = STATE_NAMES.get(status, "")
    return short(f"{prefix}: {text}" if prefix and text else text or prefix or "값 없음", limit)


def envelope(a, b, decision=None):
    if decision is None:
        decision = select(a, b, "둘다", [], [], "내용 합의", mode="기계")
    pending = decision.result == "사용자판정"
    result = {
        "status": "pending" if pending else decision.status,
        "value": None if pending else decision.value,
        "accepted": [] if pending else decision.accepted,
        "source": f"대기:{decision.question}"
        if pending
        else "|".join(f"규칙{n}" for n in decision.rules) or "합의",
        "rules": decision.rules,
        "A": a,
        "B": b,
        "references": decision.references,
        "evidence": [vars(e) for e in unique_evidence(decision.evidence)],
    }
    if decision.candidates:
        result.update(
            A=decision.candidates["A"], B=decision.candidates["B"], original_A=a, original_B=b
        )
    return result


def csv_write(path, rows, columns):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, buffer.getvalue(), "utf-8-sig")


def representative(values):
    rank = {"과제명": 3, "평가영역": 2, "번호": 1, "기타": 0, None: -1}
    return max(values, key=lambda v: rank[title_role(v["raw"])]) if values else None


def refresh_titles(record):
    if record["type"] != "item" or "title" not in record["fields"]:
        return
    title, role = record["fields"]["title"], record["fields"]["title_role"]
    if isinstance(title["value"], dict):
        if role["value"] is not None:
            title["value"]["role"] = role["value"]
        else:
            title["value"].pop("role", None)
        title["role_source"] = role["source"]
    vals = [
        v
        for f in ("title", "task_text")
        for v in (record["fields"][f]["value"] or {}).get("values", [])
    ]
    if vals:
        record["representative_title"] = representative(vals)
        record["representative_title_source"] = "규칙1"
    else:
        record.pop("representative_title", None)


def question_cause(f, a, b, pack):
    """Only pool decisions whose A/B directions and source problem are the same."""
    if value_status(a) == "source_absent" and value_status(b) == "ambiguous" and f == "rubric":
        contexts = [normalize(clean(" ".join(s for _, s in pack.context(x)))) for x in locations(b)]
        if contexts and all(
            "평가요소" in x
            and "배점" in x
            and not any(word in x for word in ("채점기준", "평가준거", "성취수준"))
            for x in contexts
        ):
            return (
                "요소와 배점만 있는 표",
                "원문에 없음",
                "그 과제의 평가요소·배점 표를 채점기준으로 인정 (세부 채점 설명 없음)",
            )
    if f == "task_text" and value_status(a) == "source_absent" and value_status(b) == "present":
        texts = [clean(v["raw"]) for v in b.get("values", [])]
        if len(texts) >= 2 and any(re.search(r"1[.]\s*.+2[.]", t) for t in texts):
            return (
                "과제명과 수행 단계 포함 여부",
                "원문에 없음",
                "그 과제의 원문 과제명과 단계별 수행 내용을 과제 설명으로 인정",
            )
    return None


def question_groups(rows, decisions, lookup_a, lookup_b, pack):
    groups = {}
    displays = {}
    for row in rows:
        decision = decisions[row["불일치ID"]]
        if decision.result != "사용자판정":
            continue
        f = row["필드"]
        a, b = json.loads(row["A값"]), json.loads(row["B값"])
        if decision.candidates:
            a, b = decision.candidates["A"], decision.candidates["B"]
        cause = question_cause(f, a, b, pack)
        signature = (
            (row["학교"], f, cause[0])
            if cause
            else (row["학교"], f, human_value(f, a, 100000), human_value(f, b, 100000))
        )
        if signature not in groups:
            groups[signature] = []
            displays[signature] = (
                (cause[1], cause[2])
                if cause
                else (human_value(f, a, 100000), human_value(f, b, 100000))
            )
        groups[signature].append(row)
    result = []
    for n, (signature, group) in enumerate(groups.items(), 1):
        q = f"Q{n:02d}"
        row = group[0]
        for entry in group:
            decisions[entry["불일치ID"]].question = q
        left, right = lookup_a.get(row["A항목키"]), lookup_b.get(row["B항목키"])
        titles = [
            v for it in (left, right) if it for f in ("title", "task_text") for v in it[f]["values"]
        ]
        title = representative(titles)
        display_title = (
            title["raw"] if title else f"문서 {row.get('원문 위치', '').split(':', 1)[0]}"
        )
        result.append(
            {
                "question": q,
                "rows": group,
                "title": display_title,
                "A": displays[signature][0],
                "B": displays[signature][1],
            }
        )
    return result


def read_answers(path, questions):
    allowed = {q["question"] for q in questions}
    aliases = {
        "a": "A",
        "b": "B",
        "둘다": "둘다",
        "둘 다": "둘다",
        "둘 다 아님": "둘다아님",
        "둘다아님": "둘다아님",
    }
    answers = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["질문번호", "답"]:
            raise ValueError("답 CSV 머리글은 질문번호,답 이어야 함")
        for row in reader:
            q, answer = row["질문번호"].strip().upper(), row["답"].strip().lower()
            if q not in allowed or answer not in aliases or q in answers:
                raise ValueError(f"알 수 없는/중복 질문 또는 답: {q}, {answer}")
            answers[q] = aliases[answer]
    if allowed - answers.keys():
        raise ValueError("답이 빠진 질문: " + ", ".join(sorted(allowed - answers.keys())))
    return answers


def apply_answers(records, answers):
    result = copy.deepcopy(records)
    for record in result:
        for f, cell in record["fields"].items():
            if not cell["source"].startswith("대기:"):
                continue
            q = cell["source"].split(":", 1)[1]
            answer = answers[q]
            if answer == "둘다아님":
                cell.update(
                    status="ambiguous",
                    value=None,
                    accepted=[],
                    source=f"사용자:{q}",
                    answer=answer,
                    note="두 후보 기각; 대체 정답을 만들지 않음",
                )
                continue
            if f.endswith("존재") and answer == "둘다":
                accepted = [v for v in (cell["A"], cell["B"]) if v is not None]
            else:
                accepted = (
                    [cell[answer]] if answer in {"A", "B"} else unique([cell["A"], cell["B"]])
                )
            val = None
            for candidate in accepted:
                val = merge(val, candidate)
            state = value_status(val)
            if answer == "둘다" and cell["A"] != cell["B"]:
                state = "conflict" if f == "title" else state
            cell.update(
                status=state, value=val, accepted=accepted, source=f"사용자:{q}", answer=answer
            )
        refresh_titles(record)
    finalized = []
    for record in result:
        if record.get("merged_into"):
            continue
        exists = record["fields"].get("항목 존재") or record["fields"].get("문서 존재")
        if exists and exists["value"] is None and exists.get("answer") != "둘다아님":
            continue
        finalized.append(record)
    return finalized


def run(a_path, b_path, disagreements, pack_path, output, answers_path=None):
    a, _, ae = read_labels(a_path)
    b, _, be = read_labels(b_path)
    if ae or be:
        raise ValueError("; ".join(ae + be))
    with disagreements.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    # Bind IDs to freshly reproduced v2 content. Stale CSV must fail closed.
    fresh, pairing_summary = compare_labels(a, b, pack_path)
    columns = ("불일치ID", "필드", "A항목키", "B항목키", "A값", "B값", "원문 위치")
    if len(rows) != len(fresh) or any(
        any(x[c] != y[c] for c in columns) for x, y in zip(rows, fresh, strict=True)
    ):
        raise ValueError("disagreements.csv가 현재 입력의 v2 비교 결과와 다름")
    items_a = sorted((x for x in a if x["type"] == "item"), key=lambda x: x["item_key"])
    items_b = sorted((x for x in b if x["type"] == "item"), key=lambda x: x["item_key"])
    lookup_a = {x["item_key"]: x for x in items_a}
    lookup_b = {x["item_key"]: x for x in items_b}
    pack = Pack(pack_path)
    ib, ib_evidence = ib_groups(items_a, items_b, pack)
    decisions = {
        row["불일치ID"]: adjudicate(
            row,
            lookup_a.get(row["A항목키"]),
            lookup_b.get(row["B항목키"]),
            pack,
            ib,
            ib_evidence,
        )
        for row in rows
    }
    questions = question_groups(rows, decisions, lookup_a, lookup_b, pack)
    diff_lookup = {
        (row["A항목키"], row["B항목키"], row["필드"]): decisions[row["불일치ID"]]
        for row in rows
        if row["종류"] != "문서"
    }
    pairs, only_a, only_b = match_items(items_a, items_b)
    slots = [(items_a[i], items_b[j]) for i, j in pairs]
    slots += [(items_a[i], None) for i in only_a] + [(None, items_b[j]) for j in only_b]
    draft = []
    for left, right in slots:
        item = left or right
        record = {k: item[k] for k in ("type", "school_id", "grade", "semester", "item_key")}
        record["input_keys"] = {
            "A": left["item_key"] if left else None,
            "B": right["item_key"] if right else None,
        }
        record["adjudication_key"] = (
            f"A:{record['input_keys']['A'] or ''}|B:{record['input_keys']['B'] or ''}"
        )
        keys = (record["input_keys"]["A"] or "", record["input_keys"]["B"] or "")
        owner_key = next(
            (
                (s, x["item_key"])
                for s, x in (("A", left), ("B", right))
                if x and (s, x["item_key"]) in ib
            ),
            None,
        )
        owner = ib.get(owner_key)
        if owner is not None and left is not owner and right is not owner:
            record["merged_into"] = owner["item_key"]
            record["merged_into_side"] = "A" if owner in items_a else "B"
        record["occurrences"] = unique(
            (left or {}).get("occurrences", []) + (right or {}).get("occurrences", [])
        )
        record["aliases"] = unique(
            [v for x in (left, right) if x for f in ("title", "task_text") for v in x[f]["values"]]
        )
        if owner is not None and not record.get("merged_into"):
            members = [(side, key) for (side, key), target in ib.items() if target is owner]
            record["merged_inputs"] = [
                {"side": side, "record": (lookup_a if side == "A" else lookup_b)[key]}
                for side, key in members
            ]
            record["aliases"] = unique(
                record["aliases"]
                + [
                    v
                    for member in record["merged_inputs"]
                    for f in ("title", "task_text")
                    for v in member["record"][f]["values"]
                ]
            )
        record["fields"] = {}
        if left is None or right is None:
            record["fields"]["항목 존재"] = envelope(left, right, diff_lookup[(*keys, "항목 존재")])
        for f in CONTENT_FIELDS:
            av = (left["title"].get("role") if f == "title_role" else left[f]) if left else None
            bv = (right["title"].get("role") if f == "title_role" else right[f]) if right else None
            d = diff_lookup.get((*keys, f))
            if owner is not None:
                chosen = owner["title"].get("role") if f == "title_role" else owner[f]
                d = select(
                    chosen, None, "A", [6], ib_evidence[owner_key], "기존 과제 단위 구조 선택"
                )
                # Rule 5 also applies to agreed/structurally merged periods.
                if f == "period":
                    val, rules, es, excluded, changed = filter_source(f, chosen, pack)
                    if changed:
                        d = select(
                            val,
                            None,
                            "A",
                            [5, 6],
                            es + ib_evidence[owner_key],
                            "과제 단위 구조; 평가계획 시기만 정답",
                        )
                        d.references = excluded
            elif (
                d is None
                and left is not None
                and right is not None
                and f
                in {
                    "period",
                    "method",
                    "rubric",
                }
            ):
                # Shared but inadmissible source values are also only references.
                d = source_decision(f, av, bv, pack)
                if d and d.result == "사용자판정":
                    raise ValueError(f"합의 필드의 규칙 적용 후 새 불일치: {keys} {f}")
            record["fields"][f] = envelope(av, bv, d)
        refresh_titles(record)
        draft.append(record)
    docs_a = {x["doc_id"]: x for x in a if x["type"] == "document"}
    docs_b = {x["doc_id"]: x for x in b if x["type"] == "document"}
    doc_rows = defaultdict(dict)
    for row, original in zip(rows, fresh, strict=True):
        if row["종류"] == "문서":
            doc_rows[original["_doc_id"]][row["필드"]] = decisions[row["불일치ID"]]
    for doc_id in sorted(docs_a.keys() | docs_b.keys()):
        left, right = docs_a.get(doc_id), docs_b.get(doc_id)
        item = left or right
        record = {
            "type": "document",
            "doc_id": doc_id,
            "school_id": item["school_id"],
            "fields": {},
        }
        for f in ("edition", "science_sections"):
            record["fields"][f] = envelope(
                (left or {}).get(f), (right or {}).get(f), doc_rows[doc_id].get(f)
            )
        if left is None or right is None:
            record["fields"]["문서 존재"] = envelope(left, right, doc_rows[doc_id]["문서 존재"])
        draft.append(record)
    # Validate answers before publishing any artifact, so invalid/incomplete input
    # cannot leave a seemingly finalized file behind.
    final = apply_answers(draft, read_answers(answers_path, questions)) if answers_path else None
    output.mkdir(parents=True, exist_ok=True)
    ledger = []
    for row in rows:
        d = decisions[row["불일치ID"]]
        ledger.append(
            {
                **row,
                "적용규칙": "|".join(map(str, d.rules)),
                "결과": d.result,
                "정답값요약": (
                    f"미정:{d.question}"
                    if d.result == "사용자판정"
                    else human_value(row["필드"], d.value)
                ),
                "근거위치": " / ".join(e.position for e in unique_evidence(d.evidence)),
                "근거발췌": short(" / ".join(e.excerpt for e in unique_evidence(d.evidence)), 80),
                "판정방식": d.mode,
                "메모": d.memo,
                "질문번호": d.question,
            }
        )
    csv_write(output / "rules_applied.csv", ledger, RULE_COLUMNS)
    queue = []
    pending_count = sum(len(q["rows"]) for q in questions)
    md = [
        f"사용자 판정 {len(questions)}문항 · 영향 불일치 {pending_count}건",
        "고르기: A / B / 둘 다 / 둘 다 아님 (묶음은 같은 답을 함께 적용)",
        "번호와 답만 보내면 됨: 예 Q01 A, Q02 둘다",
        "",
    ]
    for q in questions:
        group, row = q["rows"], q["rows"][0]
        qid = q["question"]
        es = unique_evidence(decisions[row["불일치ID"]].evidence)
        if len(es) > 2:
            es = [es[0], es[-1]]
        excerpt = " / ".join(e.excerpt for e in es[:2]) or clean(row["원문 발췌"])
        position = " / ".join(e.position for e in es[:2]) or " / ".join(
            row["원문 위치"].split(" / ")[:2]
        )
        terms = list(dict.fromkeys(f"{r['학년']}학년 {r['학기']}학기" for r in group))
        term = " · ".join(terms) if row["학년"] else "문서 전체"
        impact = f" (같은 선택 {len(group)}건)" if len(group) > 1 else ""
        field_name = FIELD_NAMES.get(row["필드"], row["필드"])
        cause = question_cause(row["필드"], json.loads(row["A값"]), json.loads(row["B값"]), pack)
        reason = (
            cause[0]
            if cause
            else {
                "method": "방법의 내용 또는 체크·확실성이 다름",
                "rubric": "채점표의 범위 또는 판독 확실성이 다름",
                "science_sections": "과학으로 잡은 원문 줄 범위가 다름",
                "standards": "성취기준의 범위 또는 확실성이 다름",
                "task_text": "과제 설명에 넣은 내용이 다름",
                "task_no": "번호에 포함한 글이 다름",
                "ratio": "비율 값 또는 확실성이 다름",
            }.get(row["필드"], "적은 값 또는 확실성이 다름")
        )
        md += [
            f"### {qid}. {row['학교']} {term} · 「{short(clean(q['title']), 90)}」",
            f"무엇이 다른가: {field_name}{impact} · {reason}",
            f'원문: "{short(excerpt, 200)}" ({position})',
            f"A안: {short(q['A'], 500)}",
            f"B안: {short(q['B'], 500)}",
            "고르기: A / B / 둘 다 / 둘 다 아님",
            "",
        ]
        queue.append(
            {
                "질문번호": qid,
                "영향건수": len(group),
                "불일치ID": "|".join(x["불일치ID"] for x in group),
                "학교": row["학교"],
                "학년학기": " / ".join(dict.fromkeys(f"{x['학년']}-{x['학기']}" for x in group)),
                "항목대표제목": q["title"],
                "필드": row["필드"],
                "A안": q["A"],
                "B안": q["B"],
                "개별선택지": " / ".join(
                    f"{r['불일치ID']} A: {human_value(r['필드'], json.loads(r['A값']), 100000)}"
                    f" ; B: {human_value(r['필드'], json.loads(r['B값']), 100000)}"
                    for r in group
                ),
                "원문위치": " / ".join(dict.fromkeys(x["원문 위치"] for x in group)),
                "원문발췌": short(excerpt, 200),
            }
        )
    csv_write(
        output / "queue_v3.csv",
        queue,
        (
            "질문번호",
            "영향건수",
            "불일치ID",
            "학교",
            "학년학기",
            "항목대표제목",
            "필드",
            "A안",
            "B안",
            "개별선택지",
            "원문위치",
            "원문발췌",
        ),
    )
    atomic_text(output / "queue_v3.md", "\n".join(md))
    atomic_text(output / "gold_v1_draft.jsonl", "".join(json_text(x) + "\n" for x in draft))
    rule0_count = sum(rule0(json.loads(r["A값"]), json.loads(r["B값"])) for r in rows)
    incremental, remaining, applications = Counter(), len(rows) - rule0_count, Counter()
    reopened = Counter()
    for row in rows:
        d = decisions[row["불일치ID"]]
        applications.update(d.rules)
        if 0 in d.rules and d.result == "사용자판정":
            reopened[min(n for n in d.rules if n != 0)] += 1
        if d.result != "사용자판정" and not rule0(json.loads(row["A값"]), json.loads(row["B값"])):
            if d.rules:
                incremental[min(d.rules)] += 1
    steps = []
    for n in range(1, 7):
        remaining += reopened[n] - incremental[n]
        steps.append(
            {"rule": n, "resolved": incremental[n], "reopened": reopened[n], "remaining": remaining}
        )
    summary = {
        "input_disagreements": len(rows),
        "rule0_resolved": rule0_count,
        "after_rule0": len(rows) - rule0_count,
        "rule0_reopened": sum(reopened.values()),
        "steps": steps,
        "rule_applications": {str(n): applications[n] for n in range(7)},
        "rule_resolved": {
            str(n): sum(n in d.rules and d.result != "사용자판정" for d in decisions.values())
            for n in range(7)
        },
        "results": dict(Counter(d.result for d in decisions.values())),
        "remaining_questions": len(questions),
        "remaining_disagreements": len([d for d in decisions.values() if d.result == "사용자판정"]),
        "judgment_count": sum(d.mode == "판단" for d in decisions.values()),
        "low_confidence": [
            r["불일치ID"] for r in rows if "확신 낮음" in decisions[r["불일치ID"]].memo
        ],
        "pairing": pairing_summary["item_pairing"],
        "draft_item_slots": len(slots),
        "merged_redirects": sum(bool(r.get("merged_into")) for r in draft),
        "canonical_items": sum(r["type"] == "item" and not r.get("merged_into") for r in draft),
        "documents": len(docs_a.keys() | docs_b.keys()),
        "rule0_definition": (
            "present + raw 정규표기 또는 기존 norm 숫자 교집합. 위치/메모/옵션 메타 제외"
        ),
        "counting": (
            "단계별 해결은 규칙0 미해결 건의 최초 해결 규칙(복수면 작은 번호). 적용 수는 중복 포함"
        ),
        "draft_format": (
            "필드별 판정 봉투; A/B는 원본, value는 선택/합집합. 대기는 value=null, 양쪽 보존"
        ),
        "answers_neither": "둘다아님은 두 후보 기각(ambiguous/null). 원문 없음으로 추정하지 않음",
    }
    atomic_text(
        output / "rules_summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    if final is not None:
        atomic_text(output / "gold_v1.jsonl", "".join(json_text(x) + "\n" for x in final))
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument(
        "--disagreements", type=Path, default=DEFAULT_PACK.parent / "disagreements.csv"
    )
    parser.add_argument("--pack-dir", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_PACK.parent)
    parser.add_argument("--answers", type=Path, help="UTF-8 CSV: 질문번호,답")
    args = parser.parse_args(argv)
    try:
        summary = run(args.a, args.b, args.disagreements, args.pack_dir, args.out_dir, args.answers)
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
