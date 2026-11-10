"""Build deterministic nationwide middle-school rosters from saved source data.

Run .venv/Scripts/python.exe scripts/build_nationwide_roster.py build (or counts).
Verify with .venv/Scripts/python.exe -m pytest -q -k nationwide_roster.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ROSTER_DIR = Path("data/roster")
RAW_SOURCE = ROSTER_DIR / "raw/schoolinfo-search-middle-2026-11-10.json"
MCP_SOURCE = ROSTER_DIR / "raw/mcp-search-school-bundle1-2026-11-10.json"
NATIONWIDE_CSV = ROSTER_DIR / "nationwide-middle-2026-11-10.csv"
BUNDLES = {
    1: ["세종특별자치시", "제주특별자치도"],
    2: ["울산광역시", "대전광역시"],
    3: ["강원특별자치도", "충청북도", "충청남도", "전북특별자치도"],
    4: ["부산광역시", "대구광역시", "인천광역시"],
    5: ["전남광주통합특별시", "경상북도", "경상남도"],
    6: ["서울특별시", "경기도"],
}
SIDO_ALIASES = {"광주광역시": "전남광주통합특별시", "전라남도": "전남광주통합특별시"}
PUBLISHED_SAMPLE_SETS = {
    1: frozenset({"dev2-20", "gold10", "gold2-5", "fresh3", "fresh4", "fresh5"}),
    3: frozenset({"dev2-20", "gold10", "gold2-5", "fresh3", "fresh4", "fresh5", "dev12"}),
}
NATIONWIDE_FIELDS = (
    "bundle", "sido", "sgg", "school_name", "school_code", "shl_idf_cd", "founding",
    "sample_sets", "published_rounds", "excluded_reason",
)
ROUND_FIELDS = (
    "school_id", "school_name", "region_sido", "region_sgg", "school_code",
    "neis_school_code", "education_office_code", "school_kind", "shl_idf_cd",
)
COUNTS_HEADER = (
    "| 묶음 | 시도 | 학교 | 분교 제외 | 이미 공개(회차1/회차3) | "
    "묶음 회차1 대상 | 묶음 회차3 대상 |",
    "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
)


def compact_name(value: str) -> str:
    return "".join(value.split())


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        reader.fieldnames = [name.removeprefix("\ufeff") for name in reader.fieldnames or []]
        return list(reader)


def csv_text(fields: tuple[str, ...], rows: list[dict[str, str]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def load_middle_rows(root: Path) -> list[dict[str, str]]:
    source = json.loads((root / RAW_SOURCE).read_text(encoding="utf-8"))
    assignments = {sido: bundle for bundle, sidos in BUNDLES.items() for sido in sidos}
    rows = []
    codes, identifiers = set(), set()
    for raw in source["rows"]:
        if raw.get("SCHUL_KIND") != "03":
            continue
        sido = raw["USER_DFN_CODE_VALUE_01"].strip()
        if sido not in assignments:
            raise ValueError(f"unassigned sido: {sido}")
        code, identifier = raw["SHL_CD"].strip(), raw["SHL_IDF_CD"].strip()
        if not code or not identifier or code in codes or identifier in identifiers:
            raise ValueError(f"missing or duplicate school identity: {code}")
        codes.add(code)
        identifiers.add(identifier)
        name = raw["SHL_NM"].strip()
        rows.append({
            "bundle": str(assignments[sido]), "sido": sido,
            "sgg": (raw.get("USER_DFN_CODE_VALUE_02") or "").strip() or sido,
            "school_name": name, "school_code": code, "shl_idf_cd": identifier,
            "founding": (raw.get("FOND_SC_NM") or "").strip(),
            "sample_sets": "", "published_rounds": "",
            "excluded_reason": "branch_campus" if "분교" in name else "",
        })
    return sorted(rows, key=lambda row: (
        int(row["bundle"]), row["sido"], row["sgg"], row["school_name"], row["school_code"],
    ))


def mark_samples(root: Path, rows: list[dict[str, str]]) -> dict:
    index = defaultdict(list)
    for row in rows:
        index[(row["sido"], compact_name(row["school_name"]))].append(row)
    matched_sets = defaultdict(set)
    unmatched, sample_count, matched_count = [], 0, 0
    for path in sorted((root / "data/rosters").glob("middle-*.csv")):
        if path.stem.startswith("middle-nw"):
            continue
        sample_set = path.stem.removeprefix("middle-")
        for sample in read_csv(path):
            sample_count += 1
            sido = sample["region_sido"].strip()
            sido = SIDO_ALIASES.get(sido, sido)
            sgg = sample["region_sgg"].strip()
            candidates = [row for row in index[(sido, compact_name(sample["school_name"]))]
                          if sgg in row["sgg"]]
            if len(candidates) != 1:
                unmatched.append({"sample_set": sample_set, **sample,
                                  "match_count": len(candidates)})
                continue
            matched_count += 1
            matched_sets[candidates[0]["school_code"]].add(sample_set)
    for row in rows:
        samples = matched_sets.get(row["school_code"], set())
        row["sample_sets"] = ";".join(sorted(samples))
        row["published_rounds"] = ";".join(
            str(round_no) for round_no, published in PUBLISHED_SAMPLE_SETS.items()
            if samples & published
        )
    return {"sample_rows": sample_count, "matched_samples": matched_count,
            "matched_schools": len(matched_sets), "unmatched_samples": unmatched}


def round_rows(rows: list[dict[str, str]], bundle: int, round_no: int) -> list[dict[str, str]]:
    return [{
        "school_id": "ms-nw-" + row["school_code"].lower(),
        "school_name": compact_name(row["school_name"]),
        "region_sido": row["sido"], "region_sgg": row["sgg"],
        "school_code": row["school_code"], "neis_school_code": "",
        "education_office_code": row["school_code"][:3], "school_kind": "중학교",
        "shl_idf_cd": row["shl_idf_cd"],
    } for row in rows if row["bundle"] == str(bundle) and not row["excluded_reason"]
        and str(round_no) not in row["published_rounds"].split(";")]


def compare_mcp(root: Path, rows: list[dict[str, str]]) -> list[dict]:
    source = json.loads((root / MCP_SOURCE).read_text(encoding="utf-8"))
    comparisons = []
    for frame in source["frames"]:
        expected = {compact_name(name) for name in frame["names"]}
        actual = {compact_name(row["school_name"]) for row in rows
                  if row["sido"] == frame["sido"] and row["sgg"] == frame["sgg"]}
        comparisons.append({
            "sido": frame["sido"], "sgg": frame["sgg"],
            "mcp_schools": len(expected), "roster_schools": len(actual),
            "only_in_mcp": sorted(expected - actual), "only_in_roster": sorted(actual - expected),
        })
    return comparisons


def preserve_round_rosters(outputs: dict[Path, str]) -> None:
    # Check every snapshot before writing any output. Exclusive creation also
    # prevents a concurrently created snapshot from being overwritten.
    for path, content in outputs.items():
        if path.exists() and path.read_bytes() != content.encode("utf-8"):
            raise ValueError(f"existing roster differs: {path}")
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
        except FileExistsError:
            if path.read_bytes() != content.encode("utf-8"):
                raise ValueError(f"existing roster differs: {path}") from None


def build(root: Path = PROJECT) -> dict:
    rows = load_middle_rows(root)
    samples = mark_samples(root, rows)
    comparisons = compare_mcp(root, rows)
    outputs, bundles = {}, []
    for bundle, sidos in BUNDLES.items():
        definition = {"bundle": bundle, "sido": sidos,
                      "schools": sum(row["bundle"] == str(bundle) for row in rows)}
        for round_no in PUBLISHED_SAMPLE_SETS:
            selected = round_rows(rows, bundle, round_no)
            definition[f"round_{round_no}_schools"] = len(selected)
            path = root / f"data/rosters/middle-nw{bundle}-round-{round_no}.csv"
            outputs[path] = csv_text(ROUND_FIELDS, selected)
        bundles.append(definition)
    summary = {
        "total_schools": len(rows), "by_sido": dict(sorted(Counter(
            row["sido"] for row in rows).items())),
        "branch_campus_excluded": sum(bool(row["excluded_reason"]) for row in rows),
        **samples, "mcp_comparison": comparisons,
    }
    preserve_round_rosters(outputs)
    (root / ROSTER_DIR).mkdir(parents=True, exist_ok=True)
    for path, content in (
        (NATIONWIDE_CSV, csv_text(NATIONWIDE_FIELDS, rows)),
        (ROSTER_DIR / "bundles.json", json_text({"bundles": bundles})),
        (ROSTER_DIR / "nationwide-summary.json", json_text(summary)),
    ):
        (root / path).write_text(content, encoding="utf-8", newline="")
    return summary


def count_row(label: str, sido: str, rows: list[dict[str, str]]) -> str:
    branches = sum(bool(row["excluded_reason"]) for row in rows)
    published = [sum(str(round_no) in row["published_rounds"].split(";") for row in rows)
                 for round_no in PUBLISHED_SAMPLE_SETS]
    targets = [sum(not row["excluded_reason"]
                   and str(round_no) not in row["published_rounds"].split(";") for row in rows)
               for round_no in PUBLISHED_SAMPLE_SETS]
    return (f"| {label} | {sido} | {len(rows):,} | {branches:,} | "
            f"{published[0]:,}/{published[1]:,} | {targets[0]:,} | {targets[1]:,} |")


def counts(root: Path = PROJECT) -> str:
    rows = read_csv(root / NATIONWIDE_CSV)
    groups = defaultdict(list)
    for row in rows:
        groups[(int(row["bundle"]), row["sido"])].append(row)
    lines = [*COUNTS_HEADER]
    for (bundle, sido), selected in sorted(groups.items()):
        lines.append(count_row(str(bundle), sido, selected))
    lines.append(count_row("합계", "", rows))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "counts"))
    args = parser.parse_args()
    try:
        if args.command == "build":
            summary = build()
            print(f"built {summary['total_schools']} schools and 12 round rosters")
        else:
            print(counts())
    except (OSError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
