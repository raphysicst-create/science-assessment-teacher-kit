"""List bounded science cards whose method text contains scorer/form patterns.

Run .venv/Scripts/python.exe scripts/check_science_method_text.py --database DB
    [--output json]. Exit 0 for no contaminated cards, otherwise 1.
Verify .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_s19_merge_method.py
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

METHOD_CONTAMINATION_RE = re.compile(
    r"교사|자기평가|동료평가|상호평가|관찰\s*및\s*기록|개별|개인별|모둠"
    r"|관찰\s*[·⋅･ㆍ・‧•]\s*기록"
)


def check_database(database: Path) -> dict:
    """Inspect the catalog read-only, returning one row per contaminated card."""
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT i.item_id, i.source_round, c.school_name, i.title, i.method "
            "FROM assessment_items AS i JOIN cases AS c ON c.case_id = i.case_id "
            "WHERE i.extraction_status = 'bounded' ORDER BY i.source_round, i.item_id"
        )
        items = [dict(row) for row in rows if METHOD_CONTAMINATION_RE.search(row["method"] or "")]
    return {"count": len(items), "items": items}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", choices=("json",))
    args = parser.parse_args()
    report = check_database(args.database)
    if args.output == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"method contamination cards = {report['count']}")
        for row in report["items"]:
            print(json.dumps(row, ensure_ascii=False))
    return int(report["count"] > 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
