"""The items step reads method checks from a small side file instead of the multi-GB report.

Run: .venv/Scripts/python.exe -m pytest -q \
    services/math-assessment-api/tests/test_method_checks_side_file.py
Why: nw5 conversion reports ran out of memory (11-16); items loaded the whole report.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from audit_middle_conversion import METHOD_CHECKS_SUFFIX, method_checks_file  # noqa: E402
from audit_middle_items import load_method_checks  # noqa: E402

ROUND = "2026-round-1-nw9"
DOCUMENTS = [
    {"sha256": "a", "method_check_comparison": {"source_rows": 3, "target_rows": 3}},
    {"sha256": "b", "converters": {"kordoc": {"conversion_status": "ok"}}},
    {"sha256": "c", "method_check_comparison": {"source_rows": 1, "target_rows": 0},
     "children": [{"sha256": "d", "method_check_comparison": {"source_rows": 9}}]},
]


def write_full(folder: Path) -> None:
    (folder / f"{ROUND}.json").write_text(
        json.dumps({"documents": DOCUMENTS}, ensure_ascii=False), encoding="utf-8")


def write_side(folder: Path) -> None:
    (folder / f"{ROUND}{METHOD_CHECKS_SUFFIX}").write_text(
        json.dumps(method_checks_file(ROUND, DOCUMENTS), ensure_ascii=False), encoding="utf-8")


def test_side_file_matches_full_report(tmp_path):
    write_full(tmp_path)
    from_full = load_method_checks(tmp_path, ROUND)
    write_side(tmp_path)
    assert load_method_checks(tmp_path, ROUND) == from_full
    assert set(from_full) == {"a", "c"}


def test_side_file_is_read_without_opening_full_report(tmp_path):
    write_side(tmp_path)
    (tmp_path / f"{ROUND}.json").write_text("not json", encoding="utf-8")
    side = tmp_path / f"{ROUND}{METHOD_CHECKS_SUFFIX}"
    os.utime(side, (side.stat().st_atime, (tmp_path / f"{ROUND}.json").stat().st_mtime + 1))
    assert set(load_method_checks(tmp_path, ROUND)) == {"a", "c"}


def test_stale_side_file_falls_back_to_full_report(tmp_path):
    (tmp_path / f"{ROUND}{METHOD_CHECKS_SUFFIX}").write_text(
        json.dumps({"method_checks": {"old": {}}}), encoding="utf-8")
    write_full(tmp_path)
    full = tmp_path / f"{ROUND}.json"
    side = tmp_path / f"{ROUND}{METHOD_CHECKS_SUFFIX}"
    os.utime(side, (side.stat().st_atime, full.stat().st_mtime - 10))
    assert set(load_method_checks(tmp_path, ROUND)) == {"a", "c"}


def test_no_report_means_no_checks(tmp_path):
    assert load_method_checks(tmp_path, ROUND) == {}
