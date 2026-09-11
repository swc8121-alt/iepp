"""L1 comparison only: entropy policies versus the existing no-entropy baseline.

Threads share one in-memory registry. Barrier release creates concurrent callers,
not a distributed/VM experiment or a fairness/security-probability estimate.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import threading
from collections import Counter
import core
import entropy_ablation as baseline

MODES = ('os_random', 'fixed', 'alternating', 'predictable_unique', 'no_entropy')

class Fixture:
    def __init__(self, mode):
        self.mode = mode
        self.authority = core.ChallengeAuthority()
        key = core.Ed25519PrivateKey.generate()
        initial = sha256(b'comparison-initial').digest()
        if mode == 'no_entropy':
            self.prover = baseline.Prover(key, initial)
            self.registry = baseline.Registry(self.authority, key, initial)
        else:
            self.prover = core.Prover('entity', 'domain', 'key', key, initial)
            self.registry = core.AtomicRegistry('comparison', self.authority)
            self.registry.enroll('entity', 'domain', initial, 'key', key.public_key(), {'declared-software'})
        self.serial = 0

    def challenge(self):
        self.serial += 1
        return self.authority.issue('entity', 'domain', now=0, ttl=30,
            nonce=sha256(str(self.serial).encode()).digest())

    def evidence(self, prover, challenge, source='declared-software'):
        if self.mode == 'no_entropy':
            return prover.transition(challenge)
        step = prover.counter + 1
        entropy = {'fixed': b'fixed', 'alternating': bytes([step % 2]),
                   'predictable_unique': sha256(f'public-step-{step}'.encode()).digest()}.get(self.mode)
        if entropy is None:
            entropy = os.urandom(32)
        return prover.transition(challenge, entropy, source, b'controlled-runtime')

    def verify(self, evidence):
        result = self.registry.verify_and_advance(evidence, now=0)
        return result if isinstance(result, tuple) else (result, 'ACCEPT' if result else 'REJECT')


def paired(fixture, schedule, pool, reverse_submission=False):
    # Full current key/state clone, independent fresh challenges, common parent.
    clone = fixture.prover.clone()
    original = fixture.evidence(fixture.prover, fixture.challenge())
    attacker = fixture.evidence(clone, fixture.challenge())
    if schedule == 'concurrent':
        gate = threading.Barrier(2, timeout=10)
        def submit(evidence):
            gate.wait()
            return fixture.verify(evidence)
        if reverse_submission:
            right = pool.submit(submit, attacker)
            left = pool.submit(submit, original)
        else:
            left = pool.submit(submit, original)
            right = pool.submit(submit, attacker)
        return left.result(timeout=15), right.result(timeout=15)
    if schedule == 'original_first':
        return fixture.verify(original), fixture.verify(attacker)
    right = fixture.verify(attacker)
    return fixture.verify(original), right


def run(trials):
    summary = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for mode in MODES:
            row = {}
            for schedule in ('original_first', 'clone_first', 'concurrent'):
                counts = Counter()
                for trial in range(trials):
                    left, right = paired(Fixture(mode), schedule, pool, trial % 2 == 1)
                    n = int(left[0]) + int(right[0])
                    counts['original_accepts'] += left[0]
                    counts['clone_accepts'] += right[0]
                    counts['double_accepts'] += n == 2
                    counts['zero_accepts'] += n == 0
                row[schedule] = dict(counts)
            # Same challenge isolates contribution to branch divergence.
            divergence = 0
            replay = 0
            tamper = 0
            for _ in range(trials):
                f = Fixture(mode)
                clone = f.prover.clone()
                challenge = f.challenge()
                first = f.evidence(f.prover, challenge)
                second = f.evidence(clone, challenge)
                divergence += first.state != second.state
                tamper += f.verify(replace(first, state=bytes(32)))[0]
                if not f.verify(first)[0]:
                    raise AssertionError('valid first transition rejected')
                replay += f.verify(first)[0]
            row['same_challenge_divergences'] = divergence
            row['replay_false_accepts'] = replay
            row['unsigned_tamper_false_accepts'] = tamper
            f = Fixture(mode)
            sequence = []
            for _ in range(4):
                outcome = f.verify(f.evidence(f.prover, f.challenge()))
                sequence.append({'accepted': outcome[0], 'reason': outcome[1]})
                if not outcome[0]:
                    break  # Do not continue from an unaccepted local state.
            row['four_step_sequence'] = sequence
            if mode != 'no_entropy':
                f = Fixture(mode)
                row['disallowed_source'] = f.verify(f.evidence(f.prover, f.challenge(), 'unapproved'))
            summary[mode] = row
    return {'schema': 'iepp-entropy-comparison-v1', 'evidence_level': 'L1',
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'source_sha256': {name: sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ('core.py', 'entropy_ablation.py', 'entropy_comparison.py')},
        'concurrent_submission': 'alternating which branch is submitted first; no fairness claim',
        'python': platform.python_version(), 'platform': platform.platform(), 'trials_per_case': trials,
        'scope': 'single-process threads, one in-memory registry; no VM, attestation, or physical entropy',
        'baseline_limit': 'Existing entropy_ablation implementation; narrower validation and no audit checkpoint parity.',
        'modes': summary}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials', type=int, default=1000)
    parser.add_argument('--output', type=Path, default=Path('results/entropy_comparison_v1.json'))
    args = parser.parse_args()
    if args.trials < 1:
        parser.error('--trials must be positive')
    result = run(args.trials)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
