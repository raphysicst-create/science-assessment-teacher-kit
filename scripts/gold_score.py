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
    "sub_scores": "sub_scores",
    "ratio": "weight",
    "rubric": "rubric",
    "free_semester": "free_semester",
}
OUTCOMES = ("정답", "부분", "누락", "오값", "허위값", "둘다없음")
FIELD_COLUMNS = (*OUTCOMES, "미추출", "오귀속")
AI_UNEXTRACTED_REASON = "AI 읽기 1단계: 필드 미추출"
FIELD_RULES = {
    "title": "대표 제목·별칭·승인된 제목 중 하나와 정규화 일치",
    "task_text": (
        "문자열·문자열 목록·정답 raw 목록을 정규화한 집합의 완전 일치. "
        "완전 일치 없이 공통 원소 또는 원소 간 문자열 포함 관계가 있으면 부분. "
        "순서·중복은 무시하고 HTML·공백·문장부호를 제거하며 의미 유사도는 사용하지 않음"
    ),
    "period": "timing과 정답 raw 값의 정규화 집합 일치",
    "method": (
        "선택값 목록과 정답 checked/selected·plain_text·other_text를 "
        "쉼표·슬래시·세미콜론·줄바꿈으로 나눈 정규화 집합 일치. 동의어 확장 없음"
    ),
    "standards": "성취기준 코드 집합 일치. equal/subset/excess/different 별도 집계",
    "max_score": "score와 정답 norm 또는 raw에서 읽은 숫자 집합 일치",
    "sub_scores": (
        "sub_scores의 (element, score) 목록과 정답 (name, norm/raw) 목록을 "
        "(정규화 요소명, 숫자) 집합으로 비교. 순서·중복·근거 메타데이터는 비교에서 제외"
    ),
    "ratio": "weight와 정답 norm 또는 raw에서 읽은 숫자 집합 일치",
    "rubric": (
        "필드 evidence·값 내부 evidence/locator·table_locators를 pack 줄로 변환해 "
        "승인된 정답 채점표 위치와 하나 이상 겹치면 정답. 수준 문장 일치는 요구하지 않음"
    ),
    "free_semester": "명시된 bool의 동일성. false도 값이 있는 것으로 처리하고 추론하지 않음",
}
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
    if name == "task_text":
        return frozenset(norm(s) for s in raw_values(value) if norm(s))
    if name == "sub_scores" and isinstance(value, (dict, list)):
        values = value.get("values", [value]) if isinstance(value, dict) else value
        return frozenset(
            (norm(v.get("element", v.get("name", ""))), n)
            for v in values
            for n in (content("max_score", v["score"]) if "score" in v else numeric_values(v))
        )
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
            return frozenset(n for v in values for n in numeric_values(v))
        numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
        return frozenset(float(n) for n in numbers)
    if isinstance(value, dict):
        return frozenset(norm(s) for s in raw_values(value) if norm(s))
    return frozenset([norm(value)]) if value not in (None, "", []) else frozenset()


def pipeline_field(item: dict, name: str) -> dict:
    return item.get("fields", {}).get(FIELD_MAP[name], {"status": "unconfirmed", "value": None})


def field_observations(field: dict) -> list[dict]:
    """Read field-owned observations, including nested value evidence."""
    nodes = [field]
    value = field.get("value")
    if isinstance(value, dict):
        nodes.append(value)
    elif isinstance(value, list):
        nodes.extend(v for v in value if isinstance(v, dict))
    return [observation for node in nodes for observation in [node, *node.get("evidence", [])]]


def field_locators(field: dict) -> list[dict]:
    """Read field-owned source positions, excluding headers and alternate observations."""
    return [o["locator"] for o in field_observations(field) if "locator" in o] + field.get(
        "table_locators", []
    )


def ai_unextracted(item: dict, name: str) -> bool:
    field = pipeline_field(item, name)
    return (
        ai_item(item) and field.get("status") == "unconfirmed"
        and field.get("reason") == AI_UNEXTRACTED_REASON
    )


def field_result(name: str, gold: dict, item: dict) -> dict:
    expected = gold["fields"].get(name, {"status": "source_absent", "value": None})
    actual = pipeline_field(item, name)
    if ai_unextracted(item, name):
        return {"result": "미추출", "gold_conflict": False, "standards_relation": None}
    conflict = expected.get("status") == "conflict"
    emitted = actual.get("status") == "present" and actual.get("value") not in (None, "", [])
    if name == "free_semester" and actual.get("status") == "present":
        emitted = isinstance(actual.get("value"), bool)
    if name == "rubric" and actual.get("status") == "present":
        emitted = emitted or bool(item.get("field_locations", {}).get(name))
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
    if actual.get("status") == "unconfirmed":
        return {**result, "result": "누락"}
    if expected.get("status") == "source_absent":
        if emitted:
            return {**result, "result": "허위값"}
        return {
            **result,
            "result": "둘다없음" if actual.get("status") == "source_absent" else "누락",
        }
    if not emitted:
        return {**result, "result": "누락"}
    observed = content(name, actual.get("value"))
    options = [content(name, v) for v in alternatives(expected)]
    if name == "title":
        correct = bool(observed & gold_titles(gold, task=False))
    elif name == "rubric":
        # Gold rubric is a source range, not a verbatim transcription requirement.
        correct = bool(
            overlap(
                [loc for value in alternatives(expected) for loc in locations(value)],
                item.get("field_locations", {}).get(name, []),
            )
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
    if name == "task_text" and not correct and any(
        left in right or right in left
        for option in options
        for left in observed
        for right in option
    ):
        return {**result, "result": "부분", "basis": "정규화 원소 일치·문자열 부분 포함"}
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


def ai_item(item: dict) -> bool:
    return (
        item.get("extraction_status") == "ai_verified" or item.get("extraction_method") == "ai_read"
    )


def combined_items(pipeline: list[dict], reports: list[dict]) -> list[dict]:
    """Deduplicate the a/b/c union by round-qualified item ID, retaining all support."""
    support = defaultdict(list)
    for report in reports:
        for relation in ("agrees", "agrees_by_title"):
            for row in report.get("ai_relations", {}).get(relation, []):
                if row.get("bounded") is not False:
                    continue
                ids = [row["rule_item_id"]] if relation == "agrees" else row["rule_item_ids"]
                for item_id in ids:
                    support[report["round"] + "/" + item_id].append({
                        "relation": relation, "ai_task_id": row["ai_task_id"],
                    })
    selected = []
    for item in pipeline:
        sources = []
        if not ai_item(item) and independent(item) and item.get("candidate_role") == "performance":
            if confirmed(item):
                sources.append("a")
        if item.get("extraction_status") == "ai_verified":
            sources.append("b")
        evidence = support[item["score_id"]] if not ai_item(item) else []
        sources += [
            "c_location" if relation == "agrees" else "c_title"
            for relation in ("agrees", "agrees_by_title")
            if any(row["relation"] == relation for row in evidence)
        ]
        if sources:
            selected.append({**item, "contributions": sources, "ai_support": evidence})
    return selected


def pair_combined_items(
    gold: list[dict], pipeline: list[dict], *, use_task_no: bool = True,
) -> tuple[list[dict], list[int], list[int]]:
    """Preserve primary locator/title/number pairs before AI-owned evidence fallback."""
    pairs, missing, extra = pair_items(gold, pipeline, use_task_no=use_task_no)
    for pair in pairs:
        pair["basis"]["owned_ranges_used"] = False
    fallback = [
        {
            **pipeline[j],
            "occurrences": pipeline[j].get("owned_occurrences") or pipeline[j]["occurrences"],
        }
        for j in extra
    ]
    more, _, _ = pair_items([gold[i] for i in missing], fallback, use_task_no=False)
    for pair in more:
        gi, pi = missing[pair["gold_index"]], extra[pair["pipeline_index"]]
        owned_used = (
            ai_item(pipeline[pi]) and bool(pipeline[pi].get("owned_occurrences"))
            and pair["basis"]["overlap_pack_lines"] > 0
        )
        pair.update(gold_index=gi, pipeline_index=pi)
        pair["basis"].update(
            owned_ranges_used=owned_used,
            locator_overlap_pack_lines=overlap(
                gold[gi]["occurrences"], pipeline[pi]["occurrences"],
            ),
            pairing_phase="owned_ranges" if owned_used else "location_title_after_owned_ranges",
        )
        pairs.append(pair)
    paired_gold = {p["gold_index"] for p in pairs}
    paired_pipeline = {p["pipeline_index"] for p in pairs}
    return (
        sorted(pairs, key=lambda p: p["gold_index"]),
        [i for i in missing if i not in paired_gold],
        [j for j in extra if j not in paired_pipeline],
    )


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

    def __init__(self, root: Path, s4: list[dict], gold_dir: Path | None = None):
        self.root = root
        gold_dir = root / "data/gold" if gold_dir is None else root / gold_dir
        self.index = read(gold_dir / "pack/index.json")
        seal = read(gold_dir / "SEAL.json")
        self.sources = {s["sha256"]: s for s in seal["sources"]}
        self.pack = {
            r["doc_id"]: (gold_dir / f"pack/{r['doc_id']}.md").read_text(encoding="utf-8")
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


def seal_check(root: Path, gold_dir: Path | None = None) -> dict:
    gold_dir = root / "data/gold" if gold_dir is None else root / gold_dir
    seal = read(gold_dir / "SEAL.json")
    records = [(root / r["original_path"], r["sha256"]) for r in seal["sources"]]
    records += [(gold_dir / r["raw_path"], r["sha256"]) for r in seal["sources"]]
    records += [(gold_dir / r["path"], r["sha256"]) for r in seal["pack_files"]]
    records += [(root / seal[k]["path"], seal[k]["sha256"]) for k in ("guide", "schema")]
    errors = [
        str(p.relative_to(root) if p.is_relative_to(root) else p)
        for p, digest in records
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != digest
    ]
    return {"checked": len(records), "mismatches": errors}


def score(
    root: Path, gold_path: Path, meta_path: Path, rounds: list[str], *, use_task_no: bool = True,
    items_dir: Path | None = None,
    gold_dir: Path | None = None,
) -> dict:
    labels = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines()]
    meta = read(meta_path)
    if hashlib.sha256(gold_path.read_bytes()).hexdigest() != meta["sha256"]:
        raise ValueError("gold-v1 hash mismatch")
    gold = [r for r in labels if r["type"] == "item"]
    names = [n for n in FIELD_MAP if n in meta["scored_fields"] and n not in meta["not_scored"]]
    s4 = [read(root / f"data/derived/segments/{r}.json") for r in rounds]
    s5 = [read(root / f"data/derived/subjects/{r}.json") for r in rounds]
    items_dir = root / (items_dir or Path("data/derived/items"))
    s6 = [read(items_dir / f"{r}.json") for r in rounds]
    ai_enabled = any("ai_relations" in report for report in s6)
    mapper = SourceMap(root, s4) if gold_dir is None else SourceMap(root, s4, gold_dir)
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
            if ai_item(row):
                ai_enabled = True
                row["owned_occurrences"] = [
                    loc for pos in row.get("owned_ranges", [])
                    for loc in mapper.locate(row["converted_path"], pos)
                ]
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
                    for locator in field_locators(pipeline_field(row, n))
                    for loc in mapper.locate(row["converted_path"], locator)
                ]
                for n in names
            }
            pipeline.append(row)
    combined = combined_items(pipeline, s6) if ai_enabled else []
    ai_pipeline = pipeline
    pipeline = [p for p in pipeline if not ai_item(p)]
    # Explicit non-performance roles remain in the diagnostic inventory only.
    raw_independent = [p for p in pipeline if independent(p)]
    candidates = [p for p in raw_independent if p.get("candidate_role") == "performance"]
    nonperformance = [p for p in raw_independent if p.get("candidate_role") != "performance"]
    stages = {}
    cases = []
    stage_inputs = [
        ("confirmed", [p for p in candidates if confirmed(p)]),
        ("all_candidates", candidates),
    ]
    if ai_enabled:
        stage_inputs.append(("rule_ai", combined))
    for stage, selected in stage_inputs:
        pairing = pair_combined_items if stage == "rule_ai" else pair_items
        pairs, missing, extra = pairing(gold, selected, use_task_no=use_task_no)
        counters = {n: Counter({o: 0 for o in OUTCOMES}) for n in names}
        conflict_counts = {n: Counter() for n in names}
        relations = Counter()
        attributed = []
        for pair in pairs:
            g, p = gold[pair["gold_index"]], selected[pair["pipeline_index"]]
            results = {n: field_result(n, g, p) for n in names}
            pair["fields"] = results
            pair["pipeline_locations"] = (
                p.get("owned_occurrences", []) if pair["basis"].get("owned_ranges_used")
                else p["occurrences"]
            )
            pair["pipeline_title"] = pipeline_field(p, "title").get("value")
            if stage == "rule_ai":
                pair["contributions"] = p["contributions"]
                pair["ai_support"] = p["ai_support"]
            for n, result in results.items():
                counters[n][result["result"]] += 1
                if result["gold_conflict"]:
                    conflict_counts[n][result["result"]] += 1
                if n == "standards" and result["standards_relation"]:
                    relations[result["standards_relation"]] += 1
            attributed.extend(misattributions(g, p, gold, names))
        unmatched = [unmatched_record(selected[j], gold, pairs) for j in extra]
        if stage == "rule_ai":
            for row in unmatched:
                row["included_in_precision"] = True
        stages[stage] = {
            "recall": wilson(len(pairs), len(gold)),
            "precision": wilson(len(pairs), len(selected)),
            "role_counts": dict(Counter(p["candidate_role"] for p in selected)),
            "pairs": pairs,
            "missing_gold_keys": [gold[j]["item_key"] for j in missing],
            "unmatched_gold": [
                pairing_failure(
                    gold[j], ai_pipeline if stage == "rule_ai" else pipeline, pairs, gold, selected,
                ) for j in missing
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
    report = {
        "version": "gold-v1.4",
        "gold_sha256": meta["sha256"],
        "rounds": rounds,
        "scored_fields": names,
        "field_map": FIELD_MAP,
        "field_rules": FIELD_RULES,
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
        "seal": seal_check(root) if gold_dir is None else seal_check(root, gold_dir),
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
    if ai_enabled:
        add_ai_report(report, gold, combined, s6, mapper, root, rounds)
    return report


def unmatched_ai_record(item: dict, gold: list[dict], pairs: list[dict]) -> dict:
    row = unmatched_record(item, gold, pairs)
    title = norm(row["title"] or "")
    same_school = [g for g in gold if g["school_id"] == item["school_id"]]
    identity_matches = [
        g for g in same_school
        if title in gold_titles(g) or overlap(item["occurrences"], g["occurrences"])
    ]
    peers = [
        g for g in identity_matches
        if all(g[k] == item[k] for k in ("grade", "semester"))
    ]
    # Diagnostic only. Method values never participate in pair_items or pair_combined_items.
    method_peers = [
        g for g in same_school
        if all(g[k] == item[k] for k in ("grade", "semester"))
        and any(title in method_tokens(v) for v in alternatives(g["fields"].get("method", {})))
        and overlap(item["occurrences"], locations(g["fields"].get("method", {})))
    ]
    matched = {p["gold_key"] for p in pairs}
    if item.get("grade") not in {1, 2} or item.get("semester") not in {1, 2} or (
        identity_matches and not peers
    ):
        reason = "학년·학기 오류"
        detail = "대상 학년·학기가 없거나 제목·위치가 대응하는 정답의 학년·학기와 다름"
    elif method_peers and not any(title in gold_titles(g) for g in peers):
        reason = "수행평가 아님"
        detail = "같은 위치의 평가방법과 제목이 일치. 평가방법을 독립 과제로 읽은 것으로 추정"
    elif any(g["item_key"] in matched for g in peers):
        reason = "중복(같은 과제의 다른 위치)"
        detail = "같은 학교·학년·학기의 이미 연결된 정답과 제목 또는 위치가 대응함"
    elif row["classification"] in {"다른 교과", "지필평가", "운영표·규정"}:
        reason = "수행평가 아님"
        detail = row["classification"]
    else:
        reason = "정답 누락 가능성"
        detail = (
            "같은 집단 정답과 대응하지만 1대1 짝을 확정하지 못함"
            if peers else "같은 집단에서 제목·위치가 대응하는 정답을 찾지 못함"
        )
    evidence = item.get("boundary_evidence", {}).get("ai_evidence", [])
    if not evidence:
        evidence = pipeline_field(item, "title").get("evidence", [])
    return {
        **row, "estimated_reason": reason, "reason_detail": detail,
        "included_in_precision": True,
        "evidence_quotes": [e.get("raw", e.get("text", "")) for e in evidence],
        "owned_ranges": item.get("owned_ranges", []),
        "owned_locations": item.get("owned_occurrences", []),
        "method_diagnostic_gold_keys": [g["item_key"] for g in method_peers],
    }


def ai_window_coverage(gold: dict, windows: list[dict]) -> dict:
    """Compare sealed pack coordinates, without filtering a window by inferred grade."""
    hits = [w for w in windows if overlap(gold["occurrences"], w["locations"])]
    return {
        "ai_window_status": "창 안" if hits else "창 밖",
        "ai_window_ids": [w["target_id"] for w in hits],
        "ai_window_basis": "정답 occurrence와 AI 대상 창의 pack 줄 겹침",
    }


def ai_field_diagnosis(row: dict, gold: dict) -> tuple[str, str]:
    """Conservative review hints from values and source positions, never new labels."""
    if row["other_gold_keys"]:
        return "다른 과제 값(오귀속)", "같은 학교·학년·학기의 다른 정답과 일치. " + ", ".join(
            row["other_gold_keys"]
        )
    name = row["field"]
    expected = gold["fields"].get(name, {"status": "source_absent"})
    actual_strings = [norm(s) for s in raw_values(row["ai_value"]) if norm(s)]
    quoted = any(s in norm(q) for s in actual_strings for q in row["evidence_quotes"])
    own_source = bool(overlap(gold["occurrences"], row["field_locations"]))
    if expected.get("status") == "source_absent" and quoted and own_source:
        return "정답 쪽 표기 차이", (
            "정답은 source_absent이나 AI 값이 인용에 있고 과제 위치가 겹침. 정답 근거 재검토 추정"
        )
    expected_strings = [norm(s) for v in alternatives(expected) for s in raw_values(v) if norm(s)]
    if own_source and any(
        left in right or right in left for left in actual_strings for right in expected_strings
    ):
        return "같은 과제 다른 표기", "과제 위치가 겹치고 값의 정규화 문자열이 부분 포함됨"
    return "값 오류", (
        "허용 정답과 불일치하며 다른 과제 일치·표기 차이를 뒷받침할 근거가 부족함. "
        f"필드 상태 {row['pipeline_status']}"
    )


def add_ai_field_report(report: dict, gold: list[dict], selected: list[dict]) -> None:
    """Partition matched fields, with misattribution as an overlapping error count."""
    stage = report["stages"]["rule_ai"]
    names = report["scored_fields"]
    by_id = {p["score_id"]: p for p in selected}
    gold_by_key = {g["item_key"]: g for g in gold}

    def empty_fields():
        return {n: Counter({o: 0 for o in FIELD_COLUMNS}) for n in names}

    groups = {key: empty_fields() for key in ("a", "b", "c")}
    methods = {key: empty_fields() for key in ("rule_reuse", "ai_read", "미기록")}
    alignments = {key: empty_fields() for key in (
        "same_column", "same_row", "own_table", "shared_span", "prose", "미기록",
    )}
    missing = {key: {} for key in ("대조 실패", "absent", "답 없음", "1단계 미추출", "기타")}
    records = []
    errors = []
    attributed = {
        (e["pipeline_key"], e["field"]): e["other_gold_keys"] for e in stage["misattributions"]
    }
    group_by_id = {
        p["score_id"]: "b" if "b" in p["contributions"] else "a" if "a" in p["contributions"]
        else "c" for p in selected
    }
    stage["field_group_counts"] = {
        key: {
            "input": sum(group == key for group in group_by_id.values()),
            "matched": sum(group_by_id[p["pipeline_key"]] == key for p in stage["pairs"]),
        }
        for key in groups
    }
    for pair in stage["pairs"]:
        item = by_id[pair["pipeline_key"]]
        g = gold_by_key[pair["gold_key"]]
        group = group_by_id[pair["pipeline_key"]]
        for name, result in pair["fields"].items():
            outcome = result["result"]
            other_keys = attributed.get((pair["pipeline_key"], name), [])
            groups[group][name][outcome] += 1
            groups[group][name]["오귀속"] += bool(other_keys)
            if group != "b":
                continue
            field = pipeline_field(item, name)
            evidence = [o for o in field_observations(field) if any(
                k in o for k in ("locator", "raw", "text", "ai_alignment")
            )]
            method = field.get("fill_method") or "미기록"
            # Multiple evidence alignments form one bucket so partitions sum to b.
            alignment = "/".join(sorted({
                e["ai_alignment"] for e in evidence if e.get("ai_alignment")
            })) or "미기록"
            for buckets, key in ((methods, method), (alignments, alignment)):
                if key not in buckets:
                    buckets[key] = empty_fields()
                buckets[key][name][outcome] += 1
                buckets[key][name]["오귀속"] += bool(other_keys)
            reason = field.get("reason", "")
            if outcome in {"누락", "미추출"}:
                category = (
                    "1단계 미추출" if outcome == "미추출" else
                    "absent" if reason == "AI: 원문에 없다고 답함(미검증)" else
                    "답 없음" if reason == "AI 항목 읽기: 답 없음" else
                    "대조 실패" if reason.startswith("AI 항목 읽기:") else "기타"
                )
                counts = missing[category].setdefault(reason, Counter({"누락": 0, "미추출": 0}))
                counts[outcome] += 1
            row = {
                "gold_key": g["item_key"], "pipeline_key": item["score_id"],
                "school": item["school"], "grade": item["grade"], "semester": item["semester"],
                "title": g.get("representative_title", {}).get("raw", ""),
                "pipeline_title": pipeline_field(item, "title").get("value"),
                "field": name, "result": outcome,
                "gold_status": g["fields"].get(name, {}).get("status", "source_absent"),
                "gold_accepted": alternatives(g["fields"].get(name, {})),
                "ai_value": field.get("value"), "pipeline_status": field.get("status"),
                "fill_method": method, "ai_alignment": alignment, "reason": reason,
                "evidence": evidence,
                "evidence_quotes": list(dict.fromkeys(
                    e.get("raw") or e.get("text") for e in evidence if e.get("raw") or e.get("text")
                )),
                "field_locations": item.get("field_locations", {}).get(name, []),
                "other_gold_keys": other_keys, "misattributed": bool(other_keys),
            }
            if outcome in {"오값", "허위값"} or other_keys:
                row["estimated_reason"], row["reason_detail"] = ai_field_diagnosis(row, g)
                errors.append(row)
            records.append(row)
    stage.update(
        fields_by_group=groups, ai_fields_by_fill_method=methods,
        ai_fields_by_alignment=alignments, ai_field_errors=errors, ai_missing_reasons=missing,
    )
    report["cases"].extend({"type": "ai_field", "key": r["pipeline_key"] + "/" + r["field"], **r}
                           for r in records)


def add_ai_report(
    report: dict, gold: list[dict], selected: list[dict], sources: list[dict],
    mapper: SourceMap, root: Path, rounds: list[str],
) -> None:
    stage = report["stages"]["rule_ai"]
    confirmed_keys = {p["gold_key"] for p in report["stages"]["confirmed"]["pairs"]}
    paired_keys = {p["gold_key"] for p in stage["pairs"]}
    by_id = {p["score_id"]: p for p in selected}
    case_by_key = {c["key"]: c for c in report["cases"] if c["type"] == "gold"}
    verified = {}
    windows = []
    for round_key in rounds:
        directory = root / "data/derived/ai_read" / round_key
        verified_path = directory / "verified.json"
        if verified_path.exists():
            verified.update({
                round_key + "/" + task["ai_task_id"]: task
                for task in read(verified_path)["kept"]
            })
        target_path = directory / "targets.jsonl"
        for line in target_path.read_text(encoding="utf-8").splitlines():
            window = json.loads(line)
            windows.append({
                "target_id": window["target_id"], "round": round_key,
                "converted_path": window["converted_path"],
                "start": window["start"], "end": window["end"],
                "locations": mapper.locate(window["converted_path"], window),
            })
    newly_matched = []
    for pair in stage["pairs"]:
        item = by_id[pair["pipeline_key"]]
        round_key = pair["pipeline_key"].split("/", 1)[0]
        pair["ai_titles"] = (
            [pair["pipeline_title"]] if ai_item(item) else [
                verified.get(round_key + "/" + s["ai_task_id"], {}).get("title")
                for s in pair["ai_support"]
            ]
        )
        if pair["gold_key"] not in confirmed_keys:
            case = case_by_key[pair["gold_key"]]
            newly_matched.append({
                "gold_key": pair["gold_key"],
                **{k: case[k] for k in ("school", "grade", "semester", "title")},
                "pipeline_key": pair["pipeline_key"], "pipeline_title": pair["pipeline_title"],
                "contributions": pair["contributions"], "ai_titles": pair["ai_titles"],
                "basis": pair["basis"], "locations": pair["pipeline_locations"],
            })
    contribution_counts = {}
    paired_ids = {p["pipeline_key"] for p in stage["pairs"]}
    for source in ("a", "b", "c_location", "c_title"):
        members = [p for p in selected if source in p["contributions"]]
        contribution_counts[source] = {
            "input": len(members),
            "matched": sum(p["score_id"] in paired_ids for p in members),
            "unmatched": sum(p["score_id"] not in paired_ids for p in members),
            "new_gold": sum(source in p["contributions"] for p in newly_matched),
        }
    stage["contribution_counts"] = contribution_counts
    stage["input_count"] = len(selected)
    stage["owned_ranges_pair_count"] = sum(p["basis"]["owned_ranges_used"] for p in stage["pairs"])
    stage["retained_confirmed_gold_count"] = len(paired_keys & confirmed_keys)
    stage["lost_confirmed_gold_keys"] = sorted(confirmed_keys - paired_keys)
    stage["title_accuracy"] = (
        wilson(stage["fields"]["title"]["정답"], len(stage["pairs"]))
        if "title" in stage["fields"] else wilson(0, 0)
    )
    stage["ai_unextracted_fields"] = {
        n: {
            "input": sum(ai_unextracted(p, n) for p in selected),
            "matched": stage["fields"][n].get("미추출", 0),
        }
        for n in report["scored_fields"] if n != "title"
    }
    add_ai_field_report(report, gold, selected)
    unmatched_ai = [
        unmatched_ai_record(p, gold, stage["pairs"])
        for p in selected if ai_item(p) and p["score_id"] not in paired_ids
    ]
    remaining = []
    for failure in stage["unmatched_gold"]:
        case = case_by_key[failure["gold_key"]]
        g = next(g for g in gold if g["item_key"] == failure["gold_key"])
        coverage = ai_window_coverage(g, windows)
        findings = []
        for task_key, task in verified.items():
            if any(task.get(k) != case[k] for k in ("school", "grade", "semester")):
                continue
            primary = mapper.locate(task["converted_path"], task["locator"])
            owned = [
                loc for pos in task.get("locators", [])
                for loc in mapper.locate(task["converted_path"], pos)
            ]
            title_match = norm(task["title"]) in gold_titles(g)
            primary_overlap = overlap(g["occurrences"], primary)
            owned_overlap = overlap(g["occurrences"], owned)
            if not (title_match or primary_overlap or owned_overlap):
                continue
            task_round, task_id = task_key.split("/", 1)
            relation_types = [
                name for source in sources if source["round"] == task_round
                for name, rows in source.get("ai_relations", {}).items()
                if any(
                    row.get("ai_task_id") == task_id or task_id in row.get("ai_task_ids", [])
                    for row in rows
                )
            ]
            findings.append({
                "ai_task_key": task_key, "title": task["title"],
                "title_match": title_match, "locator_overlap_pack_lines": primary_overlap,
                "owned_overlap_pack_lines": owned_overlap, "relations": relation_types,
            })
        ai_reason = (
            "AI 검증 과제 후보 " + ", ".join(
                f"{f['title']} ({'/'.join(f['relations']) or '관계 없음'}, "
                f"{'제목 일치' if f['title_match'] else '위치 근거만 겹침'})"
                for f in findings
            ) + ". " if findings else "대응하는 AI 검증 보존 과제 없음. "
        )
        row = {
            **failure, "school": case["school"], **coverage,
            "rule_cause": case["cause"],
            "ai_findings": findings,
            "cause": (
                "AI 창 안에서 미회복. " if coverage["ai_window_status"] == "창 안"
                else "AI 창 밖. "
            ) + ai_reason + failure["reason"].replace("; ", ". "),
        }
        remaining.append(row)
    recovered = paired_keys | {
        p["gold_key"] for p in report["stages"]["all_candidates"]["pairs"]
    }
    ai_loss = Counter({k: 0 for k in report["loss_map"]})
    ai_loss["gold"] = len(gold)
    for g in gold:
        case = case_by_key[g["item_key"]]
        paired = g["item_key"] in recovered
        generated = case["candidate_generated"] or any(
            all(p[k] == g[k] for k in ("school_id", "grade"))
            and overlap(g["occurrences"], p["occurrences"] + p.get("owned_occurrences", []))
            for p in selected
        )
        ai_loss["document"] += case["document_found"] or paired
        ai_loss["section"] += case["section_found"] or paired
        ai_loss["candidate"] += paired or (case["section_found"] and generated)
        ai_loss["matched"] += paired
        ai_loss["confirmed"] += g["item_key"] in paired_keys
    report.update(
        newly_matched_gold=newly_matched,
        unmatched_ai_pipeline=unmatched_ai,
        remaining_rule_ai_misses=remaining,
        ai_windows=windows,
        ai_window_counts={
            status: sum(r["ai_window_status"] == status for r in remaining)
            for status in ("창 안", "창 밖")
        },
        loss_maps={"rule_only": report["loss_map"], "rule_ai": ai_loss},
        ai_relation_counts={
            relation: sum(len(s.get("ai_relations", {}).get(relation, [])) for s in sources)
            for relation in ("agrees", "agrees_by_title", "agrees_by_evidence",
                             "ai_split_suggested", "conflict", "new")
        },
    )
    for case in case_by_key.values():
        pair = next((p for p in stage["pairs"] if p["gold_key"] == case["key"]), None)
        case.update(
            rule_ai_found=pair is not None,
            rule_ai_pipeline_key=pair["pipeline_key"] if pair else "",
            rule_ai_pipeline_title=pair["pipeline_title"] if pair else "",
            rule_ai_ai_titles=pair["ai_titles"] if pair else [],
            rule_ai_newly_matched=bool(pair) and case["key"] not in confirmed_keys,
            rule_ai_pair_basis=pair["basis"] if pair else {},
            rule_ai_contributions=pair["contributions"] if pair else [],
            rule_ai_field_results=(
                {n: r["result"] for n, r in pair["fields"].items()} if pair else {}
            ),
        )
        if not pair:
            failure = next(r for r in remaining if r["gold_key"] == case["key"])
            case.update({k: failure[k] for k in ("ai_window_status", "ai_window_ids")})
            case["rule_ai_cause"] = failure["cause"]
            case["rule_ai_ai_findings"] = failure["ai_findings"]
    report["cases"].extend({"type": "ai_unmatched", "key": r["pipeline_key"], **r}
                           for r in unmatched_ai)


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


def compare_item_metrics(before: dict, after: dict) -> dict:
    """Compare item metrics and pairing evidence independently of field scoring."""
    differences = []
    for stage, previous in before["stages"].items():
        result = after["stages"][stage]
        for key in ("recall", "precision", "role_counts", "missing_gold_keys"):
            if previous[key] != result[key]:
                differences.append(f"stages.{stage}.{key}")
        old_pairs, new_pairs = (
            [(p["gold_key"], p["pipeline_key"], p["basis"]) for p in source["pairs"]]
            for source in (previous, result)
        )
        if old_pairs != new_pairs:
            differences.append(f"stages.{stage}.pairs")
    for key in ("loss_map", "raw_independent_diagnostic", "excluded_summary_aliases"):
        if before[key] != after[key]:
            differences.append(key)
    return {"equal": not differences, "differences": differences}


def compare_score_metrics(before: dict, after: dict) -> dict:
    """Compare preserved item and field metrics over stages available in both runs."""
    common = [key for key in before["stages"] if key in after["stages"]]
    comparison = compare_item_metrics(
        {**before, "stages": {key: before["stages"][key] for key in common}}, after,
    )
    differences = comparison["differences"]
    for key in common:
        left, right = before["stages"][key], after["stages"][key]
        for name in (
            "fields", "conflict_fields", "standards_relations", "misattributions",
            "misattributions_by_field", "public_misattributions", "ai_unextracted_fields",
            "title_accuracy", "contribution_counts", "input_count",
        ):
            if left.get(name) != right.get(name):
                differences.append(f"stages.{key}.{name}")
        if [p["fields"] for p in left["pairs"]] != [p["fields"] for p in right["pairs"]]:
            differences.append(f"stages.{key}.pairs.fields")
    return {"equal": not differences, "differences": differences, "compared_stages": common}


def pair_basis_text(basis: dict) -> str:
    if basis.get("owned_ranges_used"):
        return f"owned_ranges 보조 겹침 {basis['overlap_pack_lines']}줄"
    if basis.get("task_no_used"):
        return f"연결용 task_no {basis['normalized_task_no']}"
    if basis.get("overlap_pack_lines"):
        return f"locator 겹침 {basis['overlap_pack_lines']}줄"
    return "제목 일치 " + ", ".join(basis.get("normalized_title_matches", []))


def rule_markdown(report: dict) -> str:
    stages = report["stages"]
    rounds = "두" if len(report["rounds"]) == 2 else str(len(report["rounds"]))
    schools = len({document["school_id"] for document in report["documents"]})
    lines = [
        "# S9 ⑧ 채점기 v1.4 · 정답 v1",
        "",
        f"{rounds} 공시 회차·{schools}개교·정답 {report['loss_map']['gold']}항목. "
        "추출 규칙·패턴·임계값 변경 0. 오프라인 실행.",
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
        "기존 규칙대로 위치·제목 짝을 먼저 보존한 뒤 미짝 항목만 task_no로 보완한다. "
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
        "conflict는 원문 보존 값 하나 이상 또는 파이프라인 conflict 표시를 인정하고 "
        "별도 집계한다. 파이프라인 unconfirmed는 정답의 상태와 무관하게 누락이다. "
        "정답과 파이프라인이 모두 source_absent이면 둘다없음이며, source_absent 정답에 "
        "확정 값을 내면 허위값으로 센다. task_no는 채점에서 제외한다. "
        "부분은 정답 수에 합산하지 않는다.",
        "",
        "## 필드별 비교 규칙",
        "",
        "| 정답 필드 | S6 필드 | 비교 규칙 |",
        "|---|---|---|",
        *[f"| {n} | {FIELD_MAP[n]} | {cell(rule)} |" for n, rule in FIELD_RULES.items()],
        "",
        "## v1.2와 v1.4 성적 비교",
        "",
        "수치 괄호는 Wilson 95% 구간이다. v1.2은 보존된 JSON의 실제 측정값이다. "
        "재현율 기준 ≥95%, 정밀도 기준 ≥99%.",
        "",
        f"기준 파일 `{report['baseline']['path']}` · SHA-256 `{report['baseline']['sha256']}`.",
        "",
        "항목 지표·짝·짝짓기 근거·손실 지도 대조 결과 "
        + ("동일." if report["item_metric_comparison"]["equal"] else
           "차이 있음. " + cell(report["item_metric_comparison"]["differences"])),
        "",
        "| 단계 | v1.2 재현율 | v1.4 재현율 | v1.2 정밀도 | v1.4 정밀도 | 번호 직접 사용 |",
        "|---|---|---|---|---|---:|",
    ]
    for key, label in (("confirmed", "확정"), ("all_candidates", "전체 후보")):
        s = stages[key]
        before = report["comparison"]["v1.2"]["stages"][key]
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
        "## 짝 없는 확정 파이프라인 항목 전부 · v1.4",
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
        "## 남은 짝짓기 실패 정답 전부 · v1.4 전체 후보 기준",
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
            "| 필드 | 정답 | 부분 | 누락 | 오값 | 허위값 | 둘다없음 | "
            "conflict 정답/대상 | 오귀속 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
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
            f"### {label} 필드 전후 비교",
            "",
            "각 칸은 v1.2 → v1.4 건수다. v1.2에 없던 부분은 0으로 표시한다.",
            "",
            "| 필드 | 정답 | 부분 | 누락 | 오값 | 허위값 | 둘다없음 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
        for n, counts in s["fields"].items():
            before = report["comparison"]["v1.2"]["stages"][key]["fields"][n]
            lines.append(
                f"| {n} | "
                + " | ".join(f"{before.get(o, 0)} → {counts[o]}" for o in OUTCOMES)
                + " |"
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


def ai_field_markdown(stage: dict) -> list[str]:
    lines = [
        "", "## 규칙+AI 단계 필드 표", "",
        "정답과 짝지어진 항목의 필드만 집계한다. 집단은 b → a → c 순서로 한 곳에 배정한다. "
        "a와 c의 지원이 겹치면 a에 포함한다. 오귀속은 오값·허위값 중 다른 과제 정답과 일치한 "
        "필드의 중복 지표다.",
    ]

    def table(title, fields):
        lines.extend(["", f"### {title}", "", "| 필드 | " + " | ".join(FIELD_COLUMNS) + " |",
                      "|---|" + "---:|" * len(FIELD_COLUMNS)])
        for name, counts in fields.items():
            lines.append("| " + " | ".join(cell(v) for v in (
                name, *(counts.get(o, 0) for o in FIELD_COLUMNS),
            )) + " |")

    for key, label in (("a", "(a) 확정 규칙 항목"), ("b", "(b) AI 새 항목"),
                       ("c", "(c) AI 확인 후보")):
        counts = stage["field_group_counts"][key]
        table(f"{label} · 입력 {counts['input']}개 · 짝 {counts['matched']}개",
              stage["fields_by_group"][key])
    lines += ["", "## AI 새 항목의 필드 결과 분할", "",
              "fill_method는 필드의 기록을 사용한다. ai_alignment는 필드 소유 evidence의 "
              "서로 다른 정렬을 정렬해 /로 묶는다. 복수 정렬도 한 칸으로 집계하여 b와 합계가 같다. "
              "미기록은 메타데이터가 없는 필드다."]
    for dimension, key in (("fill_method", "ai_fields_by_fill_method"),
                           ("ai_alignment", "ai_fields_by_alignment")):
        for value, fields in stage[key].items():
            table(f"{dimension} = {value}", fields)
    lines += ["", "## AI 새 항목 필드의 오값·허위값·오귀속 전부", "",
              "원인 추정은 값·인용·위치 대조에 따른 검토용 분류다. "
              "교육 판단 확정은 별도 검토가 필요하다.",
              "",
              "| 학교 | 학년·학기 | 과제 제목 | 필드 | 결과 | 정답 값 | AI 값 | 인용 | 정렬 | "
              "fill_method | 원인 추정 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in stage["ai_field_errors"]:
        values = (
            row["school"], f"중{row['grade']} {row['semester']}학기", row["title"], row["field"],
            row["result"] + (" · 오귀속" if row["misattributed"] else ""),
            row["gold_accepted"], row["ai_value"], " / ".join(row["evidence_quotes"]),
            row["ai_alignment"], row["fill_method"],
            row["estimated_reason"] + " · " + row["reason_detail"],
        )
        lines.append("| " + " | ".join(cell(html.escape(str(v))) for v in values) + " |")
    if not stage["ai_field_errors"]:
        lines.append("| - | - | 없음 | - | - | - | - | - | - | - | - |")
    lines += ["", "## AI 새 항목의 누락 사유 분포", "",
              "짝지어진 b 항목의 누락과 1단계 미추출을 구분한다. 1단계 미추출은 누락 합계에 "
              "더하지 않는다. absent는 미검증 부재 응답이다.", "",
              "| 분류 | 사유 | 누락 | 미추출 |", "|---|---|---:|---:|"]
    for category, reasons in stage["ai_missing_reasons"].items():
        if not reasons:
            lines.append(f"| {category} | - | 0 | 0 |")
        for reason, counts in reasons.items():
            lines.append(f"| {category} | {cell(reason)} | {counts['누락']} | {counts['미추출']} |")
    return lines


def ai_markdown(report: dict) -> str:
    stages = report["stages"]
    lines = [
        "# 채점기 v1.4 · 규칙+AI",
        "",
        "오프라인 측정. a는 기존 확정 단계의 독립 수행 항목(bounded 또는 public_eligible), "
        "b는 ai_verified 새 항목, c는 bounded=false인 agrees·agrees_by_title의 규칙 항목이다. "
        "agrees는 위치 확인, agrees_by_title은 제목 확인으로 구분한다. "
        "합집합은 회차·항목 ID로 중복 제거한다. c의 위치·제목 지원이 겹치면 "
        "각각의 지원 건수에 포함되므로 기여 행의 합은 합집합과 다를 수 있다.",
        "",
        "학교·학년·학기가 같은 항목을 기존 위치 겹침 → 제목 → 연결용 task_no로 짝짓는다. "
        "채점할 필드 값은 짝짓기에 사용하지 않는다. AI locator의 기본 짝을 보존한 뒤 "
        "남은 AI 항목에 owned_ranges 위치 보조 짝짓기를 적용한다. 모든 짝은 1대1이다.",
        "",
        f"기준 파일 `{report['baseline']['path']}`. 항목 지표·짝·짝 근거·손실 지도 "
        + ("일치." if report["item_metric_comparison"]["equal"] else
           "차이 있음. " + cell(report["item_metric_comparison"]["differences"])),
        "",
        "## 확정 대 규칙+AI",
        "",
        "재현율·정밀도 괄호는 Wilson 95% 구간이다. 필드 오귀속은 짝지어진 항목에서 집계한다.",
        "",
        "| 단계 | 재현율 | 정밀도 | 필드 오귀속 | 공개 필드 오귀속 |",
        "|---|---|---|---:|---:|",
    ]
    for key, label in (("confirmed", "확정(규칙만)"), ("rule_ai", "규칙+AI"),
                       ("all_candidates", "전체 후보(규칙만)")):
        if key in stages:
            stage = stages[key]
            lines.append(f"| {label} | {metric(stage['recall'])} | {metric(stage['precision'])} | "
                         f"{len(stage['misattributions'])} | {stage['public_misattributions']} |")
    if "rule_ai" in stages:
        stage = stages["rule_ai"]
        lines += ["", "| 기여 | 입력 | 맞힘 | 미짝 | 확정 대비 새 정답 |",
                  "|---|---:|---:|---:|---:|"]
        labels = {"a": "a 확정 규칙", "b": "b AI 새 항목",
                  "c_location": "c 위치 확인", "c_title": "c 제목 확인"}
        for key, label in labels.items():
            counts = stage["contribution_counts"][key]
            lines.append(f"| {label} | {counts['input']} | {counts['matched']} | "
                         f"{counts['unmatched']} | {counts['new_gold']} |")
        lines += ["", f"합집합 입력 {stage['input_count']}개. 기존 확정 정답 유지 "
                  f"{stage['retained_confirmed_gold_count']}개. 잃은 확정 정답 "
                  f"{cell(stage['lost_confirmed_gold_keys'])}. "
                  f"owned_ranges 보조 짝 {stage['owned_ranges_pair_count']}개.", "",
                  "## 새로 맞힌 정답 전부", "",
                  "| 정답 키 | 학교 | 학년 | 학기 | 정답 제목 | 기여 | "
                  "항목 키 · 규칙/AI 제목 | AI 제목 | 짝 근거 |",
                  "|---|---|---:|---:|---|---|---|---|---|"]
        for row in report["newly_matched_gold"]:
            values = (row["gold_key"], row["school"], row["grade"], row["semester"], row["title"],
                      ", ".join(row["contributions"]),
                      f"{row['pipeline_key']} · {row['pipeline_title'] or '(제목 미추출)'}",
                      row["ai_titles"], pair_basis_text(row["basis"]))
            lines.append("| " + " | ".join(cell(v) for v in values) + " |")
        lines += ["", "## 짝 없는 AI 항목 전부", "",
                  "추정 이유는 검토용 분류다. 위치의 문자 끝은 제외한다. 근거는 원문 인용이다.", "",
                  "| 학교 | 학년 | 학기 | AI 제목 | 항목 키 | 위치 | 근거 인용 | "
                  "추정 이유 · 설명 |",
                  "|---|---:|---:|---|---|---|---|---|"]
        for row in report["unmatched_ai_pipeline"]:
            values = (row["school"], row["grade"], row["semester"], row["title"],
                      row["pipeline_key"], location_text(row),
                      " / ".join(row["evidence_quotes"]),
                      f"{row['estimated_reason']} · {row['reason_detail']}")
            lines.append("| " + " | ".join(cell(html.escape(str(v))) for v in values) + " |")
        if not report["unmatched_ai_pipeline"]:
            lines.append("| - | - | - | 없음 | - | - | - | - |")
        lines += ["", "## 손실 지도", "",
                  "문서·구간은 규칙 검출 범위에 위치·제목·번호 복구를 포함한다. 후보·1대1 짝은 "
                  "전체 규칙 후보와 AI 보완의 포괄 범위다. 마지막 행은 단계별 채점 대상이다.", "",
                  "| 지점 | 규칙만 | 규칙+AI |", "|---|---:|---:|"]
        for key, label in (("gold", "정답"), ("document", "문서"), ("section", "구간"),
                           ("candidate", "후보"), ("matched", "1대1 짝"),
                           ("confirmed", "확정 / 규칙+AI")):
            lines.append(f"| {label} | {report['loss_maps']['rule_only'][key]} | "
                         f"{report['loss_maps']['rule_ai'][key]} |")
        lines += ["", "## 규칙+AI의 남은 놓침 전부", "",
                  "창 안·밖은 targets.jsonl의 문자 범위를 pack 줄로 변환해 "
                  "정답 occurrence와 대조한다. "
                  "창 안의 미회복은 AI 미검출·병합 보류·짝짓기 실패를 포함한다. "
                  "창 밖은 이 좌표 대조에서 정답 근거와 겹치는 대상 창이 없음을 뜻한다.", "",
                  "| 정답 키 | 학교 | 학년 | 학기 | 정답 제목 | AI 창 | 대상 창 ID | 원인 |",
                  "|---|---|---:|---:|---|---|---|---|"]
        for row in report["remaining_rule_ai_misses"]:
            values = (row["gold_key"], row["school"], row["grade"], row["semester"], row["title"],
                      row["ai_window_status"], row["ai_window_ids"], row["cause"])
            lines.append("| " + " | ".join(cell(v) for v in values) + " |")
        if not report["remaining_rule_ai_misses"]:
            lines.append("| - | - | - | - | 없음 | - | - | - |")
        lines += ["", "## 규칙+AI 제목과 미추출 필드", "",
                  f"짝지어진 항목의 제목 정확도 {metric(stage['title_accuracy'])}.", "",
                  "AI 새 항목은 규칙 항목과 같은 field_result로 채점한다. "
                  "unconfirmed이며 사유가 'AI 읽기 1단계: 필드 미추출'인 필드만 미추출로 분리한다. "
                  "c 항목의 필드는 보존된 규칙 값을 채점한다.", "",
                  "| AI 새 항목의 미추출 필드 | 입력 전체 | 짝지어진 항목 |",
                  "|---|---:|---:|"]
        for name, counts in stage["ai_unextracted_fields"].items():
            lines.append(f"| {name} | {counts['input']} | {counts['matched']} |")
        lines += ai_field_markdown(stage)
    for key, stage in stages.items():
        lines += ["", f"## {key} 필드 채점", "",
                  "| 필드 | 정답 | 부분 | 누락 | 오값 | 허위값 | 둘다없음 | 미추출 | 오귀속 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for name, counts in stage["fields"].items():
            values = [name, *(counts.get(o, 0) for o in (*OUTCOMES, "미추출")),
                      stage["misattributions_by_field"].get(name, 0)]
            lines.append("| " + " | ".join(map(cell, values)) + " |")
        if stage["misattributions"]:
            lines.append("")
        for error in stage["misattributions"]:
            lines.append(f"- `{error['gold_key']}` · {error['field']} · "
                         f"{cell(error['value'])} · 다른 정답 {cell(error['other_gold_keys'])}")
    lines += ["", "## 봉인 검증", "",
              f"{report['seal']['checked']}개 해시 대조. "
              f"불일치 {report['seal']['mismatches']}.", ""]
    return "\n".join(lines)


def markdown(report: dict) -> str:
    rules = rule_markdown(report)
    if "metric_comparisons" in report:
        lines = ["## 보존 성적과 항목·필드 불변 대조", ""]
        for version, comparison in report["metric_comparisons"].items():
            status = "일치" if comparison["equal"] else cell(comparison["differences"])
            lines.append(f"- {version} · {', '.join(comparison['compared_stages'])} · {status}")
        rules = "\n".join(lines) + "\n\n" + rules
    if "rule_ai" in report["stages"]:
        return ai_markdown(report) + "\n\n" + rules
    return rules


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=ROOT / "data/gold/gold_v1.jsonl")
    parser.add_argument("--meta", type=Path, default=ROOT / "data/gold/gold_v1.meta.json")
    parser.add_argument("--gold-dir", type=Path, default=ROOT / "data/gold")
    parser.add_argument("--round-keys", nargs="+", default=list(ROUNDS))
    parser.add_argument("--items-dir", type=Path, default=ROOT / "data/derived/items")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/derived/gold_score/v5")
    parser.add_argument(
        "--baseline", type=Path,
        default=ROOT / "data/derived/gold_score/v3/gold-v1.2.json",
        help="Preserved v1.2 JSON used for comparison",
    )
    parser.add_argument(
        "--v13-baseline", type=Path,
        default=ROOT / "data/derived/gold_score/v4/gold-v1.3.json",
        help="Preserved v1.3 JSON used for item and field comparison",
    )
    args = parser.parse_args()
    baseline_path = args.baseline.resolve()
    baseline_report = read(baseline_path)
    v13_path = args.v13_baseline.resolve()
    v13_report = read(v13_path)
    report = score(ROOT, args.gold, args.meta, args.round_keys,
                   items_dir=args.items_dir, gold_dir=args.gold_dir)
    report["items_dir"] = args.items_dir.as_posix()
    report["baseline"] = {
        "path": (
            baseline_path.relative_to(ROOT).as_posix()
            if baseline_path.is_relative_to(ROOT) else baseline_path.as_posix()
        ),
        "sha256": hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
    }
    report["item_metric_comparison"] = compare_item_metrics(baseline_report, report)
    report["metric_comparisons"] = {
        "v1.2": compare_score_metrics(baseline_report, report),
        "v1.3": compare_score_metrics(v13_report, report),
    }
    report["v13_baseline"] = {
        "path": v13_path.relative_to(ROOT).as_posix() if v13_path.is_relative_to(ROOT)
        else v13_path.as_posix(),
        "sha256": hashlib.sha256(v13_path.read_bytes()).hexdigest(),
    }
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
        for version, source in (
            ("v1.2", baseline_report), ("v1.3", v13_report), ("v1.4", report),
        )
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
    (args.output_dir / "gold-v1.4.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "gold-v1.4.md").write_text(markdown(report), encoding="utf-8")
    columns = list(dict.fromkeys(k for row in report["cases"] for k in row))
    csv_path = args.output_dir / "gold-v1.4.cases.csv"
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
