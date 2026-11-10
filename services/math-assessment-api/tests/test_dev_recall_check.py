"""Exercise development-key parsing and recall measurement using isolated SQLite data.

Run .venv/Scripts/python.exe -m pytest -q
    services/math-assessment-api/tests/test_dev_recall_check.py
Verify .venv/Scripts/python.exe -m ruff check scripts/dev_task_key.py
       scripts/dev_recall_check.py services/math-assessment-api/tests/test_dev_recall_check.py
"""

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from scripts import dev_task_key
from scripts.count_astra_card_verdicts import count_verdicts
from scripts.dev_recall_check import check_recall, main, method_set, titles_match
from scripts.dev_task_key import (
    assign_activities,
    expand_task_ids,
    fresh6_evidence,
    fresh6_sources,
    line_ranges,
    read_fresh6_tasks,
    read_tasks,
    resolve_documents,
)

ROUND = "2026-round-3-fresh4"
FRESH6_ROUND = "2026-round-3-nw1"
LEGACY_KEY_SHA256 = "440a0763d043b44f06da1cdf1fe5a9e66b09db075eb0cc474bcf2d0bf4f6e79d"


def task(task_id="T01", title="기체의 압력 탐구하기", **changes):
    result = {
        "task_id": task_id,
        "set": "fresh4",
        "school": "테스트중학교",
        "round": ROUND,
        "grade": 1,
        "semester": 2,
        "title": title,
        "methods_key": [],
        "activity_key": None,
        "activity_accept": [],
        "lines": [[10, 20]],
    }
    return result | changes


def make_database(tmp_path, cards):
    path = tmp_path / "public.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE cases (case_id TEXT PRIMARY KEY, school_name TEXT);
            CREATE TABLE assessment_items (
                item_id TEXT PRIMARY KEY, case_id TEXT, source_round TEXT,
                grade INTEGER, semester INTEGER, title TEXT, method TEXT, extraction_status TEXT,
                locator TEXT
            );
            CREATE TABLE assessment_item_axes (
                item_id TEXT, axis TEXT, value TEXT, rank INTEGER
            );
        """)
        for index, supplied in enumerate(cards):
            card = {
                "school": "테스트중학교",
                "round": ROUND,
                "grade": 1,
                "semester": 2,
                "method": "",
                "activity": "",
                "status": "bounded",
                "locator": {},
            } | supplied
            item_id = f"item-{index}"
            db.execute("INSERT INTO cases VALUES (?, ?)", (item_id, card["school"]))
            db.execute(
                "INSERT INTO assessment_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item_id,
                    item_id,
                    card["round"],
                    card["grade"],
                    card["semester"],
                    card["title"],
                    card["method"],
                    card["status"],
                    json.dumps(card["locator"]),
                ),
            )
            if card["activity"]:
                db.execute(
                    "INSERT INTO assessment_item_axes VALUES (?, 'activity', ?, 1)",
                    (item_id, card["activity"]),
                )
    return path


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("ABC 기체, 압력!<br>탐구", "abc기체압력탐구", True),
        ("기체의 압력 탐구하기", "기체의 압력 탐구하기 및 보고서 작성", True),
        ("보고서 작성 및 기체의 압력 탐구하기", "기체의 압력 탐구하기", True),
        ("기체 압력", "기체 압력 탐구하기", False),
        ("기체 압력 탐구하기", "기체 압력", False),
        ("가나다라마바", "추가 가나다라마바 제목", True),
        ("가나다라마", "추가 가나다라마 제목", False),
        ("발표", "발표", True),
        ("...<br/>", "", False),
    ],
)
def test_title_normalization_and_inclusion(left, right, expected):
    assert titles_match(left, right) is expected


def test_matching_scopes_public_filter_and_unmatched_lists(tmp_path):
    tasks = [task(), task("T02", "태양계의 특징 설명하기"), task("T03", "압력")]
    cards = [
        {"title": "기체의 압력 탐구하기"},
        {"title": "태양계의 특징 설명하기 및 결과 발표하기"},
        {"title": "압력에 대한 관찰 및 설명하기"},
        {"title": tasks[0]["title"], "school": "다른중학교"},
        {"title": tasks[0]["title"], "grade": 2},
        {"title": tasks[0]["title"], "semester": 1},
        {"title": tasks[0]["title"], "round": "outside-key"},
        {"title": tasks[0]["title"], "status": "excluded"},
    ]
    database = make_database(tmp_path, cards)
    result = check_recall(database, tasks)
    assert result["recall"]["fresh4"] == {"numerator": 2, "denominator": 3, "rate": 2 / 3}
    assert [t["task_id"] for t in result["unmatched_tasks"]] == ["T03"]
    assert len(result["public_card_ids"]) == 6
    assert len(result["unmatched_cards"]) == 4
    assert {c["match_basis"] for c in result["card_verdicts"] if c["task_ids"]} == {"title"}
    assert result["duplicate_cards"] == []
    for card in result["unmatched_cards"]:
        assert card["verdicts"]["수행평가 과제"] == "미판정"
        assert card["verdicts"]["제목"] == "미판정"
        assert all(str(card[k]) in card["notes"] for k in ("school", "round", "title"))


def test_combined_card_covers_three_tasks_and_duplicates_are_separate(tmp_path):
    tasks = [
        task("T01", "기체의 압력 탐구하기"),
        task("T02", "태양계의 특징 설명하기"),
        task("T03", "여러 가지 힘의 원리 설명하기"),
    ]
    tasks[0].update(activity_key="탐구", activity_accept=["탐구"], methods_key=["프로젝트"])
    database = make_database(
        tmp_path,
        [
            {"title": " / ".join(t["title"] for t in tasks)},
            {"title": tasks[0]["title"]},
        ],
    )
    result = check_recall(database, tasks)
    assert result["recall"]["total"]["numerator"] == 3
    assert result["recall"]["total"]["denominator"] == 3
    assert len(result["combined_cards"]) == 1
    combined = result["combined_cards"][0]
    assert combined["task_ids"] == ["T01", "T02", "T03"]
    assert combined["verdicts"]["활동"] == combined["verdicts"]["방법"] == "-"
    assert len(result["duplicate_cards"]) == 1
    assert result["duplicate_cards"][0]["task"]["task_id"] == "T01"
    assert len(result["duplicate_cards"][0]["item_ids"]) == 2


@pytest.mark.parametrize("separator", [", ", " · "])
def test_method_normalization_and_boundary_acceptance(tmp_path, separator):
    key = [
        task(
            methods_key=["서술·논술", "실험･실습"],
            activity_key="추론·설명",
            activity_accept=["추론·설명", "발표·토론"],
        )
    ]
    database = make_database(
        tmp_path,
        [
            {
                "title": key[0]["title"],
                "method": separator.join(["서·논술", "실험·실습평가"]),
                "activity": "presentation",
            }
        ],
    )
    result = check_recall(database, key)
    verdict = result["card_verdicts"][0]["verdicts"]
    assert verdict["활동"] == verdict["방법"] == "맞음"
    assert method_set(["실험ㆍ실습", "실험・실습", "실험‧실습", "실험⋅실습"]) == {"실험·실습"}


def test_missing_wrong_and_excluded_verdicts(tmp_path):
    tasks = [
        task(
            "T01",
            "첫 번째 과제 제목",
            methods_key=["논술"],
            activity_key="작성",
            activity_accept=["작성"],
        ),
        task(
            "T02",
            "두 번째 과제 제목",
            methods_key=["논술"],
            activity_key="작성",
            activity_accept=["작성"],
        ),
        task("T03", "세 번째 과제 제목", methods_key=None),
    ]
    database = make_database(
        tmp_path,
        [
            {"title": tasks[0]["title"]},
            {"title": tasks[1]["title"], "method": "구술", "activity": "inquiry"},
            {"title": tasks[2]["title"]},
        ],
    )
    result = check_recall(database, tasks)
    by_task = {c["task_ids"][0]: c for c in result["card_verdicts"]}
    for field in ("활동", "방법"):
        assert by_task["T01"]["verdicts"][field] == "빈칸"
        assert by_task["T02"]["verdicts"][field] == "틀림"
        assert by_task["T03"]["verdicts"][field] == "-"
    assert "논술" in by_task["T02"]["notes"] and "구술" in by_task["T02"]["notes"]


def test_cli_outputs_countable_table_and_filters_rounds(tmp_path, capsys):
    tasks = [task(), task("P01", "다른 회차의 과제", set="fresh3", round="2026-round-1-fresh3")]
    key = tmp_path / "key.json"
    key.write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")
    database = make_database(tmp_path, [{"title": tasks[0]["title"]}])
    original_hash = hashlib.sha256(database.read_bytes()).hexdigest()
    prefix = tmp_path / "nested" / "recall"
    assert (
        main(
            [
                "--database",
                str(database),
                "--key",
                str(key),
                "--out-prefix",
                str(prefix),
                "--rounds",
                ROUND,
            ]
        )
        == 0
    )
    report = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    markdown = (prefix.parent / "recall-verdicts.md").read_text(encoding="utf-8")
    assert count_verdicts(markdown) == report["verdict_counts"]
    assert report["verdict_counts"]["cards"] == 1
    assert "| E01 |" in markdown
    assert report["recall"]["fresh4"]["denominator"] == 1
    assert report["recall"]["fresh3"]["denominator"] == 0
    assert report["unmatched_tasks"] == []
    assert report["database_sha256_16"] == original_hash[:16]
    assert hashlib.sha256(database.read_bytes()).hexdigest() == original_hash
    assert json.loads(capsys.readouterr().out)["public_card_ids"] == 1
    assert check_recall(database, tasks) == check_recall(database, tasks)
    with pytest.raises(ValueError, match="rounds present"):
        check_recall(database, tasks, ["unknown-round"])


def test_task_key_parses_headings_methods_and_ranges():
    markdown = """### 1절 원문 과제 목록
#### 가중학교 `2026-round-3-fresh4`
| 학년 | 학기 | 과제 제목(원문 그대로) | 만점·비율 | 체크된 평가 방법 | 성취기준 코드 | 근거(줄) |
|---|---|---|---|---|---|---|
| 1 | 2 | 첫 과제 | 100 | 논술, 실험･실습 | 코드 | T01 · 1~2 |
| 1 | 2 | 긴 방법 | 100 | 탐구실험의절차와방법에맞춰설계하고결론을서술하기 | 코드 | T02 · 3 |
#### 나중학교 2026-round-1-fresh3
| 학년 | 학기 | 과제 제목(원문 그대로) | 만점·비율 | 체크된 평가 방법 | 성취기준 코드 | 근거(줄) |
|---|---|---|---|---|---|---|
| 2 | 1 | 셋째 과제 | 100 | 포트폴리오 | 코드 | P01: 4–5 |
"""
    tasks = read_tasks(markdown, "fresh4")
    assert tasks[0]["school"] == "가중학교"
    assert tasks[0]["round"] == ROUND
    assert tasks[0]["methods_key"] == ["논술", "실험･실습"]
    assert tasks[1]["methods_key"] is None
    assert tasks[2]["round"] == "2026-round-1-fresh3"
    assert tasks[0]["lines"] == [[1, 2]]
    assert tasks[2]["lines"] == [[4, 5]]
    assert line_ranges("1, 4~5, 7–8, 10-11") == [[1, 1], [4, 5], [7, 8], [10, 11]]
    assert expand_task_ids("T01~T04, T08~T11") == [
        "T01",
        "T02",
        "T03",
        "T04",
        "T08",
        "T09",
        "T10",
        "T11",
    ]


def test_activity_key_verdict_rules_and_combined_exclusion():
    verdicts = [
        {"카드": "D01", "활동": "맞음", "1절 과제(짝)": "T01", "메모": ""},
        {"카드": "D02", "활동": "틀림", "1절 과제(짝)": "T02", "메모": "**작성** **분석**"},
        {"카드": "D03", "활동": "경계", "1절 과제(짝)": "T03", "메모": "**추론·설명**"},
        {"카드": "D04", "활동": "빈칸", "1절 과제(짝)": "T04", "메모": "**작성**"},
        {"카드": "D05", "활동": "빈칸", "1절 과제(짝)": "T05", "메모": "근거 없음"},
        {"카드": "D06", "활동": "맞음", "1절 과제(짝)": "T06~T08", "메모": ""},
    ]
    screens = {v["카드"]: {"주활동": "발표·토론"} for v in verdicts}
    tasks = [task(f"T{i:02d}") for i in range(1, 9)]
    assign_activities(tasks, verdicts, screens, ["발표·토론", "작성", "분석", "추론·설명"])
    assert [t["activity_key"] for t in tasks] == [
        "발표·토론",
        "작성",
        "발표·토론",
        "작성",
        None,
        None,
        None,
        None,
    ]
    assert tasks[2]["activity_accept"] == ["발표·토론", "추론·설명"]


def located_task(task_id, title, line_numbers, digest="text-hash", **changes):
    return task(
        task_id, title, doc={"doc_sha256": digest},
        spans=[{"line": number, "start": number * 10, "end": number * 10 + 8}
               for number in line_numbers], **changes,
    )


def test_unique_position_overrides_title_and_can_cover_multiple_tasks(tmp_path):
    tasks = [located_task("T01", "개요표 이름", [1, 3]),
             located_task("T02", "세부표 과제 문장", [1, 5])]
    database = make_database(tmp_path, [
        {"title": tasks[1]["title"], "locator": {"sha256": "text-hash", "start": 31, "end": 38}},
        {"title": "제목으로는 찾을 수 없음",
         "locator": {"sha256": "text-hash", "start": 31, "end": 58}},
    ])
    by_item = {c["item_id"]: c for c in check_recall(database, tasks)["card_verdicts"]}
    assert by_item["item-0"]["task_ids"] == ["T01"]
    # 여러 과제 고유 위치와 겹치고 제목이 안 맞으면 가장 많이 겹친 과제 하나(S20).
    assert len(by_item["item-1"]["task_ids"]) == 1
    assert {c["match_basis"] for c in by_item.values()} == {"position_unique"}


def test_unique_positions_with_titles_keep_combined_card(tmp_path):
    tasks = [located_task("T01", "첫 번째 과제 문장", [1, 3]),
             located_task("T02", "두 번째 과제 문장", [5])]
    database = make_database(tmp_path, [
        {"title": "첫 번째 과제 문장 두 번째 과제 문장",
         "locator": {"sha256": "text-hash", "start": 0, "end": 60}},
    ])
    card = check_recall(database, tasks)["card_verdicts"][0]
    assert card["task_ids"] == ["T01", "T02"]


def test_shared_position_requires_title_and_limits_candidates(tmp_path):
    tasks = [located_task("T01", "첫 번째 과제 문장", [1, 3]),
             located_task("T02", "두 번째 과제 문장", [1, 5]),
             located_task("T03", "첫 번째 과제 문장", [7])]
    database = make_database(tmp_path, [
        {"title": tasks[0]["title"], "locator": {"sha256": "text-hash", "start": 10, "end": 18}},
        {"title": "제목이 다름", "locator": {"sha256": "text-hash", "start": 10, "end": 18}},
    ])
    by_item = {c["item_id"]: c for c in check_recall(database, tasks)["card_verdicts"]}
    assert by_item["item-0"]["task_ids"] == ["T01"]
    assert by_item["item-0"]["match_basis"] == "position_shared_title"
    assert by_item["item-1"]["task_ids"] == []


@pytest.mark.parametrize("locator", [
    {"sha256": "other-document", "start": 30, "end": 38},
    {"sha256": "text-hash", "start": 22, "end": 30},
    {"sha256": "text-hash", "start": 38, "end": 45},
    {"sha256": "text-hash", "start": 30, "end": 30},
    {"sha256": "text-hash", "start": 30, "end": 38, "offset_unit": "byte"},
    {}, "invalid JSON",
])
def test_nonoverlap_wrong_hash_and_invalid_locators_fall_back_to_title(tmp_path, locator):
    tasks = [located_task("T01", "과제의 개요표 이름", [3]), task("T02", "카드의 과제 제목")]
    database = make_database(tmp_path, [{"title": tasks[1]["title"], "locator": locator}])
    card = check_recall(database, tasks)["card_verdicts"][0]
    assert card["task_ids"] == ["T02"]
    assert card["match_basis"] == "title"


def test_line_shared_with_other_grade_cannot_be_a_unique_position(tmp_path):
    tasks = [located_task("T01", "다른 이름", [3]),
             located_task("T02", "다른 학년 과제", [3], grade=2)]
    database = make_database(tmp_path, [{
        "title": "일치하지 않는 제목", "locator": {"sha256": "text-hash", "start": 30, "end": 38},
    }])
    assert check_recall(database, tasks)["card_verdicts"][0]["task_ids"] == []


@pytest.mark.parametrize("matching_documents", [0, 1, 2])
def test_document_resolution_requires_one_title_near_evidence(tmp_path, matching_documents):
    folder = tmp_path / "data/derived/segments"
    folder.mkdir(parents=True)
    documents = []
    texts = ["😀\n첫째\n근거 줄\n여유 줄\n과제 제목\n마지막\n"] * matching_documents
    texts += ["다른 문서\n제목 없음"]
    for index, text in enumerate(texts):
        path = f"data/derived/segments/{ROUND}-{index}.json"
        (tmp_path / path).write_text(json.dumps({"text": text}), encoding="utf-8")
        documents.append({"source": {"school_name": "테스트중학교"}, "converted_path": path})
    (folder / f"{ROUND}.json").write_text(json.dumps({"documents": documents}), encoding="utf-8")
    tasks = [task(title="과제 제목", lines=[[1, 1], [3, 3]])]
    resolve_documents(tasks, tmp_path)
    if matching_documents == 1:
        assert tasks[0]["doc"]["doc_sha256"] == hashlib.sha256(texts[0].encode()).hexdigest()
        assert tasks[0]["doc"]["converted_path"] == documents[0]["converted_path"]
        assert tasks[0]["spans"] == [
            {"line": 1, "start": 0, "end": 1}, {"line": 3, "start": 5, "end": 9},
        ]
        assert tasks[0]["doc_reason"] is None
    else:
        assert tasks[0]["doc"] is None
        assert tasks[0]["spans"] == []
        assert tasks[0]["doc_reason"] == (
            "no_title_near_lines" if matching_documents == 0 else "multiple_documents"
        )


@pytest.mark.parametrize(
    ("evidence", "expected_lines", "multiple"),
    [
        ("01234567:1–2,4-4", [[1, 2], [4, 4]], False),
        ("01234567:1-2,4–4", [[1, 2], [4, 4]], False),
        ("01234567:1–2; 89abcdef:3-4,5", [[1, 2], [3, 4], [5, 5]], True),
    ],
)
@pytest.mark.parametrize(
    "methods", ["서술·논술,실험･실습, 구술·발표", "서술·논술 · 실험･실습 ㆍ 구술·발표"],
)
def test_fresh6_document_evidence_methods_and_spans(tmp_path, evidence, expected_lines,
                                                  multiple, methods):
    text = "😀\n첫 과제\n공통\n끝\n"
    paths = [f"data/derived/segments/{FRESH6_ROUND}-conversions/{prefix}.json"
             for prefix in ("01234567", "89abcdef")]
    sources_md = f"## 테스트중학교 `{FRESH6_ROUND}`\n"
    for path in paths:
        converted = tmp_path / path
        converted.parent.mkdir(parents=True, exist_ok=True)
        converted.write_text(json.dumps({"text": text, "sha256": Path(path).stem}),
                             encoding="utf-8")
        sources_md += f"- `{path}` · 파일 `과학.pdf`\n"
    markdown = f"""### 1절 원문 과제 목록
#### 테스트중학교 {FRESH6_ROUND}
| 학년 | 학기 | 과제 제목(원문 그대로) | 체크된 평가 방법 | 근거(줄) |
|---|---|---|---|---|
| 1 | 2 | 첫 과제 | {methods} | {evidence} |
### 2절 카드 판정
#### 다른학교 {FRESH6_ROUND}
| 학년 | 학기 | 과제 제목(원문 그대로) | 체크된 평가 방법 | 근거(줄) |
|---|---|---|---|---|
| 2 | 2 | 키에 들어가면 안 됨 | 발표 | 잘못된 근거 |
"""
    tasks = read_fresh6_tasks(markdown, fresh6_sources(sources_md), tmp_path)
    assert len(tasks) == 1
    parsed = tasks[0]
    assert parsed["task_id"] == "F6-01" and parsed["set"] == "fresh6"
    assert (parsed["school"], parsed["round"]) == ("테스트중학교", FRESH6_ROUND)
    assert (parsed["grade"], parsed["semester"], parsed["title"]) == (1, 2, "첫 과제")
    assert parsed["activity_key"] is None
    assert parsed["methods_key"] == ["서술·논술", "실험･실습", "구술·발표"]
    assert parsed["lines"] == expected_lines
    if multiple:
        assert parsed["doc"] is None and parsed["doc_reason"] == "multiple_documents"
        assert parsed["spans"] == []
    else:
        assert parsed["doc"]["doc_sha256"] == hashlib.sha256(text.encode()).hexdigest()
        assert parsed["doc"]["locator_sha256"] == "01234567"
        assert parsed["doc"]["converted_path"] == paths[0]
        assert parsed["doc_reason"] is None
        assert parsed["spans"] == [
            {"line": 1, "start": 0, "end": 1},
            {"line": 2, "start": 2, "end": 6},
            {"line": 4, "start": 10, "end": 11},
        ]


@pytest.mark.parametrize("evidence", ["01234567:0-2", "01234567:3–2", "no-prefix:1-2"])
def test_fresh6_rejects_invalid_evidence(evidence):
    with pytest.raises(ValueError):
        fresh6_evidence(evidence)


def test_cli_schools_filter_applies_to_tasks_and_cards(tmp_path, capsys):
    tasks = [task(), task("T02", school="다른중학교")]
    database = make_database(tmp_path, [
        {"title": tasks[0]["title"]},
        {"title": tasks[1]["title"], "school": "다른중학교"},
        {"title": "키에 없는 학교 카드", "school": "키없는중학교"},
    ])
    key = tmp_path / "key.json"
    key.write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")
    prefix = tmp_path / "schools"
    assert main(["--database", str(database), "--key", str(key), "--out-prefix", str(prefix),
                 "--rounds", ROUND, "--schools", "테스트중학교"]) == 0
    report = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8"))
    assert report["recall"]["total"] == {"numerator": 1, "denominator": 1, "rate": 1}
    assert report["public_card_ids"] == ["item-0"]
    assert report["unmatched_tasks"] == report["unmatched_cards"] == []
    assert report["card_verdicts"][0]["card"] == "E01"
    assert json.loads(capsys.readouterr().out)["public_card_ids"] == 1
    assert len(check_recall(database, tasks)["public_card_ids"]) == 3
    for schools in ([], ["없는학교"], ["테스트중학교", "없는학교"]):
        with pytest.raises(ValueError, match="schools present"):
            check_recall(database, tasks, schools=schools)


def test_fresh6_cli_builds_28_tasks_without_legacy_gold_reads(tmp_path, monkeypatch, capsys):
    original_read = Path.read_text

    def read_allowed(path, *args, **kwargs):
        if path.parent.name == "gold":
            assert path == dev_task_key.ROOT / dev_task_key.FRESH6_QUALITY or (
                path == dev_task_key.ROOT / dev_task_key.FRESH6_SOURCES
            )
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_allowed)
    output = tmp_path / "fresh6.json"
    assert dev_task_key.main(["--set", "fresh6", "--out", str(output)]) == 0
    tasks = json.loads(output.read_text(encoding="utf-8"))
    assert [t["task_id"] for t in tasks] == [f"F6-{number:02d}" for number in range(1, 29)]
    assert all(t["set"] == "fresh6" and t["activity_key"] is None for t in tasks)
    assert sum(t["doc"] is None for t in tasks) == 4
    assert json.loads(capsys.readouterr().out)["fresh6"]["tasks"] == 28


def test_legacy_cli_preserves_saved_77_task_bytes(tmp_path, monkeypatch, capsys):
    """Exercise legacy CLI serialization; original gold Markdown must not be read here."""
    original = dev_task_key.OUTPUT.read_bytes()
    assert hashlib.sha256(original).hexdigest() == LEGACY_KEY_SHA256
    saved_tasks = json.loads(original)
    assert len(saved_tasks) == 77
    monkeypatch.setattr(dev_task_key, "build_key", lambda: saved_tasks)
    output = tmp_path / "legacy-key.json"
    assert dev_task_key.main(["--out", str(output)]) == 0
    assert output.read_bytes() == original
    assert dev_task_key.OUTPUT.read_bytes() == original
    assert json.loads(capsys.readouterr().out)["total"]["tasks"] == 77
