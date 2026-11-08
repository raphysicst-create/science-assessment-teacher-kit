"""Compare gold label content (v2), or reproduce the v1 comparison with --strict."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from uuid import uuid4

from gold_validate import (
    DEFAULT_PACK,
    line_range,
    load_index,
    pack_lines,
    read_labels,
    validate_file,
    walk,
)

FIELDS = (
    "title", "task_text", "task_no", "period", "method", "standards",
    "max_score", "sub_scores", "ratio", "rubric", "free_semester",
)
CONTENT_FIELDS = ("title", "title_role", *FIELDS[1:])
COLUMNS = (
    "불일치ID", "학교", "학년", "학기", "종류", "필드", "A항목키", "B항목키",
    "A값", "B값", "원문 위치", "원문 발췌", "A상태", "B상태", "A값요약", "B값요약",
)


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def merged_ranges(locations: list[dict]) -> dict[str, list[tuple[int, int]]]:
    groups = defaultdict(list)
    for location in locations:
        groups[location["doc_id"]].append(line_range(location))
    result = {}
    for doc_id, ranges in groups.items():
        merged = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        result[doc_id] = merged
    return result


def overlap(a: list[dict], b: list[dict]) -> int:
    left, right = merged_ranges(a), merged_ranges(b)
    return sum(
        max(0, min(end_a, end_b) - max(start_a, start_b) + 1)
        for doc_id in left.keys() & right.keys()
        for start_a, end_a in left[doc_id]
        for start_b, end_b in right[doc_id]
    )


def normalize(text: str) -> str:
    """Remove spacing, HTML breaks and Unicode punctuation; retain the words."""
    text = re.sub(r"<br\s*/?\s*>", "", text, flags=re.IGNORECASE)
    return "".join(char for char in text.lower()
                   if not char.isspace() and not unicodedata.category(char).startswith("P"))


def titles(item: dict) -> set[str]:
    return {text for name in ("title", "task_text")
            for value in item[name]["values"] if (text := normalize(value["raw"]))}


def match_items(
    a: list[dict], b: list[dict], *, strict: bool = False,
) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Pair mutual unique maxima, using titles to break overlap ties in v2.

    A zero-overlap title match must be unique in both directions. No input order
    or item key breaks a remaining tie, and empty titles never provide evidence.
    """
    scores = {}
    a_titles, b_titles = [titles(row) for row in a], [titles(row) for row in b]
    for i, left in enumerate(a):
        for j, right in enumerate(b):
            group = ("school_id", "grade", "semester")
            if all(left[key] == right[key] for key in group):
                score = overlap(left["occurrences"], right["occurrences"])
                same_title = not strict and bool(a_titles[i] & b_titles[j])
                if score or same_title:
                    scores[i, j] = (score, same_title)

    def best(reverse: bool) -> dict[int, int]:
        groups = defaultdict(list)
        for (i, j), score in scores.items():
            groups[j if reverse else i].append((score, i if reverse else j))
        winners = {}
        for key, choices in groups.items():
            maximum = max(score for score, _ in choices)
            candidates = [candidate for score, candidate in choices if score == maximum]
            if len(candidates) == 1:
                winners[key] = candidates[0]
        return winners

    pairs = []
    while scores:
        forward, backward = best(False), best(True)
        confirmed = [(i, j) for i, j in forward.items() if backward.get(j) == i]
        pairs.extend(confirmed)
        if strict or not confirmed:
            break
        # Resolve only proven pairs, then reconsider remaining candidates. A long
        # duplicated PDF range on an already paired item must not block a peer.
        used_a, used_b = {i for i, _ in confirmed}, {j for _, j in confirmed}
        scores = {(i, j): score for (i, j), score in scores.items()
                  if i not in used_a and j not in used_b}
    pairs.sort()
    used_a, used_b = {i for i, _ in pairs}, {j for _, j in pairs}
    return pairs, sorted(set(range(len(a))) - used_a), sorted(set(range(len(b))) - used_b)


def canonical(value):
    """Preserve the v1 comparison exactly for --strict and historical metrics.

    Arrays are order independent so conflicting alternatives can be written in
    either order. Numbers retain JSON numeric equality (20 equals 20.0).
    """
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value).strip()
    if isinstance(value, list):
        return sorted((canonical(child) for child in value), key=json_text)
    if isinstance(value, dict):
        return {
            key: canonical(child) for key, child in value.items()
            if key not in {"loc", "note", "link_basis"}
        }
    return value


def numeric_values(value: dict) -> set[float]:
    if "norm" in value:
        return {value["norm"]}
    # Units and parentheses do not affect a score. Preserve decimal/sign values.
    return {float(number) for number in re.findall(
        r"[-+]?\d+(?:\.\d+)?", value["raw"].replace(",", ""),
    )}


def content(field: str, value):
    """Return only the content explicitly compared by v2, as deduplicated sets."""
    if field in {"free_semester", "title_role"}:
        return value
    if field == "standards":
        return (
            frozenset(group["status"] for group in value),
            frozenset(code for group in value for code in group["codes"]),
            frozenset(text for group in value
                      if (text := normalize(group.get("area_name_raw", "")))),
        )
    status = value["status"]
    if field in {"title", "task_text", "task_no", "period"}:
        return status, frozenset(normalize(v["raw"]) for v in value["values"])
    if field in {"max_score", "ratio"}:
        return status, frozenset(n for v in value["values"] for n in numeric_values(v))
    if field == "sub_scores":
        return status, frozenset((normalize(v.get("name", "")), n)
                                 for v in value["values"] for n in numeric_values(v))
    if field == "method":
        return (
            status,
            frozenset((normalize(option["text"]), option["state"])
                      for option in value.get("options", [])),
            normalize(value.get("plain_text", "")), normalize(value.get("other_text", "")),
        )
    if field == "rubric":
        return status
    raise ValueError(f"Unknown content field: {field}")


def field_equal(field: str, left, right) -> bool:
    if content(field, left) != content(field, right):
        return False
    if field == "rubric" and left["status"] == right["status"] == "present":
        return overlap(locations(left), locations(right)) > 0
    return True


def sections_equal(a: dict, b: dict, pack: Path | None = None) -> bool:
    left, right = a["science_sections"], b["science_sections"]
    if pack is not None:
        lines = pack_lines(pack / f"{a['doc_id']}.md")
        boundary = next((n for n, line in enumerate(lines, 1)
                         if line.strip().lower() == "## pymupdf"), len(lines) + 1)

        def kordoc(sections):
            # Clip crossing ranges, discard ranges wholly in the duplicated text.
            return [{**s, "line_end": min(s["line_end"], boundary - 1)} for s in sections
                    if s["line_start"] < boundary]

        left, right = kordoc(left), kordoc(right)
    if {(s["grade"], s["semester"]) for s in left} != {
        (s["grade"], s["semester"]) for s in right
    }:
        return False
    for source, target in ((left, right), (right, left)):
        for section in source:
            if not any(
                section["grade"] == other["grade"]
                and section["semester"] == other["semester"]
                and section["line_start"] <= other["line_end"]
                and other["line_start"] <= section["line_end"]
                for other in target
            ):
                return False
    return True


def locations(value) -> list[dict]:
    return [
        node for _, node in walk(value)
        if "doc_id" in node and ("line" in node or "line_start" in node)
    ]


def source_excerpt(locs: list[dict], pack: Path) -> tuple[str, str]:
    ranges = merged_ranges(locs)
    names, excerpts = [], []
    for doc_id in sorted(ranges):
        lines = pack_lines(pack / f"{doc_id}.md")
        for start, end in ranges[doc_id]:
            names.append(f"{doc_id}:{start}-{end}")
            # Bound slicing too, even when the labeled range spans a whole document.
            snippet = "\n".join(
                f"{n + 1} | {lines[n]}" for n in range(max(0, start - 3), min(len(lines), end + 2))
            )
            excerpts.append(f"[{doc_id}]\n{snippet}")
    return " / ".join(names), "\n\n".join(excerpts)[:400]


def short(text: str, limit: int = 150) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def item_title(item: dict | None) -> str:
    if item is None:
        return "없음"
    for name in ("title", "task_text"):
        values = list(dict.fromkeys(v["raw"] for v in item.get(name, {}).get("values", [])))
        if values:
            return short(" | ".join(values))
    return item.get("item_key", item.get("doc_id", "제목 없음"))


def value_status(value) -> str:
    if value is None:
        return "missing"
    if isinstance(value, dict):
        return value.get("status", "present")
    if isinstance(value, list) and value and all("status" in v for v in value):
        return " | ".join(sorted({v["status"] for v in value}))
    return "present"


def value_summary(field: str, value, status: str) -> str:
    if value is None:
        text = "없음"
    elif field == "항목 존재":
        text = item_title(value)
    elif field == "문서 존재":
        text = value["doc_id"]
    elif field == "science_sections":
        text = " | ".join(f"{s['grade']}학년 {s['semester']}학기 "
                          f"L{s['line_start']}–{s['line_end']}" for s in value)
    elif field == "standards":
        text = " | ".join(sorted({code for group in value for code in group["codes"]}
                                 | {g["area_name_raw"] for g in value if g.get("area_name_raw")}))
    elif isinstance(value, dict):
        if field == "method":
            parts = [f"{o['text']} ({o['state']})" for o in value.get("options", [])]
            parts += [value.get("plain_text", ""), value.get("other_text", "")]
        elif field == "rubric":
            parts = [f"{v['doc_id']}:L{line_range(v)[0]}–{line_range(v)[1]}"
                     for v in locations(value)]
        else:
            parts = [f"{v['name']}: {v.get('norm', v['raw'])}" if v.get("name")
                     else str(v.get("norm", v["raw"])) for v in value.get("values", [])]
        text = " | ".join(dict.fromkeys(p for p in parts if p))
    elif isinstance(value, bool):
        text = "자유학기" if value else "일반학기"
    else:
        text = str(value)
    return short(f"{status}: {text}" if text else status)


def compare_labels(
    a: list[dict], b: list[dict], pack: Path, *, strict: bool = False,
) -> tuple[list[dict], dict]:
    index = load_index(pack)
    differences = []
    fields = FIELDS if strict else CONTENT_FIELDS
    totals = {field: {"matched": 0, "total": 0}
              for field in (*fields, "document.edition", "document.science_sections")}

    def count(field: str, equal: bool) -> None:
        totals[field]["total"] += 1
        totals[field]["matched"] += int(equal)

    def add(kind, field, left, right, a_value, b_value, locs, statuses=None):
        item = left or right
        school_id = item["school_id"]
        school = next((row["school_name"] for row in index.values()
                       if row["school_id"] == school_id), school_id)
        position, excerpt = source_excerpt(locs, pack)
        a_status, b_status = statuses or (value_status(a_value), value_status(b_value))
        row = dict(zip(COLUMNS, (
            f"D{len(differences) + 1:04d}", school, item.get("grade", ""),
            item.get("semester", ""), kind, field,
            (left or {}).get("item_key", ""), (right or {}).get("item_key", ""),
            json_text(a_value), json_text(b_value), position, excerpt,
            a_status, b_status, value_summary(field, a_value, a_status),
            value_summary(field, b_value, b_status),
        ), strict=True))
        # Report context only; keep the original JSON value columns intact.
        row.update(_a_title=item_title(left), _b_title=item_title(right),
                   _doc_id=item.get("doc_id", ""))
        differences.append(row)

    items_a = sorted((r for r in a if r["type"] == "item"), key=lambda r: r["item_key"])
    items_b = sorted((r for r in b if r["type"] == "item"), key=lambda r: r["item_key"])
    pairs, only_a, only_b = match_items(items_a, items_b, strict=strict)
    for i in only_a:
        item = items_a[i]
        add("항목존재", "항목 존재", item, None, item, None, item["occurrences"])
    for j in only_b:
        item = items_b[j]
        add("항목존재", "항목 존재", None, item, None, item, item["occurrences"])
    for i, j in pairs:
        left, right = items_a[i], items_b[j]
        for field in fields:
            a_value, b_value = (
                (left["title"].get("role"), right["title"].get("role"))
                if field == "title_role" else (left[field], right[field])
            )
            equal = (canonical(a_value) == canonical(b_value) if strict
                     else field_equal(field, a_value, b_value))
            count(field, equal)
            if not equal:
                locs = locations([a_value, b_value])
                statuses = ((left["title"]["status"], right["title"]["status"])
                            if field == "title_role" else None)
                add("필드", field, left, right, a_value, b_value,
                    locs or left["occurrences"] + right["occurrences"], statuses)
    docs_a = {row["doc_id"]: row for row in a if row["type"] == "document"}
    docs_b = {row["doc_id"]: row for row in b if row["type"] == "document"}
    for doc_id in sorted(docs_a.keys() | docs_b.keys()):
        left, right = docs_a.get(doc_id), docs_b.get(doc_id)
        if left is None or right is None:
            add("문서", "문서 존재", left, right, left, right, [{"doc_id": doc_id, "line": 1}])
            continue
        for field, equal in (
            ("edition", left["edition"] == right["edition"]),
            ("science_sections", sections_equal(left, right, None if strict else pack)),
        ):
            count(f"document.{field}", equal)
            if not equal:
                locs = [{"doc_id": doc_id, **section}
                        for section in left["science_sections"] + right["science_sections"]]
                add("문서", field, left, right, left[field], right[field],
                    locs or [{"doc_id": doc_id, "line": 1}])
    denominator = len(items_a) + len(items_b)
    summary = {
        "item_pairing": {
            "a_count": len(items_a), "b_count": len(items_b), "paired": len(pairs),
            "unpaired_a": len(only_a), "unpaired_b": len(only_b),
            "ratio": 2 * len(pairs) / denominator if denominator else None,
            "formula": "2 * paired / (a_count + b_count)",
            "matching": (
                "mutual unique maximum overlapping line count within school/grade/semester"
                if strict else "mutual unique maximum overlap, then normalized title/task_text; "
                "unique title fallback without overlap, within school/grade/semester"
            ),
        },
        "fields": {field: {**counts, "agreement": (
            counts["matched"] / counts["total"] if counts["total"] else None
        )}
                   for field, counts in sorted(totals.items())},
        "difference_count": len(differences),
        "disagreement_types": [
            {"field": field, "a_status": a_status, "b_status": b_status, "count": count}
            for (field, a_status, b_status), count in sorted(
                Counter((f"document.{row['필드']}" if row["종류"] == "문서" else row["필드"],
                         row["A상태"], row["B상태"]) for row in differences).items(),
                key=lambda pair: (-pair[1], pair[0]),
            )
        ],
    }
    return differences, summary


def atomic_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Use an ordinary directory and a same-directory temporary file for ACLs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding=encoding, newline="") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def markdown_text(text: str) -> str:
    text = short(text, 350).replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"([\\`*_\[\]#|])", r"\\\1", text)


def write_reports(rows: list[dict], summary: dict, output: Path) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(output, buffer.getvalue(), "utf-8-sig")
    atomic_text(output.parent / "agreement.json",
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    lines = ["# 독립 라벨 불일치 판정", "", f"총 {len(rows)}건 · A/B는 실행 입력 순서", ""]
    previous_school = previous_term = previous_item = None
    for row in sorted(rows, key=lambda row: (
        row["학교"], row["학년"] or 0, row["학기"] or 0,
        row["A항목키"], row["B항목키"], row["_doc_id"], row["필드"],
    )):
        school = row["학교"]
        term = school, row["학년"], row["학기"]
        item = *term, row["A항목키"], row["B항목키"], row["_doc_id"]
        if school != previous_school:
            lines += [f"## {markdown_text(school)}", ""]
        if term != previous_term:
            heading = (f"{row['학년']}학년 {row['학기']}학기" if row["학년"] else "문서")
            lines += [f"### {heading}", ""]
        if item != previous_item:
            title = (row["_a_title"] if row["_a_title"] == row["_b_title"]
                     else f"A: {row['_a_title']} / B: {row['_b_title']}")
            lines += [f"#### {markdown_text(title)}", "",
                      f"A `{row['A항목키'] or row['_doc_id'] or '없음'}` · "
                      f"B `{row['B항목키'] or row['_doc_id'] or '없음'}`", ""]
        lines += [
            f"**{row['불일치ID']} · {row['필드']}**", "",
            f"- A값요약: {markdown_text(row['A값요약'])}",
            f"- B값요약: {markdown_text(row['B값요약'])}", "",
            f"원문 위치: `{row['원문 위치']}`", "", "원문 발췌:", "",
            *[f"> {markdown_text(line)}" for line in row["원문 발췌"][:300].splitlines()], "",
            "판정: A · B · 둘 다 아님", "",
        ]
        previous_school, previous_term, previous_item = school, term, item
    atomic_text(output.with_suffix(".md"), "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--out", type=Path, help="CSV 출력 경로 (기본 파일명은 모드에 따름)")
    parser.add_argument("--pack-dir", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--strict", action="store_true", help="v1 전체 비교 결과를 출력")
    args = parser.parse_args()
    for path in (args.a, args.b):
        errors = validate_file(path, args.pack_dir)
        if errors:
            print(f"입력 검사 실패 {path}")
            for error in errors:
                print(f"- {error}")
            return 1
    a, _, _ = read_labels(args.a)
    b, _, _ = read_labels(args.b)
    v1_rows, v1 = compare_labels(a, b, args.pack_dir, strict=True)
    v2_rows, v2 = compare_labels(a, b, args.pack_dir)
    summary = {"version": 2, "inputs": {"A": str(args.a), "B": str(args.b)}, "v1": v1, "v2": v2}
    rows, metrics = (v1_rows, v1) if args.strict else (v2_rows, v2)
    output = args.out or DEFAULT_PACK.parent / (
        "disagreements_strict.csv" if args.strict else "disagreements.csv"
    )
    write_reports(rows, summary, output)
    print(f"{'v1 strict' if args.strict else 'v2'} 불일치 {len(rows)}건. "
          f"항목 짝 비율 {metrics['item_pairing']['ratio']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
