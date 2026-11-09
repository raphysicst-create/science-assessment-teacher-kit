"""독립 원문 확인 Markdown과 개발 추출 항목·방법을 대조해 JSON/MD 지표를 쓴다.

Run: .venv/Scripts/python.exe scripts/dev_extraction_check.py --result review.md
     --sample A=sample.json --out-prefix docs/dev/check [--suffix .prev-s18]
Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_dev_extraction_check.py
        .venv/Scripts/python.exe -m ruff check scripts/dev_extraction_check.py
        services/math-assessment-api/tests/test_dev_extraction_check.py
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEAD = re.compile(r"^###\s+([A-Z]+-S\d+)\s+(.+?)\s+중([12])\s+([12])학기\s*$")
COLUMNS = ("제목", "만점", "비율", "평가 방법", "평가 주체·형태", "근거(줄)")
OUTCOMES = ("정답", "오값-여러값", "오값-한값", "누락", "허위")
UNREADABLE = re.compile(r"^(?:(?:상태|개수)\s*:\s*)?판독\s*불가(?:능)?(?:\s|$|[.:·(])")


def checked_path(path):
    path = Path(path)
    resolved = path.resolve()
    if "gold" in str(path).casefold() or "gold" in str(resolved).casefold():
        raise ValueError(f"gold 경로 거부: {path}")
    return resolved


def read_json(path):
    return json.loads(checked_path(path).read_text(encoding="utf-8-sig"))


def normalize(text):
    # Same pure rule as gold_diff.normalize, without importing gold-label tooling.
    text = re.sub(r"<br\s*/?\s*>", "", text, flags=re.IGNORECASE)
    return "".join(c for c in text.lower()
                   if not c.isspace() and not unicodedata.category(c).startswith("P"))


def parse_section(lines):
    items, in_table, saw_table, count = [], False, False, None
    unreadable = any(UNREADABLE.match(line.strip().replace("**", "")) for line in lines)
    for line in lines:
        line = line.strip()
        found = re.fullmatch(r"개수\s*:\s*(\d+)\s*(?:건)?", line.replace("**", ""))
        if found:
            count = int(found[1])
        if line == "0건":
            count = 0
        if not line.startswith("|"):
            in_table = False
            continue
        values = [v.strip().replace(r"\|", "|") for v in re.split(r"(?<!\\)\|", line)[1:-1]]
        if tuple(values) == COLUMNS:
            in_table = saw_table = True
        elif in_table and not all(re.fullmatch(r":?-+:?", v) for v in values):
            if len(values) != len(COLUMNS) or not values[0]:
                raise ValueError(f"표 행 형식 오류: {line}")
            items.append(dict(zip(COLUMNS, values, strict=True)))
    if not unreadable and (count is None and not saw_table):
        raise ValueError("항목 표·0건·판독 불가 표시가 없는 칸")
    if not unreadable and count is not None and count != len(items):
        raise ValueError(f"개수 불일치: 선언 {count}, 표 {len(items)}")
    return {"astra": items, "unreadable": unreadable}


def parse_result(path):
    sections, cell, lines, coordinate = {}, None, [], None
    text = checked_path(path).read_text(encoding="utf-8-sig")
    for line in [*text.splitlines(), "### END"]:
        if line.startswith("### "):
            if cell:
                sections[cell] = {**parse_section(lines), "coordinate": coordinate}
            cell, lines = None, []
            if match := HEAD.fullmatch(line):
                cell, school, grade, semester = match.groups()
                if cell in sections:
                    raise ValueError(f"중복 결과 칸: {cell}")
                coordinate = (school, int(grade), int(semester))
            elif re.match(r"###\s+[A-Z]+-S\d+", line):
                raise ValueError(f"칸 머리 형식 오류: {line}")
        elif cell:
            lines.append(line)
    return sections


def load_cells(samples, suffix):
    cells, reports, prefixes = {}, {}, set()
    for specification in samples:
        prefix, separator, path = specification.partition("=")
        if not separator or not re.fullmatch(r"[A-Z]+", prefix) or prefix in prefixes:
            raise ValueError(f"--sample은 중복 없는 A=경로 형식이어야 함: {specification}")
        prefixes.add(prefix)
        for source in read_json(path)["source_review"]:
            name = source["round"] + suffix
            if "/" in name or "\\" in name or name in (".", ".."):
                raise ValueError(f"잘못된 round/suffix: {name}")
            ai = checked_path(ROOT / f"data/derived/items_ai/{name}.json")
            fallback = checked_path(ROOT / f"data/derived/items/{name}.json")
            if name not in reports:
                reports[name] = read_json(ai if ai.is_file() else fallback)["items"]
            cell = f"{prefix}-{source['cell_id']}"
            if cell in cells:
                raise ValueError(f"중복 표본 칸: {cell}")
            coordinate = tuple(source[key] for key in ("school", "grade", "semester"))
            items = [item for item in reports[name]
                     if tuple(item.get(k) for k in ("school", "grade", "semester")) == coordinate
                     and item.get("candidate_role") == "performance"
                     and item.get("extraction_status") in ("bounded", "ai_verified")]
            if len({i["item_id"] for i in items}) != len(items):
                raise ValueError(f"중복 pipeline item_id: {cell}")
            cells[cell] = {"source": source, "pipeline": items, "coordinate": coordinate}
    return cells


def field_value(item, name):
    value = item.get("fields", {}).get(name, item.get(name, ""))
    return value.get("value") if isinstance(value, dict) else value


def title(item):
    return field_value(item, "title") or ""


def candidate_keys(text):
    keys = {normalize(text)}
    # Reviewer may append a summary-table title in parentheses.
    match = re.search(r"[（(]([^()（）]+)[)）]\s*$", text)
    if match:
        keys.update((normalize(text[:match.start()]), normalize(match[1])))
    return keys - {""}


def key_score(astra_keys, pipeline_keys):
    if astra_keys & pipeline_keys:
        return 0
    if any(min(len(a), len(p)) >= 4 and (a in p or p in a)
           for a in astra_keys for p in pipeline_keys):
        return 1
    return None


def pair_items(astra, pipeline, overrides):
    pairs, used_a, used_p, accepted_a, accepted_p = [], set(), set(), [], []
    for override in overrides:
        verdict = override["verdict"]
        a = [i for i, row in enumerate(astra)
             if normalize(row["제목"]) == normalize(override.get("astra_title", ""))]
        p = [i for i, row in enumerate(pipeline)
             if row["item_id"] == override.get("pipeline_item_id")]
        if verdict not in ("same", "pipeline_extra_ok", "astra_extra_ok"):
            raise ValueError(f"알 수 없는 override verdict: {verdict}")
        if verdict != "pipeline_extra_ok" and (len(a) != 1 or a[0] in used_a):
            raise ValueError(f"override astra 대상 없음·중복: {override}")
        if verdict != "astra_extra_ok" and (len(p) != 1 or p[0] in used_p):
            raise ValueError(f"override pipeline 대상 없음·중복: {override}")
        if verdict != "pipeline_extra_ok":
            used_a.add(a[0])
        if verdict != "astra_extra_ok":
            used_p.add(p[0])
        if verdict == "same":
            pairs.append((a[0], p[0], "override"))
        elif verdict == "pipeline_extra_ok":
            accepted_p.append(p[0])
        else:
            accepted_a.append(a[0])
    candidates = []
    for a, row in enumerate(astra):
        keys = candidate_keys(row["제목"])
        for p, item in enumerate(pipeline):
            score = key_score(keys, {normalize(title(item))} - {""})
            if score is None:
                values = [field_value(item, k) or "" for k in ("assessment_area", "task_text")]
                # task_text는 목록일 수 있다(한 칸의 여러 값). 원소마다 후보 키로 쓴다.
                flat = [v for value in values
                        for v in (value if isinstance(value, list) else [value])]
                alternate = {normalize(str(v)) for v in flat} - {""}
                alternate_score = key_score(keys, alternate)
                score = None if alternate_score is None else alternate_score + 2
            if score is not None:
                candidates.append((score, a, p))
    for score, a, p in sorted(candidates):
        if a not in used_a and p not in used_p:
            reason = ("exact", "contains", "area_task_exact", "area_task_contains")[score]
            pairs.append((a, p, reason))
            used_a.add(a)
            used_p.add(p)
    return pairs, sorted(set(range(len(astra))) - used_a), sorted(
        set(range(len(pipeline))) - used_p), accepted_a, accepted_p


def method_values(value):
    values = value if isinstance(value, list) else [value]
    return {key for text in values for part in re.split(r"[;,/]", text or "")
            if (key := normalize(part))}


def method_outcome(astra, item):
    expected = method_values(astra) - {"없음"}
    actual = method_values(field_value(item, "method"))
    uncertain = expected == {normalize("확실하지 않음")}
    state = item.get("fields", {}).get("method", {}).get("state")
    if uncertain:
        if not actual or state == "unknown":
            return "정답"
        return "오값-여러값" if len(actual) >= 2 else "오값-한값"
    if expected == actual:
        return "정답"
    if not uncertain and expected and not actual:
        return "누락"
    if not expected and actual:
        return "허위"
    return "오값-여러값" if len(actual) >= 2 else "오값-한값"


def compare(cells, sections, overrides):
    if cells.keys() != sections.keys():
        raise ValueError(f"결과 칸 불일치: 누락 {cells.keys() - sections.keys()}, "
                         f"추가 {sections.keys() - cells.keys()}")
    if any(row["cell"] not in cells or sections[row["cell"]]["unreadable"] for row in overrides):
        raise ValueError("override는 판독 가능한 표본 칸에만 적용할 수 있음")
    result = {"cells": {}, "items": {"precision": {"num": 0, "den": 0},
                                    "recall": {"num": 0, "den": 0}},
              "method": {"accuracy": {"num": 0, "den": 0},
                         "outcomes": dict.fromkeys(OUTCOMES, 0)},
              "unreadable_cells": [], "unmatched_pipeline": [],
              "unmatched_astra": [], "method_wrong": []}
    for cell, source in cells.items():
        section = sections[cell]
        if source["coordinate"] != section["coordinate"]:
            raise ValueError(f"학교·학년·학기 불일치: {cell}")
        astra, pipeline = section["astra"], source["pipeline"]
        output = {**source, **section, "pairs": [], "unmatched_astra": [],
                  "unmatched_pipeline": [], "accepted_astra": [], "accepted_pipeline": []}
        result["cells"][cell] = output
        if section["unreadable"]:
            result["unreadable_cells"].append(cell)
            continue
        pairs, only_a, only_p, accepted_a, accepted_p = pair_items(
            astra, pipeline, [row for row in overrides if row["cell"] == cell])
        output["accepted_astra"] = [astra[i] for i in accepted_a]
        output["accepted_pipeline"] = [pipeline[i]["item_id"] for i in accepted_p]
        for key, num, den in (("precision", len(pairs) + len(accepted_p), len(pipeline)),
                              ("recall", len(pairs) + len(accepted_a), len(astra))):
            result["items"][key]["num"] += num
            result["items"][key]["den"] += den
        for a, p, reason in pairs:
            outcome = method_outcome(astra[a]["평가 방법"], pipeline[p])
            output["pairs"].append({"astra_index": a, "pipeline_item_id": pipeline[p]["item_id"],
                                    "reason": reason, "method_outcome": outcome})
            result["method"]["accuracy"]["den"] += 1
            result["method"]["accuracy"]["num"] += int(outcome == "정답")
            result["method"]["outcomes"][outcome] += 1
            if outcome != "정답":
                result["method_wrong"].append({"cell": cell, "title": astra[a]["제목"],
                    "astra": astra[a]["평가 방법"], "pipeline": field_value(pipeline[p], "method"),
                    "outcome": outcome})
        for index in only_a:
            row = {"cell": cell, "title": astra[index]["제목"], **astra[index]}
            output["unmatched_astra"].append(row)
            result["unmatched_astra"].append(row)
        for index in only_p:
            item = pipeline[index]
            row = {"cell": cell, "item_id": item["item_id"], "title": title(item),
                   "layout": item.get("layout"), "layout_position": item.get("layout_position")}
            output["unmatched_pipeline"].append(row)
            result["unmatched_pipeline"].append(row)
    return result


def markdown(result):
    lines = ["# 독립 확인 대조", "", "| 지표 | 분수 | JSON 키 |", "|---|---|---|"]
    for group, name in (("items", "precision"), ("items", "recall"), ("method", "accuracy")):
        metric = result[group][name]
        lines.append(f"| {name} | {metric['num']}/{metric['den']} | "
                     f"`{group}.{name}.num` / `{group}.{name}.den` |")
    lines += ["", "| 방법 결과 | 건수 | JSON 키 |", "|---|---|---|"]
    for outcome, count in result["method"]["outcomes"].items():
        lines.append(f"| {outcome} | {count} | `method.outcomes.{outcome}` |")
    lines += ["", f"판독 불가 {len(result['unreadable_cells'])}칸 (`unreadable_cells`)", ""]
    for key in ("unreadable_cells", "unmatched_pipeline", "unmatched_astra", "method_wrong"):
        lines += [f"## {key}", ""]
        lines += ["- " + json.dumps(row, ensure_ascii=False) for row in result[key]] or ["- 없음"]
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--sample", required=True, action="append")
    parser.add_argument("--suffix", default="")
    parser.add_argument("--overrides", type=Path)
    parser.add_argument("--out-prefix", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        outputs = [checked_path(str(args.out_prefix) + ext) for ext in (".json", ".md")]
        sections = parse_result(args.result)
        overrides = read_json(args.overrides) if args.overrides else []
        result = compare(load_cells(args.sample, args.suffix), sections, overrides)
        for path, content in zip(outputs, (json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                           markdown(result)), strict=True):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
