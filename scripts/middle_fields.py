"""S6d-3 field rules; only literal cells owned by an item or scoped policy evidence."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

METHOD_RE = re.compile(
    r"(?:실험(?:[·ㆍ\s]?실습)?|실습|실기|탐구|보고서(?:법)?|관찰(?:평가|법)?|"
    r"서[·ㆍ]?논술형?|서술형|논술형|서논술형|서술논술형|구술(?:[·ㆍ]?발표)?|"
    r"발표|토의|토론|프로젝트|포트폴리오|면접|자기평가|동료평가|"
    r"교사평가|교사\s*관찰\s*및\s*기록|선택형|단답형|모둠|개별|지필평가|"
    r"체크리스트|수업\s*참여도)(?:\s*평가)?"
)
LEVEL_RE = re.compile(
    r"[ABCDE](?:\s*[·ㆍ,/~-]\s*[ABCDE])*|상|중|하|매우\s*우수|우수|보통|미흡|매우\s*미흡"
    r"|\d+(?:\.\d+)?(?:\s*[~∼-]\s*\d+(?:\.\d+)?)?\s*점?"
)


def method_literal(value):
    parts = re.split(r"\s*[,，/·ㆍ\n]+\s*", value.strip())
    return bool(parts) and all(METHOD_RE.fullmatch(p) for p in parts)


@lru_cache(maxsize=1)
def reference_codes():
    data = json.loads((Path(__file__).resolve().parents[1]
                       / "data/reference/standards_middle_science_2022.json").read_text(
                           encoding="utf-8"))
    return tuple(s["code"] for s in data["standards"])


def title_parts(cell):
    """An explicit prefixed task number is separate from the literal task name."""
    if __package__:
        from .middle_items import cell_part
    else:
        from middle_items import cell_part
    if re.search(r"(?:<br\s*/?>|\n)\s*\d+\s*[.)]", cell["raw"], re.I):
        return None, cell  # A list of subactivities is task text, not a task number.
    match = re.fullmatch(
        r"\s*((?:수행\s*평가|과제|실험|탐구)\s*\d+|\d+\s*(?:차|회)|[①-⑳]"
        r"|\d+(?=\s*[:：.)-]))"
        r"\s*(?:[:：.)-]\s*|<br\s*/?>\s*|\s+)(.+?)\s*", cell["raw"], re.S | re.I,
    )
    return (cell_part(cell, *match.span(1)), cell_part(cell, *match.span(2))) if match else (
        None, cell,
    )


def title_alias_key(value):
    # Normalize only unambiguous orthographic errors, never activity synonyms.
    value = unicodedata.normalize("NFKC", value)
    for wrong, correct in (("됬", "됐"), ("되요", "돼요"), ("했읍", "했습"), ("하였읍", "하였습")):
        value = value.replace(wrong, correct)
    return re.sub(r"[\s·ㆍ･‧,，'\"‘’“”]+", "", value)


def enrich_claims(structure):
    """Read element/level columns only inside the already established ownership."""
    if __package__:
        from .middle_items import label_role
    else:
        from middle_items import label_role
    claims, cells = structure["claims"], structure["cells"]
    rows = {}
    for c in cells:
        if "table" in c:
            rows.setdefault((c["table"], c["row"]), []).append(c)
    sub_scores, rubric = [], []
    for header in cells:
        role = label_role(header["text"])
        if role not in {"elements", "rubric"}:
            continue
        for (table, row), values in rows.items():
            if table != header.get("table") or row <= header["row"]:
                continue
            same = [c for c in values if c["col"] == header["col"]]
            if role == "elements":
                for c in same:
                    if c["text"] and not label_role(c["text"]):
                        claims["elements"].append((c, header))
                        inline = re.fullmatch(r"(.+?)\s*\(\s*(\d+(?:\.\d+)?)\s*점?\s*\)",
                                              c["text"])
                        if inline:
                            sub_scores.append((inline[1].strip(), float(inline[2]), [c], header))
                        else:
                            point_headers = [h for h in cells if h.get("table") == table
                                             and h["row"] == header["row"]
                                             and label_role(h["text"]) in {"points", "score"}]
                            for h in point_headers:
                                amounts = [v for v in values if v["col"] == h["col"]
                                           and re.fullmatch(r"\d+(?:\.\d+)?\s*점?", v["text"])]
                                for v in amounts:
                                    sub_scores.append((c["text"], float(re.sub(r"점|\s", "",
                                                                                 v["text"])),
                                                       [c, v], header))
    # Dedicated task rubric: a judgment column and at least two distinct levels.
    # General curriculum achievement tables cannot satisfy this grammar.
    for table in {c.get("table") for c in cells if "table" in c}:
        local = [c for c in cells if c.get("table") == table]
        headers = [c for c in local if label_role(c["text"]) == "rubric"]
        for h in headers:
            judgments, levels = [], set()
            for (t, row), values in rows.items():
                if t != table or row <= h["row"]:
                    continue
                criteria = [c for c in values if h["col"] <= c["col"] < h["col"] + h["colspan"]
                            and c["text"] and not label_role(c["text"])
                            and not LEVEL_RE.fullmatch(c["text"])
                            and re.search(r"함|됨|있|없|임$|한다|이다|미흡|충실|우수|필요|부족|"
                                          r"정확|오류|이상|미만|못|모두|일부|완료", c["text"])]
                scale = [c for c in values if c not in criteria
                         and LEVEL_RE.fullmatch(c["text"])]
                if criteria and scale:
                    judgments.extend(criteria + scale)
                    levels.update(c["text"] for c in scale)
            if len(levels) >= 2:
                rubric.extend((c, h) for c in judgments)
    claims["rubric"] = list({c["start"]: (c, h) for c, h in rubric}.values())
    # Inline element(point) pairs also occur across a form row, not just below
    # a column heading. Keep their original subcell offsets.
    if __package__:
        from .middle_items import cell_part
    else:
        from middle_items import cell_part
    for cell, header in claims.get("elements", []):
        for m in re.finditer(r"([^<>\r\n/]+?)\s*\(\s*(\d+(?:\.\d+)?)\s*점?\s*\)",
                             cell["raw"]):
            part = cell_part(cell, m.start(), m.end())
            sub_scores.append((m[1].strip(), float(m[2]), [part], header))
    return sub_scores


def sub_score_field(entries, conversion):
    if __package__:
        from .middle_items import evidence
    else:
        from middle_items import evidence
    values, observations = [], []
    for element, score, cells, header in entries:
        obs = [evidence(c, conversion, header) for c in cells]
        value = {"element": element, "score": score, "evidence": obs}
        if not any(v["element"] == element and v["score"] == score for v in values):
            values.append(value)
        observations.extend(obs)
    conflicts = {v["element"] for v in values if len(
        {p["score"] for p in values if p["element"] == v["element"]}) > 1}
    if conflicts:
        return {"value": [], "evidence": observations, "status": "conflict",
                "observed_values": values, "conflict_elements": sorted(conflicts),
                "reason": "같은 평가요소의 배점 충돌·수준별 점수를 만점으로 추정하지 않음"}
    return {"value": values, "evidence": observations, "reason": "" if values else
            "요소·배점 쌍 미확인"}


def free_semester_field(structure, section, conversion):
    if __package__:
        from .middle_segments import text_locator
    else:
        from middle_segments import text_locator
    text = conversion["text"]
    start, end = section["locator"]["start"], section["locator"]["end"]
    references = []
    # S4/S5 grade/term scope is mandatory: never borrow another term's policy.
    pattern = r"자유\s*학(?:기|년)(?:제)?|성취도\s*(?:미산출|산출하지\s*않)|이수\s*/\s*미이수"
    for m in re.finditer(pattern, text[start:end]):
        left, right = start + m.start(), start + m.end()
        # Explicit policy for a different grade/term does not apply to this item.
        line = text[text.rfind("\n", start, left) + 1:text.find("\n", right)
                    if "\n" in text[right:] else end]
        grades = {int(n) for n in re.findall(r"([123])\s*학년", line)}
        terms = {int(n) for n in re.findall(r"([12])\s*학기", line)}
        if grades and grades != {section.get("grade")}:
            continue
        if terms and terms != {section.get("semester")}:
            continue
        references.append({"raw": text[left:right], "text": text[left:right],
                           "locator": text_locator(left, right, conversion),
                           "scope": "grade_semester_section"})
    cells = structure["cells"]
    if not references and not structure["claims"].get("score"):
        rubric_cells = {c["start"] for c, _ in structure["claims"].get("rubric", [])}
        levels = [c for c in cells if re.fullmatch(
            r"[ABCDE](?:\s*[·ㆍ,/~-]\s*[ABCDE])*", c["text"])
                  and c["start"] in rubric_cells]
        has_scale = any(re.search(r"척도|등급|성취수준", c["text"]) for c in cells)
        has_points = any(re.search(r"\d+\s*점", c["text"]) for c in cells)
        if len({c["text"] for c in levels}) >= 2 and has_scale and not has_points:
            references = [{"raw": c["raw"], "text": c["text"],
                           "locator": text_locator(c["start"], c["end"], conversion),
                           "scope": "unscored_task_levels"} for c in levels]
    return {"value": bool(references), "evidence": [], "reference_evidence": references,
            "scope_locator": section["locator"], "reason": "학년·학기 구간의 자유학기 근거"
            if references else "해당 학년·학기 구간에 자유학기 근거 없음"}
