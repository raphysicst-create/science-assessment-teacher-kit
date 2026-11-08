"""Build and seal an offline, conversion-only source pack for independent labelers."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from extract_math_assessment_batch import extract_document

PROJECT = Path(__file__).resolve().parents[1]
GUIDE = Path("docs/gold/label_guide_v1.md")
SCHEMA = Path("data/reference/gold_label_schema.json")


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sources(root: Path) -> list[dict]:
    rows = []
    for number in (1, 3):
        manifest = root / f"data/derived/schoolinfo_4ga/2026-round-{number}-gold/attachments.jsonl"
        for line in manifest.read_text(encoding="utf-8-sig").splitlines():
            row = json.loads(line)
            # Collection already excluded regulation filenames. Keep every downloaded
            # record, including the deliberately retained 자유중 filename typo.
            if row.get("result") == "downloaded":
                if row["disclosure_round"] != number:
                    raise ValueError(f"manifest round mismatch: {manifest}")
                rows.append(row)
    return sorted(rows, key=lambda row: (
        row["school_name"], row["school_id"], row["disclosure_round"], row["candidate_name"],
    ))


def pack_text(doc_id: str, row: dict, converted: dict, extension: str) -> str:
    structured = converted if converted["converter"] == "kordoc" else converted.get("kordoc", {})
    metadata = [
        f"# {doc_id}",
        f"doc_id = {doc_id}",
        f"학교 = {row['school_id']} / {row['school_name']}",
        f"공시 회차 = {row['disclosure_round']}차",
        f"원문 파일명 = {row['candidate_name']}",
        f"ZIP 자식명 = {converted.get('member_name', '')}",
        f"형식 = {extension}",
        f"변환기 = kordoc{' + pymupdf' if extension == 'pdf' else ''}",
        f"변환 상태 = {converted['conversion_status']}",
        f"kordoc 상태 = {structured.get('conversion_status', 'failed')}",
    ]
    if structured.get("error"):
        metadata.append(f"kordoc 오류 = {json.dumps(structured['error'], ensure_ascii=False)}")
    output = "\n".join(metadata) + "\n\n## kordoc\n\n" + structured.get("text", "")
    if extension == "pdf":
        observed = converted.get("pymupdf", converted)
        output += f"\n\n## pymupdf\n\n상태 = {observed['conversion_status']}\n"
        if observed.get("error"):
            output += f"오류 = {json.dumps(observed['error'], ensure_ascii=False)}\n"
        for page in observed.get("pages", []):
            output += f"\n<<<PAGE {page['page']}>>>\n{page['text']}"
    return output + ("" if output.endswith("\n") else "\n")


def markdown_index(records: list[dict]) -> str:
    columns = [
        "doc_id", "school_id", "school_name", "disclosure_round", "original_filename",
        "zip_child", "format", "conversion_status", "line_count", "sha256",
    ]
    lines = ["# 정답 세트 원문 묶음", "", "줄 번호는 각 md 파일의 첫 줄부터 1로 셉니다.", ""]
    lines += ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in records:
        cells = [str(row[key]).replace("|", "\\|").replace("\n", " ") for key in columns]
        cells[0] = f"[{row['doc_id']}]({row['doc_id']}.md)"
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def build_pack(root: Path, output: Path, kordoc: Path) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"existing source pack must be preserved: {output}")
    inputs = sources(root)
    guide_hash = sha256(root / GUIDE)
    schema_hash = sha256(root / SCHEMA)
    records, originals, archive_counts = [], [], []
    # Ordinary mkdir preserves inherited ACLs when this directory is published.
    stage = output.parent / f".source-build-{uuid4().hex}"
    stage.mkdir()
    try:
        (stage / "raw").mkdir()
        (stage / "pack").mkdir()
        seen = set()
        for number, row in enumerate(inputs, 1):
            source = root / row["saved_path"]
            digest = sha256(source)
            if row["sha256"] != digest:
                raise ValueError(f"original hash mismatch: {source}")
            extension = source.suffix.lower()
            raw = stage / "raw" / f"{digest}{extension}"
            shutil.copyfile(source, raw)
            if sha256(raw) != digest:
                raise ValueError(f"copy hash mismatch: {raw}")
            originals.append({
                "sha256": digest, "original_path": row["saved_path"],
                "raw_path": f"raw/{raw.name}", "school_id": row["school_id"],
                "disclosure_round": row["disclosure_round"],
            })
            converted = extract_document(
                raw, kordoc, root, {"sha256": digest},
                pdf_converter="kordoc", conversion_only=True,
            )
            if sha256(source) != digest or sha256(raw) != digest:
                raise ValueError(f"source changed during conversion: {source}")
            children = converted.get("children", []) if extension == ".zip" else [converted]
            if extension == ".zip":
                if converted.get("error") or not children:
                    raise ValueError(f"ZIP enumeration failed: {source}: {converted.get('error')}")
                archive_counts.append({"sha256": digest, "children": len(children)})
            for position, child in enumerate(children, 1):
                doc_id = digest[:12] + (f"-c{position:02d}" if extension == ".zip" else "")
                if doc_id in seen:
                    raise ValueError(f"duplicate doc_id: {doc_id}")
                seen.add(doc_id)
                child_format = Path(child.get("member_name", raw.name)).suffix.lower().lstrip(".")
                target = stage / "pack" / f"{doc_id}.md"
                content = pack_text(doc_id, row, child, child_format)
                target.write_text(content, encoding="utf-8", newline="\n")
                records.append({
                    "doc_id": doc_id, "school_id": row["school_id"],
                    "school_name": row["school_name"], "disclosure_round": row["disclosure_round"],
                    "original_filename": row["candidate_name"],
                    "zip_child": child.get("member_name", ""), "format": child_format,
                    "conversion_status": child["conversion_status"],
                    "converter": child["converter"], "line_count": content.count("\n"),
                    "sha256": sha256(target), "source_sha256": digest,
                    "warnings": child.get("warnings", []), "error": child.get("error"),
                })
            print(f"converted {number}/{len(inputs)} documents={len(records)}", flush=True)
        write_json(stage / "pack/index.json", records)
        (stage / "pack/INDEX.md").write_text(markdown_index(records), encoding="utf-8")
        if sha256(root / GUIDE) != guide_hash or sha256(root / SCHEMA) != schema_hash:
            raise ValueError("guide or schema changed during generation")
        seal = {
            "created_at": datetime.now(UTC).isoformat(),
            "source_count": len(originals), "document_count": len(records),
            "sources": originals, "zip_archives": archive_counts,
            "pack_files": [
                {"path": f"pack/{path.name}", "sha256": sha256(path)}
                for path in sorted((stage / "pack").iterdir())
            ],
            "guide": {"path": GUIDE.as_posix(), "sha256": guide_hash},
            "schema": {"path": SCHEMA.as_posix(), "sha256": schema_hash},
        }
        write_json(stage / "SEAL.json", seal)
        # Publish raw, pack and seal together after every check. A failed build
        # leaves the destination empty and can be retried without partial output.
        if output.exists():
            output.rmdir()
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {
        "sources": len(originals), "documents": len(records),
        "zip_children": sum(row["children"] for row in archive_counts),
        "formats": dict(Counter(row["format"] for row in records)),
        "statuses": dict(Counter(row["conversion_status"] for row in records)),
        "line_count": sum(row["line_count"] for row in records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT)
    parser.add_argument("--output", type=Path, default=PROJECT / "data/gold")
    parser.add_argument("--kordoc", type=Path, default=PROJECT / "node_modules/kordoc/dist/cli.js")
    args = parser.parse_args()
    print(json.dumps(build_pack(args.project_root, args.output, args.kordoc), ensure_ascii=False))


if __name__ == "__main__":
    main()
