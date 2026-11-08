"""Compare two independently labeled gold files using source-line overlap."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

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
COLUMNS = (
    "불일치ID", "학교", "학년", "학기", "종류", "필드", "A항목키", "B항목키",
    "A값", "B값", "원문 위치", "원문 발췌",
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


def match_items(a: list[dict], b: list[dict]) -> tuple[list[tuple[int, int]], list[int], list[int]]:
    """Only mutual unique maxima pair. Ties stay unmatched, independent of order."""
    scores = {}
    for i, left in enumerate(a):
        for j, right in enumerate(b):
            group = ("school_id", "grade", "semester")
            if all(left[key] == right[key] for key in group):
                score = overlap(left["occurrences"], right["occurrences"])
                if score:
                    scores[i, j] = score

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

    forward, backward = best(False), best(True)
    pairs = sorted((i, j) for i, j in forward.items() if backward.get(j) == i)
    used_a, used_b = {i for i, _ in pairs}, {j for _, j in pairs}
    return pairs, sorted(set(range(len(a))) - used_a), sorted(set(range(len(b))) - used_b)


def canonical(value):
    """Compare source values, choices and numbers, ignoring evidence prose/locations.

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


def sections_equal(a: dict, b: dict) -> bool:
    left, right = a["science_sections"], b["science_sections"]
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


def compare_labels(a: list[dict], b: list[dict], pack: Path) -> tuple[list[dict], dict]:
    index = load_index(pack)
    differences = []
    totals = {field: {"matched": 0, "total": 0}
              for field in (*FIELDS, "document.edition", "document.science_sections")}

    def count(field: str, equal: bool) -> None:
        totals[field]["total"] += 1
        totals[field]["matched"] += int(equal)

    def add(kind, field, left, right, a_value, b_value, locs):
        item = left or right
        school_id = item["school_id"]
        school = next((row["school_name"] for row in index.values()
                       if row["school_id"] == school_id), school_id)
        position, excerpt = source_excerpt(locs, pack)
        differences.append(dict(zip(COLUMNS, (
            f"D{len(differences) + 1:04d}", school, item.get("grade", ""),
            item.get("semester", ""), kind, field,
            (left or {}).get("item_key", ""), (right or {}).get("item_key", ""),
            json_text(a_value), json_text(b_value), position, excerpt,
        ), strict=True)))

    items_a = sorted((r for r in a if r["type"] == "item"), key=lambda r: r["item_key"])
    items_b = sorted((r for r in b if r["type"] == "item"), key=lambda r: r["item_key"])
    pairs, only_a, only_b = match_items(items_a, items_b)
    for i in only_a:
        item = items_a[i]
        add("항목존재", "항목 존재", item, None, item, None, item["occurrences"])
    for j in only_b:
        item = items_b[j]
        add("항목존재", "항목 존재", None, item, None, item, item["occurrences"])
    for i, j in pairs:
        left, right = items_a[i], items_b[j]
        for field in FIELDS:
            equal = canonical(left[field]) == canonical(right[field])
            count(field, equal)
            if not equal:
                locs = locations([left[field], right[field]])
                add("필드", field, left, right, left[field], right[field],
                    locs or left["occurrences"] + right["occurrences"])
    docs_a = {row["doc_id"]: row for row in a if row["type"] == "document"}
    docs_b = {row["doc_id"]: row for row in b if row["type"] == "document"}
    for doc_id in sorted(docs_a.keys() | docs_b.keys()):
        left, right = docs_a.get(doc_id), docs_b.get(doc_id)
        if left is None or right is None:
            add("문서", "문서 존재", left, right, left, right, [{"doc_id": doc_id, "line": 1}])
            continue
        for field, equal in (
            ("edition", left["edition"] == right["edition"]),
            ("science_sections", sections_equal(left, right)),
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
            "matching": "mutual unique maximum overlapping line count within school/grade/semester",
        },
        "fields": {field: {**counts, "agreement": (
            counts["matched"] / counts["total"] if counts["total"] else None
        )}
                   for field, counts in sorted(totals.items())},
        "difference_count": len(differences),
    }
    return differences, summary


def write_reports(rows: list[dict], summary: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    (output.parent / "agreement.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    lines = ["# 독립 라벨 불일치 판정", "", f"총 {len(rows)}건", ""]
    for row in rows:
        lines += [
            f"## {row['불일치ID']} · {row['학교']} · {row['필드']}", "",
            f"{row['학년']}학년 {row['학기']}학기 · {row['종류']}" if row["학년"] else "문서 판정",
            "", f"A 항목 `{row['A항목키']}`", "", "**A값**", "", row["A값"], "",
            f"B 항목 `{row['B항목키']}`", "", "**B값**", "", row["B값"], "",
            f"원문 위치 `{row['원문 위치']}`", "", "**원문 발췌**", "",
            *[f"> {line}" for line in row["원문 발췌"].splitlines()], "",
            "판정: A / B / 둘 다 아님(직접 입력)", "", "직접 입력 및 근거 ____________________", "",
        ]
    output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_PACK.parent / "disagreements.csv")
    parser.add_argument("--pack-dir", type=Path, default=DEFAULT_PACK)
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
    rows, summary = compare_labels(a, b, args.pack_dir)
    write_reports(rows, summary, args.out)
    print(f"불일치 {len(rows)}건. 항목 짝 비율 {summary['item_pairing']['ratio']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
