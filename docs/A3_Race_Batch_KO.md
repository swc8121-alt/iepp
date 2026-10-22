# A3 두 VM 경쟁 제출 반복 도구

이 도구는 두 VM에서 후보를 생성·서명하고 Windows의 단일 온라인 레지스트리에 제출한다.
매 회차 **새 실험 키, 초기 head, SQLite DB, challenge 저장소**를 사용한다.
기존 `a3_registry.py`의 판정·잠금·CAS 로직은 변경하지 않는다.
HTTP 제어 어댑터가 그 엔진을 호출한다. 이전 수동 실행과 HTTP 어댑터는 다르므로
실행 코드 해시와 도구 버전을 함께 보관한다.

## 범위와 계획

- `--repetitions 1`: fresh/shared 각 11개 지연 조합 = **22회** 준비 시험.
- `--repetitions 10`: 새 작업 폴더에서 **220회** 본시험. 준비 시험 검토 뒤 실행한다.
- `(A 지연 ms, B 지연 ms)`: `(0,0), (0,1), (1,0), (0,5), (5,0),
  (0,10), (10,0), (0,50), (50,0), (0,100), (100,0)`.
- 각 회차 DB와 키는 독립이며 다른 회차의 head를 이어 쓰지 않는다.
- 두 worker는 이미 실행 중인 VM을 사용한다. **회차마다 VirtualBox를 복원하지 않는다.**
  JSON 상태 배포 및 공유 challenge 조건을 새로운 실제 VM 복원 증거로 집계하지 않는다.
- L1, 협조적인 클라이언트, 모의 보호 동작만 검증한다. 내재적 원본, 엔트로피 품질,
  게이트 우회, L2 키 보호, 악성 네트워크 및 서버 자체 롤백은 범위 밖이다.
- 설정 지연은 목표값이며 실제 도착 순서를 보장하지 않는다. 잠금도 FIFO 보장이 아니다.

## 시간과 결과 판정

각 worker는 회차별 5회 왕복 측정 중 RTT가 가장 짧은 표본으로 서버 단조 시계와
자기 단조 시계의 차이를 추정한다. 두 후보가 준비된 뒤 서버는 3초 뒤 목표를 설정한다.
worker는 벽시계 대신 단조 시계로 대기한다. VM 시계나 NTP 설정을 바꾸지 않는다.
왕복 중간점 추정은 네트워크 비대칭·스케줄러 지연 때문에 정확한 동기화를 보장하지 않는다.
모든 표본 선택 결과, RTT, 목표 시각, 실제 전송 지각 시간을 보관한다.
최소 RTT >200ms 또는 로컬 목표 대비 지각 >100ms면 준비 품질 문제로 중단한다.

검사기는 각 회차의 서명된 후보, enrollment, 두 클라이언트 결과, 서버 원본 이벤트,
최종 head를 대조한다. 정확히 1회 승인·1회 모의 동작 실행, 상대 차단, counter=1,
유효 challenge, 올바른 fresh/shared 관계, 요청 ID와 시각 일치가 필요하다.
전송 실패·만료·누락·중복은 정상 차단으로 계산하지 않는다.

서버 처리 구간은 `request_received_monotonic_ns`부터 `decision_monotonic_ns`까지다.
두 구간의 교집합이 양수인 회차만 `server_intervals_overlap=true`로 집계한다.
겹치지 않은 회차도 단일 승인 불변식을 검사하되 동시 경쟁 성공 회차로 부르지 않는다.
이 구간의 겹침은 잠금 안에서 두 상태 갱신이 동시에 실행됐다는 뜻이 아니다.
`passed_trials`는 판정 불변식, `schedule_quality_ok_trials`는 예약 품질,
`overlap_trials`는 관측된 겹침 개수다. **22회 모두 통과와 22회 모두 겹침은 다르다.**

## 설치

새 Git worktree를 사용해 기존 실험 코드를 보존한다. 배포 시 안내받은 커밋을 고정한다.
Node3/Node4 모두 `~/iepp-a3-race/reference/iepp_vnext`에 같은 버전을 둔다.
Windows에는 SCP로 그 `iepp_vnext` 폴더 전체를
`$env:USERPROFILE\IEPP-Lab\a3-race-code`로 복사한다.
기존 가상환경 Python과 cryptography 의존성을 그대로 사용한다.
세 컴퓨터의 관련 Python 파일 7개 SHA-256이 일치하지 않으면 실행을 거절한다.
Git SHA가 UNKNOWN인 복사본도 파일 해시로 비교한다.

## Windows 준비 및 실행

아래는 **새 폴더** `a3-race-batch-01`, 포트 **8050** 예시다.

```powershell
& "$env:USERPROFILE\IEPP-Lab\iepp_vnext\.venv\Scripts\python.exe" "$env:USERPROFILE\IEPP-Lab\a3-race-code\iepp_vnext\a3_race_batch.py" prepare --workspace "$env:USERPROFILE\IEPP-Lab\a3-race-batch-01"
```

`private\worker-A.private.json`을 SCP 포트 2224로 Node3의
`~/a3-race-worker-A.private.json`에 복사하고,
`private\worker-B.private.json`을 포트 2225로 Node4의
`~/a3-race-worker-B.private.json`에 복사한다.
각 bundle은 실험용 개인키와 해당 branch 제어 토큰을 포함한다. 채팅/공개 저장소에 올리지 않는다.
서버는 키를 HTTP로 배포하지 않는다. HTTP bearer 제어 토큰은 암호화되지 않으므로
기존 A3와 같은 신뢰된 host-only 실험망에서만 사용한다.

```powershell
& "$env:USERPROFILE\IEPP-Lab\iepp_vnext\.venv\Scripts\python.exe" "$env:USERPROFILE\IEPP-Lab\a3-race-code\iepp_vnext\a3_race_batch.py" serve --workspace "$env:USERPROFILE\IEPP-Lab\a3-race-batch-01"
```

이 창은 `ready:true` 이후 두 worker를 기다린다. 두 VM을 다른 IP(.12/.13)로 유지한다.
같은 hostname은 허용하지만 같은 관측 주소에서 A/B를 실행하면 기본적으로 거절한다.
IP 구분은 하드웨어/VM attestation이 아니다. `--allow-same-host`는 loopback 통합 검사 전용이다.

## 두 Ubuntu worker

왼쪽 Node3(A, SSH 2224):

```bash
chmod 600 ~/a3-race-worker-A.private.json
~/iepp/.venv/bin/python ~/iepp-a3-race/reference/iepp_vnext/a3_race_batch.py worker --config ~/a3-race-worker-A.private.json --output ~/a3-race-output-A-01
```

오른쪽 Node4(B, SSH 2225):

```bash
chmod 600 ~/a3-race-worker-B.private.json
~/iepp/.venv/bin/python ~/iepp-a3-race/reference/iepp_vnext/a3_race_batch.py worker --config ~/a3-race-worker-B.private.json --output ~/a3-race-output-B-01
```

A가 먼저 실행되면 B를 기다린다. 매번 비밀번호를 다시 입력하지 않는다.
두 worker가 준비되면 자동으로 22회 실행되고 각 회차 결과가 표시된다.
클라이언트 후보·결과는 VM 로컬과 Windows public 폴더 양쪽에 보관된다.

## 완료, 실패, 보관

Windows 서버가 마지막에 `planned`, `passed_trials`, `overlap_trials`, `passed`를 출력한다.
`public-results.zip`에는 public 폴더만 담긴다. 원본 결과 검토에는 이 ZIP만 첨부한다.
개인키·DB·토큰이 든 private 폴더와 worker bundle은 공개하지 않는다.

```powershell
& "$env:USERPROFILE\IEPP-Lab\iepp_vnext\.venv\Scripts\python.exe" "$env:USERPROFILE\IEPP-Lab\a3-race-code\iepp_vnext\a3_race_batch.py" check --public "$env:USERPROFILE\IEPP-Lab\a3-race-batch-01\public"
```

불변식 실패·예약 품질 문제는 다음 회차로 진행하지 않는다. 누락된 결과도 checker에서 실패한다.
준비 후 두 worker 연결 대기는 최대 30분, 활성 회차는 최대 90초다.
네트워크 오류 발생 시 제출을 자동 재시도하지 않는다. 중복 제출로 결과를 흐리지 않기 위해서다.
서버를 중단하거나 재시작하면 같은 폴더에서 재개할 수 없다. 사용된 challenge 상태가 메모리이기 때문이다.
기존 폴더를 삭제/덮어쓰지 말고 오류와 부분 결과를 보존한 뒤 새 batch 이름으로 시작한다.

## 검증 구분

자동 테스트는 **로컬 loopback HTTP**로 두 worker와 22개 조합, 누락·중복·만료·변조,
토큰·코드 불일치, 개인키 비노출, 작업 폴더 덮어쓰기 거절을 검사한다.
그 결과를 실제 노트북 두 VM에서 22회 또는 220회 수행한 결과로 집계하지 않는다.
실제 두 VM의 자동 반복 결과는 실행 후 업로드된 원본으로 별도 검증해야 한다.
