"""Validate independent gold JSONL labels against the schema and sealed pack."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = PROJECT / "data/gold/pack"
DEFAULT_SCHEMA = PROJECT / "data/reference/gold_label_schema.json"

# The repository's installed Ajv 8 provides draft 2020-12 without downloading
# Python dependencies or resolving remote schema references.
AJV_CHECK = """
const fs = require('fs');
const Ajv = require(process.argv[1]).default;
const {schema, records} = JSON.parse(fs.readFileSync(0, 'utf8'));
const ajv = new Ajv({allErrors: true, strict: false, validateFormats: false});
const validators = {};
for (const type of ['document', 'item']) {
  const branch = {...schema, $id: undefined, oneOf: undefined, $ref: '#/$defs/' + type};
  validators[type] = ajv.compile(branch);
}
const root = ajv.compile({...schema, $id: undefined});
const errors = records.map(record => {
  const check = validators[record?.type] || root;
  return check(record) ? [] : check.errors;
});
process.stdout.write(JSON.stringify(errors));
"""


def schema_errors(records: list, schema_path: Path = DEFAULT_SCHEMA) -> list[list[dict]]:
    candidates = [PROJECT / "node_modules/ajv/dist/2020.js"]
    candidates += sorted((PROJECT / "node_modules/.pnpm").glob(
        "ajv@8*/node_modules/ajv/dist/2020.js",
    ))
    ajv = next((path for path in candidates if path.exists()), None)
    if ajv is None:
        raise RuntimeError(
            "draft 2020-12 validator missing: install repository dependencies offline",
        )
    payload = {"schema": json.loads(schema_path.read_text(encoding="utf-8")), "records": records}
    result = subprocess.run(
        ["node", "-e", AJV_CHECK, str(ajv)], input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"schema validator failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def read_labels(path: Path) -> tuple[list, list[int], list[str]]:
    records, numbers, errors = [], [], []
    text = path.read_text(encoding="utf-8-sig")
    lines = text.split("\n") if text else []
    if text.endswith("\n"):
        lines.pop()
    for number, line in enumerate(lines, 1):
        try:
            records.append(json.loads(line))
            numbers.append(number)
        except ValueError as exc:
            errors.append(f"JSONL {number}줄: JSON 오류 ({exc})")
    return records, numbers, errors


def load_index(pack: Path) -> dict[str, dict]:
    rows = json.loads((pack / "index.json").read_text(encoding="utf-8"))
    index = {row["doc_id"]: row for row in rows}
    if len(index) != len(rows):
        raise ValueError("pack index contains duplicate doc_id")
    return index


def line_range(loc: dict) -> tuple[int, int]:
    if "line" in loc:
        return loc["line"], loc["line"]
    return loc["line_start"], loc["line_end"]


def pack_lines(path: Path) -> list[str]:
    # Only LF creates a physical pack line. str.splitlines also splits PDF form
    # feeds and Unicode separators, which would disagree with grep -n.
    text = path.read_bytes().decode("utf-8")
    if not text:
        return []
    lines = text.split("\n")
    return lines[:-1] if text.endswith("\n") else lines


def walk(value, path: str = ""):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from walk(child, f"{path}/{key}")
    elif isinstance(value, list):
        for number, child in enumerate(value):
            yield from walk(child, f"{path}/{number}")


def validate_file(
    path: Path, pack: Path = DEFAULT_PACK, schema: Path = DEFAULT_SCHEMA,
    schools: list[str] | None = None,
) -> list[str]:
    records, numbers, errors = read_labels(path)
    index = load_index(pack)
    selected_schools = None if schools is None else set(schools)
    if selected_schools is not None:
        unknown = selected_schools - {row["school_id"] for row in index.values()}
        for school_id in sorted(unknown):
            errors.append(f"INDEX에 없는 school_id: {school_id}")
    counts = {}
    for doc_id, metadata in index.items():
        counts[doc_id] = len(pack_lines(pack / f"{doc_id}.md"))
        if counts[doc_id] != metadata["line_count"]:
            errors.append(f"INDEX {doc_id}: 실제 줄 수와 line_count가 다름")
    documents, item_keys = Counter(), Counter()

    def check_location(loc: dict, prefix: str, school_id: str) -> None:
        doc_id = loc["doc_id"]
        if doc_id not in index:
            errors.append(f"{prefix}: 존재하지 않는 doc_id {doc_id}")
            return
        if school_id != index[doc_id]["school_id"]:
            errors.append(f"{prefix}: 위치의 학교와 school_id가 다름")
        start, end = line_range(loc)
        if not 1 <= start <= end <= counts[doc_id]:
            errors.append(f"{prefix}: {doc_id} 줄 범위 {start}~{end}, 허용 1~{counts[doc_id]}")

    violations_by_record = schema_errors(records, schema)
    for record, number, violations in zip(records, numbers, violations_by_record, strict=True):
        prefix = f"JSONL {number}줄"
        if violations:
            for violation in violations:
                details = json.dumps(violation["params"], ensure_ascii=False)
                errors.append(
                    f"{prefix} {violation['instancePath'] or '/'}: "
                    f"스키마 {violation['message']} {details}",
                )
            continue
        if selected_schools is not None and record["school_id"] not in selected_schools:
            errors.append(f"{prefix}: 학교 범위 밖 school_id {record['school_id']}")
        if record["type"] == "document":
            doc_id = record["doc_id"]
            documents[doc_id] += 1
            if doc_id not in index:
                errors.append(f"{prefix}: 존재하지 않는 doc_id {doc_id}")
            elif record["school_id"] != index[doc_id]["school_id"]:
                errors.append(f"{prefix}: INDEX의 학교와 school_id가 다름")
            for section in record["science_sections"]:
                check_location({"doc_id": doc_id, **section}, prefix, record["school_id"])
        else:
            item_keys[record["item_key"]] += 1
            expected = f"{record['school_id']}-g{record['grade']}-s{record['semester']}-"
            if not record["item_key"].startswith(expected):
                errors.append(f"{prefix}: item_key의 학교·학년·학기가 본문과 다름")
        for location, value in walk(record):
            if "status" in value and "values" in value:
                minimum = {"present": 1, "conflict": 2}.get(value["status"], 0)
                if len(value["values"]) < minimum:
                    errors.append(
                        f"{prefix} {location}: {value['status']} values는 {minimum}개 이상",
                    )
            if "doc_id" in value and ("line" in value or "line_start" in value):
                check_location(value, f"{prefix} {location}", record["school_id"])
    for doc_id, metadata in index.items():
        if selected_schools is not None and metadata["school_id"] not in selected_schools:
            continue
        if documents[doc_id] != 1:
            errors.append(f"문서 {doc_id}: document 줄 {documents[doc_id]}개 (정확히 1개 필요)")
    for key, count in item_keys.items():
        if count > 1:
            errors.append(f"항목 {key}: item_key 중복 {count}개")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--pack-dir", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--schools", nargs="+", help="검사할 school_id 목록 (생략하면 전체 학교)")
    args = parser.parse_args()
    try:
        errors = validate_file(args.labels, args.pack_dir, args.schema, args.schools)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        errors = [f"검사 실행 오류: {exc}"]
    for error in errors:
        print(f"- {error}")
    print(f"검사 {'실패' if errors else '통과'}. 오류 {len(errors)}개")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
