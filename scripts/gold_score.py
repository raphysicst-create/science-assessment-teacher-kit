"""Score the sealed gold-v1 corpus against offline S4/S5/S6 artifacts."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import html
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from gold_diff import locations, match_items, normalize, numeric_values, overlap
from middle_segments import child_identifier

ROOT = Path(__file__).resolve().parents[1]
FIELD_MAP = {
    "title": "title",
    "task_text": "task_text",
    "period": "timing",
    "method": "method",
    "standards": "standards",
    "max_score": "score",
    "sub_scores": "points",
    "ratio": "weight",
    "rubric": "rubric",
    "free_semester": "free_semester",
}
OUTCOMES = ("정답", "누락", "오값", "허위값", "둘다없음")
UNMATCHED_CATEGORIES = (
    "다른 교과",
    "중3",
    "지필평가",
    "요약·중복",
    "운영표·규정",
    "짝짓기 보류",
    "정답 누락 가능성",
    "기타",
)
ROUNDS = ("2026-round-1-gold", "2026-round-3-gold")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(value: object) -> str:
    return normalize(html.unescape(re.sub(r"<[^>]*>", "", str(value))))


def raw_values(value) -> list[str]:
    if isinstance(value, dict):
        return [str(v["raw"]) for v in value.get("values", []) if "raw" in v]
    if isinstance(value, list):
        return [s for child in value for s in raw_values(child)]
    return [str(value)] if value is not None else []


def alternatives(field: dict) -> list:
    return field.get("accepted", []) or [field.get("value")]


def gold_titles(item: dict, *, task: bool = True) -> set[str]:
    strings = [item.get("representative_title", {}).get("raw", "")]
    strings += [a["raw"] for a in item.get("aliases", [])]
    names = ("title", "task_text") if task else ("title",)
    strings += [
        s for n in names for v in alternatives(item["fields"].get(n, {})) for s in raw_values(v)
    ]
    return {norm(s) for s in strings if norm(s)}


def method_tokens(value) -> frozenset[str]:
    """Use checked labels and explicit method prose, with no semantic synonyms."""
    if isinstance(value, dict):
        options = value.get("options", [])
        strings = [o["text"] for o in options if o.get("state") in {"checked", "selected"}]
        strings += [value.get("plain_text", ""), value.get("other_text", "")]
        if not options and not any(strings):
            strings = raw_values(value)
    elif isinstance(value, list):
        strings = [str(v) for v in value]
    else:
        strings = [str(value)]
    return frozenset(
        norm(part)
        for s in strings
        for part in re.split(r"[,/;\n]|<br\s*/?>", s)
        if norm(part) and norm(part) != "-"
    )


def content(name: str, value):
    if name == "free_semester":
        return value if isinstance(value, bool) else None
    if name == "method":
        return method_tokens(value)
    if name == "standards":
        if isinstance(value, list) and all(isinstance(v, dict) for v in value):
            return frozenset(norm(c) for v in value for c in v.get("codes", []))
        return frozenset(
            norm(c) for c in re.findall(r"\[\s*9\s*과\s*\d+\s*-\s*\d+\s*\]", str(value))
        )
    if name in {"max_score", "ratio", "sub_scores"}:
        if isinstance(value, (int, float)):
            return frozenset([float(value)])
        if isinstance(value, dict):
            values = value.get("values", [value])
            if name == "sub_scores":
                return frozenset(
                    (norm(v.get("name", "")), n) for v in values for n in numeric_values(v)
                )
            return frozenset(n for v in values for n in numeric_values(v))
        numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
        return frozenset(float(n) for n in numbers)
    if isinstance(value, dict):
        return frozenset(norm(s) for s in raw_values(value) if norm(s))
    return frozenset([norm(value)]) if value not in (None, "", []) else frozenset()


def pipeline_field(item: dict, name: str) -> dict:
    return item.get("fields", {}).get(FIELD_MAP[name], {"status": "unconfirmed", "value": None})


def field_result(name: str, gold: dict, item: dict) -> dict:
    expected = gold["fields"].get(name, {"status": "source_absent", "value": None})
    actual = pipeline_field(item, name)
    conflict = expected.get("status") == "conflict"
    emitted = actual.get("status") == "present" and actual.get("value") not in (None, "", [])
    if name == "free_semester" and actual.get("status") == "present":
        emitted = isinstance(actual.get("value"), bool)
    result = {
        "gold_status": expected.get("status"),
        "pipeline_status": actual.get("status"),
        "gold_accepted": alternatives(expected),
        "pipeline_value": actual.get("value"),
        "gold_conflict": conflict,
        "standards_relation": None,
    }
    if conflict and actual.get("status") == "conflict":
        return {**result, "result": "정답", "basis": "conflict 보존"}
    if expected.get("status") == "source_absent":
        return {**result, "result": "허위값" if emitted else "둘다없음"}
    if not emitted:
        return {**result, "result": "누락"}
    observed = content(name, actual["value"])
    options = [content(name, v) for v in alternatives(expected)]
    if name == "title":
        correct = bool(observed & gold_titles(gold, task=False))
    elif name == "rubric":
        # Gold rubric is a source range, not a verbatim transcription requirement.
        correct = bool(
            overlap(locations(expected.get("value")), item.get("field_locations", {}).get(name, []))
        )
    else:
        correct = observed in options
    if conflict and name != "free_semester":
        # Each preserved atomic observation is an allowed conflicting alternative.
        atomic = [
            content(name, {"values": [v]})
            for a in alternatives(expected)
            if isinstance(a, dict)
            for v in a.get("values", [])
        ]
        if name == "standards":
            codes = set().union(*options) if options else set()
            correct = bool(observed) and observed <= codes
        else:
            correct = correct or observed in atomic
    if name == "standards":
        union = set().union(*options) if options else set()
        relation = (
            "equal"
            if observed == union
            else ("subset" if observed < union else "excess" if observed > union else "different")
        )
        result["standards_relation"] = relation
    return {**result, "result": "정답" if correct else "오값"}


def misattributions(gold: dict, item: dict, peers: list[dict], names: list[str]) -> list[dict]:
    errors = []
    for name in names:
        own = field_result(name, gold, item)
        if own["result"] not in {"오값", "허위값"}:
            continue
        others = [
            p["item_key"]
            for p in peers
            if p["item_key"] != gold["item_key"]
            and all(p[k] == gold[k] for k in ("school_id", "grade", "semester"))
            and field_result(name, p, item)["result"] == "정답"
        ]
        if others:
            errors.append(
                {
                    "field": name,
                    "gold_key": gold["item_key"],
                    "pipeline_key": item["score_id"],
                    "other_gold_keys": others,
                    "value": pipeline_field(item, name).get("value"),
                    "public_eligible": item.get("public_eligible", False),
                }
            )
    return errors


def independent(item: dict) -> bool:
    return not (item.get("candidate_role") == "summary_duplicate" and item.get("identity_relation"))


def confirmed(item: dict) -> bool:
    return item.get("extraction_status") == "bounded" or item.get("public_eligible") is True


def task_number(value) -> str | None:
    """Read a single identity number, never a number embedded in task prose."""
    numbers = set()
    for raw in raw_values(value):
        text = unicodedata.normalize("NFKC", raw)
        if len(re.findall(r"[0-9]+", re.sub(r"\s+", "", text))) != 1:
            return None
        text = norm(text)
        match = re.fullmatch(r"(?:수행평가|과제|평가)?제?([0-9]+)(?:번|차)?", text)
        if not match:
            return None
        number = int(match[1])
        if number < 1:
            return None
        numbers.add(str(number))
    return next(iter(numbers)) if len(numbers) == 1 else None


def identity_number(item: dict, *, is_gold: bool) -> str | None:
    field = item.get("fields", {}).get("task_no", {})
    explicit = task_number(field.get("value")) if field.get("status") == "present" else None
    if is_gold:
        return explicit
    title = task_number(pipeline_field(item, "title").get("value"))
    # An ambiguous explicit observation must not be hidden by a generic title.
    if field.get("status") == "conflict" or (
        field.get("status") == "present" and raw_values(field.get("value")) and not explicit
    ):
        return None
    if explicit and title and explicit != title:
        return None
    return explicit or title


def number_links(gold: list[dict], pipeline: list[dict]) -> dict[tuple[int, int], str]:
    """Require uniqueness over the entire stage, including already paired rows."""
    indexes = []
    for rows, is_gold in ((gold, True), (pipeline, False)):
        index = defaultdict(list)
        for i, row in enumerate(rows):
            group = tuple(row.get(k) for k in ("school_id", "grade", "semester"))
            number = identity_number(row, is_gold=is_gold)
            if all(v is not None for v in group) and number:
                index[(*group, number)].append(i)
        indexes.append(index)
    return {
        (left[0], indexes[1][key][0]): key[-1]
        for key, left in indexes[0].items()
        if len(left) == 1 and len(indexes[1].get(key, [])) == 1
    }


def pair_items(
    gold: list[dict], pipeline: list[dict], *, use_task_no: bool = True,
) -> tuple[list[dict], list[int], list[int]]:
    left = [
        {
            **g,
            "title": {"values": [{"raw": s} for s in gold_titles(g)]},
            "task_text": {"values": []},
        }
        for g in gold
    ]
    right = [
        {
            **p,
            "title": {
                "values": [
                    {"raw": s}
                    for n in ("title", "task_text")
                    for s in raw_values(pipeline_field(p, n)["value"])
                ]
            },
            "task_text": {"values": []},
        }
        for p in pipeline
    ]
    pairs, missing, extra = match_items(left, right)
    numbered = {}
    released = set()
    if use_task_no:
        links = number_links(gold, pipeline)
        while missing and extra:
            recovered = {(i, j): n for (i, j), n in links.items() if i in missing and j in extra}
            if not recovered:
                break
            numbered.update(recovered)
            pairs.extend(recovered)
            missing = [i for i in missing if i not in {i for i, _ in recovered}]
            extra = [j for j in extra if j not in {j for _, j in recovered}]
            # A proven number link can also release a former location/title tie.
            more, mi, ex = match_items([left[i] for i in missing], [right[j] for j in extra])
            resolved = [(missing[i], extra[j]) for i, j in more]
            released.update(resolved)
            pairs.extend(resolved)
            missing, extra = [missing[i] for i in mi], [extra[j] for j in ex]
    pairs.sort()
    records = []
    for gi, pi in pairs:
        common = gold_titles(gold[gi]) & {norm(v["raw"]) for v in right[pi]["title"]["values"]}
        records.append(
            {
                "gold_index": gi,
                "pipeline_index": pi,
                "gold_key": gold[gi]["item_key"],
                "pipeline_key": pipeline[pi]["score_id"],
                "basis": {
                    "overlap_pack_lines": overlap(
                        gold[gi]["occurrences"], pipeline[pi]["occurrences"]
                    ),
                    "normalized_title_matches": sorted(common),
                    "task_no_used": (gi, pi) in numbered,
                    "normalized_task_no": numbered.get((gi, pi)),
                    "pairing_phase": "task_no" if (gi, pi) in numbered else (
                        "location_title_after_task_no" if (gi, pi) in released else "location_title"
                    ),
                    "algorithm": "mutual unique maximum overlap + title, iterative 1:1"
                    + ("; unresolved: globally mutual unique task_no" if use_task_no else ""),
                },
            }
        )
    return records, missing, extra


def wilson(success: int, total: int) -> dict:
    if not total:
        return {"numerator": success, "denominator": total, "value": None, "ci95": [None, None]}
    z = 1.959963984540054
    p = success / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    delta = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return {
        "numerator": success,
        "denominator": total,
        "value": p,
        "ci95": [max(0, center - delta), min(1, center + delta)],
    }


class SourceMap:
    """Map actual S4 character offsets to sealed pack lines by exact text equality."""

    def __init__(self, root: Path, s4: list[dict]):
        self.root = root
        self.index = read(root / "data/gold/pack/index.json")
        seal = read(root / "data/gold/SEAL.json")
        self.sources = {s["sha256"]: s for s in seal["sources"]}
        self.pack = {
            r["doc_id"]: (root / f"data/gold/pack/{r['doc_id']}.md").read_text(encoding="utf-8")
            for r in self.index
        }
        self.records = defaultdict(list)
        self.diagnostics = []
        for report in s4:
            for doc in report["documents"]:
                # S6d-1: ZIP members are independent S4 documents keyed by the
                # parent archive hash and member name.
                digest = doc.get("parent_sha256") or doc["sha256"]
                source = self.sources.get(digest)
                if not source or source["original_path"] != doc["original_path"]:
                    raise ValueError(f"unsealed pipeline source {doc['original_path']}")
                conversion = read(root / doc["converted_path"])
                if doc.get("parent_sha256") and doc.get("member_name") is not None:
                    children = [{**conversion, "member_name": doc["member_name"]}]
                else:
                    children = conversion.get("children", [conversion])
                cursor = 0
                for child in children:
                    rows = [
                        r
                        for r in self.index
                        if r["source_sha256"] == digest
                        and r["zip_child"] == child.get("member_name", "")
                    ]
                    if len(rows) != 1:
                        raise ValueError(f"ambiguous source hash/member name {digest}")
                    row = rows[0]
                    text = child["text"]
                    offset = conversion["text"].find(text, cursor) if text else -1
                    packed = self.pack[row["doc_id"]]
                    for heading in (
                        f"doc_id = {row['doc_id']}",
                        f"원문 파일명 = {row['original_filename']}",
                        f"ZIP 자식명 = {row['zip_child']}",
                    ):
                        if heading not in packed.splitlines()[:20]:
                            raise ValueError(f"pack header mismatch {row['doc_id']}")
                    marker = packed.index("## kordoc\n\n") + len("## kordoc\n\n")
                    exact = bool(text) and packed.startswith(text, marker) and offset >= 0
                    self.diagnostics.append(
                        {
                            "doc_id": row["doc_id"],
                            "exact_kordoc": exact,
                            "source_sha256": digest,
                            "filename": row["original_filename"],
                            "zip_child": row["zip_child"],
                        }
                    )
                    if exact:
                        self.records[doc["converted_path"]].append(
                            {
                                "doc_id": row["doc_id"],
                                "start": offset,
                                "end": offset + len(text),
                                "child_id": child_identifier(digest, child)
                                if "children" in conversion
                                else None,
                                "pack_offset": marker,
                                "line_starts": [0] + [m.end() for m in re.finditer("\n", packed)],
                            }
                        )
                    cursor = max(cursor, offset + len(text))

    def locate(self, path: str, locator: dict) -> list[dict]:
        found = []
        for record in self.records[path]:
            start = max(locator["start"], record["start"])
            end = min(locator["end"], record["end"])
            if start >= end:
                continue
            base = record["pack_offset"] - record["start"]
            found.append(
                {
                    "doc_id": record["doc_id"],
                    "line_start": bisect.bisect_right(record["line_starts"], base + start),
                    "line_end": bisect.bisect_right(record["line_starts"], base + end - 1),
                }
            )
        return found


def classify(item: dict, gold: list[dict], matched: list[dict]) -> str:
    if item.get("subject_status") not in (None, "target"):
        return "다른 교과"
    if item.get("grade") == 3:
        return "중3"
    title = str(pipeline_field(item, "title").get("value") or "")
    if re.search(r"지필|중간고사|기말고사|\d차고사", title):
        return "지필평가"
    strings = {
        norm(s)
        for n in ("title", "task_text")
        for s in raw_values(pipeline_field(item, n)["value"])
    } - {""}
    peers = [g for g in gold if all(g[k] == item[k] for k in ("school_id", "grade", "semester"))]
    paired_keys = {p["gold_key"] for p in matched}
    if any(
        g["item_key"] not in paired_keys
        and (overlap(item["occurrences"], g["occurrences"]) or strings & gold_titles(g))
        for g in peers
    ):
        return "짝짓기 보류"
    generic_title = not title or re.fullmatch(r"(?:\d+\s*/\s*)?수행평가\s*\d+", title.strip())
    summary_overlap = (
        item.get("table_role") == "summary"
        and generic_title
        and any(overlap(item["occurrences"], g["occurrences"]) for g in peers)
    )
    if (
        summary_overlap
        or item.get("candidate_role") == "summary_duplicate"
        or any(
            strings & gold_titles(g)
            for g in peers
            if g["item_key"] in {p["gold_key"] for p in matched}
        )
    ):
        return "요약·중복"
    if item.get("candidate_role") in {"teaching_plan", "general_standards", "affective", "other"}:
        return "운영표·규정"
    if (
        item.get("candidate_role") == "performance"
        and item.get("grade") in {1, 2}
        and item.get("semester") in {1, 2}
        and title
    ):
        return "정답 누락 가능성"
    return "기타"


def unmatched_record(item: dict, gold: list[dict], pairs: list[dict]) -> dict:
    category = classify(item, gold, pairs)
    reason = {
        "다른 교과": "정답에 없는 비과학",
        "중3": "중3",
        "지필평가": "지필",
        "요약·중복": "중복",
        "짝짓기 보류": "짝짓기 보류",
        "정답 누락 가능성": "실제 누락 의심",
        "운영표·규정": "짝짓기 보류",
        "기타": "짝짓기 보류",
    }[category]
    return {
        "pipeline_key": item["score_id"],
        "school": item["school"],
        "grade": item["grade"],
        "semester": item["semester"],
        "title": pipeline_field(item, "title").get("value"),
        "classification": category,
        "estimated_reason": reason,
        "reason_detail": category,
        "candidate_role": item["candidate_role"],
        "table_role": item.get("table_role"),
        "extraction_status": item.get("extraction_status"),
        "public_eligible": item.get("public_eligible", False),
        "review_reasons": item.get("review_reasons", []),
        "locator": item["locator"],
        "locations": item["occurrences"],
        "source": item["original_path"],
        "included_in_precision": independent(item) and item.get("candidate_role") == "performance",
    }


def pairing_failure(
    gold: dict, pipeline: list[dict], pairs: list[dict],
    gold_items: list[dict], selected: list[dict],
) -> dict:
    """Describe unresolved identity using only group, location, title and number."""
    peers = [
        p for p in pipeline
        if all(p[k] == gold[k] for k in ("school_id", "grade", "semester"))
    ]
    paired = {p["pipeline_key"]: p["gold_key"] for p in pairs}
    selected_keys = {p["score_id"] for p in selected}
    eligible = [p for p in peers if p["score_id"] in selected_keys]

    def rank(g: dict, p: dict) -> tuple[int, bool]:
        titles = {
            norm(s) for name in ("title", "task_text")
            for s in raw_values(pipeline_field(p, name).get("value"))
        } - {""}
        return overlap(g["occurrences"], p["occurrences"]), bool(gold_titles(g) & titles)

    maximum = max((rank(gold, p) for p in eligible), default=(0, False))
    best = [p for p in eligible if rank(gold, p) == maximum] if any(maximum) else []
    if not eligible:
        location_reason = "해당 단계에 같은 학교·학년·학기의 독립 수행 후보 없음"
    elif not best:
        location_reason = "위치 겹침·제목 일치 없음"
    elif all(p["score_id"] in paired for p in best):
        location_reason = "위치·제목 최대 후보가 이미 다른 정답에 연결됨"
    elif len(best) > 1:
        location_reason = f"위치·제목 최대 후보 {len(best)}개 동률"
    else:
        p = best[0]
        remaining_gold = [
            g for g in gold_items
            if all(g[k] == gold[k] for k in ("school_id", "grade", "semester"))
            and g["item_key"] not in set(paired.values())
        ]
        reverse_maximum = max(rank(g, p) for g in remaining_gold)
        competing = [g for g in remaining_gold if rank(g, p) == reverse_maximum]
        location_reason = (
            "후보가 다른 정답과 더 큰 위치·제목 일치"
            if reverse_maximum > maximum else
            f"후보의 위치·제목 최대가 정답 {len(competing)}개와 동률"
            if len(competing) > 1 else "위치·제목 상호 유일 최대 불성립"
        )
    number = identity_number(gold, is_gold=True)
    same_number = [p for p in eligible if number and identity_number(p, is_gold=False) == number]
    if not number:
        number_reason = "정답 task_no 부재·모호"
    elif not same_number:
        number_reason = "해당 단계의 파이프라인 동일 번호 부재·모호"
    else:
        number_reason = "번호 양방향 유일성 미충족 또는 후보 기짝짓기"
    return {
        "gold_key": gold["item_key"],
        "grade": gold["grade"],
        "semester": gold["semester"],
        "title": gold.get("representative_title", {}).get("raw", ""),
        "locations": gold["occurrences"],
        "normalized_task_no": number,
        "reason": location_reason + "; " + number_reason,
        "location_title_reason": location_reason,
        "task_no_reason": number_reason,
        "candidates": [
            {
                "pipeline_key": p["score_id"],
                "title": pipeline_field(p, "title").get("value"),
                "extraction_status": p.get("extraction_status"),
                "public_eligible": p.get("public_eligible", False),
                "candidate_role": p.get("candidate_role"),
                "eligible_for_stage": p["score_id"] in selected_keys,
                "locations": p["occurrences"],
                "locator": p["locator"],
                "normalized_task_no": identity_number(p, is_gold=False),
                "paired_to": paired.get(p["score_id"]),
                "overlap_pack_lines": overlap(gold["occurrences"], p["occurrences"]),
            }
            for p in peers
        ],
    }


def seal_check(root: Path) -> dict:
    seal = read(root / "data/gold/SEAL.json")
    records = [(root / r["original_path"], r["sha256"]) for r in seal["sources"]]
    records += [(root / "data/gold" / r["raw_path"], r["sha256"]) for r in seal["sources"]]
    records += [(root / "data/gold" / r["path"], r["sha256"]) for r in seal["pack_files"]]
    records += [(root / seal[k]["path"], seal[k]["sha256"]) for k in ("guide", "schema")]
    errors = [
        str(p.relative_to(root))
        for p, digest in records
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != digest
    ]
    return {"checked": len(records), "mismatches": errors}


def score(
    root: Path, gold_path: Path, meta_path: Path, rounds: list[str], *, use_task_no: bool = True,
) -> dict:
    labels = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines()]
    meta = read(meta_path)
    if hashlib.sha256(gold_path.read_bytes()).hexdigest() != meta["sha256"]:
        raise ValueError("gold-v1 hash mismatch")
    gold = [r for r in labels if r["type"] == "item"]
    names = [n for n in FIELD_MAP if n in meta["scored_fields"] and n not in meta["not_scored"]]
    s4 = [read(root / f"data/derived/segments/{r}.json") for r in rounds]
    s5 = [read(root / f"data/derived/subjects/{r}.json") for r in rounds]
    s6 = [read(root / f"data/derived/items/{r}.json") for r in rounds]
    mapper = SourceMap(root, s4)
    schools = {r["school_name"]: r["school_id"] for r in mapper.index}
    pipeline = []
    for report in s6:
        for row in report["items"]:
            row = {
                **row,
                "school_id": schools[row["school"]],
                "score_id": report["round"] + "/" + row["item_id"],
            }
            row["occurrences"] = mapper.locate(row["converted_path"], row["locator"])
            row["expected_child_doc_ids"] = [
                r["doc_id"]
                for r in mapper.records[row["converted_path"]]
                if row.get("child_id") and r["child_id"] == row["child_id"]
            ]
            row["child_coordinate_conflict"] = bool(row["expected_child_doc_ids"]) and any(
                loc["doc_id"] not in row["expected_child_doc_ids"] for loc in row["occurrences"]
            )
            row["field_locations"] = {
                n: [
                    loc
                    for obs in pipeline_field(row, n).get("evidence", [])
                    for loc in mapper.locate(row["converted_path"], obs["locator"])
                ]
                for n in names
            }
            pipeline.append(row)
    # Explicit non-performance roles remain in the diagnostic inventory only.
    raw_independent = [p for p in pipeline if independent(p)]
    candidates = [p for p in raw_independent if p.get("candidate_role") == "performance"]
    nonperformance = [p for p in raw_independent if p.get("candidate_role") != "performance"]
    stages = {}
    cases = []
    for stage, selected in (
        ("confirmed", [p for p in candidates if confirmed(p)]),
        ("all_candidates", candidates),
    ):
        pairs, missing, extra = pair_items(gold, selected, use_task_no=use_task_no)
        counters = {n: Counter({o: 0 for o in OUTCOMES}) for n in names}
        conflict_counts = {n: Counter() for n in names}
        relations = Counter()
        attributed = []
        for pair in pairs:
            g, p = gold[pair["gold_index"]], selected[pair["pipeline_index"]]
            results = {n: field_result(n, g, p) for n in names}
            pair["fields"] = results
            pair["pipeline_locations"] = p["occurrences"]
            pair["pipeline_title"] = pipeline_field(p, "title").get("value")
            for n, result in results.items():
                counters[n][result["result"]] += 1
                if result["gold_conflict"]:
                    conflict_counts[n][result["result"]] += 1
                if n == "standards" and result["standards_relation"]:
                    relations[result["standards_relation"]] += 1
            attributed.extend(misattributions(g, p, gold, names))
        unmatched = [unmatched_record(selected[j], gold, pairs) for j in extra]
        stages[stage] = {
            "recall": wilson(len(pairs), len(gold)),
            "precision": wilson(len(pairs), len(selected)),
            "role_counts": dict(Counter(p["candidate_role"] for p in selected)),
            "pairs": pairs,
            "missing_gold_keys": [gold[j]["item_key"] for j in missing],
            "unmatched_gold": [
                pairing_failure(gold[j], pipeline, pairs, gold, selected) for j in missing
            ],
            "unmatched_pipeline": unmatched,
            "unmatched_classification_counts": {
                name: sum(p["classification"] == name for p in unmatched)
                for name in UNMATCHED_CATEGORIES
            },
            "fields": counters,
            "conflict_fields": conflict_counts,
            "standards_relations": relations,
            "misattributions": attributed,
            "misattributions_by_field": dict(Counter(a["field"] for a in attributed)),
            "public_misattributions": sum(a["public_eligible"] for a in attributed),
            "public_item_count": sum(p.get("public_eligible") is True for p in selected),
            "recall_pass": len(pairs) / len(gold) >= 0.95 if gold else None,
            "precision_pass": len(pairs) / len(selected) >= 0.99 if selected else None,
        }
    target_sections = []
    for report in s5:
        for section in report["sections"]:
            if section["status"] == "target":
                target_sections.append(
                    {
                        **section,
                        "occurrences": mapper.locate(section["converted_path"], section["locator"]),
                    }
                )
    active_docs = {r["doc_id"] for s in target_sections for r in s["occurrences"]}
    present_docs = {r["doc_id"] for records in mapper.records.values() for r in records}
    all_pairs = {p["gold_key"]: p for p in stages["all_candidates"]["pairs"]}
    bounded_pairs = {p["gold_key"]: p for p in stages["confirmed"]["pairs"]}
    bounded_keys = set(bounded_pairs)
    failures_by_key = {r["gold_key"]: r for r in stages["all_candidates"]["unmatched_gold"]}
    loss = Counter(
        {
            "gold": len(gold),
            "document": 0,
            "section": 0,
            "candidate": 0,
            "matched": 0,
            "confirmed": 0,
        }
    )
    for g in gold:
        doc_ids = {loc["doc_id"] for loc in g["occurrences"]}
        document_found = bool(doc_ids & active_docs)
        section_found = document_found and any(
            s["grade"] == g["grade"] and overlap(s["occurrences"], g["occurrences"])
            for s in target_sections
        )
        paired = g["item_key"] in all_pairs
        bounded = g["item_key"] in bounded_keys
        # Title-only pairs can be found outside labeled ranges. Keep the map
        # monotone and record that recovery explicitly for audit.
        generated = any(
            all(p[k] == g[k] for k in ("school_id", "grade"))
            and overlap(p["occurrences"], g["occurrences"])
            for p in candidates
        )
        loss["document"] += document_found or paired
        loss["section"] += section_found or paired
        loss["candidate"] += paired or (section_found and generated)
        loss["matched"] += paired
        loss["confirmed"] += bounded
        cause = (
            "찾음"
            if paired
            else (
                "문서 제외"
                if not (doc_ids & present_docs)
                else "과학 문서 미검출"
                if not document_found
                else "구간 못 찾음"
                if not section_found
                else "짝짓기 실패"
                if generated
                else "후보 생성 실패"
            )
        )
        cases.append(
            {
                "type": "gold",
                "key": g["item_key"],
                "school": next(
                    r["school_name"] for r in mapper.index if r["school_id"] == g["school_id"]
                ),
                "grade": g["grade"],
                "semester": g["semester"],
                "title": g.get("representative_title", {}).get("raw", ""),
                "document_found": document_found,
                "section_found": section_found,
                "title_only_recovery": paired and not section_found,
                "candidate_found": paired,
                "candidate_generated": paired or generated,
                "confirmed_found": bounded,
                "cause": cause,
                "locations": g["occurrences"],
                "pipeline_key": all_pairs.get(g["item_key"], {}).get("pipeline_key", ""),
                "task_no_used": all_pairs.get(g["item_key"], {}).get("basis", {}).get(
                    "task_no_used", False
                ),
                "confirmed_task_no_used": bounded_pairs.get(g["item_key"], {}).get("basis", {}).get(
                    "task_no_used", False
                ),
                "pair_basis": all_pairs.get(g["item_key"], {}).get("basis", {}),
                "confirmed_pair_basis": bounded_pairs.get(g["item_key"], {}).get("basis", {}),
                "pairing_failure_reason": failures_by_key.get(g["item_key"], {}).get("reason", ""),
                "same_group_candidates": failures_by_key.get(g["item_key"], {}).get(
                    "candidates", []
                ),
                "confirmed_pipeline_key": bounded_pairs.get(g["item_key"], {}).get(
                    "pipeline_key", ""
                ),
                "all_field_results": {
                    n: f["result"]
                    for n, f in all_pairs.get(g["item_key"], {}).get("fields", {}).items()
                },
                "confirmed_field_results": {
                    n: f["result"]
                    for n, f in bounded_pairs.get(g["item_key"], {}).get("fields", {}).items()
                },
            }
        )
    docs = []
    for d in [r for r in labels if r["type"] == "document"]:
        doc_id = d["doc_id"]
        record = next(r for r in mapper.index if r["doc_id"] == doc_id)
        expected = d["fields"]["science_sections"]["value"]
        sections = [
            s for s in target_sections if any(loc["doc_id"] == doc_id for loc in s["occurrences"])
        ]
        matches = [
            any(
                s["grade"] == e["grade"] and overlap(s["occurrences"], [{"doc_id": doc_id, **e}])
                for s in sections
            )
            for e in expected
        ]
        docs.append(
            {
                "doc_id": doc_id,
                "school_id": d["school_id"],
                "school": record["school_name"],
                "filename": record["original_filename"],
                "zip_child": record["zip_child"],
                "has_gold_items": any(
                    doc_id in {o["doc_id"] for o in g["occurrences"]} for g in gold
                ),
                "science_detected": bool(sections),
                "gold_section_count": len(expected),
                "overlapping_section_count": sum(matches),
                "any_section_overlap": any(matches),
                "all_sections_overlap": bool(matches) and all(matches),
                "edition_gold": d["fields"]["edition"]["value"],
                "processing_result": "대상 과학 구간 처리"
                if sections
                else (
                    "S4 변환·문서 제외"
                    if doc_id not in present_docs
                    else "S5 대상 과학 구간 미검출"
                    if expected
                    else "대상 과학 구간 없음 · 중3·타교과 또는 미확정"
                ),
            }
        )
    failures = []
    for report in s4:
        for d in report["documents"]:
            if d["conversion_status"] != "ok" or not d["segments"]:
                failures.append(
                    {
                        "round": report["round"],
                        "school": d["source"]["school_name"],
                        "source": d["original_path"],
                        "stage": "S4",
                        "reason": d["conversion_status"],
                        "error": d.get("conversion_error"),
                    }
                )
        failures += [
            {"round": report["round"], "stage": "S4", "reason": "non_plan_filename", **r}
            for r in report["excluded_non_plan"]
        ]
        failures += [
            {
                **r,
                "round": report["round"],
                "stage": "수집기 기록",
                "reason": r["result"],
                "school": r.get("school_name", ""),
                "original_path": r.get("candidate_name", ""),
            }
            for r in report["incomplete_sources"]
        ]
    for report in s6:
        failures += [{"round": report["round"], "stage": "S6", **r} for r in report["excluded"]]
    for p in stages["all_candidates"]["unmatched_pipeline"]:
        cases.append(
            {
                "type": "pipeline_unmatched",
                "key": p["pipeline_key"],
                "school": p["school"],
                "grade": p["grade"],
                "semester": p["semester"],
                "title": p["title"],
                "cause": p["classification"],
                "locations": p["locations"],
                "source": p["source"],
            }
        )
    for p in nonperformance:
        cases.append(
            {
                "type": "pipeline_nonperformance",
                "key": p["score_id"],
                "school": p["school"],
                "grade": p["grade"],
                "semester": p["semester"],
                "title": pipeline_field(p, "title").get("value"),
                "cause": classify(p, gold, stages["all_candidates"]["pairs"]),
                "locations": p["occurrences"],
                "source": p["original_path"],
                "candidate_role": p["candidate_role"],
            }
        )
    raw_pairs, _, raw_extra = pair_items(gold, raw_independent, use_task_no=use_task_no)
    confirmed_pair_keys = {p["pipeline_key"] for p in stages["confirmed"]["pairs"]}
    unmatched_confirmed = [
        unmatched_record(p, gold, stages["confirmed"]["pairs"])
        for p in pipeline if confirmed(p) and p["score_id"] not in confirmed_pair_keys
    ]
    case_by_key = {c["key"]: c for c in cases if c["type"] == "gold"}
    pairing_failures = [
        {**row, "school": case_by_key[row["gold_key"]]["school"]}
        for row in stages["all_candidates"]["unmatched_gold"]
        if case_by_key[row["gold_key"]]["cause"] == "짝짓기 실패"
    ]
    return {
        "version": "gold-v1.1" if use_task_no else "gold-v1",
        "gold_sha256": meta["sha256"],
        "rounds": rounds,
        "scored_fields": names,
        "field_map": FIELD_MAP,
        "acceptance_thresholds": {
            "recall_min": 0.95,
            "precision_min": 0.99,
            "public_misattributions_max": 0,
        },
        "stages": stages,
        "unmatched_confirmed_pipeline": unmatched_confirmed,
        "remaining_pairing_failures": pairing_failures,
        "loss_map": loss,
        "cases": cases,
        "documents": docs,
        "failures_exclusions": failures,
        "source_mapping": mapper.diagnostics,
        "seal": seal_check(root),
        "zip_coordinate_conflicts": [
            {
                "pipeline_key": p["score_id"],
                "expected_doc_ids": p["expected_child_doc_ids"],
                "actual_text_locations": p["occurrences"],
            }
            for p in pipeline
            if p["child_coordinate_conflict"]
        ],
        "raw_independent_diagnostic": {
            "count": len(raw_independent),
            "performance_count": len(candidates),
            "nonperformance_count": len(nonperformance),
            "nonperformance_roles": dict(Counter(p["candidate_role"] for p in nonperformance)),
            "recall": wilson(len(raw_pairs), len(gold)),
            "precision": wilson(len(raw_pairs), len(raw_independent)),
            "unmatched_count": len(raw_extra),
        },
        "excluded_summary_aliases": [p["score_id"] for p in pipeline if not independent(p)],
        "status_counts": {
            n: dict(Counter(str(p.get(n)) for p in pipeline))
            for n in (
                "candidate_role",
                "extraction_status",
                "completeness_status",
                "public_eligible",
            )
        },
        "gold_omission_review": [
            p
            for p in stages["all_candidates"]["unmatched_pipeline"]
            if p["classification"] == "정답 누락 가능성"
        ],
        "identity_unresolved_review": [
            p
            for p in stages["all_candidates"]["unmatched_pipeline"]
            if p["semester"] not in {1, 2} and p["title"]
        ],
    }


def metric(value: dict) -> str:
    if value["value"] is None:
        return "분모 0"
    low, high = value["ci95"]
    return (
        f"{value['numerator']}/{value['denominator']} = {value['value']:.2%} ({low:.2%}–{high:.2%})"
    )


def cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def location_text(row: dict) -> str:
    parts = [
        f"{loc['doc_id']}:{loc.get('line_start', loc.get('line'))}"
        f"–{loc.get('line_end', loc.get('line_start', loc.get('line')))}"
        for loc in row.get("locations", [])
    ]
    locator = row.get("locator")
    if locator:
        parts.append(f"문자 {locator['start']}–{locator['end']}")
    return "; ".join(parts) or "위치 없음"


def markdown(report: dict) -> str:
    stages = report["stages"]
    lines = [
        "# S9 ⑧ 채점기 v1.1 · 정답 v1",
        "",
        "두 공시 회차·10개교·정답 83항목. 추출 규칙·패턴·임계값 변경 0. 오프라인 실행.",
        "",
        "## 단계와 비교 규칙",
        "",
        "전체 후보는 candidate_role=performance인 독립 수행 후보 전부다. identity_relation이 "
        "있는 summary_duplicate는 제외한다. 명시적으로 다른 역할인 운영표·진도표·성취수준 "
        "행은 진단 목록에 보존한다. 확정 단계는 이 중 extraction_status=bounded "
        "또는 public_eligible=true다. completeness_status는 완전성 인증을 뜻하지 않아 "
        "추가 필터로 사용하지 않는다.",
        "",
        "같은 학교·학년·학기에서 pack 줄 겹침의 상호 유일 최대를 1대1로 잇고 제목으로 "
        "동률을 해소한다. 위치가 없어도 정규화 제목·별칭·과제 설명이 양방향 유일 일치하면 "
        "잇는다. 기존 gold_diff.match_items를 재사용했다. "
        "각 단계에서 따로 짝지으므로 같은 정답에 대응하는 요약·상세 행은 단계별로 달라질 수 있다.",
        "",
        "v1.1은 기존 위치·제목 짝을 먼저 보존한 뒤 미짝 항목만 task_no로 보완한다. "
        "정답 task_no 값과 파이프라인 task_no 또는 번호뿐인 제목(수행평가 1·1·① 등)을 "
        "NFKC·공백·문장부호 정규화해 번호를 얻는다. 같은 학교·학년·학기의 해당 단계 "
        "입력 전체에서 양방향 유일할 때만 잇고, 여러 번호·충돌·남은 동률은 보류한다. "
        "번호로 연결한 뒤 위치·제목을 다시 검사하되, 번호 유일성은 이미 짝지은 항목까지 "
        "포함해 검사한다. 각 짝 basis.task_no_used와 normalized_task_no에 근거를 남긴다.",
        "",
        "짝짓기는 위치·제목·별칭·기존 과제명(task_text)과 연결용 task_no만 사용한다. "
        "성취기준·점수·비율·시기·방법·채점기준 등 채점할 필드 값의 일치는 짝짓기나 "
        "동률 해소에 사용하지 않는다. 채점 대상을 연결 근거로 사용해 필드 점수가 "
        "부풀려지는 것을 막는다. task_no 자체는 필드 채점에서 계속 제외한다.",
        "",
        "원문 해시를 SEAL과 대조하고 ZIP 자식명·pack 머리의 파일명으로 doc_id를 정한다. "
        "S4 실제 텍스트와 pack kordoc 본문이 완전 일치할 때만 문자 위치를 줄로 바꾼다. "
        "pymupdf 사본 위치만 있는 정답은 제목 짝짓기로 복구할 수 있다.",
        "",
        "제목은 대표 제목·aliases·승인된 제목 중 하나와 정규화 일치하면 정답이다. "
        "HTML·공백·문장부호를 제거하고 소문자화한다. 방법은 checked/selected 선택지만 "
        "포함하고 plain_text·other_text를 합쳐 쉼표·슬래시·줄바꿈으로 나눈 집합을 비교한다. "
        "동의어 확장은 하지 않는다. 성취기준은 코드 집합, 숫자는 norm 값, 세부배점은 "
        "요소명·숫자 집합으로 비교한다. 채점기준은 추출 근거가 정답 전용 채점표 위치와 "
        "겹쳐야 한다. free_semester는 명시된 bool 필드만 채점하며 추론하지 않는다.",
        "",
        "conflict는 원문 보존 값 하나 이상 또는 파이프라인 conflict 표시를 인정하고 "
        "별도 집계한다. 미확정 필드는 누락으로, source_absent 정답에 확정 값을 내면 "
        "허위값으로 센다. task_no는 채점에서 제외한다.",
        "",
        "## v1과 v1.1 성적 비교",
        "",
        "수치 괄호는 Wilson 95% 구간이다.",
        "",
        "동일 입력으로 v1 기존 규칙과 v1.1 번호 보완 규칙을 각각 재계산한다. "
        "기존 gold-v1 산출물은 덮어쓰지 않는다. 재현율 기준 ≥95%, 정밀도 기준 ≥99%.",
        "",
        "| 단계 | v1 재현율 | v1.1 재현율 | v1 정밀도 | v1.1 정밀도 | 번호 직접 사용 |",
        "|---|---|---|---|---|---:|",
    ]
    for key, label in (("confirmed", "확정"), ("all_candidates", "전체 후보")):
        s = stages[key]
        before = report["comparison"]["v1"]["stages"][key]
        lines.append(
            f"| {label} | {metric(before['recall'])} | {metric(s['recall'])} | "
            f"{metric(before['precision'])} | {metric(s['precision'])} | "
            f"{sum(p['basis']['task_no_used'] for p in s['pairs'])} |"
        )
    lines += [
        "",
        "공개 항목이 0이면 공개 오귀속 0은 무노출 관찰치다. 항목 합격 여부는 점추정치로 비교한다.",
        "합격선 판정: " + "; ".join(
            f"{label} 재현율 {'통과' if stages[key]['recall_pass'] else '미달'}·"
            f"정밀도 {'통과' if stages[key]['precision_pass'] else '미달'}"
            for key, label in (("confirmed", "확정"), ("all_candidates", "전체 후보"))
        ) + ".",
        "공개 필드 오귀속: " + "; ".join(
            f"{label} {stages[key]['public_misattributions']}건 / "
            f"공개 항목 {stages[key]['public_item_count']}개"
            for key, label in (("confirmed", "확정"), ("all_candidates", "전체 후보"))
        ) + ".",
        "",
        "## 단계별 손실 지도",
        "",
        " → ".join(
            f"{label} {report['loss_map'][key]}개"
            for key, label in (
                ("gold", "정답"),
                ("document", "과학 문서에서"),
                ("section", "과학 구간에서"),
                ("candidate", "후보에서"),
                ("matched", "1대1 짝에서"),
                ("confirmed", "확정에서"),
            )
        ),
        "",
        "문서·구간은 정답 위치가 검출된 대상 과학 구간에 겹치는지 검사한다. "
        "후보 단계는 같은 학교·학년의 수행 후보가 정답 위치에 겹친 수다. "
        "학기 미확정·짝짓기 동률은 다음 1대1 단계에서 손실로 센다. "
        "위치 밖에서 제목·번호로 복구한 짝은 앞 단계에도 포함한다. 기존 호환 필드 "
        "cases.title_only_recovery는 구간 밖 복구를 뜻하며, 실제 근거는 pair_basis로 구분한다.",
        "",
        "## 큰 실패 원인 상위 5",
        "",
    ]
    missing = [c for c in report["cases"] if c["type"] == "gold" and c["cause"] != "찾음"]
    causes = Counter(c["cause"] for c in missing)
    review = [
        c
        for c in report["cases"]
        if c["type"] == "gold" and c["candidate_found"] and not c["confirmed_found"]
    ]
    if review:
        causes["후보 경계 미확정"] = len(review)
    for cause, count in causes.most_common(5):
        example = next(
            c
            for c in (review if cause == "후보 경계 미확정" else missing)
            if cause == "후보 경계 미확정" or c["cause"] == cause
        )
        lines.append(
            f"- {cause} {count}개. {example['school']} 중{example['grade']} "
            f"{cell(example['title'])} · `{example['key']}`"
        )
    diagnostic = report["raw_independent_diagnostic"]
    lines += [
        "",
        f"보조 진단에서 역할 구분 전 독립 행은 {diagnostic['count']}개, "
        f"비수행 역할은 {diagnostic['nonperformance_count']}개다. "
        f"모든 행을 분모로 잡으면 재현율 {metric(diagnostic['recall'])}, "
        f"정밀도 {metric(diagnostic['precision'])}다. 공식 전체 후보 성적은 수행 역할 기준이다.",
        "",
        f"ZIP 자식 ID와 실제 텍스트 좌표 충돌은 "
        f"{len(report['zip_coordinate_conflicts'])}개다. 신정중 ZIP의 자식별 S4 좌표가 "
        "S5의 합친 텍스트에서 사용되는 기존 경로에서 관찰했다. 실제 S6 근거가 가리키는 "
        "본문으로 채점했으며 개별 충돌은 JSON에 보존했다.",
        "",
        "## 짝 없는 확정 파이프라인 항목 전부 · v1.1",
        "",
        f"{len(report['unmatched_confirmed_pipeline'])}개. 역할 제외·중복 별칭을 포함해 원본 "
        "파이프라인의 모든 bounded/public_eligible 행을 검사한다. 공식 정밀도 분모 포함 "
        "여부를 별도로 표시한다. 추정 이유는 검토 제안이며 정답 누락 확정이 아니다. "
        "문자 위치는 끝 제외다.",
        "",
        "| 학교 | 학년 | 학기 | 제목 | 역할 / 표 역할 | 위치 | 추정 이유 | 정밀도 포함 | 항목 키 |",
        "|---|---:|---:|---|---|---|---|---|---|",
    ]
    for p in report["unmatched_confirmed_pipeline"]:
        lines.append("| " + " | ".join(map(cell, (
            p["school"], p["grade"], p["semester"], p["title"],
            f"{p['candidate_role']} / {p['table_role']}", location_text(p),
            f"{p['estimated_reason']} ({p['reason_detail']})",
            "예" if p["included_in_precision"] else "아니오", p["pipeline_key"],
        ))) + " |")
    if not report["unmatched_confirmed_pipeline"]:
        lines.append("| - | - | - | - | - | - | 없음 | - | - |")
    lines += [
        "",
        "## 남은 짝짓기 실패 정답 전부 · v1.1 전체 후보 기준",
        "",
        f"{len(report['remaining_pairing_failures'])}개. 손실 지도에서 짝짓기 실패로 남은 "
        "정답을 모두 싣는다. 후보 목록은 같은 학교·학년·학기 원본 행 전체이며 "
        "제목·상태·역할·위치·기짝짓기 대상을 생략하지 않는다. 후보 미생성 등 다른 "
        "누락과 확정 단계의 모든 미짝 정답도 JSON stages.*.unmatched_gold에 남긴다.",
        "",
        "| 학교 | 학년 | 학기 | 정답 키 · 제목 | "
        "같은 집단 후보: 제목 · 상태 · 역할 · 위치 · 기짝짓기 | 실패 이유 |",
        "|---|---:|---:|---|---|---|",
    ]
    for row in report["remaining_pairing_failures"]:
        candidates = "<br>".join(
            cell(f"{p['title'] or '(제목 없음)'} · "
                 f"{p['extraction_status']} / public={p['public_eligible']} · "
                 f"{p['candidate_role']} · {location_text(p)} · "
                 f"짝={p['paired_to'] or '없음'} · {p['pipeline_key']}")
            for p in row["candidates"]
        ) or "없음"
        lines.append(
            f"| {cell(row['school'])} | {row['grade']} | {row['semester']} | "
            f"{cell(row['gold_key'])} · {cell(row['title'])} | "
            f"{candidates} | {cell(row['reason'])} |"
        )
    if not report["remaining_pairing_failures"]:
        lines.append("| - | - | - | - | - | 없음 |")
    for key, label in (("confirmed", "확정"), ("all_candidates", "전체 후보")):
        s = stages[key]
        lines += [
            "",
            f"## {label} 필드",
            "",
            "| 필드 | 정답 | 누락 | 오값 | 허위값 | 둘다없음 | conflict 정답/대상 | 오귀속 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for n, counts in s["fields"].items():
            conflict = s["conflict_fields"][n]
            lines.append(
                "| "
                + n
                + " | "
                + " | ".join(str(counts[o]) for o in OUTCOMES)
                + f" | {conflict.get('정답', 0)}/{sum(conflict.values())} | "
                f"{s['misattributions_by_field'].get(n, 0)} |"
            )
        lines += [
            "",
            f"성취기준 집합 관계 {dict(s['standards_relations'])}",
            "",
            f"필드 오귀속 {len(s['misattributions'])}건. 한 값이 여러 항목과 같아도 "
            "항목·필드당 1건으로 센다.",
            "",
        ]
        for error in s["misattributions"]:
            lines.append(
                f"- `{error['gold_key']}` · {error['field']} · 값 {cell(error['value'])} "
                f"· 다른 정답 {', '.join(error['other_gold_keys'])}"
            )
        categories = s["unmatched_classification_counts"]
        lines += ["", f"미짝 후보 분류 {categories}"]
    docs = [d for d in report["documents"] if d["has_gold_items"]]
    sections = [d for d in report["documents"] if d["gold_section_count"]]
    lines += [
        "",
        "## 문서 지표",
        "",
        f"정답 항목이 있는 문서 {len(docs)}개 중 과학 검출 "
        f"{sum(d['science_detected'] for d in docs)}개. "
        f"정답 과학 구간과 하나 이상 겹친 문서는 {sum(d['any_section_overlap'] for d in docs)}개. "
        f"정답 science_sections {sum(d['gold_section_count'] for d in sections)}개 중 "
        f"겹친 구간 {sum(d['overlapping_section_count'] for d in sections)}개. "
        "중복 변환 사본도 정답 기록대로 분모에 보존한다. "
        "kordoc 대응 여부는 JSON에서 확인한다.",
        "",
        "## 정답 누락 가능성 · 총괄 확인",
        "",
        "아래는 미짝 performance 후보의 보수적 확인 목록이다. 짝짓기 실패·중복·오검출도 "
        "포함될 수 있어 정답 누락으로 확정하지 않는다.",
        "",
    ]
    for p in report["gold_omission_review"]:
        lines.append(
            f"- {p['school']} 중{p['grade']} {p['semester']}학기 · {cell(p['title'])} "
            f"· `{p['pipeline_key']}` · {cell(p['locations'])}"
        )
    if not report["gold_omission_review"]:
        lines.append("확인 대상 0개.")
    if report["identity_unresolved_review"]:
        lines += [
            "",
            "학기가 미확정된 아래 후보는 정답 누락 가능성과 분리해 짝짓기 보류로 남긴다.",
            "",
        ]
        for p in report["identity_unresolved_review"]:
            lines.append(
                f"- {p['school']} 중{p['grade']} · {cell(p['title'])} "
                f"· 학기 미확정 · {cell(p['locations'])}"
            )
    lines += [
        "",
        "## 실패·제외 기록",
        "",
        "| 회차 | 단계 | 학교 | 문서·구간 | 이유 |",
        "|---|---|---|---|---|",
    ]
    for failure in report["failures_exclusions"]:
        lines.append(
            "| "
            + " | ".join(
                cell(failure.get(k, ""))
                for k in ("round", "stage", "school", "original_path", "reason")
            )
            + " |"
        )
    if not report["failures_exclusions"]:
        lines.append("| - | - | - | - | 실행 실패·제외 없음 |")
    lines += [
        "",
        "## pack 문서별 처리 결과",
        "",
        "| 학교 | doc_id | 원문·ZIP 자식명 | 결과 |",
        "|---|---|---|---|",
    ]
    for d in report["documents"]:
        lines.append(
            "| "
            + " | ".join(
                map(
                    cell,
                    (
                        d["school"],
                        d["doc_id"],
                        d["zip_child"] or d["filename"],
                        d["processing_result"],
                    ),
                )
            )
            + " |"
        )
    lines += [
        "",
        "## 봉인 검증",
        "",
        f"{report['seal']['checked']}개 해시 대조, 불일치 {len(report['seal']['mismatches'])}개.",
        "",
    ]
    if "development_hashes" in report:
        hashes = report["development_hashes"]
        lines += [
            "",
            "## 개발 산출물 수정 전후 SHA-256",
            "",
            f"{len(hashes)}개 파일 중 불일치 {sum(not row['equal'] for row in hashes)}개.",
            "",
            "| 파일 | 수정 전 | 수정 후 | 바이트 동일 |",
            "|---|---|---|---|",
        ]
        for row in hashes:
            lines.append(
                f"| {row['path']} | `{row['before']}` | `{row['after']}` "
                f"| {'동일' if row['equal'] else '불일치'} |"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=ROOT / "data/gold/gold_v1.jsonl")
    parser.add_argument("--meta", type=Path, default=ROOT / "data/gold/gold_v1.meta.json")
    parser.add_argument("--round-keys", nargs="+", default=list(ROUNDS))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/derived/gold_score")
    args = parser.parse_args()
    baseline_report = score(ROOT, args.gold, args.meta, args.round_keys, use_task_no=False)
    report = score(ROOT, args.gold, args.meta, args.round_keys)
    report["comparison"] = {
        version: {
            "stages": {
                stage: {
                    k: result[k] for k in (
                        "recall", "precision", "fields", "conflict_fields",
                        "misattributions_by_field", "public_misattributions",
                    )
                }
                for stage, result in source["stages"].items()
            },
            "loss_map": source["loss_map"],
        }
        for version, source in (("v1", baseline_report), ("v1.1", report))
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    baseline = args.output_dir / "development-before.json"
    if baseline.exists():
        hashes = []
        for path, before in read(baseline).items():
            target = ROOT / path
            after = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
            hashes.append(
                {"path": path, "before": before, "after": after, "equal": before == after}
            )
        report["development_hashes"] = hashes
    (args.output_dir / "gold-v1.1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "gold-v1.1.md").write_text(markdown(report), encoding="utf-8")
    columns = list(dict.fromkeys(k for row in report["cases"] for k in row))
    csv_path = args.output_dir / "gold-v1.1.cases.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in report["cases"]:
            writer.writerow(
                {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                    for k, v in row.items()
                }
            )
    print(
        json.dumps(
            {k: {m: s[m] for m in ("recall", "precision")} for k, s in report["stages"].items()},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
