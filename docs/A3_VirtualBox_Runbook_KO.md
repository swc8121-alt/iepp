# A3 VirtualBox 동일 자격증명 복원 경쟁 실행서

상태: L1 연구용 하네스. 프로덕션 보안 주장이나 하이퍼바이저 저항성 증명이 아니다.

## 무엇을 실제로 검사하는가

한 VM 스냅샷에 **동일한 Ed25519 시험용 개인키, 동일 counter, 동일 canonical head**가 들어 있다. 이 스냅샷에서 복원한 Fork A와 Fork B가 별도 네트워크 registry에 실제 서명된 transition evidence를 제출한다. Registry는 서버가 발급한 challenge, 서명, counter, predecessor, 상태 전이를 확인하고 SQLite transaction의 compare-and-swap으로 successor 하나만 승인한다.

승인된 branch만 `EXECUTED_SIMULATED` 보호 작업을 기록한다. 이것은 애플리케이션이 IEPP 결정을 준수하는 policy gate의 동작을 보여준다. 악성 branch가 gate를 무시하고 자체 작업을 수행하는 것을 막는 실험은 아니다.

## 가장 빠른 재현: 한 명령 loopback

VirtualBox 없이 서명·HTTP·동시 race 경로를 먼저 확인한다.

```bash
cd reference/iepp_vnext
python a3_safe_resume_demo.py --workspace ./a3-demo-output --trials 25
python a3_vm_runner.py check --log ./a3-demo-output/client-results.jsonl
```

각 trial은 동일 predecessor에서 두 후보를 만들며 다음 두 사례를 번갈아 실행한다.

1. `BEFORE_CHALLENGE`: 복원 후 각 branch가 서로 다른 fresh challenge를 받는다.
2. `AFTER_CHALLENGE`: 복원 전 받은 같은 challenge까지 스냅샷에 포함한다.

성공 조건은 trial마다 승인 1건, 거절 1건, 모의 보호 작업 실행 1건, double accept 0건이다.

> `a3-demo-output/snapshot.json`에는 의도적으로 복제 가능한 시험용 개인키가 있다. 외부 시스템 자격증명으로 재사용하거나 공개 저장소에 올리지 않는다.

## 실제 2-VM 구성

### 1. 격리된 registry 준비

호스트 또는 별도 registry VM에서 저장소 commit을 고정하고 의존성을 설치한다. HTTP adapter에는 TLS나 client authentication이 없으므로 인터넷에 노출하지 말고 VirtualBox host-only network에서만 실행한다.

```bash
cd reference/iepp_vnext
python a3_vm_runner.py prepare --workspace ./a3-lab --snapshot-point BEFORE_CHALLENGE
python a3_registry_server.py \
  --database ./a3-lab/registry.db \
  --enrollment ./a3-lab/enrollment.json \
  --event-log ./a3-lab/registry-events.jsonl \
  --bind 192.168.56.1 --port 8043
```

`192.168.56.1`은 예시 host-only 주소다. 실제 호스트 주소로 교체한다. Registry는 trial 중 계속 실행되어야 한다.

Registry와 게스트의 역할은 분리한다.

| 위치 | 보관 파일 | 금지 사항 |
|---|---|---|
| Registry 호스트 | `registry.db`, `enrollment.json`, server event log | DB를 공유 폴더에서 두 VM이 직접 열지 않음 |
| Base VM과 두 복원본 | `snapshot.json`, runner와 core 코드 | `registry.db` 또는 enrollment private copy를 넣지 않음 |
| 결과 수집 위치 | 두 client log의 병합본 | 전송 실패를 정책 거절로 세지 않음 |

### 2. 복원 후 challenge 사례

`a3-lab/snapshot.json`만 Base VM의 실험 디렉터리에 복사한 후 VM을 완전히 종료한다. VirtualBox에서 `S1_AFTER_P0_BEFORE_CHALLENGE` 스냅샷을 만들고 Fork A와 Fork B를 full clone한다. 두 clone은 같은 시험용 개인키와 상태를 갖고, MAC 주소와 SSH 포트만 다르게 한다.

각 VM에서 후보를 만든다.

```bash
# Fork A
python a3_vm_runner.py candidate \
  --snapshot ./snapshot.json --branch-id A \
  --trial-id S1-0001 --case-id A3-FRESH-POST-RESTORE \
  --registry-url http://192.168.56.1:8043 --output ./candidate-A.json

# Fork B
python a3_vm_runner.py candidate \
  --snapshot ./snapshot.json --branch-id B \
  --trial-id S1-0001 --case-id A3-FRESH-POST-RESTORE \
  --registry-url http://192.168.56.1:8043 --output ./candidate-B.json
```

### 3. 복원 전 shared challenge 사례

Base VM에서 registry가 실행 중인 동안 challenge를 받아 `snapshot.json`에 넣는다. 기본 TTL은 900초다.

```bash
python a3_vm_runner.py bind-challenge \
  --snapshot ./snapshot.json \
  --registry-url http://192.168.56.1:8043 --ttl 900
```

즉시 VM을 종료하고 `S2_AFTER_CHALLENGE` 스냅샷을 만든 뒤 A/B를 복원한다. 두 branch는 `candidate` 명령에서 `--registry-url` 없이도 스냅샷에 든 같은 challenge로 서로 다른 서명 evidence를 만든다. Registry를 재시작하면 메모리 challenge record가 사라지므로 이 사례는 무효가 된다.

### 4. 통제된 동시 제출

두 VM의 시간을 NTP로 동기화한다. 동일한 미래 epoch nanoseconds 값을 두 VM에 전달하고 A/B 제출 순서 및 0/1/5/10/50/100 ms delay를 양방향으로 반복한다.

```bash
# Fork A
python a3_vm_runner.py submit \
  --registry-url http://192.168.56.1:8043 \
  --candidate ./candidate-A.json --log ./result-A.jsonl \
  --barrier-epoch-ns 1780000000000000000 --delay-ms 0

# Fork B
python a3_vm_runner.py submit \
  --registry-url http://192.168.56.1:8043 \
  --candidate ./candidate-B.json --log ./result-B.jsonl \
  --barrier-epoch-ns 1780000000000000000 --delay-ms 1
```

Barrier 값은 실행 시점보다 약 15초 뒤의 실제 값으로 교체한다. 승인 branch는 종료 코드 0, 정책상 losing branch는 종료 코드 2, transport failure는 종료 코드 3이다.

각 독립 race trial은 새 registry DB와 그 DB에 대응하는 새 스냅샷에서 시작해야 한다. 이미 advance된 DB에 P0 스냅샷을 다시 제출하면 두 branch 모두 stale 상태로 거절되는 것이 정상이다.

### 5. 결과 수집과 검사

두 VM의 결과 JSONL을 호스트의 한 파일로 병합한 후 검사한다.

```bash
python a3_vm_runner.py check --log ./combined-results.jsonl
python a3_vm_runner.py head \
  --registry-url http://192.168.56.1:8043 --sid a3-entity
```

필수 불변식은 다음과 같다.

- A/B 두 record가 모두 있고 transport가 성공했을 것
- `canonical_accept == true`가 정확히 1건일 것
- `protected_action == EXECUTED_SIMULATED`가 정확히 1건일 것
- 최종 canonical head가 승인 successor와 일치할 것
- fresh-challenge losing fork는 rollback/stale 계열, shared-challenge losing fork는 used-challenge 계열로 거절될 것

## 주장 경계와 남은 시험

이 하네스가 지지하는 문장은 좁다.

> 선언된 신뢰 가정 아래, 한 온라인 registry가 동일한 인증 predecessor에서 나온 경쟁 successor 가운데 정책상 canonical continuation 하나만 승인했다.

다음 항목은 이 결과로 확립되지 않는다.

- 의식, 인격, 법적 동일성, 물리적 원본 또는 형이상학적 원본
- 악성 코드가 IEPP policy gate 자체를 우회하는 경우
- 현재 개인키와 상태가 함께 탈취된 뒤 공격자가 먼저 제출하는 경우
- registry 재시작을 가로지르는 durable one-time challenge
- 분리된 registry, network partition, split view 또는 equivocation
- TPM/TEE/secure element/PUF 기반 L2-L4 결합
- VirtualBox나 하이퍼바이저에 대한 일반적 snapshot 저항성
- entropy 품질 또는 production readiness

따라서 loopback 성공은 네트워크 통합 시험이고, 실제 2-VM 실행 로그는 별도로 수집해야 한다. 둘 다 현재 공개 증거 수준은 L1이다.
