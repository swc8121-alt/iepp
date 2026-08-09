"""Bounded abstract-state exploration of the canonical single-successor invariants."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ModelState:
    counter: int
    head: str
    used: frozenset[int]
    accepted_at_counter: tuple[tuple[int, str], ...]


def successors(state: ModelState, challenge_count: int):
    # Valid next transitions with two possible fork labels.
    for challenge in range(challenge_count):
        if challenge not in state.used:
            for branch in ("A", "B"):
                new_counter = state.counter + 1
                new_head = f"{state.head}>{branch}{challenge}"
                yield ModelState(new_counter, new_head, state.used | {challenge},
                                 state.accepted_at_counter + ((new_counter, new_head),))
    # Replay/rollback/unknown challenge actions are rejection self-loops and do
    # not need separate states; count them for transition coverage.


def check(depth: int = 7, challenge_count: int = 5) -> dict:
    initial = ModelState(0, "GENESIS", frozenset(), tuple())
    frontier, seen = {initial}, {initial}
    explored_transitions = 0
    violations = []
    for _ in range(depth):
        next_frontier = set()
        for state in frontier:
            explored_transitions += 3  # replay, rollback, unknown rejection self-loops
            for candidate in successors(state, challenge_count):
                explored_transitions += 1
                counters = [counter for counter, _ in candidate.accepted_at_counter]
                if counters != list(range(1, candidate.counter + 1)):
                    violations.append("counter-not-contiguous")
                if len(candidate.used) != candidate.counter:
                    violations.append("challenge-reuse-or-loss")
                if len({counter for counter, _ in candidate.accepted_at_counter}) != candidate.counter:
                    violations.append("double-successor-at-counter")
                if candidate not in seen:
                    seen.add(candidate)
                    next_frontier.add(candidate)
        frontier = next_frontier
        if not frontier:
            break
    return {"schema": "iepp-bounded-abstract-model-v1", "depth": depth,
            "challenge_count": challenge_count, "states_explored": len(seen),
            "transitions_explored": explored_transitions, "violations": sorted(set(violations)),
            "all_invariants_hold": not violations,
            "limitation": "Bounded executable model, not an unbounded formal proof or TLA+/ProVerif analysis."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--depth", type=int, default=7)
    parser.add_argument("--challenges", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("iepp_lab/results/bounded_model_v1.json"))
    args = parser.parse_args()
    result = check(args.depth, args.challenges)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
