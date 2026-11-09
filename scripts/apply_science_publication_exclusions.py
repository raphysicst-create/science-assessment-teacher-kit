"""감사 차단 항목을 공개 DB에서 뺀다 (S16 완료 기준 2).

무엇을 하는가: `run_science_audits.py`가 만든 위험 큐(`risk-queue.csv`, severity=blocking만)의
item_id를 공개판 SQLite 사본에서 `extraction_status='review'`로 바꾼다. 공개 조건이 `bounded`이므로
그 항목은 화면·API·패키지에서 빠진다. 원본 DB는 손대지 않고 사본을 새로 만든다.
처리 결정 기록으로 면제하지 않는다.
돌리기:
  .venv/Scripts/python.exe scripts/apply_science_publication_exclusions.py \
    --source data/publish/science/math_assessment_catalog_detail.sqlite \
    --risk-queue data/derived/science_audit/risk-queue.csv \
    --output data/publish/science/math_assessment_catalog_detail.public.sqlite \
    --report data/derived/science_audit/publication-exclusions.json
검증: 출력 DB에서 큐 item_id의 bounded 수가 0이고, report의 excluded 수가 큐의 blocking 행 수와
같다.
여러 큐는 --risk-queue CSV1 CSV2 또는 --risk-queue CSV1 --risk-queue CSV2로 전달한다.
검증 명령 .venv/Scripts/python.exe -m pytest -q
  services/math-assessment-api/tests/test_science_card_check.py -k risk_queues
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

REVIEW_STATUS = "review"


def blocking_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row for row in csv.DictReader(handle)
                if row.get("severity", "blocking") == "blocking"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(source: Path, risk_queue: Path | list[Path], output: Path, report: Path) -> dict:
    queues = [risk_queue] if isinstance(risk_queue, Path) else list(risk_queue)
    rows = [row for queue in queues for row in blocking_rows(queue)]
    ids = sorted({row["item_id"] for row in rows if row.get("item_id")})
    if output.exists():
        output.unlink()
    shutil.copyfile(source, output)
    with closing(sqlite3.connect(output)) as db, db:
        marks = ",".join("?" * len(ids))
        before = {r[0]: r[1] for r in db.execute(
            "SELECT item_id, extraction_status FROM assessment_items "
            f"WHERE item_id IN ({marks})", ids)} if ids else {}
        db.executemany(
            "UPDATE assessment_items SET extraction_status = ? WHERE item_id = ?",
            [(REVIEW_STATUS, item_id) for item_id in ids],
        )
        remaining = db.execute(
            "SELECT COUNT(*) FROM assessment_items "
            f"WHERE extraction_status = 'bounded' AND item_id IN ({marks})",
            ids).fetchone()[0] if ids else 0
        public_after = db.execute(
            "SELECT COUNT(*) FROM assessment_items WHERE extraction_status = 'bounded'"
        ).fetchone()[0]
        public_before = public_after + sum(1 for v in before.values() if v == "bounded")
    with closing(sqlite3.connect(output)) as db:
        db.isolation_level = None
        db.execute("VACUUM")
    summary = {
        "source": source.as_posix(), "source_sha256": sha256(source),
        "output": output.as_posix(), "output_sha256": sha256(output),
        "risk_queue": queues[0].as_posix() if len(queues) == 1 else [q.as_posix() for q in queues],
        "risk_queue_sha256": sha256(queues[0]) if len(queues) == 1 else [sha256(q) for q in queues],
        "excluded": len(ids),
        "excluded_was_bounded": sum(1 for v in before.values() if v == "bounded"),
        "not_in_db": sorted(set(ids) - set(before)),
        "public_bounded_before": public_before, "public_bounded_after": public_after,
        "remaining_bounded_blocking": remaining,
        "items": [{"item_id": r["item_id"], "school_name": r.get("school_name"),
                   "title": r.get("title"), "blocking_codes": r.get("blocking_codes"),
                   "reasons": r.get("reasons")} for r in rows],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--risk-queue", type=Path, action="append", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    queues = [queue for group in args.risk_queue for queue in group]
    summary = apply(args.source, queues, args.output, args.report)
    print(json.dumps({k: summary[k] for k in (
        "excluded", "excluded_was_bounded", "public_bounded_before", "public_bounded_after",
        "remaining_bounded_blocking", "not_in_db")}, ensure_ascii=False))
    return 0 if summary["remaining_bounded_blocking"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
