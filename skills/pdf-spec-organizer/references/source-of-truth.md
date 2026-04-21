# Source-of-truth 인터페이스 (v2 확장 포인트)

v1 에서는 구현되지 않는다. v2 "기존 스펙과의 충돌 체크" 를 위한 인터페이스 스케치.

## 목적

Phase 2 (구조화) 직후, 추출된 피처가 기존 앱/스펙과 **충돌/중복**되는지 사전 확인.

## 입력

- 추출된 피처 리스트: `[{name, platform, summary}]`
- 기존 source-of-truth 구성:
  ```json
  {
    "notion_feature_db": "<db-id>",
    "codebase_roots": ["/path/to/ios-repo", "/path/to/android-repo"]
  }
  ```
  프로젝트 레포의 `yeoboya-workflow.config.json` 에 선언.

## 출력 (각 피처마다)

```json
{
  "feature_name": "알림 설정 화면",
  "matches": [
    {"kind": "notion_page", "title": "알림 설정", "id": "<page-id>", "similarity": 0.85},
    {"kind": "code_symbol", "path": "ios-repo/NotificationSettings.swift", "line": 42}
  ],
  "recommendation": "관련 피처로 연결 제안 (Relation)"
}
```

## 구현 힌트 (v2 작업자용)

- Notion DB 쿼리: `mcp__claude_ai_Notion__notion-search` 으로 제목/본문 유사도 기반 후보 수집
- 코드베이스: `grep -rn "<피처명의 키워드>" <codebase>` 로 간단한 심볼/파일명 매칭
- 유사도 판정은 Claude 에게 후보 목록 + 피처 설명을 주고 맡긴다 (임베딩/벡터 DB 는 v3 이상)

## v1 에서 이 인터페이스를 어떻게 "열어두는가"

- Phase 2 직후에 "[Phase 2.5] source-of-truth 조회 — v1 비활성" 주석만 SKILL.md 에 남김
- 추출된 피처 리스트를 임시 JSON 으로 덤프하는 코드 경로를 유지 (나중에 v2 가 이 JSON 을 소비)
- Notion 페이지의 `관련_피처` Relation 속성은 v1 에서 비워두지만 **스키마에는 존재**
