// Science reference search contract and user interactions. Verify: npm run test:web.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ReferenceExplorer from "../app/references/ReferenceExplorer";
import ReferenceCard from "../app/references/ReferenceCard";
import CasesExplorer from "../app/cases/CasesExplorer";
import type { AxisValue, ScienceReferenceItem, ScienceReferenceResponse } from "../app/lib/catalog-api";
import { readReferenceFilters } from "../app/references/reference-filters";

const navigation = vi.hoisted(() => ({ replace: vi.fn(), query: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => navigation,
  useSearchParams: () => new URLSearchParams(navigation.query),
}));

const ACTIVITY_IDS = ["inquiry", "experiment", "writing", "making", "analysis", "explanation", "presentation", "measurement", "process", "problem_solving"];

function axis(value: string, label: string, basis = "checkbox", evidence = "☑실험·실습"): AxisValue {
  return { value, label, basis, evidence, locator: { table: 2, row: 1 } };
}

function referenceItem(item_id = "item-1"): ScienceReferenceItem {
  return {
    item_id, case_id: "case-1", order: 1, title: `열 이동 실험 ${item_id}`, title_raw: "열 이동 실험", title_basis: "table",
    extraction_status: "bounded", overview: "", method: "", timing: "", score: "", weight: "",
    standards: ["[9과03-01]"], has_rubric: true, source_available: true,
    curriculum: "2022", subject: "과학", school_name: "예시중학교", region: "서울", district: "강남구",
    category: "experiment", priority_score: 0, priority_signals: [], grade: 1, semester: 2,
    units: [axis("03", "열", "standard_code", "[9과03-01]")],
    activity: {
      primary: axis("experiment", "실험평가"),
      secondary: [axis("measurement", "계산·측정"), axis("analysis", "자료 분석"), axis("writing", "세 번째 보조")],
      abstain_reason: null, notice: "자동 분류(참고)",
    },
    locator: { table: 2, row: 1 },
  };
}

function response(overrides: Partial<ScienceReferenceResponse> = {}): ScienceReferenceResponse {
  return {
    profile: "science", activity_policy: "all_reference", classification_notice: "자동 분류 결과는 원문과 함께 확인하세요.",
    filters: { unit: null, standard: null, activity: null, grade: null, region: null, district: null },
    total: 7, total_items: 7, total_cases: 3, limit: 30, offset: 0, category: "",
    items: [referenceItem()],
    axes: {
      units: Array.from({ length: 23 }, (_, index) => ({ value: String(index + 1).padStart(2, "0"), label: index === 2 ? "열" : `단원 ${index + 1}`, item_count: index === 0 ? 0 : 2, case_count: 1 })),
      activities: ACTIVITY_IDS.map((value, index) => ({ value, label: index === 1 ? "실험평가" : `활동 ${index}`, item_count: 2, case_count: 1, tab: true })),
      grades: [{ value: 1, item_count: 7, case_count: 3 }],
      standards: [{ value: "[9과03-01]", item_count: 0, case_count: 0 }],
    },
    facets: { regions: [{ value: "서울", count: 3 }], districts: [{ value: "강남구", count: 3 }], action_tags: [] },
    subjects: [], interpretation: "조건에 맞은 항목입니다.", ...overrides,
  };
}

let payload: ScienceReferenceResponse;
let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  payload = response();
  navigation.query = "";
  navigation.replace.mockClear();
  fetchMock = vi.fn(async () => ({ ok: true, json: async () => payload }));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("과학 수행평가 참고", () => {
  it("단원 23개와 활동 전체+10개, 항목·사례 수를 따로 표시한다", async () => {
    render(<ReferenceExplorer />);
    await screen.findByRole("article");
    const units = within(screen.getByRole("group", { name: "과학 단원" }));
    expect(units.getAllByRole("button")).toHaveLength(23);
    expect(units.getByRole("button", { name: "01 단원 1 · 0" })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getAllByRole("tab")).toHaveLength(11);
    expect(screen.getByRole("tab", { name: "전체 · 7" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getAllByText("자동 분류(참고)")).toHaveLength(2);
    expect(screen.getByLabelText("검색 결과 수")).toHaveTextContent("항목 7 · 사례 3");
    expect(screen.queryByRole("combobox", { name: "수학 과목" })).not.toBeInTheDocument();
  });

  it("정책에 따라 tab:false인 활동을 탭에서 뺀다", async () => {
    payload.activity_policy = "high_accuracy_only";
    payload.axes.activities[9].tab = false;
    render(<ReferenceExplorer />);
    await screen.findByRole("article");
    expect(screen.getAllByRole("tab")).toHaveLength(10);
    expect(screen.queryByRole("tab", { name: /활동 9/ })).not.toBeInTheDocument();
  });

  it("보조는 2개만 표시하고 주활동·단원 근거와 사람 번호 위치를 보인다", async () => {
    render(<ReferenceExplorer />);
    const card = within(await screen.findByRole("article"));
    expect(card.getByText(/주: 실험평가 · 보조: 계산·측정, 자료 분석/)).toBeInTheDocument();
    expect(card.queryByText(/세 번째 보조/)).not.toBeInTheDocument();
    expect(card.getByText(/평가방법 칸: ☑실험·실습 · 표 3 · 2행/)).toHaveTextContent("성취기준 [9과03-01] · 표 3 · 2행");
    expect(card.getByRole("link", { name: "원문 표 보기 →" })).toHaveAttribute("href", "/cases/case-1?item=item-1");
    expect(card.getByText(/예시중학교 · 1학년 · 2학기 · 서울 강남구/)).toBeInTheDocument();
  });

  it("기권과 항목 범위 위치를 표시하고 근거 문자열을 80자로 제한한다", () => {
    const item = referenceItem();
    item.activity.primary = null;
    item.activity.abstain_reason = "insufficient_evidence";
    item.units = [axis("03", "열", "area_name", "가".repeat(90))];
    item.units[0].locator = { fallback: "item" };
    render(<ReferenceCard item={item} />);
    expect(screen.getByText(/활동 미분류\(근거 부족\)/)).toBeInTheDocument();
    expect(screen.getByText(/평가영역 칸:/)).toHaveTextContent(`평가영역 칸: ${"가".repeat(80)}… · 항목 범위`);
    expect(screen.queryByText(/가{81}/)).not.toBeInTheDocument();
  });

  it("빈 조합을 0건으로 표시하고 조건을 해제한다", async () => {
    navigation.query = "unit=03&grade=1";
    payload = response({ total: 0, total_items: 0, total_cases: 0, items: [] });
    render(<ReferenceExplorer />);
    expect(await screen.findByText("이 조합의 사례는 0건입니다.")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "조건 해제" })[1]);
    await waitFor(() => expect(navigation.replace).toHaveBeenLastCalledWith("/references", { scroll: false }));
  });

  it("0건 단원도 선택·해제되고 단원 변경은 성취기준을 초기화한다", async () => {
    render(<ReferenceExplorer />);
    await screen.findByRole("article");
    fireEvent.click(screen.getByRole("button", { name: "01 단원 1 · 0" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "01 단원 1 · 0" })).toHaveAttribute("aria-pressed", "true"));
    fireEvent.click(screen.getByRole("button", { name: "03 열 · 2" }));
    fireEvent.click(await screen.findByRole("button", { name: "[9과03-01] · 0" }));
    await waitFor(() => expect(decodeURIComponent(navigation.replace.mock.lastCall![0])).toContain("standard=[9과03-01]"));
    fireEvent.click(screen.getByRole("button", { name: "03 열 · 2" }));
    await waitFor(() => expect(navigation.replace).toHaveBeenLastCalledWith("/references", { scroll: false }));
    expect(screen.queryByRole("group", { name: "성취기준" })).not.toBeInTheDocument();
  });

  it("모든 필터를 URL과 요청에 동기화하고 offset 페이지를 이어 붙인다", async () => {
    navigation.query = "unit=03&standard=%5B9과03-01%5D&activity=experiment&grade=2&region=서울&district=강남구";
    payload.total_items = 2;
    render(<ReferenceExplorer />);
    await screen.findByRole("article");
    const requested = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(Object.fromEntries(requested.searchParams)).toMatchObject({ unit: "03", standard: "[9과03-01]", activity: "experiment", grade: "2", region: "서울", district: "강남구", limit: "30", offset: "0" });
    payload = response({ total_items: 2, items: [referenceItem("item-2")], offset: 1 });
    fireEvent.click(screen.getByRole("button", { name: "더 보기" }));
    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(2));
    expect(fetchMock.mock.lastCall![0]).toContain("offset=1");
    expect(screen.queryByRole("button", { name: "더 보기" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "시·도" }), { target: { value: "" } });
    await waitFor(() => expect(fetchMock.mock.lastCall![0]).not.toContain("district="));
    expect(fetchMock.mock.lastCall![0]).toContain("offset=0");
  });

  it("잘못된 URL 값을 비우며 성취기준의 단원·번호 범위를 확인한다", async () => {
    navigation.query = "unit=24&standard=%5B9과03-99%5D&activity=bad&grade=3&region=bad&district=bad";
    render(<ReferenceExplorer />);
    await screen.findByRole("article");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/references?limit=30&offset=0");
    expect(readReferenceFilters(new URLSearchParams("unit=02&standard=[9과03-01]"))).toMatchObject({ unit: "02", standard: "" });
    expect(readReferenceFilters(new URLSearchParams("standard=[9과23-02]"))).toMatchObject({ standard: "[9과23-02]" });
  });

  it("더 보기 오류 후 재시도에서도 중복 없이 이어 붙인다", async () => {
    payload.total_items = 2;
    render(<ReferenceExplorer />);
    await screen.findByRole("article");
    fetchMock.mockRejectedValueOnce(new Error("연결 오류"));
    fireEvent.click(screen.getByRole("button", { name: "더 보기" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("연결 오류");
    payload = response({ total_items: 2, items: [referenceItem("item-2")], offset: 1 });
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    await waitFor(() => expect(screen.getAllByRole("article")).toHaveLength(2));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

it("전체 라이브러리에서 과목 대신 학년을 cases API와 URL로 보낸다", async () => {
  navigation.query = "grade=1";
  fetchMock.mockImplementation(async (url: string) => ({ ok: true, json: async () => url.includes("facets?") ? payload.facets : { items: [], total: 0, limit: 20, offset: 0, caution: "" } }));
  render(<CasesExplorer />);
  await screen.findByText("조건에 맞는 사례가 없습니다.");
  expect(screen.queryByRole("combobox", { name: "수학 과목" })).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole("combobox", { name: "학년" }), { target: { value: "2" } });
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url.startsWith("/api/v1/cases?") && url.includes("grade=2"))).toBe(true));
  expect(navigation.replace.mock.lastCall![0]).toContain("grade=2");
  expect(fetchMock.mock.calls.some(([url]) => url.includes("subject=") || url.endsWith("/subjects"))).toBe(false);
});
