# MIRAS.ART Digital Artwork Passport Platform
## Technical Proposal

---

## Solution Overview

### 1.1 Business Context

MIRAS.ART addresses a critical gap in the global art market: the absence of a tamper-proof, compliance-grade identity layer for physical artworks. The EU Anti-Money Laundering Regulation (EU Regulation 2024/1624), in force since 2024, requires art market professionals to apply rigorous KYC/AML controls to high-value transactions. Yet the tools available today are fragmented, manual, and entirely disconnected from the artwork's physical identity.

MARGIN International LLC has engineered a proprietary 5-layer authentication architecture protected by two Italian UIBM patents. The fundamental innovation is that artwork authentication and transaction compliance are architecturally inseparable: a forgery attempt automatically elevates the AML risk score. ScienceSoft is proposing to build the full software platform realising this architecture.

MIRAS.ART is a neutral infrastructure platform — it does not buy, sell, or broker artworks. Its value derives entirely from the trust every market participant places in its data. The platform connects a heterogeneous set of human actors and external systems through a single compliance-grade registry, where each participant reads or writes according to their role and accreditation level. The diagram below shows all actors and external system dependencies at C4 Level 1 (System Context).

> **Discovery & Validation commitment.** The RFQ and supporting patent documentation were developed with AI assistance — the conceptual architecture is substantive and the UIBM patent claims are well-founded. ScienceSoft's engagement opens with a dedicated Phase 0 Discovery sprint (see Delivery Phasing below) in which a BA and Solutions Architect verify every technical claim against the patent specifications, surface discrepancies, resolve ambiguous scope, and produce a signed-off architecture before any code is written. *We do not just build — we validate, refine, and de-risk the architecture.*

![MIRAS.ART System Context — C4 Level 1: all actors and external system dependencies](illustrations/fig_c4_system_context.png)

*Figure 1. MIRAS.ART System Context (C4 Level 1): 10 platform actors (Art Market supply/demand on the left; Compliance & Institutions on the right), 1 regulatory recipient (FIU/AMLA), and 1 external-system integration group (Art Loss Register / Interpol).*

#### Stakeholder Role Reference

| # | Role | Type | Platform Role | Key Interests | Source & Client Quote |
|---|------|------|--------------|---------------|-----------------------|
| 1 | Artist | External — Supply | artist | Simple self-service onboarding; prove authorship from date of creation; no compliance burden | ArchNotes §6.1: *"RS0a: fully automated. The artist opens the app, takes the photos, the system generates the Visual DNA and anchors it on the blockchain. Zero MIRAS intervention."* |
| 2 | Institutional Curator (Tier I / II / III) | External — Supply | curator | Pipeline efficiency; co-sign workflow; MIRAS accreditation as market credential; cost passed to client | Whitepaper §03: *"Only formally accredited Institutional Curators and Agent Curators with institutional co-signatures can produce passports at this tier."* |
| 3 | Agent Curator | External — Supply | curator | Automatic 15–20% revenue share; no invoicing overhead; accreditation as professional differentiator | Whitepaper §03: *"MIRAS returns a percentage — indicatively fifteen to twenty percent — of the passport fees they produce. No invoicing, no commissions to chase: the revenue share is automatic."* |
| 4 | Collector / Buyer / Seller | External — Demand | viewer | Documented chain of title for lending and insurance; friction-free transfer via QR or NFC tap | RFQ §6 B5: *"Seller initiates, buyer accepts via QR or NFC tap. Both parties must pass KYC before transfer completes. Transfer event triggers automatic AML risk recalculation."* |
| 5 | Compliance Officer | Institutional (Gallery / Auction House) | compliance\_officer | Pre-populated STR narrative; Orange/Red queue management; decision audit trail defensible to AMLA | RFQ §5.1 A13: *"Queue of transactions requiring review; detailed scoring breakdown with explanatory narrative per variable; decision workflow: approve / request additional info / escalate / file STR."* |
| 6 | Art & Compliance Analyst | Internal (MIRAS) | analyst | Flagged-cases-only review; system prepares data → human verifies; 15–25 min / RS1a, ~2 h / RS1b | ArchNotes §6.3: *"This is not an artistic appraisal — it is a coherence check. In Y1, with 800 RS0a registrations and 8 RS1b passports, one person is more than enough."* |
| 7 | Admin (MIRAS) | Internal (MIRAS) | admin | User lifecycle; AML threshold and modifier configuration; ML model versioning | RFQ §5.1 A11: *"User management with RBAC (admin, compliance officer, analyst, viewer). AML threshold configuration. ML model management (retraining triggers, version history, performance metrics)."* |
| 8 | Art Finance Lender / Bank | External — Demand | api\_client | 48 h loan approval vs. 4–8 weeks; LTV monitoring; defensible compliance documentation | RFQ §5.1 A9: *"Institutional API for banks, insurers, and lenders to query Passport status and risk scores. Configurable data sharing levels (full passport, compliance summary only, risk score only)."* |
| 9 | Wealth Manager / Insurer | External — Demand | api\_client | Machine-readable price indices and risk benchmarks; first systematic intelligence layer for the art market | Whitepaper §01: *"The aggregated dataset — price histories, condition records, lending performance, market indices — becomes the first systematic, machine-readable intelligence layer the art market has ever had."* |
| 10 | Customs Authority | External — Demand | api\_client | Real-time cultural property compliance check; replaces manual paper documentation | RFQ §1.1: *"Web Platform — a Bloomberg-style archive and due-diligence dashboard for institutional users (auction houses, galleries, lenders, insurers, customs authorities, compliance officers)."* |
| 11 | FIU / AMLA | Regulatory — External | — (report recipient) | Structured machine-readable STR; ≥10-year audit trail; immutable blockchain anchor | RFQ §4.6: *"Retention: minimum 10 years for AML audit trail (exceeds regulatory 7-year requirement)."* ArchNotes §4: *"goAML is the software platform developed by UNODC that most Financial Intelligence Units worldwide use to receive and manage Suspicious Transaction Reports."* |
| 12 | Art Loss Register / Interpol | External System | — (API integration) | Stolen art data exchange; Trap Mode delivers GPS/device data on fraudulent NFC taps | ArchNotes §2.4: *"The old NFC tag is NOT invalidated immediately — we leave it active in 'trap' mode, so every tap on the fake registers GPS position, timestamp, and device ID. Data shareable with Interpol, Art Loss Register, and the competent FIU."* |

> **Registration trust tiers.** Artist Self-Certified passports establish authorship provenance. Institutional Curator passports (Tier I automatic via CINOA/TEFAF/ADAA; Tier II standard; Tier III provisional with enhanced MIRAS review) are required for art-secured lending, insurance, and regulated transactions. Agent Curator submissions are published only after an Institutional co-signature. Every passport is tagged with its registration path and trust level, visible to all subscribers.

---

### 1.2 The Five-Layer Architecture

The MIRAS.ART platform is structured as five interlocking protection layers, each building on the foundation beneath it:

![MIRAS.ART Platform Overview — Five-layer architecture from physical artwork to Artwork Passport and AML decision](illustrations/fig1_platform_overview.png)

*Figure 2. MIRAS.ART high-level platform architecture: physical artwork passes through five protection layers to produce a verifiable Artwork Passport and a compliance-grade AML transaction decision.*

| Layer | Name | What It Establishes |
|-------|------|---------------------|
| Layer 100 | Visual DNA Engine *(PoP L1)* | Digital identity of the artwork's physical appearance: 64-bit pHash + 384-dim DINOv2 embedding + 32-descriptor Gabor filter bank, combined via SHA-256 binding of three independent visual features into a single cryptographic fingerprint. Patent-specified matching thresholds: pHash Hamming distance ≤ 8, DINOv2 cosine similarity ≥ 0.92, Gabor MSE ≤ 0.15. |
| Layer 300 | NFC Physical Binding *(PoP L2)* | Cryptographic link between digital identity and physical object: NXP NTAG 424 DNA chip with AES-128 encryption, SUN messaging protocol, CMAC rolling authentication, TagTamper tamper-evidence wire |
| Layer 400 | Dual-Layer Blockchain | Immutable provenance ledger: Hyperledger Fabric (private, RBAC, full transaction data) anchored to Polygon EVM (public, SHA-256 hashes only, daily Merkle tree batching) |
| Layer 500 | Compliance | Regulatory identity verification: KYC via Sumsub, ALR screening, UNESCO 1970 / UNIDROIT 1995 treaty compliance, GDPR-compliant data handling |
| Layer 600 | AML Risk Scoring | Transaction risk engine (Patent 2): 26 scoring variables across three engines (CSE/ASE/TSE), 10 contextual modifiers, four decision bands (GREEN/YELLOW/ORANGE/RED) |

> *Patent 1 — UIBM Application No. 102026000009442, filed April 2026: covers Layers 100–500, 18 claims.*  
> *Patent 2 — UIBM Pending, filed 15 April 2026: covers Layer 600, 17 claims.*

The five-layer architecture is designed so that no single component constitutes a single point of failure. Visual DNA, NFC, and blockchain each independently verify artwork authenticity — any single layer can be checked in isolation, and all three must agree for a full-confidence result. On the compliance side, KYC, ALR screening, and the AML scoring engine operate as independent verification gates. The platform remains operationally degraded but functional if any one external data source is temporarily unavailable; circuit-breaker patterns ensure failed external calls never cascade into platform downtime.

### 1.2.1 Proof of Physical Existence — Three-Tier Physical Authentication

The three physical verification mechanisms — Visual DNA (Layer 100, PoP L1), NFC Physical Binding (Layer 300, PoP L2), and Spectral Certification (PoP L3, expert tier) — form the *Proof of Physical Existence* (PoP) framework. All three levels must be simultaneously defeated for a forged artwork to pass authentication undetected.

**PoP Level 3 — Spectral Certification (Expert Tier).** MIRAS offers spectral certification through partnerships with accredited conservation laboratories. The analysis applies the full suite of material science techniques directly to the physical artwork:

- Multispectral imaging under ultraviolet (UV) and infrared (IR) illumination — UV fluorescence reveals prior restorations, later overpainting, aged varnish layers, and anomalous signatures; IR reflectography exposes underdrawing beneath surface paint
- Raking-light documentation of surface relief and physical condition
- Pigment composition analysis through X-ray fluorescence (XRF) and Raman spectroscopy
- Three-dimensional craquelure mapping via Optical Coherence Tomography (OCT)

Spectral certification results are hashed and anchored to Hyperledger Fabric as a separate, timestamped event linked to the Artwork Passport record. Completion of PoP L3 elevates the passport's verification level to Expert Tier — displayed in the Public Registry (Phase 1 deliverable, see Phase 1 module PUBLIC-REG) and returned in Institutional API responses. Replicating a spectral signature requires recreating the exact chemical composition of the original historical pigments, making material forgery effectively impossible to execute undetected.

**Anti-forgery defence matrix.** Each PoP level blocks a distinct attack class:

| Attack Vector | PoP L1: Visual DNA | PoP L2: NFC Binding | PoP L3: Spectral Certification |
|---|---|---|---|
| Photograph & reproduce | Blocked — copy has different material texture; hash mismatch | Blocked — tag cannot be cloned | Blocked — spectral signature cannot be replicated |
| Remove NFC from original, attach to forgery | Blocked — forgery Visual DNA mismatches stored hash | Blocked — tamper-evident tag self-destructs on removal | Blocked — spectral data of forgery mismatches stored hash |
| Register forgery through corrupt curator | Partial — Visual DNA recorded; cross-check available on re-verification | N/A — tag applied at registration by curator | Blocked — spectral analysis reveals material inconsistency |
| Compromise MIRAS database | Blocked — Visual DNA hash on blockchain; mismatch detectable | Blocked — NFC binding record on blockchain | Blocked — spectral hash on blockchain |

Partner laboratories: CIRAM (Paris), MATIS/CSEM (Switzerland), Art+Image (Germany), Hephaestus (Greece), SAT (Italy).

---

### 1.3 The Integration Innovation: Patent 1 Powers Patent 2

The architectural distinguisher that separates MIRAS.ART from any existing compliance tool is the live data bridge between authentication and risk scoring. Three of the nine variables in the AML Artwork Scoring Engine (ASE) draw their inputs directly from the authentication layers at transaction time:

![Patent 1 to Patent 2 integration: A5, A6, A8 data flows from authentication layers into the AML Artwork Scoring Engine](illustrations/fig2_patent_integration.png)

*Figure 3. Three real-time data feeds from Patent 1 layers flow into the Patent 2 AML Artwork Scoring Engine (ASE, β = 0.35). A failed physical authentication automatically elevates the composite AML risk score.*

| AML Variable | Source Layer | What It Measures |
|-------------|-------------|-----------------|
| A5 Visual DNA Verification Score | Layer 100 (Visual DNA) | Cosine similarity between current photograph and the registered DINOv2 canonical embedding; detects visual substitution |
| A6 NFC Authentication Status | Layer 300 (NFC Binding) | CMAC code validity, tap counter freshness, TagTamper wire integrity; detects physical chip tampering |
| A8 Blockchain Integrity Index | Layer 400 (Blockchain) | Hyperledger Fabric ↔ Polygon hash synchronisation, chain continuity since registration; detects ledger manipulation |

This means: a forged artwork cannot be sold through a MIRAS.ART-compliant channel without triggering an AML flag. The two systems are not integrated after the fact — they are designed as a closed loop from first principles.

Additionally, four of the ten contextual modifiers (M7–M10) are MIRAS-exclusive, derived exclusively from Patent 1 runtime data:

- M7 — Visual DNA verification failure modifier (ASE A5 > 50)
- M8 — NFC authentication compromise modifier (ASE A6 > 50)
- M9 — Freeport / non-cooperative destination modifier (TSE T4 > 50)
- M10 — Cross-layer custody chain inconsistency modifier (ASE A8 > 50)

---

## Technology Stack

### 2.1 Architecture Pattern: Modular Monolith + Selective Microservices

A full microservices split would maximise long-term scalability but front-loads significant distributed-systems overhead (network partitions, distributed transactions) before the domain model is even stable — an unnecessary risk for a Phase 1 team. A traditional layered monolith is quick to start but creates the tight coupling that would make Phase 3 AML engine extraction expensive. ScienceSoft recommends a Modular Monolith with two selective Python microservices: all core business logic ships as a single Go deployment with enforced internal domain boundaries, while only the two operations that genuinely require Python runtimes — Visual DNA (GPU inference) and AML Scoring (ML libraries) — are extracted from day one. This reaches Phase 1 MVP without closing the door to a full microservices migration at Phase 4.

![Recommended Architecture: Go Modular Monolith with Visual DNA and AML Python microservices](illustrations/fig3_recommended_architecture.png)

*Figure 4. Platform architecture overview: Go Modular Monolith with ten domain modules, two Python microservices, and Asynq task queues for async operations.*

The Go Modular Monolith handles all core business logic as a single deployable unit with enforced internal domain boundaries. Ten modules ship inside the monolith:

| # | Service | Description |
|---|---------|-------------|
| 1 | KYB/KYC Onboarding | Institutional identity verification via Sumsub |
| 2 | Passport & Provenance | Artwork registration and lifecycle management |
| 3 | Billing & Subscriptions | Stripe-based subscription and tier management |
| 4 | Artist Self-Service | Independent artist onboarding with light identity check |
| 5 | NFC Tag Shop | NFC chip procurement and fulfillment |
| 6 | Compliance Dashboard | AML alert review and STR filing workflow |
| 7 | Institutional API | B2B integration endpoints for banks, insurers, and customs |
| 8 | Blockchain Anchoring | Hyperledger Fabric writes and daily Polygon Merkle anchoring |
| 9 | Admin & Config | RBAC, feature flags, and multi-tenancy configuration |
| 10 | Notifications | Event-driven alerts via email and webhook |

All async operations — Visual DNA processing, blockchain writes, PDF passport generation, and AML scoring — run through Asynq task queues backed by Redis. Persistent data lives in PostgreSQL 16 (with pgvector for artwork similarity queries) and AWS S3 for documents and PDFs. Blockchain provenance records are written to Hyperledger Fabric via Amazon Managed Blockchain; daily digest hashes are anchored to Polygon EVM for public verifiability.

Two Python microservices operate outside the monolith and are invoked asynchronously:

| # | Service | Description |
|---|---------|-------------|
| 1 | Visual DNA Microservice | Dedicated GPU node combining perceptual hashing, Gabor texture analysis, and DINOv2 deep embeddings to produce a tamper-evident artwork fingerprint. *Implements Patent 1 Layer 100 (Visual DNA Engine).* |
| 2 | AML Scoring Microservice | Stateless ML service scoring all 26 risk variables across the CSE/ASE/TSE composite engine. *Implements Patent 2 Layer 600 (AML Artwork Scoring Engine).* |

NFC chip authentication is handled within the Go Monolith, with cryptographic keys in AWS Secrets Manager. *Implements Patent 1 Layer 300 (NFC Physical Binding).* Clients connect via a Next.js 14 web dashboard and React Native 0.74 mobile app. External compliance data feeds — Dow Jones, Refinitiv, ComplyAdvantage, Art Loss Register, Interpol, ICOM Red Lists — are integrated progressively from Phase 2 onward.

> **Every architectural decision has been made to stay as close to the patent specification as technically viable, protecting the IP moat.** The Go + Python dual-runtime model ensures that Patent 1 Layer 100 (GPU-accelerated Visual DNA) and Patent 2 Layer 600 (ML-based AML scoring) remain in their optimal runtimes, while the Go core handles all compliance-grade transactional logic with predictable latency guarantees.

---

## Delivery Phasing

The delivery plan structures work into five stages, opening with a time-boxed discovery sprint. Phase 0 validates the architecture and produces a signed-off backlog; Phase 1 delivers institutional KYB/KYC onboarding and the core artwork registration and passport issuance capability. Phase 2 adds NFC physical binding, dual-layer blockchain, and ownership transfer. Phase 3 activates the full Patent 2 AML scoring engine. Phase 4 completes the adaptive ML layer and opens the institutional portal.

| Phase | Core Delivery | Modules | Phase Exit Criterion |
|-------|--------------|---------|----------------------|
| Phase 0 | Discovery & Architecture Validation | BA + Architect sprint: Requirements Validation Report, Patent Alignment Map, ADR, Phase 1 Backlog | Client and ScienceSoft sign-off on validated architecture before development begins |
| Phase 1 | Institutional KYB/KYC onboarding, artwork registration: mobile capture, Visual DNA fingerprinting, provenance chain, PDF export, Public Registry | A1, A2, A3, A10, A11, B1, B6, KYC/Sumsub, PUBLIC-REG | Verified institution can photograph, fingerprint, and issue a verifiable PDF Artwork Passport; any person can independently verify an Active Passport via the Public Registry |
| Phase 2 | ALR integration, NFC physical binding, dual-layer blockchain, KYC-gated ownership transfer, PoP L3 Spectral Certification, Billing & Subscription Management | A4, A6, A7, B2, B3, B4 (base), B5 (base), Fabric + Polygon, SPECTRAL-CERT, BILLING | NFC-linked artwork can be verified and transferred on-chain with both parties identity-verified; spectral certification workflow available for Expert Tier passports |
| Phase 3 | AML risk scoring engine: full Patent 2 implementation, 26 variables, 8 data integrations | A5, A12, A13, B4 (update — adds AML risk score field), B5 (update — adds AML recalc trigger), AML Engine, External APIs | Transaction scored 0–100 in ≤5s; ORANGE/RED decisions routed to compliance review; audit trail complete |
| Phase 4 | ML enhancement, institutional portal, security audit | A8, A9, B7, B8, ML Module, STR Automation | Adaptive risk thresholds live; multi-institution portal operational; independent penetration test passed |

---

## Phase 0 — Discovery & Architecture Validation

Phase 0 is a time-boxed sprint that runs before any development begins. A ScienceSoft Business Analyst, Solutions Architect, and DevOps / Cloud Engineer work through every module in the RFQ, verify all technical claims against the two UIBM patent specifications, and produce six mandatory artefacts. No Sprint 1 work starts until the Phase 0 exit criterion is met.

| Deliverable | Description |
|---|---|
| Requirements Validation Report | BA reviews all RFQ modules (A1–A13, B1–B8), identifies gaps, contradictions, and ambiguous scope; resolves open questions with MIRAS |
| Patent Alignment Map | Architect maps both UIBM patent specifications to concrete system components; confirms the proposed technology stack fully implements all patent claims |
| Architecture Decision Record (ADR) | Confirms or revises the recommended architecture with documented rationale for each key technology decision |
| AWS Cloud Infrastructure Design | VPC topology, service layout across dev / staging / prod environments, Amazon Managed Blockchain provisioning, GPU node setup for Visual DNA, S3 / RDS / Secrets Manager configuration |
| CI/CD Pipeline Design | GitHub Actions workflows for automated build, test, container publishing, and environment promotion; branch strategy, secrets management, and rollback procedures |
| Phase 1 Backlog | Complete story-map with effort estimates and acceptance criteria for all Phase 1 modules, ready for Sprint 1 kick-off |

> **Phase 0 exit criterion:** Client and ScienceSoft jointly sign off on the validated architecture before development begins. This protects MARGIN against "we built the wrong thing" and protects ScienceSoft against scope creep from undiscovered requirements.

---

## Phase 1 — Foundation & Visual DNA MVP

Phase 1 delivers the foundational platform: institutional KYB/KYC onboarding via Sumsub, mobile-guided artwork registration, Visual DNA fingerprinting, provenance chain management, and verifiable PDF Artwork Passport issuance. At Phase 1 exit, a verified institution can onboard artworks end-to-end via the mobile app, review and manage them in the web dashboard, and deliver compliance-ready PDF passports to clients. Phase 1 is intentionally self-contained and production-deployable without NFC hardware, blockchain, or AML scoring.

### Institutional KYB/KYC Onboarding

All platform users — galleries, museums, and auction houses — are organisations, not individuals. Before an institution can register artworks on the platform, it must first complete KYB (Know Your Business) verification via Sumsub: beneficial ownership disclosure, business registration confirmation, AML policy review, and sanctions screening of the entity and its principals. KYB/KYC verification is therefore part of Phase 1, integrated as a gate condition in the institutional onboarding flow. An organisation that has not cleared KYB cannot proceed to artwork registration.

> [!WARNING]
> - **Risk:** Institutional KYB onboarding timelines are unpredictable. A gallery failing to clear KYB may delay its own artwork registration regardless of platform readiness.
> - **Mitigation:** Initiate the KYB process for all initial platform participants at project kick-off, in parallel with Phase 1 development.

> **Phase 1 exit = Investor-Ready MVP.** The platform is production-deployable, demonstrable to institutional partners, and ready to support fundraising conversations and pilot agreements without requiring NFC hardware, blockchain infrastructure, or AML scoring. Timeline: *XX weeks from Phase 0 sign-off* (to be confirmed by PM during Phase 0).
Gallery scenario (Modules A1, A2, A3, A10, A11, B1, B6): a gallery employee opens the mobile app and selects Register Artwork. The app guides them through the 6-shot capture protocol — front view, reverse, and four corner close-ups — enforcing a quality gate of ≥80/100 per frame. On completion, the platform automatically computes the artwork's Visual DNA fingerprint, creates an Artwork Passport record with full provenance metadata, and generates a signed PDF passport with an embedded QR code. The complete onboarding flow takes under two minutes and requires no NFC hardware, blockchain infrastructure, or AML scoring.

![Phase 1 end-to-end flow: mobile 6-shot capture, Visual DNA fingerprinting pipeline, and Artwork Passport PDF issuance](illustrations/fig4_phase1_flow.png)

*Figure 5. Phase 1 end-to-end data flow: gallery employee follows the B1 guided 6-shot capture protocol; approved frames are processed by the Visual DNA Python microservice (pHash + DINOv2 + Gabor → SHA-256); the resulting fingerprint is stored in PostgreSQL with pgvector; a PDF Artwork Passport is generated and stored in S3.*

The Phase 1 data flow begins on the mobile device: the gallery employee follows the B1 guided 6-shot capture protocol, where `react-native-vision-camera` v4 Skia frame processors enforce a per-frame quality gate of ≥80/100 before any frame is accepted. All six approved frames are uploaded to S3 and a `visual-dna` task is enqueued in Asynq. The Visual DNA Python microservice picks up the job and runs three algorithms in parallel:

- `opencv-python` (`cv2.img_hash.PHash`) — perceptual hashing: compresses each frame to a 64-bit DCT signature; per-frame hashes aggregated by majority-vote
- `transformers` + `torch` — DINOv2 visual embedding: Meta AI Vision Transformer produces a 384-dimensional semantic vector per frame; six frame embeddings averaged into a single canonical embedding
- `opencv-python` — Gabor filter bank: 32 filters (8 orientations × 4 frequencies) extract surface microtexture — brushstroke direction, canvas grain, craquelure; produces a 32-element descriptor

All three outputs are serialised and combined with `hashlib.sha256()` into the 64-character Visual DNA fingerprint. The fingerprint and canonical embedding are written to PostgreSQL with a pgvector HNSW index (m=16, ef_construction=200) to enable sub-millisecond cosine similarity duplicate detection. A `pdf-generate` Asynq task then triggers chromedp (Go Chromium DevTools client) to render the branded Artwork Passport PDF, which is stored in S3 and linked to the passport record.

| Algorithm | Library | Description |
|-----------|---------|----------|
| pHash — 64-bit DCT perceptual hash | `opencv-python` | OpenCV `cv2.img_hash.PHash`; same library as Gabor; Apache-2.0 |
| DINOv2 — 384-dim visual embedding | `transformers` + `torch` | Meta AI ViT pretrained on 142M images; no labelled training data required; Apache-2.0 |
| Gabor filter bank — 8 orientations × 4 frequencies | `opencv-python` | Standard CV library; hardware-accelerated; Apache-2.0 |

The Artwork Passport record carries a unique identifier in the format `MIRAS-YYMMDD-XXXXX` and progresses through five statuses: Draft → Under Review → Cleared → Active → Archived. The A1 intake wizard captures all required artwork metadata — artist, title, medium, dimensions, date, edition — plus provenance entries and document attachments before the Visual DNA pipeline is triggered.

The remaining Phase 1 modules deliver a complete, production-ready platform alongside the Visual DNA core.

![Phase 1 module component architecture](illustrations/fig5_phase1_components.png)

*Figure 6. Phase 1 module architecture: nine modules across mobile (B1, B6), Go Monolith (KYB/KYC, A1, A2, A3, A10, A11), Visual DNA Python Microservice, and PUBLIC-REG Next.js portal; NFC, Blockchain, and AML layers deferred to Phases 2–4.*

### Public Artwork Registry

Any person — without registration, login, or subscription — can search the MIRAS registry by MIRAS ID, artist name, artwork title, or registering institution, and independently verify whether an artwork holds an Active Passport and at which PoP level it has been certified. The public response is strictly limited to the Identity layer: MIRAS ID, title, artist, medium, dimensions, year, current PoP level, blockchain verification hash, and registering institution. No ownership chain, valuation history, compliance documentation, or private collector data are exposed.

MIRAS.ART enforces a three-tier access model at the **infrastructure level** — not through application-layer access controls. The Public Registry is served from a read-only PostgreSQL replica scoped to the `artwork_identity` view with no network path to Vault data; the Subscriber API tier gates provenance and condition data behind API keys (Phase 4); the Vault tier holds compliance documentation, ownership chain, and AML scoring data under institutional authentication and RBAC.

![MIRAS.ART Public Registry — three-tier access model: Public Registry open to any person, Subscriber API for institutional clients, Vault for restricted compliance data; each tier enforced at infrastructure level](illustrations/fig_public_registry.png)

*Figure 7. MIRAS.ART three-tier access model: the Public Registry is served from a read-only database replica exposing only the Identity layer; the Subscriber API gates provenance and condition data; the Vault is institution-authenticated and case-authorised. Tier boundaries are enforced at the data infrastructure level — not through application-layer access control.*

Delivered as Next.js 14 server-side rendered pages via CloudFront CDN; no new infrastructure components required beyond the Phase 1 PostgreSQL read replica. The Public Registry is GDPR-compliant by construction — the public tier contains no personal data. *Phase activation note: in Phase 1 the registry surfaces only the Visual DNA SHA-256 fingerprint and registering institution; the «blockchain verification hash» field is populated automatically once Phase 2 ships (A6); PoP L3 Expert Tier badges appear once SPECTRAL-CERT is delivered in Phase 2.*

### Phase 1 Modules

| # | Module | Description |
|---|--------|-------------|
| KYB/KYC | Institutional Onboarding (Sumsub) | Institutional onboarding flow for galleries, museums, and auction houses. Before artwork registration is available to an organisation, it completes KYB verification via Sumsub: beneficial ownership disclosure, business registration confirmation, and sanctions screening of the entity and its principals. Verification status is stored against the organisation record and enforced as a gate condition on artwork intake. Individual KYC (for contact persons) follows the same Sumsub integration. |
| A1 | Artwork Intake & Passport Builder | Wizard-driven intake form capturing all required artwork metadata — artist, title, medium, dimensions, date, edition — plus provenance entries and document attachments. Auto-generates the unique Passport ID (`MIRAS-YYMMDD-XXXXX`) and drives the five-status workflow (Draft → Under Review → Cleared → Active → Archived). Triggers the Visual DNA processing pipeline upon image upload. |
| B1 | 6-Shot Capture & Visual DNA | Mobile guided capture interface enforcing the patent-specified 6-shot protocol (recto, verso, four detail zones). `react-native-vision-camera` v4 Skia frame processors apply a real-time per-frame quality gate (resolution, blur, lighting, colour calibration) with a minimum threshold of 80/100. Approved frames are uploaded to S3; final Visual DNA computation runs server-side on the GPU microservice. |
| A2 | Secure Document Vault | Stores all artwork images and supporting documents in AWS S3 with AES-256 server-side encryption. Accepted formats: JPEG, PNG, TIFF, PDF, DOCX. Every uploaded file passes virus scanning at ingestion; every access and download event is appended to an immutable audit trail. |
| A3 | Provenance Chain Builder | Records the initial provenance entry at registration and supports seven transaction types: purchase, inheritance, gift, consignment, loan, restitution, and auction. Each entry captures acquisition type, date, parties, supporting documents, and geographic location. Temporal and geographic gaps are flagged automatically; the system computes the Provenance Completeness Index — `PCI = (1 − GapYears / TotalYears) × 100` — the value that feeds directly into AML variable A1 of the Phase 3 Artwork Scoring Engine. *Note: RFQ Table 1 prints this formula as `PCI = 1 − (GapYears / TotalYears) × 100`, which yields negative values under standard operator precedence; the parenthesised form above matches the patent intent (PCI as a 0–100 completeness percentage) and will be confirmed in Phase 0 as part of the Patent Alignment Map.* |
| A10 | PDF Passport Generator | Generates the branded Artwork Passport PDF on demand via a `pdf-generate` Asynq task. chromedp (Go Chromium DevTools) renders a structured document containing artwork metadata, photographs, provenance chain, compliance status, and an embedded QR code linking to the public passport record. The PDF is stored in S3 and linked to the passport record. AML risk score summary field is present in the template but populated from Phase 3 onward. |
| A11 | Admin Panel | Ships in Phase 1 to make the platform operationally self-sufficient from day one. Provides user management under four RBAC roles — admin, compliance officer, analyst, and viewer. Subscription tier management: assigns and modifies Artist / Gallery / Enterprise tiers per account; enforces tier-based feature gating (AML scoring inaccessible on Artist tier; Institutional API restricted to Enterprise tier). Multi-tenancy configuration: per-tenant feature flags, rate limits, and data isolation boundaries. Market data feed configuration: Artnet/Artprice API credentials and quota monitoring for Market Intelligence (RS3); RS3 subscriber onboarding and API key provisioning. Configurable AML threshold settings (active from Phase 3). ML model management foundation required by Phase 4. Market Intelligence metrics dashboard: operational monitoring of Artnet/Artprice API quota consumption, RS3 subscriber activity, and price-index data freshness indicators. |
| B6 | Offline Mode | Implements an offline-first architecture in the React Native mobile app. All capture, quality-gate, and metadata entry operations function without network connectivity. Approved frames and form data are queued locally and submitted to the S3/Asynq pipeline via background sync once connectivity is restored — essential for gallery basements, art fairs, and auction previews where Wi-Fi is unreliable. |
| PUBLIC-REG | Public Artwork Registry | Public-facing, no-login search portal (Next.js 14 SSR, CloudFront CDN). Any person can search by MIRAS ID, artist name, artwork title, or registering institution and verify an Active Passport at its certified PoP level. Response limited to Identity layer only — no ownership chain, valuation history, or compliance data. Three-tier access model (Public Registry / Subscriber API / Vault) enforced at infrastructure level — see §Public Artwork Registry above. |

---

#### Commercial Enabler Modules — Phasing to be confirmed in Phase 0

The following modules arise from the three-tier commercial model (Artist / Gallery / Enterprise) and are architecturally required for a commercial launch. **Note:** this section covers commercial-enabler modules whose delivery phase has not yet been confirmed with MIRAS — it does not imply platform-wide availability across all phases. Institutional onboarding for galleries, museums, and curators is already a core Phase 1 deliverable (see KYB/KYC Institutional Onboarding above) and is not listed here. Phasing is subject to discussion with MARGIN as part of Phase 0.

| # | Module | Proposed Phase | Description |
|---|--------|---------------|-------------|
| BILLING | Billing & Subscription Management | Phase 2 | Stripe integration supporting three billing schemes: per-artwork (Artist tier, e.g. €20/artwork), monthly/annual subscription (Gallery tier, e.g. €149/year), and enterprise contract (Institutional tier, €100K+/year). Usage metering — passport count per Artist account. Subscription lifecycle: invoicing, dunning, upgrade/downgrade, cancellation. Required for any commercial deployment. *Patent alignment: none direct; commercial enabler for the platform's scalable distribution model.* |
| ARTIST | Artist Self-Service Onboarding | Phase 2 | Self-service registration for individual artists (not organisations). Email verification + Sumsub IDV light-KYC (identity document check only; no beneficial ownership disclosure). No compliance officer manual review required. Critical for bottom-up go-to-market: without this module there is no artist supply entering the platform. Delivered in Phase 2 as a dedicated early sprint in parallel with NFC development (Variant B — confirmed). |
| NFC-SHOP | NFC Tag Ordering & Fulfillment | Phase 2 | In-platform NFC tag ordering workflow: artist or curator requests tags → platform creates an order record → webhook/email to MARGIN ops team for fulfillment. Optional extension (Phase 3): fulfillment service integration (ShipBob / Sendcloud) for automated dispatch. Tags priced at margin above ~€0.70 COGS. |

#### Artist Self-Service Phasing — Decision

The ARTIST module is confirmed for Phase 2 as a dedicated early sprint running in parallel with NFC development (**Variant B**). Phase 1 scope remains focused on institutional KYB/KYC onboarding; artist self-service is decoupled from the Phase 1 critical path and delivered at the start of Phase 2, ensuring the capability is live before the broader platform launch. This enables the bottom-up go-to-market strategy — individual artists begin registering and generating Passport supply before the full NFC and blockchain layers are complete.

## Phase 2 — NFC, Blockchain & Compliance

Phase 2 completes the physical authentication layer by binding each registered Artwork Passport to an NFC chip embedded in the artwork, and anchoring provenance records to the dual-layer blockchain. It also activates the Art Loss Register integration that checks every artwork against the global stolen art database, enables KYC-gated ownership transfer — the first on-chain transaction lifecycle, built on the institutional identities already verified during Phase 1 onboarding — and ships the **PoP L3 Spectral Certification** workflow described in §1.2.1, allowing accredited conservation laboratories to upload spectral analysis results and elevate qualifying artworks to Expert Tier. At Phase 2 exit, any counterparty with a compatible smartphone can independently verify a MIRAS-registered artwork through a three-layer authentication cascade, every ownership change is recorded immutably with both parties identity-verified, and Expert Tier passports become available for the highest-value artworks.

NFC activation and verification scenario (Modules B2, B3, A4, A6, A7): a gallery employee opens the mobile app, selects a Phase 1 registered artwork, and taps Activate NFC Tag. The app uses the NXP TapLinx Android SDK 3.0 (or Apple CoreNFC on iOS) to read the NTAG 424 DNA chip UID and verify genuine chip authenticity. The SHA-256 Visual DNA digest computed in Phase 1 is then written to the chip's NDEF memory — establishing bidirectional binding: the chip stores the artwork's digital fingerprint; Hyperledger Fabric will map the chip UID back to the Artwork Passport. Simultaneously, the Art Loss Register API is queried; a clearance result is written to ASE variable A3. If cleared, the binding event is recorded on Hyperledger Fabric and the artwork advances to Active status. Later, when a prospective buyer scans the chip at an art fair to verify authenticity, the B3 module runs the three-layer cascade — Visual DNA match, NFC CMAC rolling-code check, blockchain integrity confirmation — and returns a per-layer confidence score with a single PASS / REVIEW / FAIL verdict.

![Phase 2 data flow: NFC chip binding, CMAC rolling authentication, and dual-layer blockchain anchoring](illustrations/fig6_phase2_nfc_blockchain_flow.png)

*Figure 8. Phase 2 data flow: mobile app writes Visual DNA SHA-256 to the NTAG 424 DNA chip NDEF payload; each subsequent verification tap generates a unique non-replayable CMAC code; the provenance record is written to Hyperledger Fabric and a daily SHA-256 Merkle root is anchored to Polygon EVM.*

The NFC authentication protocol relies on the NTAG 424 DNA chip's Secure Dynamic Messaging (SDM/SUN). The AES-128 secret key is stored in write-once chip hardware and never transmitted. On every tap, the chip computes a fresh CMAC code using the key, a monotonically increasing tap counter, and the chip UID. The MIRAS backend decrypts the PICC data block, recomputes the CMAC independently, and confirms the counter has strictly incremented since the last verified event — preventing replay of any previously captured tap. The TagTamper wire loop status is read on every verification call; a broken loop is recorded irreversibly in a protected chip register and routed to the compliance queue. No feasible key extraction attack exists without physically destroying the chip.

The blockchain layer applies a two-tier model that separates confidential provenance data from public verifiability. All full provenance records — ownership entries, condition reports, valuations, NFC binding events — are written to Hyperledger Fabric (Amazon Managed Blockchain, Year 1) under RBAC-enforced read permissions. A Blockchain Worker Go service runs daily: it collects all new Fabric transactions, constructs a Merkle tree, and anchors the SHA-256 root to Polygon EVM via an ERC-721-compatible token. Any third party can verify that a specific provenance record existed at a given point in time without accessing the confidential content.

![Phase 2 module component architecture: NFC, blockchain, and ALR modules activated](illustrations/fig7_phase2_components.png)

*Figure 9. Phase 2 module architecture: B2 and B3 mobile modules add NFC chip operations; A4 ALR integration, A6 blockchain anchoring, and A7 analyst dashboard activated in the Go Monolith; Hyperledger Fabric and Polygon EVM become operational infrastructure.*

| # | Module | Description |
|---|--------|-------------|
| A4 | Art Loss Register Integration | Automated ALR API query triggered on every NFC binding event and artwork registration. Result is written to ASE variable A3 (Art Loss Register Match) and displayed in the Artwork Passport. A positive stolen-art match halts the binding workflow and routes the case to the compliance officer queue. |
| A6 | Blockchain Anchoring | SHA-256 of the complete Artwork Passport record is submitted to Hyperledger Fabric on every provenance-modifying event (registration, transfer, NFC binding, valuation update). A scheduled Blockchain Worker batches daily Fabric transactions via Merkle tree and anchors the root hash to Polygon EVM. Each Passport carries a public verification URL. AML audit trail anchoring (per Module 607 specification) activates in Phase 3. |
| A7 | Analyst Dashboard | Full-text and faceted search across the Passport registry: artist, medium, period, provenance location, NFC activation status, and blockchain anchor status. Portfolio view with aggregate statistics and compliance coverage metrics. AML risk heat map and scoring distribution charts activate in Phase 3. |
| B2 | NFC Tag Activation & Binding | Reads NTAG 424 DNA chip UID via NXP TapLinx SDK (Android 3.0) or Apple CoreNFC (iOS), verifies genuine NXP chip, writes SHA-256 Visual DNA digest to NDEF memory. Binding confirmation is returned from the server only after Hyperledger Fabric records the event. TagTamper wire status is checked and stored at first activation. |
| B3 | Authentication Verification | Three-layer verification cascade: Visual DNA camera re-match against canonical DINOv2 embedding → NFC CMAC and tap-counter verification with TagTamper check → Blockchain record confirmation (Fabric ↔ Polygon hash synchronisation). Returns a weighted confidence score with per-layer breakdown. Clear PASS / REVIEW / FAIL verdict with guidance for the next action. |
| B4 (base) | Artwork Profile — Mobile Passport View | Full Artwork Passport view on the mobile app: artwork metadata, capture images, provenance timeline, NFC activation status, and blockchain verification badge. AML risk score summary field is added in Phase 3 as the B4 update. |
| B5 (base) | Ownership Transfer — KYC-gated on-chain transfer | Seller initiates transfer; buyer accepts via QR or NFC tap. Both parties must hold a valid Sumsub KYC clearance before the transfer is signed; the transfer event is written to Hyperledger Fabric and the SHA-256 of the new ownership record is included in the next daily Polygon Merkle anchor. **Phase 2 scope:** Transfer processing at this stage is limited to KYC validation of both parties — no AML risk score is computed on transfer. Automatic AML risk recalculation on transfer is added in Phase 3 as the B5 update (see RFQ §8 «B5 updates»). |
| NFC-SHOP | NFC Tag Ordering & Fulfillment | In-platform NFC tag ordering workflow activated in Phase 2: registered users request NTAG 424 DNA chips through the platform → order record created with delivery address and quantity → webhook/email notification to MARGIN ops team for fulfillment dispatch. Optional Phase 3 extension: automated fulfillment service integration (ShipBob / Sendcloud) for streamlined dispatch at volume. Tags priced at margin above ~€0.70 COGS. |
| SPECTRAL-CERT | PoP L3 Spectral Certification Workflow | End-to-end workflow for elevating an Artwork Passport to Expert Tier through accredited-laboratory spectral analysis (see §1.2.1 Proof of Physical Existence). Capabilities: (a) order placement against partner laboratories — CIRAM (Paris), MATIS/CSEM (Switzerland), Art+Image (Germany), Hephaestus (Greece), SAT (Italy); (b) secure upload of laboratory deliverables (multispectral UV/IR imagery, raking-light documentation, XRF/Raman pigment analysis, OCT craquelure maps) to the Document Vault; (c) lab-result review and acceptance by the MIRAS Art & Compliance Analyst; (d) on acceptance, the spectral signature is hashed (SHA-256) and anchored to Hyperledger Fabric as a separate timestamped event linked to the Artwork Passport, and the passport's verification level is elevated to Expert Tier — surfaced in the Public Registry (PUBLIC-REG) and via the Phase 4 A9 Lender Portal & API. Patent alignment: Patent 1, third tier of the Proof of Physical Existence framework. |
| ARTIST | Artist Self-Service Onboarding | Self-service registration for individual artists (not organisations). Email verification + Sumsub IDV light-KYC (identity document check only; no beneficial ownership disclosure required). No compliance officer manual review. Delivered as a dedicated early Phase 2 sprint in parallel with NFC development, enabling the bottom-up go-to-market strategy before the full NFC and blockchain layers complete. |

---

## Phase 3 — AML Risk Scoring Engine

Phase 3 activates the full Patent 2 AML Risk Scoring System: seven backend modules processing 26 variables across three scoring engines, 10 contextual modifiers, and four decision bands. Every sale, consignment, auction, or ownership transfer involving a MIRAS-registered artwork triggers a composite risk score computed in under 5 seconds. At Phase 3 exit, every transaction is scored, routed to the appropriate decision band, and archived in a blockchain-anchored audit trail compliant with EU Regulation 2024/1624 (AMLA) and the 6AMLD.

Transaction scoring scenario (Modules 601–607, A5, A12, A13, B4, B5): a gallery submits a sale event — artwork value €180,000, bank transfer, buyer domiciled in a FATF-monitored jurisdiction.

1. Module 601 — Data Ingestion: normalises inputs from 8 source categories — KYC records from Sumsub, Visual DNA and NFC authentication data from Phases 1/2, provenance records from Hyperledger Fabric, real-time watchlists from Dow Jones and ComplyAdvantage, transaction metadata, and cultural property databases. All values scaled to 0–100; SHA-256 integrity hash per record.

2. Module 602 — Client Scoring Engine (CSE, α=0.30): scores 9 client-risk variables. FATF jurisdiction mapping (C4) and no adverse media return a moderate buyer risk score of 28/100.

3. Module 603 — Artwork Scoring Engine (ASE, β=0.35): scores 9 artwork-risk variables. Patent 1 live feeds return clean results — A5 Visual DNA DINOv2 cosine similarity 0.96 → score 4; A6 NFC CMAC fresh, TagTamper intact → score 0; A8 Fabric–Polygon hash synchronisation confirmed → score 0. Artwork engine total: 12/100.

4. Module 604 — Transaction Scoring Engine (TSE, γ=0.35): scores 8 transaction-risk variables. Two modifiers activate: FATF-greylist jurisdiction triggers M3 (α+=0.15, β−=0.05, γ−=0.10); €180,000 transaction value triggers M1 (γ+=0.10).

5. Module 605 — Composite Engine: applies all modifier deltas, renormalises weights via Softmax (floor 0.10, ceiling 0.60 per engine), computes final weighted sum. Result: 29/100 — YELLOW band (26–50), enhanced due diligence required.

6. Module 606 — Decision Support: routes the case to the compliance officer review queue in A13 Compliance Officer Workstation. The officer reviews the full 26-variable breakdown, requests an additional source-of-funds document, and marks the case resolved.

7. Module 607 — Audit Trail: archives the complete scoring event — all inputs, applied weights, intermediate engine scores, active modifiers, composite score, and decision — to Hyperledger Fabric with SHA-256 integrity hash and a Polygon EVM timestamp anchor.

![Phase 3 AML scoring pipeline: 7 backend modules, 26 variables, 10 modifiers, and 4 decision bands](illustrations/fig8_phase3_aml_pipeline.png)

*Figure 10. Phase 3 AML scoring pipeline: transaction event ingested and normalised by Module 601, scored in parallel by CSE/ASE/TSE engines (Modules 602–604), composite score computed by Module 605 with dynamic modifier weights, decision classified by Module 606 into one of four bands, and archived immutably by Module 607 to Hyperledger Fabric and Polygon EVM.*

The composite scoring formula — Score = α(ctx) × CSE + β(ctx) × ASE + γ(ctx) × TSE — uses context-dependent weights that shift in response to active modifiers. Default weights α=0.30, β=0.35, γ=0.35 are adjusted by up to 10 active modifiers (M1–M10), each independently modifying one or more engine weights. Floor 0.10 and ceiling 0.60 per engine prevent any single engine from dominating; weights are renormalised via Softmax after all modifier deltas are applied. The four MIRAS-exclusive modifiers (M7–M10) pull live data from the Phase 1/2 authentication layers at scoring time: M7 activates when Visual DNA confidence falls below threshold (ASE variable A5 > 50); M8 when NFC CMAC freshness degrades or TagTamper is triggered (A6 > 50); M9 when the destination is a freeport or non-cooperative jurisdiction (TSE variable T4 > 50); M10 when the cross-layer custody chain is inconsistent (A8 > 50). These four modifiers are architecturally unavailable to any compliance system not integrated with Patent 1.

The AML Python microservice (FastAPI, scikit-learn) serves the scoring pipeline as a stateless service at `POST /internal/aml/score`, pre-warmed at startup, targeting ≤4s SLA. The eight external data integrations are accessed via a circuit-breaker adapter layer: failed provider calls return a degraded score with a stale-data flag rather than blocking the pipeline.

![Phase 3 module component architecture: AML Python microservice, web dashboards, and 8 external integrations](illustrations/fig9_phase3_components.png)

*Figure 11. Phase 3 module architecture: AML Scoring Python Microservice (Modules 601–607) receives scoring requests; A5 AML Dashboard, A12 Reporting, and A13 Compliance Officer Workstation are activated in the Go Monolith; eight external data providers are connected via circuit-breaker adapters.*

| # | Module | Description |
|---|--------|-------------|
| 601 | Data Ingestion Module | Centralised normalisation layer receiving data from 8 source categories (KYC, blockchain, provenance, Visual DNA, NFC, watchlists, transaction metadata, cultural property databases). All inputs scaled to 0–100 range; SHA-256 integrity hash per input record; timestamp validation to flag stale data. |
| 602 | Client Scoring Engine (CSE, α=0.30) | Scores 9 client-risk variables: PEP status (C1), sanctions match — Dow Jones, Refinitiv, OpenSanctions (C2), adverse media NLP score via ComplyAdvantage (C3), FATF jurisdiction mapping (C4), platform transaction history (C5), UBO transparency (C6), source of wealth verification (C7), account age (C8), and ML-derived pattern anomaly (C9). |
| 603 | Artwork Scoring Engine (ASE, β=0.35) | Scores 9 artwork-risk variables: Provenance Completeness Index (A1), historical risk windows 1933–45/1949–90 (A2), ALR clearance score (A3), catalogue raisonné consistency (A4), Visual DNA verification score (A5 — Patent 1 Layer 100 live feed), NFC authentication status (A6 — Patent 1 Layer 300 live feed), documentation quality (A7), blockchain integrity index (A8 — Patent 1 Layer 400 live feed), and provenance source credibility (A9). |
| 604 | Transaction Scoring Engine (TSE, γ=0.35) | Scores 8 transaction-risk variables: transaction value vs market estimate (T1), payment method risk tier — bank transfer to crypto to cash (T2), transaction velocity (T3), geographic jurisdiction risk — freeports and non-cooperative jurisdictions (T4), price anomaly vs Artnet/Artprice comparables (T5), structuring indicators (T6), counterparty relationship and shell company flags (T7), temporal pattern anomaly (T8). |
| 605 | Composite Scoring Engine | Implements the patented three-step weighting algorithm (RFQ §4.5.2): **Step 1** — calculate cumulative weight deltas from all active modifiers; **Step 2** — apply deltas to default weights (α=0.30, β=0.35, γ=0.35); **Step 3** — renormalise via Softmax and enforce floor 0.10 / ceiling 0.60 per engine. Then computes the final weighted sum Score = α(ctx)·CSE + β(ctx)·ASE + γ(ctx)·TSE. |
| 606 | Decision Support Module | Maps composite score to the four decision bands: GREEN 0–25 auto-approve with standard monitoring; YELLOW 26–50 enhanced due diligence and compliance officer review; ORANGE 51–75 senior compliance review with additional documentation required; RED 76–100 automatic transaction hold and mandatory STR consideration. Configurable band thresholds. |
| 607 | Audit Trail Module | Records the full scoring event — all inputs, applied weights, intermediate scores per engine, active modifiers, composite score, and decision — with SHA-256 integrity hash. Anchors to Hyperledger Fabric (detailed record, RBAC-gated) and Polygon EVM (hash only, public). Minimum 10-year retention; full reconstruction capability for any historical event. |
| A5 | AML Risk Scoring Dashboard | Real-time composite risk score display with colour-coded band indicator. Drill-down into all 26 variables per engine. Dynamic weight visualisation with active modifier list (M1–M10). Score history timeline and trend analysis. Side-by-side what-if scenario comparison. One-click STR draft generation for ORANGE/RED decisions. Compliance officer annotation and decision logging. |
| A12 | Reporting Module | Automated weekly and monthly compliance reports aggregating scoring distribution, band counts, and compliance officer decision outcomes. Audit trail export in structured format for regulatory inspection. STR log. AMLA-ready structured data export. |
| A13 | Compliance Officer Workstation | Dedicated review queue for YELLOW/ORANGE/RED transactions. Per-variable explanatory narrative for all 26 variables. Decision workflow: approve / request additional info / escalate / file STR. Decision audit trail with mandatory rationale. ML suggestion panel with accept/reject interface (active from Phase 4). |

---

## Phase 4 — ML Enhancement & Institutional Portal

Phase 4 completes the full Patent 2 specification by activating the machine-learning feedback loop, automating STR filing for RED-band decisions, opening the institutional portal for multi-organisation access, and closing the programme with an independent OWASP security audit. At Phase 4 exit, the AML scoring engine is self-improving — compliance officer decisions flow back into monthly retraining — and the platform is accessible to institutional clients (banks, insurers, lenders, auction houses) through a rate-limited API with configurable data-sharing levels.

> **Design note — Phase 4 is a directional blueprint.** Phase 4 is scheduled approximately 18–24 months from project kick-off. By the time Phase 3 exits, the platform will have 12–18 months of real operational data, established relationships with institutional clients, and a clearer picture of the regulatory landscape under EU AML Regulation 2024/1624. All of this will materially shape what Phase 4 actually looks like. The design described in this section represents ScienceSoft's best current thinking — how we would build Phase 4 if it started today. Phase 4 scope, module boundaries, and ML architecture will be formally re-planned at the Phase 3 exit milestone, incorporating operational learnings and any regulatory or market developments that occur in the interim. Clients should treat what follows as a well-reasoned directional design, not a fixed specification.

ML feedback scenario (ML Module): after three months of Phase 3 operation, the training dataset contains more than 1,200 compliance officer decisions. The Gradient Boosting model retrains on this labelled history, adjusting per-variable feature-importance weights. On the same dataset, a DBSCAN clustering job running overnight identifies a previously undetected risk ring: three client accounts sharing beneficial ownership, each individually scoring YELLOW, appear as a high-density cluster with elevated composite risk. An Isolation Forest scan flags a pattern of structured sub-threshold transactions from the same jurisdiction — all individually YELLOW, but collectively matching structuring indicators at scale (TSE variable T6). Both outputs appear as suggestions in the A13 compliance officer workstation. The compliance officer reviews, confirms the ring, and files a STR. Their decision is appended to the training dataset and will inform the next monthly retrain. Every ML action, suggestion, and human override is logged with full versioning for model audit.

**AML model training data.** The AML scoring engine draws on three sources. The primary input is internal operational data: compliance officer decisions accumulated since Phase 3 launch, with labels derived exclusively from human actions — never from ML outputs — to prevent feedback-loop contamination. This is supplemented by FATF art market typologies and EU AML Regulation 2024/1624 interpretive guidance as the regulatory reference baseline, and by Artnet/Artprice historical pricing to anchor the transaction-value anomaly variables to real market comparables. The model is expected to reach a statistically meaningful training corpus within the first three months of Phase 3 live operation.

**DINOv2 fine-tuning.** Phase 1 deploys the pre-trained `facebook/dinov2-small` model, which provides general-purpose visual features sufficient for initial Passport registration. By Phase 4, the platform will have accumulated tens of thousands of artwork photographs across Phases 1–3 — a corpus that, supplemented by publicly licensed museum datasets, enables fine-tuning DINOv2 on artwork-domain imagery. The fine-tuned model produces artwork-specific embeddings that are materially more difficult for competitors to replicate, strengthening the patent defensibility argument. Fine-tuning runs on a quarterly cadence using the existing GPU infrastructure; the minimum viable corpus of 500 artworks is expected to be reached during Phase 2–3, coinciding with the Visual DNA benchmarking exercise scheduled as part of the Phase 2–3 acceptance plan. Each new model version is validated against a held-out set before replacing the production model, with automatic rollback on quality regression.

![Phase 4 ML feedback loop and institutional portal architecture](illustrations/fig10_phase4_ml_institutional.png)

*Figure 12. Phase 4 architecture: Gradient Boosting model retrains monthly on accumulated compliance officer decisions; DBSCAN and Isolation Forest run as nightly batch jobs producing human-review suggestions; A8 and A9 open valuation data feeds and institutional API access; B7 and B8 complete the mobile module set.*

The ML training pipeline (scikit-learn) is strictly human-in-the-loop: no ML suggestion affects a live risk score without explicit compliance officer confirmation. Model retraining is configurable (default: monthly), with full version history, rollback capability, and explainability logging for every retrained model. DBSCAN cluster reports and Isolation Forest anomaly flags are presented as advisory outputs in A13; they do not auto-modify scoring weights or trigger automated actions. Each new AML model version is shadow-deployed alongside the production model for a one-week parallel evaluation period — scoring the same live transactions silently — before promotion, providing a safety net against model regression without interrupting live operations.

**Retrieval-Augmented Generation (RAG) — under evaluation for Phase 4.** A compliance assistant capability within A13 is under consideration: when a compliance officer opens a flagged transaction for review, the system would surface the most relevant precedent decisions from the platform's case history alongside applicable FATF typology excerpts and EU AML regulation articles — retrieved from a local knowledge base and presented as contextual reference, not as automated guidance. The technical path is straightforward: `pgvector` is already in the stack and can store text embeddings in a separate index with full tenant isolation at no additional infrastructure cost, and a GPU node already available for DINOv2 inference could host a compact open-weight LLM (such as Mistral-7B) to keep all data on-premises. The primary open question is governance: GDPR Article 17 right-to-erasure creates a complication when compliance officer decisions form part of a retrievable corpus, and the interaction with AML record-retention obligations under EU 2024/1624 (typically five years) requires legal review. ScienceSoft will assess the governance model during Phase 3 and present a formal go/no-go recommendation before Phase 4 planning is finalised. If approved, this capability requires no new infrastructure and can be delivered within Phase 4 scope as a module extension to A13.

The institutional portal (A9 Lender Portal & API) exposes a rate-limited REST API for banks, insurers, and lenders querying Passport status and risk scores for artworks used as loan collateral or insurance subjects. Three configurable disclosure levels are supported: full Passport (complete provenance chain, all 26 AML variables, current composite score), compliance summary (AML band, per-layer pass/fail, no raw data), and risk score only (numeric score and band, no provenance detail). Each institutional consumer is provisioned with an isolated API key, scoped permissions, and audit-logged request history. Full STR automation activates in Phase 4: every RED-band decision triggers a structured STR draft pre-populated in goAML-compatible XML format (UNODC standard, used by Italian UIF, French TRACFIN, and Qatari regulators); the compliance officer reviews and signs; the filing event is recorded in Module 607 with a Polygon EVM timestamp anchor.

| # | Module | Description |
|---|--------|-------------|
| ML Module | Adaptive Scoring Enhancement | Gradient Boosting model retrained monthly on labelled compliance officer decisions (internal operational data), supplemented by FATF typology reference data and Artnet/Artprice market comparables for feature calibration. DBSCAN unsupervised clustering detects novel connected-party risk rings; Isolation Forest identifies outlier transactions and structuring patterns. DINOv2 fine-tuned quarterly on the accumulated artwork corpus using existing GPU infrastructure; minimum viable corpus 500 artworks, expected to be reached during Phase 2–3 alongside the Visual DNA benchmarking exercise. All ML outputs require human confirmation before affecting live scoring. New AML model versions shadow-deployed for one week before promotion; automatic rollback on quality regression. Full model versioning and explainability logging per retraining cycle. |
| A8 | Valuation Module | Market comparable integration with Artnet and Artprice data feeds. Current estimated market value stored per artwork and refreshed on each pricing event. Value feeds directly into TSE variables T1 (transaction value deviation from estimated market value) and T5 (price anomaly vs comparable market prices), increasing the precision of transaction risk scoring. |
| A9 | Lender Portal & API | Rate-limited institutional REST API allowing banks, insurers, and lenders to query Passport status and risk scores for artworks offered as collateral or covered under insurance. Three configurable disclosure levels: full Passport, compliance summary, and risk score only. Per-institution API key provisioning, scoped permissions, rate limits, and complete request audit log. |
| B7 | Notifications | Push notification delivery for transaction events (ownership transfer initiated or completed), compliance alerts (risk band change, ALR match, ORANGE or RED score reached), and platform events (NFC tamper detected, passport status change). Configurable notification preferences per user role. |
| B8 | Internationalisation | Full multi-language support with initial release covering English, Italian, and Arabic, including RTL layout handling. Multi-currency display: EUR, USD, GBP, and QAR as minimum set. Localised date and number formatting. Translatable compliance report templates. |
| STR Automation | Full Filing Pipeline | Automated STR draft generation for every RED-band decision (score ≥76) in goAML-compatible XML format (UNODC standard), pre-populated with transaction metadata, scoring breakdown, and the MIRAS Artwork Passport identifier. Compliance officer review and sign-off required before submission. Filing event recorded in Module 607 audit trail with Polygon EVM timestamp anchor. |

Phase 4 closes with an independent OWASP Top 10 penetration test covering the full API surface, mobile application binary analysis, Hyperledger Fabric smart contract audit, and infrastructure hardening review. All findings are remediated before the Phase 4 completion milestone is signed off. A SOC 2 Type I readiness assessment is conducted in parallel to prepare the compliance evidence package required for institutional client procurement processes.

---


---

## Non-Functional Requirements

ScienceSoft's implementation is designed from inception to meet the following contractual NFRs:

| Category | Requirement | Design Approach |
|----------|-------------|-----------------|
| API Response Time | ≤500ms p95 for all REST endpoints | Go Echo v4 framework; Redis caching; pgvector HNSW indexed queries |
| Visual DNA Processing | ≤30s end-to-end for 6-shot passport creation | Async Asynq queue; GPU-accelerated DINOv2 inference pod |
| AML Scoring | ≤5s end-to-end from transaction submission | Dedicated Python AML microservice; pre-warmed scikit-learn model |
| Availability | 99.5% uptime SLA | Multi-AZ Kubernetes deployment; managed PostgreSQL with read replicas |
| Scale | 100K+ Passports; 500+ concurrent institutional users; 10K+ AML events/day | HNSW index for vector search; horizontal pod autoscaling; Asynq queue concurrency controls |
| Data Retention | 7 years AML records; 10 years audit trail | PostgreSQL archival partitioning; Hyperledger Fabric immutable ledger |
| Security | OWASP Top 10; AES-256 at rest; TLS 1.3; MFA | Security-first design; independent penetration test at Phase 4 milestone |
| EU AML Regulation 2024/1624 | Full regulatory compliance from Phase 3; audit trail format aligned with AMLA reporting requirements | Module 607 Audit Trail anchored to Hyperledger Fabric + Polygon EVM; 10-year immutable retention |
| GDPR | Data minimisation; right to erasure (passport archival + PII anonymisation without breaking audit integrity); DPA agreements with all sub-processors (Sumsub, Dow Jones, Refinitiv, ComplyAdvantage) | Data architecture designed for erasure compliance; sub-processor DPAs in place before Phase 1 go-live |
| Penetration Testing | Independent OWASP Top 10 test at Phase 4 exit; annual thereafter | Covers full API surface, mobile binary, Hyperledger Fabric smart contract audit, and infrastructure hardening; mandatory Phase 4 exit criterion |
| SOC 2 Type I | Readiness assessment at Phase 4 exit; Type II audit in Year 2 | Evidence collection begins Phase 3; compliance evidence package required for institutional client procurement |
| Incident Response | Documented IRP; regulatory notification ≤72h per GDPR Art. 33 | IRP runbook delivered with Phase 4; P1 (platform down) ≤15 min response / ≤4h resolution; P2 (degraded) ≤1h / ≤8h; P3 (non-critical) ≤4h / ≤48h |

---

## Proposed AWS Infrastructure

> **⚠ Preliminary estimate.** The infrastructure design presented in this section is based on current understanding of requirements and represents a first-pass approximation. Service selection, instance sizing, topology, and cost parameters will be refined iteratively as functional requirements, load profiles, and non-functional constraints are clarified during the discovery and design phases.

### Overview

The MIRAS.ART platform runs entirely on AWS in a European region, with a multi-tier VPC architecture designed for operational resilience and data sovereignty. Public traffic enters through Amazon CloudFront and AWS WAF; an Application Load Balancer routes requests into a private EKS cluster hosting all containerised workloads. The Visual DNA layer uses a dedicated GPU compute node for embedding inference. Stateful storage is distributed across Amazon RDS for PostgreSQL (Multi-AZ with automated failover), Amazon ElastiCache for Redis, and Amazon S3. The Year 1 Hyperledger Fabric network is hosted on Amazon Managed Blockchain, with an option to migrate to a self-hosted deployment from Year 2 as the network matures.

Encryption keys are managed by AWS KMS using Customer-Managed Keys (CMKs) stored in FIPS 140-2 Level 3 Hardware Security Modules. Data at rest is protected via AES-256 envelope encryption: KMS generates a per-resource data key, encrypts data with it, then wraps the data key under the CMK — the CMK itself never leaves the HSM boundary. All data in transit uses TLS 1.3.

NFC chip authentication relies on per-chip AES-128 session keys derived from a master diversification secret. The master diversification key is stored as a CMK in AWS KMS and never materialises outside the HSM. Per-chip derived keys are computed on demand and stored in AWS Secrets Manager — each secret is identified by chip UID, encrypted under the KMS CMK, and injected into the NFC Worker at runtime. NFC SUN (Secure Unique NFC) message verification is performed server-side using the retrieved per-chip key; no key material is ever sent to a client or logged.

![MIRAS.ART AWS cloud infrastructure: VPC layout with EKS cluster, GPU node, RDS Multi-AZ, ElastiCache, S3, Amazon Managed Blockchain, CloudFront/WAF edge, and external compliance API connections](illustrations/fig11_aws_infrastructure.png)

*Figure 13. MIRAS.ART AWS infrastructure: public traffic enters via CloudFront and WAF; ALB distributes to EKS pods running the Go Monolith, Visual DNA (GPU), AML Scoring, and Blockchain Worker services; the data tier comprises RDS PostgreSQL Multi-AZ with a read replica, ElastiCache Redis, and three S3 buckets; Amazon Managed Blockchain provides the Year 1 Hyperledger Fabric network; eight external compliance APIs connect via circuit-breaker adapters over NAT Gateway.*

---

### AWS Service Reference

| Category | Service | MIRAS.ART Usage |
|----------|---------|-----------------|
| Compute | Amazon EKS | Kubernetes cluster running all containerised workloads: Go Modular Monolith, AML Scoring Python microservice, Blockchain Worker, and Polygon Anchor service. Horizontal Pod Autoscaler handles burst compliance traffic; Cluster Autoscaler manages node group size. |
| Compute | Amazon EC2 — g4dn.xlarge | Dedicated GPU node for the Visual DNA Python microservice. Runs Meta AI DINOv2 Small (PyTorch 2.3) for 384-dim embedding inference within the ≤30 s end-to-end SLA. Reserved instance (1-year) for predictable cost. |
| Storage | Amazon S3 | Three buckets with SSE-KMS (AES-256): `miras-artwork-images` (6-shot raw frames), `miras-provenance-docs` (supporting documents, JPEG/PNG/TIFF/PDF/DOCX), `miras-passports` (signed PDF Artwork Passports). Versioning enabled on all buckets; lifecycle rules tier data to S3 Glacier Instant Retrieval after 3 years and S3 Glacier Deep Archive after 7 years (meeting 10-year audit-trail retention). Virus scanning via S3 Event → Lambda → ClamAV at ingestion. |
| Database | Amazon RDS for PostgreSQL 16 | Primary relational store and pgvector HNSW index (m=16, ef_construction=200) for 384-dim cosine similarity duplicate detection. Multi-AZ deployment with automated failover; one read replica serving the A7 Analyst Dashboard and A12 Reporting module. Storage encrypted via KMS. Automated daily snapshots retained for 35 days. |
| Cache / Queues | Amazon ElastiCache for Redis 7 | Asynq task queues: `visual-dna`, `pdf-generate`, `blockchain-write`, `aml-score`, `polygon-anchor`. Cluster mode with one replica per shard for queue durability; automatic failover. Redis also serves as the API response cache (≤500 ms p95 target). |
| Blockchain (Year 1) | Amazon Managed Blockchain — Hyperledger Fabric | Fully managed Fabric network for all provenance write operations: artwork registration, NFC binding events, ownership transfers, valuation updates, and Module 607 AML audit records. Two Fabric peer nodes across two AZs. Migrates to self-hosted Fabric on EKS from Year 2. |
| CDN | Amazon CloudFront | Global delivery of Next.js static assets and PDF Artwork Passports. Signed URLs for private document access. Edge-cached public passport verification pages. Terminates TLS 1.3 at edge. |
| Load Balancing | AWS Application Load Balancer | Layer-7 routing to EKS pods; path-based routing separates `/api/` and `/internal/` paths. Health checks with automatic pod deregistration. WebSocket support for real-time AML dashboard score updates. |
| Networking | Amazon VPC | Three subnet tiers: public (ALB, NAT Gateways), private application (EKS worker nodes), private data (RDS, ElastiCache, Managed Blockchain). S3 accessed via VPC Gateway Endpoint (no NAT cost). Outbound calls to eight external compliance APIs (Sumsub, Dow Jones, Refinitiv, ComplyAdvantage, ALR, Interpol, ICOM, OpenSanctions) exit via NAT Gateway. |
| DNS | Amazon Route 53 | Authoritative DNS for `miras.art` and `api.miras.art`. Health-check-based failover routing; latency-based routing for future multi-region expansion. |
| Security | AWS WAF | OWASP Top 10 managed rule group on CloudFront distribution and ALB. Rate limiting on the A9 institutional REST API (configurable per API key). Bot control and IP reputation rules. |
| Security | AWS KMS | Customer-managed keys for: S3 SSE-KMS (three keys, one per bucket), RDS storage encryption, ElastiCache encryption at rest, and Secrets Manager. Automatic annual key rotation. CloudTrail logs all KMS API calls. |
| Security | AWS Secrets Manager | Runtime injection of all third-party credentials: Sumsub KYC API key, Dow Jones API key, Refinitiv World-Check credentials, ComplyAdvantage API key, Art Loss Register token, Interpol Works of Art access, ICOM Red Lists token, OpenSanctions API key, Artnet/Artprice data feed credentials, Polygon RPC endpoint key. Automatic rotation where provider APIs support it. |
| Security | AWS IAM | IRSA (IAM Roles for Service Accounts) for all EKS workloads — least-privilege per microservice. MFA enforced on all human IAM users. SCPs via AWS Organizations prevent accidental public S3 bucket exposure. |
| Notifications | Amazon SNS + Amazon Pinpoint | B7 push notification delivery: ownership transfer events, risk band changes (ORANGE/RED alerts), ALR stolen-art matches, NFC tamper detections, passport status changes. Pinpoint manages per-device tokens for iOS (APNs) and Android (FCM). SNS fan-out for multi-channel delivery. |
| Email | Amazon SES | Transactional email: registration confirmations, compliance officer YELLOW/ORANGE/RED review alerts, automated weekly/monthly compliance report delivery (A12 module), STR filing confirmations. |
| Monitoring | Amazon CloudWatch | Centralised logs from all EKS pods, RDS, ElastiCache, ALB, and WAF. Custom metrics: AML scoring pipeline latency (per-module), Visual DNA queue depth, Asynq failed task count, Polygon anchor lag. Operational dashboards per phase. Alarms to SNS for p95 > threshold or queue depth > 500. |
| Monitoring | AWS X-Ray | Distributed tracing across the AML scoring pipeline (Modules 601–607) and the Visual DNA processing chain. Identifies latency outliers within the ≤5 s AML SLA; service map shows cross-microservice call graph. |
| Container Registry | Amazon ECR | Private registry for all Docker images: Go Monolith, Visual DNA microservice (GPU), AML Scoring microservice, Blockchain Worker. Immutable image tags; ECR image scanning (Trivy) on push; lifecycle policy retains last 30 tagged images. |

---

*Document prepared by ScienceSoft*  
*April 27, 2026*  
*For MARGIN International LLC — CONFIDENTIAL — For addressee only*
