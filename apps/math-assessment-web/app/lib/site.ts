// Shared science archive identity and contact details, imported by pages and routes.
// Run with npm run dev:web. Verify with npm run test:web && npm run build.
import type { Metadata } from "next";

export const SITE_NAME = "중학교 과학 수행평가 아카이브";
export const SITE_DESCRIPTION = "중학교 과학 수행평가를 단원과 활동으로 찾아 원문 근거와 함께 비교하는 교사용 아카이브";
// 사이트 주소: 지정값 → Vercel이 빌드 때 주는 운영 도메인 → 로컬. 서버 쪽(메타데이터·robots·sitemap)에서만 쓴다.
export function resolveSiteUrl(explicit?: string, vercelProductionHost?: string): string {
  if (explicit) return explicit;
  return vercelProductionHost ? `https://${vercelProductionHost}` : "http://localhost:3000";
}
export const SITE_URL = resolveSiteUrl(process.env.NEXT_PUBLIC_SITE_URL, process.env.VERCEL_PROJECT_PRODUCTION_URL);
export const OPERATOR_NAME = "raphysicst-create";
export const OPERATOR_URL = "https://github.com/raphysicst-create";
export const CONTACT_URL = "https://github.com/raphysicst-create/math-assessment-teacher-kit/issues";
export const CONTACT_LABEL = "자료 오류·정정·삭제 요청: GitHub 이슈";
export const ORIGINAL_WORK_NOTICE = "이 사이트는 「수학 수행평가 아이디어 아카이브」(서아인, MIT 라이선스)를 바탕으로 만든 과학판입니다.";

// 검색엔진에 알릴 안내·탐색 화면. 개인 작업 화면(/review, /compare)과 사례 상세는 싣지 않는다.
export const SITEMAP_PATHS = ["/", "/references", "/cases", "/trends", "/guide", "/sources", "/terms", "/privacy"] as const;

// 페이지마다 자기 주소를 대표 주소(canonical)와 공유 주소(og:url)로 낸다. 레이아웃 값은 물려받지 않는다.
export function pageMetadata(path: string, title: string, description: string): Metadata {
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { title: `${title} | ${SITE_NAME}`, description, url: path, siteName: SITE_NAME, locale: "ko_KR", type: "website" },
  };
}
