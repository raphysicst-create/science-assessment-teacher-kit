"""Read-only PDF cell geometry checks for collapsed converter title cells."""

from __future__ import annotations

import re

if __package__:
    from .middle_items import source_tables
else:
    from middle_items import source_tables


def compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def verified_title_splits(text: str, pdf_path) -> dict:
    import fitz

    candidates = []
    for table in source_tables(text):
        for cell in table["cells"]:
            match = re.fullmatch(r"(.+?)\s+(영역\s*만점)\s*(\d+(?:\.\d+)?)\s*", cell["raw"])
            if match and any(
                c["row"] == cell["row"]
                and compact(c["text"]) == "평가영역명"
                and c["col"] < cell["col"]
                for c in table["cells"]
            ):
                candidates.append((cell, match))
    if not candidates:
        return {}
    output = {}
    with fitz.open(pdf_path) as document:
        for cell, match in candidates:
            expected = ["평가영역명", *(compact(match[n]) for n in (1, 2, 3))]
            proofs = []
            for page in document:
                page_text = compact(page.get_text())
                if not all(v in page_text for v in expected):
                    continue
                for table in page.find_tables().tables:
                    for row, values in zip(table.rows, table.extract(), strict=True):
                        actual = [compact(v) for v in values if v]
                        boxes = [
                            list(box) for box, v in zip(row.cells, values, strict=True) if v and box
                        ]
                        if actual != expected or len(boxes) != 4:
                            continue
                        if not all(
                            a[2] <= b[0] + 1 for a, b in zip(boxes, boxes[1:], strict=False)
                        ):
                            continue
                        proofs.append(
                            {
                                "page": page.number + 1,
                                "cells": boxes,
                                "values": actual,
                                "basis": "distinct_pdf_row_cells",
                            }
                        )
            if len(proofs) == 1:
                output[str(cell["start"])] = {
                    "cell_raw": cell["raw"],
                    "proof": proofs[0],
                    "parts": [{"start": match.start(n), "end": match.end(n)} for n in (1, 2, 3)],
                }
    return output
