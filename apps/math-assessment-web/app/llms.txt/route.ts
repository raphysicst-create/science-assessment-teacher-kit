import { CONTACT_LABEL, CONTACT_URL, OPERATOR_NAME, ORIGINAL_WORK_NOTICE, SITE_NAME, SITE_URL } from "../lib/site";

const POLICY = `# ${SITE_NAME}

사이트 주소 ${SITE_URL}
운영 ${OPERATOR_NAME}
${ORIGINAL_WORK_NOTICE}
코드의 이용에는 LICENSE의 MIT 라이선스가 적용됩니다.
학교알리미 공개 평가계획 원문은 별도 권리와 이용 조건의 적용을 받습니다.

## 이용 조건
- 사람 교사의 개별 수업·평가 설계 참고를 위한 열람과 링크 공유는 허용됩니다.
- 자동 수집, 대량 복제, 데이터셋 구축, 재배포, 다른 서비스의 학습·검색 인덱스·생성형 AI 학습 또는 복제에는 사전 서면 허락이 필요합니다.
- 항목별 표는 안전 변환한 재현본이므로 공식 원문을 대체하지 않습니다.

${CONTACT_LABEL} ${CONTACT_URL}
`;

export function GET() {
  return new Response(POLICY, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "X-Robots-Tag": "noindex, nofollow, noarchive",
    },
  });
}
