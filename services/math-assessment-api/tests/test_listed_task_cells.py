"""Plan C (task unit, E1): find listed task cells and add the C rule only to those chunks.

Run: .venv/Scripts/python.exe -m pytest -q \
    services/math-assessment-api/tests/test_listed_task_cells.py
Why: the C rule must reach the AI for 공산중-like cells, while every other chunk keeps its
prompt bytes so cached answers stay valid (N3, 26 such cells nationwide).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import middle_ai_first as first  # noqa: E402
from listed_task_cells import task_column_lines  # noqa: E402

HEADER = "<tr><th>단원</th><th>평가 방법</th><th>수행 과제</th><th>시기</th></tr>"
LISTED = ("<td>보일 법칙 실험 및 보고서 작성하기<br>샤를 법칙 실험 및 보고서 작성하기"
          "<br>생활 속 기체 현상 조사 및 발표하기</td>")


def plan(row):
    return "\n".join(["# 과학 평가 계획", "<table>" + HEADER, row + "</table>", "끝"])


def test_listed_cell_without_task_name_is_found():
    text = plan(f"<tr><td>Ⅵ 기체의 성질</td><td>보고서평가</td>{LISTED}<td>9월</td></tr>")
    assert task_column_lines(text) == [3]


def test_named_task_in_same_row_makes_lines_steps():
    named = "<td>힘의 특징을 이용한 기구 설계 및 발표하기</td>"
    text = plan(f"<tr><td>Ⅴ 힘의 작용</td>{named}{LISTED}<td>9월</td></tr>")
    assert task_column_lines(text) == []


def test_lines_with_own_scores_are_not_listed_tasks():
    scored = ("<td>보일 법칙 실험 및 보고서 작성하기 20점<br>"
              "샤를 법칙 실험 및 보고서 작성하기 20점</td>")
    text = plan(f"<tr><td>Ⅵ 기체의 성질</td><td>보고서평가</td>{scored}<td>9월</td></tr>")
    assert task_column_lines(text) == []


def test_only_chunks_with_a_listed_cell_get_the_c_rule(tmp_path):
    listed = plan(f"<tr><td>Ⅵ 기체의 성질</td><td>보고서평가</td>{LISTED}<td>9월</td></tr>")
    text = listed + "\n" + "본문 줄\n" * 5
    metadata = {"round": "r", "document_id": "d"}
    windows = [(1, 4), (5, 9)]
    plain = first.document_targets(tmp_path / "a", "T", metadata, "a_full", windows, "h", text)
    with_c = first.document_targets(tmp_path / "b", "T", metadata, "a_full", windows, "h", text,
                                    task_unit_c="\nC규칙")
    prompts = [(tmp_path / "b" / f"prompts/{t['target_id']}.md").read_text(encoding="utf-8")
               for t in with_c]
    assert "C규칙" in prompts[0] and "C규칙" not in prompts[1]
    assert with_c[1]["prompt_sha256"] == plain[1]["prompt_sha256"]
    assert with_c[0]["prompt_sha256"] != plain[0]["prompt_sha256"]
