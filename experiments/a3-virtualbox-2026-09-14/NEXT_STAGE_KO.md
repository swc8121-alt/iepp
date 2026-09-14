# 다음 주요 단계 — A3 증거 보완 → A4 → L2 진입 준비

상태: 준비 계획, 미실행. 2026-09-14.
기준: [Issue #6](https://github.com/swc8121-alt/iepp/issues/6), [고정 버전 A3 실행서](https://github.com/swc8121-alt/iepp/blob/a8a5ef374afb18f2c8a7014641fa9fad33fdb26d/docs/A3_VirtualBox_Runbook_KO.md).
기존 백서·원본 로그·스냅샷은 보존한다. 이후 결과는 새 ID와 디렉터리에 저장한다.

## 1. 가장 먼저: 보유 증거 수집

새 VM 복제 전에 Windows의 a3-vm-lab-01/02/03 폴더에서 각각 registry-events.jsonl을 수집한다. RESTORE-0001은 lab-01 서버 기록과 함께 대조한다. 파일이 없으면 재현 결과로 대체하지 않고 '당시 서버 원문 없음'으로 남긴다.

실행 파일 5개(a3_vm_runner.py, a3_registry_server.py, a3_registry.py, core.py, durable_store.py)의 SHA-256을 Windows와 VM에서 수집한다. 서로 다른 파일은 숨기지 말고 차이를 확인한다. 이후 실행에는 저장소 작업 디렉터리 안에서 prepare를 수행해 git_revision()의 현재 디렉터리 의존성을 피한다. 기존 snapshot이 물려준 UNKNOWN은 과거 로그를 고쳐 없애지 않는다.

새 로그에는 trial ID, VM 이름·SSH 포트·IP, 스냅샷 UUID, 실제 restore 시작/완료, Git SHA·dirty 여부, 실행 파일 해시, Python/VirtualBox 버전, challenge 발급·만료, 서버 재시작 유무, barrier와 delay를 별도로 남긴다. hostname이 같은 네 VM은 SSH 포트와 VM UUID로 구별한다.

## 2. 승인 후 상태를 포함하는 A3 보완

Issue #6의 '승인 전이 이후 스냅샷'은 현재의 초기 enrolled-P0 스냅샷과 구분해야 한다.

| 새 ID | 절차 | 완료 기준 |
|---|---|---|
| A3-P1-BASELINE-0001 | 새 격리 레지스트리에서 P0→P1→P2 정상 전이 | 각 전이 승인, counter 1→2, head 일치 |
| A3-P1-RESTORE-0001 | P1 승인 후 저장한 VM 스냅샷을 명시적으로 복원; 서버가 P1일 때 후속 제출 | 정상 후속 1회 승인 |
| A3-P1-STALE-0001 | 서버가 P2로 진행한 뒤 VM만 P1으로 복원; 새 챌린지 제출 | stale predecessor 거절, P2 유지 |
| A3-SHARED-BA-0001 | 동일 키·P1·미사용 챌린지를 포함한 스냅샷에서 두 분기 복원, B→A | B 승인, A used-challenge 거절 |
| A3-SHARED-RESTORE-0001 | shared challenge 소비 전 스냅샷 저장; A 승인 후 VM만 복원; 같은 challenge 제출 | 유효기간 내 사용된 챌린지 거절, 승인 head 유지 |

준비가 필요한 구현: 현행 CLI에는 승인된 결과를 확인한 뒤 비밀키를 유지하며 counter/head를 갱신하는 안전한 snapshot 내보내기 명령이 없다. 소스에는 snapshot_at_head() 함수만 있다. 다음 코드 변경에서는 서버의 승인 응답과 기존 key/sid, successor/counter를 확인한 뒤 **새 출력 파일**을 생성하는 명령을 추가한다. 거절·통신 실패·head 불일치 때 갱신을 금지하는 검증을 포함한다. 이 명령이 준비되기 전에 사용자에게 수동으로 private snapshot 값을 바꾸도록 요구하지 않는다.

현재 챌린지는 서버 메모리에 있으므로 시험 중 서버를 재시작하지 않는다. TTL은 이번에 수락된 3,600초 이내로 설정하고 모든 준비가 끝난 뒤 발급한다. 만료·통신 실패·서버 재시작은 정상 정책 거절 표본으로 계산하지 않는다. 이미 사용되거나 만료된 04b 챌린지는 새 시험에 재사용하지 않는다.

## 3. 경쟁 제출의 사전 고정 범위

한 온라인 서버가 요청을 실제로 언제 수신·처리했는지 기록하도록 monotonic 수신·검증 시작·판정 완료 시각과 요청 식별자를 추가한다. 이 변경은 새 커밋으로 고정하고 과거 결과와 구별한다. 공통 barrier 또는 서로 다른 VM의 시각만으로 처리 중첩을 선언하지 않는다.

- 챌린지 유형: 분기별 fresh / 스냅샷에 포함된 shared.
- 상대 delay: (0,0), (0,1), (1,0), (0,5), (5,0), (0,10), (10,0), (0,50), (50,0), (0,100), (100,0) ms.
- 준비 점검: 2유형 × 11조건 × 1회 = 22개의 유효한 두 분기 시험.
- 준비 점검이 모두 검증되면 본 실행: 2유형 × 11조건 × 10회 = 220개. 준비 점검과 분리하여 집계.
- 각 독립 시험은 별도 등록 상태·DB·새 trial ID로 시작한다. 진행된 DB를 초기 P0 파일로 재사용하지 않는다.
- 유효한 두 분기 시험마다 승인 1·모의 동작 1·최종 head 일치. 이중 승인, 예상 밖 사유, 통신 실패는 숨기지 않고 별도 기록한다.
- 실제 중첩이 관측되지 않은 표본은 scheduled competing submissions로 보고하며 controlled overlap으로 부르지 않는다.
- 자동화가 준비되기 전 220회를 수동 복제 작업으로 진행하지 않는다. Node3·4를 재사용하되 복원으로 IP가 돌아가는 위험을 관리한다.

## 4. A4 엔트로피 장애 시험

Issue #6의 우선순위에 따라 A3 잔여 증거를 정리한 후, frozen/repeated/biased/predictable/unavailable/truncated/substituted 입력을 실제 reference 경로에 주입하는 계획을 확정한다. 각 입력의 예상 reject/detect/downgrade를 먼저 적는다. canonical acceptance와 entropy health는 별도 지표다. 정상 entropy가 아니라도 승인 직렬화가 유지되는 결과를 '엔트로피 품질 검증'으로 해석하지 않는다. 정적·예측 가능한 입력 대조군과 인증·predecessor 위반 음성 대조군을 함께 둔다.

## 5. L2는 별도 진입 관문

프로젝트의 L2 정의는 격리된 키/상태와 TPM·TEE·secure-element attestation이다. VM 개수 또는 PC 개수를 늘리는 것만으로 L2가 되지 않는다.

첫 조사는 비용 없는 읽기 전용 장비 확인이다. TPM 초기화·Clear·소유권 변경·펌웨어 변경은 준비 범위에 넣지 않는다. 다음 항목을 문서로 확정한 뒤 장비 또는 클라우드를 선택한다.

1. 공격자가 복제할 수 있는 파일·키·VM 상태와 신뢰할 하드웨어/검증자를 명시한다.
2. 비내보내기 키뿐 아니라 rollback 가능한 실행 상태를 어떤 보호 상태 또는 외부 checkpoint와 결합할지 정한다.
3. attestation freshness, 검증 체인, 측정 코드와 IEPP transition의 결합을 설명한다.
4. 정상 재개, 복사된 디스크/자격증명, 과거 상태 재개, 검증 실패·만료, 허가된 migration을 각각 구분한다.
5. TPM/TEE 사용 사실과 uninterrupted canonical continuity 보장을 구별한다.
6. 총 지출 상한 30,000원. 현재 계획 작성으로 발생한 구매·클라우드 실행은 없다.

## 실행 순서

보유 서버 기록과 파일 해시 확보 → 승인 상태 export 및 서버 관측 기능을 작은 PR로 구현·검증 → 승인 후 snapshot/restore 보완 → 22회 준비 점검 → 220회 사전 고정 실행 → A4 및 L2 읽기 전용 적합성 조사.

기존 Issue #6의 체크박스는 부분 증거로 일괄 완료 처리하지 않는다. A3의 전체 baseline·snapshot 위치·restore·delay·challenge 조건을 충족한 뒤 해당 항목별로 증거 링크를 붙인다.
