"""atomic_json writes the same bytes as before while streaming to disk.

Run: .venv/Scripts/python.exe -m pytest -q services/math-assessment-api/tests/test_atomic_json_stream.py
Why: nw5 conversion reports (several GB) hit MemoryError when the whole JSON was built as one string.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import collect_schoolinfo_4ga_historical as historical  # noqa: E402

SAMPLE = {"학교": "거제고현중학교", "documents": [{"n": 1, "ok": True, "x": None}], "빈": []}


def test_atomic_json_bytes_match_previous_format(tmp_path):
    target = tmp_path / "report.json"
    historical.atomic_json(target, SAMPLE)
    expected = (json.dumps(SAMPLE, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    assert target.read_bytes() == expected
    assert list(tmp_path.glob("*.partial")) == []


def test_atomic_json_does_not_build_one_string(tmp_path, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("json.dumps would hold the whole report in memory")

    monkeypatch.setattr(historical.json, "dumps", refuse)
    historical.atomic_json(tmp_path / "report.json", SAMPLE)
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8")) == SAMPLE
