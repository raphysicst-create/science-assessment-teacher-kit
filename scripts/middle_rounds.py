"""Offline round/roster selection shared by S4, S5 and S6 runners.

Import roster_path(root, round_key) to select a roster.
Verify with .venv/Scripts/python.exe -m pytest -q -k 'roster or rounds'.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

NATIONWIDE_ROUND = re.compile(r"^\d{4}-round-(\d)-nw(\d+)$")


def roster_path(root: Path, round_key: str, roster: Path | None = None) -> Path:
    if not round_key or not all(c.isalnum() or c == "-" for c in round_key):
        raise ValueError("round key must contain only letters, digits and hyphens")
    if roster is not None:
        return roster if roster.is_absolute() else root / roster
    nationwide = NATIONWIDE_ROUND.fullmatch(round_key)
    if nationwide:
        return root / "data/rosters" / f"middle-nw{nationwide[2]}-round-{nationwide[1]}.csv"
    fresh = re.search(r"-fresh(\d+)$", round_key)
    name = (
        "middle-dev2-20.csv" if round_key.endswith("-dev2") else
        "middle-gold2-5.csv" if round_key.endswith("-gold2") else
        f"middle-fresh{fresh[1]}.csv" if fresh else
        "middle-gold10.csv" if round_key.endswith("-gold") else "middle-dev12.csv"
    )
    return root / "data/rosters" / name


def roster_codes(path: Path) -> set[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {str(row["school_code"]) for row in csv.DictReader(handle)}
