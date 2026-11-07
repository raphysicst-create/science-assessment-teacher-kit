"""Offline physical PDF correspondence; converter offsets are never rewritten.

Independent cell anchors locate a unique best matching physical surface; later
pages need additional cells. Tied occurrences remain ambiguous. Geometry, not
the converter's ordering of headings, establishes continuation ownership.
"""

from __future__ import annotations

import re
from collections import defaultdict

RULE_VERSION = "middle-physical-v1"

if __package__:
    from .middle_items import CODE_RE, source_tables
    from .middle_segments import visible
else:
    from middle_items import CODE_RE, source_tables
    from middle_segments import visible


def compact(value):
    return re.sub(r"\s+", "", value)


def pdf_surfaces(document):
    """Page -> proven left/right pane -> original block/line order."""
    import fitz

    output = []
    for page in document:
        blocks = page.get_text("blocks")
        mid = page.rect.width / 2
        body = [b for b in blocks if 25 < b[1] < page.rect.height - 25]
        two_up = (
            page.rect.width > page.rect.height * 1.3
            and sum(b[2] < mid for b in body) >= 4
            and sum(b[0] > mid for b in body) >= 4
            and not any(b[0] < mid - 20 and b[2] > mid + 20 for b in body)
        )
        for pane in range(2 if two_up else 1):
            clip = (
                fitz.Rect(pane * mid, 0, (pane + 1) * mid, page.rect.height)
                if two_up
                else page.rect
            )
            data = page.get_text("dict", clip=clip)
            rows = []
            for bn, block in enumerate(data["blocks"]):
                for ln, line in enumerate(block.get("lines", [])):
                    rows.append(
                        {
                            "text": "".join(s["text"] for s in line["spans"]),
                            "bbox": list(line["bbox"]),
                            "block": bn,
                            "line": ln,
                        }
                    )
            output.append(
                {
                    "page": page.number + 1,
                    "pane": pane,
                    "two_up": two_up,
                    "width": clip.width,
                    "height": clip.height,
                    "lines": rows,
                }
            )
    return output


HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s*)?(?:[가-하]\.\s*|\d+[)]\s*)(.+?)\s*$")
PEER_RE = re.compile(r"^\s*(?:[가-하][.]|\d+[)])\s*")
DETAIL_RE = re.compile(r"수행\s*평가\s*세부\s*(?:기준|계획)")


def physical_index(text: str, conversion: dict, pdf_path=None) -> dict:
    surfaces = conversion.get("pymupdf", conversion).get("surfaces")
    if surfaces is None:
        if pdf_path is None:
            return {"tables": {}, "titles": {}}
        import fitz

        with fitz.open(pdf_path) as document:
            surfaces = pdf_surfaces(document)
    bodies = [compact("".join(r["text"] for r in s["lines"])) for s in surfaces]
    tables = source_tables(text)
    wanted = set()
    for t in tables:
        if CODE_RE.search(text[t["start"] : t["end"]]):
            wanted.update(range(t["table"], min(len(tables), t["table"] + 3)))
    located = {}
    for t in tables:
        if t["table"] not in wanted:
            continue
        votes = defaultdict(list)
        for cell in t["cells"]:
            value = compact(cell["text"])
            if len(value) < 18:
                continue
            # Both ends of a long cell can occupy different physical pages.
            segments = [compact(visible(v)) for v in re.split(r"<br\s*/?>|\n", cell["raw"])]
            anchors = [
                v for part in [value, *segments] if len(part) >= 18 for v in (part[:24], part[-24:])
            ]
            for anchor in dict.fromkeys(anchors):
                hits = [(n, b.find(anchor)) for n, b in enumerate(bodies) if b.count(anchor) == 1]
                for n, offset in hits:
                    surface = surfaces[n]
                    cursor, boxes = 0, []
                    for row in surface["lines"]:
                        stop = cursor + len(compact(row["text"]))
                        if cursor < offset + len(anchor) and stop > offset:
                            boxes.append(row["bbox"])
                        cursor = stop
                    if boxes:
                        votes[n].append(
                            {
                                "cell_start": cell["start"],
                                "anchor": anchor,
                                "bbox": [
                                    min(b[0] for b in boxes),
                                    min(b[1] for b in boxes),
                                    max(b[2] for b in boxes),
                                    max(b[3] for b in boxes),
                                ],
                            }
                        )
        fragments = []
        maximum = max(
            (len({a["cell_start"] for a in anchors}) for anchors in votes.values()), default=0
        )
        best = [n for n, v in votes.items() if len({a["cell_start"] for a in v}) == maximum]
        selected = set(best)
        if len(best) == 1:
            n = best[0]
            base_cells = {a["cell_start"] for a in votes[n]}
            for nxt in (n + 1, n + 2):
                extra = {a["cell_start"] for a in votes.get(nxt, [])} - base_cells
                if len(extra) < 2:
                    break
                selected.add(nxt)
                base_cells.update(extra)
        for n, anchors in votes.items():
            if len({a["cell_start"] for a in anchors}) < 2:
                continue
            if n not in selected:
                continue
            s = surfaces[n]
            boxes = [a["bbox"] for a in anchors]
            fragments.append(
                {
                    "page": s["page"],
                    "pane": s["pane"],
                    "two_up": s["two_up"],
                    "surface": n,
                    "bbox": [
                        min(b[0] for b in boxes),
                        min(b[1] for b in boxes),
                        max(b[2] for b in boxes),
                        max(b[3] for b in boxes),
                    ],
                    "anchor_cells": len({a["cell_start"] for a in anchors}),
                    "anchors": anchors,
                }
            )
        if fragments:
            located[str(t["table"])] = sorted(
                fragments, key=lambda f: (f["page"], f["pane"], f["bbox"][1])
            )
    titles = {}
    for match in re.finditer(r"(?m)^([^\n]+)$", text):
        heading = HEADING_RE.fullmatch(match[1])
        if not heading or len(heading[1]) < 4:
            continue
        # A title must be outside every converter table.
        if any(t["start"] <= match.start() < t["end"] for t in tables):
            continue
        raw = match[1][heading.start(1) : heading.end(1)]
        key = compact(raw)
        hits = []
        for n, surface in enumerate(surfaces):
            for row in surface["lines"]:
                original = HEADING_RE.fullmatch(row["text"])
                if original and compact(original[1]) == key:
                    hits.append((n, row))
        if len(hits) != 1:
            continue
        n, row = hits[0]
        s = surfaces[n]
        # The detail section can continue onto the next physical surface, but
        # another numbered top-level section closes it.
        before = []
        for prior in surfaces[: n + 1]:
            before.extend(
                r["text"] for r in prior["lines"] if prior is not s or r["bbox"][1] < row["bbox"][1]
            )
        markers = [v for v in before if DETAIL_RE.search(v) or re.match(r"^\s*\d+[.]\s*", v)]
        if not markers or not DETAIL_RE.search(markers[-1]):
            continue
        next_y = min(
            (
                r["bbox"][1]
                for r in s["lines"]
                if r["bbox"][1] > row["bbox"][3]
                and r["bbox"][0] <= row["bbox"][0] + 5
                and re.match(
                    r"^\s*[가-하][.]"
                    if re.match(r"^\s*[가-하][.]", row["text"])
                    else r"^\s*\d+[)]",
                    r["text"],
                )
            ),
            default=s["height"],
        )
        eligible = []
        for tn, fragments in located.items():
            f = fragments[0]
            if f["surface"] == n and row["bbox"][3] <= f["bbox"][1] and f["bbox"][3] <= next_y:
                eligible.append(int(tn))
        if not eligible:
            continue
        tn = min(eligible, key=lambda num: located[str(num)][0]["bbox"][1])
        left = match.start() + heading.start(1)
        titles[str(tn)] = {
            "raw": raw,
            "text": visible(raw),
            "start": left,
            "end": left + len(raw),
            "source_cell_proof": {
                "page": s["page"],
                "pane": s["pane"],
                "bbox": row["bbox"],
                "next_peer_y": next_y,
                "basis": "same_pane_detail_section_before_next_peer",
            },
        }
    order = sorted(
        (f["page"], f["pane"], f["bbox"][1], int(number))
        for number, fragments in located.items()
        for f in fragments
    )
    return {
        "rule_version": RULE_VERSION,
        "tables": located,
        "titles": titles,
        "surfaces": surfaces,
        "table_order": [dict(page=p, pane=s, y=y, table=t) for p, s, y, t in order],
    }


def continuation_proof(previous: dict, following: dict, text: str, physical: dict) -> dict | None:
    """All four gates: pages, columns, unfinished rows, no intervening peer."""
    a = physical.get("tables", {}).get(str(previous["table"]), [])
    b = physical.get("tables", {}).get(str(following["table"]), [])
    if not a or not b or following["table"] != previous["table"] + 1:
        return None
    # A repeated conversion-score grid can occur under several tasks. Physical
    # adjacency must select one unique occurrence; converter order alone cannot.
    pairs = [
        (x, y)
        for x in a
        for y in b
        if (
            y["surface"] == x["surface"] + 1
            if x.get("two_up") and y.get("two_up")
            else y["page"] == x["page"] + 1 and y["pane"] == x["pane"]
        )
    ]
    if len(pairs) != 1:
        return None
    left, right = pairs[0]
    gap = visible(text[previous["end"] : following["start"]])
    if gap.strip():
        return None
    surfaces = physical.get("surfaces", [])
    if (
        left["bbox"][3] < surfaces[left["surface"]]["height"] * 0.8
        or right["bbox"][1] > surfaces[right["surface"]]["height"] * 0.4
    ):
        return None
    for f, tail in ((left, True), (right, False)):
        for row in surfaces[f["surface"]]["lines"]:
            y = row["bbox"][1]
            if (y > f["bbox"][3] if tail else y < f["bbox"][1]) and (
                PEER_RE.match(row["text"]) or re.match(r"^\s*\d+[.]\s*", row["text"])
            ):
                return None
    # Physical vertical rulings supply column boundaries, independent of the
    # converter's inconsistent colspan counts on continued pages.
    if "columns" not in left or "columns" not in right:
        return None
    lc = [x - surfaces[left["surface"]].get("width", 0) * left["pane"] for x in left["columns"]]
    rc = [x - surfaces[right["surface"]].get("width", 0) * right["pane"] for x in right["columns"]]
    shared = [x for x in lc if any(abs(x - y) <= 3 for y in rc)]
    if len(shared) < 3 or abs(lc[0] - rc[0]) > 3 or abs(lc[-1] - rc[-1]) > 3:
        return None
    labels = {compact(c["text"]) for c in previous["cells"]}
    finished = any("기본점수" == v for v in labels)
    unfinished = not finished and (
        any(re.fullmatch(r"[ABCDE]", c["text"]) for c in previous["cells"])
        or "채점기준" in labels
        or "평가요소" in labels
        or "영역만점" in labels
    )
    if not unfinished:
        return None
    # A new title/form closes ownership, including an unnumbered title cell.
    if any(
        compact(c["text"]) in {"평가영역", "평가영역명", "수행과제", "평가과제명"}
        for c in following["cells"]
    ):
        return None
    return {
        "basis": "physical_pages_columns_unfinished_rows_no_peer",
        "from": left,
        "to": right,
        "shared_columns": shared,
        "unfinished": True,
    }


def add_column_geometry(physical: dict, pdf_path) -> None:
    import fitz

    with fitz.open(pdf_path) as document:
        cache = {}
        for fragments in physical["tables"].values():
            for f in fragments:
                p = f["page"]
                if p not in cache:
                    cache[p] = document[p - 1].get_drawings()
                xvalues = []
                page = document[p - 1]
                pane_left = page.rect.width / 2 * f["pane"] if f["two_up"] else 0
                pane_right = pane_left + (page.rect.width / 2 if f["two_up"] else page.rect.width)
                for path in cache[p]:
                    entries = []
                    for entry in path["items"]:
                        if entry[0] == "re":
                            rect = entry[1]
                            entries.extend([("l", rect.tl, rect.bl), ("l", rect.tr, rect.br)])
                        else:
                            entries.append(entry)
                    for entry in entries:
                        if entry[0] == "l":
                            a, b = entry[1:3]
                            if (
                                abs(a.y - b.y) < 1
                                and abs(a.x - b.x) > 25
                                and f["bbox"][1] - 15 <= a.y <= f["bbox"][3] + 15
                                and pane_left < min(a.x, b.x) < max(a.x, b.x) < pane_right
                            ):
                                xvalues.extend((round(a.x, 1), round(b.x, 1)))
                            if (
                                abs(a.x - b.x) < 1
                                and abs(a.y - b.y) > 15
                                and (
                                    min(a.y, b.y) <= f["bbox"][3]
                                    and max(a.y, b.y) >= f["bbox"][1]
                                    and pane_left < a.x < pane_right
                                )
                            ):
                                xvalues.append(round(a.x, 1))
                # Cluster duplicate rulings without quantization boundary drift.
                clustered = []
                for x in sorted(xvalues):
                    if not clustered or x - clustered[-1] > 3:
                        clustered.append(x)
                f["columns"] = clustered
