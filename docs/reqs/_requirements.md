---
exemplar:
  id: equitea-2026
  industry: marketplace/hospitality
  domain_tags: [referral, booking, payments, invite-only, subscription, escrow, stripe-connect]
  project_type: platform
  complexity: medium
  source_types: [transcript, chat, brief, qa, pdf]
  source_count: 5
  fr_count: 42
  nfr_count: 13
  sections: [domain-grounding, stakeholders, business-context, fr, nfr, business-rules, data-model, integrations, open-questions]
  quality_score: null
  language: en
---

# Requirements: Equitea Platform

**Generated:** 29 March 2026
**Sources analysed:** 5 documents
**Output language:** English

---

## Document Index

| # | File | Type |
|---|------|------|
| 1 | `Equitea Developer Brief _amend 10 02 26 close.md` | Primary specification / brief |
| 2 | `Requirements Initial Questions.md` | Q&A (vendor responses from ScienceSoft) |
| 3 | `chat.txt` | Client chat transcript (Sam, Equitea) |
| 4 | `Online meeting between Equitea Ltd and ScienceSoft.md` | Meeting transcript — 25 March 2026 |
| 5 | `Equitea_Open_Questions.md` | Pre-proposal validation document (ScienceSoft) |

---

## Domain Grounding

This project is a **four-party, invite-only referral and booking marketplace** (Equitea) where verified Clients earn referral fees for introducing off-platform Guests to verified Businesses (restaurants, goods providers, service providers), with the platform managing bookings, subscription billing, and escrow-style referral fee payouts through Stripe Connect.

---

## 1. Stakeholders & Roles

| Role | Description |
|------|-------------|
| **Admin** (Equitea operator) | Platform operator. Manages users, approves listings, oversees bookings and payments, moderates content. Earns revenue through onboarding fees and commission on referral fees. |
| **Client** | Invited individual with a verified profile and active subscription. Introduces Guests to Businesses. Earns a referral fee per successful recommendation. Pays a one-off onboarding fee and monthly Direct Debit subscription. |
| **Business** | Invited company (restaurant, goods provider, service provider). Lists services and manages availability. Pays onboarding fee. Pays referral fee to Client via platform on successful booking. |
| **Guest** | Off-platform person that a Client books on behalf of, or refers to, a Business. Has no platform account. Pays Business directly, outside the platform. |

[Source: `Equitea Developer Brief _amend 10 02 26 close.md`, `Equitea_Open_Questions.md`]

---

## 2. Business Context

- **Platform model:** Invite-only marketplace. Access denied to anyone not holding a valid invitation link. [Source: `Equitea Developer Brief _amend 10 02 26 close.md`, `chat.txt`]
- **Revenue streams:** Client onboarding fees (one-off), Client monthly subscriptions (Direct Debit), Business onboarding fees, commission on referral fees. [Source: `Equitea Developer Brief _amend 10 02 26 close.md`]
- **Referral fee direction:** Business → Platform → Client. Platform holds funds for a maximum of 48 hours (escrow-style) before releasing to Client. [Source: `Equitea Developer Brief _amend 10 02 26 close.md`]
- **Geographic rollout:** MVP (UK) → Phase 1 (Europe) → Phase 2 (USA, Canada, other). [Source: `chat.txt`, `Online meeting between Equitea Ltd and ScienceSoft.md`]
- **Timeline preference:** MVP delivery in 4–6 months. [Source: `chat.txt`, `Online meeting between Equitea Ltd and ScienceSoft.md`]
- **Competitive reference apps:** Trovier (trovier.com), Gaido App, 5 O'Clock App — cited by Sam as look-and-feel references. [Source: `chat.txt`]
- **Code and IP ownership:** Fully customer (Equitea) owned. [Source: `Requirements Initial Questions.md`]
- **Post-launch requirement:** Support and maintenance package expected from vendor. [Source: `Online meeting between Equitea Ltd and ScienceSoft.md`]

---

## 3. Functional Requirements

### 3.1 Authentication & Access Control

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-001 | The platform MUST be invite-only. Access must be denied to any user who does not hold a valid, unexpired invitation link. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md`, `chat.txt` |
| FR-002 | The system must generate unique, expiring invitation links. Role (Client or Business) must be assigned at the invitation stage. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-003 | New users must verify their company email address and mobile phone number during registration. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-004 | The system must support two-factor authentication (2FA) for all user roles. | MUST | `Requirements Initial Questions.md` |
| FR-005 | Role-based access control (RBAC) must be enforced across all platform screens and API endpoints — Admin, Client, and Business roles must have separate privilege sets. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-006 | Bot protection measures must be implemented at registration and login: reCAPTCHA / hCaptcha, WAF, rate limiting, and IP filtering. | MUST | `Requirements Initial Questions.md` |
| FR-007 | The system must support secure password reset and account recovery flows. | MUST | `Requirements Initial Questions.md` (inferred from verified auth requirements) |

---

### 3.2 Client Onboarding

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-010 | Upon accepting a Client invitation link, the system must guide the user through: (1) company email verification, (2) profile creation, (3) payment of a one-off onboarding/admin fee, (4) setup of a recurring monthly Direct Debit subscription. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-011 | Client onboarding (including payment setup) must be completable within 5 minutes. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-012 | The Client must be able to complete and manage their profile (personal details, preferences, profile image). | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |

---

### 3.3 Business Onboarding

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-020 | Upon accepting a Business invitation link, the system must guide the operator through: (1) company verification, (2) payment of a one-off onboarding fee, (3) acceptance of commission/referral-fee terms, (4) upload of service catalogue (services, images, descriptions, pricing), (5) activation of the booking system. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-021 | Admin must be able to onboard a new Business from the admin dashboard within 10 minutes. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-022 | Businesses must be able to upload and manage service listings, menu items, table configurations, or product catalogues (depending on business type). | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-023 | Businesses must be able to manage their availability (time slots, capacity, open hours) directly, without admin intervention. Published availability is **indicative** — actual confirmation is manual (see FR-042). | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |

---

### 3.4 Search & Discovery

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-030 | Clients must be able to search for, browse, and view detailed profiles of verified Businesses on the platform. | MUST | `chat.txt` (Sam: "ability for Clients to search out business and connect with them or book their service through the platform") |
| FR-031 | Business profiles must display relevant details: description, services offered, images, location, availability, and pricing. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-032 | Clients must be able to initiate a connection with a Business prior to, or independently from, making a booking. | SHOULD | `chat.txt` |

---

### 3.5 Booking System

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-040 | Clients must be able to book a table reservation at a restaurant Business through the platform. | MUST | `chat.txt`, `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-041 | Clients must be able to book a service appointment with a service-provider Business through the platform. | MUST | `chat.txt`, `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-042 | Client selects date, time, and party size from the Business's published availability and submits a booking request. The Booking is created with status **Pending**. Business receives a notification and manually confirms or rejects the request via their Dashboard. No auto-confirm at MVP. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md`, design decision (stakeholder-confirmed) |
| FR-043 | Booking statuses must include: **Pending**, **Confirmed**, **Completed**, **Cancelled**. All transitions must be tracked and auditable. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-044 | The booking request flow (search → select Business → enter Guest details → submit) must be completable by the Client within 3 minutes. No payment is collected from the Client at booking time in the flat-fee MVP model. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-045 | The system must generate booking confirmations and send notifications (email and/or SMS) to both Client and Business. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` (implied by booking confirmation page) |
| FR-046 | Businesses must be able to confirm or cancel bookings via their dashboard. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-047 | Upon booking confirmation the system must generate a unique, single-use alphanumeric verification code and associate it with the Booking record. | MUST | Design decision (stakeholder-confirmed) |
| FR-048 | When creating a booking the Client must provide the Guest's email address and/or mobile number. The platform must send the verification code directly to the Guest via email and/or SMS. The code must also be visible to the Client in the booking details screen. | MUST | Design decision (stakeholder-confirmed) |
| FR-049 | The Business must be able to enter the Guest's verification code in the platform. The system must validate the code and, on success, transition the Booking status to **Completed** and trigger the referral-fee payout flow. An invalid or expired code must be rejected with a clear error message. | MUST | Design decision (stakeholder-confirmed) |

---

### 3.6 Payments, Subscriptions & Payouts

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-050 | The system must integrate Stripe and Stripe Connect as the primary payment infrastructure. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-051 | Client monthly subscriptions must be collected via Direct Debit through Stripe. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-052 | Client one-off onboarding fees must be collected via Stripe at registration. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-053 | Business one-off onboarding fees must be collected via Stripe at registration. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-054 | The referral fee flow must be: upon successful verification-code validation (FR-049), the platform auto-charges the Business's Stripe Connect account for a flat fee (configurable by Admin per Business category) → platform holds funds (escrow, maximum 48 hours) → platform pays out to Client's Stripe account. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md`, `chat.txt` (Sam: "ability for the referral fee to reach the client" as core MVP), C-002 resolution |
| FR-058 | The referral fee amount must be a flat amount configured by Admin per Business category (e.g. £10 for restaurants, £20 for services). The system must not require knowledge of the Guest's actual bill amount at MVP. | MUST | Design decision (C-002 resolution). Flat fee avoids dependency on real bill amount. |
| FR-055 | Clients must be able to withdraw their earned referral fees to their personal bank account via Stripe Connect. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-056 | The payment implementation must be PCI DSS compliant. | MUST | `Requirements Initial Questions.md` |
| FR-057 | The system must provision each Business with a Stripe Connect account (Express) for referral-fee collection (auto-charge upon booking completion). In the post-MVP full-payment model this account will also receive payout settlements. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md`, `Requirements Initial Questions.md` |

---

### 3.7 Admin Dashboard

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-060 | Admin must have a dedicated dashboard with the following capabilities: user management (view, invite, suspend, remove users), booking oversight, payment and payout management, listings moderation, and manual overrides. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-061 | Admin must be able to approve, reject, or edit Business listings and content. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-062 | Admin must be able to issue invitation links to both Client and Business users. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| FR-063 | Admin must have lightweight operational visibility: active users, booking volume, payment summaries. Full analytics is out of MVP scope. | MUST | `chat.txt` (Sam: "lightweight operational visibility can be sufficient") |
| FR-064 | Admin must be able to perform manual overrides on bookings and payments (e.g., issue refunds, resolve disputes). | SHOULD | `Equitea Developer Brief _amend 10 02 26 close.md` |

---

### 3.8 Notifications & Communication

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-070 | The platform must send transactional email notifications for: invitation links, registration confirmation, booking confirmations, booking status changes, **verification code delivery to Guest** (email and/or SMS per FR-048), payment receipts, and payout notifications. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md`, design decision (FR-048) |
| FR-071 | SMS notifications (OTP for verification, booking reminders) must be supported optionally. | SHOULD | `Requirements Initial Questions.md`, `Equitea Developer Brief _amend 10 02 26 close.md` |

---

### 3.9 Basic Fraud & Security Controls

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-080 | Basic fraud and spam safeguards must be in place for MVP: rate limiting, reCAPTCHA at registration/login, WAF, IP filtering, email domain verification. | MUST | `chat.txt` (Sam: "basic safeguards can remain"), `Requirements Initial Questions.md` |

---

### 3.10 Platform Pages (MVP UI)

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-090 | The following pages must exist at MVP: Landing / invitation acceptance page, Login page, Client dashboard, Business dashboard, Booking flow (search → select → confirm → payment), Payment confirmation page, Admin dashboard. | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |

---

### 3.11 Out of MVP Scope (Phase 2 and Beyond)

The following requirements are **explicitly excluded from MVP** per stakeholder confirmation:

| Feature | Source |
|---------|--------|
| Reviews / ratings system | `chat.txt`, `Online meeting between Equitea Ltd and ScienceSoft.md` (Sam: "take reviewing businesses away from that scope completely and pop that into phase two") |
| Client-to-client messaging | `chat.txt` (Sam: "No need for clients to communicate with each other") |
| Offer and promo broadcasts to Clients | `chat.txt` (Sam: "No need for Offer/Promo Broadcasts") |
| Advanced fraud and spam controls (ML-based, behavioural, full fraud detection layer) | `chat.txt` |
| Full reporting and analytics suite | `chat.txt` |
| Native mobile application (iOS / Android) | `Equitea Developer Brief _amend 10 02 26 close.md` |
| Waitlists | `Equitea Developer Brief _amend 10 02 26 close.md` |
| Dynamic pricing | `Equitea Developer Brief _amend 10 02 26 close.md` |
| European market rollout | `chat.txt` |
| USA / Canada market rollout | `chat.txt` |
| **Full payment through platform** — Guest pays full bill via Stripe Checkout link/QR generated by platform when Business enters verification code + bill amount. Platform auto-deducts referral fee, forwards remainder to Business. Enables percentage-based referral fees. | Design decision (C-002 resolution). Post-MVP Phase 1. |
| **EPOS integration** — Platform connects to restaurant POS systems for (a) real-time availability sync and auto-confirm of bookings, (b) automatic real bill amounts for percentage-based referral fees. Eliminates manual confirmation and manual amount entry. | `Online meeting between Equitea Ltd and ScienceSoft.md` (Sam ~13:53: "We've already built something previously that connects to EPOS systems"). Post-MVP Phase 2. |
| **Capacity grid with auto-confirm (OpenTable-style)** — Business defines capacity per time slot; system auto-confirms bookings within available capacity without manual intervention. Intermediate step between manual confirmation (MVP) and full EPOS integration. | `Equitea Developer Brief _amend 10 02 26 close.md` ("OpenTable-style backend logic"). Post-MVP Phase 1. |
| **PayPal as alternative payment method** — Stripe alternative or supplement. | `Online meeting between Equitea Ltd and ScienceSoft.md` (Sam ~23:14: mentions PayPal as option alongside Stripe) |

---

## 4. Non-Functional Requirements

| ID | Requirement | Category | Source |
|----|-------------|----------|--------|
| NFR-001 | The platform must be mobile-first responsive. | UX | `Equitea Developer Brief _amend 10 02 26 close.md`, `Online meeting between Equitea Ltd and ScienceSoft.md` (Sam confirmed mobile-first) |
| NFR-002 | The system must comply with UK GDPR. All personal data handling must meet UK data protection law. A compliance officer is available on the vendor side. | Legal / Compliance | `Equitea Developer Brief _amend 10 02 26 close.md`, `Requirements Initial Questions.md` |
| NFR-003 | Payment processing must be PCI DSS compliant. | Security | `Requirements Initial Questions.md` |
| NFR-004 | The architecture must be scalable to support 1,000,000+ registered users. | Scalability | `Requirements Initial Questions.md` |
| NFR-005 | Data must be hostable in EU and/or US data centres (client choice). | Data Sovereignty | `Requirements Initial Questions.md` |
| NFR-006 | The system must maintain separate development, staging, and production environments. | Ops | `Requirements Initial Questions.md` |
| NFR-007 | Daily backups and a disaster recovery plan must be in place. | Ops / Resilience | `Requirements Initial Questions.md` |
| NFR-008 | The platform must support multiple languages (multi-lingual) for future geographic expansion. | Internationalisation | `Requirements Initial Questions.md` |
| NFR-009 | The platform must support multi-currency (GBP at MVP minimum; EUR, USD for subsequent phases). | Internationalisation | `Requirements Initial Questions.md` |
| NFR-010 | Privacy policy and cookie consent mechanisms must be implemented in compliance with applicable law. | Legal | `Equitea Developer Brief _amend 10 02 26 close.md` |
| NFR-011 | Terms and Conditions must be accepted by all user types during registration. | Legal | `Equitea Developer Brief _amend 10 02 26 close.md` |
| NFR-012 | Secure authentication must be enforced (HTTPS, hashed credentials, session management). | Security | `Equitea Developer Brief _amend 10 02 26 close.md` |
| NFR-013 | The referral fee escrow window must not exceed 48 hours. | Business / Financial | `Equitea Developer Brief _amend 10 02 26 close.md` |

---

## 5. Business Rules & Constraints

| ID | Rule | Source |
|----|------|--------|
| BR-001 | No user (Client or Business) can register without a valid, unexpired invitation link. Self-registration is not possible. | `Equitea Developer Brief _amend 10 02 26 close.md`, `chat.txt` |
| BR-002 | The role assigned to a user (Client or Business) is fixed at the invitation stage and cannot be changed post-registration. | `Equitea Developer Brief _amend 10 02 26 close.md` |
| BR-003 | A Client must complete full onboarding (including payment of onboarding fee and subscription setup) before gaining access to the platform. | `Equitea Developer Brief _amend 10 02 26 close.md` |
| BR-004 | A Business must have a verified, admin-approved profile before its listings become visible to Clients. | `Equitea Developer Brief _amend 10 02 26 close.md` |
| BR-005 | The referral fee is triggered when the Business enters the Guest's verification code and the system validates it (Booking → Completed). The fee flows: Business → Platform → Client. The platform must not retain funds beyond 48 hours. | `Equitea Developer Brief _amend 10 02 26 close.md`, design decision |
| BR-006 | Client subscription continuity is required for active platform access; lapsed subscriptions must result in suspended access until payment is resolved. | `Equitea Developer Brief _amend 10 02 26 close.md` (inferred from subscription model) |
| BR-007 | Reviews functionality is excluded from MVP. Reviews are a Phase 2 feature. | `chat.txt`, `Online meeting between Equitea Ltd and ScienceSoft.md` |
| BR-008 | Advanced fraud controls (behavioural analysis, ML-based detection) are excluded from MVP. Basic safeguards (reCAPTCHA, rate limiting, WAF) are required. | `chat.txt` |
| BR-009 | Full analytics and reporting suite is excluded from MVP. Lightweight operational visibility (booking counts, user counts, payment summaries) is sufficient for MVP. | `chat.txt` |
| BR-010 | Client-to-client messaging is excluded from MVP. | `chat.txt` |
| BR-011 | Code and IP produced under this engagement are owned fully by Equitea Ltd. | `Requirements Initial Questions.md` |

---

## 6. Data Model (Derived from Sources)

The following entities are referenced in source documents. This is not a complete data model specification — it reflects entities explicitly mentioned.

| Entity | Key Attributes (Referenced) | Notes |
|--------|----------------------------|-------|
| **User** | ID, role (Admin / Client / Business), email, mobile, verification status, subscription status | [Source: Dev Brief] |
| **Invitation** | Token, associated role, expiry date/time, issued-by (Admin), claimed status | [Source: Dev Brief] |
| **ClientProfile** | Company name, profile image, personal details, bank account (for payout) | [Source: Dev Brief] |
| **BusinessProfile** | Company name, verification status, business type (restaurant / goods / service), description, images, contact details | [Source: Dev Brief] |
| **ServiceListing** | Business ID, name, description, pricing, images, availability | [Source: Dev Brief] |
| **Booking** | ID, Client ID, Business ID, service/table reference, Guest details (name, email, mobile), date/time, status (Pending/Confirmed/Completed/Cancelled), verification_code | [Source: Dev Brief, design decision] |
| **Payment** | ID, Booking ID, amount, currency, payment method, Stripe payment intent reference, status | [Source: Dev Brief, Q&A] |
| **ReferralFee** | ID, Booking ID, Client ID, Business ID, amount, escrow timestamp, payout status | [Source: Dev Brief] |
| **Subscription** | Client ID, plan, Direct Debit mandate reference, status, next billing date | [Source: Dev Brief] |
| **OnboardingFee** | User ID, amount, type (client/business), Stripe charge reference, paid date | [Source: Dev Brief] |

> **Review** entity is out of MVP scope. [Source: `chat.txt`]

---

## 7. Integration Points

| Integration | Purpose | Priority | Source |
|-------------|---------|----------|--------|
| **Stripe** | Client/Business onboarding fee collection, Client monthly subscription (Direct Debit), payment processing for bookings | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| **Stripe Connect** | Business sub-accounts; referral fee escrow and payout to Client; Client withdrawal to personal bank | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` |
| **Email delivery service** (e.g., SendGrid) | Transactional emails: invitations, registration confirmations, booking confirmations, payment receipts, payout notifications | MUST | `Equitea Developer Brief _amend 10 02 26 close.md` (implied) |
| **SMS / OTP provider** (e.g., Twilio) | Mobile number verification at registration; optional booking reminders | SHOULD | `Requirements Initial Questions.md`, `Equitea Developer Brief _amend 10 02 26 close.md` |
| **reCAPTCHA / hCaptcha** | Bot protection at registration and login | MUST | `Requirements Initial Questions.md` |
| **WAF (Web Application Firewall)** | Perimeter security for bot/DDoS protection | MUST | `Requirements Initial Questions.md` |

> **Note:** OpenTable is cited as an *inspiration* for booking logic, not a third-party integration. [Source: `Equitea Developer Brief _amend 10 02 26 close.md`]

---

## 8. Open Questions, Conflicts & Assumptions

### 8.1 Conflicts Found

| # | Conflict | Documents in Conflict | Resolution |
|---|----------|-----------------------|------------|
| C-001 | **Reviews in MVP:** Developer Brief (Section 5.2) lists Reviews as a functional MVP feature. Sam (in `chat.txt` and in meeting transcript of 25 March 2026) explicitly states: *"No need for reviews on the MVP"* and *"take reviewing businesses away from that scope completely and pop that into phase two."* | `Equitea Developer Brief _amend 10 02 26 close.md` vs. `chat.txt`, `Online meeting between Equitea Ltd and ScienceSoft.md` | **Resolution: Reviews are excluded from MVP.** Most recent direct stakeholder statement (March 2026) supersedes the written spec. Reviews are Phase 2. |
| C-002 | **Payment flow routing:** Developer Brief states *"Client pays for services directly to the provider"* (Business), implying full payment goes Business-direct, outside the platform. However, the referral-fee escrow model requires at least the referral portion to flow through Stripe Connect. `Equitea_Open_Questions.md` explicitly flags this as unresolved: *"Does full transaction flow through the platform OR only the referral fee via Stripe Connect?"* | `Equitea Developer Brief _amend 10 02 26 close.md` vs. `Equitea_Open_Questions.md` | **RESOLVED.** MVP = referral-fee-only through platform (flat fee, configurable by Admin per Business category). Guest pays Business directly (cash/card at venue). The platform charges Business a flat referral fee upon Booking completion (code entry). **Post-MVP:** Full-payment-through-platform option via Stripe Checkout (Guest shows code → Business enters code + bill amount → platform generates Stripe Checkout link/QR → Guest pays → platform auto-deducts referral fee → remainder to Business). See FR-058, Post-MVP backlog. |

---

### 8.2 Gaps (Information Not Found in Any Source Document)

| # | Gap | Impact |
|---|-----|--------|
| G-001 | **Guest verification mechanism:** How does a Business verify that the arriving Guest was referred by an Equitea Client, so that the referral fee payout is triggered? Guest has no platform account. | **RESOLVED.** Platform generates a unique alphanumeric verification code at booking confirmation. The code is sent directly to the Guest via email/SMS (contact details provided by the Client at booking). The Guest presents the code on-site; the Business enters it in the platform, which validates the code, marks the Booking as "Completed", and triggers referral-fee payout. See FR-047 – FR-049. |
| G-002 | **Goods provider scope in MVP:** Is a goods-provider Business limited to discovery / showcase only (no purchase transaction), or can Clients purchase goods through the platform? Sam's chat message mentions only *"table booking or booking of a service"* — suggesting goods may be discovery-only, but this is not explicitly confirmed. | Core scope definition, pricing model, Stripe integration depth |
| G-003 | **Service booking type:** Is a service booking a: (a) time-slot appointment, (b) date-range reservation, or (c) request-for-quote / enquiry? Different business types may need different models. | Booking system architecture |
| G-004 | **Business availability source:** Does availability management exist only on the platform, or can Businesses integrate external calendars (e.g., Google Calendar, Outlook) to sync availability? | **PARTIALLY RESOLVED.** MVP: platform-only, Business manages availability manually and confirms each booking via Dashboard (see FR-042, A-005, A-014). Post-MVP: EPOS integration for real-time availability sync (Sam ~13:53 confirms prior EPOS experience). External calendar sync remains unscoped. |
| G-005 | **Target audience definition:** Is the platform targeting exclusively high-net-worth individuals, upper-middle professionals, or the broader public with a premium UX? This affects referral-fee economics, subscription pricing, and design tone. | Positioning, UX, pricing model |

---

### 8.3 Explicit Assumptions

> Assumptions are marked clearly and have NOT been confirmed by source documents. They require validation with Equitea.

#### Scope & Business Logic

| # | Assumption | Basis |
|---|------------|-------|
| A-001 | **Goods providers in MVP = discovery/showcase only.** No product purchase transactions in MVP for goods-type Businesses. | Sam's chat message references only "table booking or booking of a service." Goods purchases are not mentioned. |
| A-002 | **MVP geography = UK only.** GDPR-compliant data hosting in EU is the MVP baseline. European and US expansion is Phase 1 and Phase 2 respectively. | `chat.txt` geographic roadmap; `Requirements Initial Questions.md` EU/USA hosting options. |
| A-003 | **"Company email" at Client registration** means a corporate-domain email address (not a consumer address such as Gmail or Yahoo). The platform should enforce or verify a company email format. | `Equitea Developer Brief _amend 10 02 26 close.md` phrase "company email" used without further definition. |
| A-004 | **Referral fee = flat amount per Business category, configurable by Admin.** MVP does not use percentage-of-bill. The platform does not need to know the real bill amount. Admin sets fee per category (e.g. £10 for restaurants, £20 for services). Post-MVP may add percentage-of-bill model when full-payment-through-platform is implemented. | Design decision. DevBrief does not specify fixed vs. percentage; flat fee avoids the "how does the platform know the bill amount" problem for MVP. |
| A-005 | **Platform owns the booking lifecycle** — it is not a directory that "just connects the parties." The platform creates, confirms, completes, and cancels bookings via an internal state machine (FSM). **MVP model: manual Business confirmation.** Client submits a request → Pending → Business confirms or rejects via Dashboard → Confirmed / Cancelled. No auto-confirm at MVP. Post-MVP: capacity-grid auto-confirm (OpenTable-style) and EPOS integration for real-time availability. | DevBrief §5.2 lists booking statuses Pending / Confirmed / Completed / Cancelled. `Open Questions` §4.2 explicitly asks this question; transcript confirms platform owns booking (Sam 11:27). Design decision: manual confirmation for MVP simplicity. |
| A-006 | **Table booking and service booking share a single generic Booking entity** at MVP. The same FSM and data model serve both restaurant date+time+party-size and service time-slot scenarios. | `chat.txt`: "table booking or booking of a service." v2.md Appendix B defines one Booking entity. Separate engines deferred to post-MVP if business types diverge. |
| A-007 | **Service booking = time-slot appointment model** (date + time + duration). Date-range and request-for-quote models are out of MVP scope. | Simplest model aligned with restaurant booking; G-003 gap remains unresolved. |
| A-008 | **Basic fraud/spam safeguards sufficient for MVP.** No dedicated fraud-detection engine; rate limiting, input validation, invite-only access act as primary controls. | `chat.txt`: Sam explicitly deferred "advanced Fraud/Spam Controls" but confirmed "basic safeguards can remain." |
| A-009 | **Lightweight operational visibility replaces full analytics in MVP.** Admin dashboard shows booking counts, revenue, user counts. No BI, funnels, or retention reports. | `chat.txt`: Sam explicitly deferred "full Reporting & Analytics"; "lightweight operational visibility" accepted. |

#### Payment & Payout

| # | Assumption | Basis |
|---|------------|-------|
| A-010 | **MVP: Only the referral fee (flat amount) routes through the platform (Stripe Connect).** The Guest pays the Business directly (cash/card at venue). The platform does not process the full transaction amount. **Post-MVP:** Full payment through platform via Stripe Checkout — Guest pays the full bill through a platform-generated payment link; platform auto-deducts referral fee and forwards the remainder to Business. | DevBrief §5.3: "Client pays for services directly to the provider but the referral fee is paid from the service or goods provider through platform." C-002 resolved: flat fee for MVP, full payment flow as Post-MVP evolution. |
| A-011 | **Guest verification = code-based confirmation.** At booking confirmation the platform generates a unique alphanumeric verification code and sends it directly to the Guest via email/SMS (contact details provided by Client at booking). On arrival the Guest presents the code; the Business enters it in the platform. A valid code transitions the Booking to "Completed" and triggers the referral-fee payout. | Design decision confirmed by stakeholder. Replaces previous dashboard-only confirmation. See FR-047 – FR-049, G-001 (resolved). |
| A-012 | **Stripe Connect Express accounts** (not Custom) for Business onboarding. Express provides Stripe-hosted onboarding and identity verification while keeping regulatory burden off Equitea. | Standard for marketplaces with <$1M monthly volume; not contradicted by sources. |

#### Architecture & Delivery

| # | Assumption | Basis |
|---|------------|-------|
| A-013 | **MVP = web application only.** No native mobile apps. Three web front-ends: Client/Business web app, Admin panel, future mobile shell. | DevBrief §1: "BIO web app." `chat.txt` reference to Gaido (mobile-preferred) is post-MVP aspiration. |
| A-014 | **Business availability = platform-only at MVP.** Businesses manage their availability through the platform dashboard. Published slots are indicative; each booking requires manual Business confirmation (see FR-042, A-005). No integration with external calendars or POS systems. **Post-MVP:** EPOS integration for real-time availability sync and auto-confirm. | G-004 gap. Simplest approach for MVP; EPOS integration deferred to Post-MVP. |
| A-015 | **Proposed timeline ~9 weeks (4 phases) assumes prompt project kickoff and timely stakeholder decisions.** Sam's stated expectation is "MVP in four to six months" (Meeting ~19:00), giving budget margin but also a discrepancy to discuss. | v2.md §8 roadmap vs. Meeting transcript. Needs alignment at project kickoff. |

---

*End of requirements document.*
