# arXiv submission metadata

## Title

IEPP: Policy-Relative Canonical Continuation for Copyable AI Agents

## Authors

Woocheol Seo

## Primary category

cs.CR (Cryptography and Security)

## Cross-list

cs.AI (Artificial Intelligence)

## Comments

11 pages, 2 figures, 5 tables. Includes an entropy-field ablation and the evidence-led evolution from preliminary entropy and statistical hypotheses to registry-relative canonical continuation. Public reference implementation and reproducibility artifacts are available at https://github.com/swc8121-alt/iepp.

## Abstract

Long-running AI agents can be copied, snapshotted, rolled back, migrated, and forked. A static identifier or signing key authenticates a credential holder, but does not show that one execution is the accepted continuation of a previously observed execution. We call this the canonical-continuation problem and present the Individual Entity Proof Protocol (IEPP), an early-stage protocol for registry-relative execution-lineage verification. IEPP binds a fresh challenge, monotonic counter, current canonical commitment, declared evidence, and enrolled signing key into an authenticated transition. An atomic registry accepts at most one successor of a canonical head. TRP 2.0 is a capability-indexed Canonical Continuation Game spanning observation through key-plus-state and registry compromise. A public L1 implementation accepted 50,000 valid transitions and recorded no false accepts in 10,000 trials each of replay, rollback/losing-fork, and signed-field substitution, no double accepts in 1,000 fork races, and no invariant violation in a bounded exploration of 1,063,623 states and 2,319,131 transitions. An ablation that removed both entropy fields likewise recorded no replay false accept in 10,000 trials and no double accept in 1,000 races, confirming that canonical serialization comes from freshness, predecessor agreement, and atomic head update rather than entropy. A declared entropy commitment remains a policy and audit hook; it does not certify unpredictability. Current-key-plus-state compromise and isolated registries remain explicit failure boundaries. The evidence supports only a narrow L1 single-registry software claim.

## Submission files

- `iepp_arxiv_v1.tex`
- `references.bib`

The source builds with pdfLaTeX and BibTeX. Do not upload generated auxiliary files.
