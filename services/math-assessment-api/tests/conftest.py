"""Build an isolated science demo and axis export for API contract tests.

Verify with pytest services/math-assessment-api/tests/test_science_reference_api.py.
"""

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

if str(Path(__file__).resolve().parents[3]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.build_math_assessment_demo import build_demo

from app.main import app


@pytest.fixture
def science_demo(tmp_path, monkeypatch):
    database = tmp_path / "science.sqlite"
    axes = tmp_path / "axes.json"
    build_demo(database, axes)
    monkeypatch.setenv("MATH_ASSESSMENT_PUBLISH_DB", str(database))
    monkeypatch.setenv("MATH_ASSESSMENT_DETAIL_DB", str(database))
    monkeypatch.setenv("MATH_ASSESSMENT_ACTIVITY_TAB_POLICY", "all_reference")
    with TestClient(app, headers={"x-real-ip": str(uuid.uuid4())}) as client:
        yield {"client": client, "database": database, "axes": axes}
