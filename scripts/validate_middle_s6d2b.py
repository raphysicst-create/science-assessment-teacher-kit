"""Check development provenance, disjoint sampling and absence of source-specific rules."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from compare_middle_performance_items import ROUNDS, read
from compare_middle_s6d2b import PREFIX, save_json
from verify_middle_s6d2b import VIOLATIONS, guard

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "scripts/middle_items.py", "scripts/middle_identity.py", "scripts/middle_segments.py",
    "scripts/compare_middle_s6d2b.py", "scripts/recheck_middle_s6d2b.py",
    "scripts/verify_middle_s6d2b.py", "scripts/validate_middle_s6d2b.py",
    "services/math-assessment-api/tests/test_middle_s6d2b.py",
)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    needles, conversions, preserved = set(), {}, []
    for r in ROUNDS:
        report = read(f"data/derived/items/{r}.json")
        for d in report["documents"]:
            needles.add(d["school"])
            needles.add(d["filename"])
            needles.add(Path(d["filename"]).name)
            needles.add(Path(d["filename"]).stem)
            conversions[d["converted_path"]] = d["text_sha256"]
        for kind in ("items", "segments", "subjects"):
            for ext in ("json", "md"):
                path = ROOT / f"data/derived/{kind}/{r}.prev-s6d2.{ext}"
                assert path.exists(), path
                preserved.append({"path": path.relative_to(ROOT).as_posix(),
                                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    hits = []
    for filename in FILES:
        text = (ROOT / filename).read_text(encoding="utf-8")
        for needle in sorted(needles):
            if len(needle) > 3 and needle in text:
                hits.append({"file": filename, "kind": "source_metadata_literal", "text": needle})
        for match in re.finditer(r"(?<![\w])[0-9a-f]{64}(?![\w])", text):
            hits.append({"file": filename, "kind": "hash_literal", "text": match.group()})
        for match in re.finditer(
            r"\b(?:line_start|line_end|converted_path|source_sha256)\s*==\s*[\"'\d]", text,
        ):
            hits.append({"file": filename, "kind": "source_coordinate_branch",
                         "text": match.group()})
    changed_conversions = []
    for filename, expected in conversions.items():
        actual = hashlib.sha256(read(filename)["text"].encode("utf-8")).hexdigest()
        if expected != actual:
            changed_conversions.append(filename)
    old = read("docs/dev/2026-11-08-s6d2-review-sample.json")
    new = read(f"docs/dev/{PREFIX}-review-sample.json")

    def cells(sample):
        return {(c["round"], c["school"], c["grade"], c["semester"])
                for c in sample["source_review"]}

    overlap = cells(old) & cells(new)
    result = {"checked_files": FILES, "hardcoding_hits": hits,
              "preserved_results": preserved, "conversion_texts_checked": len(conversions),
              "conversion_text_hash_errors": changed_conversions,
              "sample_population": new["population_size"], "sample_size": len(cells(new)),
              "sample_overlap_with_previous": len(overlap), "access_violations": VIOLATIONS}
    save_json(ROOT / "data/derived/s6d2b/validation.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "preserved_results"},
                     ensure_ascii=False, indent=2))
    if hits or changed_conversions or overlap or len(cells(new)) != 16 or VIOLATIONS:
        raise SystemExit("S6d-2b validation failed")


if __name__ == "__main__":
    main()
