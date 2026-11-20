# IEPP A3 2-VM 경쟁 시험 증거 검토 기록

- 검토일: 2026-10-27
- 대상 증거: `evidence-vm-20261027-140157.zip`
- 실행 ID: `a3-20261027050157-222dfc76`
- 실행기 버전: `0.2.4.2`
- 판정: **검증 통과**
- 주장 수준: `L1_REGISTRY_RELATIVE_CONTINUATION`
- 관찰 수준: `TWO_VM_OBSERVED`

## 1. 결론

제출된 증거 묶음은 구조·해시·증거 체인·시험별 의미 조건을 모두 통과했다. Windows 10 호스트의 Oracle VM VirtualBox 7.2.16에서 서로 다른 Ubuntu 24.04 VM 두 개와 별도 Node.js HTTP 레지스트리 프로세스를 사용한 실행으로 기록되어 있다. 22개 시험이 모두 통과했으며, 42개 레지스트리 사건과 8개 동시 경쟁 시험이 원시 기록에서 확인됐다.

이 결과는 **동일한 전임 상태에서 경쟁하는 두 후보 가운데 레지스트리가 canonical successor 하나만 승인하고, 사용된 challenge의 재사용을 거부했다**는 L1 관찰을 뒷받침한다. 물리적 원본 런타임의 식별, 복제 불가능성, PUF·TEE 기반 하드웨어 신원, 분산 합의, 독립 엔트로피의 효과는 이 시험의 결론에 포함되지 않는다.

## 2. 검토 방법과 결과

| 검토 항목 | 결과 | 확인 내용 |
|---|---:|---|
| ZIP 구조 안전성 | 통과 | 7개 파일, 절대경로·상위경로 이동 항목 없음 |
| 제공 검증기 | 통과 | `verify-bundle.mjs` 종료코드 0 |
| 핵심 파일 SHA-256 | 통과 | `integrity.json`에 기록된 4개 해시와 실제 바이트 일치 |
| trial 증거 체인 | 통과 | 22개 `evidence_prev_hash` 연결과 최종 head 재계산 일치 |
| 원시 레지스트리 사건 | 통과 | 42개, request ID 중복 없음, candidate digest 일치 |
| trial-사건 대응 | 통과 | 42개 embedded event의 서버 필드와 원본 event가 일치 |
| 시나리오 의미 재판정 | 통과 | 보고된 `pass`를 사용하지 않고 22개 모두 조건 충족 확인 |
| 경쟁 실행 | 통과 | 8/8 서버 처리 구간 겹침, 8/8 단일 승인, CAS 겹침 0/8 |
| 실행기 소스 고정 | 통과 | evidence의 소스 해시 5개가 보관된 v0.2.4.2 소스와 일치 |
| VM 구분 | 통과 | VM 이름 해시 2개가 서로 다르고 실제 시험 대상 이름과 일치 |
| 자격증명 노출 검사 | 통과 | private key·API token·평문 비밀번호 패턴 없음; password-file 값은 전부 `<redacted>` |

## 3. 시나리오 결과

| 시나리오 | 목적 | 결과 |
|---|---|---:|
| `r1_baseline_continue` | 정상 단일 후속자 승인 | 2/2 |
| `r2_fresh_order_ab` | 서로 다른 challenge, A 선행 | 3/3 |
| `r3_fresh_order_ba` | 서로 다른 challenge, B 선행 | 3/3 |
| `r4_controlled_race_fresh` | 서로 다른 challenge의 동시 경쟁 | 4/4 |
| `r5_shared_challenge_ab` | 동일 challenge, A 선행 | 2/2 |
| `r6_shared_challenge_ba` | 동일 challenge, B 선행 | 2/2 |
| `r7_controlled_race_shared_challenge` | 동일 challenge의 동시 경쟁 | 4/4 |
| `r8_consumed_before_restore` | 복원 전 승인 상태가 복원 후에도 레지스트리에 유지되는지 확인 | 2/2 |

순서 편향을 확인하기 위해 A→B와 B→A를 모두 실행했다. 순차 fork 시험에서는 첫 후보만 승인되고 둘째 후보는 `FORK_CONFLICT`로 거부됐다. 동일 challenge 시험에서는 첫 사용만 승인되고 재사용 후보는 `CHALLENGE_REPLAY`로 거부됐다.

경쟁 시험 8회에서는 두 요청의 **서버 처리 시간 구간**이 모두 겹쳤다. CAS 임계구역 자체의 겹침은 0회였으며 이는 원자적 직렬화와 일치한다. 따라서 “동시에 도착한 경쟁 요청이 실제로 관찰됐고, 원자적 판정 구간에서 한 후보만 승인됐다”가 정확한 표현이다.

## 4. 실행환경과 운영 증거

| 항목 | 관찰값 |
|---|---|
| 호스트 | Windows 10.0.19045, x64 |
| 하이퍼바이저 | Oracle VM VirtualBox 7.2.16r174877 |
| VM | 서로 다른 VM 2개, 서로 다른 snapshot UUID |
| 게스트 A | Ubuntu 24.04 LTS, Linux 6.8.0-147-generic, Node.js v22.23.4 |
| 게스트 B | Ubuntu 24.04 LTS, Linux 6.8.0-142-generic, Node.js v22.23.4 |
| 레지스트리 | 별도 Node 프로세스, HTTP/1.1, localhost 임시 포트 |
| 성공한 snapshot restore | 46회 |
| 성공한 VM start / shutdown | 각 48회 |

명령 기록에는 guest readiness 대기 중 상태코드 1이 313회, VM 상태 전환 확인 중 상태코드 1이 5회 남아 있다. 전부 `retry_allowed=true`인 폴링 단계였으며 이후 성공했다. 시험 판정 실패는 아니다. 다만 다음 재현 실행에서는 부팅 준비 시간과 retry 수를 별도 성능 지표로 집계하는 편이 좋다.

## 5. 무결성 기준값

### 전체 ZIP

`1918b5e44f66de5a0e31db67eb0a5bd35911cea0ec7fd5a2ccc720bd26779f54`

### 증거 체인 head

`947895864ebc515e2a769029683919430fee33a3ff6c86f2f198a7c04f51fe29`

### 핵심 파일

| 파일 | SHA-256 |
|---|---|
| `summary.json` | `2af10cfef40dca1e757e5af7c61c0c3eeb7d8c08adef7c157c264d9fe402bb76` |
| `trials.jsonl` | `e8db572fb8f574f74447dedcbf882c5bcfdbd1c55b76ff381849e1b02505de35` |
| `commands.jsonl` | `1957deb06cd7358a0e44cc5f92073b1919839be15397ca5c4095130fcaa0569d` |
| `registry-events.jsonl` | `c47995da0c8db5a8307a973ebef08ff2acc76f46afdc37065d5688560ad31d64` |

## 6. 주장 경계

이번 결과가 직접 뒷받침하는 주장은 다음과 같다.

> 두 개의 서로 다른 VM snapshot에서 생성된 경쟁 continuation 후보를 별도 HTTP registry가 관찰했으며, 동일 predecessor에 대해 하나의 canonical successor만 승인하고 challenge의 단일 사용을 강제했다.

이번 결과만으로 주장하면 안 되는 항목은 다음과 같다.

- 승인된 후보가 물리적 또는 역사적 “원본 런타임”이라는 주장
- VM 복제 자체를 방지하거나 복제본을 하드웨어 수준에서 식별했다는 주장
- PUF, TPM 또는 TEE를 사용했다는 주장
- guest 요청을 암호학적으로 인증했다는 주장
- registry 장애·분할·복제 환경에서 분산 합의를 달성했다는 주장
- intrinsic entropy가 판정 정확도를 독립적으로 높였다는 주장

현재 무결성 구조는 SHA-256 파일 해시와 연결 해시다. 보관 후 변경 탐지에는 유용하지만, 공격자가 묶음 전체를 다시 만들 수 있는 상황을 막는 서명이나 제3자 타임스탬프는 아니다.

## 7. 공개 전 개인정보 점검

평문 비밀번호, 개인키, API token, 실제 VM 이름은 발견되지 않았다. 다만 원본에는 다음 운영 메타데이터가 포함된다.

- 일반형 Windows 사용자 경로 `C:\Users\user`
- guest 계정명 `iepp`
- snapshot UUID 두 개
- 호스트·VirtualBox·Guest Additions·커널 버전
- localhost 주소와 임시 실행 정보

원본 증거는 비공개 원본으로 보존하는 것이 적절하다. 공개본이 필요하면 snapshot UUID와 로컬 경로를 제거한 **별도 공개용 파생본**을 만들고, 파생본에 새 해시·변경 목록을 붙여야 한다. 원본 파일을 직접 고치면 현재 무결성 검증이 깨진다.

## 8. 논문·특허·개발 반영 권고

1. 논문에는 A3를 “two-VM observed L1 registry-relative continuation experiment”로 기술하고 위 주장 문장을 그대로 사용한다.
2. 결과표에는 `22/22`, `42 events`, `8/8 processing overlap`, `8/8 single accept`, `0/8 CAS overlap`을 함께 제시해 동시성과 직렬화를 구분한다.
3. 특허·핵심 청구 서술은 challenge freshness, predecessor commitment, single-successor arbitration, replay rejection의 결합에 집중한다.
4. 다음 버전은 guest 요청 서명 또는 mTLS, 외부 timestamp/서명, 독립 장비에서의 재현 실행을 추가한다.
5. 그 다음 단계에서 registry 재시작·로그 손상·네트워크 분할·복구 거버넌스를 별도 시험한다.

## 9. 성숙도 판단

이 결과로 IEPP는 아이디어·시뮬레이션 단계에서 **실제 두 VM과 별도 레지스트리 경계를 사용한 재현 가능한 proof-of-concept 증거 단계**로 올라갔다. arXiv v1의 실험 근거로 사용할 수 있는 수준이다. 보안 제품 또는 표준 후보 수준으로 평가받으려면 암호학적 guest 인증, 서명된 증거 보존, 제3자 재현, 장애·분산 환경 시험이 추가로 필요하다.

---

검토 범위는 제출된 ZIP과 함께 보관된 v0.2.4.2 소스에 한정된다. 이 기록은 독립 제3자 인증서가 아니라, 원시 증거를 재계산하고 주장 범위를 제한한 기술 검토 기록이다.
