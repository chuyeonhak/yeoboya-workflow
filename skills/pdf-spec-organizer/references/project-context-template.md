# Project Context (템플릿)

이 파일을 프로젝트 루트 (또는 `yeoboya-workflow.config.json` 의 `project_context_path` 로 지정한 경로)에 복사해 사용한다. 섹션은 **권장** 수준이며, 팀이 필요에 따라 추가/축소할 수 있다. Claude 는 **있는 만큼** 참고한다.

최대 **500 줄** 까지 사용된다. 그 이상이면 절삭되고 경고가 표시된다.

---

# Project Context

## Team
- iOS: <인원수, 예: 2명 (Junior 1, Mid 1)>
- Android: <인원수>
- 백엔드: <조직 정보, Slack 채널 등>
- 디자인: <Figma/Notion 등>
- QA: <주기/회의>

## Current Sprint / Roadmap
- <현재 스프린트 / 분기 목표>
- <진행 중 프로젝트 / 이미 착수된 피처>

## Past Effort References
기간 추정 calibration 의 근간. 실측 기반으로 업데이트 권장.

- 간단 UI (기본 컴포넌트 조합): iOS 1일, Android 1일
- 신규 플로우 (2-3 화면 + API 연동): iOS 3-5일, Android 3-5일
- A/B 테스트 추가: +1일 (실험 플랫폼 연동 오버헤드)
- 네이티브 기능 (카메라/권한/결제): iOS 2-3일, Android 3-5일

## External Teams & Channels
- 백엔드: Slack #backend, 리드 @<handle>, API 변경은 최소 1주 전 요청
- 디자인: Notion "디자인 리소스 DB", Figma 소스 있음. 새 스타일 요청은 2-3일
- QA: 매주 월 QA 회의, 새 피처는 전주 금요일까지 요청
- 데이터/분석: (옵션) Amplitude/GA 연동 담당자

## Known Constraints
- 플랫폼 최소 지원: iOS <version>+, Android API <version>+
- 푸시: <FCM/APNs, 중앙화 정책>
- 결제: <IAP/PG 정책>
- 그 외 전사 정책 (보안/개인정보/접근성 등)
