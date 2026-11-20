# A3 다음 실행: 승인된 P1 저장과 복원

상태: 코드·HTTP 통합 검증 완료, 사용자 VirtualBox 실행 대기.
이 변경은 2026-09-14 결과의 실행 버전과 분리한다. 기존 스냅샷·로그·lab-01~04 디렉터리를 보존한다.

## 추가된 기능

`export-snapshot`은 원래 시험용 snapshot, 서명된 candidate, 해당 candidate의 단일 승인 log record, 현재 온라인 registry head를 대조한다. 키 지문·서명·전이 commitment·counter·sid/domain/key_id·이전 상태·결과 ID와 승인 head가 일치해야 새 파일을 생성한다. 이미 존재하는 출력 파일은 교체하지 않는다. POSIX에서는 파일 권한을 0600으로 생성하며 stdout에는 비밀키를 출력하지 않는다. Windows에서는 사용자 디렉터리의 ACL을 따른다.

등록 서버는 신뢰하는 L1 시험 서버다. head HTTP 응답은 인증서 또는 attestation이 아니며, 조회 직후 다른 분기가 진행하면 내보낸 상태가 stale해질 수 있다. 시험 중 다른 제출을 중지한 상태에서 export한다. 이 명령 자체는 VirtualBox 스냅샷을 만들거나 복원하지 않는다.

`git_revision()`은 현재 shell 위치 대신 실행 코드 디렉터리에서 버전을 읽는다. 새 candidate의 `iepp_source_revision`은 실제 실행 코드 버전이고, 원래 snapshot의 버전은 `snapshot_source_revision`에 보존된다. 이전 UNKNOWN 로그는 변경하지 않는다.

## 서버 시각 기록

새 `registry_timing` 객체가 server transition event, HTTP decision, client submit 결과에 공통으로 포함된다.

| 필드 | 의미 |
|---|---|
| server_instance_id | 서버 engine를 시작할 때 생성되는 식별자 |
| request_id | 검증 호출마다 서버가 생성하는 식별자 |
| request_received_monotonic_ns | HTTP handler 진입 시각; 헤더 파싱 이후, body 읽기 이전 |
| body_complete_monotonic_ns | body 파싱 이후 검증 호출 직전 |
| verification_requested_monotonic_ns | engine 검증 호출 진입 |
| lock_acquired_monotonic_ns | 직렬화 lock 획득 |
| decision_monotonic_ns | 판정 객체 생성; 로그 기록·응답 전송 이전 |

engine 직접 호출은 HTTP 수신/body 필드가 null이다. monotonic 시각은 동일 server_instance_id 안에서만 비교한다. `verification_requested`~`decision` 구간이 겹치면 서버에서 두 요청이 진행 중이거나 기다렸다는 증거다. 이는 두 CAS 임계 구역이 동시에 실행됐다는 뜻이 아니다. wall clock 또는 서로 다른 VM의 send 시각을 빼서 동시성을 단정하지 않는다. malformed HTTP 요청은 정상 transition 표본에 포함하지 않는다.

## 노트북에 설치할 위치

- Node3: SSH 2224 / 192.168.56.12 / 시험 분기 A.
- Node4: SSH 2225 / 192.168.56.13 / 시험 분기 B.
- VM 새 코드: `/home/iepp/iepp-a3-next`. 기존 `/home/iepp/iepp`와 venv는 보존한다.
- VM Python: `/home/iepp/iepp/.venv/bin/python`으로 새 코드 파일의 절대 경로를 실행한다.
- Windows 새 코드 디렉터리: `C:\Users\user\IEPP-Lab\a3-next-code`.
- Windows 새 상태: `C:\Users\user\IEPP-Lab\a3-vm-lab-05`. 기존 디렉터리 재사용·`--force` 금지.
- 새 host-only 서버 포트 후보: 8047. 실제 사용 중인지 먼저 확인한다.

코드 설치는 게시된 새 커밋을 양쪽 VM과 Windows에 동일하게 고정한다. 기존 서버를 종료하기 전에 lab-01~04의 event log를 수집한다. 실험은 새 lab-05 서버에서 진행한다. 당시 기록이 없는 이전 시험은 '원문 없음'으로 남긴다.

## 첫 실제 VM 실행 순서

1. Node3·Node4 접속과 IP를 확인하고 새 코드 작업 디렉터리를 만든다. Windows와 VM의 다섯 실행 파일 해시를 대조한다. baseline은 Node3만 제출한다.
2. Windows에서 새 lab-05를 prepare하고 8047 서버를 실행한다. `snapshot.json`만 Node3로 복사한다. 비밀키 파일은 공개 업로드하지 않는다.
3. Node3에서 `A3-P1-BASELINE-0001` candidate를 만들고 제출하여 P0→P1 승인을 확인한다. 새 결과·candidate 파일명을 사용한다.
4. 아래 명령으로 승인된 P1을 새 파일로 저장한다. 거절·전송 실패·현재 head 불일치는 export 실패가 정상이다.

```bash
~/iepp/.venv/bin/python ~/iepp-a3-next/reference/iepp_vnext/a3_vm_runner.py export-snapshot \
  --snapshot ~/a3-snapshot-05.json \
  --candidate ~/candidate-P1-baseline-0001.json \
  --log ~/result-P1-baseline-0001.jsonl \
  --registry-url http://192.168.56.1:8047 \
  --output ~/a3-accepted-P1-05.json
```

5. stdout의 counter=1과 head, 서버의 last_evidence_id를 확인한다. Node3를 정상 종료하고 `A3_P1_ACCEPTED_05`라는 **실제 VirtualBox 스냅샷**을 만든다. UUID와 시각을 기록한다. 서버는 계속 실행한다.
6. 해당 스냅샷을 실제 restore한 뒤 P1 파일에서 새 challenge로 candidate를 만들어 P1→P2 정상 승인을 확인한다. 레지스트리 counter=2와 head를 기록한다.
7. Node3를 다시 종료하고 같은 P1 VM 스냅샷으로 복원한다. 서버의 P2는 유지한다. 새 challenge로 P1 기반 candidate를 제출하여 `ROLLBACK_OR_LOSING_FORK`와 P2 head 불변을 확인한다. 복원으로 사라질 candidate·로그는 **각 복원 전에 Windows로 복사**한다.
8. 이후 새 격리 상태에서 shared challenge B→A, challenge 소비 후 명시적 restore, 경쟁 제출 순으로 진행한다. 이전 P0·04b 파일은 이 신규 사례에 재사용하지 않는다.

시험 ID·파일 경로를 실제 안내와 맞추고 한 단계씩 실행한다. 이 문서의 예시 파일은 자동 생성된 상태가 아니므로 준비 없이 export 명령만 실행하지 않는다.

## 검증 기록

로컬 `python -m unittest discover -s reference/iepp_vnext/tests -v`: 25개 통과.
추가 5개 검증은 실제 loopback HTTP registry를 사용하여 P1 export→P2 정상 진행→복사해 둔 P1 재제출 차단, 입력 변조 및 head 불일치 거절, 중복 로그·기존 출력 거절, shared B→A 차단, 요청 대기 구간 기록과 서버/응답 일치를 검사한다. 이 중 복사한 JSON 상태는 VM restore 증거로 집계하지 않는다.

이 검증에는 실제 VirtualBox 조작이 없다. 노트북의 22회 준비 점검이나 220회 본시험을 수행한 것으로 계산하지 않는다. 클론의 내재적 원본, entropy 품질, durable challenge across restart 및 L2 보호는 이 변경의 보장에 포함하지 않는다.
