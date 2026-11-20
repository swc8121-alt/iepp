# IEPP L2 VirtualBox 배치 — v0.2.3 실제 VM 최종 검증 보고서

> **명칭 주의:** `L2 VirtualBox runner`는 도구·워크스트림 이름입니다. 이번 실행의 관측 수준은 `VM_OBSERVED`이지만, 보안 주장 수준은 `L1_REGISTRY_RELATIVE_CONTINUATION`입니다.

## 최종 판정

2026년 10월 22일 KST에 공개 준비된 v0.2.3 정확 패키지를 Windows 10 호스트와 Ubuntu 24.04 게스트에서 실행했습니다. 22개 시험이 모두 통과했고, 증거 ZIP의 파일 해시·연결 해시·전이 digest·레지스트리 판정을 별도 코드로 재계산한 결과도 모두 일치했습니다.

**판정: 범위 제한 PASS**

- 관측 수준: `VM_OBSERVED`
- 보안 주장 수준: `L1_REGISTRY_RELATIVE_CONTINUATION`
- 실제 VM 실행: `true`
- 결과: 22/22
- v0.2.3 정확 러너 해시 일치: 예

이 결과는 실제 VirtualBox 스냅숏 복원과 L1 레지스트리 판정 경로를 검증합니다. 물리적·원본 런타임 식별, 복제 저항, 하드웨어 신뢰루트 또는 엔트로피의 독자적 우월성을 증명하지는 않습니다.

## 증거 식별자

| 항목 | 값 |
|---|---|
| 실행 ID | `l2-20261022034842-d78a5cb2` |
| 실행 완료 | 2026-10-22 13:10:44 KST |
| 증거 ZIP SHA-256 | `3ea76709a9db6a8b5d9044ee59a9a72fc275f677bf230e40cfd8d094398b207c` |
| 증거 체인 head | `0dc34b7d6429ee3d99e9f89cf5dfd0efd360bd409318e81f67ac250510e6f197` |
| v0.2.3 패키지 SHA-256 | `c63e1c516b36a7bc02e768452674accee31dd3b256733ca42ee8394d9f5b7b4d` |
| 실행 러너 SHA-256 | `7af548c5dee3943e16d393cb7d0741cd33d7eb2f318bd1308c7e256f31c6f6ab` |
| manifest SHA-256 | `e6edafeb94155f364b7e4bf61ba59ee56e022a82142f50ccf3ad76eddfd80f01` |
| guest probe SHA-256 | `b20dbd3ea6609475051b8e931ac86be26b6877846ecd327515ff899413096080` |

## 실행환경

| 항목 | 값 |
|---|---|
| 호스트 | Windows 10 `10.0.19045`, x64 |
| VirtualBox | `7.2.16r174877` |
| 게스트 | Ubuntu 24.04 LTS, Linux `6.8.0-147-generic` |
| Guest Additions | `7.2.16` |
| 게스트 Node | `v22.23.4`, `/snap/node/current/bin/node` |
| genesis 스냅숏 | `iepp-l2-genesis-b20dbd3ea6-v023` |
| 스냅숏 UUID | `974cddc8-1338-4fd5-9c3c-2b22d024d09a` |
| 이전 스냅숏 재사용 | 아니오 |

37개 부팅 세션이 모두 준비됐습니다. 러너 기준 부팅 준비시간은 최소 27.150초, 중앙값 28.627초, 최대 38.413초, 평균 29.014초였습니다. 전체 명령 로그 구간은 약 22.04분입니다.

## 독립 검증 결과

| 검증 항목 | 결과 |
|---|---:|
| 내부 파일 SHA-256 | 3/3 일치 |
| 시험 연결 해시 | 22/22 일치 |
| transition digest 재계산 | 40/40 일치 |
| 레지스트리 판정 재계산 | 40/40 일치 |
| 시험 pass 조건 재계산 | 22/22 일치 |
| 고유 challenge | 36개 |
| 의도된 exact-replay 중복 | 4쌍 |
| 실제 스냅숏 복원 | 36/36 |
| VM 시작·게스트 준비 | 37/37 |
| v0.2.3 전용 genesis 생성 | 1/1 |
| 총 기록 명령 | 763개 |

상태값이 0이 아닌 명령 311개는 모두 `guest_readiness_probe` 단계의 재시도 허용 항목이었습니다. 스냅숏 생성·복원, VM 제어, guest probe 실행 등 다른 명령의 실패는 없었습니다. 명령 로그에는 VM 원문 이름과 암호 파일 경로가 남지 않았습니다.

## 시나리오 결과

| 시나리오 | 결과 | 해석 |
|---|---:|---|
| 정상 연속 | 4/4 | 첫 후속자 승인 |
| 승인 뒤 과거 스냅숏 복원 | 4/4 | stale predecessor 거절 |
| 동일 전이 재전송 | 4/4 | challenge replay 거절 |
| 동일 스냅숏의 두 후속자 | 6/6 | 직렬 제출에서 하나만 canonical |
| 현재 자격증명 복제본 선점 | 4/4 | 복제본 승인 후 정상 후보 거절 |

마지막 항목은 중요한 음성 결과입니다. 현재 head·상태·자격증명을 공유한 복제본이 먼저 제출하면 L1 레지스트리는 이를 원본 실행체와 구별하지 못합니다. 따라서 확인된 것은 “원본 런타임”이 아니라 “레지스트리가 먼저 승인한 canonical successor”입니다.

## 주장 경계

이번 결과가 직접 뒷받침하는 내용:

1. v0.2.3 러너가 선언된 환경에서 실제 VM 스냅숏 생성·복원과 증거 생성을 완주합니다.
2. 시험한 직렬 제출에서 외부 L1 판정 상태가 stale predecessor와 replay를 거절합니다.
3. 하나의 predecessor에 대해 레지스트리가 둘 이상의 canonical successor를 승인하지 않았습니다.
4. 실행 번들의 출처 해시와 증거 체인을 사후 독립 검증할 수 있습니다.

이번 결과가 뒷받침하지 않는 내용:

- 물리적 또는 원본 런타임 식별
- 현재 자격증명을 공유한 복제본의 선제 제출 탐지
- TEE·TPM·PUF 또는 하드웨어 키 격리
- 분산 레지스트리 합의
- 키 탈취 뒤 복구·재앵커링
- 암호학적 게스트 인증
- 엔트로피가 기존 nonce·해시·레지스트리보다 제공하는 독립 보안 이점
- 생산환경 준비성 또는 일반적 무결성 보장

guest probe의 `probe_instance_id`는 genesis에서 생성되어 스냅숏과 함께 복원됩니다. 매 transition의 별도 intrinsic entropy 효과를 비교한 실험이 아니므로, 본 결과는 엔트로피/TRP 핵심 가설의 최종 검증이 아니라 A3 시스템·위협모델 검증으로 분류합니다.

## A3 완료 범위와 잔여 항목

v0.2.3 정확 패키지의 22회 실제 VM 실행 게이트는 완료했습니다. 그러나 Issue #6의 A3 전체 항목을 모두 완료로 처리하지는 않습니다. 다음이 남아 있습니다.

- A→B와 B→A 두 제출 순서의 완전한 대칭 시험
- 실제 제어된 동시 race
- 스냅숏 복원 전·후에 발급한 challenge 비교
- entropy-health 및 fault-injection과의 분리 시험
- 네트워크 경계의 독립 레지스트리 어댑터

## 연구·특허·표준화 반영

- 논문: “VM-observed execution”과 “L1 registry-relative security claim”을 별도 표로 제시합니다.
- 논문: clone-first 4/4를 숨기지 않고 L1 한계와 하드웨어 anchor의 필요성을 설명합니다.
- 특허: VM 복원 자체보다 신규 challenge, 직전 canonical commitment, 경쟁 후속자 판정, 외부 기준점의 결합을 중심으로 기술합니다.
- 실험: 다음 단계는 동시 race 보완 후 A4 entropy fault-injection입니다.
- 표준화: credential possession, platform attestation, execution-lineage continuity를 서로 다른 claim으로 유지합니다.

## 공개 반영 권고

1. v0.2.3 소스·패키지·증거 ZIP·이 보고서를 하나의 변경 세트로 보존합니다.
2. PR #19에는 정확 패키지 22회 실행 완료만 체크하고, 미실행 A3 세부항목은 열어 둡니다.
3. PR #20의 L1 한계·Astra 관찰과 이번 VM 관측 결과를 서로 다른 증거 계층으로 유지합니다.
4. 홈페이지에는 “실제 VM 22/22”와 함께 `L1_REGISTRY_RELATIVE_CONTINUATION` 경계를 같은 화면에 표시합니다.


## 공개 파일 및 재검증

- 러너 소스: [`experiments/l2-virtualbox/`](../experiments/l2-virtualbox/)
- 정확 패키지: [`iepp-l2-virtualbox-runner-v0.2.3.zip`](../experiments/l2-virtualbox/releases/iepp-l2-virtualbox-runner-v0.2.3.zip)
- 실제 VM 증거: [`iepp-l2-v023-actual-vm-evidence-20261022.zip`](../evidence/a3-v023/iepp-l2-v023-actual-vm-evidence-20261022.zip)
- 독립 감사 요약: [`iepp-l2-v023-actual-vm-audit-summary.json`](../evidence/a3-v023/iepp-l2-v023-actual-vm-audit-summary.json)
- 독립 감사 코드: [`audit-v023.mjs`](../evidence/a3-v023/audit-v023.mjs)
- 기계 판독 상태: [`status.json`](../evidence/a3-v023/status.json)

증거 ZIP을 푼 디렉터리를 첫 번째 인수로 주고 다음처럼 다시 계산할 수 있습니다.

```bash
node evidence/a3-v023/audit-v023.mjs <evidence-directory> \
  7af548c5dee3943e16d393cb7d0741cd33d7eb2f318bd1308c7e256f31c6f6ab \
  e6edafeb94155f364b7e4bf61ba59ee56e022a82142f50ccf3ad76eddfd80f01 \
  b20dbd3ea6609475051b8e931ac86be26b6877846ecd327515ff899413096080
```
