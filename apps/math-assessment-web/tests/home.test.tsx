import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Home from "../app/page";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ profile: "science", total_items: 1234, total_cases: 56 }),
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("과학 아카이브 시작 화면", () => {
  it("API에서 받은 전체 항목과 사례 집계를 보여 준다", async () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: /중학교 과학 단원과 활동에서/ })).not.toBeNull();
    expect(await screen.findByText("1,234")).not.toBeNull();
    expect(screen.getByText("56")).not.toBeNull();
    expect(screen.getByText("미검출은 미개설이 아닙니다.")).not.toBeNull();
    expect(fetch).toHaveBeenCalledWith("/api/v1/references?limit=1", expect.any(Object));
  });

  it("단원×활동 찾기와 사례 비교로 이동할 수 있다", () => {
    render(<Home />);

    expect(screen.getByRole("link", { name: "단원×활동 찾기" }).getAttribute("href")).toBe("/references");
    expect(screen.getByRole("link", { name: "사례 보기" }).getAttribute("href")).toBe("/cases");
    expect(screen.getByRole("link", { name: "단원×활동으로 찾아보기" }).getAttribute("href")).toBe("/references");
  });

  it.each([
    {},
    { profile: "science" },
    { profile: "science", total_items: null, total_cases: -1 },
    { profile: "other", total_items: 1234, total_cases: 56 },
  ])("집계가 없거나 유효하지 않으면 숫자 영역을 숨긴다 %j", async (payload) => {
    const json = vi.fn().mockResolvedValue(payload);
    vi.mocked(fetch).mockResolvedValue({ ok: true, json } as unknown as Response);
    render(<Home />);

    await waitFor(() => expect(json).toHaveBeenCalled());
    expect(screen.queryByRole("complementary", { name: "현재 데이터 집계" })).toBeNull();
  });

  it("API 호출이 실패하면 숫자 영역을 숨긴다", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("offline"));
    render(<Home />);

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(screen.queryByRole("complementary", { name: "현재 데이터 집계" })).toBeNull();
  });

  it("응답을 기다리는 동안 숫자 영역을 숨긴다", () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {}));
    render(<Home />);
    expect(screen.queryByRole("complementary", { name: "현재 데이터 집계" })).toBeNull();
  });

  it("API의 0을 표시하고 누락된 집계만 숨긴다", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ profile: "science", total_items: 0 }),
    } as Response);
    render(<Home />);

    expect(await screen.findByText("0")).not.toBeNull();
    expect(screen.getByText("전체 수행평가 항목")).not.toBeNull();
    expect(screen.queryByText("전체 사례")).toBeNull();
  });
});
