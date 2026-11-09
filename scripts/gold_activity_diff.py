"""두 라벨러의 활동 라벨 비교 (S9 2차 라벨 불일치 추출).

무엇을 하는가: data/gold/activity/labels/<A>.jsonl과 <B>.jsonl을 item_key로 맞춰
  - 주활동 일치율(기권 포함), 보조활동 집합 일치율, 라벨러별 주활동 분포, 혼동표(A 주 × B 주)
  - 불일치 목록(항목·학교·제목·A 주/보조·B 주/보조·각자의 근거 인용)을 CSV와 MD로 쓴다.
판정(정의로 풀리는지, 사람에게 물을지)은 사람(부서장)이 MD를 보고 한다.
이 스크립트는 판단하지 않는다.
돌리기: .venv/Scripts/python.exe scripts/gold_activity_diff.py
      --a data/gold/activity/labels/claude.jsonl
      --b data/gold/activity/labels/astra.jsonl --out data/gold/activity/disagreements
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ITEMS_PATH = ROOT / "data/gold/activity/items_v1.jsonl"
ABSTAIN = "(기권)"


def load_jsonl(path: Path) -> dict[str, dict]:
    records = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                record = json.loads(line)
                records[record["item_key"]] = record
    return records


def primary_of(record: dict | None) -> str:
    if record is None:
        return "(없음)"
    return record.get("primary") or ABSTAIN


def quotes(record: dict | None) -> str:
    if not record:
        return ""
    return " / ".join(f"[{e.get('type')}] {e.get('quote')}" for e in record.get("evidence", []))


def compare(a: dict[str, dict], b: dict[str, dict], items: dict[str, dict]) -> dict:
    keys = sorted(set(a) | set(b))
    rows, confusion = [], Counter()
    primary_match = secondary_match = both_abstain = 0
    for key in keys:
        left, right = a.get(key), b.get(key)
        pa, pb = primary_of(left), primary_of(right)
        confusion[(pa, pb)] += 1
        sa = set((left or {}).get("secondary", []))
        sb = set((right or {}).get("secondary", []))
        same_primary = pa == pb
        same_secondary = sa == sb
        primary_match += same_primary
        secondary_match += same_secondary
        both_abstain += pa == pb == ABSTAIN
        if same_primary and same_secondary:
            continue
        item = items.get(key, {})
        title = (item.get("representative_title") or {}).get("raw", "")
        rows.append({
            "item_key": key, "school_id": item.get("school_id", ""),
            "grade": item.get("grade", ""), "semester": item.get("semester", ""),
            "title": title.replace("\n", " "),
            "kind": "주활동" if not same_primary else "보조활동",
            "A_primary": pa, "A_secondary": "|".join(sorted(sa)),
            "B_primary": pb, "B_secondary": "|".join(sorted(sb)),
            "A_evidence": quotes(left), "B_evidence": quotes(right),
            "A_note": (left or {}).get("note", ""), "B_note": (right or {}).get("note", ""),
        })
    total = len(keys)
    return {
        "items": total, "primary_agreement": primary_match / total if total else None,
        "primary_agree": primary_match, "secondary_agree": secondary_match,
        "both_abstain": both_abstain,
        "primary_disagreements": sum(1 for r in rows if r["kind"] == "주활동"),
        "secondary_only_disagreements": sum(1 for r in rows if r["kind"] == "보조활동"),
        "A_primary_counts": dict(Counter(primary_of(a.get(k)) for k in keys)),
        "B_primary_counts": dict(Counter(primary_of(b.get(k)) for k in keys)),
        "confusion": [{"A": pa, "B": pb, "count": c} for (pa, pb), c in sorted(confusion.items())],
        "rows": rows,
    }


def write_outputs(report: dict, out_prefix: Path, a_name: str, b_name: str) -> None:
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    rows = report["rows"]
    with (out_prefix.with_suffix(".csv")).open("w", encoding="utf-8", newline="") as stream:
        fields = list(rows[0].keys()) if rows else ["item_key"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {k: v for k, v in report.items() if k != "rows"}
    (out_prefix.with_suffix(".json")).write_text(
        json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    lines = [f"# 활동 라벨 불일치 ({a_name} vs {b_name})", "",
             f"- 항목 {report['items']} · 주활동 일치 {report['primary_agree']} "
             f"({report['primary_agreement']:.1%}) · 보조 집합 일치 {report['secondary_agree']} · "
             f"둘 다 기권 {report['both_abstain']}",
             f"- 주활동 불일치 {report['primary_disagreements']} · 보조만 불일치 "
             f"{report['secondary_only_disagreements']}", "",
             "## 혼동표 (A 주 × B 주)", "", "| A \\ B | " + " | ".join(
                 sorted({c['B'] for c in report['confusion']})) + " |"]
    cols = sorted({c["B"] for c in report["confusion"]})
    lines.append("|---|" + "---|" * len(cols))
    grid = {(c["A"], c["B"]): c["count"] for c in report["confusion"]}
    for pa in sorted({c["A"] for c in report["confusion"]}):
        lines.append(f"| {pa} | " + " | ".join(str(grid.get((pa, pb), "")) for pb in cols) + " |")
    lines += ["", "## 불일치 목록", ""]
    for row in rows:
        lines += [f"### {row['item_key']} · {row['school_id']} "
                  f"{row['grade']}-{row['semester']} · {row['title']}",
                  f"- 종류: {row['kind']}",
                  f"- {a_name}: 주 **{row['A_primary']}** · 보조 {row['A_secondary'] or '-'} · "
                  f"근거 {row['A_evidence'] or '-'}"
                  + (f" · 메모 {row['A_note']}" if row['A_note'] else ""),
                  f"- {b_name}: 주 **{row['B_primary']}** · 보조 {row['B_secondary'] or '-'} · "
                  f"근거 {row['B_evidence'] or '-'}"
                  + (f" · 메모 {row['B_note']}" if row['B_note'] else ""), ""]
    (out_prefix.with_suffix(".md")).write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a", type=Path, required=True)
    parser.add_argument("--b", type=Path, required=True)
    parser.add_argument("--items", type=Path, default=ITEMS_PATH)
    parser.add_argument("--out", type=Path, required=True, help="출력 접두(확장자 없이)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    items = load_jsonl(args.items)
    report = compare(load_jsonl(args.a), load_jsonl(args.b), items)
    write_outputs(report, args.out, args.a.stem, args.b.stem)
    print(json.dumps({k: v for k, v in report.items() if k not in {"rows", "confusion"}},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
