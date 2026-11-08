"""Deterministic edition families and a non-destructive S6 history ledger."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path

DATE_RE = re.compile(r"(?<!\d)(20\d{2}|\d{2})[.\-_년 ]+(\d{1,2})[.\-_월 ]+(\d{1,2})(?:일)?")


def edition_stem(filename):
    stem = Path(filename).stem
    stem = DATE_RE.sub("", stem)
    stem = re.sub(r"최종본?|수정본?|개정본?|변경본?", "", stem)
    return re.sub(r"[\W_]+", "", stem)


def edition_rank(document):
    filename = document["filename"]
    dates = []
    for match in DATE_RE.finditer(filename):
        year, month, day = map(int, match.groups())
        if 1 <= month <= 12 and 1 <= day <= 31:
            dates.append((year + 2000 if year < 100 else year, month, day))
    # A dated amendment can postdate a file labelled final. Lower FILE_SEQ is
    # the newer published attachment order in the preserved disclosure metadata.
    edition = document.get("edition", {})
    sequence = str(edition.get("file_seq", ""))
    return (max(dates, default=(0, 0, 0)), bool(re.search(r"최종", filename)),
            bool(re.search(r"수정|개정|변경", filename)),
            -int(sequence) if sequence.isdigit() else -10**9,
            edition.get("collected_at", ""), document.get("converted_path", ""))


def select_editions(documents):
    groups = defaultdict(list)
    for document in documents:
        groups[(document["school_code"], tuple(document.get("grades", [])),
                edition_stem(document["filename"]))].append(document)
    for family in groups.values():
        chosen = max(family, key=edition_rank)
        for document in family:
            document["development_selected"] = document is chosen
            document["representative_converted_path"] = chosen["converted_path"]
            document["edition_selection"] = {
                "basis": "filename_family_date_final_revision_publication_order",
                "rank": edition_rank(document),
                "identical_text": document["text_sha256"] == chosen["text_sha256"],
                "family_size": len(family),
            }
    identical = defaultdict(list)
    for document in documents:
        if (document["development_selected"] and document.get("text_sha256")
                and document["text_sha256"] != hashlib.sha256(b"").hexdigest()):
            terms = tuple(re.findall(r"[12]\s*학기", document["filename"]))
            identical[(document["school_code"], tuple(document.get("grades", [])),
                       terms, document["text_sha256"])].append(document)
    for family in identical.values():
        chosen = max(family, key=edition_rank)
        replaced = {d["converted_path"] for d in family if d is not chosen}
        for document in documents:
            if document["representative_converted_path"] in replaced:
                document["development_selected"] = False
                document["representative_converted_path"] = chosen["converted_path"]
                document["edition_selection"]["body_identity_representative"] = chosen[
                    "converted_path"]
    return documents


def edition_history(documents, items):
    selected = {d["converted_path"] for d in documents if d["development_selected"]}
    current = [i for i in items if i["converted_path"] in selected]
    history = []
    for document in documents:
        if document["development_selected"]:
            continue
        previous = [i for i in items if i["converted_path"] == document["converted_path"]]
        representative = [i for i in current if i["converted_path"]
                          == document["representative_converted_path"]]
        differences = []
        for item in previous:
            # Compare matching positions within the same grade/term and layout
            # sequence. Unmatched entries remain fully available in the ledger.
            peers = [i for i in representative if i["grade"] == item["grade"]
                     and i["semester"] == item["semester"] and i["layout"] == item["layout"]]
            own = [i for i in previous if i["grade"] == item["grade"]
                   and i["semester"] == item["semester"] and i["layout"] == item["layout"]]
            index = own.index(item)
            peer = peers[index] if len(own) == len(peers) else None
            changed = {name: {"previous": field["value"],
                              "representative": peer["fields"][name]["value"] if peer else None}
                       for name, field in item["fields"].items()
                       if peer is None or field["value"] != peer["fields"][name]["value"]}
            if changed:
                differences.append({"item_id": item["item_id"],
                                    "representative_item_id": peer["item_id"] if peer else None,
                                    "alignment": "layout_sequence" if peer else "unmatched",
                                    "fields": changed})
        history.append({"document": document, "items": previous, "differences": differences,
                        "removed_bounded": sum(i["extraction_status"] == "bounded"
                                               and i["candidate_role"] != "summary_duplicate"
                                               for i in previous)})
    return current, history
