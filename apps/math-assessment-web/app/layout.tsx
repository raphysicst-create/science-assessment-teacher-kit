import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import Link from "./SiteLink";

import "@fontsource/gowun-dodum/korean.css";
import "katex/dist/katex.min.css";
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
import "./globals.css";
import VisitorCounter from "./VisitorCounter";
import { CONTACT_LABEL, CONTACT_URL, OPERATOR_NAME, OPERATOR_URL, ORIGINAL_WORK_NOTICE, SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "./lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_NAME,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: {
    title: SITE_NAME,
    description: SITE_DESCRIPTION,
    url: "/",
    siteName: SITE_NAME,
    locale: "ko_KR",
    type: "website",
  },
};

const navigation = [
  { href: "/trends", label: "공개자료 경향" },
  { href: "/references", label: "유형별 설계 참고" },
  { href: "/cases", label: "전체 라이브러리" },
  { href: "/guide", label: "사용설명서" },
  { href: "/sources", label: "자료 안내" },
];

function releaseDateLabel() {
  const parts = new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? "00";
  return `${value("year")}.${value("month")}.${value("day")}`;
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" data-scroll-behavior="smooth">
      <body>
        <a className="skipLink" href="#main-content">본문으로 바로가기</a>
        <header className="siteHeader">
          <div className="headerInner">
            <Link className="brand" href="/" aria-label={`${SITE_NAME} 홈`}>
              <svg className="brandLogo" viewBox="0 0 40 40" aria-hidden="true">
                <rect x="1" y="1" width="38" height="38" rx="9" fill="currentColor" />
                <path d="M10.5 27V13.5L20 22l9.5-8.5V27" fill="none" stroke="white" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="20" cy="22" r="2.35" fill="#38bdf8" />
              </svg>
              <span>{SITE_NAME}</span>
              <small className="brandUpdatedAt">업데이트 {releaseDateLabel()}</small>
            </Link>
            <nav aria-label="주요 메뉴">
              <ul className="mainNav">
                {navigation.map((item) => (
                  <li key={item.href}><Link href={item.href}>{item.label}</Link></li>
                ))}
              </ul>
            </nav>
          </div>
        </header>
        {children}
        <footer className="siteFooter">
          <div className="footerInner">
            <p>학교알리미 평가계획을 설계 근거로 활용하며, 최종 판단은 교사가 합니다.</p>
            <div className="footerMeta">
              <a href={OPERATOR_URL}>운영 {OPERATOR_NAME}</a>
              <a href={CONTACT_URL}>{CONTACT_LABEL}</a>
              <Link href="/terms">이용·보호 안내</Link>
              <Link href="/privacy">개인정보 처리방침</Link>
              <VisitorCounter />
            </div>
            <p>{ORIGINAL_WORK_NOTICE}</p>
          </div>
        </footer>
        {process.env.NEXT_PUBLIC_MATH_ASSESSMENT_ENABLE_ANALYTICS === "1" && <Analytics />}
      </body>
    </html>
  );
}
