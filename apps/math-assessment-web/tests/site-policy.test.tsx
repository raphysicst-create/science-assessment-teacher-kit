// Verify shared identity in metadata and policy routes. Run with npm run test:web.
import { describe, expect, it } from "vitest";
import { metadata } from "../app/layout";
import { GET as llms } from "../app/llms.txt/route";
import { GET as tdm } from "../app/.well-known/tdmrep.json/route";
import robots from "../app/robots";
import sitemap from "../app/sitemap";
import { CONTACT_URL, OPERATOR_NAME, ORIGINAL_WORK_NOTICE, SITE_DESCRIPTION, SITE_NAME, SITE_URL, SITEMAP_PATHS, pageMetadata, resolveSiteUrl } from "../app/lib/site";
import { metadata as casesMetadata } from "../app/cases/page";
import { generateMetadata as caseDetailMetadata } from "../app/cases/[caseId]/page";
import { metadata as compareMetadata } from "../app/compare/page";
import { metadata as guideMetadata } from "../app/guide/page";
import { metadata as privacyMetadata } from "../app/privacy/page";
import { metadata as referencesMetadata } from "../app/references/page";
import { metadata as reviewMetadata } from "../app/review/page";
import { metadata as sourcesMetadata } from "../app/sources/page";
import { metadata as termsMetadata } from "../app/terms/page";
import { metadata as trendsMetadata } from "../app/trends/page";

describe("과학판 공통 사이트 정보", () => {
  it("메타데이터와 sitemap 주소에 공통 상수를 사용한다", () => {
    expect(metadata.title).toEqual({ default: SITE_NAME, template: `%s | ${SITE_NAME}` });
    expect(metadata.description).toBe(SITE_DESCRIPTION);
    expect(metadata.metadataBase?.href).toBe(new URL(SITE_URL).href);
    expect(robots().sitemap).toBe(new URL("/sitemap.xml", SITE_URL).href);
  });

  it("정책 응답에 운영자와 이슈 주소·원저작 고지를 제공한다", async () => {
    const policy = await llms().text();
    expect(policy).toContain(SITE_NAME);
    expect(policy).toContain(SITE_URL);
    expect(policy).toContain(OPERATOR_NAME);
    expect(policy).toContain(CONTACT_URL);
    expect(policy).toContain(ORIGINAL_WORK_NOTICE);
    expect(await tdm().json()).toMatchObject({ owner: OPERATOR_NAME, contact: CONTACT_URL, site: SITE_URL });
  });
});

describe("검색엔진 색인 정보", () => {
  const pages = [
    ["/cases", casesMetadata], ["/compare", compareMetadata], ["/guide", guideMetadata],
    ["/privacy", privacyMetadata], ["/references", referencesMetadata], ["/review", reviewMetadata],
    ["/sources", sourcesMetadata], ["/terms", termsMetadata], ["/trends", trendsMetadata],
  ] as const;

  it("루트 레이아웃은 대표 주소를 하위 페이지에 물려주지 않는다", () => {
    expect(metadata.alternates).toBeUndefined();
    expect(metadata.openGraph).not.toHaveProperty("url");
  });

  it.each(pages)("%s 페이지의 대표 주소와 공유 주소는 자기 주소다", (path, page) => {
    expect(page.alternates?.canonical).toBe(path);
    expect(page.openGraph?.url).toBe(path);
    expect(page.title).toBeTruthy();
    expect(page.description).toBeTruthy();
  });

  it("사례 상세의 대표 주소는 그 사례 주소다", async () => {
    const detail = await caseDetailMetadata({ params: Promise.resolve({ caseId: "0f35007c0d5d6805ff1135e8" }) });
    expect(detail.alternates?.canonical).toBe("/cases/0f35007c0d5d6805ff1135e8");
  });

  it("페이지 메타데이터는 공유 제목에 사이트 이름을 붙인다", () => {
    expect(pageMetadata("/guide", "사용설명서", "설명")).toEqual({
      title: "사용설명서",
      description: "설명",
      alternates: { canonical: "/guide" },
      openGraph: { title: `사용설명서 | ${SITE_NAME}`, description: "설명", url: "/guide", siteName: SITE_NAME, locale: "ko_KR", type: "website" },
    });
  });

  it("sitemap은 안내·탐색 화면만 사이트 주소로 싣는다", () => {
    expect(sitemap().map((entry) => entry.url)).toEqual(SITEMAP_PATHS.map((path) => new URL(path, SITE_URL).href));
    expect(SITEMAP_PATHS).toEqual(["/", "/references", "/cases", "/trends", "/guide", "/sources", "/terms", "/privacy"]);
  });

  it("사이트 주소는 지정값, Vercel 운영 도메인, 로컬 순으로 정한다", () => {
    expect(resolveSiteUrl("https://example.kr", "x.vercel.app")).toBe("https://example.kr");
    expect(resolveSiteUrl(undefined, "x.vercel.app")).toBe("https://x.vercel.app");
    expect(resolveSiteUrl("", "x.vercel.app")).toBe("https://x.vercel.app");
    expect(resolveSiteUrl(undefined, undefined)).toBe("http://localhost:3000");
  });
});
