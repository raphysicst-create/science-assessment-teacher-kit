import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import RootLayout from "../app/layout";
import { CONTACT_LABEL, CONTACT_URL, OPERATOR_NAME, OPERATOR_URL, ORIGINAL_WORK_NOTICE, SITE_NAME } from "../app/lib/site";

vi.mock("../app/VisitorCounter", () => ({ default: () => null }));

afterEach(cleanup);

describe("주요 메뉴", () => {
  it("교사가 어느 화면에서든 사용설명서로 이동할 수 있다", () => {
    const layout = RootLayout({
      children: <main id="main-content">현재 화면</main>,
    });
    const body = layout.props.children;
    render(<>{body.props.children}</>);

    expect(screen.getByRole("link", { name: "사용설명서" }).getAttribute("href")).toBe(
      "/guide",
    );
  });
  it("과학판 이름과 운영자·이슈 연락처·원저작 고지를 표시한다", () => {
    const layout = RootLayout({ children: <main id="main-content">현재 화면</main> });
    const body = layout.props.children;
    const { container } = render(<>{body.props.children}</>);

    expect(screen.getByRole("link", { name: `${SITE_NAME} 홈` })).not.toBeNull();
    expect(screen.getByRole("link", { name: `운영 ${OPERATOR_NAME}` }).getAttribute("href")).toBe(OPERATOR_URL);
    expect(screen.getByRole("link", { name: CONTACT_LABEL }).getAttribute("href")).toBe(CONTACT_URL);
    expect(screen.getByText(ORIGINAL_WORK_NOTICE)).not.toBeNull();
    expect(container.querySelector('a[href^="mailto:"]')).toBeNull();
  });
});
