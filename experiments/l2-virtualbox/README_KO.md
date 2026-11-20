# IEPP L2 VirtualBox 22회 배치 러너

이 패키지는 실제 VirtualBox VM의 게스트 상태를 스냅숏으로 되돌린 뒤, VM 밖의 레지스트리 기준점이 롤백·재전송·경쟁 후속자를 어떻게 판정하는지 기록합니다.

버전: **v0.2.3** — Windows 호스트 + Ubuntu/Linux·Windows 게스트 자동 감지

v0.2.3은 실제 VM 자격시험에서 확인된 현장 수정을 정식 소스에 고정합니다. 게스트 Node 인수 중복을 제거하고, `guestcontrol copyto`에 원본·목적지를 명시하며, VM 부팅 준비 대기시간을 60초에서 180초로 늘렸습니다. Ubuntu에서는 `/usr/bin/node`와 `/snap/node/current/bin/node`를 자동 탐색합니다. 이전 러너의 genesis를 재사용하지 않도록 스냅숏 이름에 러너 버전을 포함하며, Guest Additions 버전, 게스트 커널·런타임, 스냅숏 UUID, 부팅 준비시간 통계를 증거에 자동 기록합니다.

## 가장 쉬운 실행 순서

1. ZIP을 새 폴더에 풉니다.
2. `CHECK_IEPP_L2.cmd`를 실행해 호스트 준비상태와 VM 목록을 확인합니다.
3. 시험용 Ubuntu/Linux 또는 Windows VM에 VirtualBox Guest Additions와 Node.js 22 이상이 설치됐는지 확인합니다.
4. `START_IEPP_L2.cmd`를 실행합니다.
5. 화면에 표시된 VM 이름, VM 내부 시험용 계정명, 암호를 입력합니다.
6. 완료되면 자동으로 열린 `evidence-vm-*` 폴더 전체를 보존합니다.

암호는 실행 중 임시 파일로만 사용하고 종료 시 삭제합니다. 결과 번들과 명령 로그에는 암호와 암호 파일 경로를 기록하지 않습니다.

## 주장 범위

- 확인 대상: VM 스냅숏 복원, stale predecessor 거절, 단일 canonical successor, 현재 자격증명 복제본의 선착순 한계
- 확인하지 않는 것: 물리적 원본성, TEE·TPM·PUF, 키 추출 저항, 복제 불가능한 런타임 신원
- VM 복원 여부는 관측 수준이고 보안 주장은 별개입니다. `summary.json`은 이를 `observation_level`과 `claim_level`로 분리해 기록합니다.
- `--dry-run` 결과는 러너 검증일 뿐 VM 증거가 아닙니다. `actual_vm_executed`가 `true`여도 보안 결론은 `L1_REGISTRY_RELATIVE_CONTINUATION`으로 제한합니다.

## 준비

1. Windows 호스트에 Oracle VM VirtualBox와 `VBoxManage`를 설치합니다.
2. 시험용 Ubuntu/Linux 또는 Windows VM에 VirtualBox Guest Additions와 Node.js 22 이상을 설치합니다.
3. VM에 시험 전용 로컬 계정을 만듭니다. Ubuntu VM의 계정명은 로그인 뒤 `whoami`, Windows VM은 `echo %USERNAME%`로 확인할 수 있습니다. 원클릭 런처는 암호를 화면에 표시하지 않고 입력받아 실행 종료 시 임시 파일을 삭제합니다.
4. 중요한 업무 VM이 아닌 폐기 가능한 시험 VM을 사용합니다. 러너가 VM을 종료하고 스냅숏을 복원합니다.

## 사전 드라이런

```powershell
node .\run.mjs --dry-run --output .\evidence-dry-run
node .\verify-bundle.mjs .\evidence-dry-run
```

## 실제 VirtualBox 실행

```powershell
node .\run.mjs `
  --vm "IEPP-L2" `
  --guest-user "iepp-test" `
  --password-file "C:\secure\iepp-l2-password.txt" `
  --guest-os auto `
  --output ".\evidence-vm"

node .\verify-bundle.mjs .\evidence-vm
```

VM 이름은 원문 대신 SHA-256으로만 보고서에 남고, 암호 파일 경로는 명령 로그에서 가려집니다. 암호 내용은 증거 번들에 기록하지 않습니다.

`--guest-os auto`는 VirtualBox의 VM 운영체제 유형을 읽어 Linux와 Windows를 구분합니다. Linux Node는 `/usr/bin/node`, `/snap/node/current/bin/node` 순서로 확인하고 작업 폴더는 `/home/<계정명>/IEPP-L2`를 사용합니다. Windows 기본값은 `C:\Program Files\nodejs\node.exe`와 `C:\IEPP-L2`입니다. 자동 감지가 실패할 때만 `--guest-os` 또는 `--guest-node`를 직접 지정하십시오.

## 정지 조건

다음 중 하나라도 발생하면 러너는 결과를 성공으로 만들지 않고 즉시 중단합니다.

- VirtualBox·VM·Guest Additions·게스트 Node 확인 실패
- 180초 안에 게스트 프로브 준비 실패
- 스냅숏 생성 또는 복원 실패
- 22개 중 하나라도 기대 판정과 불일치
- 증거 파일 해시 또는 JSONL 체인 불일치

## 결과 파일

- `summary.json`: 실행환경, 실제 VM 여부, Guest Additions·게스트 런타임·스냅숏 UUID·부팅 통계, 시나리오별 통과 수, 주장 경계
- `trials.jsonl`: 22개 시험의 후보·판정과 연결 해시
- `commands.jsonl`: 암호를 제거한 호스트 명령 기록
- `integrity.json`: 결과 파일 SHA-256과 증거 체인 head
- `REPORT_KO.md`: 사람이 읽는 요약

VirtualBox 명령은 Oracle VM VirtualBox 매뉴얼의 `VBoxManage snapshot` 및 `VBoxManage guestcontrol` 구조를 따릅니다. 버전 차이가 있으면 `node run.mjs --help`와 설치된 `VBoxManage --help`를 함께 확인하십시오.

## 증거 승격 규칙

실제 VM에서 먼저 성공한 v0.2.2 작업본은 v0.2.3 수정의 자격 근거이지만, v0.2.3 공개 패키지 자체의 최종 증거는 아닙니다. 최종 증거로 승격하려면 새 v0.2.3 ZIP을 새 폴더에 풀어 22회를 다시 실행하고, 생성된 `source_hashes.runner_sha256`와 공개 패키지 안 `run.mjs`의 SHA-256가 일치해야 합니다.
