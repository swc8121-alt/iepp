# IEPP v0.3 — Merged & Fixed
# Claude + GPT combined version
# Fixed: state_commit passed to layer2 chain verification
# Added: attacker trajectory plausibility scoring
# Colab-ready

import os
import time
import math
import hashlib
import random
import numpy as np
import pandas as pd


# =========================================================
# Utility
# =========================================================

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def runtime_entropy(dim: int) -> np.ndarray:
    mix = hashlib.sha256(
        str(time.time_ns()).encode() +
        str(time.perf_counter_ns()).encode() +
        str(random.random()).encode() +
        os.urandom(16)
    ).digest()
    v = np.frombuffer(mix, dtype=np.uint8).astype(np.float64)
    v = (v / 127.5) - 1.0
    if len(v) < dim:
        v = np.pad(v, (0, dim - len(v)), mode="wrap")
    return v[:dim]

def challenge_vec(c: str, dim: int) -> np.ndarray:
    h = hashlib.sha256(c.encode()).digest()
    v = np.frombuffer(h, dtype=np.uint8).astype(np.float64)
    v = (v / 127.5) - 1.0
    if len(v) < dim:
        v = np.pad(v, (0, dim - len(v)), mode="wrap")
    return v[:dim]

def shannon_entropy(hex_strings: list) -> float:
    joined = "".join(hex_strings)
    if not joined:
        return 0.0
    counts = {}
    for ch in joined:
        counts[ch] = counts.get(ch, 0) + 1
    total = len(joined)
    return -sum((c/total) * math.log2(c/total) for c in counts.values())


# =========================================================
# Layer 3: Statistical Continuity
# =========================================================

def trajectory_plausibility(history: list, baseline: dict = None) -> dict:
    if len(history) < 4:
        return {
            "max_jump": None, "mean_jump": None,
            "distribution_shift": None, "response_entropy": None,
            "continuity_score": None, "flags": ["insufficient_history"]
        }

    norms = [float(r["norm"]) for r in history]
    responses = [str(r["R"]) for r in history]

    jumps = [abs(norms[i] - norms[i-1]) for i in range(1, len(norms))]
    max_jump = max(jumps) if jumps else 0.0
    mean_jump = float(np.mean(jumps)) if jumps else 0.0

    mid = len(norms) // 2
    dist_shift = abs(np.mean(norms[:mid]) - np.mean(norms[mid:])) if mid > 0 else 0.0

    resp_entropy = shannon_entropy(responses)

    flags = []

    if baseline is None:
        # Heuristic thresholds
        if max_jump > 0.75:       flags.append("large_norm_jump")
        if dist_shift > 0.35:     flags.append("distribution_shift")
        if resp_entropy < 3.5:    flags.append("low_response_entropy")

        p = (min(max_jump / 1.0, 1.0) * 0.4 +
             min(dist_shift / 0.5, 1.0) * 0.3 +
             min(max(0.0, 4.0 - resp_entropy) / 4.0, 1.0) * 0.3)
        score = max(0.0, 1.0 - p)

    else:
        ub_jump  = baseline["max_jump_mean"]  + 3 * baseline["max_jump_std"]
        ub_shift = baseline["dist_shift_mean"] + 3 * baseline["dist_shift_std"]
        lb_ent   = baseline["resp_entropy_mean"] - 3 * baseline["resp_entropy_std"]

        if max_jump   > ub_jump:  flags.append("large_norm_jump")
        if dist_shift > ub_shift: flags.append("distribution_shift")
        if resp_entropy < lb_ent: flags.append("low_response_entropy")

        def z_high(x, m, s): return max(0.0, (x - m) / s) if s > 1e-12 else (0.0 if x <= m else 3.0)
        def z_low(x, m, s):  return max(0.0, (m - x) / s) if s > 1e-12 else (0.0 if x >= m else 3.0)

        p = (min(z_high(max_jump,   baseline["max_jump_mean"],   baseline["max_jump_std"])   / 3.0, 1.0) * 0.4 +
             min(z_high(dist_shift, baseline["dist_shift_mean"], baseline["dist_shift_std"]) / 3.0, 1.0) * 0.3 +
             min(z_low(resp_entropy, baseline["resp_entropy_mean"], baseline["resp_entropy_std"]) / 3.0, 1.0) * 0.3)
        score = max(0.0, 1.0 - p)

    return {
        "max_jump": round(max_jump, 6),
        "mean_jump": round(mean_jump, 6),
        "distribution_shift": round(dist_shift, 6),
        "response_entropy": round(resp_entropy, 6),
        "continuity_score": round(score, 6),
        "flags": flags
    }


# =========================================================
# Layer 2: Commitment Chain Verifier
# =========================================================

def verify_chain(history: list) -> tuple:
    """
    Returns (True, None) if chain is intact,
    (False, step_index) at first broken link.
    Requires history records to include 'state_commit'.
    """
    for i in range(1, len(history)):
        if "state_commit" not in history[i]:
            return True, None  # commit not recorded, skip layer2
        expected = sha256_hex(
            history[i-1]["R"].encode() +
            history[i]["challenge"].encode() +
            history[i]["state_commit"].encode()
        )
        if expected != history[i]["R"]:
            return False, i
    return True, None


# =========================================================
# Prover
# =========================================================

class TrajectoryProver:
    def __init__(self, dim: int = 16):
        self.dim = dim
        self.state = runtime_entropy(dim)
        self.history = []
        self.step_n = 0

    def step(self, challenge: str) -> dict:
        e = runtime_entropy(self.dim)
        c = challenge_vec(challenge, self.dim)

        mixed = 0.72 * self.state + 0.18 * c + 0.10 * e
        new_state = np.tanh(
            np.sin(mixed * 3.1) +
            np.cos(mixed * 2.3) +
            0.05 * self.step_n
        )

        state_commit = sha256_hex(np.round(new_state, 8).tobytes())
        prev = self.history[-1]["R"].encode() if self.history else b"GENESIS"

        R = sha256_hex(
            prev +
            challenge.encode() +
            state_commit.encode()
        )

        self.state = new_state
        self.step_n += 1

        rec = {
            "step": self.step_n,
            "challenge": challenge,
            "R": R,
            "state_commit": state_commit,   # kept for layer2
            "norm": float(np.linalg.norm(new_state)),
            "mean": float(np.mean(new_state)),
            "std":  float(np.std(new_state)),
        }
        self.history.append(rec)
        return rec

    def clone(self):
        p = TrajectoryProver(self.dim)
        p.state = self.state.copy()
        p.history = self.history.copy()
        p.step_n = self.step_n
        return p


# =========================================================
# Attacker (structural forger — knows algorithm, not state)
# =========================================================

class StructuralAttacker:
    """
    Knows: R sequence, challenges, algorithm structure
    Does not know: internal state, runtime entropy values
    Strategy: forge plausible-looking chain with fake state
    """
    def __init__(self, observed_history: list):
        self.history = list(observed_history)

    def continue_from(self, challenges: list) -> list:
        forged = []
        prev_R = self.history[-1]["R"]

        for ch in challenges:
            # Attacker cannot reproduce real runtime_entropy
            # Uses deterministic fake state
            fake_state = np.ones(16) * 0.5
            fake_commit = sha256_hex(np.round(fake_state, 8).tobytes())

            R = sha256_hex(
                prev_R.encode() +
                ch.encode() +
                fake_commit.encode()
            )
            rec = {
                "step": len(self.history) + len(forged) + 1,
                "challenge": ch,
                "R": R,
                "state_commit": fake_commit,
                "norm": float(np.linalg.norm(fake_state)),
                "mean": float(np.mean(fake_state)),
                "std":  float(np.std(fake_state)),
            }
            forged.append(rec)
            prev_R = R

        return forged


# =========================================================
# Baseline Builder
# =========================================================

def build_baseline(runs: int = 50, steps: int = 40, dim: int = 16, sleep_s: float = 0.001) -> dict:
    metrics = []
    for i in range(runs):
        p = TrajectoryProver(dim)
        for j in range(steps):
            p.step(f"base-c{j}")
            time.sleep(sleep_s)
        m = trajectory_plausibility(p.history)
        metrics.append(m)
        if (i+1) % 10 == 0:
            print(f"  baseline {i+1}/{runs}...")

    mdf = pd.DataFrame(metrics)
    return {
        "max_jump_mean":      float(mdf["max_jump"].mean()),
        "max_jump_std":       float(mdf["max_jump"].std(ddof=0)),
        "dist_shift_mean":    float(mdf["distribution_shift"].mean()),
        "dist_shift_std":     float(mdf["distribution_shift"].std(ddof=0)),
        "resp_entropy_mean":  float(mdf["response_entropy"].mean()),
        "resp_entropy_std":   float(mdf["response_entropy"].std(ddof=0)),
    }


# =========================================================
# Full Experiment
# =========================================================

def run_experiment(
    steps: int = 40,
    fork_step: int = 12,
    dim: int = 16,
    sleep_s: float = 0.001,
    baseline: dict = None,
) -> dict:

    original = TrajectoryProver(dim)
    fork = None

    for i in range(steps):
        original.step(f"c{i}")
        if i == fork_step:
            fork = original.clone()
        time.sleep(sleep_s)

    post_challenges = [f"c{i}" for i in range(fork_step + 1, steps)]

    for ch in post_challenges:
        fork.step(ch)
        time.sleep(sleep_s)

    attacker = StructuralAttacker(original.history[:fork_step + 1])
    atk_history = attacker.continue_from(post_challenges)
    full_atk_history = original.history[:fork_step + 1] + atk_history

    # Evaluate all three
    def evaluate(history, label):
        chain_ok, break_at = verify_chain(history)
        stats = trajectory_plausibility(history[fork_step:], baseline=baseline)
        verdict = "CONTINUOUS" if (chain_ok and stats["continuity_score"] is not None and stats["continuity_score"] > 0.6) else "ANOMALY"
        return {
            "entity": label,
            "chain_ok": chain_ok,
            "chain_break_at": break_at,
            "max_jump": stats["max_jump"],
            "dist_shift": stats["distribution_shift"],
            "entropy": stats["response_entropy"],
            "continuity_score": stats["continuity_score"],
            "flags": ",".join(stats["flags"]) if stats["flags"] else "—",
            "verdict": verdict,
        }

    results = [
        evaluate(original.history,    "ORIGINAL"),
        evaluate(fork.history,        "FORK (clone)"),
        evaluate(full_atk_history,    "ATTACKER"),
    ]

    return results


# =========================================================
# Repeated runs
# =========================================================

def run_repeated(runs: int = 30, baseline: dict = None, **kwargs) -> pd.DataFrame:
    all_rows = []
    for i in range(1, runs + 1):
        rows = run_experiment(baseline=baseline, **kwargs)
        for r in rows:
            r["run_id"] = i
        all_rows.extend(rows)
        if i % 10 == 0:
            print(f"  run {i}/{runs}...")
    return pd.DataFrame(all_rows)


# =========================================================
# Main
# =========================================================

STEPS     = 40
FORK_STEP = 12
DIM       = 16
SLEEP_S   = 0.001

print("=" * 60)
print("IEPP v0.3 — Building baseline...")
print("=" * 60)
baseline = build_baseline(runs=30, steps=STEPS, dim=DIM, sleep_s=SLEEP_S)

print("\n--- Baseline ---")
for k, v in baseline.items():
    print(f"  {k}: {round(v, 6)}")

print("\n" + "=" * 60)
print("IEPP v0.3 — Running 30-run experiment...")
print("=" * 60)
rdf = run_repeated(runs=30, baseline=baseline,
                   steps=STEPS, fork_step=FORK_STEP,
                   dim=DIM, sleep_s=SLEEP_S)

print("\n=== PER-ENTITY SUMMARY ===\n")
summary = rdf.groupby("entity").agg(
    avg_continuity_score=("continuity_score", "mean"),
    avg_max_jump=("max_jump", "mean"),
    avg_dist_shift=("dist_shift", "mean"),
    avg_entropy=("entropy", "mean"),
    pct_continuous=("verdict", lambda x: (x == "CONTINUOUS").mean()),
    chain_break_rate=("chain_ok", lambda x: (~x).mean()),
).round(4)

print(summary.to_string())

print("\n=== SAMPLE TABLE (first run) ===\n")
print(rdf[rdf.run_id == 1].to_string(index=False))
