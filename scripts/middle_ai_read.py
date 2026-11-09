"""S6e-1 prompt-only AI reading, fail-closed audit and source-verified additions.

No existing extraction output is mutated. All offsets address the unmodified
S4 Unicode text and use an exclusive end. Importing this module never runs Codex.
"""

from __future__ import annotations

import argparse
import bisect
import copy
import hashlib
import html
import json
import re
import subprocess
import sys
import tomllib
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if __package__:
    from .middle_items import FIELDS
    from .middle_segments import SUBJECT_LABELS, digest_id, text_locator
    from .middle_subjects import subject_headers, table_spans
else:
    from middle_items import FIELDS
    from middle_segments import SUBJECT_LABELS, digest_id, text_locator
    from middle_subjects import subject_headers, table_spans

ROOT = Path(__file__).resolve().parents[1]
CODEX = "C:/Users/USER/AppData/Local/OpenAI/Codex/bin/14b838c1d074ff01/codex.exe"
VERSION = "middle-ai-read-v1"
MAX_CHARS = 60_000
OVERLAP = 3_000
TIMEOUT = 900
DEV_ROUNDS = ("2026-round-1-dev2", "2026-round-3-dev2")
# CLI event names are deliberately allowlisted. Unknown versions require review.
EVENT_TYPES = {
    "thread.started", "turn.started", "turn.completed", "turn.failed", "error",
    "item.started", "item.updated", "item.completed",
}
PASSIVE_ITEMS = {"agent_message", "reasoning", "todo_list"}
TOOL_ITEMS = {
    "command_execution", "file_change", "file_read", "file_search", "web_search",
    "mcp_tool_call", "tool_call", "function_call", "computer_call", "image_view",
    "shell_command", "exec_command", "read_file", "collab_tool_call",
}


def guard_path(path: Path) -> Path:
    path = path.resolve()
    parts = [p.lower() for p in path.parts]
    if ("gold" in parts or ".gold-before-acl-fix" in parts
            or any("-gold" in p for p in parts)):
        raise ValueError("맹검 경로 접근 금지")
    return path


def read_text(path: Path) -> str:
    with guard_path(path).open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def read_json(path: Path):
    return json.loads(read_text(path))


def write_text(path: Path, text: str):
    path = guard_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def save_json(path: Path, value):
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def round_dir(root: Path, round_key: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", round_key) or "gold" in round_key.lower():
        raise ValueError("안전한 비정답 회차 키 필요")
    return guard_path(root / "data/derived/ai_read" / round_key)


def conversion_for(root: Path, document: dict) -> dict:
    path = guard_path(root / document["converted_path"])
    if not path.is_relative_to(root.resolve()):
        raise ValueError("변환본 경로가 저장소 밖임")
    conversion = read_json(path)
    text = conversion["text"]
    if sha(text) != document["text_sha256"]:
        raise ValueError("S4 원문 해시 불일치")
    return conversion


def line_index(text: str) -> tuple[list[str], list[int]]:
    lines = text.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    return lines, starts


def line_span(starts: list[int], start: int, end: int) -> tuple[int, int]:
    return (bisect.bisect_right(starts, start),
            bisect.bisect_right(starts, max(start, end - 1)))


def union_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged = []
    for lo, hi in sorted(ranges):
        if merged and lo <= merged[-1][1] + 1:
            merged[-1] = merged[-1][0], max(hi, merged[-1][1])
        else:
            merged.append((lo, hi))
    return merged


def science_markers(text: str) -> list[int]:
    """Subject labels only, never an incidental science word inside prose."""
    hits = [h["start"] for h in subject_headers(text) if h["key"] == "과학"]
    for match in re.finditer(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)\s*>", text, re.I | re.S):
        cell = normalize(match[1])
        if re.match(r"^과학(?:$|\s|[ⅠⅡⅢIV123(（:：·ㆍ])", cell):
            hits.append(match.start())
    offset = 0
    names = "|".join(re.escape(s) for s in SUBJECT_LABELS)
    for line in text.splitlines(keepends=True):
        clean = normalize(line).strip("#* ")
        cells = [normalize(c) for c in line.strip().strip("|").split("|")]
        if (line.lstrip().startswith("|")
                and any(re.match(r"^과학(?:$|\s|[ⅠⅡⅢIV123(（:：·ㆍ])", c) for c in cells)):
            hits.append(offset)
        # A subject-name list, composed entirely of names and separators.
        if "과학" in clean and re.fullmatch(rf"(?:{names}|[\s,ㆍ·/|、()])+", clean):
            hits.append(offset)
        offset += len(line)
    return sorted(set(hits))


def filename_subjects(filename: str) -> set[str]:
    # Filenames commonly use underscores, digits and a trailing '과'.
    return {name for name in SUBJECT_LABELS if re.search(
        rf"(?<![가-힣]){re.escape(name)}(?:과)?(?![가-힣])", filename)}


def target_windows(text: str, filename: str, sections: list[dict]) -> tuple[str, list, str]:
    lines, starts = line_index(text)
    science = [s for s in sections if s.get("science_candidate")]
    if not lines:
        return "excluded", [], "변환 본문 없음"
    names = filename_subjects(filename)
    if not science and names and "과학" not in names and len(names) == 1:
        return "excluded", [], "파일명이 다른 단일 교과를 가리킴"
    if science:
        headers = {h["key"] for h in subject_headers(text)}
        mixed = bool((headers | names) - {"과학"}) or any(
            s.get("status") in {"other", "mixed"} for s in sections)
        if not mixed:
            return "a_full", [(1, len(lines))], ""
        spans = []
        for section in science:
            lo, hi = line_span(starts, section["locator"]["start"], section["locator"]["end"])
            spans.append((max(1, lo - 80), min(len(lines), hi + 80)))
        return "a_context", union_ranges(spans), ""
    tables = table_spans(text)
    windows = []
    for hit in science_markers(text):
        table = next((t for t in tables if t["start"] <= hit < t["end"]), None)
        if table:
            windows.append(line_span(starts, table["start"], table["end"]))
        else:
            line = bisect.bisect_right(starts, hit)
            windows.append((max(1, line - 60), min(len(lines), line + 60)))
    return ("b_marker", union_ranges(windows), "") if windows else (
        "excluded", [], "본문에 과학 교과 표지 없음")


def split_window(lines: list[str], lo: int, hi: int,
                 limit: int = MAX_CHARS, overlap: int = OVERLAP) -> list[tuple[int, int]]:
    """Split at original line boundaries, including a >= overlap-sized suffix."""
    chunks = []
    start = lo
    while start <= hi:
        end, count = start - 1, 0
        while end < hi and count + len(lines[end]) <= limit:
            count += len(lines[end])
            end += 1
        if end < start:
            raise ValueError(f"단일 줄이 {limit}자를 초과함. 줄 경계 분할 불가 ({start}줄)")
        chunks.append((start, end))
        if end == hi:
            break
        next_start, retained = end + 1, 0
        while next_start > start + 1 and retained < overlap:
            next_start -= 1
            retained += len(lines[next_start - 1])
        # A very long overlap line must not prevent forward progress.
        start = next_start
    return chunks


def metadata_candidates(document: dict, sections: list[dict], key: str) -> list[int]:
    values = set()
    for entry in [*document.get("segments", []), *sections]:
        value = entry.get(key)
        if type(value) is int:
            values.add(value)
        for evidence in entry.get(f"{key}_evidence", []):
            if type(evidence.get(key)) is int:
                values.add(evidence[key])
    if key == "grade":
        values.update(document.get("grades", []))
    return sorted(values)


def build_targets(root: Path, round_key: str) -> dict:
    output = round_dir(root, round_key)
    s4 = read_json(root / f"data/derived/segments/{round_key}.json")
    s5 = read_json(root / f"data/derived/subjects/{round_key}.json")
    template = read_text(root / "scripts/prompts/middle_ai_read_v1.md")
    targets, excluded, selected = [], [], []
    for document in s4["documents"]:
        identity = document["document_id"]
        sections = [s for s in s5["sections"] if s["document_id"] == identity]
        source = document["source"]
        filename = document.get("member_name") or source["candidate_name"]
        description = {"document_id": identity, "school": source["school_name"],
                       "filename": filename, "converted_path": document["converted_path"]}
        if document.get("document_kind", "assessment_plan") != "assessment_plan":
            excluded.append({**description, "reason": "평가계획 문서가 아님"})
            continue
        conversion = conversion_for(root, document)
        text = conversion["text"]
        mode, windows, reason = target_windows(text, filename, sections)
        if not windows:
            excluded.append({**description, "reason": reason})
            continue
        selected.append({**description, "mode": mode, "windows": windows})
        lines, starts = line_index(text)
        metadata = {**description, "round": round_key, "school_code": source.get("school_code"),
                    "child_id": document.get("child_id"),
                    "original_path": document.get("original_path"),
                    "grade_candidates": metadata_candidates(document, sections, "grade"),
                    "semester_candidates": metadata_candidates(document, sections, "semester")}
        for lo, hi in windows:
            for left, right in split_window(lines, lo, hi):
                target_id = digest_id("ai_", VERSION, round_key, identity, left, right,
                                      document["text_sha256"])
                numbered = "".join(f"{i}\t{lines[i - 1]}" for i in range(left, right + 1))
                prompt = (template + "\n\n## 참고 메타데이터\n\n"
                          + json.dumps(metadata, ensure_ascii=False) + "\n\n"
                          + f"## 원문 (문서 전체 기준 {left}–{right}줄)\n\n"
                          + numbered)
                target = {**metadata, "target_id": target_id, "mode": mode,
                          "line_start": left, "line_end": right,
                          "start": starts[left - 1], "end": starts[right],
                          "text_sha256": document["text_sha256"],
                          "char_count": starts[right] - starts[left - 1],
                          "prompt_chars": len(prompt), "prompt_sha256": sha(prompt)}
                targets.append(target)
                write_text(output / f"prompts/{target_id}.md", prompt)
    write_text(output / "targets.jsonl", "".join(
        json.dumps(t, ensure_ascii=False) + "\n" for t in targets))
    summary = {"round": round_key, "documents": len(selected), "chunks": len(targets),
               "total_chars": sum(t["char_count"] for t in targets),
               "prompt_chars": sum(t["prompt_chars"] for t in targets),
               "expected_calls": len(targets), "selected": selected, "excluded": excluded}
    save_json(output / "summary.json", summary)
    return summary


def load_targets(output: Path) -> list[dict]:
    return [json.loads(line) for line in read_text(output / "targets.jsonl").splitlines()
            if line.strip()]


def audit_events(path: Path) -> dict:
    violations, unknown = [], Counter()
    completed = False
    count = 0
    try:
        lines = read_text(path).splitlines()
        for line in lines:
            event = json.loads(line)
            count += 1
            kind = event.get("type")
            if kind not in EVENT_TYPES:
                unknown[str(kind)] += 1
            if kind in {"turn.failed", "error"}:
                violations.append(kind)
            if kind == "turn.completed":
                completed = True
            nodes = [event]
            while nodes:
                node = nodes.pop()
                if isinstance(node, list):
                    nodes.extend(node)
                elif isinstance(node, dict):
                    if node.get("type") in TOOL_ITEMS:
                        violations.append(node["type"])
                    if any(node.get(key) for key in ("tool_calls", "function_call", "tool_name",
                                                      "command", "web_search", "file_read")):
                        violations.append("도구 실행 페이로드")
                    if str(node.get("model", "")).lower().startswith("gpt-6-astra"):
                        violations.append("제외 모델")
                    nodes.extend(node.values())
            if kind in {"item.started", "item.updated", "item.completed"}:
                item = event.get("item", {})
                item_type = item.get("type")
                if item_type in TOOL_ITEMS:
                    violations.append(str(item_type))
                elif item_type not in PASSIVE_ITEMS:
                    unknown[f"item:{item_type}"] += 1
    except (OSError, ValueError, AttributeError, TypeError):
        violations.append("이벤트 로그 누락 또는 JSON 형식 오류")
    if not completed:
        violations.append("turn.completed 없음")
    if unknown:
        violations.append("감사 불명")
    return {"valid": not violations, "violations": sorted(set(violations)),
            "unknown_types": dict(unknown), "unknown_count": sum(unknown.values()),
            "event_count": count}


def parse_response(path: Path) -> dict:
    value = read_json(path)
    if (not isinstance(value, dict) or not isinstance(value.get("tasks"), list)
            or not isinstance(value.get("uncertain"), list)):
        raise ValueError("tasks/uncertain 배열을 갖는 JSON 하나 필요")
    return value


def isolated_directory(path: Path) -> Path:
    path = path.resolve(strict=True)
    workspace = Path("D:/workspace").resolve()
    if not path.is_dir() or path.is_relative_to(workspace) or workspace.is_relative_to(path):
        raise ValueError("--isolated-cwd는 D:/workspace 밖의 빈 폴더여야 함")
    if any(path.iterdir()):
        raise ValueError("--isolated-cwd가 비어 있지 않음")
    return path


def default_model_guard():
    """Keep the configured default, refusing excluded defaults/profiles."""
    import os

    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    config_path = codex_home / "config.toml"
    if not config_path.exists():
        return
    config = tomllib.loads(read_text(config_path))
    profiles = config.get("profiles", {})
    profile = profiles.get(config.get("profile"), {})
    model = profile.get("model", config.get("model", ""))
    if str(model).lower().startswith("gpt-6-astra"):
        raise ValueError("기본 모델이 gpt-6-astra임. 총괄이 기본 모델을 변경해야 함")


def codex_command(cwd: Path, answer: Path) -> list[str]:
    return [CODEX, "exec", "--strict-config", "--skip-git-repo-check", "-s", "read-only",
            "-C", str(cwd), "--json", "-o", str(answer), "-"]


def valid_run(output: Path, target: dict) -> tuple[bool, dict]:
    identity = target["target_id"]
    status_path = output / f"responses/{identity}.status.json"
    answer = output / f"responses/{identity}.json"
    events = output / f"responses/{identity}.events.jsonl"
    try:
        status = read_json(status_path)
        audit = audit_events(events)
        parse_response(answer)
        valid = (status["valid"] and audit["valid"]
                 and status["prompt_sha256"] == target["prompt_sha256"]
                 and sha(read_text(output / f"prompts/{identity}.md")) == target["prompt_sha256"]
                 and status["answer_sha256"] == sha(read_text(answer))
                 and status["events_sha256"] == sha(read_text(events)))
        return bool(valid), audit
    except (OSError, ValueError, KeyError, TypeError):
        return False, {"valid": False, "violations": ["유효한 실행 기록 없음"]}


def run_targets(root: Path, round_key: str, isolated_cwd: Path, *, workers: int = 4,
                fake_responses: Path | None = None, dry_run: bool = False) -> dict:
    cwd = isolated_directory(isolated_cwd)
    if workers < 1:
        raise ValueError("--workers는 1 이상이어야 함")
    output = round_dir(root, round_key)
    targets = load_targets(output)
    if not fake_responses and not dry_run:
        default_model_guard()

    def one(target):
        identity = target["target_id"]
        answer = output / f"responses/{identity}.json"
        events = output / f"responses/{identity}.events.jsonl"
        prompt = read_text(output / f"prompts/{identity}.md")
        if sha(prompt) != target["prompt_sha256"]:
            raise ValueError("지시문 해시 불일치. targets부터 다시 생성해야 함")
        command = codex_command(cwd, answer)
        if dry_run:
            return {"target_id": identity, "command": subprocess.list2cmdline(command),
                    "stdin": str(output / f"prompts/{identity}.md")}
        if valid_run(output, target)[0]:
            return {"target_id": identity, "skipped": True, "valid": True}
        answer.parent.mkdir(parents=True, exist_ok=True)
        # Never let an old answer survive a failed retry.
        write_text(answer, "")
        failure = None
        if fake_responses:
            try:
                write_text(answer, read_text(fake_responses / f"{identity}.json"))
                fake_events = guard_path(fake_responses / f"{identity}.events.jsonl")
                write_text(events, read_text(fake_events))
            except OSError:
                failure = "가짜 응답 또는 이벤트 없음"
                write_text(events, "")
        else:
            # The prompt travels only on stdin. The child cwd contains no source files.
            with events.open("w", encoding="utf-8", newline="\n") as event_stream:
                try:
                    result = subprocess.run(command, input=prompt, encoding="utf-8",
                                            stdout=event_stream, stderr=subprocess.PIPE,
                                            cwd=cwd, timeout=TIMEOUT, check=False)
                    if result.returncode:
                        failure = f"Codex 종료 코드 {result.returncode}"
                    write_text(output / f"responses/{identity}.stderr.txt", result.stderr)
                except (subprocess.TimeoutExpired, OSError, UnicodeError) as error:
                    failure = f"호출 실패 {type(error).__name__}"
        audit = audit_events(events)
        try:
            parse_response(answer)
        except (OSError, ValueError):
            failure = failure or "답 JSON 형식 오류"
        status = {"target_id": identity, "prompt_sha256": target["prompt_sha256"],
                  "answer_sha256": sha(read_text(answer)),
                  "events_sha256": sha(read_text(events)),
                  "valid": audit["valid"] and failure is None, "audit": audit,
                  "failure": failure, "fake": fake_responses is not None}
        save_json(output / f"responses/{identity}.status.json", status)
        return status

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(one, targets))
    report = {"round": round_key, "dry_run": dry_run, "results": results,
              "valid": sum(r.get("valid", False) for r in results),
              "skipped": sum(r.get("skipped", False) for r in results),
              "unknown_events": sum(r.get("audit", {}).get("unknown_count", 0) for r in results)}
    if not dry_run:
        save_json(output / "run.json", report)
    return report


def normalized_map(raw: str) -> tuple[str, list[tuple[int, int]]]:
    """NFKC + collapsed whitespace, retaining a map back to raw codepoints."""
    units = []
    for match in re.finditer(r"<[^>]*>|&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);|.", raw, re.S):
        token = match[0]
        if token.startswith("<"):
            value = " " if re.match(r"<br\b", token, re.I) else ""
        else:
            value = html.unescape(token)
        for char in value:
            # Canonical composition and modern Hangul Jamo composition retain
            # the complete source cluster, including compatibility characters.
            normalized_char = unicodedata.normalize("NFKC", char)
            previous_normalized = unicodedata.normalize("NFKC", units[-1][0]) if units else ""
            joins_hangul = (
                "\u1160" <= normalized_char <= "\u11ff"
                and any("\u1100" <= c <= "\u11ff" or "\uac00" <= c <= "\ud7a3"
                        for c in previous_normalized))
            if units and (unicodedata.combining(char) or joins_hangul):
                previous, left, _ = units.pop()
                units.append((previous + char, left, match.end()))
            else:
                units.append((char, match.start(), match.end()))
    chars, offsets = [], []
    for value, left, right in units:
        for char in unicodedata.normalize("NFKC", value):
            if char.isspace():
                if chars and chars[-1] == " ":
                    offsets[-1] = offsets[-1][0], right
                elif chars:
                    chars.append(" ")
                    offsets.append((left, right))
            else:
                chars.append(char)
                offsets.append((left, right))
    if chars and chars[-1] == " ":
        chars.pop()
        offsets.pop()
    return "".join(chars), offsets


def normalize(raw: str) -> str:
    return normalized_map(raw)[0]


def literal_span(raw: str, quote: str, base: int, conversion: dict) -> dict:
    needle = normalize(quote)
    haystack, positions = normalized_map(raw)
    found = haystack.find(needle) if needle else -1
    while found >= 0:
        left, right = positions[found][0], positions[found + len(needle) - 1][1]
        # A substring inside an NFKC expansion (e.g. one digit of a fraction)
        # must never acquire a locator for the entire original character.
        if normalize(raw[left:right]) == needle:
            return {**text_locator(left + base, right + base, conversion), "text_field": "text"}
        found = haystack.find(needle, found + 1)
    raise ValueError("원문 글자 불일치")


def checked_lines(target: dict, starts: list[int], lo, hi) -> tuple[int, int]:
    if (type(lo) is not int or type(hi) is not int
            or not target["line_start"] <= lo <= hi <= target["line_end"]
            or hi >= len(starts)):
        raise ValueError("줄 번호가 조각 범위 밖임")
    return starts[lo - 1], starts[hi]


def check_scope(task: dict, key: str, target: dict, text: str,
                starts: list[int], conversion: dict) -> dict | str:
    value = task.get(key)
    allowed = {1, 2, 3} if key == "grade" else {1, 2}
    if type(value) is not int or value not in allowed:
        raise ValueError(f"{key} 값 오류")
    evidence = task.get(f"{key}_evidence")
    if evidence == "metadata":
        if target.get(f"{key}_candidates") != [value]:
            raise ValueError(f"{key} 메타데이터가 하나로 확정되지 않음")
        return "metadata"
    if not isinstance(evidence, dict):
        raise ValueError(f"{key} 근거 없음")
    line = evidence.get("line")
    start, end = checked_lines(target, starts, line, line)
    quote = evidence.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        raise ValueError(f"{key} 인용 없음")
    locator = literal_span(text[start:end], quote, start, conversion)
    clean = normalize(quote)
    if key == "grade":
        numbers = set(re.findall(r"(?<!\d)\(?\s*([123])\s*\)?\s*학년", clean))
        numbers.update(re.findall(
            r"(?<![가-힣A-Za-z\d])(?:중학교|중)\s*\(?([123])\)?(?!\d)", clean))
        combined = re.search(r"[123]\s*[·ㆍ,/~∼-]\s*[123]\s*학년", clean)
    else:
        numbers = set(re.findall(r"(?<!\d)\(?\s*([12])\s*\)?\s*학기", clean))
        combined = re.search(r"[12]\s*[·ㆍ,/~∼-]\s*[12]\s*학기", clean)
    if numbers != {str(value)} or combined:
        raise ValueError(f"{key} 인용에 단일 학년·학기 표지가 없음")
    return {"raw": text[locator["start"]:locator["end"]], "locator": locator}


def verify_task(task: dict, target: dict, conversion: dict) -> dict:
    text = conversion["text"]
    _, starts = line_index(text)
    title = task.get("title")
    if not isinstance(title, str) or not normalize(title):
        raise ValueError("제목 없음")
    title_line = task.get("title_line")
    title_start, title_end = checked_lines(target, starts, title_line, title_line)
    title_locator = literal_span(text[title_start:title_end], title, title_start, conversion)
    source_evidence = task.get("evidence")
    if not isinstance(source_evidence, list) or not source_evidence:
        raise ValueError("과제 근거 없음")
    evidence = []
    covers_title = False
    for item in source_evidence:
        lo, hi = item.get("line_start"), item.get("line_end")
        start, end = checked_lines(target, starts, lo, hi)
        quote = item.get("quote")
        if not isinstance(quote, str) or not quote.strip() or len(quote) > 200:
            raise ValueError("근거 인용은 1–200자여야 함")
        locator = literal_span(text[start:end], quote, start, conversion)
        evidence.append({"raw": text[locator["start"]:locator["end"]],
                         "text": normalize(quote), "locator": locator,
                         "line_start": lo, "line_end": hi})
        if lo <= title_line <= hi:
            covers_title = True
    if not covers_title:
        raise ValueError("제목이 근거 인용 줄 범위 밖임")
    grade_evidence = check_scope(task, "grade", target, text, starts, conversion)
    semester_evidence = check_scope(task, "semester", target, text, starts, conversion)
    if task.get("seen_in") not in {"overview", "detail", "both"}:
        raise ValueError("seen_in 값 오류")
    # Store source spelling, even when the supplied title used equivalent spacing.
    raw_title = text[title_locator["start"]:title_locator["end"]]
    metadata_keys = ("document_id", "child_id", "school", "school_code", "filename",
                     "converted_path", "original_path", "text_sha256", "round")
    return {**{k: target.get(k) for k in metadata_keys},
            "ai_task_id": digest_id("aitask_", target["document_id"], task["grade"],
                                    task["semester"], normalize(title), title_locator),
            "title": normalize(raw_title), "title_raw": raw_title, "title_line": title_line,
            "title_locator": title_locator, "grade": task["grade"], "semester": task["semester"],
            "grade_evidence": grade_evidence, "semester_evidence": semester_evidence,
            "evidence": evidence, "locators": [e["locator"] for e in evidence],
            "locator": {**text_locator(min(e["locator"]["start"] for e in evidence),
                                       max(e["locator"]["end"] for e in evidence), conversion),
                        "text_field": "text"},
            "seen_in": task["seen_in"], "target_ids": [target["target_id"]]}


def overlaps(left: dict, right: dict) -> bool:
    return left["start"] < right["end"] and right["start"] < left["end"]


def deduplicate(tasks: list[dict]) -> list[dict]:
    result = []
    for task in sorted(tasks, key=lambda t: (t["document_id"], t["title_locator"]["start"])):
        duplicate = next((old for old in result if (
            (old["document_id"], old.get("child_id"), old["grade"], old["semester"],
             normalize(old["title"])) == (task["document_id"], task.get("child_id"),
                                         task["grade"], task["semester"], normalize(task["title"]))
            and any(overlaps(a, b) for a in old["locators"] for b in task["locators"]))), None)
        if duplicate is None:
            result.append(copy.deepcopy(task))
            continue
        duplicate["target_ids"] = sorted(set(duplicate["target_ids"] + task["target_ids"]))
        for evidence in task["evidence"]:
            if evidence not in duplicate["evidence"]:
                duplicate["evidence"].append(evidence)
        duplicate["locators"] = [e["locator"] for e in duplicate["evidence"]]
        duplicate["locator"]["start"] = min(loc["start"] for loc in duplicate["locators"])
        duplicate["locator"]["end"] = max(loc["end"] for loc in duplicate["locators"])
        if "pages" in duplicate["locator"]:
            pages = sorted({page for loc in duplicate["locators"] for page in loc.get("pages", [])})
            duplicate["locator"].update({"pages": pages,
                                         "page_start": pages[0] if pages else None,
                                         "page_end": pages[-1] if pages else None})
        if duplicate["seen_in"] != task["seen_in"]:
            duplicate["seen_in"] = "both"
    return result


def verify_targets(root: Path, round_key: str) -> dict:
    output = round_dir(root, round_key)
    kept, discarded, outside, uncertain = [], [], [], []
    cache, bindings = {}, {}
    for target in load_targets(output):
        valid, audit = valid_run(output, target)
        if not valid:
            discarded.append({"target_id": target["target_id"], "reason": "실행 감사·무결성 실패",
                              "audit": audit})
            continue
        status = read_json(output / f"responses/{target['target_id']}.status.json")
        binding_keys = ("prompt_sha256", "answer_sha256", "events_sha256", "fake")
        bindings[target["target_id"]] = {k: status[k] for k in binding_keys}
        path = target["converted_path"]
        if path not in cache:
            cache[path] = conversion_for(root, target)
        conversion = cache[path]
        if sha(conversion["text"]) != target["text_sha256"]:
            raise ValueError("조각 간 원문 해시 충돌")
        response = parse_response(output / f"responses/{target['target_id']}.json")
        uncertain.extend({"target_id": target["target_id"], "value": u}
                         for u in response["uncertain"])
        for task in response["tasks"]:
            try:
                verified = verify_task(task, target, conversion)
            except (ValueError, TypeError, AttributeError, KeyError) as error:
                discarded.append({"target_id": target["target_id"], "task": task,
                                  "reason": str(error)})
                continue
            if verified["grade"] not in {1, 2}:
                outside.append({**verified, "reason": "범위 밖"})
            else:
                kept.append(verified)
    report = {"schema_version": 1, "rule_version": VERSION, "round": round_key,
              "kept": deduplicate(kept), "discarded": discarded,
              "out_of_scope": deduplicate(outside), "uncertain": uncertain,
              "targets_sha256": sha(read_text(output / "targets.jsonl")),
              "run_bindings": bindings, "simulated": any(b["fake"] for b in bindings.values())}
    report["summary"] = {k: len(report[k]) for k in
                         ("kept", "discarded", "out_of_scope", "uncertain")}
    save_json(output / "verified.json", report)
    return report


def ai_item(task: dict) -> dict:
    identity = task["ai_task_id"]
    fields = {name: {"value": [], "status": "unconfirmed", "evidence": [],
                     "reason": "AI 읽기 1단계: 필드 미추출"} for name in FIELDS}
    for name in ("title", "assessment_area", "task_no", "timing", "score", "points",
                 "weight", "essay_weight", "rubric", "criteria", "free_semester"):
        fields[name]["value"] = ""
    fields["title"] = {"value": task["title"], "status": "present", "reason": "",
                       "evidence": [{"raw": task["title_raw"], "text": task["title"],
                                     "locator": task["title_locator"], "owner_item_id": identity}]}
    return {**{k: task.get(k) for k in ("document_id", "child_id", "school", "school_code",
                                       "filename", "converted_path", "original_path",
                                       "text_sha256", "grade", "semester")},
            "item_id": identity, "segment_id": None, "section_id": None,
            "rule_version": VERSION, "layout": "ai_read", "table_role": task["seen_in"],
            "candidate_role": "performance", "role_basis": "AI 읽기 원문 검증",
            "layout_position": {"table": None, "row": None, "col": None},
            "boundary_evidence": {"ai_evidence": task["evidence"],
                                  "grade_evidence": task["grade_evidence"],
                                  "semester_evidence": task["semester_evidence"]},
            "locator": task["locator"], "fields": fields, "title_role": "title",
            "title_authenticity": "source_text_candidate", "title_specificity_score": 0,
            "title_generated": False, "links": [], "completeness_status": "completion_unconfirmed",
            "owned_ranges": task["locators"], "shared_fields": [],
            "extraction_status": "ai_verified", "extraction_method": "ai_read",
            "review_reasons": ["AI 읽기 1단계: 필드 미추출"], "subject_status": "target",
            "public_eligible": False, "target_ids": task["target_ids"]}


def merge_report(rules: dict, verified: dict) -> dict:
    result = copy.deepcopy(rules)
    tasks = verified["kept"]
    performance = [i for i in result["items"] if i.get("candidate_role") == "performance"]
    by_task = {}
    by_rule = {i["item_id"]: [] for i in performance}
    for task in tasks:
        matches = [item for item in performance if (
            (item["document_id"], item.get("child_id"), item.get("grade"), item.get("semester"))
            == (task["document_id"], task.get("child_id"), task["grade"], task["semester"]))
            and any(overlaps(item["locator"], loc) for loc in task["locators"])]
        by_task[task["ai_task_id"]] = matches
        for item in matches:
            by_rule[item["item_id"]].append(task["ai_task_id"])
    relations = {"agrees": [], "ai_split_suggested": [], "conflict": [], "new": []}
    for item in performance:
        ids = by_rule[item["item_id"]]
        if len(ids) > 1:
            kind = "conflict" if item["extraction_status"] == "bounded" else "ai_split_suggested"
            relations[kind].append({"rule_item_id": item["item_id"], "ai_task_ids": ids})
            # Keep every rule item byte-for-byte equivalent. Its annotation is
            # keyed by item ID in ai_relations, rather than rewriting the item.
    for task in tasks:
        matches = by_task[task["ai_task_id"]]
        if len(matches) > 1:
            relations["conflict"].append({"ai_task_ids": [task["ai_task_id"]],
                                          "rule_item_ids": [i["item_id"] for i in matches],
                                          "reason": "AI 과제가 규칙 항목 여러 개와 겹침"})
            continue
        if matches:
            item = matches[0]
            if len(by_rule[item["item_id"]]) == 1:
                relations["agrees"].append({"ai_task_id": task["ai_task_id"],
                                            "rule_item_id": item["item_id"],
                                            "bounded": item["extraction_status"] == "bounded"})
                continue
            if item["extraction_status"] == "bounded":
                continue
        result["items"].append(ai_item(task))
        relations["new"].append({"ai_task_id": task["ai_task_id"],
                                  "item_id": task["ai_task_id"],
                                  "reason": "덩어리 분할" if matches else "규칙 겹침 없음"})
    result["ai_relations"] = relations
    result["ai_read_summary"] = {"rule_items": len(rules["items"]),
                                  "added_items": len(relations["new"]),
                                  "relations": {k: len(v) for k, v in relations.items()}}
    return result


def merge_targets(root: Path, round_key: str) -> dict:
    output = round_dir(root, round_key)
    rules = read_json(root / f"data/derived/items/{round_key}.json")
    verified = read_json(output / "verified.json")
    if verified["round"] != round_key or rules["round"] != round_key:
        raise ValueError("병합 회차 불일치")
    if verified["targets_sha256"] != sha(read_text(output / "targets.jsonl")):
        raise ValueError("targets가 변경됨. verify를 다시 실행해야 함")
    targets = {t["target_id"]: t for t in load_targets(output)}
    for identity, binding in verified["run_bindings"].items():
        status = read_json(output / f"responses/{identity}.status.json")
        if (not valid_run(output, targets[identity])[0]
                or any(status[key] != value for key, value in binding.items())):
            raise ValueError("응답이 변경됨. verify를 다시 실행해야 함")
    for task in verified["kept"]:
        conversion_for(root, task)
    result = merge_report(rules, verified)
    result["ai_read_summary"]["simulated"] = verified["simulated"]
    result["ai_read_summary"]["rule_input_sha256"] = sha(json.dumps(rules, sort_keys=True))
    result["ai_read_summary"]["verification_sha256"] = sha(json.dumps(verified, sort_keys=True))
    save_json(root / f"data/derived/items_ai/{round_key}.json", result)
    return result


def markdown_cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def reference_rows(path: Path) -> dict:
    result = {}
    current = None
    for line in read_text(path).splitlines():
        heading = re.match(r"###\s+(S\d+)\b", line)
        if heading:
            current = heading[1]
            result[current] = {"rows": [], "unreadable": False}
        if current is None or not line.startswith("|"):
            continue
        cells = markdown_cells(line)
        if len(cells) != 7 or cells[0] == "제목" or cells[0].startswith("---"):
            continue
        if cells[0].startswith("판독 불가"):
            result[current]["unreadable"] = True
            continue
        spans = []
        for match in re.finditer(r"(?<!\d)(\d+)\s*[–—~〜∼-]\s*(\d+)(?!\d)", cells[6]):
            spans.append((int(match[1]), int(match[2])))
        remaining = re.sub(r"\d+\s*[–—~〜∼-]\s*\d+", "", cells[6])
        spans.extend((int(n), int(n)) for n in re.findall(r"\b\d+\b", remaining))
        result[current]["rows"].append({"title": cells[0], "source_lines": spans,
                                        "raw_cells": cells})
    return result


def chief_rows(path: Path | None) -> dict:
    result = {}
    if path is None:
        return result
    for line in read_text(path).splitlines():
        cells = markdown_cells(line)
        if len(cells) < 7:
            continue
        cell_id = re.match(r"(S\d+)\b", cells[0])
        count = re.match(r"(\d+)", cells[1])
        if cell_id and count:
            result[cell_id[1]] = {"reference_count": int(count[1]), "note": cells[-1],
                                   "historical_counts": cells[2:6], "source": str(path)}
    return result


def load_references(root: Path) -> list[dict]:
    directory = root / "docs/dev"
    references = []
    for sample_path in sorted(directory.glob("2026-11-0[89]-s6d2*-review-sample.json")):
        suffix = sample_path.name.split("-s6d2", 1)[1].removesuffix("-review-sample.json")
        reviews = sorted(directory.glob(f"2026-11-0[89]-s6d2{suffix}-astra-review.md"))
        checks = sorted(directory.glob(f"2026-11-0[89]-s6d2{suffix}-check.md"))
        if not reviews:
            raise ValueError(f"개발 참고 목록 없음 {sample_path.name}")
        rows = reference_rows(reviews[-1])
        judgments = chief_rows(checks[-1] if checks else None)
        for cell in read_json(sample_path)["source_review"]:
            review = rows.get(cell["cell_id"])
            if review is None:
                raise ValueError("참고 목록의 칸 누락")
            chief = judgments.get(cell["cell_id"])
            references.append({"sample": sample_path.name, "cell": cell, **review,
                               "chief": chief, "reference_source": str(reviews[-1]),
                               "reference_count": chief["reference_count"] if chief else
                               len(review["rows"])})
    return references


def compare_reference(rows: list[dict], items: list[dict], text_cache: dict) -> dict:
    """One-to-one literal title matches, with unique source-range suggestions."""
    used, matches, missed = set(), [], []
    for row in rows:
        title = normalize(re.sub(r"〔.*?〕", "", row["title"]))
        candidates = [i for i in items if i["item_id"] not in used and title in {
            normalize(str(n)) for n in [i["fields"]["title"]["value"],
                                        *i["fields"]["title"].get("aliases", [])]}]
        if candidates:
            item = candidates[0]
            used.add(item["item_id"])
            matches.append({"reference": row, "item_id": item["item_id"],
                            "basis": "normalized_literal_title"})
        else:
            suggestions = []
            for item in items:
                if item["item_id"] in used:
                    continue
                locs = item["fields"]["title"]["evidence"]
                text = text_cache[item["converted_path"]]
                for observation in locs:
                    # Count line starts correctly when the locator follows a newline.
                    line = text.count("\n", 0, observation["locator"]["start"]) + 1
                    if any(lo <= line <= hi and sum((lo, hi) in r["source_lines"]
                           for r in rows) == 1 for lo, hi in row["source_lines"]):
                        suggestions.append(item["item_id"])
                        break
            missed.append({"reference": row, "source_position_suggestions": suggestions})
    extras = [{"item_id": i["item_id"], "title": i["fields"]["title"]["value"]}
              for i in items if i["item_id"] not in used]
    return {"found": len(matches), "reference": len(rows), "predicted": len(items),
            "precision": len(matches) / len(items) if items else None,
            "recall": len(matches) / len(rows) if rows else None,
            "matches": matches, "missed": missed, "extra": extras}


def difference_type(title: str) -> str:
    if re.search(r"지필|정기|중간고사|기말고사", title):
        return "정기시험 의심"
    if re.search(r"기본점수|미인정|결석|특수교육", title):
        return "점수 처리 규정 의심"
    if re.search(r"단원|진도|수업|성취수준", title):
        return "운영표·단원 의심"
    return "제목·경계·귀속 대조 필요"


def evaluate_targets(root: Path, round_key: str) -> dict:
    if round_key not in DEV_ROUNDS:
        raise ValueError("evaluate는 지정된 보충 두 회차만 지원함")
    output = round_dir(root, round_key)
    verified = read_json(output / "verified.json")
    rules = read_json(root / f"data/derived/items/{round_key}.json")
    merged = read_json(root / f"data/derived/items_ai/{round_key}.json")
    provenance = merged["ai_read_summary"]
    if (provenance["rule_input_sha256"] != sha(json.dumps(rules, sort_keys=True))
            or provenance["verification_sha256"] != sha(json.dumps(verified, sort_keys=True))):
        raise ValueError("규칙·검증 결과 변경. merge를 다시 실행해야 함")
    references = load_references(root)
    ai = [ai_item(t) for t in verified["kept"]]
    bounded = [i for i in rules["items"] if i.get("candidate_role") == "performance"
               and i["extraction_status"] == "bounded"]
    added = [i for i in merged["items"] if i.get("extraction_method") == "ai_read"]
    cells, differences, chief_confirmation = [], [], []
    text_cache = {}
    for item in [*ai, *bounded, *added]:
        if item["converted_path"] not in text_cache:
            text_cache[item["converted_path"]] = conversion_for(root, item)["text"]
    for reference in references:
        cell = reference["cell"]
        if cell["round"] != round_key:
            continue
        allowed_paths = {d["converted_path"] for d in cell.get("source_documents", [])}
        allowed_paths.update(d["converted_path"] for d in cell.get("science_ranges", []))

        def in_cell(item, cell=cell, allowed_paths=allowed_paths):
            return (item["school"], item["grade"], item["semester"]) == (
                cell["school"], cell["grade"], cell["semester"]) and (
                not allowed_paths or item["converted_path"] in allowed_paths)

        entry = {"sample": reference["sample"], "cell": cell,
                 "chief": reference["chief"], "unreadable": reference["unreadable"],
                 "reference_count": reference["reference_count"]}
        if reference["unreadable"]:
            cells.append(entry)
            continue
        for name, candidates in (("ai", ai), ("bounded", bounded),
                                 ("union", [*bounded, *added])):
            comparison = compare_reference(reference["rows"], list(filter(in_cell, candidates)),
                                           text_cache)
            # Chief counts supersede the independent list, but historical rule
            # counts do not describe today's rules and are retained as context.
            comparison["reference"] = reference["reference_count"]
            comparison["recall"] = comparison["found"] / reference["reference_count"] if (
                reference["reference_count"]) else None
            entry[name] = comparison
        if reference["reference_count"] != len(reference["rows"]):
            chief_confirmation.append({"sample": reference["sample"], "cell_id": cell["cell_id"],
                                       "kind": "총괄 판정 차이",
                                       "chief": reference["chief"],
                                       "independent_list_count": len(reference["rows"])})
        rule_found = {normalize(m["reference"]["title"]) for m in entry["bounded"]["matches"]}
        for match in entry["ai"]["matches"]:
            if normalize(match["reference"]["title"]) not in rule_found:
                differences.append({"sample": reference["sample"], "cell_id": cell["cell_id"],
                                    "school": cell["school"], "kind": "AI가 더 찾음",
                                    "type": "규칙 확정 밖 추가 확인", "value": match})
        for kind, values in (("AI 오검출 의심", entry["ai"]["extra"]),
                             ("AI 놓침 의심", entry["ai"]["missed"])):
            for value in values:
                title = value.get("title", value.get("reference", {}).get("title", ""))
                record = {"sample": reference["sample"], "cell_id": cell["cell_id"],
                          "school": cell["school"], "kind": kind,
                          "type": difference_type(title), "value": value}
                differences.append(record)
                chief_confirmation.append(record)
        cells.append(entry)
    totals = {}
    for name in ("ai", "bounded", "union"):
        total = {key: sum(c[name][key] for c in cells if name in c)
                 for key in ("found", "reference", "predicted")}
        total["precision"] = total["found"] / total["predicted"] if total["predicted"] else None
        total["recall"] = total["found"] / total["reference"] if total["reference"] else None
        totals[name] = total
    report = {"round": round_key, "metric_type": "개발 참고 지표·총괄 확인 필요",
              "simulated": verified["simulated"],
              "reference_is_truth": False, "matching": "NFKC·태그 제거·공백 접기 제목 일대일",
              "reference_total_cells": len(references), "cells": cells, "totals": totals,
              "differences": differences, "chief_confirmation": chief_confirmation}
    save_json(output / "evaluation.json", report)
    lines = ["# S6e-1 개발 참고 대조", "", "참고 목록과 제목을 글자 단위로 대조했다. "
             "의미가 같아 보이는 제목도 자동 확정하지 않는다. 불일치는 총괄 확인 대상이다.", "",
             "| 표본·칸 | AI 찾음/참고 | AI 정밀도 | bounded 찾음/참고 | bounded 정밀도 | "
             "합집합 찾음/참고 | 합집합 정밀도 |", "|---|---|---|---|---|---|---|"]
    for cell in cells:
        if cell["unreadable"]:
            lines.append(f"| {cell['sample']} {cell['cell']['cell_id']} | 판독 불가 | | | | | |")
            continue
        values = []
        for name in ("ai", "bounded", "union"):
            metric = cell[name]
            precision = f"{metric['precision']:.1%}" if metric['precision'] is not None else "—"
            values.extend([f"{metric['found']}/{metric['reference']}", precision])
        lines.append(f"| {cell['sample']} {cell['cell']['cell_id']} | " + " | ".join(values) + " |")
    counts = Counter((d["kind"], d["type"]) for d in differences)
    lines += ["", "## 유형별 차이", "", "| 구분 | 유형 | 수 |", "|---|---|---:|"]
    lines.extend(f"| {kind} | {category} | {count} |" for (kind, category), count in counts.items())
    lines += ["", "## 총괄 확인", "", "| 표본·칸 | 구분 | 내용 |", "|---|---|---|"]
    for row in chief_confirmation:
        detail = json.dumps(row.get("value", row.get("chief")), ensure_ascii=False)
        detail = detail.replace("|", "\\|")
        lines.append(f"| {row['sample']} {row['cell_id']} | {row['kind']} | {detail} |")
    write_text(output / "evaluation.md", "\n".join(lines) + "\n")
    return report


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("targets", "run", "verify", "merge", "evaluate"):
        command = commands.add_parser(name)
        command.add_argument("--round-key", required=True)
        if name == "run":
            command.add_argument("--isolated-cwd", type=Path, required=True)
            command.add_argument("--workers", type=int, default=4)
            command.add_argument("--fake-responses", type=Path)
            command.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.command == "targets":
            result = build_targets(ROOT, args.round_key)
            print(json.dumps({k: v for k, v in result.items() if k not in {"selected", "excluded"}},
                             ensure_ascii=False))
        elif args.command == "run":
            result = run_targets(ROOT, args.round_key, args.isolated_cwd, workers=args.workers,
                                 fake_responses=args.fake_responses, dry_run=args.dry_run)
            if args.dry_run:
                for entry in result["results"]:
                    print(entry["command"])
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "verify":
            print(json.dumps(verify_targets(ROOT, args.round_key)["summary"], ensure_ascii=False))
        elif args.command == "merge":
            result = merge_targets(ROOT, args.round_key)
            print(json.dumps(result["ai_read_summary"], ensure_ascii=False))
        else:
            print(json.dumps(evaluate_targets(ROOT, args.round_key)["totals"], ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
