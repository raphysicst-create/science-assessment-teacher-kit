"""S6 항목의 단원·활동을 science-axes-v2 규칙으로 분류한다.

실행: .venv/Scripts/python.exe scripts/science_axes.py classify --items INPUT --out OUTPUT
검증: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
      services/math-assessment-api/tests/test_science_axes_classifier.py
S층은 평평한 배열에서 수준 순서의 재시작으로 묶음을 찾는 '최고 수준 문장 근사'다.
S층 어미 판별은 끝 괄호 묶음을 제외하되 문장 전체를 감싼 괄호는 유지한다.
활동 나열은 단순 분리하고 한 어절 항목에 앞 항목의 머리말만 붙인다. 복잡한 병렬문은 복원하지 않는다.
R3은 마지막 어절(평가 바로 앞 포함)의 방법어 접미를 긴 낱말부터 대조한다.
접미 앞부분의 단원·개념명 여부는 검사하지 않는 근사다.
평문 방법은 쉼표·슬래시·줄바꿈으로 분리한다. 값과 선택지가 비면 근거의 HTML·월 표기를 정리해 쓴다.
R4는 사전의 하다 동사형을 하 어간으로 줄이고 하/함/할 활용형을 대조한다. 명사는 부분 일치한다.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXES = json.loads((ROOT / "data/reference/science_axes.json").read_text(encoding="utf-8"))
ACTIVITY_NAMES = [a["name"] for a in AXES["activities"]]
DOTS = str.maketrans({c: "·" for c in "·ㆍ･⋅・‧"})
MAKING_END = re.compile(r"(?:만들기|제작하기|제작|디자인하기|디자인)\s*$")
DOCUMENTS = (
    "노트", "포트폴리오", "보고서", "계획서", "글", "일기", "일지", "시나리오", "발표 자료",
)
BULLETS = re.compile(r"[\n•▪§∘▶Ÿ※]|(?<!\S)-\s*|(?<!\S)(?:\d+\.|[ivxlcdmⅰ-ⅻ]+\.)\s*|[①-⑳]")
LEVEL = re.compile(
    r"^(?:[A-E]|\d+(?:\.\d+)?(?:점)?|상|중|하|우수|보통|미흡|매우우수|노력요함|"
    r"(?:채점)?기준\d+개(?:이상|이하)?충족.*)$"
)
SCORING_END = re.compile(r"(?:함|음|됨|임|다|니다|했다|한다|있다|없다|경우|이상|미만|만족|충족)$")
SCORING_PHRASE = re.compile(
    r"채점요소를|\d+개서술|\d+가지(?:이상|만족|충족)|모두(?:만족|충족)|"
    r"우수함|보통임|미흡함|부족함|못함|않음"
)
LEXICON_VERB_END = re.compile(r"(?:하기|하다|함|할|하는|하여|하고)$")
VERB_STEM_FORMS = ("하", "함", "할")
METHOD_SEPARATOR = re.compile(r"[,/\r\n]+")
HTML_TAG = re.compile(r"<[^>]*>")
MONTH_NOTE = re.compile(r"\(\s*\d{1,2}\s*(?:(?:월\s*)?[~～\-–]\s*\d{1,2}\s*)?월\s*\)")
METHOD_WORDS = {
    "실험": "experiment", "프로젝트": "project", "포트폴리오": "portfolio",
    "보고서": "report", "글쓰기": "report", "논술": "essay", "서·논술형": "essay",
    "발표": "presentation", "구술": "presentation", "토론": "presentation",
    "탐구": "project", "탐구활동": "project",
}
NO_CHECKS = "없음(평문/방법어/투표만)"
ACTION_ENDING = re.compile(
    r"(?:하고|하여|하며|하기|하는|하자|할|함|됨|되어|되는|된|한다|있다|없다|읽고|읽기|쓰고|쓰기|보고)$"
)


def normalize(text):
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text.translate(DOTS)).translate(DOTS))


def strings(value):
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [v for v in value if isinstance(v, str) and v.strip()] if isinstance(value, list) else []


def field(item, name):
    fields = item.get("fields")
    value = fields.get(name) if isinstance(fields, dict) else None
    return value if isinstance(value, dict) else {}


def text_field(item, name):
    value = field(item, name).get("value")
    return value if isinstance(value, str) else ""


def guard_path(path):
    path = Path(path)
    if ("gold" in (str(path) + str(path.resolve())).lower()
            and os.environ.get("SCIENCE_AXES_GOLD") != "chief-measurement"):
        raise ValueError("맹검 경로")
    return path


def split_units(text):
    result = []
    # NFKC가 원문자의 번호 테두리를 지우기 전에 경계를 보존한다.
    text = re.sub(r"[①-⑳]", "\n", text.translate(DOTS))
    for bullet in BULLETS.split(unicodedata.normalize("NFKC", text).translate(DOTS)):
        parts = re.split(r"·|및", bullet)
        prefix = ""
        for part in parts:
            part = part.strip(" \t-")
            if not part:
                continue
            words = part.split()
            if len(words) == 1 and prefix:
                part = prefix + " " + part
            elif len(words) > 1:
                prefix = " ".join(words[:-1])
            result.append(part)
    return result


def level_rank(text):
    text = normalize(text)
    if not LEVEL.fullmatch(text):
        return None
    if re.fullmatch(r"[A-E]", text):
        return ord(text) - ord("A")
    if re.fullmatch(r"\d+(?:\.\d+)?(?:점)?", text):
        return -float(text.removesuffix("점"))
    return {
        "매우우수": 0, "우수": 1, "상": 1, "보통": 2, "중": 2, "미흡": 3, "하": 3, "노력요함": 4,
    }.get(text, 5)


def rubric_units(value):
    values = strings(value)
    leading = bool(values and level_rank(values[0]) is not None)
    blocks, sentence, rank = [], None, None
    for text in values:
        current = level_rank(text)
        if current is None:
            if sentence is None:
                sentence = text
        elif leading:
            if sentence is not None:
                blocks.append((sentence, rank))
            sentence, rank = None, current
        else:
            if sentence is not None:
                blocks.append((sentence, current))
            sentence = None
    if sentence is not None:
        blocks.append((sentence, rank))
    result, previous = [], None
    for sentence, rank in blocks:
        if previous is None or rank is None or rank <= previous:
            result.append(sentence)
        previous = rank
    return result


def is_scoring_sentence(text):
    shaped = unicodedata.normalize("NFKC", text).strip()
    ending = shaped.rstrip(" .。")
    while ending.endswith(")"):
        depth = 0
        for index in range(len(ending) - 1, -1, -1):
            depth += (ending[index] == ")") - (ending[index] == "(")
            if depth == 0:
                break
        if depth or not ending[:index].strip():
            break
        ending = ending[:index].rstrip(" .。")
    ending = re.sub(r"[.。()]", "", normalize(ending))
    return bool(SCORING_END.search(ending) or SCORING_PHRASE.search(normalize(shaped))
                or re.match(r"^[A-E]\s", shaped))


def activity_units(item):
    """출처 순서로 중복을 예약하고 연속한 S층마다 최고 수준 문장을 고른다."""
    seen, units_e, units_s = set(), [], []
    for source in ("title", "assessment_area", "elements", "task_text", "rubric"):
        named = source in ("title", "assessment_area")
        values = [text_field(item, source)] if named else strings(field(item, source).get("value"))
        quotes = []
        for text in values:
            if named or level_rank(text) is not None:
                quotes.append(text)
            else:
                quotes.extend(split_units(text))
        records = []
        for quote in quotes:
            key = normalize(quote)
            if not key:
                continue
            scoring = not named and (source == "rubric" or is_scoring_sentence(quote)
                                     or level_rank(quote) is not None)
            records.append((scoring, quote, key not in seen))
            seen.add(key)
        for scoring, group in groupby(records, key=lambda row: row[0]):
            group = list(group)
            fresh = {normalize(quote) for _, quote, unique in group if unique}
            quotes = [quote for _, quote, _ in group]
            selected = rubric_units(quotes) if scoring else quotes
            kind = "title_verb" if source == "title" else source
            kind = "rubric_s" if scoring else ("rubric_e" if not named else kind)
            for quote in selected:
                key = normalize(quote)
                if key in fresh:
                    (units_s if scoring else units_e).append((kind, quote))
                    fresh.remove(key)
    return units_e, units_s


def checkbox_class(text):
    normalized = normalize(text).removesuffix("평가")
    hits = []
    for name, definition in AXES["checkbox_classes"].items():
        for pattern in definition["patterns"]:
            match = normalize(pattern)
            if match in normalized:
                hits.append((normalized.rfind(match) + len(match), len(match), name))
    # 마지막 어절에 가장 가깝게 끝나는 표지가 머리명사다. 같은 끝이면 긴 표지를 쓴다.
    return max(hits)[2] if hits else None


def method_texts(method):
    """평문 값이 없으면 근거 원문을 정리하고 방법 나열을 분리한다."""
    values = strings(method.get("value"))
    if not values:
        evidence = method.get("evidence")
        evidence = evidence if isinstance(evidence, list) else []
        for entry in evidence:
            if not isinstance(entry, dict):
                continue
            raw = strings(entry.get("raw")) or strings(entry.get("text"))
            for text in raw:
                text = unicodedata.normalize("NFKC", text)
                values.append(MONTH_NOTE.sub(" ", HTML_TAG.sub(" ", text)))
    return [part.strip() for text in values
            for part in METHOD_SEPARATOR.split(text) if part.strip()]


def named_method_entries(item):
    """제목·영역의 마지막 어절에서 가장 긴 방법어 접미를 고른다.

    R3 근사: 마지막 어절 앞의 어절에 행위 어미(…하고·…하여·…하기 등)가 있으면
    내용어가 단원·개념명뿐이 아니므로 방법어로 인정하지 않는다.
    """
    entries = []
    for text in (text_field(item, "title"), text_field(item, "assessment_area")):
        words = unicodedata.normalize("NFKC", text).translate(DOTS).split()
        tail = normalize(words[-1]) if words else ""
        if tail == "평가" and len(words) > 1:
            tail = normalize(words[-2])
            heads = words[:-2]
        else:
            tail = tail.removesuffix("평가")
            heads = words[:-1]
        if any(ACTION_ENDING.search(normalize(word)) for word in heads):
            continue
        for word in sorted(METHOD_WORDS, key=len, reverse=True):
            if tail.endswith(normalize(word)):
                entries.append(("assessment_area", text, METHOD_WORDS[word]))
                break
    return entries


def method_candidates(item):
    method = field(item, "method")
    options = method.get("options")
    options = [o for o in options if isinstance(o, dict)] if isinstance(options, list) else []
    checked = [o for o in options if o.get("state") == "checked"]
    entries = []
    for option in checked:
        label = option.get("option_text", "")
        label = label if isinstance(label, str) else ""
        other = option.get("other_content")
        other = other if isinstance(other, str) else ""
        if normalize(label).startswith("기타"):
            label = "기타(" + other + ")" if other.strip() else "기타"
        elif other.strip():
            label += "(" + other + ")"
        entries.append(("checkbox", label, checkbox_class(label)))
    plain = method_texts(method) if not options else []
    if not checked:
        entries.extend(("method_text", text, checkbox_class(text)) for text in plain)
    if not checked and not plain:
        entries.extend(named_method_entries(item))
    candidates, classes, evidence = [], [], []
    for kind, quote, cls in entries:
        activity = AXES["checkbox_classes"].get(cls, {}).get("activity")
        if cls and cls not in classes:
            classes.append(cls)
        if activity and activity not in candidates:
            candidates.append(activity)
        evidence.append({"type": kind, "quote": quote, "activity": activity})
    return candidates, classes, evidence


def lexicon_matches(term, normalized):
    term = normalize(term)
    stem = LEXICON_VERB_END.sub("하", term)
    if stem == term:
        return term in normalized
    return any(stem[:-1] + ending in normalized for ending in VERB_STEM_FORMS)


def vote(units):
    votes = dict.fromkeys(ACTIVITY_NAMES, 0)
    evidence = []
    for kind, quote in units:
        normalized = normalize(quote)
        for activity in AXES["activities"]:
            name = activity["name"]
            excluded = any(lexicon_matches(s, normalized)
                           for s in activity.get("exclusions_in_lexicon", []))
            count = int(any(lexicon_matches(s, normalized) for s in activity["lexicon"]))
            if kind == "title_verb" and name == "제작":
                excluded |= any(normalize(s) in normalized for s in DOCUMENTS)
                if MAKING_END.search(quote):
                    count = activity["title_verb_weight"]
            if count and not excluded:
                votes[name] += count
                evidence.append({"type": kind, "quote": quote, "activity": name})
    return votes, evidence


def leaders(votes):
    highest = max(votes.values(), default=0)
    return [name for name, count in votes.items() if highest and count == highest]


def choose_primary(candidates, classes, votes, title_votes):
    top = leaders(votes)
    if len(candidates) == 1:
        default = candidates[0]
        if default == "추론·설명" and votes["작성"] >= 1:
            return "작성", None, "R5-①"
        if default == "탐구" and votes["제작"] >= 1:
            return "제작", None, "R5-②"
        if len(top) == 1 and votes[top[0]] >= 2 and votes[top[0]] > votes[default]:
            return top[0], None, "R5-③"
        if "report" in classes and top:
            titled = [name for name in top if title_votes[name]]
            chosen = top[0] if len(top) == 1 else (
                titled[0] if len(titled) == 1 else ("탐구" if "탐구" in top else "작성"))
            return chosen, None, "R5-④"
        return default, None, "R5"
    rule = "R6" if candidates else "R7"
    if not top:
        return None, "체크 여러 개·요소 근거 없음" if candidates else "근거 없음", rule
    if len(top) == 1:
        return top[0], None, rule
    included = [name for name in top if name in candidates]
    if candidates and len(included) == 1:
        return included[0], None, rule
    return None, "근거 동률", rule


def classify_unit(item):
    codes = strings(field(item, "standards").get("value"))
    areas = []
    for code in codes:
        for area in AXES["units"]["areas"]:
            if normalize(code) in [normalize(s) for s in area["standards"]]:
                existing = next((a for a in areas if a["area_no"] == area["area_no"]), None)
                if existing is None:
                    existing = {"area_no": area["area_no"], "area": area["area"],
                                "basis": "standard_code", "evidence": []}
                    areas.append(existing)
                if code not in existing["evidence"]:
                    existing["evidence"].append(code)
    title = (text_field(item, "title")
             if item.get("title_role") in ("평가영역", "assessment_area") else "")
    raw = text_field(item, "assessment_area") or title
    normalized = re.sub(r"\(\d+월\)", "", normalize(raw))
    named = next((a for a in AXES["units"]["areas"] if normalize(a["area"]) == normalized), None)
    conflict = bool(areas and named and {a["area_no"] for a in areas} != {named["area_no"]})
    if not areas and named:
        areas = [{"area_no": named["area_no"], "area": named["area"],
                  "basis": "area_name", "evidence": [raw]}]
    status = "conflict" if conflict else ("confirmed" if areas else "undetermined")
    return {"areas": areas, "status": status,
            "reason": "코드·영역명 충돌" if conflict else (None if areas else "코드·영역명 없음")}


def classify_item(item):
    candidates, classes, evidence = method_candidates(item)
    units_e, units_s = activity_units(item)
    title_units = [unit for unit in units_e if unit[0] == "title_verb"]
    votes_e, evidence_e = vote(units_e)
    votes_s, evidence_s = vote(units_s)
    title_votes, _ = vote(title_units)
    primary, reason, rule = choose_primary(
        candidates, classes, votes_e if any(votes_e.values()) else votes_s, title_votes)
    totals = {name: votes_e[name] + votes_s[name] for name in ACTIVITY_NAMES}
    secondary = [name for name in ACTIVITY_NAMES
                 if name != primary and (totals[name] or name in candidates)]
    secondary.sort(key=lambda name: (
        -totals[name], name not in candidates, ACTIVITY_NAMES.index(name)))
    result = {name: item.get(name) for name in (
        "item_id", "school", "school_code", "grade", "semester", "extraction_status")}
    result.update(title=text_field(item, "title"), unit=classify_unit(item), activity={
        "primary": primary, "secondary": secondary, "abstain_reason": reason,
        "candidates": candidates, "candidate_classes": classes,
        "votes_e": votes_e, "votes_s": votes_s,
        "evidence": evidence + evidence_e + evidence_s, "rule_applied": rule,
    })
    return result


def summary(items):
    return {
        "item_count": len(items),
        "primary_counts": dict(Counter(i["activity"]["primary"] or "기권" for i in items)),
        "abstain_reasons": dict(Counter(i["activity"]["abstain_reason"] for i in items
                                        if i["activity"]["primary"] is None)),
        "unit_status": dict(Counter(i["unit"]["status"] for i in items)),
        "area_counts": dict(Counter(a["area_no"] for i in items for a in i["unit"]["areas"])),
    }


def classify(document):
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise ValueError("items 배열 필요")
    items = [classify_item(i) for i in document["items"] if isinstance(i, dict)
             and i.get("candidate_role") == "performance"
             and i.get("extraction_status") in ("bounded", "ai_verified")]
    return {"rule_version": AXES["version"], "definition_version": AXES["definition_version"],
            "round": document.get("round"), "items": items, "summary": summary(items)}


def confusion(documents):
    items = [dict(i, round=d.get("round")) for d in documents for i in d["items"]]
    columns = ACTIVITY_NAMES + ["기권"]
    matrix = {row: dict.fromkeys(columns, 0) for row in ACTIVITY_NAMES + ["복수", NO_CHECKS]}
    transitions = []
    for item in items:
        activity = item["activity"]
        checked = list(dict.fromkeys(e["activity"] for e in activity["evidence"]
                                     if e["type"] == "checkbox" and e["activity"]))
        row = checked[0] if len(checked) == 1 else ("복수" if checked else NO_CHECKS)
        matrix[row][activity["primary"] or "기권"] += 1
        if len(checked) == 1 and checked[0] != activity["primary"]:
            transitions.append({k: item.get(k) for k in ("round", "item_id", "school", "title")} | {
                "candidate": checked[0], "primary": activity["primary"],
                "votes_e": activity["votes_e"], "votes_s": activity["votes_s"],
            })
    counts = {name: {
        "primary": sum(i["activity"]["primary"] == name for i in items),
        "including_secondary": sum(name in [i["activity"]["primary"]] + i["activity"]["secondary"]
                                   for i in items),
    } for name in ACTIVITY_NAMES}
    return {"summary": summary(items), "confusion": matrix,
            "activity_counts": counts, "transitions": transitions}


def markdown_table(headers, rows):
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(map(cell, headers)) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(map(cell, row)) + " |" for row in rows)
    return "\n".join(lines)


def confusion_markdown(report):
    columns = ACTIVITY_NAMES + ["기권"]
    sections = [
        ("체크 기본 후보 × 최종 주활동", ["C"] + columns,
         [[k] + [v[c] for c in columns] for k, v in report["confusion"].items()]),
        ("기권 사유", ["사유", "수"], list(report["summary"]["abstain_reasons"].items())),
        ("활동 분포", ["활동", "주", "보조 포함"],
         [[k, v["primary"], v["including_secondary"]]
          for k, v in report["activity_counts"].items()]),
        ("단원 상태", ["상태", "수"], list(report["summary"]["unit_status"].items())),
        ("영역별 항목", ["영역", "수"], list(report["summary"]["area_counts"].items())),
        ("전환 항목", ["학교", "제목", "C", "주", "E표", "S표"],
         [[t["school"], t["title"], t["candidate"], t["primary"], t["votes_e"], t["votes_s"]]
          for t in report["transitions"]]),
    ]
    return "\n\n".join("## " + title + "\n\n" + markdown_table(headers, rows)
                       for title, headers, rows in sections) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("classify", "confusion"):
        child = sub.add_parser(command)
        child.add_argument("--items", required=True, nargs="+" if command == "confusion" else None)
        child.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        paths = args.items if isinstance(args.items, list) else [args.items]
        outputs = ([guard_path(args.out)] if args.command == "classify" else
                   [guard_path(args.out + suffix) for suffix in (".json", ".md")])
        inputs = [guard_path(p) for p in paths]
        documents = [json.loads(p.read_text(encoding="utf-8-sig")) for p in inputs]
        result = classify(documents[0]) if args.command == "classify" else confusion(documents)
        contents = [json.dumps(result, ensure_ascii=False, indent=2) + "\n"]
        if args.command == "confusion":
            contents.append(confusion_markdown(result))
        for path, content in zip(outputs, contents, strict=False):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
