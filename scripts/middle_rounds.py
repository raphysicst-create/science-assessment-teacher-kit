"""Offline round/roster selection shared by S4, S5 and S6 runners."""

from __future__ import annotations

import csv
from pathlib import Path


def roster_path(root: Path, round_key: str, roster: Path | None = None) -> Path:
    if not round_key or not all(c.isalnum() or c == "-" for c in round_key):
        raise ValueError("round key must contain only letters, digits and hyphens")
    if roster is not None:
        return roster if roster.is_absolute() else root / roster
    name = (
        "middle-dev2-20.csv" if round_key.endswith("-dev2") else
        "middle-gold10.csv" if round_key.endswith("-gold") else "middle-dev12.csv"
    )
    return root / "data/rosters" / name


def roster_codes(path: Path) -> set[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {str(row["school_code"]) for row in csv.DictReader(handle)}
