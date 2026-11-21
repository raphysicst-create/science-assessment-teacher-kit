// /sitemap.xml: robots.ts가 가리키는 사이트 지도. Verify: npm run test:web.
import type { MetadataRoute } from "next";
import { SITE_URL, SITEMAP_PATHS } from "./lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  return SITEMAP_PATHS.map((path) => ({ url: new URL(path, SITE_URL).href }));
}
