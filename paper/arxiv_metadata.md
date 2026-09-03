# arXiv submission metadata

## Title

IEPP: Entropy-Anchored Canonical Continuation for Copyable AI Agents

## Authors

Woocheol Seo

## Primary category

cs.CR (Cryptography and Security)

## Cross-list

cs.AI (Artificial Intelligence)

## Comments

10 pages, 4 tables. Includes the evidence-led evolution from preliminary entropy and statistical hypotheses to registry-relative canonical continuation. Public reference implementation and reproducibility artifacts are available at https://github.com/swc8121-alt/iepp.

## Abstract

Long-running AI agents can be copied, snapshotted, rolled back, migrated, and forked. A static identifier or signing key authenticates a credential holder, but does not show that one execution is the accepted continuation of a previously observed execution. We call this the canonical-continuation problem and present the Individual Entity Proof Protocol (IEPP), an early-stage protocol for registry-relative execution-lineage verification. IEPP binds a fresh challenge, monotonic counter, current canonical commitment, declared-entropy commitment, optional runtime and attestation commitments, and enrolled signing key into authenticated transition evidence. An atomic registry accepts at most one successor of a canonical head. We refine the Trajectory Reconstruction Problem as TRP 2.0, a capability-indexed Canonical Continuation Game spanning observation, copying, state leakage, snapshots, entropy influence, key-plus-state compromise, and registry or platform compromise. In a public Python implementation, 50,000 of 50,000 valid transitions were accepted; no false acceptance was observed in 10,000 trials each of replay, rollback/losing-fork, and signed-field substitution; no double acceptance was observed in 1,000 fork races; and bounded exploration covered 1,063,623 states and 2,319,131 transitions without invariant violation. Single-host durability tests covered F00--F12 fault points. Negative controls show that entropy commitments do not certify unpredictability, a clone with the current key and state can win an L1 race, isolated registries can split, and output statistics do not identify an original. The evidence supports a narrow L1 single-registry software claim, not metaphysical identity, entropy quality, distributed safety, production readiness, or security after complete compromise.

## Submission files

- `iepp_arxiv_v1.tex`
- `references.bib`

The source builds with pdfLaTeX and BibTeX. Do not upload generated auxiliary files.
