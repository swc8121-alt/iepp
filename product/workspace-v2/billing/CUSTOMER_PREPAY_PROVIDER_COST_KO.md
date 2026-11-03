# IEPP Workspace — 고객 선결제 / 사업자 API 원가 부담 구조 v0.1

상태: 설계안. 실제 결제·API 실행·운영 배포는 하지 않았음. 2026-11-03.

## 핵심: 결제는 서로 독립적
- 고객은 IEPP Workspace의 서비스 이용권을 원화로 선결제한다. 고객의 결제금액이 OpenAI로 자동 이전되는 것은 아니다.
- 사업자는 자체 OpenAI API 조직의 크레딧 또는 카드 청구를 별도로 부담한다. 신규 API 계정은 보통 크레딧을 사전에 구입하는 선불 방식이므로 고객을 받기 전에 운영 잔액을 확보해야 한다.
- PG가 고객 카드 결제를 승인한 시간과 사업자 계좌에 정산대금을 입금하는 시간은 다르다. API는 고객 이용 시 먼저 사업자 선불 크레딧에서 차감될 수 있다.
- 사업자 API 원가에는 모델 토큰 외 웹 검색, 저장/전송, 환율, 기타 도구 사용료를 포함한다. 판매가에는 결제대행 수수료와 세금도 고려한다.

## 권장 베타: 1,900원 / 7일 / 단건 결제
- 1,900원은 가격 가설이다. 실측 원가 없이 실행 횟수나 예산을 확정하지 않는다.
- 프로젝트 1개, AI 팀 구조 4개, 작업 초안 6개를 관리할 수 있다고 해도 API를 6회 무조건 실행하거나 영상 파일을 보장하는 것은 아니다.
- 고객이 현금처럼 이전·환급·전송할 수 있는 포인트 판매가 아니라, 기간·사용한도·기능 범위가 정해진 서비스 이용권을 첫 상품 후보로 검토한다.
- 자동 갱신 없음. 실제 영상 렌더링과 장시간 고급 추론은 베타 기본 제공량에서 분리한다.

## 결제 → 실행 → 정산 순서
1. 운영자가 별도로 OpenAI API 잔액을 확보하고 자동 충전 임계값 및 월 충전 한도를 확인한다.
2. 고객이 서비스 상품을 선택하고 국내 결제대행사(PG)에서 결제한다.
3. 우리 서버가 PG 승인 응답을 검증한다. 결제 성공 페이지 표시만으로 이용권을 발급하지 않는다.
4. 동일 주문(orderId)에 대해 서비스 이용권을 한 번만 발급한다. 결제 취소/환불/중복 웹훅을 별도로 처리한다.
5. 고객이 AI 실행을 누르면 모델, 검색 옵션, 토큰 상한, 고객 이용권 잔여 사용 한도, 회사 API 잔액과 공급자 상태를 점검한다.
6. (tenant_id, action_id)를 고유키로 원가 예상 상한을 서버에서 선점한다. 선점 실패 시 API를 호출하지 않는다.
7. 서버가 회사 소유 API 키로 OpenAI를 호출한다. 사용자 브라우저나 클라이언트에 회사의 API 키를 배포하지 않는다.
8. 공급자 응답·실제 사용량을 확인해 사용 원가를 정산하고 미사용 예약액을 해제한다. 결과 불명이면 unknown으로 보관하고 확인한다.
9. PG 실정산 입금액과 고객 결제·환불 원장을 대사하고, 회사 OpenAI API 구매/사용 기록과도 별도 대사한다.

## 운영 및 보안 핵심
- 데이터 제안: orders(id, tenant_id, order_id UNIQUE, pg_payment_key UNIQUE, amount_krw, status); entitlements(order_id UNIQUE, expires_at, api_budget_microusd, used_microusd, reserved_microusd); ai_actions(tenant_id, action_id, state, reserved_microusd, provider_ref) UNIQUE(tenant_id, action_id); usage_events(action_id, actual_cost_microusd, observed_at); provider_balance_snapshots.
- 비율/통화 계산에는 부동소수점 대신 정수 최소 단위를 쓴다. 원화 판매액과 달러 API 사용 원가를 분리해 관리한다.
- 사용량 예약·차감·재시도는 데이터베이스 트랜잭션과 원자적 멱등 처리가 필요하다. 이 문서의 구조만으로 그런 보장이 생기지는 않는다.
- 시스템의 API 잔액 부족은 사용자 예산 부족과 다르다. 이미 결제한 고객에게 추가 결제를 강요하지 않고 운영 장애·복구·이용기간·환불 정책으로 처리한다.
- 공급자 응답 지연/실패 시 서비스 완료나 비용 차감 완료를 확정하지 않는다. 외부 결과 조회 후 대사한다.
- 개인정보, 결제 정보, 약관·환불·표시 의무 및 선불성 상품 관련 법률 검토는 국내 유료 공개 전 별도 진행한다.

## 초기 수용 테스트
1. 위조된 결제 완료 URL / 결제 실패 시 이용권 미발급
2. 동일 주문 결제 승인 중복 도착 시 이용권 1개
3. 같은 작업 동시 실행 요청 시 비용 예약 및 AI 실행 중복 방지
4. 고객 한도 부족 vs 회사 OpenAI 잔액 부족의 별도 오류 표시
5. 타임아웃/실패 시 예약액 복구 또는 결과 확인 대기 상태
6. PG 카드 정산 전에도 API 사용 가능한 사업자 운전자금 확보
7. 모델 + 검색 + 도구 사용료 실측 후 제공량과 판매가 확정

## 아직 연결되지 않은 필수 요소
- 실제 IEPP 운영 사이트 소스/배포 경로 및 staging
- PG 테스트 가맹점·결제 승인 서버, 실제 운영 사업자/API 결제 권한
- 실제 모델별 호출 측정과 검색비 견적, 소비자 약관·환불 조건

공식 근거:
- OpenAI API 선불 결제: https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing
- OpenAI API 청구 유형: https://help.openai.com/en/articles/8156167-invoice-dates-for-chatgpt-and-api-billing
- Toss Payments 결제 승인: https://docs.tosspayments.com/guides/v2/get-started/payment-flow
- Toss Payments 멱등성: https://docs.tosspayments.com/reference/using-api/authorization

이 문서는 개발 설계이며 실제 결제 연동, API 요금 결제, 정산 또는 서비스 배포를 수행한 것이 아니다.