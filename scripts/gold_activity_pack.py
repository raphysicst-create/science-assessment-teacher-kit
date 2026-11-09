"""정답 세트 활동 라벨용 항목 묶음 만들기 (S8/S9 2차 라벨 준비).

무엇을 하는가: data/gold/gold_v1.jsonl(확정 정답 v1, 항목 83)에서
라벨러가 활동을 판정하는 데 필요한 것만 뽑아 data/gold/activity/items_v1.jsonl에 쓴다.
한 줄=한 항목이며 파이프라인 산출물(data/derived)은 쓰지 않는다.
포함: item_key, 학교, 학년·학기, 대표 제목·다른 이름, 제목 역할, 과제 설명,
평가 방법(체크 선택지·상태·평문), 채점기준 위치, 성취기준 코드, 자유학기, 원문 위치(doc_id·줄).
값은 정답 v1의 확정값(value)만 쓴다(A/B 라벨러 원본은 넣지 않는다).
돌리기: .venv/Scripts/python.exe scripts/gold_activity_pack.py  → 항목 수와 sha256을 출력
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = ROOT / "data/gold/gold_v1.jsonl"
OUT_PATH = ROOT / "data/gold/activity/items_v1.jsonl"
FIELDS = ("title", "title_role", "task_text", "method", "rubric", "standards", "free_semester",
          "period", "ratio", "max_score", "sub_scores")


def field_value(fields: dict, name: str):
    value = fields.get(name)
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def pack_item(item: dict) -> dict:
    fields = item["fields"]
    standards = field_value(fields, "standards") or []
    codes = sorted({code for group in standards if isinstance(group, dict)
                    for code in group.get("codes", [])})
    return {
        "item_key": item["item_key"], "school_id": item["school_id"],
        "grade": item["grade"], "semester": item["semester"],
        "representative_title": item.get("representative_title"),
        "aliases": item.get("aliases", []),
        "occurrences": item.get("occurrences", []),
        "title_role": field_value(fields, "title_role"),
        "task_text": field_value(fields, "task_text"),
        "method": field_value(fields, "method"),
        "rubric": field_value(fields, "rubric"),
        "standards_codes": codes,
        "standards_status": [g.get("status") for g in standards if isinstance(g, dict)],
        "free_semester": field_value(fields, "free_semester"),
    }


def build(gold_path: Path = GOLD_PATH, out_path: Path = OUT_PATH) -> dict:
    items = []
    with gold_path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("type") == "item":
                items.append(pack_item(record))
    items.sort(key=lambda i: i["item_key"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(i, ensure_ascii=False, sort_keys=True) + "\n" for i in items)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return {"items": len(items),
            "path": str(out_path.relative_to(ROOT) if out_path.is_relative_to(ROOT) else out_path),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=GOLD_PATH)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(build(args.gold, args.out), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
