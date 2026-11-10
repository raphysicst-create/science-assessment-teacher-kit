"""새 학교 품질 확인(astra) 여러 회를 한 표로 합산한다(S18 fresh3 · S19 fresh4 · S20 fresh5 · N1 fresh6 …).

무엇: 각 astra 품질 Markdown의 2절 카드 판정 칸을 `count_astra_card_verdicts.count_verdicts`로 세고,
      4절 요약의 "원문 과제 m개 중 카드 없음 k"에서 재현율 (m-k)/m을 낸다. 재판정 보충 파일
      (예: S18 `fresh3-astra-extra.md`의 "원문 과제 **31 → 추출 29 → 공개 22**")이 있으면 재현율은 그 값을 쓴다.
Run: .venv/Scripts/python.exe scripts/fresh_quality_table.py \
       S18=docs/gold/2026-11-10-fresh3-astra-quality.md+docs/gold/2026-11-10-fresh3-astra-extra.md \
       S19=docs/gold/2026-11-10-fresh4-astra-quality.md S20=docs/gold/2026-11-10-fresh5-astra-quality.md \
       N1=docs/gold/2026-11-10-fresh6-astra-quality.md
Verify: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_fresh_quality_table.py
"""

# ruff: noqa: E501  (실행 예시·표 줄은 줄바꿈하지 않는다)

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.count_astra_card_verdicts import count_verdicts

SUMMARY_RE = re.compile(r"원문 과제\s*(\d+)\s*개 중 카드 없음\s*(\d+)")
EXTRA_RE = re.compile(r"원문 과제\s*\**(\d+)\s*→\s*추출\s*(\d+)\s*→\s*공개\s*(\d+)")
OK = ("맞음", "경계")  # 경계는 맞음으로 센다(요청문 판정 기준)


def recall_from(markdown: str, extra: str | None) -> tuple[int, int]:
    if extra:
        match = EXTRA_RE.search(extra)
        if not match:
            raise ValueError("보충 파일에 '원문 과제 N → 추출 N → 공개 N' 줄이 없다")
        return int(match[3]), int(match[1])
    match = SUMMARY_RE.search(markdown)
    if not match:
        raise ValueError("4절 요약에 '원문 과제 m개 중 카드 없음 k'가 없다")
    tasks, missing = int(match[1]), int(match[2])
    return tasks - missing, tasks


def row(label: str, markdown: str, extra: str | None = None) -> dict:
    counts = count_verdicts(markdown)
    columns = counts["columns"]
    found, tasks = recall_from(markdown, extra)
    cards = counts["cards"]

    def ok(name: str) -> int:
        return sum(columns.get(name, {}).get(value, 0) for value in OK)

    return {
        "label": label, "source_tasks": tasks, "tasks_with_card": found,
        "recall": round(found / tasks, 3) if tasks else None,
        "cards": cards, "precision": f"{columns.get('수행평가 과제', {}).get('맞음', 0)}/{cards}",
        "title_ok": ok("제목"), "unit_ok": ok("단원"),
        "activity_ok": ok("활동"), "activity_blank": columns.get("활동", {}).get("빈칸", 0),
        "method_ok": ok("방법"), "method_blank": columns.get("방법", {}).get("빈칸", 0),
        "recall_source": "보충 파일" if extra else "4절 요약",
    }


def markdown_table(rows: list[dict]) -> str:
    lines = ["| 회 | 원문 과제 | 카드 있는 과제 | 재현율 | 카드 | 정밀도(과제 맞음) | 제목 | 단원 | 활동 맞음(빈칸) | 방법 맞음(빈칸) |",
             "|---|---:|---:|---:|---:|---|---:|---:|---|---|"]
    for r in rows:
        lines.append(f"| {r['label']} | {r['source_tasks']} | {r['tasks_with_card']} | {r['recall']} | {r['cards']} | "
                     f"{r['precision']} | {r['title_ok']} | {r['unit_ok']} | {r['activity_ok']}({r['activity_blank']}) | "
                     f"{r['method_ok']}({r['method_blank']}) |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    for spec in (argv if argv is not None else sys.argv[1:]):
        label, paths = spec.split("=", 1)
        main_path, _, extra_path = paths.partition("+")
        markdown = Path(main_path).read_text(encoding="utf-8")
        extra = Path(extra_path).read_text(encoding="utf-8") if extra_path else None
        rows.append(row(label, markdown, extra))
    print(json.dumps(rows, ensure_ascii=False, indent=1))
    print(markdown_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
