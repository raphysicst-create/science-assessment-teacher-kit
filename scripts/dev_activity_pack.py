"""개발 표본 활동 라벨용 항목 묶음 만들기 (정답 아님, 개발용).

무엇을 하는가: 개발 12개교(2026-round-3)와 보충 20개교(2026-round-1-dev2, 2026-round-3-dev2)의
확정 수행평가 항목(candidate_role=performance, extraction_status∈{bounded, ai_verified})마다
라벨러가 원문을 읽을 수 있게 변환 텍스트의 줄 범위와 발췌를 붙여
data/dev_labels/items_dev.jsonl에 쓴다.
파이프라인이 추출한 필드(방법·요소·채점기준)는 넣지 않는다.
라벨러는 원문 발췌만 본다(추출 오류와 독립).
문서 전문은 data/dev_labels/pack/<doc_id>.txt(줄 번호 붙임)에 쓴다.

돌리기: .venv/Scripts/python.exe scripts/dev_activity_pack.py  → 항목 수·학교 수·sha256 출력
검증: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
services/math-assessment-api/tests/test_dev_activity_pack.py
정답 회차(*-gold*)는 읽지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "2026-round-3": ROOT / "data/derived/items/2026-round-3.json",
    "2026-round-1-dev2": ROOT / "data/derived/items_ai/2026-round-1-dev2.json",
    "2026-round-3-dev2": ROOT / "data/derived/items_ai/2026-round-3-dev2.json",
}
OUT_DIR = ROOT / "data/dev_labels"
LINES_BEFORE = 5
LINES_AFTER = 45


def guard(path: Path) -> Path:
    if "gold" in str(path).lower():
        raise ValueError(f"맹검 경로: {path}")
    return path


def doc_id(document_id: str) -> str:
    return document_id.removeprefix("doc_")[:12]


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def numbered_lines(text: str) -> list[str]:
    return [f"{number:>6}\t{line}" for number, line in enumerate(text.split("\n"), 1)]


def pack_item(item: dict, round_key: str, text: str, numbered: list[str]) -> dict:
    locator = item["locator"]
    start, end = locator["start"], locator["end"]
    line_start = line_of(text, start)
    line_end = line_of(text, max(start, end - 1))
    first = max(1, line_start - LINES_BEFORE)
    last = min(len(numbered), line_end + LINES_AFTER)
    title = item.get("fields", {}).get("title", {})
    return {
        "item_id": item["item_id"],
        "round": round_key,
        "school": item.get("school"),
        "school_code": item.get("school_code"),
        "grade": item.get("grade"),
        "semester": item.get("semester"),
        "title": title.get("value") if isinstance(title, dict) else None,
        "title_role": item.get("title_role"),
        "extraction_status": item.get("extraction_status"),
        "doc_id": doc_id(item["document_id"]),
        "converted_path": item.get("converted_path"),
        "line_start": line_start,
        "line_end": line_end,
        "excerpt_lines": [first, last],
        "excerpt": "\n".join(numbered[first - 1:last]),
    }


def build(sources: dict[str, Path] = SOURCES, out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    pack_dir = out_dir / "pack"
    pack_dir.mkdir(exist_ok=True)
    rows, texts, documents = [], {}, {}
    for round_key, path in sources.items():
        document = json.loads(guard(path).read_text(encoding="utf-8-sig"))
        for item in document["items"]:
            if item.get("candidate_role") != "performance":
                continue
            if item.get("extraction_status") not in ("bounded", "ai_verified"):
                continue
            converted = guard(ROOT / item["converted_path"])
            if converted not in texts:
                texts[converted] = json.loads(converted.read_text(encoding="utf-8-sig"))["text"]
                numbered = numbered_lines(texts[converted])
                documents[converted] = numbered
                (pack_dir / f"{doc_id(item['document_id'])}.txt").write_text(
                    "\n".join(numbered) + "\n", encoding="utf-8", newline="\n")
            rows.append(pack_item(item, round_key, texts[converted], documents[converted]))
    rows.sort(key=lambda row: (row["round"], row["school"] or "", row["grade"] or 0,
                               row["semester"] or 0, row["line_start"], row["item_id"]))
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    out_path = out_dir / "items_dev.jsonl"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return {"items": len(rows), "schools": len({r["school"] for r in rows}),
            "documents": len(documents), "path": str(out_path.relative_to(ROOT)),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "by_round": {k: sum(r["round"] == k for r in rows) for k in sources}}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(build(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
