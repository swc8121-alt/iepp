# TRP 2.0 Threat Coverage Matrix

| Threat | Primary control | Evidence dependency | v0.1 status |
|---|---|---|---|
| exact replay | single-use challenge + accepted-evidence state | L1 | bounded model |
| challenge substitution | authenticated challenge binding | L1 | bounded concept / integration pending |
| wrong-key clone | authentication | L1 | bounded model |
| stale rollback | canonical predecessor + counter | L1 | bounded model |
| fork race | atomic single-successor update | registry | bounded model; real concurrency pending |
| snapshot clone | predecessor policy + protected authority | L1/L2 | real snapshot pending |
| entropy freeze | entropy profile/downgrade policy | profile dependent | pending |
| key+state theft | protected state/key, refresh, recovery | L2+ | explicit L1 boundary |
| registry equivocation | signed checkpoints + gossip/quorum/anchor | L3 | pending |
| physical replacement | physical binding/lifecycle | L4 | future work |

Coverage means the threat has a named control/test target. It does not mean the control has been proven secure in every deployment.
