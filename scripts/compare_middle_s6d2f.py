"""Offline precision replay of all five development reviews; no new sample."""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections import Counter

import compare_middle_s6d2e as previous
from audit_middle_items import audit, markdown
from compare_middle_s6d2e import ROOT, prior, representative_items, save, write
from compare_middle_s6d3b import field_audit
from middle_items import POLICY_RE, UNIT_NUMBER_RE, method_literal, unit_list
from middle_rounds import roster_path
from recheck_middle_s6d2b import normalize
from verify_middle_s6d2f import VIOLATIONS, guard

PREFIX = "2026-11-09-s6d2f"
REVIEW_PREFIXES = (*previous.REVIEW_PREFIXES, "2026-11-09-s6d2e")


def suspects(reports):
    rows = []
    counts = Counter()
    population = 0
    independent_population = 0
    for round_key in prior.ROUNDS[1:]:
        report = reports[round_key]
        bounded = [i for i in report["items"] if i["extraction_status"] == "bounded"]
        independent = [i for i in prior.independent(report) if i["extraction_status"] == "bounded"]
        population += len(bounded)
        independent_population += len(independent)
        selected = {d["converted_path"] for d in report["documents"] if d["development_selected"]}
        # A proven summary/detail alias is one identity when looking for
        # duplicate task titles, while every bounded source row is scanned.
        duplicates = Counter((i["school"], i["grade"], i["semester"],
                              normalize(i["fields"]["title"]["value"])) for i in independent)
        for item in bounded:
            f = item["fields"]
            title = f["title"]["value"]
            reasons = []
            if method_literal(title) or re.search(r"평가방법|관찰평가|포트폴리오|논술형", title):
                reasons.append("방법 어휘")
            if POLICY_RE.search(title) or re.search(r"점수.*처리|특수교육|미제출", title):
                reasons.append("규정 어휘")
            if UNIT_NUMBER_RE.match(title) or unit_list(title) or re.search(
                r"단원|물질의|지권|생물의|열$|전기와|별과|에너지|빛과", title,
            ):
                reasons.append("단원 어휘")
            if all(f[k]["value"] in ("", [], None) for k in ("score", "weight", "standards")):
                reasons.append("만점·비율·성취기준 모두 빈칸")
            if duplicates[item["school"], item["grade"], item["semester"], normalize(title)] > 1:
                reasons.append("같은 칸 제목 중복")
            if reasons:
                counts.update(reasons)
                rows.append({"round": round_key, **prior.coordinate(item),
                             "representative": item["converted_path"] in selected,
                             "proven_summary_alias": bool(item.get("identity_relation")
                                                          and item["candidate_role"]
                                                          == "summary_duplicate"),
                             "reasons": reasons, "fields": {k: f[k]["value"]
                                                               for k in ("score", "weight",
                                                                         "standards")}})
    return {"population": population, "independent_population": independent_population,
            "summary_alias_population": population - independent_population,
            "suspect_count": len(rows),
            "reason_counts": {key: counts[key] for key in (
                "방법 어휘", "규정 어휘", "단원 어휘", "만점·비율·성취기준 모두 빈칸",
                "같은 칸 제목 중복")},
            "items": rows}


def suspect_markdown(result):
    lines = ["# S6d-2f 보충 bounded 전체 오검출 의심 목록", "",
             f"보충 두 회차 bounded {result['population']}개 전수 중 "
             f"{result['suspect_count']}개. 대표 판본 여부와 원문 위치를 JSON에 보존했다.", "",
             f"독립 항목 {result['independent_population']}개와 동일성이 입증된 요약 별칭 "
             f"{result['summary_alias_population']}개를 모두 검색했다. 제목 중복 판정에서는 "
             "입증된 요약·상세 쌍을 한 항목으로 세며, 어휘 검색에 걸린 별칭은 아래에 표시한다.", "",
             "의심 어휘는 검토용 검색 조건이다. 실제 영역명이 단원명·방법명인 경우도 포함하며, "
             "이 목록만으로 잘못이라고 확정하지 않는다. 새 독립 표본을 만들지 않았다.", "",
             "사유별(중복 집계): " + json.dumps(result["reason_counts"], ensure_ascii=False), "",
             "| 회차·학교·칸 | 제목 | 사유 | 만점 / 비율 / 코드 | 항목·원문 위치 |",
             "|---|---|---|---|---|"]
    for row in result["items"]:
        f = row["fields"]
        lines.append(f"| {row['round']} {row['school']} 중{row['grade']} "
                     f"{row['semester']}학기 | {row['title']}"
                     f"{'〔확인된 요약 별칭〕' if row['proven_summary_alias'] else ''} | "
                     f"{' / '.join(row['reasons'])} | "
                     f"{f['score']} / {f['weight']} / {', '.join(f['standards'])} | "
                     f"`{row['item_id']}` · `{row['converted_path']}` "
                     f"{row['locator']['start']}–{row['locator']['end']} |")
    return "\n".join(lines) + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.addaudithook(guard)
    reports = {"before": {}, "after": {}}
    result = {"rounds": {}}
    lines = ["# S6d-2f 전후 비교", "", "| 회차 | bounded 전→후 | 검토 전→후 |",
             "|---|---:|---:|"]
    for r in prior.ROUNDS:
        for ext in ("json", "md"):
            current = ROOT / f"data/derived/items/{r}.{ext}"
            snapshot = current.with_name(f"{r}.prev-s6d2e.{ext}")
            if not snapshot.exists():
                shutil.copyfile(current, snapshot)
        before = prior.read(f"data/derived/items/{r}.prev-s6d2e.json")
        after = audit(ROOT / f"data/derived/subjects/{r}.json", roster_path(ROOT, r, None))
        save(ROOT / f"data/derived/items/{r}.json", after)
        write(ROOT / f"data/derived/items/{r}.md", markdown(after))
        reports["before"][r], reports["after"][r] = before, after
        row = {"before": prior.metrics(before), "after": prior.metrics(after),
               "audit": prior.safety_counts(after) | prior.column_audit(after) | field_audit(after),
               "split_merges": previous.split_merges(before, after)}
        result["rounds"][r] = row
        lines.append(f"| {r} | {row['before']['bounded']}→{row['after']['bounded']} | "
                     f"{row['before']['review']}→{row['after']['review']} |")
        print(r, row["before"]["bounded"], row["after"]["bounded"], row["audit"], flush=True)
    previous.PREFIX, previous.REVIEW_PREFIXES = PREFIX, REVIEW_PREFIXES
    selected = {id(report): representative_items(report)
                for phase in reports.values() for report in phase.values()}
    previous.representative_items = lambda report: selected[id(report)]
    recheck = previous.recheck(reports)
    # The inherited comparison is a development recheck only; never call sample().
    md_path = ROOT / f"docs/dev/{PREFIX}-recheck.md"
    write(md_path, md_path.read_text(encoding="utf-8").replace("S6d-2e", "S6d-2f")
          .replace("64칸", "80칸").replace("판독 불가 세 칸", "판독 불가 네 칸"))
    result.update(development_totals=recheck["totals"], access_violations=VIOLATIONS)
    save(ROOT / f"docs/dev/{PREFIX}-comparison.json", result)
    write(ROOT / f"docs/dev/{PREFIX}-comparison.md", "\n".join(lines) + "\n")
    suspicious = suspects(reports["after"])
    save(ROOT / f"docs/dev/{PREFIX}-suspects.json", suspicious)
    write(ROOT / f"docs/dev/{PREFIX}-suspects.md", suspect_markdown(suspicious))
    print(json.dumps(recheck["totals"], ensure_ascii=False))
    if VIOLATIONS or any(v for row in result["rounds"].values() for v in row["audit"].values()):
        raise SystemExit("S6d-2f audit violations")


if __name__ == "__main__":
    main()
