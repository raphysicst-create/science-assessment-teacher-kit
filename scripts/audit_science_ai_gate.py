"""Block public science cards lacking a verified, source-backed AI approval.

Run: .venv/Scripts/python.exe scripts/audit_science_ai_gate.py --database DB
     --verified card_check/verified.json --output JSON --queue CSV
Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_s19_ai_gate.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.science_card_check import blocking_codes
from scripts.science_rules import public_items, risk_record, write_audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--verified", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    args = parser.parse_args()
    verified = json.loads(args.verified.read_text(encoding="utf-8"))
    verdicts = {card["item_id"]: card for card in verified["cards"]}
    rows = public_items(args.database)
    queue, counts = [], Counter()
    for item in rows:
        reasons = blocking_codes(verdicts.get(item["item_id"]))
        if reasons:
            codes = [reason.split(":", 1)[0] for reason in reasons]
            counts.update(codes)
            queue.append(risk_record(item, codes, reasons=";".join(reasons)))
    report = {
        "public_item_count": len(rows),
        "blocking_code_counts": dict(sorted(counts.items())),
        "verified": str(args.verified.resolve()),
    }
    write_audit(report, queue, args.output, args.queue)
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
