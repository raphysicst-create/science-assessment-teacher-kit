"use client";

// Science unit/activity search with URL filters and pagination. Verify: npm run test:web && npm run lint:web.
import Link from "../SiteLink";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiParameters, fetchCatalog, type ScienceReferenceResponse } from "../lib/catalog-api";
import ReferenceCard from "./ReferenceCard";
import { readReferenceFilters, type ReferenceFilters } from "./reference-filters";
import { SCIENCE_STANDARD_TEXT, UNIT_GRADE_GROUPS, unitGrade } from "../lib/science-standards";

const PAGE_SIZE = 30;
const EMPTY_FILTERS: ReferenceFilters = { unit: "", standard: "", activity: "", grade: "", region: "", district: "" };

export default function ReferenceExplorer() {
  const parameters = useSearchParams();
  const router = useRouter();
  const [filters, setFilters] = useState(() => readReferenceFilters(parameters));
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<ScienceReferenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchCatalog<ScienceReferenceResponse>(`references?${apiParameters({ ...filters, limit: PAGE_SIZE, offset })}`, controller.signal)
      .then((payload) => {
        if (controller.signal.aborted) return;
        setData((previous) => ({ ...payload, items: offset ? [...(previous?.items ?? []), ...payload.items] : payload.items }));
      })
      .catch((reason: Error) => { if (!controller.signal.aborted) setError(reason.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, offset, retry]);

  useEffect(() => {
    const query = apiParameters(filters);
    router.replace(query ? `/references?${query}` : "/references", { scroll: false });
  }, [filters, router]);

  function changeFilters(values: Partial<ReferenceFilters>) {
    setLoading(true);
    setError("");
    setOffset(0);
    setFilters((previous) => ({ ...previous, ...values }));
  }

  function clearFilters() { changeFilters(EMPTY_FILTERS); }
  // A unit from another grade's group would show only stray cards, so drop it.
  function changeGrade(grade: string) {
    const keepUnit = !grade || !filters.unit || unitGrade(filters.unit) === grade;
    changeFilters(keepUnit ? { grade } : { grade, unit: "", standard: "" });
  }

  const units = data?.axes.units ?? [];
  const unitGroups = UNIT_GRADE_GROUPS
    .map((group) => ({ ...group, units: units.filter((item) => unitGrade(item.value) === group.grade) }))
    .sort((left, right) => Number(right.grade === filters.grade) - Number(left.grade === filters.grade));
  const unitStandards = (data?.axes.standards ?? []).filter((item) => item.value.slice(3, 5) === filters.unit);
  function loadMore() { setLoading(true); setError(""); setOffset(data?.items.length ?? 0); }

  return <main id="main-content" className="catalogPage referencePage scienceReferences">
    <header className="pageHeaderCompact">
      <div><p className="breadcrumb"><Link href="/">홈</Link><span>/</span>단원·활동별 사례</p><h1>단원·활동으로 찾는 과학 수행평가</h1>
        <p>단원을 고르고 활동을 고르면, 그 조합의 실제 사례가 나옵니다.</p>
        <p className="referenceSource">단원: 2022 개정 중학교 과학 교육과정 영역 · 활동: 명칭은 생명과학판에서 차용, 판정 정의는 별도 작성</p></div>
      <p aria-label="검색 결과 수">항목 {(data?.total_items ?? 0).toLocaleString()} · 사례 {(data?.total_cases ?? 0).toLocaleString()}</p>
    </header>

    <section className="caseFilterPanel referenceFilterPanel" aria-label="과학 수행평가 필터">
      <div className="caseFilterTopline"><div><span className="stepPill">필터</span><h2>지역 좁히기</h2></div><button type="button" onClick={clearFilters}>조건 해제</button></div>
      <div className="filterControls">
        <label><span>시·도</span><select value={filters.region} onChange={(event) => changeFilters({ region: event.target.value, district: "" })}><option value="">전국</option>{data?.facets.regions.map((item) => <option key={item.value} value={item.value}>{item.value} · {item.count}</option>)}</select></label>
        <label><span>시·군·구</span><select value={filters.district} disabled={!filters.region} onChange={(event) => changeFilters({ district: event.target.value })}><option value="">{filters.region ? "전체 시·군·구" : "시·도를 먼저 선택"}</option>{filters.region ? data?.facets.districts.map((item) => <option key={item.value} value={item.value}>{item.value} · {item.count}</option>) : null}</select></label>
      </div>
    </section>

    <section className="curatedSection" aria-labelledby="reference-units">
      <h2 id="reference-units">학년·단원 선택</h2>
      <div className="filterControls referenceUnitSelects">
        <label><span>학년</span><select value={filters.grade} onChange={(event) => changeGrade(event.target.value)}><option value="">전체 학년</option><option value="1">1학년</option><option value="2">2학년</option></select></label>
        <label><span>단원</span><select value={filters.unit} onChange={(event) => changeFilters({ unit: event.target.value, standard: "" })}>
          <option value="">전체 단원</option>
          {unitGroups.map((group) => <optgroup key={group.grade} label={group.label}>
            {group.units.map((item) => <option key={item.value} value={item.value}>{item.value} {item.label} · {item.item_count.toLocaleString()}</option>)}
          </optgroup>)}
        </select></label>
        <label><span>성취기준</span><select value={filters.standard} disabled={!filters.unit} onChange={(event) => changeFilters({ standard: event.target.value })}>
          <option value="">{filters.unit ? "단원 전체 성취기준" : "단원을 먼저 선택"}</option>
          {unitStandards.map((item) => <option key={item.value} value={item.value}>{item.value} {SCIENCE_STANDARD_TEXT[item.value] ?? ""} · {item.item_count.toLocaleString()}</option>)}
        </select></label>
      </div>
      {filters.standard ? <p className="referenceStandardText"><strong>{filters.standard}</strong> {SCIENCE_STANDARD_TEXT[filters.standard] ?? ""}</p> : null}
    </section>

    <section className="curatedSection referenceCuratedSection" aria-labelledby="reference-activities">
      <h2 id="reference-activities">활동 선택</h2>
      <p className="referenceClassification"><span className="basisLabel">자동 분류(참고)</span> {data?.classification_notice}</p>
      <div className="categoryTabs" role="tablist" aria-label="과학 활동">
        <button type="button" role="tab" aria-selected={!filters.activity} className={!filters.activity ? "selected" : ""} onClick={() => changeFilters({ activity: "" })}>전체 · {(data?.total_items ?? 0).toLocaleString()}</button>
        {data?.axes.activities.filter((item) => item.tab).map((item) => <button type="button" role="tab" aria-selected={filters.activity === item.value} className={filters.activity === item.value ? "selected" : ""} key={item.value} onClick={() => changeFilters({ activity: item.value })}>{item.label} · {item.item_count.toLocaleString()}</button>)}
      </div>
      {loading ? <div className="compactLoading" role="status">사례를 불러오고 있습니다.</div> : null}
      {error ? <div className="errorPanel" role="alert"><strong>자료를 불러오지 못했습니다.</strong><p>{error}</p><button type="button" onClick={() => { setLoading(true); setError(""); setRetry((value) => value + 1); }}>다시 시도</button></div> : null}
      {data && (!loading || offset > 0) && (!error || offset > 0) ? <div className="scienceReferenceCards">{data.items.map((item) => <ReferenceCard key={item.item_id} item={item} />)}</div> : null}
      {!loading && !error && data?.total_items === 0 ? <div className="compactEmpty"><p>이 조합의 사례는 0건입니다.</p><button type="button" onClick={clearFilters}>조건 해제</button></div> : null}
      {!error && data && data.total_items > data.items.length ? <div className="pagination"><button type="button" disabled={loading} onClick={loadMore}>더 보기</button></div> : null}
      {data?.interpretation ? <p className="rankingBoundary">{data.interpretation}</p> : null}
    </section>
  </main>;
}
