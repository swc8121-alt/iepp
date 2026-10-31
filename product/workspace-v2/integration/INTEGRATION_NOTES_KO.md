# IEPP 개인용 AI 워크스페이스 — 실제 사이트 연동 준비 v0.1

> 단계: **실제 운영 사이트 미반영**. 정적 UI와 연결 서비스의 관찰된 계약을 이어주는 구현 준비 자료. 연구 프로토콜이나 계정 데이터를 변경하지 않는다.

## 1. 확인된 기반과 미확인 구간

- GitHub `swc8121-alt/iepp`에는 v2 정적 UI 프로토타입(PR #22)이 있다. 사이트 배포용 전체 코드/설정은 확인되지 않았다.
- IEPP Lineage 연결 도구에 `get_project_recommendation_request({draft_id})`, `save_project_recommendation({...})`가 있다. 첫 번째로 요청·revision을 읽어야 저장이 가능하다.
- `save_project_recommendation`은 **대기 중인 초안**을 저장한다. 등록·승인·실제 AI 실행이 아니다. 사용자가 사이트에서 검토하고 생성하는 단계가 남는다.
- 라이브 사이트의 브라우저 UI/소스/배포 경로를 현재 수정할 권한이나 도구는 확인되지 않았다. UI에서 요청 초안을 생성하는 실제 백엔드 API 경로와 응답 JSON은 **미확인**이므로 임의 경로를 코드에 만들지 않았다.

## 2. 안전한 통합 순서

1. 사용자 사이트에 로그인해 목표, 프로젝트명, 템플릿, 선호 모델을 입력한다.
2. **실제 사이트가 지원하는 요청 생성 기능**으로 사용자 소유 `draft_id`를 생성하고, 해당 요청의 현재 revision을 반환한다. (이 기능의 실제 소스·경로 확인 전까지는 미구현.)
3. ChatGPT 연결 도구가 `get_project_recommendation_request({draft_id})`를 호출한다. 요청 내용과 revision이 현재 사용자·목표에 부합하는지 확인한다.
4. 서버/신뢰된 실행 환경에서 `buildPendingRecommendation`이 `save_project_recommendation`의 payload를 만든다. 실제 응답이 제공한 `draft_id`, `expected_revision`, `goal`만 넣고 모델명을 정직하게 기록한다.
5. `save_project_recommendation`을 호출하여 초안을 저장한다. revision 불일치 시 무조건 다시 읽고, 자동 덮어쓰기·중복 생성 금지.
6. 브라우저에 **사용자가 검토할 초안**이 표시된다. 사용자가 동의할 때만 사이트에서 실제 프로젝트 생성·승인 과정을 진행한다.
7. 프로젝트별 데이터 조회 후 UI를 갱신한다. 기록 일치는 실제 런타임 검증이나 원본성으로 표시하지 않는다.

## 3. 실제 도구에 넣을 구조

`buildPendingRecommendation` 반환 객체는 아래 필드를 가진다.

```json
{
  "draft_id": "<실제 get에서 확인한 ID>",
  "expected_revision": 1,
  "structure": {
    "version": 1,
    "title": "프로젝트명",
    "goal": "고객 목표",
    "agents": [],
    "tasks": [],
    "connections": ["iepp-lineage"]
  },
  "explanation": "검토용 추천안 설명",
  "model_label": "실제 작성 모델의 이름"
}
```

실제 실행 시 `agents`/`tasks`는 각 3개로 채워진다. `model_label`은 배정 모델이 아니라 **추천 표시**이고, `connections`는 연결 제안이지 승인된 외부 서비스 권한이 아니다. `output_plan`, 일정, 자동 발송은 기본적으로 제외한다.

## 4. 수용 기준 (운영 서버와 연결된 후 수행)

- 사용자 1, 사용자 2의 `draft_id`를 교차 사용해도 데이터가 노출되지 않음(인증 계정 격리).
- 수정 중 revision 충돌 발생 시 409 등 서버 정의 충돌을 감지하고 재조회; 이전 제안 자동 재전송 금지.
- 3개 역할/3개 작업이 모두 동일 사용자·동일 프로젝트로 연결되고, 승인 없이 실행되지 않음.
- 브라우저 새로고침 후 추천안/생성 상태가 서버 조회값과 일치.
- `draft`/`requested`/`approved`/`reported`/`stopped`/`unknown`을 혼동하지 않음. `running`은 실제 런타임 관측이 있을 때만 표기.
- 기록 해시 일치(`match`)를 실행 연속성 증명·원본성으로 주장하지 않음.
- API 요청 과금/중복 차감 방지 및 미연결·오류·중단 복구를 별도 시험.

## 5. 검증된 내용과 범위

`node --test product/workspace-v2/integration/recommendation-contract.test.mjs` : 템플릿 3종, 참조 무결성, revision 입력 검사, 프롬프트 주입 문자열의 역할 지침 분리, IEPP 상태 표기 분리를 모의 입력으로 시험한다. 이 테스트는 실서버 통합 시험이 **아니다**.

## 6. 다음에 반드시 필요한 자료

운영 사이트의 실제 소스 저장 위치 또는 ChatGPT Site 편집 경로, 해당 사용자 계정의 프로젝트 추천 요청 생성 UI/API 계약, 작업 승인·산출물 조회 응답 예제(개인정보 제거), staging 환경. 이 네 가지가 확인되면 별도 브랜치에서 API 연결과 E2E 테스트를 추가한다.