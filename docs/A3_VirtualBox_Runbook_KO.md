# A3 VirtualBox 스냅샷/동일 자격증명 포크 실행서

상태: 연구용 실행 하네스. 프로덕션 보안 주장이나 하이퍼바이저 저항성 증명이 아니다.

## 검증 경계

동일 코드·동일 자격증명 식별자·동일 사전 상태에서 복원된 두 VM이 같은 canonical predecessor의 경쟁 successor를 제출할 때, 단일 SQLite registry CAS가 최대 하나만 승인하는지 검사한다. 승인된 branch는 registry-relative winner일 뿐 물리적·통계적·형이상학적 원본이 아니다.

## 준비

호스트에 VirtualBox 7.x, 게스트에 Ubuntu 24.04와 Python 3.11+를 설치한다. 저장소를 같은 commit에 고정하고 `pip install -r requirements-lock.txt`를 실행한다. 공유 폴더는 registry DB를 동시에 여는 용도로 사용하지 말고, DB는 호스트 또는 별도 registry VM의 로컬 디스크에 둔다.

```bash
cd reference/iepp_vnext
python a3_vm_runner.py prepare --workspace ~/a3-s1 --snapshot-point BEFORE_CHALLENGE
```

`~/a3-s1/snapshot.json`이 생성된 상태에서 VM을 종료하고 VirtualBox 스냅샷 `S1_AFTER_P0_BEFORE_CHALLENGE`를 만든다. 이 스냅샷에서 Fork A와 Fork B를 full clone하고 MAC 주소와 SSH 포트만 서로 다르게 설정한다.

## 후보 생성

각 복원 VM에서 같은 `snapshot.json`을 사용한다. post-restore challenge 사례에서는 서로 다른 challenge ID를 지정한다.

```bash
python a3_vm_runner.py candidate --snapshot ~/a3-s1/snapshot.json --branch-id A --trial-id S1-AB-0001 --case-id S1-AB --challenge-id CA-0001 --output ~/a3-A.json
python a3_vm_runner.py candidate --snapshot ~/a3-s1/snapshot.json --branch-id B --trial-id S1-AB-0001 --case-id S1-AB --challenge-id CB-0001 --output ~/a3-B.json
```

복원 전 challenge 사례는 `prepare`에 같은 challenge를 저장한다.

```bash
python a3_vm_runner.py prepare --workspace ~/a3-s2 --snapshot-point AFTER_CHALLENGE --challenge-id C-SHARED-0001
```

## 직렬 순서

A→B와 B→A를 각각 새 registry DB에서 반복한다. 첫 제출은 종료 코드 0, losing fork는 종료 코드 2와 `CAS_CONFLICT`가 기대된다.

```bash
python a3_vm_runner.py submit --database ~/a3-s1/registry.db --candidate ~/a3-A.json --log ~/a3-results.jsonl
python a3_vm_runner.py submit --database ~/a3-s1/registry.db --candidate ~/a3-B.json --log ~/a3-results.jsonl
```

## 통제된 race

두 VM의 UTC/NTP를 동기화하고 호스트에서 현재 epoch ns보다 15초 뒤의 barrier를 계산한다. 두 VM에서 동일한 `--barrier-epoch-ns`를 사용하며 0/1/5/10/50/100 ms offset을 양방향으로 각각 10회 이상 반복한다.

```bash
python a3_vm_runner.py submit --database /registry/registry.db --candidate ~/a3-A.json --log ~/a3-results.jsonl --barrier-epoch-ns 0 --delay-ms 0
```

위의 `0`은 실제 미래 epoch ns 값으로 교체한다. SQLite DB를 게스트 공유 폴더에서 직접 경쟁 접근하지 않는다. 실제 2-VM 시험에서는 registry를 한 VM/호스트 서비스로 노출하는 어댑터가 필요하다. 현재 runner는 동일 머신 또는 registry 로컬 파일 기반 CAS의 재현 가능한 1단계 하네스다.

## 결과 검사

```bash
python a3_vm_runner.py check --log ~/a3-results.jsonl
```

필수 불변식은 trial별 `canonical_accept_count <= 1`, `CAS success_count <= 1`, 단일 최종 canonical head이다. timeout, 전송 실패, HTTP 500은 올바른 정책 거절로 세지 않는다. entropy health는 이 하네스가 평가하지 않으므로 항상 `NOT_EVALUATED`로 별도 기록한다.

## 제한

현재 단계는 실제 `SQLiteCanonicalStore.compare_and_swap`의 단일 registry 경계를 실행한다. challenge single-use의 내구 저장, 네트워크 API, VirtualBox 자동 제어, protected key/attestation, 악성 하이퍼바이저, registry partition은 포함하지 않는다. 따라서 결과는 L1의 제한된 시스템 증거이며 L2/L3/L4 또는 일반적 snapshot 저항성을 확립하지 않는다.
