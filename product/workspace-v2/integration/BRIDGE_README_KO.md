# IEPP Workspace v2 — 실제 추천안 저장 연결 어댑터

현재 상태: **로컬 계약 테스트 완료 / 실 운영 사이트 미연결**.

## 목적
사용자가 실제 IEPP Lineage 사이트에서 추천 요청 초안을 생성했을 때, ChatGPT 연결을 통해 요청을 **읽고** 현재 revision을 기준으로 구성안을 **검토 대기 상태로 저장**할 수 있는 어댑터를 추가했다.

## 안전 경계
- 실제 `draft_id`는 운영 사이트가 생성해야 한다. UI에서 추정하거나 임의로 구성하지 않는다.
- `readOwnedRequest`는 인증된 계정의 `get_project_recommendation_request` 결과를 사이트에서 정규화한 객체만 반환해야 한다. **연결 도구의 실제 원시 응답은 아직 확인되지 않아 정규화 계층은 미구현**이다.
- `savePending`는 공식 `save_project_recommendation`에만 연결한다. 프로젝트 생성·승인·에이전트 실행·유튜브 게시·과금과 연결하지 않는다.
- revision 충돌/권한 오류/네트워크 오류에서 자동 재시도 또는 성공 표시 금지.
- 클라이언트가 제공한 goal, agent 지시문, 모델명, owner 정보가 권한의 근거가 되어서는 안 된다.
- 4개 역할/6개 작업, 자료조사/콘텐츠/사업용 일반 템플릿도 지원한다.

## 호출 예제 (서버 측 / 승인된 연결 제공자에 한함)
```js
import {submitForHumanReview} from './recommendation-bridge.mjs';
const result = await submitForHumanReview({
  draftId: siteGeneratedOwnedDraftId,
  actualModelLabel: 'GPT-6',
  readOwnedRequest: async ({draft_id}) => {
    const raw = await officialConnector.get_project_recommendation_request({draft_id});
    return normalizeOfficialToolResponse(raw); // 반드시 실제 응답을 관찰하여 구현
  },
  savePending: (payload) => officialConnector.save_project_recommendation(payload),
});
// 사용자에게 result.next_action 표시. 생성/승인 완료라고 주장하지 않는다.
```

## 마지막 연동에 필요한 항목
1. 실제 사이트 소스/배포 제어권, 안전한 staging.
2. 실제 계정이 생성한 `draft_id`와 `get_project_recommendation_request` 원시 응답(민감 정보 제외)으로 정규화 구현.
3. 브라우저에서 추천안 저장/새로고침/검토/최종 프로젝트 생성 E2E 시험.
4. 사용자별 접근 격리, 중복 클릭, revision 경합, 인증 만료, 오류 복구 테스트.

## 로컬 검증
`node --test recommendation-contract.test.mjs recommendation-bridge.test.mjs`

도구의 읽기/쓰기 인터페이스를 모의로 주입하여 성공·실패·권한·revision·프롬프트 주입 경계를 검증한다. **실제 사이트 연결 시험은 아직 수행하지 않았다.**
## 운영 연결의 성공 응답 규칙

실제 Site 연결 코드는 `save_project_recommendation`의 원시 응답을 확인하여 **검토 대기 초안 저장이 성공했을 때만** `savePending`에서 `{ok:true}`를 반환해야 한다. 오류, 응답 누락, 응답 형식 미확인은 실패로 처리한다. 실제 원시 응답 형태를 보지 못한 상태에서 성공으로 추정하지 않는다.
