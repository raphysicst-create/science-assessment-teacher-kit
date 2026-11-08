"""Synthetic, offline adjudication tests; use ordinary folders for Windows ACLs."""

import copy
import csv
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT = Path(__file__).resolve().parents[3]


@pytest.fixture
def rules(monkeypatch):
    monkeypatch.syspath_prepend(str(PROJECT / "scripts"))

    def no_network(*args, **kwargs):
        pytest.fail("Adjudication must be offline")

    monkeypatch.setattr("socket.socket.connect", no_network)
    return importlib.import_module("gold_adjudicate")


@pytest.fixture
def ordinary_dir():
    parent = PROJECT / ".tmp/gold-rule-tests"
    directory = parent / uuid4().hex
    directory.mkdir(parents=True)
    yield directory
    assert directory.resolve().is_relative_to(parent.resolve())
    shutil.rmtree(directory)


def loc(line=2, end=None):
    return (
        {"doc_id": "synthetic", "line": line}
        if end is None
        else {
            "doc_id": "synthetic",
            "line_start": line,
            "line_end": end,
        }
    )


def value(raw=None, line=2, status=None, **extra):
    vals = [] if raw is None else [{"raw": raw, "loc": loc(line), **extra}]
    return {"status": status or ("present" if raw is not None else "source_absent"), "values": vals}


def make_pack(rules, ordinary_dir, lines):
    pack = ordinary_dir / "pack"
    pack.mkdir(exist_ok=True)
    (pack / "synthetic.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (pack / "index.json").write_text(
        json.dumps(
            [
                {
                    "doc_id": "synthetic",
                    "school_id": "school",
                    "school_name": "가상중",
                    "line_count": len(lines),
                }
            ]
        ),
        encoding="utf-8",
    )
    return rules.Pack(pack)


def item(key="01", title="밀도 측정하기", role="과제명"):
    fields = {
        f: value()
        for f in (
            "task_text",
            "task_no",
            "period",
            "method",
            "max_score",
            "sub_scores",
            "ratio",
            "rubric",
        )
    }
    return {
        "type": "item",
        "school_id": "school",
        "grade": 1,
        "semester": 1,
        "labeler": "synthetic",
        "item_key": f"school-g1-s1-{key}",
        "occurrences": [loc(1, 4)],
        "title": {**value(title), "role": role},
        "free_semester": False,
        "standards": [{**value(), "codes": []}],
        **fields,
    }


def row(field, a, b, identifier="arbitrary-not-a-real-ID"):
    return {
        "필드": field,
        "A값": json.dumps(a, ensure_ascii=False),
        "B값": json.dumps(b, ensure_ascii=False),
        "불일치ID": identifier,
    }


def decide(rules, pack, field, a, b):
    return rules.adjudicate(row(field, a, b), item(), item(), pack)


def test_rule0_union_preserves_every_existing_value(rules, ordinary_dir):
    pack = make_pack(rules, ordinary_dir, ["수행평가", "4월", "5월", "6월"])
    a, b = value("4월"), value("4월")
    a["values"].append(value("5월", 3)["values"][0])
    b["values"].append(value("6월", 4)["values"][0])
    d = decide(rules, pack, "period", a, b)
    assert d.result == "둘다" and d.rules == [0]
    assert {v["raw"] for v in d.value["values"]} == {"4월", "5월", "6월"}
    assert d.mode == "기계"


def test_rule0_numeric_overlap_and_no_metadata_overlap(rules):
    assert rules.rule0(value("15", norm=15), value("15점", norm=15))
    assert not rules.rule0(value("15", status="ambiguous"), value("15"))
    assert not rules.rule0(value("첫 값"), value("다른 값"))  # Same loc is not overlap.


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("실험", "평가영역"),
        ("탐구", "평가영역"),
        ("서논술형", "평가영역"),
        ("수행평가 1", "번호"),
        ("2 / 수행평가 1", "번호"),
        ("열, 비열, 열팽창 관계 실험 보고서 쓰기", "과제명"),
        ("천체의 운동 구술 평가", "과제명"),
    ],
)
def test_rule1_roles(rules, text, expected):
    assert rules.title_role(text) == expected


def test_rule1_representative_and_role_choice(rules, ordinary_dir):
    pack = make_pack(rules, ordinary_dir, ["수행평가 1", "밀도 측정하기", "실험", "끝"])
    a, b = value("밀도 측정하기", 2), value("수행평가 1", 1)
    d = rules.rule_titles(a, b, pack)
    assert d.result == "A" and d.rules == [1]
    left, right = item(), item(title="수행평가 1", role="번호")
    right["title"]["values"][0]["loc"] = loc(1)
    role = rules.rule1("과제명", "번호", left, right, pack)
    assert role.value == "과제명" and role.result == "A"


def test_rule2_generic_levels_are_absent(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "## 학기 전체 성취기준별 성취수준",
            "<table>",
            "<tr><th>성취기준</th><th>성취기준별 성취수준</th></tr>",
            "<tr><td>A</td><td>설명할 수 있다</td></tr>",
            "</table>",
        ],
    )
    d = decide(rules, pack, "rubric", value("성취수준", 4, "ambiguous"), value("성취수준", 4))
    assert d.result == "없음(source_absent)" and d.rules == [2]
    assert d.value == rules.ABSENT
    assert any(e.line in (1, 3) and "성취수준" in e.excerpt for e in d.evidence)
    assert all(len(e.excerpt) <= 80 for e in d.evidence)


def test_rule2_dedicated_rubric_is_not_generic(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "## 밀도 측정 수행평가",
            "<table>",
            "<tr><th>채점기준</th><th>배점</th></tr>",
            "<tr><td>밀도를 바르게 계산</td><td>10점</td></tr>",
            "</table>",
        ],
    )
    a, b = value("채점기준", 4, "ambiguous"), value("채점기준", 4)
    d = decide(rules, pack, "rubric", a, b)
    assert d.result == "사용자판정"  # Rule 2 cannot fix an independent certainty dispute.


def test_task_rubric_with_ae_levels_and_standards_is_preserved(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "## 수행평가 밀도 측정",
            "<table>",
            "<tr><th>교육과정 성취기준</th><th>성취수준</th></tr>",
            "<tr><td>A</td><td>정확한 밀도 계산</td></tr>",
            "<tr><td>평가요소</td><td>배점</td><td>채점 기준</td></tr>",
            "<tr><td>계산</td><td>10점</td><td>단위와 계산 모두 정확함</td></tr>",
            "</table>",
        ],
    )
    v = value("채점 기준", 6)
    transformed, _, _, _, changed = rules.filter_source("rubric", v, pack)
    assert transformed == v and not changed


def test_task_specific_levels_and_performance_levels_stay_a_rubric(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "<table>",
            "<tr><th>평가 영역명</th><th>밀도 실험하기</th></tr>",
            "<tr><td>수행과제</td><td>밀도를 측정하고 해석하기</td></tr>",
            "<tr><td>성취기준</td><td>성취기준별 성취수준</td></tr>",
            "<tr><td>A</td><td>물질을 설명할 수 있다</td></tr>",
            "<tr><td>평가 요소</td><td>수행 수준</td></tr>",
            "<tr><td>실험 수행</td><td>A: 안전하게 측정하고 결과를 정확히 해석함</td></tr>",
            "</table>",
        ],
    )
    assert pack.classify(loc(7))[0] == "rubric"
    assert rules.filter_source("rubric", value("수행 수준", 7), pack)[-1] is False


def test_context_does_not_take_the_next_sections_heading(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "## 수행평가 평가계획",
            "| 평가 방법 | 보고서 |",
            "| 평가 시기 | 4월 |",
            "",
            "## 학기 단위 성취수준",
            "<table>",
            "<tr><td>A</td></tr>",
            "</table>",
        ],
    )
    assert pack.classify(loc(3))[0] == "plan"


def test_rule2_mixed_rubric_removes_only_general_levels(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "## 수행평가 밀도",
            "<table>",
            "<tr><th>평가 준거</th><th>배점</th></tr>",
            "<tr><td>계산</td><td>10</td></tr>",
            "</table>",
            "## 성취기준별 성취수준",
            "<table>",
            "<tr><td>A</td></tr>",
            "</table>",
        ],
    )
    a = value("평가 준거", 3)
    b = value("평가 준거", 3, "ambiguous")
    b["values"].extend(value("성취수준", 8)["values"])
    d = decide(rules, pack, "rubric", a, b)
    assert d.result == "둘다" and d.rules == [2]
    assert all(v["loc"]["line"] == 3 for v in d.value["values"])
    assert d.references[0]["loc"]["line"] == 8


def test_rule3_schedule_method_excluded(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "## 수업·평가 연계표",
            "<table>",
            "<tr><th>시수</th><th>단원명</th><th>수업·평가 연계</th></tr>",
            "<tr><td>4</td><td>열</td><td>관찰평가, 형성평가</td></tr>",
            "</table>",
        ],
    )
    d = decide(rules, pack, "method", value(), value("관찰평가, 형성평가", 4, "ambiguous"))
    assert d.result == "없음(source_absent)" and d.rules == [3]
    assert d.references


def test_rule3_does_not_borrow_a_closed_tables_header(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "<table>",
            "<tr><th>수업·평가 연계</th></tr>",
            "</table>",
            "## 수행평가",
            "<table>",
            "<tr><th>수행평가 평가방법</th></tr>",
            "<tr><td>관찰평가</td></tr>",
            "</table>",
        ],
    )
    assert pack.classify(loc(7))[0] == "plan"
    assert decide(rules, pack, "method", value(), value("관찰평가", 7)).result == "사용자판정"


def test_rule3_mixed_method_excludes_schedule_values_and_options(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "<table>",
            "<tr><th>수행평가 평가방법</th></tr>",
            "<tr><td>보고서</td></tr>",
            "</table>",
            "<table>",
            "<tr><th>시수 누계 단원명</th></tr>",
            "<tr><td>관찰평가</td></tr>",
            "</table>",
        ],
    )
    a, b = value("보고서", 3), value("보고서", 3)
    b["values"].extend(value("관찰평가", 7)["values"])
    b["options"] = [{"text": "관찰평가", "state": "no_box", "loc": loc(7)}]
    b["plain_text"] = "관찰평가"
    d = decide(rules, pack, "method", a, b)
    assert d.result == "둘다" and d.rules == [0, 3]
    assert {v["raw"] for v in d.value["values"]} == {"보고서"}
    assert d.value["options"] == [] and "plain_text" not in d.value
    assert d.references


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("혈액 명함 만들기", "혈액 명암 만들기", "둘다"),
        ("상태변화의 열에너지 탐구하기", "상태 변화와 열에너지 탐구하기", "둘다"),
        ("천체의 운동 구술 평가", "천체의 운동 글쓰기 평가", "충돌보존"),
        ("기체의 성질 탐구하기", "고체의 성질 탐구하기", "충돌보존"),
    ],
)
def test_rule4_spelling_and_semantic_conflict(rules, ordinary_dir, a, b, expected):
    pack = make_pack(rules, ordinary_dir, [a, b, "끝", "끝"])
    d = decide(rules, pack, "title", value(a, 1), value(b, 2, "conflict"))
    assert d.result == expected and d.rules == [4]
    assert {v["raw"] for v in d.value["values"]} == {a, b}
    assert d.status == ("conflict" if expected == "충돌보존" else "present")


def test_rule4_needs_original_evidence(rules, ordinary_dir):
    pack = make_pack(rules, ordinary_dir, ["알 수 없는 원문", "빈칸", "끝", "끝"])
    d = decide(
        rules, pack, "title", value("혈액 명함 만들기", 1), value("혈액 명암 만들기", 2, "conflict")
    )
    assert d.result == "사용자판정" and not d.rules


def test_rule5_schedule_dates_are_references_even_after_rule0(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "<table>",
            "<tr><th>수행평가 평가시기</th></tr>",
            "<tr><td>4월</td></tr>",
            "</table>",
            "<table>",
            "<tr><th>시수</th><th>누계</th><th>단원명</th></tr>",
            "<tr><td>4월 1주 (수행평가)</td></tr>",
            "</table>",
        ],
    )
    a, b = value("4월", 3), value("4월", 3)
    b["values"].extend(value("4월 1주", 7)["values"])
    d = decide(rules, pack, "period", a, b)
    assert d.rules == [0, 5] and d.result == "둘다"
    assert {v["raw"] for v in d.value["values"]} == {"4월"}
    assert d.references[0]["raw"] == "4월 1주"


def test_rule5_partial_application_stays_pending(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "<table>",
            "<tr><th>수행평가 평가시기</th></tr>",
            "<tr><td>4월 5월</td></tr>",
            "</table>",
            "<table>",
            "<tr><th>시수 누계 단원명</th></tr>",
            "<tr><td>3월 (수행평가)</td></tr>",
            "</table>",
        ],
    )
    a, b = value("4월", 3), value("5월", 3)
    b["values"].extend(value("3월", 7)["values"])
    d = decide(rules, pack, "period", a, b)
    assert d.result == "사용자판정" and d.rules == [5] and d.mode == "판단"
    d.question = "Q01"
    cell = rules.envelope(a, b, d)
    assert {v["raw"] for v in cell["B"]["values"]} == {"5월"}
    assert cell["original_B"] == b


def ib_fixture(rules, ordinary_dir):
    pack = make_pack(
        rules,
        ordinary_dir,
        [
            "## 수행평가",
            "<table>",
            "<tr><th>평가기준A</th><th>평가기준B</th></tr>",
            "<tr><td>영역만점 15점</td><td>15점</td></tr>",
            "</table>",
        ],
    )
    merged = item("merged")
    merged["school_id"] = "ms-gold-jeonbuk-gun"
    merged["sub_scores"] = value("15점", 4, norm=15, name="평가기준A")
    merged["sub_scores"]["values"].extend(value("15점", 4, norm=15, name="평가기준B")["values"])
    split = [item("split-a", "평가기준A"), item("split-b", "평가기준B")]
    for it in split:
        it["school_id"] = merged["school_id"]
    return pack, merged, split


def test_rule6_merge_criteria_by_existing_sub_scores_not_item_order(rules, ordinary_dir):
    pack, merged, split = ib_fixture(rules, ordinary_dir)
    groups, evidence = rules.ib_groups([merged], list(reversed(split)), pack)
    assert groups[("B", split[0]["item_key"])] is merged
    assert groups[("B", split[1]["item_key"])] is merged
    assert evidence[("A", merged["item_key"])][0].line == 3
    d = rules.adjudicate(
        row("sub_scores", merged["sub_scores"], value()), merged, split[0], pack, groups, evidence
    )
    assert d.rules == [6] and d.value == merged["sub_scores"]
    assert all(v["norm"] == 15 for v in d.value["values"])  # Never invent a 30-point total.


def test_rule6_missing_table_evidence_does_not_merge(rules, ordinary_dir):
    pack, merged, split = ib_fixture(rules, ordinary_dir)
    (pack.path / "synthetic.md").write_text("무관한 줄\n" * 5, encoding="utf-8")
    assert rules.ib_groups([merged], split, pack)[0] == {}


def test_insufficient_context_is_user_question(rules, ordinary_dir):
    pack = make_pack(rules, ordinary_dir, ["제목 없음", "관찰평가", "끝", "끝"])
    d = decide(rules, pack, "method", value(), value("관찰평가"))
    assert d.result == "사용자판정" and d.rules == []
    assert d.evidence[0].line == 2


def test_phone_method_summary_keeps_raw_alternatives_beside_plain_text(rules):
    v = {**value("구술형"), "plain_text": "구술형", "status": "conflict"}
    v["values"].extend(value("천체 글쓰기 평가", 3)["values"])
    text = rules.human_value("method", v)
    assert "구술형" in text and "천체 글쓰기 평가" in text and "충돌" in text


def test_grouped_answer_uses_each_items_own_alternative(rules, ordinary_dir):
    pack = make_pack(rules, ordinary_dir, ["수행평가", "밀도 측정하기", "끝", "끝"])
    rows, decisions, records = [], {}, []
    for n in range(2):
        a, b = value(), value(f"과제{n}")
        b["values"].extend(value("1. 준비 2. 수행", 3)["values"])
        r = {
            **row("task_text", a, b, f"synthetic-{n}"),
            "학교": "가상중",
            "A항목키": "",
            "B항목키": "",
        }
        rows.append(r)
        decisions[r["불일치ID"]] = rules.Decision()
    questions = rules.question_groups(rows, decisions, {}, {}, pack)
    assert len(questions) == 1 and len(questions[0]["rows"]) == 2
    for r in rows:
        records.append(
            {
                "type": "item",
                "fields": {
                    "task_text": rules.envelope(
                        json.loads(r["A값"]), json.loads(r["B값"]), decisions[r["불일치ID"]]
                    )
                },
            }
        )
    final = rules.apply_answers(records, {"Q01": "B"})
    assert [r["fields"]["task_text"]["value"]["values"][0]["raw"] for r in final] == [
        "과제0",
        "과제1",
    ]


def test_rule6_run_retains_all_split_aliases_and_final_has_one_task(rules, ordinary_dir):
    from gold_diff import COLUMNS

    pack, merged, split = ib_fixture(rules, ordinary_dir)
    paths = [ordinary_dir / f"{side}.jsonl" for side in ("a", "b")]
    for path, rows in zip(paths, ([merged], split), strict=True):
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
        )
    differences, _ = rules.compare_labels([merged], split, pack.path)
    diff_path = ordinary_dir / "diff.csv"
    rules.csv_write(diff_path, differences, COLUMNS)
    answer_path = ordinary_dir / "answers.csv"
    answer_path.write_text("질문번호,답\n", encoding="utf-8-sig")
    out = ordinary_dir / "output"
    summary = rules.run(*paths, diff_path, pack.path, out, answer_path)
    assert summary["remaining_questions"] == 0 and summary["canonical_items"] == 1
    final = [
        json.loads(s) for s in (out / "gold_v1.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(final) == 1
    assert {v["raw"] for v in final[0]["aliases"]} >= {"평가기준A", "평가기준B"}
    assert len(final[0]["merged_inputs"]) == 3


def test_no_generated_raw_numbers_or_source_locations(rules, ordinary_dir):
    pack = make_pack(rules, ordinary_dir, ["혈액 명함 만들기", "혈액 명암 만들기", "끝", "끝"])
    a, b = value("혈액 명함 만들기", 1), value("혈액 명암 만들기", 2)
    originals = copy.deepcopy([a, b])
    d = decide(rules, pack, "title", a, b)
    assert all(v in a["values"] + b["values"] for v in d.value["values"])
    assert [a, b] == originals


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("A", "첫 값"),
        ("B", "둘째 값"),
        ("둘다", "첫 값"),
        ("둘다아님", None),
    ],
)
def test_answers_apply_without_inventing_replacement(rules, answer, expected):
    a, b = value("첫 값"), value("둘째 값")
    decision = rules.Decision(question="Q01")
    records = [{"type": "item", "fields": {"task_text": rules.envelope(a, b, decision)}}]
    final = rules.apply_answers(records, {"Q01": answer})
    cell = final[0]["fields"]["task_text"]
    assert cell["source"] == "사용자:Q01"
    if expected is None:
        assert cell["value"] is None and cell["status"] == "ambiguous"
    else:
        assert cell["value"]["values"][0]["raw"] == expected
    assert records[0]["fields"]["task_text"]["status"] == "pending"


@pytest.mark.parametrize("body", ["Q99,A\n", "Q01,모름\n", "Q01,A\nQ01,B\n", ""])
def test_answers_reject_unknown_duplicate_and_missing(rules, ordinary_dir, body):
    path = ordinary_dir / "answers.csv"
    path.write_text("질문번호,답\n" + body, encoding="utf-8-sig")
    with pytest.raises(ValueError):
        rules.read_answers(path, [{"question": "Q01"}])


def test_cli_outputs_and_answers_only_on_synthetic_data(rules, ordinary_dir):
    pack = make_pack(rules, ordinary_dir, ["## 수행평가", "밀도 측정하기", "설명 쓰기", "끝"])
    a, b = item(), item()
    b["task_text"] = value("설명 쓰기", 3)
    inputs = []
    for name, it in (("a", a), ("b", b)):
        doc = {
            "type": "document",
            "doc_id": "synthetic",
            "school_id": "school",
            "edition": "valid",
            "science_sections": [
                {"grade": 1, "semester": 1, "line_start": 1, "line_end": 4},
            ],
        }
        if name == "b":
            doc["edition"] = "conflict"
        path = ordinary_dir / f"{name}.jsonl"
        path.write_text(
            json.dumps(it, ensure_ascii=False) + "\n" + json.dumps(doc) + "\n", encoding="utf-8"
        )
        inputs.append(path)
    rows, _ = rules.compare_labels(
        [a, json.loads(inputs[0].read_text(encoding="utf-8").splitlines()[1])],
        [b, json.loads(inputs[1].read_text(encoding="utf-8").splitlines()[1])],
        pack.path,
    )
    from gold_diff import COLUMNS

    disagreements = ordinary_dir / "differences.csv"
    rules.csv_write(disagreements, rows, COLUMNS)
    out = ordinary_dir / "output"
    args = [
        sys.executable,
        "-X",
        "utf8",
        str(PROJECT / "scripts/gold_adjudicate.py"),
        *map(str, inputs),
        "--pack-dir",
        str(pack.path),
        "--disagreements",
        str(disagreements),
        "--out-dir",
        str(out),
    ]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == 0, result.stderr
    assert not (out / "gold_v1.jsonl").exists()
    with (out / "queue_v3.csv").open(encoding="utf-8-sig", newline="") as handle:
        queue = list(csv.DictReader(handle))
    assert len(queue) == 2
    md = (out / "queue_v3.md").read_text(encoding="utf-8")
    assert all(len(block.strip().splitlines()) <= 8 for block in md.split("### ")[1:])
    answers = ordinary_dir / "answers.csv"
    answers.write_text(
        "질문번호,답\n" + "".join(f"{q['질문번호']},B\n" for q in queue), encoding="utf-8-sig"
    )
    result = subprocess.run(
        [*args, "--answers", str(answers)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    final = [
        json.loads(s) for s in (out / "gold_v1.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert final[0]["fields"]["task_text"]["value"] == b["task_text"]
    assert final[1]["fields"]["edition"]["value"] == "conflict"
    assert all(not c["source"].startswith("대기:") for r in final for c in r["fields"].values())
    # A stale CSV must be rejected before outputs can be overwritten.
    rows[0]["A값"] = "null"
    rules.csv_write(disagreements, rows, COLUMNS)
    with pytest.raises(ValueError, match="v2"):
        rules.run(*inputs, disagreements, pack.path, out)
