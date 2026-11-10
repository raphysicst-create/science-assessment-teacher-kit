"""astra 품질 확인 Markdown의 '2절 카드 판정' 표를 칸별로 합산한다(결정 자료 숫자의 출처).

무엇: `| 카드 | 수행평가 과제 | 제목 | 단원 | 활동 | 방법 | …` 표의 각 칸 값(맞음·틀림·경계·빈칸·근거 없음·-)을 센다.
      손으로 요약하다 경계를 두 번 세는 일(S18·S19 검수 차단)을 막는다.
Run: .venv/Scripts/python.exe scripts/count_astra_card_verdicts.py docs/gold/2026-11-10-fresh4-astra-quality.md
Verify: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_count_astra_card_verdicts.py
"""

# ruff: noqa: E501  (실행 예시 줄은 줄바꿈하지 않는다)

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

COLUMNS = ("수행평가 과제", "제목", "단원", "활동", "방법")
CARD_RE = re.compile(r"^[A-Z]\d{2}$")


def count_verdicts(markdown: str) -> dict:
    header = None
    counts = {name: Counter() for name in COLUMNS}
    cards = 0
    for line in markdown.splitlines():
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) > 1 and cells[0] == "카드" and all(name in cells for name in COLUMNS):
            header = cells
            continue
        if header and len(cells) >= len(header) and CARD_RE.match(cells[0]):
            cards += 1
            for name in COLUMNS:
                counts[name][cells[header.index(name)]] += 1
        elif header and line.strip() and not line.strip().startswith("|"):
            header = None
    return {"cards": cards, "columns": {name: dict(counter) for name, counter in counts.items()}}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    result = count_verdicts(Path(args[0]).read_text(encoding="utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["cards"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
