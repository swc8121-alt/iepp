# IEPP A3 VirtualBox 완결 시험기 v0.2.4.2

이 패키지는 서로 다른 두 개의 폐기 가능한 VirtualBox VM에서 같은 등록 상태를 만든 뒤, 별도 Node 프로세스로 실행되는 HTTP 레지스트리에 경쟁 continuation을 제출합니다. 총 22개 시험을 한 번에 실행하고 해시로 연결된 증거 번들을 생성합니다.

이 버전은 기존 배포물과 증거를 수정하지 않습니다. v0.2.4.2는 A3의 대칭 순서·실제 HTTP 경쟁·복원 전후 챌린지를 유지하면서, VM 종료 직후 VirtualBox의 direct session 잠금이 늦게 해제될 때 `showvminfo`가 일시 실패하는 현상을 최대 30초 동안 재확인하도록 보완했습니다. 두 번 연속으로 전원 종료 상태를 확인한 뒤 snapshot 복원을 계속합니다. 실패 기록 보존 기능도 그대로 유지합니다.

## 가장 쉬운 실행 순서

1. 중요한 작업용 VM이 아닌 폐기 가능한 Ubuntu VM 두 개를 준비합니다.
2. 두 VM 모두에 VirtualBox Guest Additions와 Node.js 22 이상이 설치되어 있어야 합니다.
3. 압축을 푼 Windows 폴더에서 `CHECK_IEPP_A3.cmd`를 먼저 더블클릭합니다.
4. 점검이 통과하면 `START_IEPP_A3.cmd`를 더블클릭합니다.
5. 화면에 보이는 정확한 VM A 이름과 VM B 이름, Ubuntu 계정명을 입력합니다.
6. 경고를 읽고 `RUN A3`를 정확히 입력한 뒤 Ubuntu 비밀번호를 입력합니다. 비밀번호는 화면에 표시되지 않습니다.
7. 완료되면 열린 `evidence-vm-날짜-시간` 폴더를 그대로 보존합니다.

실패하면 창이 유지되며, 패키지 폴더의 `IEPP_A3_LAST_ERROR.txt`와 evidence 폴더의 `console-transcript.txt`를 확인할 수 있습니다. 이 두 파일에는 비밀번호가 기록되지 않습니다.

VM이 하나뿐이라면 원본을 종료한 뒤 VirtualBox의 **복제(Clone)** 기능으로 두 개의 **전체 복제(Full Clone)** 를 만드십시오. 예시 이름은 `IEPP-A`, `IEPP-B`입니다. 네트워크 MAC 주소는 새로 생성하고, 원본은 시험에 사용하지 않는 것을 권합니다. v0.2.4.2 실행기는 자동으로 VM을 복제하거나 삭제하지 않습니다.

## 시험 중 일어나는 일

- 두 VM을 종료하고 v0.2.4.2 전용 genesis snapshot을 만들거나 재사용합니다.
- 각 trial마다 해당 snapshot을 복원합니다.
- VM A와 VM B 안의 probe가 독립적으로 continuation 후보를 생성합니다.
- 호스트 controller가 후보를 별도 HTTP 레지스트리 프로세스에 전송합니다.
- 경쟁 trial에서는 두 HTTP 요청이 서버에서 실제로 겹친 구간을 기록합니다.
- canonical-state 갱신 구간은 직렬화하며 predecessor별 승인 수가 1을 넘지 않는지 검증합니다.
- 시험이 끝나면 두 VM을 종료 상태로 둡니다.

서버가 기록하는 `server_processing_interval_overlap`은 요청 수신부터 CAS 결정 완료까지의 구간이 실제로 겹쳤다는 뜻입니다. CPU 명령 자체가 동시에 실행됐다는 주장이나 분산 합의의 증거가 아닙니다. `cas_interval_overlap`은 0이어야 합니다.

## 22개 trial 구성

| 그룹 | 수 | 확인 내용 |
|---|---:|---|
| R1 baseline | 2 | 정상 continuation 승인 |
| R2 fresh A→B | 3 | A 승인 후 B fork 거절 |
| R3 fresh B→A | 3 | B 승인 후 A fork 거절 |
| R4 fresh controlled race | 4 | 서로 다른 challenge의 동시 경쟁에서 하나만 승인 |
| R5 shared challenge A→B | 2 | B의 challenge 재사용 거절 |
| R6 shared challenge B→A | 2 | A의 challenge 재사용 거절 |
| R7 shared-challenge race | 4 | 동시 경쟁에서 하나만 승인되고 하나는 replay 거절 |
| R8 consumed before restore | 2 | 복원 전에 소비된 registry 상태가 VM 복원 뒤에도 유지됨 |

## 증거 파일

- `summary.json`: 실행 환경, 관측 수준, 주장 경계, 시나리오·경쟁 집계
- `trials.jsonl`: 22개 trial의 후보·결정·연결 해시
- `registry-events.jsonl`: 별도 HTTP 레지스트리가 기록한 요청 시각·CAS 시각·결정
- `commands.jsonl`: 비밀번호 경로와 VM 이름을 가린 실행 명령 기록
- `integrity.json`: 핵심 파일 SHA-256과 evidence-chain head
- `REPORT_KO.md`: 사람이 읽는 요약 보고서

`verify-bundle.mjs`는 파일 해시, trial 연결 체인, request ID 유일성, predecessor별 단일 승인, challenge first-use 단일성, 경쟁 구간 겹침과 CAS 비중첩을 다시 검사합니다.

## 주장 경계

실제 VM 시험이 22/22 통과해도 주장 수준은 다음으로 제한됩니다.

`L1_REGISTRY_RELATIVE_CONTINUATION`

즉, 하나의 레지스트리가 관측한 canonical predecessor에서 승인 가능한 successor가 하나였다는 증거입니다. 다음을 증명하지 않습니다.

- 어느 VM이 물리적 원본인지
- 복제가 불가능한지
- guest 후보가 암호학적으로 인증되었는지
- PUF, TEE, TPM 또는 하드웨어 신뢰루트를 사용했는지
- 분산 합의나 장애 복구가 안전한지
- 엔트로피가 독립적인 보안 이점을 제공했는지

## 명령줄 사용

드라이런은 VM 증거를 만들지 않습니다.

```powershell
node run.mjs --dry-run --output .\evidence-dry-run
node verify-bundle.mjs .\evidence-dry-run
```

고급 사용자는 서로 다른 guest 계정·OS·Node 경로를 `node run.mjs --help`에 표시된 A/B별 옵션으로 지정할 수 있습니다.

## 안전 주의

- 이 실행기는 VM 전원을 끄고 snapshot을 복원합니다.
- 중요한 VM, 업무 데이터가 있는 VM, 동기화 중인 VM에는 실행하지 마십시오.
- 자동화는 두 VM의 삭제나 원본 VM 복제를 수행하지 않습니다.
- 비밀번호는 임시 파일로만 전달하고 종료 시 삭제하지만, 시험 전용 계정을 사용하십시오.
