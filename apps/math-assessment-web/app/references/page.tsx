// Science reference route and search metadata. Verify: npm run build.
import type { Metadata } from "next";
import { Suspense } from "react";

import { pageMetadata } from "../lib/site";
import ReferenceExplorer from "./ReferenceExplorer";

export const metadata: Metadata = pageMetadata("/references", "단원·활동별 과학 수행평가", "2022 개정 중학교 과학 영역과 활동으로 찾는 수행평가 사례입니다.");

export default function ReferencesPage() {
  return <Suspense fallback={<div className="routeLoading" role="status">과학 수행평가 사례를 준비하고 있습니다.</div>}><ReferenceExplorer /></Suspense>;
}
