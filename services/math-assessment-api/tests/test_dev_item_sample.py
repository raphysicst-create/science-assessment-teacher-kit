"""임시 폴더의 합성 report·subjects·segments·conversion으로 표본기를 검사한다.

Run/Verify: .venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
            services/math-assessment-api/tests/test_dev_item_sample.py
실데이터를 읽지 않는다. read의 기준 폴더와 판본 선택 입력을 합성 자료로 격리한다.
"""

import copy
import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import compare_middle_s6d2e as editions  # noqa: E402
from scripts import dev_item_sample as sampler  # noqa: E402

ROUND = "synthetic-round"
SEED = 2026111001


def write_json(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8-sig")


def synthetic_item(document, number, grade, semester, status="bounded", role="performance"):
    return {
        "item_id": f"item-{number}-{grade}-{semester}-{status}-{role}",
        **{key: document[key] for key in ("school", "converted_path", "original_path", "filename")},
        "grade": grade,
        "semester": semester,
        "extraction_status": status,
        "candidate_role": role,
        "layout_position": {"table": 0, "row": 1},
        "title_role": "task",
        "shared_fields": [],
        "owned_ranges": [],
        "links": [],
        "fields": {
            name: {"value": f"합성 {name}", "evidence": []} for name in sampler.prior.SAMPLE_FIELDS
        },
    }


def synthetic_school(number):
    document = {
        "school": f"합성학교{number}",
        "converted_path": f"conversions/doc-{number}.json",
        "original_path": f"originals/doc-{number}.pdf",
        "filename": f"문서{number}.pdf",
        "document_id": f"doc-{number}",
        "child_id": None,
        "grades": [1, 2],
        "development_selected": True,
        "status": "converted",
    }
    sections, segments, items = [], [], []
    for grade in (1, 2):
        for semester in (1, 2):
            segment_id = f"seg-{number}-{grade}-{semester}"
            segments.append(
                {
                    "segment_id": segment_id,
                    "semester": semester,
                    "semester_evidence": [{"text": f"{semester}학기", "source": "filename"}],
                }
            )
            sections.append(
                {
                    "section_id": segment_id,
                    "segment_id": segment_id,
                    "school": document["school"],
                    "grade": grade,
                    "status": "target",
                    "converted_path": document["converted_path"],
                    "locator": {"start": 4, "end": 10},
                    "boundary_verified": True,
                }
            )
            for status, role in (
                ("bounded", "performance"),
                ("ai_verified", "performance"),
                ("review", "performance"),
                ("bounded", "teaching_plan"),
            ):
                items.append(synthetic_item(document, number, grade, semester, status, role))
        items.append(synthetic_item(document, number, grade, None))
    segment_document = {
        "converted_path": document["converted_path"],
        "segments": segments,
        "edition": {"selected": True},
    }
    return document, sections, segment_document, items


@pytest.fixture
def synthetic_report(tmp_path, monkeypatch):
    documents, items, sections, segment_documents = [], [], [], []
    for number in range(4):
        document, school_sections, segment_document, school_items = synthetic_school(number)
        documents.append(document)
        sections.extend(school_sections)
        items.extend(school_items)
        segment_documents.append(segment_document)
        write_json(tmp_path, document["converted_path"], {"text": "첫 줄\n과학 평가\n끝 줄\n"})
    previous = dict(
        documents[0], converted_path="conversions/previous.json", development_selected=False
    )
    documents.append(previous)
    items.append(synthetic_item(previous, "previous", 1, 1))
    segment_documents.append(
        {
            "converted_path": previous["converted_path"],
            "segments": [],
            "edition": {"selected": False},
        }
    )
    documents.append(dict(previous, school="비선정학교", converted_path="conversions/unused.json"))
    segment_documents.append(
        {
            "converted_path": "conversions/unused.json",
            "segments": [],
            "edition": {"selected": False},
        }
    )
    report = {"round": ROUND, "documents": documents, "items": items}
    write_json(tmp_path, f"data/derived/items/{ROUND}.json", report)
    write_json(tmp_path, f"data/derived/subjects/{ROUND}.json", {"sections": sections})
    write_json(tmp_path, f"data/derived/segments/{ROUND}.json", {"documents": segment_documents})
    monkeypatch.setattr(sampler.prior, "ROOT", tmp_path)

    def select_synthetic_editions(rows):
        for row in rows:
            row["development_selected"] = row["edition"]["selected"]

    monkeypatch.setattr(editions, "select_editions", select_synthetic_editions)
    return report


def cell_keys(result):
    return [tuple(cell[key] for key in sampler.CELL_FIELDS) for cell in result["source_review"]]


def test_deterministic_sampling_sorted_population_and_school_times_four(synthetic_report):
    result = sampler.sample(synthetic_report, SEED, size=8)
    assert result == sampler.sample(synthetic_report, SEED, size=8)
    assert cell_keys(result) != cell_keys(sampler.sample(synthetic_report, SEED + 1, size=8))
    assert result["population_size"] == 4 * 4
    assert result["sample_size"] == 8
    population = [
        (ROUND, f"합성학교{number}", grade, semester)
        for number in range(4)
        for grade in (1, 2)
        for semester in (1, 2)
    ]
    assert cell_keys(result) == random.Random(SEED).sample(sorted(population), 8)
    assert all(cell[1] != "비선정학교" for cell in cell_keys(result))


def test_exclusion_deduplicates_and_counts_only_population_cells(tmp_path, synthetic_report):
    first = sampler.sample(synthetic_report, SEED, size=8)
    write_json(tmp_path, "previous.json", first)
    excluded = sampler.excluded_cells([tmp_path / "previous.json", tmp_path / "previous.json"])
    excluded.add(("another-round", "합성학교0", 1, 1))
    next_sample = sampler.sample(synthetic_report, SEED, size=16, excluded=excluded)
    assert not set(cell_keys(first)) & set(cell_keys(next_sample))
    assert next_sample["population_size"] == next_sample["sample_size"] == 8
    assert next_sample["excluded_cell_count"] == 8


def test_source_ranges_and_representative_pipeline_filters(synthetic_report):
    before = copy.deepcopy(synthetic_report)
    result = sampler.sample(synthetic_report, SEED)
    assert synthetic_report == before
    for cell, comparison in zip(
        result["source_review"], result["pipeline_comparison"], strict=True
    ):
        assert cell["cell_id"] == comparison["cell_id"]
        assert len(cell["source_documents"]) == 1
        assert cell["reviewer_items"] == []
        assert len(cell["science_ranges"]) == 1
        source = cell["science_ranges"][0]
        assert (source["line_start"], source["line_end"]) == (2, 2)
        assert source["semester"] == cell["semester"]
        assert source["semester_evidence"][0]["text"] == f"{cell['semester']}학기"
        items = comparison["bounded_items"]
        assert {item["extraction_status"] for item in items} == {"bounded", "ai_verified"}
        assert len(items) == 2
        assert all(
            item["candidate_role"] == "performance" and item["semester"] == cell["semester"]
            for item in items
        )
        assert len(comparison["semester_unresolved_bounded_items"]) == 1


def test_cli_writes_matching_format_and_one_source_heading_per_cell(tmp_path, synthetic_report):
    prefix = tmp_path / "output/sample"
    args = ["--seed", str(SEED), "--round", ROUND, "--size", "5", "--out-prefix", str(prefix)]
    assert sampler.main(args) == 0
    result = json.loads(
        (tmp_path / "output/sample-review-sample.json").read_text(encoding="utf-8-sig")
    )
    md = (tmp_path / "output/sample-review-sample.md").read_text(encoding="utf-8-sig")
    assert md.count("### S") == result["sample_size"] == 5
    assert f"seed={SEED}, 모집단 16칸 중 5칸 단순무작위 추출. 이전 표본 제외 0칸." in md
    assert md.index("## 1. 원문만 보고 독립 목록 작성") < md.index("## 2. 파이프라인 bounded 목록")
    assert "| 제목 | 번호 | 만점 | 비율 | 시기 | 성취기준 | 근거 |" in md
    assert "학기 근거" in md and "과학 구간 2–2줄" in md
    assert "제목=합성 title" in md and "성취기준=합성 standards" in md
    assert sampler.main(args + ["--exclude", str(prefix) + "-review-sample.json"]) == 0
    following = json.loads(
        (tmp_path / "output/sample-review-sample.json").read_text(encoding="utf-8-sig")
    )
    assert following["excluded_cell_count"] == 5
    assert not set(cell_keys(result)) & set(cell_keys(following))


def test_small_empty_and_fully_excluded_populations(synthetic_report):
    whole = sampler.sample(synthetic_report, SEED, size=100)
    assert whole["sample_size"] == whole["population_size"] == 16
    empty = sampler.sample(synthetic_report, SEED, excluded=set(cell_keys(whole)))
    assert empty["sample_size"] == empty["population_size"] == 0
    assert empty["excluded_cell_count"] == 16
    assert sampler.sample(synthetic_report, SEED, size=0)["sample_size"] == 0


@pytest.mark.parametrize(
    "option,value",
    [
        ("--round", "GOLD-round"),
        ("--out-prefix", "gold-output"),
        ("--exclude", "previous-gold.json"),
    ],
)
def test_rejects_blind_paths_before_reading(tmp_path, monkeypatch, option, value, capsys):
    def forbidden_read(path):
        pytest.fail(f"가드 이전 읽기: {path}")

    monkeypatch.setattr(sampler.prior, "read", forbidden_read)
    args = ["--seed", str(SEED), "--out-prefix", str(tmp_path / "output")]
    assert sampler.main(args + [option, value]) == 2
    assert "gold 경로 거부" in capsys.readouterr().err


def test_nested_conversion_path_is_guarded(synthetic_report, tmp_path):
    report = copy.deepcopy(synthetic_report)
    report["documents"][0]["converted_path"] = "gold-conversion.json"
    # 원문 범위가 참조하는 경로까지 같은 합성 입력으로 바꾼다.
    path = tmp_path / f"data/derived/subjects/{ROUND}.json"
    subjects = json.loads(path.read_text(encoding="utf-8-sig"))
    for section in subjects["sections"]:
        if section["school"] == "합성학교0":
            section["converted_path"] = "gold-conversion.json"
    write_json(tmp_path, f"data/derived/subjects/{ROUND}.json", subjects)
    with pytest.raises(ValueError, match="gold 경로 거부"):
        sampler.prior.source_ranges(report, 1, 1, "합성학교0", reader=sampler.read)


def test_negative_size_is_input_error(tmp_path, synthetic_report, capsys):
    assert (
        sampler.main(
            [
                "--seed",
                str(SEED),
                "--round",
                ROUND,
                "--size",
                "-1",
                "--out-prefix",
                str(tmp_path / "output"),
            ]
        )
        == 2
    )
    assert "size" in capsys.readouterr().err
