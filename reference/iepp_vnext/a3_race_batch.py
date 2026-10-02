"""Two-worker L1 race matrix. No VM restore, attestation, or entropy-health claim.

Private worker bundles travel via SCP, never via HTTP. The control plane uses
per-branch bearer tokens on the same trusted host-only HTTP lab network as A3.
The existing registry engine makes every transition decision unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import secrets
import threading
import time
import zipfile
from urllib.request import Request, urlopen
from uuid import uuid4

from a3_registry import A3RegistryEngine, evidence_from_dict
from a3_registry_server import A3RequestHandler
from http.server import ThreadingHTTPServer
from a3_safe_resume_demo import result_row
from a3_vm_runner import (append_jsonl, build_candidate, prepare_workspace,
                          utc_now, write_json, write_private_snapshot)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DELAYS = [(0, 0)] + [p for d in (1, 5, 10, 50, 100) for p in ((0, d), (d, 0))]
SOURCES = ('a3_race_batch.py', 'a3_registry.py', 'a3_registry_server.py',
           'a3_vm_runner.py', 'a3_safe_resume_demo.py', 'core.py', 'durable_store.py')
TIMES = ('request_received_monotonic_ns', 'body_complete_monotonic_ns',
         'verification_requested_monotonic_ns', 'lock_acquired_monotonic_ns',
         'decision_monotonic_ns')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def lines(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]


def source_hashes():
    root = Path(__file__).resolve().parent
    return {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in SOURCES}


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def prepare(root, url, repetitions):
    need(1 <= repetitions <= 10, 'repetitions must be 1..10')
    root.mkdir(parents=True, exist_ok=False)
    private = root / 'private'
    private.mkdir(mode=0o700)
    public = root / 'public'
    public.mkdir()
    run_id = uuid4().hex
    specs, snapshots = [], {}
    for rep in range(repetitions):
        for mode in ('fresh', 'shared'):
            for da, db in DELAYS:
                i = len(specs)
                trial = f'RACE-{mode.upper()}-{i + 1:04d}'
                spec = {'index': i, 'trial_id': trial, 'mode': mode,
                        'repetition': rep + 1, 'delay_ms': {'A': da, 'B': db}}
                location = private / trial
                prepared = prepare_workspace(location, 'a3-entity', 'iepp.a3.safe-resume',
                                             'a3-lab-key', f'{run_id}:{trial}:p0')
                snapshots[trial] = read(prepared['snapshot'])
                out = public / trial
                out.mkdir()
                write_json(out / 'enrollment.json', read(prepared['enrollment']))
                specs.append(spec)
    tokens = {b: secrets.token_hex(32) for b in 'AB'}
    manifest = {'schema': 'iepp-a3-race-batch-v1', 'run_id': run_id,
                'url': url.rstrip('/'), 'specs': specs, 'source_hashes': source_hashes(),
                'created_at_utc': utc_now(), 'actual_vm_restore_per_trial': False,
                'claim_scope': 'L1 single online registry; cooperative simulated gate'}
    write_json(public / 'manifest.json', manifest)
    write_private_snapshot(private / 'controller.json', {'tokens': tokens})
    for b in 'AB':
        write_private_snapshot(private / f'worker-{b}.private.json', {
            'manifest': manifest, 'branch': b, 'token': tokens[b], 'snapshots': snapshots})
    return manifest


def audit_trial(folder, spec):
    """Read public source records; missing, duplicate, stale, or mismatched = fail."""
    errors = []
    try:
        enrollment = read(folder / 'enrollment.json')
        events = lines(folder / 'registry-events.jsonl')
        decisions = [e for e in events if e['event'].startswith('TRANSITION_')]
        issued = [e['challenge'] for e in events if e['event'] == 'CHALLENGE_ISSUED']
        need(len(decisions) == 2, 'exactly-two-server-decisions-required')
        need(len(issued) == (1 if spec['mode'] == 'shared' else 2), 'challenge-count')
        by_evidence = {e['evidence_id']: e for e in decisions}
        need(len(by_evidence) == 2, 'duplicate-server-evidence')
        by_challenge = {c['challenge_id']: c for c in issued}
        records, timings, candidates = [], [], []
        pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(enrollment['public_key']))
        for branch in 'AB':
            candidate = read(folder / f'candidate-{branch}.json')
            row = read(folder / f'result-{branch}.json')
            evidence = evidence_from_dict(candidate['evidence'])
            pub.verify(evidence.signature, evidence.unsigned_body())
            need(candidate['branch_id'] == row['branch_id'] == branch, 'branch-mismatch')
            need(candidate['trial_id'] == row['trial_id'] == spec['trial_id'], 'trial-mismatch')
            need(candidate['public_key_fingerprint_sha256'] == row['public_key_fingerprint_sha256']
                 == enrollment['public_key_fingerprint_sha256'], 'key-mismatch')
            need(evidence.previous.hex() == enrollment['initial_state'] and evidence.counter == 1,
                 'not-fresh-initial-state')
            need(evidence.sid == enrollment['sid'] and evidence.domain == enrollment['domain']
                 and evidence.key_id == enrollment['key_id'], 'enrollment-mismatch')
            need(row['transport_ok'] is True and row.get('transport_error') is None, 'transport-failure')
            decision = by_evidence[row['evidence_id']]
            need(row['evidence_id'] == evidence.evidence_id().hex(), 'evidence-mismatch')
            for k in ('candidate_successor', 'presented_predecessor', 'canonical_head_before',
                      'canonical_head_after', 'registry_timing'):
                need(row[k] == decision[k], f'server-client-{k}')
            need(row['candidate_successor'] == evidence.state.hex() and
                 row['presented_predecessor'] == evidence.previous.hex(), 'candidate-result-mismatch')
            need(row['canonical_accept'] == decision['accepted'] and
                 row['registry_reason'] == decision['reason'], 'decision-mismatch')
            need(row['challenge_id'] == evidence.challenge_id.hex(), 'challenge-result-mismatch')
            challenge = by_challenge[row['challenge_id']]
            need(evidence.challenge_nonce.hex() == challenge['nonce'] and
                 evidence.challenge_expires_at == challenge['expires_at'], 'challenge-binding')
            timestamp = datetime.fromisoformat(decision['decided_at_utc']).timestamp()
            need(challenge['issued_at'] <= timestamp < challenge['expires_at'], 'expired-or-future')
            need(decision['counter'] == 1, 'counter-mismatch')
            timing = row['registry_timing']
            values = [timing[k] for k in TIMES]
            need(all(type(x) is int for x in values) and values == sorted(values), 'invalid-timing')
            records.append(row)
            timings.append(timing)
            candidates.append(candidate)
        need(sum(r['canonical_accept'] is True for r in records) == 1, 'accept-count')
        need((records[0]['challenge_id'] == records[1]['challenge_id']) ==
             (spec['mode'] == 'shared'), 'challenge-mode-mismatch')
        need(sum(r['protected_action'] == 'EXECUTED_SIMULATED' for r in records) == 1, 'action-count')
        winner = next(r for r in records if r['canonical_accept'])
        loser = next(r for r in records if not r['canonical_accept'])
        need(winner['registry_reason'] == 'CONTINUITY_VALID', 'winner-reason')
        need(loser['registry_reason'] == ('CHALLENGE_USED' if spec['mode'] == 'shared'
                                         else 'ROLLBACK_OR_LOSING_FORK'), 'loser-reason')
        need(loser['protected_action'] == 'BLOCKED', 'loser-action')
        need(winner['canonical_head_before'] == enrollment['initial_state'], 'initial-head')
        need(winner['candidate_successor'] == winner['canonical_head_after'] ==
             loser['canonical_head_before'] == loser['canonical_head_after'], 'head-changed-on-rejection')
        final = read(folder / 'final-head.json')
        need(final['ok'] and final['counter'] == 1 and final['canonical_head'] ==
             winner['candidate_successor'] and final['last_evidence_id'] == winner['evidence_id'], 'final-head')
        need(timings[0]['server_instance_id'] == timings[1]['server_instance_id'], 'different-server-clocks')
        need(timings[0]['request_id'] != timings[1]['request_id'], 'duplicate-request')
        overlap = min(t['decision_monotonic_ns'] for t in timings) - max(
            t['request_received_monotonic_ns'] for t in timings)
        schedule = read(folder / 'schedule.json')
        valid_schedule = True
        for r in records:
            b = r['branch_id']
            need(r['clock_sample'] == read(folder / f'clock-{b}.json'), 'clock-sample-mismatch')
            need(r['configured_delay_ms'] == spec['delay_ms'][b] and
                 r['server_barrier_monotonic_ns'] == schedule['server_barrier_monotonic_ns'], 'schedule-mismatch')
            valid_schedule &= (0 <= r['send_lateness_ms'] <= 100 and
                               0 <= r['clock_sample']['rtt_ms'] <= 200)
        return {'trial_id': spec['trial_id'], 'mode': spec['mode'], 'delay_ms': spec['delay_ms'],
                'passed': True, 'winner': winner['branch_id'], 'schedule_quality_ok': valid_schedule,
                'server_intervals_overlap': overlap > 0,
                'server_interval_overlap_ms': max(0, overlap) / 1e6, 'failures': []}
    except Exception as error:
        errors.append(f'{type(error).__name__}: {error}')
    return {'trial_id': spec['trial_id'], 'passed': False, 'failures': errors}


def audit_batch(public):
    manifest = read(public / 'manifest.json')
    trials = [audit_trial(public / s['trial_id'], s) for s in manifest['specs']]
    passed = sum(t['passed'] for t in trials)
    quality = sum(t.get('schedule_quality_ok', False) for t in trials)
    aborted = read(public / 'aborted.json') if (public / 'aborted.json').exists() else None
    return {'schema': 'iepp-a3-race-batch-check-v1', 'run_id': manifest['run_id'],
            'planned': len(trials), 'passed_trials': passed,
            'invariant_passed': bool(trials) and passed == len(trials),
            'passed': bool(trials) and passed == quality == len(trials) and aborted is None,
            'aborted': aborted,
            'overlap_trials': sum(t.get('server_intervals_overlap', False) for t in trials),
            'schedule_quality_ok_trials': quality,
            'claim_scope': manifest['claim_scope'], 'actual_vm_restore_per_trial': False,
            'trials': trials}


class Batch:
    def __init__(self, root, lead_seconds=3.0, allow_same_host=False):
        self.root = root
        self.public = root / 'public'
        self.manifest = read(self.public / 'manifest.json')
        need(self.manifest['source_hashes'] == source_hashes(), 'controller-code-changed')
        self.tokens = read(root / 'private/controller.json')['tokens']
        self.lock = threading.RLock()
        self.workers = {}
        self.index = 0
        self.engine = None
        self.challenges = {}
        self.ready = {}
        self.results = {}
        self.decisions = {}
        self.submitted = set()
        self.schedule = None
        self.active_since = None
        self.lead_seconds = lead_seconds
        self.allow_same_host = allow_same_host
        self.stopped = None
        self.finished = threading.Event()

    def fail(self, reason):
        with self.lock:
            self.stopped = reason
            write_json(self.public / 'aborted.json', {'reason': reason, 'at_utc': utc_now(), 'index': self.index})
            self.finished.set()

    def start_trial(self):
        spec = self.manifest['specs'][self.index]
        self.spec = spec
        self.folder = self.public / spec['trial_id']
        private = self.root / 'private' / spec['trial_id']
        self.engine = A3RegistryEngine(private / 'registry.db', private / 'enrollment.json',
                                       self.folder / 'registry-events.jsonl')
        e = self.engine.enrollment
        def issue():
            status, result = self.engine.issue_challenge(e.sid, e.domain, 120)
            need(status == 200, 'challenge-issue-failed')
            return result['challenge']
        a = issue()
        self.challenges = {'A': a, 'B': a if spec['mode'] == 'shared' else issue()}
        self.active_since = time.monotonic()

    def control(self, branch, value, peer, received_ns, body_ns):
        op = value['op']
        if op == 'clock':
            return {'server_monotonic_ns': time.monotonic_ns(), 'server_epoch_ns': time.time_ns(),
                    'run_id': self.manifest['run_id']}
        # The coordinator lock is NOT held around the registry's verification.
        if op == 'transition':
            with self.lock:
                self.require_active(branch, value)
                need(peer == self.workers[branch]['peer'], 'worker-address-changed')
                need(self.schedule is not None and branch not in self.submitted, 'transition-not-armed-or-duplicate')
                need(value['evidence'] == self.ready[branch]['candidate']['evidence'], 'unregistered-evidence')
                need(time.monotonic_ns() >= self.schedule['server_barrier_monotonic_ns'] - 250_000_000,
                     'transition-too-early')
                self.submitted.add(branch)
                engine = self.engine
            status, decision = engine.verify_and_advance(value['evidence'],
                request_received_monotonic_ns=received_ns, body_complete_monotonic_ns=body_ns)
            need(status == 200, 'registry-request-failed')
            with self.lock:
                self.decisions[branch] = decision
            return decision
        with self.lock:
            need(not self.stopped, 'batch-aborted')
            if op == 'hello':
                need(branch not in self.workers, 'duplicate-worker')
                need(value['source_hashes'] == self.manifest['source_hashes'], 'worker-code-mismatch')
                if not self.allow_same_host:
                    need(all(w['peer'] != peer for w in self.workers.values()), 'workers-must-have-distinct-addresses')
                self.workers[branch] = {'peer': peer, 'host': value['host'], 'runtime': value['runtime'],
                                        'source_hashes': value['source_hashes']}
                write_json(self.public / 'workers.json', self.workers)
                return {'ok': True}
            need(branch in self.workers, 'worker-not-registered')
            need(peer == self.workers[branch]['peer'], 'worker-address-changed')
            if op == 'task':
                if self.index == len(self.manifest['specs']):
                    return {'done': True}
                if len(self.workers) != 2 or value['index'] > self.index:
                    return {'wait': True}
                need(value['index'] == self.index, 'old-task-request')
                if self.engine is None:
                    self.start_trial()
                return {'spec': self.spec, 'challenge': self.challenges[branch]}
            self.require_active(branch, value)
            if op == 'ready':
                need(branch not in self.ready, 'duplicate-ready')
                c = value['candidate']
                need(c['branch_id'] == branch and c['trial_id'] == self.spec['trial_id'], 'wrong-candidate')
                need(c['evidence']['challenge_id'] == self.challenges[branch]['challenge_id'], 'wrong-challenge')
                need(0 <= value['clock_sample']['rtt_ms'] <= 200, 'clock-round-trip-too-large')
                self.ready[branch] = value
                write_json(self.folder / f'candidate-{branch}.json', c)
                write_json(self.folder / f'clock-{branch}.json', value['clock_sample'])
                if len(self.ready) == 2:
                    lead = int(self.lead_seconds * 1e9)
                    self.schedule = {'server_barrier_monotonic_ns': time.monotonic_ns() + lead,
                                     'server_barrier_epoch_ns': time.time_ns() + lead}
                    write_json(self.folder / 'schedule.json', self.schedule)
                return {'ok': True}
            if op == 'schedule':
                return self.schedule or {'wait': True}
            if op == 'result':
                need(branch not in self.results and branch in self.decisions, 'missing-or-duplicate-decision')
                row = value['record']
                need(row['registry_timing'] == self.decisions[branch]['registry_timing'], 'result-timing-mismatch')
                self.results[branch] = row
                write_json(self.folder / f'result-{branch}.json', row)
                append_jsonl(self.public / 'client-results.jsonl', row)
                if len(self.results) == 2:
                    _, head = self.engine.head(self.engine.enrollment.sid)
                    write_json(self.folder / 'final-head.json', head)
                    checked = audit_trial(self.folder, self.spec)
                    append_jsonl(self.public / 'trial-checks.jsonl', checked)
                    print(json.dumps({'completed': self.index + 1, 'total': len(self.manifest['specs']),
                                      **checked}), flush=True)
                    self.engine.close()
                    self.engine = None
                    if not checked['passed'] or not checked['schedule_quality_ok']:
                        self.fail('trial-failed-or-schedule-quality-out-of-range')
                        return {'ok': False, 'stop': True}
                    self.index += 1
                    self.ready, self.results, self.decisions = {}, {}, {}
                    self.submitted, self.schedule, self.active_since = set(), None, None
                    if self.index == len(self.manifest['specs']):
                        write_json(self.public / 'summary.json', audit_batch(self.public))
                        self.finished.set()
                return {'ok': True}
            raise ValueError('unknown-operation')

    def require_active(self, branch, value):
        need(not self.stopped and self.engine is not None and value['index'] == self.index,
             'inactive-trial')
        need(branch in self.workers, 'unknown-worker')


class BatchServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def __init__(self, address, batch):
        super().__init__(address, BatchHandler)
        self.batch = batch


class BatchHandler(A3RequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def do_GET(self):
        self._write(404, {'ok': False})

    def do_POST(self):
        received = time.monotonic_ns()
        if self.path != '/control':
            self._write(404, {'ok': False})
            return
        branch = self.headers.get('X-Branch', '')
        token = self.headers.get('Authorization', '')
        batch = self.server.batch
        if branch not in batch.tokens or not hmac.compare_digest(token, 'Bearer ' + batch.tokens[branch]):
            self._write(403, {'ok': False, 'reason': 'AUTH_REQUIRED'})
            return
        try:
            value = self._json_body()
            body = time.monotonic_ns()
            result = batch.control(branch, value, self.client_address[0], received, body)
            self._write(200, result)
        except Exception as error:
            # Do not echo request bodies, tokens, or private bundles into errors.
            self._write(400, {'ok': False, 'reason': type(error).__name__})


def rpc(config, value, timeout=15):
    request = Request(config['manifest']['url'] + '/control',
                      data=json.dumps(value).encode(), headers={
                          'Content-Type': 'application/json', 'X-Branch': config['branch'],
                          'Authorization': 'Bearer ' + config['token']})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def calibrate(config):
    samples = []
    for _ in range(5):
        start = time.monotonic_ns()
        response = rpc(config, {'op': 'clock'})
        end = time.monotonic_ns()
        need(response['run_id'] == config['manifest']['run_id'], 'wrong-controller')
        samples.append({'server_minus_local_ns': response['server_monotonic_ns'] - (start + end) // 2,
                        'rtt_ms': (end - start) / 1e6, 'sample_local_monotonic_ns': end})
    result = min(samples, key=lambda s: s['rtt_ms'])
    result['method'] = 'minimum-RTT midpoint estimate; not a synchronization guarantee'
    return result


def worker(config_path, output):
    config = read(config_path)
    need(config['manifest']['source_hashes'] == source_hashes(), 'worker-code-mismatch')
    if os.name != 'nt':
        need(Path(config_path).stat().st_mode & 0o077 == 0, 'chmod-600-worker-bundle-required')
    output.mkdir(parents=True, exist_ok=False)
    branch = config['branch']
    rpc(config, {'op': 'hello', 'source_hashes': source_hashes(),
                 'host': platform.node(), 'runtime': platform.python_version()})
    for index, spec in enumerate(config['manifest']['specs']):
        deadline = time.monotonic() + 900
        while True:
            task = rpc(config, {'op': 'task', 'index': index})
            if not task.get('wait'):
                break
            need(time.monotonic() < deadline, 'other-worker-timeout')
            time.sleep(.2)
        need(task['spec'] == spec, 'task-spec-mismatch')
        snapshot = dict(config['snapshots'][spec['trial_id']])
        # Shared challenge is a batch condition, NOT a VM restore event.
        candidate = build_candidate(snapshot, branch, spec['trial_id'],
                                    'A3-BATCH-' + spec['mode'].upper(), task['challenge'])
        candidate['actual_vm_restore'] = False
        candidate['batch_challenge_mode'] = spec['mode']
        folder = output / spec['trial_id']
        folder.mkdir()
        write_json(folder / 'candidate.json', candidate)
        clock = calibrate(config)
        rpc(config, {'op': 'ready', 'index': index, 'candidate': candidate, 'clock_sample': clock})
        while True:
            schedule = rpc(config, {'op': 'schedule', 'index': index})
            if not schedule.get('wait'):
                break
            need(time.monotonic() < deadline, 'schedule-timeout')
            time.sleep(.05)
        delay = spec['delay_ms'][branch]
        target = schedule['server_barrier_monotonic_ns'] - clock['server_minus_local_ns'] + delay * 1_000_000
        need(time.monotonic_ns() < target, 'missed-start-before-arming')
        while True:
            remaining = target - time.monotonic_ns()
            if remaining <= 0:
                break
            time.sleep(min(remaining / 1e9, .002))
        sent = time.monotonic_ns()
        sent_epoch = time.time_ns()
        try:
            decision = rpc(config, {'op': 'transition', 'index': index, 'evidence': candidate['evidence']})
        except Exception as error:
            write_json(folder / 'transport-failure.json', {'trial_id': spec['trial_id'],
                       'branch_id': branch, 'transport_ok': False, 'error_type': type(error).__name__})
            raise
        row = result_row(candidate, decision, (time.monotonic_ns() - sent) / 1e6)
        row.update({'host': platform.node(), 'runtime_version': platform.python_version(),
                    'transport_error': None, 'snapshot_source_revision': candidate['snapshot_source_revision'],
                    'actual_vm_restore': False, 'batch_challenge_mode': spec['mode'],
                    'barrier_clock': 'estimated-server-monotonic', **schedule,
                    'configured_delay_ms': delay, 'client_send_epoch_ns': sent_epoch,
                    'client_send_monotonic_ns': sent, 'send_lateness_ms': (sent - target) / 1e6,
                    'clock_sample': clock})
        write_json(folder / 'result.json', row)
        reply = rpc(config, {'op': 'result', 'index': index, 'record': row})
        need(reply.get('ok'), 'batch-stopped')
        print(json.dumps({'trial': spec['trial_id'], 'branch': branch,
                          'accepted': row['canonical_accept'], 'reason': row['registry_reason']}), flush=True)
    print(json.dumps({'worker_complete': branch, 'trials': len(config['manifest']['specs'])}), flush=True)


def serve(root, bind, port, allow_same_host=False):
    # In-memory challenges cannot be resumed safely after a controller restart.
    write_private_snapshot(root / 'private/started.json', {'at_utc': utc_now()})
    batch = Batch(root, allow_same_host=allow_same_host)
    server = BatchServer((bind, port), batch)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(json.dumps({'ready': True, 'url': batch.manifest['url'],
                      'trials': len(batch.manifest['specs']), 'waiting_for': ['A', 'B']}), flush=True)
    started = time.monotonic()
    try:
        while not batch.finished.wait(.5):
            if batch.active_since and time.monotonic() - batch.active_since > 90:
                batch.fail('trial-timeout')
            elif batch.active_since is None and time.monotonic() - started > 1800:
                batch.fail('workers-timeout')
    except KeyboardInterrupt:
        batch.fail('operator-interrupted')
    finally:
        # Allow the final result response to reach the second worker before closing.
        server.shutdown()
        server.server_close()
        thread.join()
        if batch.engine:
            batch.engine.close()
        summary = audit_batch(batch.public)
        summary['aborted'] = batch.stopped
        summary['passed'] = summary['passed'] and not batch.stopped
        write_json(batch.public / 'summary.json', summary)
        with zipfile.ZipFile(root / 'public-results.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(batch.public.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(root).as_posix())
        print(json.dumps({k: v for k, v in summary.items() if k != 'trials'}), flush=True)
    return 0 if summary['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('prepare')
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--url', default='http://192.168.56.1:8050')
    p.add_argument('--repetitions', type=int, default=1)
    p = commands.add_parser('serve')
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--bind', default='192.168.56.1')
    p.add_argument('--port', type=int, default=8050)
    p.add_argument('--allow-same-host', action='store_true', help='loopback integration tests only')
    p = commands.add_parser('worker')
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = commands.add_parser('check')
    p.add_argument('--public', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        m = prepare(args.workspace, args.url, args.repetitions)
        print(json.dumps({'prepared': True, 'trials': len(m['specs']), 'workspace': str(args.workspace)}))
    elif args.command == 'serve':
        need(not args.allow_same_host or args.bind == '127.0.0.1', 'same-host-only-on-loopback')
        return serve(args.workspace, args.bind, args.port, args.allow_same_host)
    elif args.command == 'worker':
        worker(args.config, args.output)
    else:
        summary = audit_batch(args.public)
        print(json.dumps(summary, indent=2))
        return 0 if summary['passed'] else 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
