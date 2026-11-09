# 중학교 과학 수행평가 아카이브

중학교 과학 교사가 2022 개정 교육과정의 단원·활동·학년으로 수행평가 사례를 찾고, 원문 근거를 확인하며 수업을 설계하는 교사용 웹앱입니다. 현재 1·2학년 자료를 대상으로 하며, 단원과 활동의 자동 분류는 설계 참고 정보로 제공합니다.

## 처음 실행하기

Node.js 24 이상, pnpm 11, Python 3.12 이상이 필요합니다. 아래 예시는 Windows PowerShell 기준입니다. GitHub에서 **Code → Download ZIP**으로 받은 경우에는 압축을 풀고 그 폴더에서 `pnpm install`부터 실행하면 됩니다.

Windows에서 프로젝트를 외장 드라이브에 둘 때는 NTFS를 사용하세요. exFAT에서는 pnpm의 의존성 링크 설치가 실패할 수 있습니다.

```powershell
git clone https://github.com/raphysicst-create/math-assessment-teacher-kit.git
cd math-assessment-teacher-kit
pnpm install --frozen-lockfile
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r services/math-assessment-api/requirements.txt
.\.venv\Scripts\python.exe -m scripts.build_math_assessment_demo
$env:MATH_ASSESSMENT_PUBLISH_DB = (Resolve-Path data/demo/demo.sqlite).Path
$env:MATH_ASSESSMENT_DETAIL_DB = $env:MATH_ASSESSMENT_PUBLISH_DB
pnpm dev
```

터미널을 열어 둔 상태에서 [사례 탐색](http://127.0.0.1:3100/cases)을 엽니다. 데모 DB에는 가상 중학교 과학 2사례·4항목이 있습니다. 1학년의 열의 이동 실험·전기 회로 발표와 2학년의 물질의 특성 탐구 보고서·과학 활동 기록으로 필터와 원문 보기를 확인할 수 있습니다. 종료할 때는 터미널에서 `Ctrl+C`를 누릅니다.

방문자 집계와 웹 분석은 기본으로 꺼져 있습니다. 사이트 주소는 `NEXT_PUBLIC_SITE_URL` 환경 변수로 지정하며, 미지정 시 `http://localhost:3000`을 사용합니다. 로컬 실행 주소에 맞추려면 `http://127.0.0.1:3100`으로 지정합니다. 방문자 집계의 허용 출처는 `MATH_ASSESSMENT_COUNTER_ORIGIN`으로 지정합니다.

macOS·Linux에서는 `py -3.12`를 `python3.12`로, `.\.venv\Scripts\python.exe`를 `.venv/bin/python`으로 바꿉니다. 환경변수는 아래처럼 지정합니다.

```bash
export MATH_ASSESSMENT_PUBLISH_DB="$PWD/data/demo/demo.sqlite"
export MATH_ASSESSMENT_DETAIL_DB="$MATH_ASSESSMENT_PUBLISH_DB"
pnpm dev
```

## 실데이터 연결과 검증

검토용 과학 실데이터 DB는 `data/publish/science/` 아래에 둡니다. 다음과 같이 두 환경 변수를 지정하면 목록과 상세 요청이 모두 과학 DB를 읽습니다. 빌더는 과학 항목·분류 근거가 준비된 회차를 입력으로 사용합니다.

```powershell
.\.venv\Scripts\python.exe scripts/build_science_catalog_db.py --output data/publish/science/math_assessment_catalog_detail.sqlite
$env:MATH_ASSESSMENT_PUBLISH_DB = (Resolve-Path data/publish/science/math_assessment_catalog_detail.sqlite).Path
$env:MATH_ASSESSMENT_DETAIL_DB = $env:MATH_ASSESSMENT_PUBLISH_DB
.\.venv\Scripts\python.exe scripts/validate_math_assessment_publish_db.py --profile science --database $env:MATH_ASSESSMENT_PUBLISH_DB --output data/derived/science-validation.json
pnpm dev
```

기존 DB를 재생성할 때 빌더에 `--replace`를 붙입니다. 검증 결과의 `passed`와 각 `checks`가 `true`인지 확인합니다. 데모 DB도 같은 검증 명령의 `--database`에 `data/demo/demo.sqlite`를 지정해 검사할 수 있습니다. 테스트는 임시 폴더에 과학 데모 DB를 만듭니다.

```powershell
npm.cmd run test:api
npm.cmd run lint:api
npm.cmd run test:web
npm.cmd run test:boundary
```

macOS·Linux에서는 `npm.cmd` 대신 `npm`을 사용합니다. 내부 패키지·환경 변수·스크립트 이름은 기존 이름을 유지합니다.

## 코드와 자료 안내

| 하고 싶은 일 | 읽을 곳 |
| --- | --- |
| 과학 DB의 필드와 공개 경계 확인 | [데이터 사전](docs/MATH_ASSESSMENT_PUBLISH_DATA_DICTIONARY.md) |
| 단원·활동 분류 기준 확인 | `data/reference/science_axes.json` |
| 사례 화면·검색·비교 로직 읽기 | `apps/math-assessment-web/app/` |
| 검색 API와 DB 연결 읽기 | `services/math-assessment-api/app/` |
| 제목, 과목 경계, 배점, 원문 표의 검증 로직 읽기 | `scripts/`의 수집·추출·감사 코드 |

## 이용 범위와 도움 요청

이 저장소의 자체 소스코드, 안내 문서, 가상 예제는 MIT 라이선스로 이용할 수 있습니다. 의존 패키지의 권리는 각 패키지 라이선스를 따릅니다. 운영 서비스의 학교 자료와 데이터베이스는 별도로 관리합니다. [MIT 라이선스](LICENSE) · [출처와 공개 기준](docs/SOURCE_POLICY.md)

운영자는 GitHub `raphysicst-create`입니다. 설치·추출 오류와 정정·삭제 요청은 GitHub 이슈로 접수합니다. 사용 중인 운영체제, Node.js와 Python 버전, 실행 명령과 오류 메시지 또는 학교알리미 출처 링크와 문제의 표 위치를 남겨 주세요. [문의·정정·삭제 요청](https://github.com/raphysicst-create/math-assessment-teacher-kit/issues)

이 사이트는 「수학 수행평가 아이디어 아카이브」(서아인, MIT 라이선스)를 바탕으로 만든 과학판입니다.

원저작권과 MIT 이용 조건은 LICENSE 파일에 보존합니다. [LICENSE](LICENSE)
