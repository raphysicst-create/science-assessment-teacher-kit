"""S6d-3 field rules; only literal cells owned by an item or scoped policy evidence."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

METHOD_RE = re.compile(
    r"(?:실험(?:[·ㆍ\s]?실습)?|실습|실기|탐구|보고서(?:법)?|관찰(?:평가|법)?|"
    r"서[·ㆍ]?논술형?|서술형?|논술형?|서논술형|서술논술형|구술(?:[·ㆍ]?발표)?|"
    r"발표|토의|토론|프로젝트|포트폴리오|면접|자기평가|동료평가|"
    r"교사평가|교사\s*관찰\s*및\s*기록|선택형|단답형|모둠|개별|지필평가|"
    r"체크리스트|수업\s*참여도)(?:\s*평가)?"
)
LEVEL_RE = re.compile(
    r"[ABCDE](?:\s*[·ㆍ,/~-]\s*[ABCDE])*|상|중|하|매우\s*우수|우수|보통|미흡|매우\s*미흡"
    r"|[A-E]\s*\(\s*\d+(?:\.\d+)?\s*\)"
    r"|\d+(?:\.\d+)?\s*점?\s*(?:이상|이하|미만|초과)"
    r"(?:\s*(?:[~∼-]\s*)?\d+(?:\.\d+)?\s*점?\s*(?:이상|이하|미만|초과))?"
    r"|\d+(?:\.\d+)?(?:\s*[~∼-]\s*\d+(?:\.\d+)?)?\s*점?"
)


def method_literal(value):
    value = re.sub(r"[ㆍ･・‧⋅•]", "·", value.strip())
    if re.fullmatch(r"(?:조사|관찰)(?:\s*·\s*(?:조사|관찰))*\s*보고서", value):
        return True
    if METHOD_RE.fullmatch(value):
        return True
    # Conversion can erase every separator between printed method choices.
    # Consume the entire cell with a closed vocabulary; activity prose cannot
    # match just because it contains a method word.
    if re.fullmatch(r"(?:" + METHOD_RE.pattern + r"|기타(?:\s*\([^()]*\))?"
                    r"|[\s,，/、·])+", value):
        return True
    parts = re.split(r"\s*[,，/、·\n]+\s*", value)
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
    return re.sub(r"[\s·ㆍ･‧⋅•・,，'\"‘’“”]+", "", value)


def enrich_claims(structure):
    """Enrich only cells whose task ownership was already established."""
    if __package__:
        from .middle_items import cell_part, label_role
    else:
        from middle_items import cell_part, label_role
    claims, cells = structure["claims"], structure["cells"]
    for cell, header in claims.get("task", []):
        if not header or not re.search(r"수행\s*과제|평가\s*과제", header["text"]):
            continue
        if len(cell["text"]) > 120 or re.search(
            r"(?:^|<br\s*/?>|\n)\s*(?:\d+[.)]|[①-⑳])", cell["raw"], re.I
        ):
            claims["task_text"].append((cell, header))
    rows = {}
    for cell in cells:
        if "table" in cell:
            rows.setdefault((cell["table"], cell["row"]), []).append(cell)
    if structure["layout"] == "form":
        detail_form_claims(claims, cells, rows)
    sub_scores, activities = [], []
    rubric = list(structure.get("plain_rubric", [])) + structure.get("continuation_rubric", [])
    for table in {c["table"] for c in cells if "table" in c}:
        local = [c for c in cells if c.get("table") == table]
        local_rows = {r: values for (t, r), values in rows.items() if t == table}
        rubric_headers = [c for c in local if label_role(c["text"]) == "rubric"]
        # A task-only unscored A–E scale after its method is also a rubric.
        methods = [c["row"] for c in local if label_role(c["text"]) == "method"]
        rubric_headers += [c for c in local if label_role(c["text"]) == "levels"
                           and methods and c["row"] > min(methods)]
        combined = [c for c in local if re.fullmatch(
            r"평가\s*요소\s*및\s*배점", c["text"])]
        rubric_headers += combined
        table_judgments = []
        for header in rubric_headers:
            stop = min((c["row"] for c in local if c["row"] > header["row"]
                        and label_role(c["text"]) in {
                            "method", "standards", "timing", "score_weight", "task_text",
                        }), default=max(local_rows, default=0) + 1)
            judgments, levels = [], set()
            for row, values in local_rows.items():
                if not header["row"] <= row < stop:
                    continue
                in_column = [c for c in values if (
                    header in combined or label_role(header["text"]) == "levels"
                    and c["col"] > header["col"]
                    or header["col"] <= c["col"] < header["col"] + header["colspan"]
                )]
                criteria = [c for c in in_column if judgment(c["text"])
                            and not label_role(c["text"])]
                scale = [c for c in values if c not in criteria
                         and LEVEL_RE.fullmatch(c["text"])]
                if criteria and scale:
                    judgments.extend((c, header) for c in criteria + scale)
                    levels.update(c["text"] for c in scale)
            if len(levels) >= 2:
                rubric.extend(judgments)
                table_judgments.extend(c for c, _ in judgments if judgment(c["text"]))
        elements = [c for c in local if label_role(c["text"]) == "elements"
                    and c not in combined]
        for header in elements:
            header_scores = {}
            point_headers = [c for c in local if c["row"] == header["row"]
                             and label_role(c["text"]) in {"points", "score"}]
            stop = min((c["row"] for c in local if c["row"] > header["row"]
                        and label_role(c["text"]) in {
                            "method", "standards", "task_text", "score_weight", "timing",
                        }), default=max(local_rows, default=0) + 1)
            for cell in local:
                if not (header["row"] < cell["row"] < stop
                        and cell["col"] == header["col"]
                        and cell["colspan"] <= header["colspan"]
                        and cell["text"] and not label_role(cell["text"])
                        and not re.match(r"합\s*계|기본\s*점수|미응시|장기", cell["text"])):
                    continue
                claims["elements"].append((cell, header))
                end = min(stop, cell["row"] + cell["rowspan"])
                scores = [v for r, values in local_rows.items() if cell["row"] <= r < end
                          for v in values for h in point_headers
                          if h["col"] <= v["col"] < h["col"] + h["colspan"]
                          and re.fullmatch(r"\d+(?:\.\d+)?\s*점?", v["text"])]
                # A numbered checklist is one holistic scale, without an
                # allocation to each listed element.
                holistic = len(re.findall(
                    r"(?:^|<br\s*/?>|\n)\s*\d+[.)]", cell["raw"], re.I
                )) > 1
                if scores and not holistic:
                    highest = max(float(re.sub(r"점|\s", "", v["text"])) for v in scores)
                    element_name = re.sub(
                        r"\s*\(\s*\d+(?:\.\d+)?\s*점?\s*\)\s*$", "", cell["text"]
                    ).strip()
                    if table_judgments:
                        previous = header_scores.get(element_name, (0, []))
                        header_scores[element_name] = (
                            max(highest, previous[0]), [*previous[1], cell, *scores]
                        )
                    else:
                        sub_scores.append((element_name, highest, [cell, *scores], header))
                # The first level of each spanned element preserves its literal
                # activity, without generating a description from the title.
                first = [c for c in table_judgments if c["row"] == cell["row"]]
                if re.search(r"하기|작성|제작|탐구|측정|조사", cell["text"]):
                    activities.append((cell, header))
                if first:
                    activities.extend((c, header) for c in first)
            sub_scores.extend((name, score, evidence, header)
                              for name, (score, evidence) in header_scores.items())
        for header in combined:
            questions = [c for c in local if c["row"] == header["row"]
                         and judgment(c["text"]) and c is not header]
            scores = [c for c in local if header["row"] < c["row"]
                      < header["row"] + header["rowspan"]
                      and re.fullmatch(r"\d+(?:\.\d+)?\s*점?", c["text"])]
            if len(questions) == 1 and scores:
                sub_scores.append((questions[0]["text"], max(
                    float(re.sub(r"점|\s", "", c["text"])) for c in scores),
                    [questions[0], *scores], header))
                activities.append((questions[0], header))
                first_row = min((c["row"] for c in table_judgments
                                 if c["row"] > header["row"]), default=None)
                activities.extend((c, header) for c in table_judgments if c["row"] == first_row)
    for table in {c["table"] for c in cells if "table" in c}:
        local = [c for c in cells if c.get("table") == table]
        extra_rubric, extra_scores = detail_scale_claims(local)
        rubric.extend(extra_rubric)
        existing = {name for name, _, _, _ in sub_scores}
        sub_scores.extend(entry for entry in extra_scores if entry[0] not in existing)
        for cell, header in claims.get("elements", []):
            if cell.get("table") != table:
                continue
            first = [c for c, _ in extra_rubric if c["row"] == cell["row"]
                     and judgment(c["text"]) and c["col"] > cell["col"]]
            if first:
                activities.append((min(first, key=lambda c: c["col"]), header))
    claims["rubric"] = list({c["start"]: (c, h) for c, h in rubric}.values())
    # Explicit step lists in element columns describe the task even without scores.
    for cell, header in claims.get("elements", []):
        if re.search(r"(?:^|<br\s*/?>|\n)\s*(?:[▪•①-⑳]|\d+[.)])", cell["raw"], re.I) or (
            re.search(r"하기|작성|제작|측정|설명|분석|설계|조사|발표|관찰", cell["text"])
            and not LEVEL_RE.fullmatch(cell["text"])
        ):
            activities.append((cell, header))
        for match in re.finditer(
            r"([^<>\r\n/]+?)\s*\(\s*(\d+(?:\.\d+)?)\s*점?\s*\)", cell["raw"]
        ):
            part = cell_part(cell, match.start(), match.end())
            sub_scores.append((match[1].strip(), float(match[2]), [part], header))
    claims["task_text"].extend(list({c["start"]: ({**c, "description_only": True}, h)
                                      for c, h in activities}.values()))
    return sub_scores


def detail_scale_claims(cells):
    """Read owned scoring grids, retaining literal embedded level/point spans."""
    if __package__:
        from .middle_items import cell_part, label_role
    else:
        from middle_items import cell_part, label_role
    rubric, allocations = [], []
    headers = [c for c in cells if label_role(c["text"]) == "rubric"]
    headers += [c for c in cells if re.fullmatch(
        r"(?:수행수준\(채점기준\)|채점기준|척도별수행특성\(기대수행\)|"
        r"채점요소척도별수행특성\(기대수행\)척도|채점영역채점기준)(?:배점)?",
        re.sub(r"\s+", "", c["text"]))]
    methods = [c["row"] for c in cells if label_role(c["text"]) == "method"]
    headers += [c for c in cells if label_role(c["text"]) == "levels"
                and methods and c["row"] > min(methods)]
    for header in headers:
        stop = min((c["row"] for c in cells if c["row"] > header["row"]
                    and label_role(c["text"]) in {
                        "method", "standards", "task_text", "timing", "score_weight",
                    }), default=max(c["row"] + c["rowspan"] for c in cells))
        # A row-spanned label owns the whole block to its right. A column label
        # owns only its printed columns until another field starts.
        vertical = header["rowspan"] > 1
        bottom = min(stop, header["row"] + header["rowspan"]) if vertical else stop
        left = header["col"] + header["colspan"] if vertical else header["col"]
        right = max(c["col"] + c["colspan"] for c in cells) if vertical else (
            header["col"] + header["colspan"])
        criteria = [c for c in cells if header["row"] < c["row"] < bottom
                    and left <= c["col"] < right
                    and judgment(c["text"]) and not label_role(c["text"])]
        pairs = []
        for criterion in criteria:
            scale = [c for c in cells if c["row"] == criterion["row"]
                     and c is not criterion and LEVEL_RE.fullmatch(c["text"])]
            scale += [c for c in cells if c["row"] == criterion["row"] + criterion["rowspan"]
                      and criterion["col"] <= c["col"]
                      < criterion["col"] + criterion["colspan"]
                      and LEVEL_RE.fullmatch(c["text"])]
            # PDF conversion can put a printed score or A–E token inside prose.
            for match in re.finditer(r"(?<!\w)[A-E](?!\w)|\d+(?:\.\d+)?\s*점"
                                     r"|(?<=\s)\d+(?:\.\d+)?\s*$", criterion["raw"]):
                scale.append(cell_part(criterion, *match.span()))
            if scale:
                pairs.append((criterion, scale))
        if len({s["text"] for _, values in pairs for s in values}) < 2:
            # An explicitly named checklist is literal scoring criteria even
            # when the form prints questions without a graded scale.
            rubric.extend((c, header) for c in criteria if len(re.findall(
                r"하는가|했는가|하였는가", c["text"])) >= 2)
            continue
        rubric.extend((c, header) for criterion, scale in pairs for c in [criterion, *scale])
        elements = [c for c in cells if label_role(c["text"]) == "elements"
                    and c["row"] == header["row"]]
        for element_header in elements:
            for cell in cells:
                if not (element_header["row"] < cell["row"] < stop
                        and element_header["col"] <= cell["col"]
                        < element_header["col"] + element_header["colspan"]
                        and cell["text"] and not label_role(cell["text"])
                        and not re.match(r"합\s*계|기본|미응시|장기", cell["text"])):
                    continue
                local = [(criterion, scale) for criterion, scale in pairs
                         if cell["row"] <= criterion["row"] < cell["row"] + cell["rowspan"]]
                numeric = [s for _, scale in local for s in scale
                           if re.fullmatch(r"\d+(?:\.\d+)?\s*점?", s["text"])]
                if not numeric or len(re.findall(r"(?:^|<br\s*/?>|\n)\s*\d+[.)]",
                                                 cell["raw"], re.I)) > 1:
                    continue
                highest = max(float(re.sub(r"점|\s", "", s["text"])) for s in numeric)
                name = re.sub(r"\s*\(\s*\d+(?:\.\d+)?\s*점?\s*\)\s*$", "",
                              cell["text"]).strip()
                allocations.append((name, highest, [cell, *numeric], element_header))
    # Transposed allocation rows are explicit element/point pairs. A score-only
    # element table supplies no criterion scale and therefore no rubric.
    for header in [c for c in cells if label_role(c["text"]) == "elements"]:
        names = [c for c in cells if c["row"] == header["row"] and c["col"] > header["col"]
                 and c["text"] and not label_role(c["text"])]
        point_headers = [c for c in cells if c["row"] == header["row"] + header["rowspan"]
                         and c["col"] == header["col"]
                         and label_role(c["text"]) == "points"]
        for name in names:
            scores = [c for c in cells for h in point_headers if c["row"] == h["row"]
                      and c["col"] == name["col"] and c["colspan"] == name["colspan"]
                      and re.fullmatch(r"\d+(?:\.\d+)?\s*점?", c["text"])]
            if len(scores) == 1:
                allocations.append((name["text"], float(re.sub(r"점|\s", "", scores[0]["text"])),
                                    [name, scores[0]], header))
    grouped = {}
    for name, score, proof, header in allocations:
        key = (name, header["start"])
        if key in grouped:
            previous = grouped[key]
            grouped[key] = (name, max(score, previous[1]), previous[2] + proof, header)
        else:
            grouped[key] = (name, score, proof, header)
    return rubric, list(grouped.values())


def plain_detail_claims(structure, section, conversion):
    """Recover explicit flat labels without certifying lost table boundaries."""
    if structure["layout"] != "text_candidate" or not structure["claims"].get("title"):
        return
    if __package__:
        from .middle_items import label_role, visible
    else:
        from middle_items import label_role, visible
    text = conversion["text"]
    title = structure["claims"]["title"][0][0]
    prefix_start = text.rfind("\n", section["locator"]["start"], title["start"])
    prefix_start = text.rfind("\n", section["locator"]["start"], max(0, prefix_start))
    prefix = text[max(section["locator"]["start"], prefix_start):title["start"]]
    if not re.search(r"(?:수행\s*과제|평가\s*과제|평가\s*영역(?:명)?)\s*[:：]?\s*$", prefix):
        return
    end = section["locator"]["end"]
    boundary = re.search(r"(?m)^\s*(?:#{1,6}\s|<table\b|(?:수행\s*과제|평가\s*과제|"
                         r"평가\s*영역(?:명)?)\s*[:：]?|[123]\s*학년)", text[title["end"]:end])
    if boundary:
        end = title["end"] + boundary.start()
    lines = list(re.finditer(r"(?m)^[^\S\n]*([^\r\n]+)", text[title["end"]:end]))
    active, header = None, None
    rubric = []
    for line in lines:
        left = title["end"] + line.start(1)
        raw = line[1].strip()
        if not raw:
            continue
        label = re.match(r"(.+?)\s*[:：]\s*(.+)$", raw)
        role = label_role(label[1] if label else raw)
        if role:
            active = role
            label_raw = label[1] if label else raw
            header = {"raw": label_raw, "text": visible(label_raw),
                      "start": left, "end": left + len(label_raw)}
            structure["cells"].append(header)
            if not label:
                continue
            left += label.start(2)
            raw = label[2]
        if active not in {"task_text", "method", "standards", "elements", "rubric"}:
            continue
        cell = {"raw": raw, "text": visible(raw), "start": left, "end": left + len(raw)}
        structure["cells"].append(cell)
        if active == "rubric":
            match = re.fullmatch(r"(상|중|하|[A-E]|매우\s*우수|우수|보통|미흡|매우\s*미흡)"
                                 r"\s+(.+?)(?:\s+(\d+(?:\.\d+)?\s*점))?", raw)
            if match and judgment(match[2]):
                rubric.append((cell, header, match[1]))
        elif active != "method" or method_literal(raw):
            structure["claims"][active].append((cell, header))
    if len({level for _, _, level in rubric}) >= 2:
        structure["plain_rubric"] = [(c, h) for c, h, _ in rubric]


def judgment(text):
    return bool(not LEVEL_RE.fullmatch(text) and re.search(
        r"함|됨|있|없|임$|한다|이다|하였다|미흡|충실|우수|필요|부족|정확|오류|이상|미만|"
        r"못|모두|일부|완료|충족|하는가|했는가|하였는가|경우|만족|높다|낮다", text))


def detail_form_claims(claims, cells, rows):
    """Read labeled form windows, including method subrows and displaced units."""
    if __package__:
        from .middle_items import METHOD_BOX_RE, cell_part, label_role
    else:
        from middle_items import METHOD_BOX_RE, cell_part, label_role
    method_claims = []
    excluded_method_cells = set()
    eligible_method_cells = set()
    for header in cells:
        role = label_role(header["text"])
        if role in {"method", "evaluator", "organization"}:
            for (table, row), values in rows.items():
                if table != header.get("table") or not (
                    header["row"] <= row < header["row"] + header["rowspan"]
                ):
                    continue
                # A second label in this row terminates the field's window.
                boundary = min((c["col"] for c in cells
                                if c.get("table") == table
                                and c["row"] <= row < c["row"] + c["rowspan"]
                                and c["col"] > header["col"]
                                and label_role(c["text"]) not in {None, "evaluator", "organization"}
                                and c is not header), default=1000)
                descriptor = " ".join(c["text"] for c in values
                                      if c["col"] > header["col"] and not METHOD_BOX_RE.search(
                                          c["raw"]) and len(c["text"]) < 12)
                if re.search(r"점수\s*부여|원점수|평균점|환산점", descriptor):
                    excluded_method_cells.update(c["start"] for c in values)
                    continue
                kind = ("evaluator" if role == "evaluator" or "주체" in descriptor else
                        "organization" if role == "organization" or "방식" in descriptor
                        else "method")
                for cell in values:
                    if not header["col"] < cell["col"] < boundary or label_role(cell["text"]):
                        continue
                    eligible_method_cells.add(cell["start"])
                    if METHOD_BOX_RE.search(cell["raw"]) or method_literal(cell["text"]):
                        method_claims.append(({**cell, "method_kind": kind}, header))
                    elif role == "method" and len(cell["text"]) > 25 and re.search(
                        r"측정|작성|설계|설명|발표|조사|분석|탐구|실험|서술", cell["text"]
                    ):
                        claims["task_text"].append(({**cell, "description_only": True}, header))
                    elif cell["text"] in {"-", "—", "없음", "미기재", "해당없음", "해당 없음"}:
                        method_claims.append((cell, header))
        if role == "timing":
            values = rows.get((header.get("table"), header["row"]), [])
            next_cells = [c for c in values if c["col"] > header["col"]]
            if next_cells:
                cell = min(next_cells, key=lambda c: c["col"])
                # Some converted forms put the time inside a neighboring unit label.
                if re.search(r"만점|반영\s*비율", cell["text"]):
                    claims["timing"] = [(c, h) for c, h in claims.get("timing", [])
                                        if h is None or h["start"] != header["start"]]
                    for match in re.finditer(r"\d{1,2}월(?:\s*\d주)?", cell["raw"]):
                        claims["timing"].append((cell_part(cell, *match.span()), header))
                    amounts = [c for c in next_cells if c["col"] > cell["col"]]
                    if amounts and re.fullmatch(r"\s*\d+점?\s*(?:<br\s*/?>)?\s*\(\d+%\)\s*",
                                               amounts[0]["raw"], re.I):
                        claims["score_weight"].append((amounts[0], cell))
    # Keep unreadable literal cells so they remain unconfirmed, not absent.
    method_claims.extend((c, h) for c, h in claims.get("method", [])
                         if c["text"] and len(c["text"]) <= 25
                         and c["start"] not in excluded_method_cells
                         and c["start"] in eligible_method_cells
                         and not any(c["start"] == v["start"] for v, _ in method_claims)
                         and not re.fullmatch(r"유형|주체|방식|점수부여방법", c["text"]))
    claims["method"] = list({c["start"]: (c, h) for c, h in method_claims}.values())


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


def mark_source_absence(fields, structure, conversion):
    """Positive empty-cell or owned rubric evidence is required for absence."""
    if __package__:
        from .middle_items import evidence, label_role
    else:
        from middle_items import evidence, label_role
    empty = {"", "-", "—", "없음", "미기재", "해당없음", "해당 없음"}
    for name in ("score", "weight", "points", "timing"):
        field = fields[name]
        observations = field["evidence"]
        if (field["value"] in ("", [], None) and field.get("status") != "conflict"
                and observations and all(o["text"].strip() in empty for o in observations)):
            field.update(source_absent=True, absence_basis="explicit_empty_cell",
                         absence_evidence=observations)
    if structure["layout"] != "form":
        return
    rubric = fields["rubric"]["evidence"]
    elements = fields["elements"]["evidence"]
    if not rubric:
        return
    cells = structure["cells"]
    # Only the task's post-method rubric can prove a qualitative scale. Its
    # curriculum achievement levels preceding the method cannot vote here.
    scale_cells = []
    for table in {c.get("table") for c in cells}:
        local = [c for c in cells if c.get("table") == table and "row" in c]
        headers = [c for c in local if label_role(c["text"]) == "elements"]
        if not headers:
            methods = [c["row"] for c in local if label_role(c["text"]) == "method"]
            headers = [c for c in local if methods and c["row"] > min(methods)
                       and label_role(c["text"]) in {"levels", "rubric"}]
        if headers:
            start = min(c["row"] for c in headers)
            scale_cells.extend(c for c in local if c["row"] > start
                               and LEVEL_RE.fullmatch(c["text"]))
    qualitative = [c for c in scale_cells if not re.search(r"\d", c["text"])]
    points_headers = any(label_role(c["text"]) in {"score", "points", "score_weight"}
                         for c in cells)
    level_only = (len({c["text"] for c in qualitative}) >= 2
                  and len(qualitative) == len(scale_cells) and not points_headers)
    holistic = any(len(re.findall(
        r"(?:^|<br\s*/?>|\n)\s*\d+[.)]", o["raw"], re.I
    )) > 1 for o in elements)
    proof = [evidence(c, conversion) for c in qualitative] if level_only else []
    for name in (("score", "weight", "sub_scores") if level_only else ("sub_scores",)):
        field = fields[name]
        if (field["value"] in ("", [], None) and field.get("status") != "conflict"
                and (level_only or holistic)):
            field.update(source_absent=True, absence_basis=(
                "qualitative_task_scale" if level_only else "holistic_checklist_scale"
            ), absence_evidence=proof or elements + rubric)


def free_semester_field(structure, section, conversion):
    if __package__:
        from .middle_segments import text_locator
    else:
        from middle_segments import text_locator
    text = conversion["text"]
    start, end = section["locator"]["start"], section["locator"]["end"]
    references = []
    # A literal grade-wide declaration before the subject section applies to
    # that grade. A term-qualified declaration still needs the matching term.
    declaration = re.compile(
        r"([123])\s*학년\s*(?:([12])\s*학기\s*)?(?:은|는)\s*"
        r"자유\s*학(?:기|년)(?:제)?(?:를?\s*(?:운영|실시)|이(?:다|므로|어서)?|로|임|\b)"
    )
    for match in declaration.finditer(text, 0, start):
        if int(match[1]) != section.get("grade") or (
            match[2] and int(match[2]) != section.get("semester")
        ):
            continue
        tail = text[match.end():text.find("\n", match.end())
                    if "\n" in text[match.end():] else start]
        if re.search(r"아니|않|미실시|미운영", tail):
            continue
        references.append({"raw": match.group(), "text": match.group(),
                           "locator": text_locator(*match.span(), conversion),
                           "scope": "document_grade_policy", "grade": int(match[1]),
                           "semester": int(match[2]) if match[2] else None})
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
        has_points = any(re.search(r"\d+\s*점", c["text"]) or (
            c["start"] in rubric_cells and re.fullmatch(r"\d+(?:\.\d+)?", c["text"])
        ) for c in cells)
        if len({c["text"] for c in levels}) >= 2 and has_scale and not has_points:
            references = [{"raw": c["raw"], "text": c["text"],
                           "locator": text_locator(c["start"], c["end"], conversion),
                           "scope": "unscored_task_levels"} for c in levels]
    return {"value": bool(references), "evidence": [], "reference_evidence": references,
            "scope_locator": section["locator"], "reason": "학년·학기 구간의 자유학기 근거"
            if references else "해당 학년·학기 구간에 자유학기 근거 없음"}
