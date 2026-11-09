// Matching assessment item and source evidence. Verify: npm run test:web.
import Link from "../SiteLink";
import type { AxisValue, Locator, ScienceReferenceItem } from "../lib/catalog-api";

const EVIDENCE_LENGTH = 80;
const SECONDARY_LIMIT = 2;
const BASIS_LABELS: Record<string, string> = {
  standard_code: "성취기준", area_name: "평가영역 칸:", checkbox: "평가방법 칸:",
  method_text: "평가방법 칸:", assessment_area: "평가영역 칸:",
  rubric_e: "평가요소·채점기준:", rubric_s: "평가요소·채점기준:", title_verb: "제목:",
};

function evidenceLocation(locator: Locator) {
  if (locator.fallback) return "항목 범위";
  return [locator.table !== undefined ? `표 ${locator.table + 1}` : "", locator.row != null ? `${locator.row + 1}행` : ""].filter(Boolean).join(" · ");
}

function evidenceText(value: AxisValue) {
  const evidence = Array.from(value.evidence);
  const preview = evidence.slice(0, EVIDENCE_LENGTH).join("") + (evidence.length > EVIDENCE_LENGTH ? "…" : "");
  const location = evidenceLocation(value.locator);
  return `${BASIS_LABELS[value.basis] ?? "근거:"} ${preview}${location ? ` · ${location}` : ""}`;
}

export default function ReferenceCard({ item }: { item: ScienceReferenceItem }) {
  const primary = item.activity.primary;
  const secondary = item.activity.secondary.slice(0, SECONDARY_LIMIT);
  const evidence = [...(primary ? [primary] : []), ...item.units];
  return <article className="caseCard scienceReferenceCard">
    <h3>{item.title}</h3>
    <p>{[item.school_name, item.grade ? `${item.grade}학년` : "학년 미확정", item.semester ? `${item.semester}학기` : "학기 미확정", [item.region, item.district].filter(Boolean).join(" ")].filter(Boolean).join(" · ")}</p>
    <div className="signalChips" aria-label="단원">{item.units.map((unit) => <span key={unit.value}>{unit.value} {unit.label}</span>)}</div>
    <p>{primary ? `주: ${primary.label}${secondary.length ? ` · 보조: ${secondary.map((value) => value.label).join(", ")}` : ""}` : "활동 미분류(근거 부족)"} <small className="basisLabel">자동 분류(참고)</small></p>
    {evidence.length ? <p className="referenceEvidence">{evidence.map(evidenceText).join(" / ")}</p> : <p className="referenceEvidence">근거 위치: {evidenceLocation(item.locator) || "위치 미확정"}</p>}
    <Link href={`/cases/${item.case_id}?item=${item.item_id}`}>원문 표 보기 →</Link>
  </article>;
}
