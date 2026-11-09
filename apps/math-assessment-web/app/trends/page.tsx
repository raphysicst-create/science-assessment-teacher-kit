import type { Metadata } from "next";
import { Suspense } from "react";

import TrendsExplorer from "./TrendsExplorer";

export const metadata: Metadata = {
  title: "수집된 공개자료의 과학 수행평가 경향",
  description: "중학교 과학 공개 평가계획의 활동 표지와 평가 근거 집계를 살펴봅니다.",
};

export default function TrendsPage() {
  return (
    <Suspense fallback={<div className="routeLoading">경향 탐색기를 준비하고 있습니다.</div>}>
      <TrendsExplorer />
    </Suspense>
  );
}
