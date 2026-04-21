# IEPP v0.4 — Autocorrelation-based Clone Detection
# New in v0.4:
#   - norm autocorrelation (lag-1, lag-2)
#   - norm velocity & acceleration
#   - composite clone_score separating ORIGINAL vs FORK
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
            "step":         self.step_n,
            "challenge":    challenge,
            "R":            R,
            "state_commit": state_commit,
            "norm":         float(np.linalg.norm(new_state)),
            "mean":         float(np.mean(new_state)),
            "std":          float(np.std(new_state)),
        }
        self.history.append(rec)
        return rec

    def clone(self):
        p = TrajectoryProver(self.dim)
        p.state   = self.state.copy()
        p.history = self.history.copy()
        p.step_n  = self.step_n
        return p


# =========================================================
# Attacker
# =========================================================

class StructuralAttacker:
    def __init__(self, observed_history: list):
        self.history = list(observed_history)

    def continue_from(self, challenges: list) -> list:
        forged  = []
        prev_R  = self.history[-1]["R"]
        fake_state = np.ones(16) * 0.5          # constant → no autocorrelation

        for ch in challenges:
            fake_commit = sha256_hex(np.round(fake_state, 8).tobytes())
            R = sha256_hex(
                prev_R.encode() +
                ch.encode() +
                fake_commit.encode()
            )
            rec = {
                "step":         len(self.history) + len(forged) + 1,
                "challenge":    ch,
                "R":            R,
                "state_commit": fake_commit,
                "norm":         float(np.linalg.norm(fake_state)),
                "mean":         float(np.mean(fake_state)),
                "std":          float(np.std(fake_state)),
            }
            forged.append(rec)
            prev_R = R

        return forged


# =========================================================
# v0.4 Metrics
# =========================================================

def compute_metrics(history: list) -> dict:
    """
    Compute all trajectory metrics from a history segment.
    Returns dict of floats (None if insufficient data).
    """
    if len(history) < 4:
        return {k: None for k in [
            "max_jump", "mean_jump", "dist_shift",
            "response_entropy", "autocorr_lag1", "autocorr_lag2",
            "mean_velocity", "std_velocity",
            "mean_acceleration", "std_acceleration",
        ]}

    norms = np.array([r["norm"] for r in history])
    responses = [r["R"] for r in history]

    # --- v0.3 metrics ---
    jumps      = np.abs(np.diff(norms))
    max_jump   = float(jumps.max())
    mean_jump  = float(jumps.mean())
    mid        = len(norms) // 2
    dist_shift = float(abs(norms[:mid].mean() - norms[mid:].mean()))
    resp_ent   = shannon_entropy(responses)

    # --- v0.4: autocorrelation ---
    def autocorr(x, lag):
        if len(x) <= lag:
            return None
        x_centered = x - x.mean()
        denom = np.dot(x_centered, x_centered)
        if denom < 1e-12:
            return 0.0
        return float(np.dot(x_centered[:-lag], x_centered[lag:]) / denom)

    ac1 = autocorr(norms, 1)
    ac2 = autocorr(norms, 2)

    # --- v0.4: velocity (1st diff) & acceleration (2nd diff) ---
    velocity     = np.diff(norms)
    acceleration = np.diff(velocity) if len(velocity) > 1 else np.array([0.0])

    return {
        "max_jump":          round(max_jump, 6),
        "mean_jump":         round(mean_jump, 6),
        "dist_shift":        round(dist_shift, 6),
        "response_entropy":  round(resp_ent, 6),
        "autocorr_lag1":     round(ac1, 6) if ac1 is not None else None,
        "autocorr_lag2":     round(ac2, 6) if ac2 is not None else None,
        "mean_velocity":     round(float(velocity.mean()), 6),
        "std_velocity":      round(float(velocity.std()), 6),
        "mean_acceleration": round(float(acceleration.mean()), 6),
        "std_acceleration":  round(float(acceleration.std()), 6),
    }


def clone_score(metrics: dict, baseline: dict) -> float:
    """
    Higher score = more likely to be a genuine continuous trajectory.
    Penalises deviations from baseline in autocorr, velocity std, etc.
    Returns float in [0, 1].
    """
    if metrics.get("autocorr_lag1") is None:
        return 0.5  # insufficient data

    penalty = 0.0

    # 1. Autocorrelation deviation (genuine trajectory has smooth autocorr)
    if baseline and "autocorr_lag1_mean" in baseline:
        for lag in ["autocorr_lag1", "autocorr_lag2"]:
            m = baseline.get(f"{lag}_mean", 0)
            s = baseline.get(f"{lag}_std", 0.1)
            z = abs(metrics[lag] - m) / max(s, 1e-6)
            penalty += min(z / 3.0, 1.0) * 0.25
    else:
        # Heuristic: real trajectories tend to have positive lag-1 autocorr
        if metrics["autocorr_lag1"] < 0.0:
            penalty += 0.25
        if metrics.get("autocorr_lag2", 0) < 0.0:
            penalty += 0.15

    # 2. Velocity std — constant fake state → std_velocity ≈ 0
    if baseline and "std_velocity_mean" in baseline:
        m = baseline["std_velocity_mean"]
        s = baseline["std_velocity_std"]
        z = abs(metrics["std_velocity"] - m) / max(s, 1e-6)
        penalty += min(z / 3.0, 1.0) * 0.25
    else:
        if metrics["std_velocity"] < 0.02:
            penalty += 0.35   # suspiciously flat

    # 3. Max jump (from v0.3)
    if metrics["max_jump"] > 0.75:
        penalty += 0.15

    return round(max(0.0, 1.0 - penalty), 6)


# =========================================================
# Baseline Builder
# =========================================================

def build_baseline(runs: int = 50, steps: int = 40,
                   dim: int = 16, sleep_s: float = 0.001) -> dict:
    records = []
    for i in range(runs):
        p = TrajectoryProver(dim)
        for j in range(steps):
            p.step(f"base-c{j}")
            time.sleep(sleep_s)
        m = compute_metrics(p.history)
        records.append(m)
        if (i + 1) % 10 == 0:
            print(f"  baseline {i+1}/{runs}...")

    df = pd.DataFrame(records).dropna()

    baseline = {}
    for col in df.columns:
        baseline[f"{col}_mean"] = float(df[col].mean())
        baseline[f"{col}_std"]  = float(df[col].std(ddof=0))

    return baseline


# =========================================================
# Single Experiment
# =========================================================

def run_experiment(steps: int = 40, fork_step: int = 12,
                   dim: int = 16, sleep_s: float = 0.001,
                   baseline: dict = None) -> list:

    original = TrajectoryProver(dim)
    fork     = None

    for i in range(steps):
        original.step(f"c{i}")
        if i == fork_step:
            fork = original.clone()
        time.sleep(sleep_s)

    post_challenges = [f"c{i}" for i in range(fork_step + 1, steps)]

    for ch in post_challenges:
        fork.step(ch)
        time.sleep(sleep_s)

    attacker     = StructuralAttacker(original.history[:fork_step + 1])
    atk_post     = attacker.continue_from(post_challenges)
    full_atk_hist = original.history[:fork_step + 1] + atk_post

    def evaluate(history, label):
        seg     = history[fork_step:]
        metrics = compute_metrics(seg)
        cs      = clone_score(metrics, baseline)
        return {
            "entity":           label,
            "autocorr_lag1":    metrics["autocorr_lag1"],
            "autocorr_lag2":    metrics["autocorr_lag2"],
            "std_velocity":     metrics["std_velocity"],
            "mean_acceleration":metrics["mean_acceleration"],
            "max_jump":         metrics["max_jump"],
            "response_entropy": metrics["response_entropy"],
            "clone_score":      cs,
            "verdict":          "GENUINE" if cs > 0.6 else "SUSPECT",
        }

    return [
        evaluate(original.history,  "ORIGINAL"),
        evaluate(fork.history,      "FORK"),
        evaluate(full_atk_hist,     "ATTACKER"),
    ]


# =========================================================
# Repeated Runs
# =========================================================

def run_repeated(runs: int = 50, baseline: dict = None, **kwargs) -> pd.DataFrame:
    rows = []
    for i in range(1, runs + 1):
        results = run_experiment(baseline=baseline, **kwargs)
        for r in results:
            r["run_id"] = i
        rows.extend(results)
        if i % 10 == 0:
            print(f"  run {i}/{runs}...")
    return pd.DataFrame(rows)


# =========================================================
# Main
# =========================================================

STEPS     = 40
FORK_STEP = 12
DIM       = 16
SLEEP_S   = 0.001

print("=" * 60)
print("IEPP v0.4 — Building baseline (50 runs)...")
print("=" * 60)
baseline = build_baseline(runs=50, steps=STEPS, dim=DIM, sleep_s=SLEEP_S)

print("\n--- Key baseline values ---")
for k in ["autocorr_lag1_mean", "autocorr_lag1_std",
          "std_velocity_mean",  "std_velocity_std"]:
    print(f"  {k}: {round(baseline[k], 6)}")

print("\n" + "=" * 60)
print("IEPP v0.4 — Running 50-run experiment...")
print("=" * 60)
rdf = run_repeated(
    runs=50, baseline=baseline,
    steps=STEPS, fork_step=FORK_STEP,
    dim=DIM, sleep_s=SLEEP_S
)

print("\n=== PER-ENTITY SUMMARY ===\n")
summary = rdf.groupby("entity").agg(
    avg_clone_score      = ("clone_score",      "mean"),
    avg_autocorr_lag1    = ("autocorr_lag1",    "mean"),
    avg_std_velocity     = ("std_velocity",      "mean"),
    avg_response_entropy = ("response_entropy",  "mean"),
    pct_genuine          = ("verdict", lambda x: (x == "GENUINE").mean()),
).round(4)

print(summary.to_string())

print("\n=== KEY QUESTION ===")
orig  = rdf[rdf.entity == "ORIGINAL"]["clone_score"].mean()
fork  = rdf[rdf.entity == "FORK"]["clone_score"].mean()
atk   = rdf[rdf.entity == "ATTACKER"]["clone_score"].mean()
gap   = orig - fork

print(f"  ORIGINAL  avg clone_score : {orig:.4f}")
print(f"  FORK      avg clone_score : {fork:.4f}")
print(f"  ATTACKER  avg clone_score : {atk:.4f}")
print(f"  ORIG-FORK gap             : {gap:.4f}  {'← separable' if abs(gap) > 0.05 else '← NOT separable yet'}")

print("\n=== SAMPLE (run 1) ===\n")
print(rdf[rdf.run_id == 1].to_string(index=False))
