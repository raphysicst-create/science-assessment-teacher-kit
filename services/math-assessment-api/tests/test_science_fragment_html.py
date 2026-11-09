"""Check science source fragments without rebuilding a catalog or reading source data.

Run/verify: .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_science_fragment_html.py
"""

import re
import zlib
from html import unescape

import pytest
from scripts.build_math_assessment_demo import demo_records
from scripts.build_science_catalog_db import close_table_fragments, item_row
from scripts.math_assessment_detail_parser import markdown_fragment_to_html

COMPLETE_TABLE = "<table><tr><td>A</td><td>완결 표</td></tr></table>"
STORED_FRAGMENT = (
    '수행과제 비열 비교하기 반영비율 20%</th></tr>\n<tr><td colspan="2">성취기준</td>'
    '<td colspan="5">성취기준별 성취수준</td></tr>\n'
    + COMPLETE_TABLE
    + "\n<tr><td>꼬리</td>"
)


def stored_row(fragment):
    record = demo_records()[0]
    prefix, suffix = "범위 밖 앞부분", "범위 밖 뒷부분"
    record["text"] = prefix + fragment + suffix
    record["item"]["locator"] = {"start": len(prefix), "end": len(prefix) + len(fragment)}
    row = item_row(record, 1)
    assert (row["source_start"], row["source_end"]) == (
        len(prefix), len(prefix) + len(fragment),
    )
    assert record["item"]["locator"] == {
        "start": row["source_start"], "end": row["source_end"],
    }
    html = zlib.decompress(row["source_html_zlib"]).decode("utf-8")
    assert row["source_html_char_count"] == len(html)
    assert prefix not in html and suffix not in html
    return html


def test_science_fragment_stored_html_preserves_text_and_complete_table():
    html = stored_row(STORED_FRAGMENT)
    assert "&lt;" not in html
    assert COMPLETE_TABLE in html
    for value in ("성취기준", "성취기준별 성취수준", "꼬리"):
        assert value in html
    # Like audit-source-table-renderer: strip tags, decode entities and ignore whitespace.
    rendered_text = re.sub(r"\s+", "", unescape(re.sub(r"<[^>]*>", " ", html)))
    for segment in re.split(r"<[^>]*>", STORED_FRAGMENT):
        assert re.sub(r"\s+", "", unescape(segment)) in rendered_text


@pytest.mark.parametrize("fragment", [
    "일반 원문\n둘째 줄<br>셋째 줄",
    "## 평가 계획\n- 관찰 기록\n\n" + COMPLETE_TABLE,
    "| 항목 | 내용 |\n| --- | --- |\n| 과제 | 실험 |",
    "<table><tr><td>바깥" + COMPLETE_TABLE + "</td></tr></table>",
    "",
])
def test_science_fragment_free_input_keeps_existing_html(fragment):
    assert close_table_fragments(fragment) == fragment
    assert stored_row(fragment) == markdown_fragment_to_html(fragment)


@pytest.mark.parametrize(("fragment", "expected"), [
    ('<tr><td colspan="2">앞<br>뒤</td><th>다음</th></tr></table>',
     "\n | 앞\n뒤 | 다음 | \n\n"),
    ("<TABLE><TR><TH>머리<BR/>둘째</TH></TR>", "\n\n | 머리\n둘째 | \n"),
    ("</td></tr>처음\n" + COMPLETE_TABLE + "\n<table><tr><td>마지막",
     " | \n처음\n" + COMPLETE_TABLE + "\n\n\n | 마지막"),
])
def test_science_fragment_boundaries_become_readable_text(fragment, expected):
    assert close_table_fragments(fragment) == expected
    assert "&lt;" not in stored_row(fragment)
