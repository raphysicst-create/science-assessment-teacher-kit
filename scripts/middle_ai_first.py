"""AI-first science task targets, offline-capable runs and literal verification.

Run: .venv/Scripts/python.exe scripts/middle_ai_first.py targets --round-key RK
Commands: targets, run, verify, merge, methods (run accepts --fake-responses).
Verify: .venv/Scripts/python.exe -m pytest -q
        services/math-assessment-api/tests/test_middle_ai_first.py
Importing this module never starts an AI process.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if __package__:
    from . import middle_ai_read as ai
    from .course_subject import course_name_before, is_non_science_course
    from .middle_ai_first_merge import VERSION, fill_methods, merge_targets
    from .middle_ai_first_merge import merge_report as merge_report
    from .middle_fields import method_literal
    from .middle_items import (
        METHOD_BOX_RE,
        SCORER_RE,
        method_options,
        split_method_text,
        standard_values,
    )
    from .middle_segments import digest_id, text_locator
else:
    import middle_ai_read as ai
    from course_subject import course_name_before, is_non_science_course
    from middle_ai_first_merge import VERSION, fill_methods, merge_targets
    from middle_ai_first_merge import merge_report as merge_report
    from middle_fields import method_literal
    from middle_items import (
        METHOD_BOX_RE,
        SCORER_RE,
        method_options,
        split_method_text,
        standard_values,
    )
    from middle_segments import digest_id, text_locator

ROOT = Path(__file__).resolve().parents[1]
METHOD_STEM_RE = re.compile(
    r"실험|실습|실기|보고서|관찰|서술|논술|구술|발표|토의|토론|프로젝트|포트폴리오|"
    r"면접|글쓰기|작품|산출물|조사|탐구|과정|기록장|활동지|체크리스트"
)


def select_windows(document, sections, filename, conversion):
    if ai.g1_out_of_scope(filename, document, sections):
        return "excluded", [], "중3 전용 또는 다른 교과 파일명"
    text = conversion["text"]
    if not text.strip():
        return "excluded", [], "변환 본문 없음"
    outside = re.sub(r"[(（][^)）]*[)）]", " ", filename)
    if ai.filename_subjects(outside) == {"과학"}:
        return "f_filename", [(1, len(ai.line_index(text)[0]))], ""
    mode, windows, reason = ai.target_windows(text, filename, sections)
    if mode in {"a_full", "a_context", "b_marker"} and windows:
        return mode, ai.union_ranges(windows), ""
    fallback = ai.plaintext_fallback_window(conversion, sections)
    if fallback:
        return "plaintext_fallback", [(w["line_start"], w["line_end"]) for w in fallback], ""
    return "excluded", [], reason or "과학 대상 창 없음"


def document_targets(output, template, metadata, mode, windows, text_sha256, text):
    lines, starts = ai.line_index(text)
    targets = []
    for lo, hi in windows:
        for left, right in ai.split_window(lines, lo, hi, limit=60_000, overlap=3_000):
            identity = digest_id("aif_", VERSION, metadata["round"], metadata["document_id"],
                                 left, right, text_sha256)
            numbered = "".join(f"{i}\t{lines[i - 1]}" for i in range(left, right + 1))
            prompt = (template + "\n\n## 참고 메타데이터\n\n"
                      + json.dumps(metadata, ensure_ascii=False) + "\n\n"
                      + f"## 원문 (문서 전체 기준 {left}–{right}줄)\n\n" + numbered)
            targets.append({**metadata, "target_id": identity, "mode": mode,
                            "line_start": left, "line_end": right,
                            "start": starts[left - 1], "end": starts[right],
                            "text_sha256": text_sha256,
                            "char_count": starts[right] - starts[left - 1],
                            "prompt_chars": len(prompt), "prompt_sha256": ai.sha(prompt)})
            ai.write_text(output / f"prompts/{identity}.md", prompt)
    return targets


def build_targets(root: Path, round_key: str) -> dict:
    output = ai.round_dir(root, round_key) / "first"
    documents = ai.read_json(root / f"data/derived/segments/{round_key}.json")["documents"]
    sections = ai.read_json(root / f"data/derived/subjects/{round_key}.json")["sections"]
    template = ai.read_text(root / "scripts/prompts/middle_ai_first_v1.md")
    targets, selected, excluded = [], [], []
    for document in documents:
        identity, source = document["document_id"], document["source"]
        local = [s for s in sections if s["document_id"] == identity]
        filename = document.get("member_name") or source["candidate_name"]
        description = {"document_id": identity, "school": source["school_name"],
                       "filename": filename, "converted_path": document["converted_path"]}
        if document.get("document_kind", "assessment_plan") != "assessment_plan":
            excluded.append({**description, "reason": "평가계획 문서가 아님"})
            continue
        conversion = ai.conversion_for(root, document)
        mode, windows, reason = select_windows(document, local, filename, conversion)
        if not windows:
            excluded.append({**description, "reason": reason})
            continue
        selected.append({**description, "mode": mode, "windows": windows})
        metadata = {**description, "round": round_key, "selection_mode": "first",
                    "school_code": source.get("school_code"), "child_id": document.get("child_id"),
                    "original_path": document.get("original_path"),
                    "grade_candidates": ai.metadata_candidates(document, local, "grade"),
                    "semester_candidates": ai.metadata_candidates(document, local, "semester")}
        targets.extend(document_targets(output, template, metadata, mode, windows,
                                        document["text_sha256"], conversion["text"]))
    ai.write_text(output / "targets.jsonl", "".join(
        json.dumps(t, ensure_ascii=False) + "\n" for t in targets))
    summary = {"round": round_key, "selection_mode": "first", "documents": len(selected),
               "chunks": len(targets), "total_chars": sum(t["char_count"] for t in targets),
               "prompt_chars": sum(t["prompt_chars"] for t in targets),
               "expected_calls": len(targets), "selected": selected, "excluded": excluded,
               "selection_modes": dict(Counter(d["mode"] for d in selected))}
    ai.save_json(output / "summary.json", summary)
    return summary


def run_targets(root, round_key, isolated_cwd, *, workers=6, model=None,
                fake_responses=None, dry_run=False):
    if not 1 <= workers <= 8:
        raise ValueError("--workers는 1~8이어야 함 (동시 8 초과 웹소켓 403)")
    output = ai.round_dir(root, round_key) / "first"
    model = ai.resolve_ai_model(model)
    arguments = {"workers": workers, "model": model, "fake_responses": fake_responses,
                 "dry_run": dry_run, "output_dir": output}
    targets = ai.load_targets(output)
    attempts = [ai.run_targets(root, round_key, isolated_cwd, **arguments)]
    if not dry_run and any(not ai.valid_run(output, t, model=model)[0] for t in targets):
        attempts.append(ai.run_targets(root, round_key, isolated_cwd, **arguments))
    valid = sum(ai.valid_run(output, t, model=model)[0] for t in targets)
    metrics = [{key: a[key] for key in ("called", "valid", "mean_elapsed_seconds")}
               for a in attempts]
    report = {"round": round_key, "model": model, "workers": workers, "dry_run": dry_run,
              "first_pass": metrics[0], "retry_pass": metrics[1] if len(metrics) > 1 else None,
              "called": sum(a["called"] for a in attempts), "valid": valid, "total": len(targets),
              "elapsed_seconds": round(sum(r.get("elapsed_seconds", 0)
                                           for a in attempts for r in a["results"]), 1),
              "all_failed": not dry_run and bool(targets) and valid == 0}
    ai.save_json(output / "run_summary.json", report)
    return report


def detail_for(task, verified, target, conversion):
    detail = task.get("detail_lines")
    if detail is None:
        return None
    _, starts = ai.line_index(conversion["text"])
    start, end = ai.checked_lines(target, starts, detail["line_start"], detail["line_end"])
    locator = {**text_locator(start, end, conversion), "text_field": "text"}
    ranges = [(verified["title_line"], verified["title_line"])]
    ranges.extend((e["line_start"], e["line_end"]) for e in verified["evidence"])
    anchors = [dict(zip(("start", "end"), ai.checked_lines(target, starts, lo, hi), strict=True))
               for lo, hi in ranges]
    if (not any(ai.overlaps(locator, loc) for loc in anchors)
            and ai.normalize(verified["title"]) not in ai.normalize(conversion["text"][start:end])):
        raise ValueError("세부표가 제목·근거와 연결되지 않음")
    return locator


def verify_method(method, verified, target, conversion):
    value, line = method["text"], method["line"]
    text = conversion["text"]
    _, starts = ai.line_index(text)
    start, end = ai.checked_lines(target, starts, line, line)
    ranges = [(e["line_start"], e["line_end"]) for e in verified["evidence"]]
    if verified.get("detail_locator"):
        ranges.append(ai.line_span(starts, verified["detail_locator"]["start"],
                                   verified["detail_locator"]["end"]))
    if not any(lo <= line <= hi for lo, hi in ranges):
        raise ValueError("방법이 과제 근거·세부표 범위 밖임")
    if not isinstance(value, str) or not 1 <= len(value) <= 20:
        raise ValueError("방법 이름은 1~20자여야 함")
    if SCORER_RE.fullmatch(value) or split_method_text(value) != (value, []):
        raise ValueError("평가 주체·수행 형태 또는 혼합 값")
    if not METHOD_STEM_RE.search(value):
        raise ValueError("지원 범위 밖 방법" if method_literal(value) else "방법 낱말 없음")
    raw = text[start:end]
    locator = ai.literal_span(raw, value, start, conversion)
    if METHOD_BOX_RE.search(raw):
        options = method_options({"raw": raw, "locator": text_locator(start, end, conversion)})
        checked = [o for o in options if value in o["option_text"] and o["state"] == "checked"]
        if not checked:
            raise ValueError("코드 판독상 체크된 방법 선택지가 아님")
        option = checked[0]
        locator = ai.literal_span(option["raw"], value, option["locator"]["start"], conversion)
    if text[locator["start"]:locator["end"]] != value:
        raise ValueError("방법 원문 글자 불일치")
    return {"text": value, "raw": value, "line": line, "locator": locator}


def verify_extras(task, verified, target, conversion):
    verified.update(detail_locator=None, methods_verified=[], methods_discarded=[])
    try:
        verified["detail_locator"] = detail_for(task, verified, target, conversion)
    except (ValueError, TypeError, AttributeError, KeyError) as error:
        verified["detail_discarded"] = {"value": task.get("detail_lines"), "reason": str(error)}
    if verified["detail_locator"]:
        verified.update(locator=verified["detail_locator"], locator_basis="detail_lines")
    methods = task.get("methods", [])
    if not isinstance(methods, list):
        verified["methods_discarded"].append({"value": methods, "reason": "methods 배열 필요"})
        methods = []
    for method in methods:
        try:
            entry = verify_method(method, verified, target, conversion)
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            verified["methods_discarded"].append({"value": method, "reason": str(error)})
        else:
            if entry not in verified["methods_verified"]:
                verified["methods_verified"].append(entry)
    return verified


def deduplicate_verified(tasks, conversions):
    result = ai.deduplicate(tasks)
    for task in result:
        keys = ("document_id", "child_id", "grade", "semester", "title")
        members = [t for t in tasks if all(t.get(k) == task.get(k) for k in keys)
                   and set(t["target_ids"]) <= set(task["target_ids"])
                   and all(e in task["evidence"] for e in t["evidence"])]
        for key in ("methods_verified", "methods_discarded"):
            task[key] = []
            for member in members:
                for entry in member[key]:
                    if entry not in task[key]:
                        task[key].append(entry)
        details = [m["detail_locator"] for m in members if m.get("detail_locator")]
        task["detail_locators"] = [d for i, d in enumerate(details) if d not in details[:i]]
        if details:
            conversion = conversions[task["converted_path"]]
            task["detail_locator"] = {**text_locator(min(d["start"] for d in details),
                                                    max(d["end"] for d in details), conversion),
                                      "text_field": "text"}
            task.update(locator=task["detail_locator"], locator_basis="detail_lines")
    return result


def detail_contains_other_title(task, tasks):
    detail = task["detail_locator"]
    keys = ("document_id", "child_id", "grade", "semester")
    return any(all(task.get(k) == peer.get(k) for k in keys)
               and ai.title_key(task["title"]) != ai.title_key(peer["title"])
               and detail["start"] <= peer["title_locator"]["start"]
               and peer["title_locator"]["end"] <= detail["end"] for peer in tasks)


def discard_detail(task, conversion):
    task["detail_discarded"] = {"value": task["detail_locator"],
                                "reason": "세부표 범위에 다른 과제 제목"}
    task.update(detail_locator=None, detail_locators=[])
    task["locator"], task["locator_basis"] = ai.title_evidence_locator(
        task, task["evidence"], conversion)
    methods, task["methods_verified"] = task["methods_verified"], []
    for method in methods:
        if any(e["line_start"] <= method["line"] <= e["line_end"] for e in task["evidence"]):
            task["methods_verified"].append(method)
        else:
            task["methods_discarded"].append({"value": method,
                                              "reason": "방법이 과제 근거·세부표 범위 밖임"})


def finalize_details(tasks, conversions):
    """Check merged ranges against all kept titles before reading literal codes."""
    for task in tasks:
        task["standards_from_detail"] = {"value": [], "occurrences": []}
        detail = task.get("detail_locator")
        if not detail:
            continue
        conversion = conversions[task["converted_path"]]
        if detail_contains_other_title(task, tasks):
            discard_detail(task, conversion)
            continue
        standards = standard_values([{"raw": conversion["text"][detail["start"]:detail["end"]],
                                      "locator": detail}])
        task["standards_from_detail"] = {key: standards[key] for key in ("value", "occurrences")}
    return tasks


def verify_response(target, output, conversion, kept, discarded, outside, uncertain):
    response = ai.parse_response(output / f"responses/{target['target_id']}.json")
    lines = conversion["text"].splitlines()
    uncertain.extend({"target_id": target["target_id"], "value": u} for u in response["uncertain"])
    for task in response["tasks"]:
        try:
            verified = ai.verify_task(task, target, conversion)
            verified = verify_extras(task, verified, target, conversion)
        except (ValueError, TypeError, AttributeError, KeyError) as error:
            discarded.append({"target_id": target["target_id"], "task": task, "reason": str(error)})
            continue
        if verified["grade"] in {1, 2}:
            first_line = min(e["line_start"] for e in verified["evidence"])
            course = course_name_before(lines, first_line)
            if course and is_non_science_course(course["course"]):
                discarded.append({"target_id": target["target_id"], "task": task,
                                  "reason": "other_subject_course:" + course["course"],
                                  "course_evidence": course})
                continue
            kept.append(verified)
        else:
            outside.append({**verified, "reason": "범위 밖"})


def verify_targets(root, round_key):
    output = ai.round_dir(root, round_key) / "first"
    kept, discarded, outside, uncertain, cache, bindings = [], [], [], [], {}, {}
    for target in ai.load_targets(output):
        valid, audit = ai.valid_run(output, target)
        if not valid:
            discarded.append({"target_id": target["target_id"], "reason": "실행 감사·무결성 실패",
                              "audit": audit})
            continue
        status = ai.read_json(output / f"responses/{target['target_id']}.status.json")
        bindings[target["target_id"]] = {k: status[k] for k in
                                       ("prompt_sha256", "answer_sha256", "events_sha256", "fake")}
        path = target["converted_path"]
        if path not in cache:
            cache[path] = ai.conversion_for(root, target)
        if ai.sha(cache[path]["text"]) != target["text_sha256"]:
            raise ValueError("조각 간 원문 해시 충돌")
        verify_response(target, output, cache[path], kept, discarded, outside, uncertain)
    report = {"schema_version": 1, "rule_version": VERSION, "round": round_key,
              "kept": finalize_details(deduplicate_verified(kept, cache), cache),
              "discarded": discarded,
              "out_of_scope": deduplicate_verified(outside, cache), "uncertain": uncertain,
              "targets_sha256": ai.sha(ai.read_text(output / "targets.jsonl")),
              "run_bindings": bindings, "simulated": any(b["fake"] for b in bindings.values())}
    report["summary"] = {k: len(report[k]) for k in
                         ("kept", "discarded", "out_of_scope", "uncertain")}
    ai.save_json(output / "verified.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("targets", "run", "verify", "merge", "methods"):
        command = commands.add_parser(name)
        command.add_argument("--round-key", required=True)
        if name == "run":
            command.add_argument("--isolated-cwd", type=Path, required=True)
            command.add_argument("--workers", type=int, default=6)
            command.add_argument("--model")
            command.add_argument("--fake-responses", type=Path)
            command.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "run":
        report = run_targets(ROOT, args.round_key, args.isolated_cwd, workers=args.workers,
                             model=args.model, fake_responses=args.fake_responses,
                             dry_run=args.dry_run)
    else:
        handlers = {"targets": build_targets, "verify": verify_targets,
                    "merge": merge_targets, "methods": fill_methods}
        report = handlers[args.command](ROOT, args.round_key)
    print(json.dumps(report.get("summary", report.get("ai_read_summary", report)),
                     ensure_ascii=False))
    if args.command == "run" and report["all_failed"]:
        raise SystemExit(3)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
