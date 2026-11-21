import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ReviewWorkspace from "../app/review/ReviewWorkspace";
import { REVIEW_STORAGE_KEY } from "../app/review/review-store";

const caseId = "0123456789abcdef01234567";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(`case=${caseId}`),
}));

const caseItem = {
  case_id: caseId,
  curriculum: "2022",
  subject: "과학",
  curriculum_ambiguous: false,
  curriculum_basis: "explicit",
  school_name: "예시중",
  region: "서울",
  academic_years: [2026],
  grades: [1],
  semesters: [1],
  primary_task_name: "열의 이동 실험 보고서",
  task_names: ["열의 이동 실험 보고서"],
  action_tags: ["과학적 모델링"],
  evidence_markers: { rubric: 1, achievement_standard: 1, weight_or_points: 1, assessment_method: 1 },
  evidence_score: 40,
  evidence_excerpt: "열의 이동 실험에서 온도 변화를 기록하고 자료를 해석한다.",
  source_name: "2026학년도 평가계획",
  source_url: "https://www.schoolinfo.go.kr/example",
  source_sha256: "a".repeat(64),
};

describe("교사 검토함", () => {
  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  it("요청한 사례를 담고 여섯 검토 기준을 보여 준다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => caseItem }));
    render(<ReviewWorkspace />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "열의 이동 실험 보고서" })).not.toBeNull());
    expect(screen.getAllByRole("combobox")).toHaveLength(6);
    expect(screen.getByText("과제 명료성")).not.toBeNull();
    expect(screen.getByText("공정성")).not.toBeNull();
    expect(screen.getByRole("button", { name: "교사 검토 저장" })).not.toBeNull();
  });

  it("불러올 수 없는 사례가 있어도 검토함을 열고 그 사례를 뺄 수 있게 한다", async () => {
    const goneId = "fedcba9876543210fedcba98";
    window.localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify({ version: 1, queue: [goneId], decisions: {} }));
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string) => (
      url.endsWith(goneId)
        ? { ok: false, status: 404, json: async () => ({ detail: "사례를 찾을 수 없습니다." }) }
        : { ok: true, json: async () => caseItem }
    )));
    render(<ReviewWorkspace />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "열의 이동 실험 보고서" })).not.toBeNull());
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText("불러올 수 없는 사례")).not.toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /불러올 수 없는 사례/ }));
    expect(screen.getByText("이 사례는 더 이상 공개되지 않거나 지금 불러올 수 없습니다. 적어 둔 검토 기록은 이 브라우저에 남아 있습니다.")).not.toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "검토함에서 빼기" }));

    await waitFor(() => expect(screen.queryByText("불러올 수 없는 사례")).toBeNull());
    const stored = JSON.parse(window.localStorage.getItem(REVIEW_STORAGE_KEY) ?? "{}");
    expect(stored.queue).toEqual([caseId]);
    await waitFor(() => expect(screen.getByRole("heading", { name: "열의 이동 실험 보고서" })).not.toBeNull());
  });
});
