"""Conservative PDF method-row comparison, independent of document glyph totals."""

from __future__ import annotations

import hashlib
import re
from collections import Counter

if __package__:
    from .assessment_symbols import BOX_RE, marker_state
    from .middle_items import evidence, label_role, source_tables
    from .middle_segments import visible
else:
    from assessment_symbols import BOX_RE, marker_state
    from middle_items import evidence, label_role, source_tables
    from middle_segments import visible

METHOD_LABEL_RE = re.compile(
    r"서술\s*[·ㆍ･・]\s*논술형?|서\s*[·ㆍ･・]\s*논술형?|서술형?|논술형?|"
    r"구술\s*[·ㆍ･・]\s*발표|구술|발표|토의\s*[·ㆍ･・]\s*토론|"
    r"조사\s*[.·ㆍ･・]\s*관찰\s*보고서|실험\s*[·ㆍ･・]\s*실습|"
    r"포트폴리오|프로젝트|실기\s*[.·ㆍ･・]\s*시연|실기|기타(?:\s*\([^)]*\))?"
)


def row_options(raw: str) -> list[dict]:
    text = visible(raw)
    options = []
    previous = 0
    for match in METHOD_LABEL_RE.finditer(text):
        prefix = text[previous : match.start()]
        markers = list(BOX_RE.finditer(prefix))
        marker = markers[-1].group() if len(markers) == 1 else ""
        residue = BOX_RE.sub("", prefix).strip()
        if residue or len(markers) > 1:
            return []
        options.append(
            {
                "label": re.sub(r"\s+", "", match.group()),
                "marker": marker,
                "state": marker_state(marker) if marker else "missing",
            }
        )
        previous = match.end()
    if text[previous:].strip() or not options:
        return []
    return options


def pdf_method_rows(page, page_number: int) -> list[dict]:
    """Use physical text boxes. Ambiguous/multi-line rows may stay unmapped."""
    lines = [
        {"text": "".join(span["text"] for span in line["spans"]), "bbox": line["bbox"]}
        for block in page.get_text("dict")["blocks"]
        if "lines" in block
        for line in block["lines"]
    ]
    rows = []
    for header in lines:
        if label_role(header["text"]) != "method":
            continue
        x0, y0, x1, y1 = header["bbox"]
        boundaries = [
            line["bbox"][1]
            for line in lines
            if line["bbox"][1] >= y1 and line["bbox"][0] <= x1 and label_role(line["text"])
        ]
        bottom = min(boundaries, default=page.rect.height)
        content = [
            line
            for line in lines
            if line["bbox"][0] >= x1 and line["bbox"][3] >= y0 and line["bbox"][1] < bottom
        ]
        content.sort(key=lambda line: (round(line["bbox"][1], 1), line["bbox"][0]))
        raw = " ".join(line["text"] for line in content)
        options = row_options(raw)
        if options:
            rows.append(
                {
                    "page": page_number,
                    "raw": raw,
                    "options": options,
                    "bbox": [x0, y0, max(line["bbox"][2] for line in content), bottom],
                }
            )
    return rows


def structured_method_rows(text: str, blocks: list[dict]) -> list[dict]:
    tables = source_tables(text)
    ir_tables = [block for block in blocks if block.get("type") == "table"]

    # Match entire cell sequences, allowing the renderer's empty merged-cell
    # placeholders and Markdown separator row. Repeated sequences stay unmapped.
    def signature(values):
        return tuple(
            re.sub(r"\s+", "", visible(value).replace("\\", ""))
            for value in values
            if value.strip() and not re.fullmatch(r"[:\-\s]+", value)
        )

    source_keys = [signature(c["text"] for c in table["cells"]) for table in tables]
    ir_keys = [
        signature(c.get("text", "") for row in block["table"]["cells"] for c in row)
        for block in ir_tables
    ]
    source_counts, ir_counts = Counter(source_keys), Counter(ir_keys)
    unique_blocks = {
        key: block for key, block in zip(ir_keys, ir_tables, strict=True) if ir_counts[key] == 1
    }
    rows = []
    for table, key in zip(tables, source_keys, strict=True):
        if not table["structure_verified"]:
            continue
        block = unique_blocks.get(key, {}) if source_counts[key] == 1 else {}
        page = block.get("pageNumber") or block.get("bbox", {}).get("page")
        for row in table["rows"]:
            for index, header in enumerate(row[:-1]):
                if label_role(header["text"]) != "method":
                    continue
                for cell in row[index + 1 :]:
                    if label_role(cell["text"]):
                        break
                    options = row_options(cell["raw"])
                    rows.append(
                        {
                            **evidence(cell, {"converter": "kordoc"}, header),
                            "page": page,
                            "options": options,
                        }
                    )
    return rows


def compare_method_rows(direct: dict, structured: dict, source_sha256: str) -> dict:
    """Require one source hash, physical page, row, and unique option labels."""
    source_rows = direct.get("method_rows", [])
    target_rows = structured.get("method_rows", [])
    rows = []
    for target in target_rows:
        page = target["page"]
        labels = [o["label"] for o in target["options"]]
        source_page = [r for r in source_rows if r["page"] == page]
        target_page = [r for r in target_rows if r["page"] == page]
        candidates = [r for r in source_page if [o["label"] for o in r["options"]] == labels]
        target_matches = [r for r in target_page if [o["label"] for o in r["options"]] == labels]
        unique = bool(
            page
            and labels
            and len(set(labels)) == len(labels)
            and len(candidates) == len(target_matches) == 1
        )
        status = "unmapped"
        glyph_differences = []
        source = candidates[0] if unique else None
        if unique:
            pairs = list(zip(source["options"], target["options"], strict=True))
            glyph_differences = [
                {"label": a["label"], "pymupdf_marker": a["marker"], "kordoc_marker": b["marker"]}
                for a, b in pairs if a["marker"] != b["marker"]
            ]
            differences = [(a, b) for a, b in pairs if a["state"] != b["state"]]
            if not differences:
                status = "matched"
            elif all(
                a["state"] in {"checked", "unchecked"} and b["state"] == "missing"
                for a, b in differences
            ):
                status = "loss"
            else:
                status = "conflict"
        elif page and labels and len(source_page) == len(target_page) == 1:
            source = source_page[0]
            status = "conflict"
        rows.append(
            {
                "source_sha256": source_sha256,
                "page": page,
                "start": target["locator"]["start"],
                "end": target["locator"]["end"],
                "status": status,
                "one_to_one": unique,
                "glyph_differences": glyph_differences,
                "kordoc": target,
                "pymupdf": source,
                "action": "retain_for_review" if status in {"loss", "conflict"} else "observe",
            }
        )
    return {
        "source_sha256": source_sha256,
        "structured_text_sha256": hashlib.sha256(structured.get("text", "").encode()).hexdigest(),
        "rows": rows,
        "statuses": dict(Counter(row["status"] for row in rows)),
        "source_rows": len(source_rows),
        "target_rows": len(target_rows),
        "policy": "같은 해시·물리 페이지·방법 행·선택지 일대일 대응만 사용. "
        "전체 기호 수로 보충 금지",
    }
