// Verify shared identity in metadata and policy routes. Run with npm run test:web.
import { describe, expect, it } from "vitest";
import { metadata } from "../app/layout";
import { GET as llms } from "../app/llms.txt/route";
import { GET as tdm } from "../app/.well-known/tdmrep.json/route";
import robots from "../app/robots";
import { CONTACT_URL, OPERATOR_NAME, ORIGINAL_WORK_NOTICE, SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "../app/lib/site";

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
