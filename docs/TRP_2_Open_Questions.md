# TRP 2.0 Open Research Questions

1. What is the minimal ideal-registry functionality needed for a useful reduction without assuming away distributed split views?
2. How should corruption timing be modeled when a snapshot contains state but not a hardware-protected signing key?
3. Can proactive key/state refresh give meaningful post-compromise continuation security after a bounded exposure window?
4. Which entropy properties are actually necessary for each evidence level: uniqueness, min-entropy, unpredictability, provenance, or only freshness commitment?
5. How should verifier-selected challenges be audited against malicious or biased challenge strategies?
6. What checkpoint gossip/quorum assumptions provide measurable L3 split-view detection guarantees?
7. How should authorized migration distinguish legitimate continuity transfer from clone promotion?
8. Which parts of TRP can be proven from standard cryptographic assumptions and which remain systems/platform properties?
9. What benchmark best represents partial-state leakage without accidentally granting the full A5 capability set?
10. How should TRP results compose across multi-agent systems where one agent delegates authority to another?
