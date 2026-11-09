"use client";

import { useEffect, useState } from "react";
import Link from "./SiteLink";
import { fetchCatalog, type ScienceReferenceResponse } from "./lib/catalog-api";

const workflow = [
  {
    number: "01",
    title: "단원과 활동으로 찾습니다",
    description: "중학교 과학 단원과 실험·탐구·보고서 등 활동을 고르고 학년별 수행평가 항목을 찾습니다.",
    href: "/references",
    action: "단원×활동 찾기",
  },
  {
    number: "02",
    title: "근거 사례를 비교합니다",
    description: "원문에서 성취기준, 실험 조건, 학생 산출물과 채점기준을 확인해 우리 과학 수업의 설계 요소를 비교합니다.",
    href: "/cases",
    action: "사례 보기",
  },
];

export default function Home() {
  const [metrics, setMetrics] = useState<Array<{ value: number; label: string }>>([]);

  useEffect(() => {
    const controller = new AbortController();
    fetchCatalog<ScienceReferenceResponse>("references?limit=1", controller.signal)
      .then((payload) => {
        if (controller.signal.aborted || payload.profile !== "science") return;
        setMetrics([
          { value: payload.total_items, label: "전체 수행평가 항목" },
          { value: payload.total_cases, label: "전체 사례" },
        ].filter(({ value }) => Number.isSafeInteger(value) && value >= 0));
      })
      .catch(() => { /* Keep metrics hidden when the API is unavailable. */ });
    return () => controller.abort();
  }, []);

  return (
    <main id="main-content">
      <section className="hero" aria-labelledby="hero-title">
        <div className="heroCopy">
          <p className="eyebrow">2026학년도 교수·학습 및 평가계획 기반</p>
          <h1 id="hero-title">중학교 과학 단원과 활동에서<br />수업 아이디어를 찾습니다</h1>
          <p className="heroDescription">
            단원×활동으로 수행평가를 찾고 학년, 지역과 성취기준으로 범위를 좁힙니다.
            실험·탐구 과정과 보고서, 채점기준을 원문 근거와 함께 비교해 우리 수업에 맞게 설계합니다.
          </p>
          <div className="heroActions">
            <Link className="primaryAction" href="/references">단원×활동으로 찾아보기</Link>
            <Link className="secondaryAction" href="/cases">전체 과학 사례 보기</Link>
          </div>
          <p className="pilotNote"><span aria-hidden="true">●</span> 2022 개정 중학교 과학 수행평가를 단원과 활동으로 탐색합니다.</p>
        </div>

        {metrics.length > 0 && <aside className="evidencePanel" aria-label="현재 데이터 집계">
          <div className="panelTopline">
            <span>과학판 자료 집계</span>
          </div>
          <dl className="metricList">
            {metrics.map((metric) => (
              <div key={metric.label}>
                <dt>{metric.label}</dt>
                <dd>{metric.value.toLocaleString("ko-KR")}</dd>
              </div>
            ))}
          </dl>
          <p>현재 API에서 조회되는 전체 과학 수행평가 항목과 사례 기준입니다.</p>
        </aside>}
      </section>

      <section className="workflowSection" aria-labelledby="workflow-title">
        <div className="sectionHeading">
          <div>
            <p className="eyebrow">교사의 설계 흐름</p>
            <h2 id="workflow-title">찾고, 비교합니다</h2>
          </div>
          <p>자동으로 정답을 고르는 대신 근거와 판단 기준을 함께 보여 줍니다.</p>
        </div>
        <ol className="workflowGrid">
          {workflow.map((item) => (
            <li key={item.number}>
              <span className="stepNumber">{item.number}</span>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
              <Link href={item.href}>{item.action}<span aria-hidden="true"> →</span></Link>
            </li>
          ))}
        </ol>
      </section>

      <section className="boundaryBanner" aria-label="자료 해석 원칙">
        <div>
          <strong>미검출은 미개설이 아닙니다.</strong>
          <p>평가계획에서 과목이 발견되지 않은 경우와 추출 실패, 교육과정 판별 유보를 구분합니다.</p>
        </div>
        <span>교사 검토 원칙</span>
      </section>
    </main>
  );
}
