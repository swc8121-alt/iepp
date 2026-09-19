# A3 Evidence Report — 2026-09-20

상태: **L1 연구 증거 보고서**. 이 문서는 2026-09-17 실제 VirtualBox restore 실험과 2026-09-20 두 VM race batch 결과를 함께 정리한다. 두 실험은 서로 다른 성질을 검증하며, 어느 쪽도 하드웨어 attestation·분산 합의·물리적 원본성·entropy 품질을 증명하지 않는다.

## 1. 검증 범위

A3의 질문은 다음과 같이 좁게 정의한다.

> 동일하거나 복제 가능한 자격증명·상태에서 나온 경쟁 continuation이 한 온라인 registry의 canonical head를 동시에 두 번 전진시킬 수 있는가, 그리고 이미 전진한 canonical head를 과거 VM 상태 복원으로 되돌릴 수 있는가?

현재 공개 claim은 **L1 single online registry + cooperative simulated policy gate** 범위다.

검증한 성질:

- 서명된 transition evidence의 challenge/counter/predecessor/state binding
- 한 registry view에서 successor 단일 승인
- losing fork 및 rollback 차단
- 승인된 branch만 cooperative simulated protected action 실행
- 실제 VirtualBox snapshot/restore 뒤 stale P1 continuation 차단
- 두 독립 VM worker의 반복 경쟁 제출에서 single-successor invariant 유지

검증하지 않은 성질:

- hypervisor가 restore 사실을 암호학적으로 attestation했다는 주장
- TPM/TEE/secure element/PUF 기반 L2 이상 보장
- 악성 애플리케이션이 policy gate 자체를 우회하는 경우
- registry 자체 rollback, split view, partition, equivocation
- 현재 key+state가 탈취된 공격자가 먼저 제출하는 경우의 방어
- entropy 품질·물리적 기원·예측불가능성
- 의식, 인격, 법적 동일성, 물리적/형이상학적 원본성

---

## 2. 실제 VirtualBox restore 실험

공개 증거 bundle:

- 파일명: `A3-actual-vm-restore-public-evidence-01.zip`
- ZIP SHA-256: `0e35e44973c0476fd8423d056e5d7c632a92eba4a951bf3001ec2affe77fc453`
- bundle 내부 8개 증거 파일은 `SHA256SUMS.txt`와 모두 일치
- 실행 코드 revision: `f2ab3b08ee26fb303e95e5032b00dc867ebf4078`

### 2.1 상태 전이

초기 P0:

`580e7f38f7f95814aee7b3d171bd21e284149e6e53ae265211a17142906174f5`

Baseline P0→P1 승인:

`2ec90523d62ef63b983426f582fb1a04b6bbe1b8aeecc980793176dceeef2865`

실제 P1 VM snapshot restore 뒤 P1→P2 승인:

`c0e56573aca8c749fa6e0590ef8c5c4be222dbb64b5bb6b7126ec9b78aba6238`

그 뒤 다시 과거 P1 상태에서 생성한 counter=2 후보를 제출했을 때:

- `canonical_accept=false`
- `registry_reason=ROLLBACK_OR_LOSING_FORK`
- `protected_action=BLOCKED`
- 거절 전후 canonical head는 모두 P2로 유지

P2 후보와 rollback 후보는 공개 enrollment key로 Ed25519 서명을 독립 검증했고, evidence ID와 상태전이 해시도 재계산해 일치했다.

### 2.2 서버 연속성

Baseline 승인, P2 승인, rollback 거절의 `registry_timing.server_instance_id`는 모두:

`76fd48e0390141fa987c1432b5655463`

따라서 공개 transcript 안에서는 registry가 같은 server instance를 유지한 채 canonical head가 P1→P2로 전진하고, 이후 stale P1 continuation을 차단한 흐름이 관측된다.

### 2.3 VirtualBox 증거

`virtualbox-snapshot-P1-01.txt`에는 다음 snapshot이 기록돼 있다.

- 이름: `A3_P1_ACCEPTED_RESTORE_01`
- UUID: `c17deb99-ecab-4251-af92-7a46abbdd944`
- 설명: `IEPP actual VirtualBox snapshot at accepted canonical P1`

이 파일은 운영자가 수집한 VirtualBox 상태 증거다. hypervisor가 restore 행위를 암호학적으로 attestation한 것은 아니다.

### 2.4 제한

Baseline P0→P1의 client result와 registry event는 bundle에 있으나 해당 baseline candidate JSON은 포함되지 않았다. 따라서 baseline 승인 사실과 head 전이는 transcript로 대조할 수 있지만, 이 bundle만으로 baseline candidate 서명을 독립 재검증하지는 못한다. P2와 rollback 후보는 candidate가 포함되어 독립 재검증했다.

---

## 3. 두 VM race 준비시험 — 22회

공개 결과 bundle:

- 파일명: `public-results.zip` (batch-02)
- SHA-256: `2dc8dceae038b7d1ffe680746da528a5004449ae0d174a34717070185e03daf2`
- 계획 22회 / 통과 22회
- schedule quality 22/22
- server-processing interval overlap 8/22
- double accept 0
- aborted 없음

이 준비시험은 매 trial 실제 VirtualBox restore를 수행하지 않는다.

---

## 4. 두 VM race 본시험 — 220회

공개 결과 bundle:

- 파일명: `public-results.zip` (batch-03)
- ZIP SHA-256: `66b4f0d759d1b23cac6dbf25a502b08b912863c1602e0d5a3a07ea5e04d92a02`
- 실행 revision: `f9848ae8cd7b4db6c90634b565205b3df9da8a39`
- 계획 220회 / 통과 220회
- Fresh 110회 / Shared 110회
- A 승리 112회 / B 승리 108회
- server-processing interval overlap 66/220
- schedule quality 220/220
- aborted 없음
- double accept 0

### 4.1 독립 감사 결과

ZIP의 자체 `summary.json`을 신뢰값으로 사용하지 않고, 공개 원본을 다시 계산했다.

| 항목 | 독립 감사 결과 |
|---|---:|
| Trial | 220 / 220 일관 |
| Candidate | 440 |
| Ed25519 서명 | 440 / 440 검증 |
| Evidence ID | 440 / 440 재계산 일치 |
| 상태전이 hash | 440 / 440 재계산 일치 |
| 전송 성공 | 440 / 440 |
| 승인 | 220 |
| 거절 | 220 |
| `EXECUTED_SIMULATED` | 220 |
| `BLOCKED` | 220 |
| Fresh loser = `ROLLBACK_OR_LOSING_FORK` | 110 / 110 |
| Shared loser = `CHALLENGE_USED` | 110 / 110 |
| Final canonical head | 220 / 220 승인 successor와 일치 |
| Double accept | 0 |
| 누락/중복 trial | 0 |
| Schedule quality | 220 / 220 |
| Observed server interval overlap | 66 / 220 |

### 4.2 독립성·다양성 검사

- trial별 시험 public key: 220/220 고유
- 초기 canonical state: 220/220 고유
- challenge: 330/330 고유
- evidence: 440/440 고유
- entropy commitment: 440/440 고유
- request ID: 중복 없음
- controller/worker가 보고한 7개 실행 파일 SHA-256: 서로 일치

`snapshot_source_revision`은 batch candidate에서 `UNKNOWN`으로 기록됐다. 실행 파일 hash 동일성은 확인되지만 이 provenance 공백은 그대로 공개한다.

### 4.3 시간 품질

독립 재계산에서:

- 최대 `send_lateness_ms`: 약 **18.29 ms**
- 최대 clock calibration RTT: 약 **11.26 ms**

실험 중단 기준인 100 ms / 200 ms 이내였다.

### 4.4 overlap 해석

`server_intervals_overlap=true`는 두 요청의 `request_received_monotonic_ns`~`decision_monotonic_ns` 구간이 같은 server instance 안에서 겹쳤다는 뜻이다.

이는 두 요청이 서버에서 동시에 진행되거나 한 요청이 다른 요청의 직렬화 구간을 기다렸다는 관측 근거다. **두 CAS 임계 구역이 동시에 실행됐다는 뜻은 아니다.**

따라서 정확한 보고 문구는:

> 220/220 trials preserved the single-successor invariant; 66/220 trials had overlapping observed server-processing intervals.

이지,

> 220 trials were all simultaneous critical-section races.

가 아니다.

---

## 5. 현재 A3에서 지지되는 결론

현재 증거는 두 축이 서로 보완한다.

1. **Actual restore path:** 이미 canonical P2로 전진한 registry는 과거 P1 VirtualBox 상태에서 나온 유효 서명 후보를 `ROLLBACK_OR_LOSING_FORK`로 차단했고 P2 head를 유지했다.
2. **Repeated two-worker race path:** 220개의 독립 trial에서 동일 predecessor로부터 나온 두 signed successor 중 정확히 하나만 canonical continuation으로 승인됐다.

따라서 현재 지지 가능한 좁은 문장은 다음과 같다.

> Under the declared L1 trust assumptions and one consistent online registry view, the tested IEPP implementation preserved a single canonical successor under repeated signed fork races, and a restored stale VM state did not roll back an already advanced canonical head.

이것은 **정책 상대적 canonical continuation** 결과다. clone의 내재적·물리적·형이상학적 “원본”을 판별했다는 주장이 아니다.

---

## 6. 다음 검증 우선순위

A3 동일조건 반복 수를 단순히 더 늘리는 것보다 아래 경계를 강화하는 편이 정보가치가 높다.

1. restart를 가로지르는 durable one-time challenge
2. registry rollback / split-view / equivocation 감지
3. key+state compromise 이후 recovery·revocation
4. TPM/TEE/secure-element 기반 L2 key/state 보호 및 attestation
5. 독립 연구자의 동일 실험 재현

---

## 7. 재현 관련 파일

- `docs/A3_VirtualBox_Runbook_KO.md`
- `docs/A3_Race_Batch_KO.md`
- `reference/iepp_vnext/a3_vm_runner.py`
- `reference/iepp_vnext/a3_race_batch.py`
- `reference/iepp_vnext/a3_registry.py`

원본 public ZIP은 private key·DB·bearer token이 포함된 private workspace와 분리해서 보존한다.
