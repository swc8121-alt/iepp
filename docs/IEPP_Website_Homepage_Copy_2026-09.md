# IEPP website replacement copy — 2026-09

This file is the paste-ready source for the public WordPress pages. It deliberately matches the current L1 evidence boundary.

## Front page

Page title: `IEPP — Canonical Continuation for Copyable AI Agents`

```html
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Credential authenticity is not execution continuity.</h3>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Individual Entity Proof Protocol (IEPP) is an early-stage research protocol and pilot architecture for testing whether an enrolled AI agent or digital entity presents the next <strong>policy-authorized continuation</strong> of a previously accepted execution lineage.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Status:</strong> L1 software research prototype · Not production ready · PCT application filed · Bounded paid pilots available</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">The operational problem</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>AI agents can be snapshotted, rolled back, restored, migrated, and forked. A copied agent may possess the same model, identifier, signing key, and saved state as another branch. Conventional identity and access management can authenticate the credential holder, but that alone does not decide which competing execution is allowed to continue a protected workflow.</p>
<!-- /wp:paragraph -->

<!-- wp:quote -->
<blockquote class="wp-block-quote"><!-- wp:paragraph -->
<p>IEPP asks a narrower question: is this candidate the next continuation accepted by the declared registry and governance policy?</p>
<!-- /wp:paragraph --></blockquote>
<!-- /wp:quote -->

<!-- wp:heading -->
<h2 class="wp-block-heading">How the L1 prototype works</h2>
<!-- /wp:heading -->

<!-- wp:list {"ordered":true} -->
<ol class="wp-block-list"><!-- wp:list-item -->
<li>The verifier issues a fresh, entity-bound challenge.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>The agent signs transition evidence binding the challenge, monotonic counter, previous canonical commitment, candidate state, runtime commitment, and declared entropy source.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>One registry validates the evidence and atomically replaces the canonical head only if the presented predecessor is still current.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>The integrating application permits the protected action only after canonical acceptance. A competing successor is rejected as a losing fork or used-challenge attempt.</li>
<!-- /wp:list-item --></ol>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>IEPP is designed to complement signatures, IAM, agent identity, provenance, and future TPM/TEE attestation. It does not replace them.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Current public evidence</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>50,000 of 50,000 valid transitions accepted in the Ed25519 reference core.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>0 false accepts observed in 10,000 replay, rollback/losing-fork, and signed-field substitution trials per tested class.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>0 double accepts observed in 1,000 in-memory single-registry fork races.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>0 double accepts and exactly one cooperative simulated protected action per trial in 100 signed HTTP-registry A3 loopback races.</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>These are finite L1 software observations under the published test models—not a formal proof, independent certification, completed VirtualBox experiment, or production guarantee.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons -->
<div class="wp-block-buttons"><!-- wp:button -->
<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://github.com/swc8121-alt/iepp">Review the public code and evidence</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->

<!-- wp:heading -->
<h2 class="wp-block-heading">What IEPP does not claim</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>It does not prove consciousness, personhood, legal identity, physical uniqueness, or a metaphysical “original.”</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>If an attacker has the current key and state, the first valid branch accepted by the registry can win.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Two isolated registries can accept conflicting branches; L3 witness, quorum, or transparency mechanisms remain future work.</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Current public tests do not establish entropy quality, protected hardware binding, malicious-runtime resistance, or production readiness.</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:heading -->
<h2 class="wp-block-heading">IEPP Safe-Resume Pilot</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>The first commercial offer is a bounded integration pilot for one high-value AI-agent workflow. A typical pilot instruments one protected action—such as deployment, payment initiation, credential use, or an irreversible external command—and tests replay, rollback, restore, and same-credential fork behavior against an explicit acceptance policy.</p>
<!-- /wp:paragraph -->

<!-- wp:list -->
<ul class="wp-block-list"><!-- wp:list-item -->
<li>Threat and trust-boundary workshop</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>One workflow integration and canonical-decision API</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Controlled replay, rollback, and competing-resume demonstration</li>
<!-- /wp:list-item -->

<!-- wp:list-item -->
<li>Machine-readable evidence, audit trail, limitations, and go/no-go report</li>
<!-- /wp:list-item --></ul>
<!-- /wp:list -->

<!-- wp:paragraph -->
<p>The pilot is intentionally narrow and complements the customer’s existing IAM and authorization stack.</p>
<!-- /wp:paragraph -->

<!-- wp:buttons -->
<div class="wp-block-buttons"><!-- wp:button -->
<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="mailto:iepp.protocol@gmail.com?subject=IEPP%20Safe-Resume%20Pilot">Request a bounded pilot</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->

<!-- wp:heading -->
<h2 class="wp-block-heading">한국어 요약</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>IEPP는 AI의 의식이나 형이상학적 원본을 증명하지 않습니다. 복제·스냅샷·롤백이 가능한 AI 에이전트가 보호 작업을 다시 시작할 때, 등록된 단일 registry와 정책을 기준으로 <strong>이 후보가 이전에 승인된 실행 계보의 다음 canonical continuation인지</strong> 검사하는 연구 프로토콜입니다.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>현재 공개 증거는 소프트웨어 키·상태와 단일 registry를 사용하는 L1 실험에 한정됩니다. 첫 유료 제공 범위는 한 개의 고위험 에이전트 작업에 IEPP 판단 gate를 연결하고, replay·rollback·동일 자격증명 fork를 통제된 환경에서 검증하는 제한형 파일럿입니다.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Research, attribution, and patent status</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>Individual Entity Proof Protocol (IEPP) was conceived and developed by <strong>Woocheol Seo</strong>, independent researcher, Republic of Korea. Patent status: PCT international application <strong>PCT/IB2026/051545</strong>, filed 18 February 2026. “Patent filed” does not mean granted, certified, or independently validated.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>Earlier pages used the historical terms “Intrinsic Entropy Proof of Presence,” “trajectory-based identity protocol,” and “AI existence proof.” Current claims must be interpreted through the narrower registry-relative formulation and its declared limitations.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Contact:</strong> <a href="mailto:iepp.protocol@gmail.com">iepp.protocol@gmail.com</a> · <a href="https://github.com/swc8121-alt/iepp">GitHub research repository</a></p>
<!-- /wp:paragraph -->
```

## Fingerprint archive page

Page title: `Historical Fingerprint Concept — Paused`

```html
<!-- wp:heading -->
<h2 class="wp-block-heading">Historical research direction — currently paused</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>This page preserves an earlier IEPP-adjacent concept involving entropy-derived fingerprint or watermark representations.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>Status as of September 2026:</strong> this direction is paused. No active PCT-preparation claim is made for the fingerprint concept on this site. Fingerprinting, watermark survival, and content-origin detection are outside the current IEPP L1 protocol claim.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p>The current IEPP research focus is policy-relative canonical continuation for copyable AI agents: authenticated predecessor-bound transitions, fresh challenges, monotonic counters, and atomic single-registry successor acceptance.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><strong>한국어:</strong> 이 페이지는 과거의 entropy fingerprint/watermark 연구 방향을 기록하기 위한 보존 페이지입니다. 2026년 9월 현재 해당 연구는 보류 상태이며, fingerprint 기술에 대한 PCT 준비 중이라는 주장을 하지 않습니다. 현재 IEPP의 공개 범위는 복제 가능한 AI 에이전트의 registry-relative canonical continuation에 한정됩니다.</p>
<!-- /wp:paragraph -->

<!-- wp:paragraph -->
<p><a href="https://entropyproof.com/">Return to the current IEPP overview</a></p>
<!-- /wp:paragraph -->
```
