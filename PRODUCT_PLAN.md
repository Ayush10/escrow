# Verdict Protocol Product Plan

## 1. Product thesis

Verdict Protocol is the trust layer for paid AI services and agent-to-agent commerce.

Core promise:
- payment-gated API or agent transaction
- tamper-evident request/response trail
- escrow-backed dispute path
- deterministic plus AI-assisted arbitration
- portable reputation for providers and agents

### Market position

The AI economy is moving toward autonomous agents that discover, negotiate, and pay for services without human intervention. This creates a trust vacuum: when Agent A pays Agent B for an API call and gets garbage back, there is no chargeback button, no customer support, no court. Verdict Protocol fills that gap.

The product sits at the intersection of three trends:
1. **Paid AI APIs** — inference, tools, data, and agent capabilities sold per-call
2. **Agent autonomy** — agents making purchasing decisions without human approval loops
3. **On-chain settlement** — crypto-native payment rails that enable programmatic escrow

Verdict Protocol is not a marketplace. It is infrastructure that marketplaces, agent frameworks, and API providers plug into.

### Naming

- `Verdict Protocol`: company + platform name
- `Agent Court`: arbitration engine / dispute resolution product

That naming matches the current repo split more cleanly than treating them as separate products. All external communication uses "Verdict Protocol" as the umbrella. "Agent Court" appears only when referring specifically to the dispute resolution and arbitration subsystem.

---

## 2. Market landscape and competitive differentiation

### Adjacent categories

| Category | Examples | Why Verdict is different |
|----------|----------|------------------------|
| API marketplaces | RapidAPI, Replicate | They aggregate APIs but offer no dispute resolution, no on-chain evidence, no escrow. Payment is credit card with traditional chargebacks. |
| Agent frameworks | LangChain, CrewAI, AutoGen | They orchestrate agent behavior but have no payment, evidence, or arbitration layer. |
| Crypto escrow | Kleros, Aragon Court | They handle human disputes with token-weighted juries. Verdict handles machine-to-machine disputes with deterministic + AI judges, at sub-second speed. |
| API monitoring | Datadog, New Relic | They observe APIs but do not link observations to payment disputes or on-chain evidence. |
| x402 payment | x402.org facilitator | x402 handles the payment gate. Verdict adds everything after: evidence capture, receipt chains, dispute filing, arbitration, reputation. |

### Differentiation

1. **Speed**: Disputes are resolved in seconds (LLM judge), not days/weeks (human jury).
2. **Determinism**: SLA checks are deterministic first, LLM-narrative second. The machine decides; the LLM explains.
3. **Evidence integrity**: Every API call produces a cryptographically linked receipt chain anchored on-chain via Merkle root.
4. **Tiered escalation**: District → Appeals → Supreme court tiers with increasing cost and model capability, discouraging frivolous disputes.
5. **Reputation portability**: ERC-8004 on-chain reputation that follows agents across platforms.
6. **No token required**: USDC-denominated. No governance token needed for V1.

### Competitive moat

The moat is the evidence standard. Once providers and consumers adopt Verdict's receipt chain format and evidence anchoring, switching costs are high because:
- historical dispute data lives on-chain
- reputation scores are non-transferable to competing systems
- SLA templates and arbitration clause libraries accumulate network effects

---

## 3. What already exists

### Technical inventory

The repo contains the nucleus of the product:

| Component | Location | Status |
|-----------|----------|--------|
| AgentCourt smart contract | `contracts/AgentCourt.sol` | Live on GOAT Testnet3 (`0xFBf9b5293A1737AC53880d3160a64B49bA54801D`) |
| Protocol package | `packages/protocol/` | Complete — hashing, schemas, signatures, receipt chains, escrow adapter |
| Evidence service | `apps/evidence_service/` | Complete — clause/receipt storage, Merkle anchoring (port 4001) |
| Provider API | `apps/provider_api/` | Complete — x402-protected endpoints with evidence hash headers (port 4000) |
| Judge service | `apps/judge_service/` | Complete — 3-tier LLM judge, event watcher, on-chain ruling submission (port 4002) |
| Reputation service | `apps/reputation_service/` | Complete — ERC-8004 feedback, scoring, leaderboard (port 4003) |
| Consumer agent | `apps/consumer_agent/` | Complete — happy path and dispute path demo flows |
| Demo runner | `apps/demo_runner/` | Complete — orchestration server with SSE streaming |
| Judge frontend | `judge-frontend/` | Complete — monolithic SPA with full dashboard |
| Verdict frontend | `verdict-frontend/` | In progress — React rewrite, partial feature coverage |

### On-chain state

- **Contract**: AgentCourt.sol on GOAT Testnet3 (chain ID 48816)
- **Payment token**: USDC at `0x29d1ee93e9ecf6e50f309f498e40a6b42d352fa1`
- **Identity registry**: ERC-8004 at `0x556089008Fc0a60cD09390Eca93477ca254A5522`
- **Reputation registry**: ERC-8004 at `0x52B2e79558ea853D58C2Ac5Ddf9a4387d942b4B4`
- **Judge fees**: $0.05 (district), $0.10 (appeals), $0.20 (supreme)
- **Service fee rate**: configurable basis points (100 = 1%)

### Current reality

- End-to-end demo flows (happy path + dispute path) execute successfully
- The architecture is credible and maps cleanly to the product thesis
- The repo is in demo-to-product transition
- Trust, ops, and UX hardening are not finished
- No CI/CD pipeline exists
- No automated integration tests beyond protocol unit tests
- Legacy code paths (`server/`, `demo/`, `guardian/`) remain in the repo

---

## 4. Product definition

### Primary product

Verdict Protocol ships first as a B2B developer platform for paid APIs and autonomous services.

V1 product statement:
> "Add paid access, verifiable execution evidence, and dispute resolution to any API or agent workflow."

### What the product includes

A single platform with four capabilities:

**1. Payment gate** — x402-based payment enforcement at the API edge. Every request requires valid payment proof before the provider processes it.

**2. Evidence trail** — Automatic capture of request/response pairs as cryptographically linked receipt chains, anchored on-chain via Merkle root commits.

**3. Dispute resolution** — Filing, evidence submission, deterministic SLA evaluation, LLM-generated judicial opinion, on-chain ruling execution, and fund transfer.

**4. Reputation** — On-chain track record (ERC-8004) of transaction history, dispute outcomes, and service quality scores that follow agents across platforms.

### Secondary products (post-V1)

Once the core platform is stable, package specific capabilities as standalone offerings:

**Agent Court Gateway** — Managed or self-hosted reverse proxy that handles x402 payment verification, request/response evidence capture, and evidence hash emission. Providers deploy it in front of their API and get payment + evidence + dispute support without writing integration code.

**Verdict Console** — Operator and merchant dashboard for managing services, monitoring transactions, reviewing disputes, and viewing reputation data. Includes audit trail export and webhook configuration.

**Verdict Reputation API** — Public API exposing provider and agent trust data, dispute history, success rates, and quality scores. Third-party marketplaces and agent frameworks query this to make routing decisions.

**Verdict Marketplace** (later) — Discovery surface where consumers browse registered services, compare reputation scores, and initiate transactions. Built on top of the platform's service registry and reputation data.

---

## 5. Ideal customer and wedge

### Beachhead users

**Persona 1: API Provider ("Alex")**
- Sells AI inference, data enrichment, or tool endpoints
- Currently uses Stripe/crypto for payment, has no dispute mechanism
- Loses revenue to chargebacks or has no recourse when consumers claim bad output
- Wants: payment enforcement, evidence trail for every call, dispute resolution
- Willingness to pay: $50-500/month or basis-point fee on transactions

**Persona 2: Agent Builder ("Sam")**
- Builds autonomous agents that call third-party APIs
- Agents spend money without human approval for each call
- Has been burned by paid APIs returning garbage with no recourse
- Wants: verified execution evidence, ability to dispute, trust scores for providers
- Willingness to pay: per-dispute fee + small per-call overhead

**Persona 3: Marketplace Operator ("Jordan")**
- Runs a platform where AI services are listed and consumed
- Needs dispute rails for machine-to-machine transactions
- Cannot build arbitration infrastructure in-house
- Wants: plug-in dispute resolution, reputation data, white-label console
- Willingness to pay: revenue share or enterprise license

### Wedge use case

Paid API calls with an SLA dispute path.

Why this wedge:
- narrow enough to ship in weeks, not months
- already matches the repo's implemented architecture
- has a concrete buyer (any API provider tired of chargebacks)
- avoids needing a full agent marketplace on day one
- creates natural expansion: more endpoints → more evidence → more disputes → more reputation data

### Expansion path from wedge

```
Paid API calls → Agent-to-agent workflows → Multi-agent chains → Marketplace
     (V1)              (V1.5)                    (V2)              (V3)
```

### Avoid as initial wedge

- general "court for all agents" — too broad, no concrete buyer
- cross-chain generalized arbitration network — infrastructure without users
- consumer marketplace — requires supply-side liquidity first
- token-heavy protocol design — introduces governance complexity before usage exists

---

## 6. V1 product surface

### A. Provider integration

Providers can:
- register as an agent on-chain (deposit bond, get ERC-8004 identity)
- register a service with terms hash, price per call, and required consumer bond
- protect any endpoint with x402 payment enforcement
- receive `X-Evidence-Hash` headers on every call for receipt binding
- view evidence anchoring status for their transactions
- respond to disputes with counter-evidence
- withdraw earnings minus platform fees

Deliverables:
- Python provider SDK (`verdict-provider`)
- Node.js provider SDK (`@verdict-protocol/provider`)
- FastAPI middleware and Express.js middleware for automatic x402 + evidence
- Gateway deployment template (Docker Compose)
- Provider onboarding guide with step-by-step integration tutorial

### B. Consumer/agent integration

Consumers can:
- register as an agent on-chain (deposit bond)
- discover services via service registry queries
- pay for a request via x402 with automatic receipt creation
- receive evidence-linked response metadata (`X-Evidence-Hash` header)
- inspect receipt chains and Merkle anchoring proofs
- open a dispute with committed evidence root hash
- track dispute status and ruling outcomes
- query provider reputation before making calls

Deliverables:
- Python consumer SDK (`verdict-consumer`)
- Node.js consumer SDK (`@verdict-protocol/consumer`)
- Dispute submission CLI and API
- Receipt chain viewer (web component)
- Provider reputation lookup API

### C. Arbitration layer (Agent Court)

Agent Court can:
- watch for `DisputeFiled` events on-chain
- fetch dispute details and evidence bundles
- verify receipt chain integrity (sequence, hash linking, signatures)
- apply deterministic SLA checks against arbitration clause rules
- generate human-readable judicial opinion via tiered LLM judges
- submit ruling on-chain with fund transfer execution
- update reputation scores for both parties
- produce signed verdict packages with full reasoning metadata

Deliverables:
- Signed verdict package export (JSON + signature)
- Dispute lifecycle API with state tracking
- Deterministic SLA check engine (separate from LLM narrative)
- Verdict archive and audit trail
- Appeals system (designed in V1, implemented in V2)

### D. Console (Verdict Console)

Operators need:
- service health dashboard with uptime and latency for all backend services
- transaction explorer with filtering by service, agent, status, and date range
- agreement explorer showing clause terms, receipt chains, and anchoring status
- dispute timeline view with evidence bundles, rulings, and fund movements
- reputation leaderboard with drill-down into agent history
- run orchestration controls for demo and testing flows
- webhook configuration and delivery log
- audit trail export (CSV, JSON)
- environment switcher (local / testnet / pilot / production)

Deliverables:
- one canonical frontend (see section 13 for detailed spec)
- no duplicated frontend paths in production

---

## 7. Dispute lifecycle specification

### State machine

```
                    ┌──────────────┐
                    │  Transaction │
                    │  Fulfilled   │
                    └──────┬───────┘
                           │ consumer calls fileDispute()
                           │ stakes frozen (plaintiff + defendant)
                           │ judge fee frozen (from plaintiff)
                           ▼
                    ┌──────────────┐
                    │   Dispute    │
                    │    Filed     │
                    │  (tier N)    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        defendant     evidence      timeout
        responds      window        expires
        with          closes        (no response)
        evidence
              │            │            │
              └────────────┼────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Judge      │
                    │   Review     │
                    └──────┬───────┘
                           │
                    ┌──────┼──────┐
                    │             │
                    ▼             ▼
              confidence     confidence
              >= 0.7         < 0.7
              AND judge      OR no judge
              authorized     authorization
                    │             │
                    ▼             ▼
             ┌───────────┐ ┌───────────┐
             │  Ruling    │ │  Manual   │
             │  Submitted │ │  Review   │
             │  On-Chain  │ │  Flagged  │
             └─────┬──────┘ └─────┬─────┘
                   │              │ operator reviews
                   │              │ and submits
                   │              ▼
                   │        ┌───────────┐
                   │        │  Ruling    │
                   │        │  Submitted │
                   │        └─────┬─────┘
                   │              │
                   └──────┬───────┘
                          │
                   ┌──────┼──────┐
                   │             │
                   ▼             ▼
             winner gets   loser's tier
             both stakes   escalated
             + payment     (disputeLossCount++)
             released
                   │             │
                   └──────┬──────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  Reputation  │
                   │  Updated     │
                   │  (ERC-8004)  │
                   └──────────────┘
```

### On-chain dispute states

From the AgentCourt contract:

| State | Condition | Transitions to |
|-------|-----------|---------------|
| **Filed** | `fileDispute()` called. `resolved == false`, `defendantEvidence == bytes32(0)` | Responded, Ruling |
| **Responded** | `respondDispute()` called. `defendantEvidence != bytes32(0)` | Ruling |
| **Ruling** | `submitRuling()` called by judge. `resolved == true`, `winner != address(0)` | Terminal |

### Off-chain dispute states (judge service)

| State | Description |
|-------|-------------|
| `detected` | DisputeFiled event received by watcher |
| `evidence_fetched` | Evidence bundle retrieved from evidence service |
| `facts_extracted` | Deterministic fact extraction complete |
| `llm_judging` | LLM judge invoked, awaiting response |
| `verdict_ready` | Verdict generated, pending submission |
| `submitted` | Ruling submitted on-chain via `submitRuling()` |
| `manual_review` | Confidence below threshold or judge error — flagged for operator |
| `failed` | Submission failed — requires retry or manual intervention |

### Timeouts and windows

| Window | Duration | Enforcement | Current status |
|--------|----------|-------------|----------------|
| **Dispute window** | Configurable per clause (`disputeWindowSec`) | Off-chain (consumer agent respects it) | Implemented in clause schema |
| **Evidence window** | Configurable per clause (`evidenceWindowSec`) | Off-chain (judge service respects it) | Implemented in clause schema |
| **Auto-complete** | 1 hour after fulfillment | On-chain (`autoComplete()` callable by anyone) | Implemented in contract |
| **Defendant response** | No on-chain deadline (judge proceeds without) | Off-chain (judge does not wait indefinitely) | Partially implemented |
| **Judge ruling deadline** | Not enforced | Should be: 5 minutes for automated, 24 hours for manual review | Not yet implemented |

### Escalation rules

Tier escalation is based on `disputeLossCount` per agent address:

| Losses | Court tier | LLM model | Judge fee | Description |
|--------|-----------|-----------|-----------|-------------|
| 0 | District | claude-haiku-4-5 | $0.05 | Fast, cheap, first-instance |
| 1 | Appeals | claude-sonnet-4-6 | $0.10 | More capable model, reviews district reasoning |
| 2+ | Supreme | claude-opus-4-6 | $0.20 | Most capable, final authority |

Escalation is permanent per address. An agent who loses 2 disputes always pays Supreme-tier fees, discouraging serial bad actors.

### What happens when a party goes silent

- **Defendant does not respond**: Judge proceeds with plaintiff evidence only. Defendant's `defendantEvidence` remains `bytes32(0)`. The judge notes the default in the opinion.
- **Judge does not rule**: Currently no on-chain timeout. V2 should add a `judgeTimeout` after which the plaintiff can claim by default or a backup judge is assigned.
- **Consumer does not confirm or dispute**: After 1 hour, anyone can call `autoComplete()` to release payment to provider.

---

## 8. SLA framework

### SLA rule types

The arbitration clause contains `slaRules` — a list of machine-evaluable conditions that define what "good service" means. Each rule has:

```json
{
  "ruleId": "latency_p99",
  "metric": "response_time_ms",
  "operator": "lte",
  "value": "3000",
  "unit": "milliseconds"
}
```

### Supported metrics (V1)

| Metric | Description | How measured | Operator |
|--------|-------------|-------------|----------|
| `response_time_ms` | Time from request to response | Timestamp delta between request and response receipts | `lte`, `lt` |
| `status_code` | HTTP status code of response | Extracted from response receipt metadata | `eq`, `neq`, `in` |
| `payload_format` | Response body schema conformance | JSON schema validation against expected format | `eq` (schema name) |
| `payload_size_bytes` | Response body size | Byte count of response payload | `gte`, `lte` |
| `uptime_percent` | Availability over rolling window | Ratio of successful to total calls in window | `gte` |
| `error_rate` | Percentage of 5xx responses | Count of error responses / total responses | `lte` |
| `content_accuracy` | Semantic quality of AI output | LLM-evaluated (not deterministic) | `gte` (0-1 score) |

### Supported operators

| Operator | Meaning |
|----------|---------|
| `eq` | equals |
| `neq` | not equals |
| `lt` | less than |
| `lte` | less than or equal |
| `gt` | greater than |
| `gte` | greater than or equal |
| `in` | value is in list |
| `not_in` | value is not in list |
| `matches` | regex match |

### Deterministic vs LLM evaluation

SLA evaluation happens in two passes:

**Pass 1: Deterministic** — The judge service extracts facts from receipts and evaluates each SLA rule mechanically. Rules like `response_time_ms lte 3000` are checked against receipt timestamps. This produces a list of `pass` / `fail` / `inconclusive` results per rule.

**Pass 2: LLM narrative** — The deterministic results, evidence bundle, and clause terms are passed to the LLM judge. The LLM generates a judicial opinion that explains the ruling in human-readable language. The LLM can weigh `inconclusive` rules and `content_accuracy` checks that require semantic evaluation.

The deterministic pass is the source of truth. The LLM cannot override a deterministic `fail` on a clear metric like latency. It can only adjudicate ambiguous cases.

### SLA template library (V1)

Pre-built templates for common use cases:

**Template: Basic API SLA**
```json
{
  "slaRules": [
    {"ruleId": "latency", "metric": "response_time_ms", "operator": "lte", "value": "5000", "unit": "ms"},
    {"ruleId": "status", "metric": "status_code", "operator": "eq", "value": "200", "unit": "http_status"},
    {"ruleId": "format", "metric": "payload_format", "operator": "eq", "value": "application/json", "unit": "mime_type"}
  ],
  "disputeWindowSec": 3600,
  "evidenceWindowSec": 1800
}
```

**Template: AI Inference SLA**
```json
{
  "slaRules": [
    {"ruleId": "latency", "metric": "response_time_ms", "operator": "lte", "value": "30000", "unit": "ms"},
    {"ruleId": "status", "metric": "status_code", "operator": "eq", "value": "200", "unit": "http_status"},
    {"ruleId": "quality", "metric": "content_accuracy", "operator": "gte", "value": "0.7", "unit": "score"},
    {"ruleId": "size", "metric": "payload_size_bytes", "operator": "gte", "value": "100", "unit": "bytes"}
  ],
  "disputeWindowSec": 7200,
  "evidenceWindowSec": 3600
}
```

**Template: Data Feed SLA**
```json
{
  "slaRules": [
    {"ruleId": "latency", "metric": "response_time_ms", "operator": "lte", "value": "1000", "unit": "ms"},
    {"ruleId": "freshness", "metric": "data_age_seconds", "operator": "lte", "value": "60", "unit": "seconds"},
    {"ruleId": "completeness", "metric": "payload_size_bytes", "operator": "gte", "value": "500", "unit": "bytes"}
  ],
  "disputeWindowSec": 1800,
  "evidenceWindowSec": 900
}
```

### Remedy rules

Each clause can specify what happens when rules are violated:

```json
{
  "remedyRules": [
    {"condition": "any_sla_breach", "action": "full_refund", "percent": 100},
    {"condition": "latency_breach_only", "action": "partial_refund", "percent": 50},
    {"condition": "content_quality_breach", "action": "full_refund", "percent": 100}
  ]
}
```

Currently, the contract supports binary outcomes (plaintiff wins or defendant wins). Partial refunds would require a V2 contract update where `submitRuling` accepts a percentage split.

---

## 9. Evidence model

### What constitutes evidence

Evidence in Verdict Protocol is a chain of `EventReceipt` objects linked by cryptographic hashes. Each receipt captures one event in a transaction lifecycle.

### Receipt types

| Event type | Created by | Contains |
|-----------|-----------|---------|
| `request` | Consumer | Request payload hash, timestamp, agreement ID, clause hash |
| `response` | Consumer (captures provider response) | Response payload hash, `X-Evidence-Hash` from provider, timestamp, status code |
| `payment` | Consumer | x402 payment reference, amount, network, tx hash |
| `sla_check` | Consumer | Violation type (e.g., `sla_breach:latency`), measured vs expected values |
| `dispute_filed` | Consumer | Dispute ID, on-chain tx hash, stake amount |

### Receipt structure

Each receipt (defined in `packages/protocol/src/verdict_protocol/types.py`):

```
EventReceipt:
  schemaVersion: "1.0.0"
  receiptId:       UUID
  agreementId:     UUID (links to ArbitrationClause)
  clauseHash:      keccak256 of clause (integrity binding)
  chainId:         48816 (GOAT Testnet3)
  contractAddress: 0xFBf9...
  sequence:        0, 1, 2, ... (monotonic within agreement)
  eventType:       "request" | "response" | "payment" | "sla_check" | "dispute_filed"
  timestamp:       unix ms
  actorId:         did:8004:0x... (ERC-8004 DID of the actor)
  counterpartyId:  did:8004:0x... (the other party)
  requestId:       UUID (links related receipts)
  payloadHash:     keccak256 of the actual payload data
  prevHash:        receiptHash of previous receipt (or 0x0 for first)
  metadata:        arbitrary JSON (latency, status code, violation details, etc.)
  receiptHash:     keccak256 of the receipt (computed, excludes receiptHash and signature)
  signature:       EIP-191 signature of receiptHash by actorId
```

### Chain of custody

Receipts form a hash-linked chain per agreement:

```
Receipt 0 (request)
  prevHash: 0x0
  receiptHash: H0
  signature: sign(H0, consumer_key)
       │
       ▼
Receipt 1 (response)
  prevHash: H0
  receiptHash: H1
  signature: sign(H1, consumer_key)
       │
       ▼
Receipt 2 (payment)
  prevHash: H1
  receiptHash: H2
  signature: sign(H2, consumer_key)
       │
       ▼
Receipt 3 (sla_check)  [only if violation detected]
  prevHash: H2
  receiptHash: H3
  signature: sign(H3, consumer_key)
```

Any modification to an earlier receipt breaks the chain because subsequent `prevHash` values will not match.

### Anchoring

After receipts are created, the consumer (or any party) calls `POST /anchor` on the evidence service:
1. Evidence service computes a Merkle root of all receipt hashes for the agreement
2. Merkle root is committed on-chain via `commitEvidence(txKey, evidenceHash)` on the AgentCourt contract
3. The anchor record is stored locally with the tx hash and receipt IDs

This means:
- Individual receipt content lives off-chain (evidence service SQLite)
- The integrity proof (Merkle root) lives on-chain
- Anyone can verify that the off-chain receipts match the on-chain root

### Verification flow (judge service)

When the judge evaluates a dispute:
1. Fetch all receipts for the agreement from evidence service
2. Sort by sequence
3. Verify each receipt hash: `compute_receipt_hash(receipt) == receipt.receiptHash`
4. Verify chain integrity: `receipt[n].prevHash == receipt[n-1].receiptHash`
5. Verify first receipt: `receipt[0].prevHash == "0x0"`
6. Verify signatures: `recover_signer_eip191(receiptHash, signature) == actorId address`
7. Verify Merkle root matches on-chain commitment
8. Extract facts from receipt metadata for SLA evaluation

### Evidence trust boundary

| Layer | Trust model | Current status |
|-------|------------|----------------|
| Receipt hashes | Cryptographic (keccak256) | Implemented |
| Chain linking | Cryptographic (prevHash) | Implemented |
| Signatures | EIP-191 signer recovery | Implemented |
| Merkle anchoring | On-chain commitment | Implemented |
| Payload content | Off-chain (evidence service stores raw data) | Trust boundary — evidence service is trusted |
| Semantic truth | Receipts attest what happened, not whether the provider's output was "good" | LLM judge evaluates quality claims |

### V2 evidence improvements

- **Provider-signed response receipts**: Currently only consumer signs receipts. Provider should also sign response receipts to prevent consumer fabrication.
- **Zero-knowledge evidence reveal**: Prove payload properties (e.g., "response was under 3 seconds") without revealing payload content.
- **Third-party evidence attestation**: Allow neutral observers (monitoring services) to submit corroborating receipts.
- **Evidence pinning**: IPFS or Arweave pinning of receipt payloads for long-term availability.

---

## 10. Pricing and economics

### Fee structure

| Fee | Who pays | When | Amount | Destination |
|-----|---------|------|--------|-------------|
| **Service fee** | Consumer (deducted from payment) | On transaction completion | `serviceFeeRate` basis points (e.g., 100 = 1%) | Judge/operator balance |
| **Judge fee** | Dispute loser (frozen from plaintiff at filing) | On ruling submission | Tiered: $0.05 / $0.10 / $0.20 | Judge balance |
| **Service price** | Consumer | On `requestService()` | Set by provider per service | Locked in contract, released to provider on completion |

### Bond mechanics

**Agent registration bond**:
- Minimum deposit required to register as an agent (`minDeposit`)
- Serves as skin-in-the-game and initial balance for transactions
- Can be topped up with `deposit()` and withdrawn with `withdraw()`
- Bond is the agent's on-chain "credit" — insufficient balance blocks service requests and dispute filing

**Consumer bond per service**:
- Each service specifies `bondRequired` — minimum balance the consumer must hold to call the service
- This is not locked per call; it is a threshold check
- Prevents underfunded agents from consuming services they cannot pay disputes on

**Dispute stakes**:
- Plaintiff sets stake amount when filing dispute
- Defendant must have at least `stake` in their balance (frozen automatically)
- Plaintiff also pays the tiered judge fee (frozen from their balance)
- Winner receives `2 * stake` (both stakes returned)
- Judge receives the judge fee
- Loser's tier is escalated for future disputes

### Escrow flow for a single transaction

```
1. Consumer has balance >= service.price + service.bondRequired
2. requestService() → consumer balance -= service.price (locked in contract)
3. Provider fulfills → status = Fulfilled
4. IF consumer confirms:
   confirmTransaction() → provider balance += (price - platformFee)
                        → judge balance += platformFee
5. IF consumer disputes:
   fileDispute(stake) → consumer balance -= (stake + judgeFee)
                      → defendant balance -= stake
                      → funds frozen until ruling
6. submitRuling(winner):
   → winner balance += 2 * stake
   → judge balance += judgeFee
   → IF consumer wins: consumer balance += price (refund)
   → IF provider wins: provider balance += (price - platformFee)
7. IF nobody acts for 1 hour after fulfillment:
   autoComplete() → same as confirmTransaction()
```

### Platform revenue model

| Revenue stream | Mechanism | V1 | Later |
|---------------|-----------|-----|-------|
| Transaction fee | Basis points on each completed transaction | Yes | Yes |
| Judge fee | Per-dispute tiered fee | Yes | Yes |
| Gateway hosting | Monthly fee for managed gateway | No | Yes |
| Enterprise license | Dedicated deployment + support SLA | No | Yes |
| Reputation API access | Per-query or subscription fee for trust data | No | Yes |
| SLA template marketplace | Revenue share on premium SLA templates | No | Maybe |

### Anti-abuse economics

- **Frivolous dispute deterrent**: Filing a dispute costs stake + judge fee. If you lose, you forfeit both and your tier escalates permanently.
- **Serial bad actor deterrent**: After 3 losses, an agent pays Supreme-tier fees ($0.20) for every dispute and their balance is likely drained.
- **Underfunded agent blocking**: Balance checks on `requestService()` and `fileDispute()` prevent agents without skin in the game from participating.
- **Auto-complete**: Prevents consumers from indefinitely locking provider payments by never confirming.

---

## 11. SDK design

### Provider SDK (Python)

```python
from verdict_protocol.provider import VerdictProvider

# Initialize
provider = VerdictProvider(
    private_key="0x...",
    contract_address="0xFBf9...",
    rpc_url="https://rpc.testnet3.goat.network",
    evidence_service_url="http://localhost:4001",
)

# Register as agent (one-time)
provider.register(deposit_amount_usdc=10.0)

# Register a service
service_id = provider.register_service(
    terms=SLATemplate.basic_api(latency_ms=5000),
    price_usdc=0.001,
    bond_required_usdc=1.0,
)

# Protect a FastAPI app
from verdict_protocol.provider.fastapi import VerdictMiddleware

app = FastAPI()
app.add_middleware(
    VerdictMiddleware,
    provider=provider,
    x402_config={
        "facilitator_url": "https://www.x402.org/facilitator",
        "network": "eip155:84532",
    },
)

# Evidence capture is automatic — every request/response gets an X-Evidence-Hash header
# Dispute responses are handled by the SDK automatically
```

### Provider SDK (Node.js)

```typescript
import { VerdictProvider } from '@verdict-protocol/provider';
import { verdictMiddleware } from '@verdict-protocol/provider/express';

const provider = new VerdictProvider({
  privateKey: process.env.PROVIDER_PRIVATE_KEY,
  contractAddress: '0xFBf9...',
  rpcUrl: 'https://rpc.testnet3.goat.network',
  evidenceServiceUrl: 'http://localhost:4001',
});

await provider.register({ depositUsdc: 10 });

const serviceId = await provider.registerService({
  terms: SLATemplate.aiInference({ latencyMs: 30000, minQuality: 0.7 }),
  priceUsdc: 0.01,
  bondRequiredUsdc: 5,
});

// Express middleware
app.use(verdictMiddleware(provider, {
  x402: { facilitatorUrl: 'https://www.x402.org/facilitator', network: 'eip155:84532' },
}));
```

### Consumer SDK (Python)

```python
from verdict_protocol.consumer import VerdictConsumer

consumer = VerdictConsumer(
    private_key="0x...",
    contract_address="0xFBf9...",
    rpc_url="https://rpc.testnet3.goat.network",
    evidence_service_url="http://localhost:4001",
)

# Register and deposit
consumer.register(deposit_amount_usdc=10.0)

# Call a protected API with automatic evidence capture
result = consumer.call_service(
    service_id=0,
    endpoint="https://provider.example.com/api/data",
    method="GET",
    # x402 payment, receipt creation, and evidence anchoring happen automatically
)

# Check result
print(result.response_data)
print(result.evidence.receipt_chain)  # list of receipt IDs
print(result.evidence.anchor_tx)     # on-chain anchor tx hash

# Dispute if unhappy
if result.sla_violations:
    dispute = consumer.file_dispute(
        transaction_id=result.tx_id,
        stake_usdc=1.0,
        evidence_root=result.evidence.merkle_root,
    )
    print(f"Dispute filed: {dispute.dispute_id}, tier: {dispute.tier}")

# Check reputation before calling
rep = consumer.get_reputation("did:8004:0xProviderAddress")
print(f"Provider success rate: {rep.success_rate}%")
```

### SDK internals

Both SDKs wrap the same protocol layer:
1. `EscrowClient` — contract interaction (register, deposit, requestService, fileDispute, etc.)
2. `EvidenceClient` — evidence service API (store clauses, store receipts, anchor)
3. `ReceiptBuilder` — constructs and signs EventReceipt objects with proper chain linking
4. `ClauseBuilder` — constructs ArbitrationClause with SLA rules and remedy rules
5. `X402Client` — handles x402 payment flow at the HTTP level

---

## 12. Developer experience and CLI

### CLI tool: `verdict`

```bash
# Install
pip install verdict-protocol-cli
# or
npm install -g @verdict-protocol/cli

# Initialize a new provider project
verdict init --type provider
# Creates: .verdict/config.toml, .env.verdict, SLA template

# Register as agent
verdict register --deposit 10.0 --network testnet

# Register a service
verdict service create \
  --template basic-api \
  --price 0.001 \
  --bond 1.0 \
  --latency 5000

# Check service status
verdict service list
verdict service status 0

# View transactions
verdict tx list --service 0 --status fulfilled
verdict tx detail 42

# View disputes
verdict dispute list
verdict dispute detail 7
verdict dispute evidence 7

# Check reputation
verdict reputation 0xYourAddress
verdict reputation leaderboard

# Run local test flow
verdict test happy-path --mock-payment
verdict test dispute-path --mock-payment

# Start local development stack
verdict dev up
# Starts: evidence service (4001), provider api (4000), judge service (4002), reputation service (4003)

verdict dev down
verdict dev logs judge

# Export audit trail
verdict export --agreement-id <uuid> --format json
verdict export --dispute-id 7 --format csv
```

### Local development flow

```bash
# 1. Clone and setup
git clone <repo>
cd escrow
uv sync              # Python dependencies
pnpm install         # Node dependencies (frontend, contracts)

# 2. Copy environment template
cp .env.example .env
# Edit: add ANTHROPIC_API_KEY, private keys

# 3. Start all services
verdict dev up
# or: pnpm dev (runs all services via npm scripts)

# 4. Run demo
verdict test full --mock-payment
# or: pnpm demo

# 5. Open console
open http://localhost:4173
# or: pnpm demo:ui
```

### Configuration file: `.verdict/config.toml`

```toml
[network]
rpc_url = "https://rpc.testnet3.goat.network"
chain_id = 48816
contract_address = "0xFBf9b5293A1737AC53880d3160a64B49bA54801D"

[identity]
private_key_env = "PROVIDER_PRIVATE_KEY"  # reads from env var
did_format = "did:8004"

[services]
evidence_url = "http://127.0.0.1:4001"
judge_url = "http://127.0.0.1:4002"
reputation_url = "http://127.0.0.1:4003"

[x402]
facilitator_url = "https://www.x402.org/facilitator"
network = "eip155:84532"
allow_mock = true  # local development only

[sla]
default_template = "basic-api"
dispute_window_sec = 3600
evidence_window_sec = 1800
```

---

## 13. Console feature specification

### Screen inventory

**Screen 1: Dashboard Home**
- Service health cards: runner, evidence, provider, judge, reputation
  - Each card shows: status (up/down), latency, last check time
  - Click to drill into service details
- Quick stats: total transactions, active disputes, protected endpoints, total volume
- Recent activity feed: last 10 events across all services
- Network info: chain ID, contract address, block height, explorer link

**Screen 2: Services**
- Table: service ID, provider address, price, bond required, status, total calls, total disputes
- Filters: by provider, by status (Active/Paused/Retired), by price range
- Actions: register new service, update status, view terms hash
- Drill-down: click service → transaction list for that service

**Screen 3: Transactions**
- Table: tx ID, service ID, consumer, provider, payment, status, created at, fulfilled at
- Filters: by status (Requested/Fulfilled/Completed/Disputed), by service, by agent, by date range
- Actions: confirm transaction, auto-complete, view on explorer
- Drill-down: click transaction → full detail view with request/response hashes and linked dispute

**Screen 4: Agreements Explorer**
- Search by agreement ID
- Shows: arbitration clause terms, SLA rules, receipt chain (with validation status), anchor status
- Receipt chain visualization: timeline of receipts with hash links
- Anchor proof: Merkle root, on-chain tx hash, verification status
- Export: full agreement bundle as JSON

**Screen 5: Disputes**
- Table: dispute ID, tx ID, plaintiff, defendant, stake, tier, status, ruling
- Filters: by status (filed/responded/resolved/manual_review), by tier, by date range
- Drill-down: click dispute → full detail:
  - Timeline: filed → responded → ruled
  - Evidence bundles: plaintiff evidence hash, defendant evidence hash
  - Verdict: winner, reason codes, confidence, full judicial opinion
  - Fund movements: stake transfers, judge fee, payment release
  - On-chain tx hashes for filing and ruling

**Screen 6: Verdicts**
- Table: dispute ID, winner, confidence, reason codes, tier, processed at
- Detail modal: full judicial opinion with formatted text
- Verdict package export: signed JSON artifact
- Opinion diff view (for appeals): side-by-side lower court vs appellate opinion

**Screen 7: Reputation**
- Leaderboard: agent address/DID, score, transactions, disputes won/lost, success rate
- Sort by: score, transaction count, success rate, registration date
- Drill-down: click agent → full history:
  - Transaction history
  - Dispute history (filed and received)
  - Score progression over time
  - On-chain stats vs off-chain metrics comparison

**Screen 8: Run Orchestration** (demo/testing)
- Mode selector: happy path, dispute path, full
- Start/stop controls
- Live SSE-backed step timeline
- Event log with expandable details
- Artifact viewer: receipt IDs, tx hashes, agreement IDs

**Screen 9: Settings**
- Webhook configuration (URL, events, secret)
- Environment info: network, contract, services
- API keys management
- Notification preferences

### Operator actions

| Action | Screen | Description |
|--------|--------|-------------|
| Retry failed ruling | Disputes | Re-submit a ruling that failed on-chain |
| Override to manual review | Disputes | Flag a dispute for human review |
| Force auto-complete | Transactions | Complete a stuck fulfilled transaction |
| Export audit trail | Agreements | Download full evidence + verdict bundle |
| Pause service | Services | Set service status to Paused |
| Bulk export | Any table | CSV/JSON export of filtered results |

---

## 14. Reputation system design

### Current system (V1)

Score mappings (from `scorer.py`):
- `completed_without_dispute`: +1
- `won_dispute`: +2
- `lost_dispute`: -5
- `lost_as_filer`: -3

This is additive and simple. It works for demos but is trivially gameable.

### V2 reputation model

#### Composite score

Instead of a single number, reputation is a vector:

```json
{
  "agent": "did:8004:0xAddress",
  "scores": {
    "reliability": 0.95,       // % of transactions completed without dispute
    "quality": 0.88,           // avg quality score from verdict assessments
    "responsiveness": 0.92,    // avg response time vs SLA targets
    "dispute_record": 0.70,    // weighted dispute win rate
    "longevity": 0.60          // time-weighted activity score
  },
  "aggregate": 0.85,           // weighted composite
  "confidence": "high",        // based on sample size
  "sample_size": 142,          // total transactions
  "last_updated": 1710000000
}
```

#### Scoring formulas

**Reliability score**:
```
reliability = successful_transactions / total_transactions
```

**Quality score** (new — requires verdict metadata):
```
quality = avg(verdict.confidence for all disputes where agent was provider and won)
          weighted by recency (exponential decay, half-life = 30 days)
```

**Dispute record score**:
```
dispute_record = (disputes_won * 2 - disputes_lost * 5) / max(1, total_disputes * 5)
                 clamped to [0, 1]
```

**Longevity score**:
```
longevity = min(1.0, days_since_registration / 180)
            * min(1.0, total_transactions / 100)
```

**Aggregate**:
```
aggregate = 0.35 * reliability
          + 0.25 * quality
          + 0.15 * responsiveness
          + 0.15 * dispute_record
          + 0.10 * longevity
```

#### Confidence levels

| Sample size | Confidence |
|-------------|-----------|
| 0-9 | `unrated` |
| 10-49 | `low` |
| 50-199 | `medium` |
| 200+ | `high` |

Consumers should treat `unrated` and `low` confidence agents with caution. The SDK can enforce minimum confidence thresholds.

#### Decay

Scores decay toward neutral (0.5) if an agent is inactive:
- After 30 days of inactivity, scores begin decaying at 1% per day
- After 90 days, scores are halved from their peak
- Registration and bond are not affected — only the reputation display

#### Sybil resistance

| Attack | Mitigation |
|--------|-----------|
| Create many agents to dilute bad reputation | ERC-8004 identity binding — one identity per address, identity requires registration deposit |
| Self-dealing (create consumer + provider, transact with self) | Contract prevents calling own service (`msg.sender != s.provider`). Cross-address self-dealing is harder to detect but has real cost (deposits, fees, gas). |
| Reputation farming (many cheap transactions to inflate score) | Weight by transaction value. Low-value transactions contribute less to reputation. |
| Dispute manipulation (file disputes against yourself to boost win count) | Disputes cost stake + judge fee. Losing a self-filed dispute costs -5 points. Net negative expected value. |

#### On-chain vs off-chain reputation

| Data | Storage | Reason |
|------|---------|--------|
| Transaction count, disputes won/lost, total earned/spent | On-chain (`AgentStats` struct) | Tamper-proof, publicly verifiable |
| Composite scores, decay, confidence | Off-chain (reputation service) | Requires computation, updates frequently |
| ERC-8004 feedback events | On-chain (reputation registry) | Standard interface for cross-platform queries |
| Score history and trends | Off-chain (reputation service DB) | Too much data for on-chain storage |

---

## 15. Webhook and notification system

### Event types

| Event | Payload | Who receives |
|-------|---------|-------------|
| `transaction.created` | txId, serviceId, consumer, provider, payment | Provider |
| `transaction.fulfilled` | txId, responseHash | Consumer |
| `transaction.completed` | txId, payment, fee | Both parties |
| `transaction.auto_completed` | txId, payment | Both parties |
| `dispute.filed` | disputeId, txId, plaintiff, stake, tier | Defendant |
| `dispute.responded` | disputeId, defendantEvidence | Plaintiff |
| `dispute.ruling` | disputeId, winner, loser, award, reasonCodes | Both parties |
| `evidence.anchored` | agreementId, rootHash, txHash | Both parties |
| `reputation.updated` | agentId, newScore, delta, reason | Agent |
| `service.status_changed` | serviceId, oldStatus, newStatus | Subscribers |

### Webhook delivery

```
POST https://consumer.example.com/webhooks/verdict
Content-Type: application/json
X-Verdict-Signature: sha256=<HMAC of body with webhook secret>
X-Verdict-Event: dispute.ruling
X-Verdict-Delivery-Id: <uuid>
X-Verdict-Timestamp: <unix seconds>

{
  "event": "dispute.ruling",
  "timestamp": 1710000000,
  "data": {
    "disputeId": 7,
    "txId": 42,
    "winner": "0xConsumerAddress",
    "loser": "0xProviderAddress",
    "award": "2000000",
    "reasonCodes": ["sla_breach:latency"],
    "tier": 0,
    "verdictHash": "0xabc...",
    "explorerUrl": "https://testnet3.goat.network/tx/0x..."
  }
}
```

### Delivery guarantees

- **At-least-once delivery**: Events may be delivered more than once. Consumers should deduplicate by `X-Verdict-Delivery-Id`.
- **Retry policy**: 3 retries with exponential backoff (5s, 30s, 300s). After 3 failures, webhook is marked `unhealthy`.
- **Timeout**: 10 second response timeout per delivery attempt.
- **Signature verification**: HMAC-SHA256 of the raw body using the webhook secret. Consumers must verify before processing.

### Notification channels

| Channel | V1 | Later |
|---------|-----|-------|
| Webhooks (HTTP POST) | Yes | Yes |
| Telegram bot | Yes (existing) | Yes |
| Email | No | Yes |
| Slack integration | No | Yes |
| In-console notifications | Yes | Yes |

---

## 16. Multi-agent transaction chains

### Problem

Agent A calls Agent B, which calls Agent C. Agent C returns garbage. Agent B passes it to Agent A. Agent A files a dispute against Agent B. But the root cause is Agent C.

### Chain transaction model

```
Agent A (consumer)
  └─ calls Agent B (provider + consumer)
       └─ calls Agent C (provider)
            └─ returns bad response
```

Each hop is a separate on-chain transaction with its own:
- Service registration
- Payment lock
- Evidence receipts
- Dispute eligibility

### V1 approach: independent disputes

In V1, each transaction is independent. Agent A disputes Agent B. Agent B separately disputes Agent C. This is simple and already works with the current contract.

Implications:
- Agent B bears the risk of Agent C's failures
- Agent B should select Agent C based on reputation
- Agent B can pass Agent C's response receipts as evidence in their dispute with Agent A

### V2 approach: linked transactions

Add a `parentTxId` field to transactions:

```solidity
struct Transaction {
    // ... existing fields ...
    uint256 parentTxId;  // 0 if root transaction
}
```

This enables:
- **Dispute propagation**: When Agent A disputes Agent B, and Agent B can prove the failure originated from Agent C, the dispute can be redirected.
- **Chain evidence**: Receipt chains across hops can be linked via agreement IDs.
- **Cascading refunds**: If Agent C loses, refunds propagate back through the chain.

### V3 approach: transaction DAGs

For complex agent workflows (fan-out, parallel calls, conditional routing):
- Model transactions as a directed acyclic graph
- Each node is a transaction with edges to dependencies
- Dispute resolution considers the full graph
- SLA evaluation includes end-to-end latency across the DAG

This is out of scope for V1 and V2 but the contract should not preclude it.

---

## 17. Appeals system design

### Current state

The contract supports tier escalation via `disputeLossCount`:
- First dispute: District court (Haiku)
- After 1 loss: Appeals court (Sonnet)
- After 2+ losses: Supreme court (Opus)

But this is **automatic escalation based on agent history**, not an appeals mechanism for a specific dispute.

### V2 appeals system

#### Appeal flow

```
1. District ruling issued for Dispute #7
2. Loser has 24 hours to file appeal
3. Appeal requires:
   - New stake (1.5x original)
   - Appeals-tier judge fee ($0.10)
   - Written appeal brief (optional, submitted as evidence)
4. Appeals judge reviews:
   - Original evidence bundle
   - District court opinion
   - Appeal brief (if any)
   - Any new evidence submitted during appeal window
5. Appeals judge either AFFIRMS or OVERTURNS
6. If overturned: original ruling reversed, stakes redistributed
7. If affirmed: appellant loses appeal stake too
8. Supreme appeal available after appeals loss (same flow, 2x stake, $0.20 fee)
```

#### Contract changes needed

```solidity
struct Dispute {
    // ... existing fields ...
    uint256 appealOf;        // 0 if original, else disputeId of lower court
    uint8 maxTier;           // highest tier this dispute can reach
    uint64 appealDeadline;   // timestamp after which no appeal is possible
}

function fileAppeal(uint256 disputeId, uint256 stake, bytes32 evidence) external returns (uint256);
```

#### Appeal constraints

- Only the **loser** of a dispute can appeal
- Maximum 2 appeals per original dispute (District → Appeals → Supreme)
- Appeal stake must be >= 1.5x the original stake
- Appeal deadline: 24 hours after ruling submission
- No appeal after Supreme ruling (final)

#### LLM judge behavior on appeal

The Appeals/Supreme prompts (already implemented in `APPEAL_PROMPT`) instruct the judge:
- Review the lower court's reasoning
- Give no automatic deference — overturn if evidence warrants it
- Use a more capable model (Sonnet for Appeals, Opus for Supreme)
- Reference the lower court opinion in the appellate opinion

---

## 18. Agent identity and DID framework

### ERC-8004 identity

Verdict Protocol uses ERC-8004 (on-chain identity standard) for agent identification:

- **Identity registry**: `IIdentityRegistry` at `0x556089008Fc0a60cD09390Eca93477ca254A5522`
- **Reputation registry**: `IReputationRegistry` at `0x52B2e79558ea853D58C2Ac5Ddf9a4387d942b4B4`
- **DID format**: `did:8004:0x<40-hex-address>`

### Identity lifecycle

```
1. Agent deploys/controls an Ethereum address
2. Agent mints an ERC-8004 identity token (one per address)
3. Agent registers on AgentCourt with deposit bond
4. Contract verifies identity: identityRegistry.balanceOf(agent) > 0
5. All receipts reference agent by DID: did:8004:0xAddress
6. Reputation feedback is given to the ERC-8004 token ID
```

### Identity enforcement

The contract has a `requireIdentity` flag:
- When `true`: `register()` requires `identityRegistry.balanceOf(msg.sender) > 0`
- When `false`: any address can register (current testnet default)

For production: `requireIdentity = true` to ensure all agents have verifiable on-chain identities.

### DID resolution in protocol

The protocol package provides:
- `did_to_address("did:8004:0xABC...")` → `"0xABC..."`
- `to_did("0xABC...")` → `"did:8004:0xABC..."`

All receipt `actorId` and `counterpartyId` fields use DID format. Signature verification extracts the address from the DID and verifies against the EIP-191 recovered signer.

### Future identity features

- **Agent metadata**: Name, description, capabilities, endpoint URLs stored off-chain, linked by DID
- **Agent delegation**: One identity can authorize sub-agents to act on its behalf
- **Cross-chain identity**: Bridge ERC-8004 identities to other chains
- **Verified agent badges**: Platform-issued attestations for agents that pass verification criteria (KYC for operators, code audit for autonomous agents)

---

## 19. V1 scope and non-goals

### In scope

- One canonical contract (`AgentCourt.sol`) and ABI on GOAT Testnet3
- One canonical service runtime (`apps/*` + `packages/protocol/`)
- One canonical frontend (chosen between judge-frontend and verdict-frontend)
- Paid API flow: register → request → fulfill → confirm (or dispute)
- Evidence anchoring: receipt chains + Merkle root on-chain
- Dispute filing and ruling: deterministic SLA check + LLM judicial opinion
- Reputation updates: on-chain stats + off-chain composite scores + ERC-8004 feedback
- Provider and consumer SDKs (Python first, Node.js second)
- CLI tool for development and operations
- Webhook notifications for key events
- Testnet deployment with canonical contract address
- 2-5 pilot customers with real integrations

### Out of scope for V1

| Feature | Reason | Phase |
|---------|--------|-------|
| Decentralized judge quorum | Requires governance design, multiple judge operators | V3+ |
| Stake-weighted protocol governance | No token, no governance needed yet | V3+ |
| Permissionless marketplace | Need supply-side first | V3 |
| Advanced sybil resistance | Basic measures sufficient for pilot scale | V2 |
| Many-chain production support | GOAT Testnet3 first, expand after product-market fit | V2 |
| Full trustless evidence reveal | ZK proofs for arbitrary payloads are research-grade | V3+ |
| Partial refunds in contract | Requires V2 ABI change | V2 |
| Cross-chain agent identity bridging | Single chain sufficient for V1 | V3 |
| Streaming/WebSocket evidence capture | REST-only in V1 | V2 |
| Multi-hop dispute propagation | Independent disputes per hop in V1 | V2 |

---

## 20. Product architecture target

### Core layers

```
┌─────────────────────────────────────────────────────────┐
│                    CONSUMER / AGENT                      │
│  (Consumer SDK, CLI, Agent Framework Integration)        │
└──────────────────────┬──────────────────────────────────┘
                       │ x402 payment + HTTP request
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   GATEWAY LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ x402         │  │ Request/     │  │ Evidence      │ │
│  │ Enforcement  │  │ Response     │  │ Hash          │ │
│  │              │  │ Capture      │  │ Emission      │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
│  (Rust gateway for production / Python provider_api)     │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PROTOCOL    │ │   SERVICE    │ │  CONTROL     │
│  LAYER       │ │   LAYER      │ │  PLANE       │
│              │ │              │ │              │
│ • Schemas    │ │ • Evidence   │ │ • Console    │
│ • Hashing    │ │   Service    │ │ • Orchestr.  │
│ • Signatures │ │ • Judge      │ │ • Merchant   │
│ • Receipt    │ │   Service    │ │   Config     │
│   Chain      │ │ • Reputation │ │ • Webhooks   │
│ • Contract   │ │   Service    │ │ • Monitoring │
│   Client     │ │ • Provider   │ │ • Audit Logs │
│              │ │   API (ref)  │ │              │
└──────┬───────┘ └──────┬───────┘ └──────────────┘
       │                │
       └────────┬───────┘
                ▼
┌─────────────────────────────────────────────────────────┐
│                   ON-CHAIN LAYER                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ AgentCourt   │  │ Identity     │  │ Reputation    │ │
│  │ Contract     │  │ Registry     │  │ Registry      │ │
│  │              │  │ (ERC-8004)   │  │ (ERC-8004)    │ │
│  │ • Registry   │  │              │  │               │ │
│  │ • Escrow     │  │              │  │               │ │
│  │ • Disputes   │  │              │  │               │ │
│  │ • Evidence   │  │              │  │               │ │
│  │ • Rulings    │  │              │  │               │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
│  GOAT Testnet3 (chain ID 48816)                         │
└─────────────────────────────────────────────────────────┘
```

### Architecture decision

Keep the current split where x402 payment happens at the API edge and escrow/dispute state lives on-chain, but present it as one product. Internally:
- The **Rust gateway** (`agent-court-rs`) handles production traffic: x402 verification, request/response proxying, evidence hash emission
- The **Python monorepo** (`apps/*` + `packages/protocol/`) handles everything else: evidence storage, dispute resolution, reputation, orchestration
- The two communicate via HTTP APIs and shared on-chain state

These can remain separate codebases as long as their interfaces are stable and versioned.

---

## 21. Gateway architecture

### Request flow (Rust gateway)

```
Consumer                    Gateway                     Provider API
   │                          │                              │
   │  GET /api/data           │                              │
   │  + x402 payment header   │                              │
   │ ─────────────────────►   │                              │
   │                          │                              │
   │                     1. Verify x402 payment              │
   │                        (call facilitator)               │
   │                     2. If invalid → 402 Payment Required│
   │                     3. Capture request:                 │
   │                        - timestamp                      │
   │                        - request body hash              │
   │                        - payment reference              │
   │                          │                              │
   │                          │  Proxy request               │
   │                          │ ─────────────────────────►   │
   │                          │                              │
   │                          │  Response                    │
   │                          │ ◄─────────────────────────   │
   │                          │                              │
   │                     4. Capture response:                │
   │                        - response body hash (keccak256) │
   │                        - latency measurement            │
   │                        - status code                    │
   │                     5. Emit X-Evidence-Hash header      │
   │                     6. Async: POST receipts to          │
   │                        evidence service                 │
   │                          │                              │
   │  Response                │                              │
   │  + X-Evidence-Hash       │                              │
   │ ◄─────────────────────   │                              │
```

### Gateway deployment model

**Option A: Sidecar** — Gateway runs alongside the provider's API as a reverse proxy (same host or same pod). Lowest latency, provider manages infrastructure.

**Option B: Managed proxy** — Verdict Protocol hosts the gateway. Provider points their DNS to the gateway, which proxies to their origin. Zero infrastructure for provider, but adds a network hop.

**Option C: SDK middleware** — No separate gateway process. Provider embeds the SDK middleware directly in their application (FastAPI middleware, Express middleware). Simplest deployment, but provider's application handles payment verification.

V1 supports Option C (SDK middleware) with the Python `provider_api` as reference. Option A and B use the Rust gateway and are production targets.

### Gateway configuration

```toml
[gateway]
listen_addr = "0.0.0.0:8080"
upstream_url = "http://localhost:4000"  # provider's actual API

[x402]
facilitator_url = "https://www.x402.org/facilitator"
network = "eip155:84532"
seller_wallet = "0xProviderAddress"

[evidence]
service_url = "http://localhost:4001"
async_receipt_submission = true  # non-blocking

[tls]
cert_path = "/etc/ssl/cert.pem"
key_path = "/etc/ssl/key.pem"
```

---

## 22. API specification

### Evidence service (port 4001)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/clauses` | Register an arbitration clause. Validates schema and hash. |
| `GET` | `/clauses` | List all clauses (limit, offset). |
| `GET` | `/clauses/{agreement_id}` | Get clause by agreement ID. |
| `POST` | `/receipts` | Store an event receipt. Validates schema, hash, and chain integrity. |
| `GET` | `/receipts` | Query receipts by `agreementId` and/or `actorId`. |
| `GET` | `/receipts/{receipt_id}` | Get single receipt. |
| `POST` | `/anchor` | Compute Merkle root of receipts and commit on-chain. |
| `GET` | `/anchors` | Get anchor by `agreementId` query param. |
| `GET` | `/anchors/by-root/{root_hash}` | Reverse lookup anchor by Merkle root. |
| `GET` | `/agreements/{agreement_id}` | Full agreement view: clause + receipts + anchor + chain validation. |
| `GET` | `/agreements` | Summary of all agreements. |

### Judge service (port 4002)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health + escrow capabilities + contract sanity. |
| `GET` | `/verdicts` | List all verdicts with count. |
| `GET` | `/verdicts/{dispute_id}` | Single verdict with full opinion, or 404. |

The judge service also runs a background watcher that polls for `DisputeFiled` events and processes disputes automatically.

### Reputation service (port 4003)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health + escrow sanity. |
| `GET` | `/reputation` | Leaderboard of all agents with scores. |
| `GET` | `/reputation/{actor_id}` | Single agent reputation record. |

### Provider API (port 4000)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/data` | Protected endpoint. Returns JSON payload. x402 payment required. |
| `GET` | `/api/data?bad=true` | Returns intentionally bad response (for dispute testing). |

All responses include `X-Evidence-Hash: 0x<keccak256(body)>` header.

### Demo runner (port 4005)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health. |
| `GET` | `/config` | Runtime configuration. |
| `POST` | `/runs` | Create a new demo run (happy/dispute/full mode). |
| `GET` | `/runs/{run_id}/stream` | SSE stream of run events. |
| `POST` | `/dashboard-payment` | Push transfer to GOAT dashboard. |

### Contract ABI (key functions)

| Function | Access | Description |
|----------|--------|-------------|
| `register(depositAmount)` | Public | Register agent with bond deposit |
| `deposit(amount)` | Registered | Add to balance |
| `withdraw(amount)` | Has balance | Withdraw from balance |
| `registerService(termsHash, price, bondRequired)` | Registered | Register API service |
| `updateService(serviceId, status)` | Provider | Change service status |
| `requestService(serviceId, requestHash)` | Registered | Initiate transaction, lock payment |
| `fulfillTransaction(txId, responseHash)` | Provider | Mark transaction fulfilled |
| `confirmTransaction(txId)` | Consumer | Confirm and release payment |
| `autoComplete(txId)` | Anyone (after 1hr) | Auto-release payment |
| `fileDispute(txId, stake, evidence)` | Party to tx | File dispute, freeze stakes |
| `respondDispute(disputeId, evidence)` | Defendant | Submit counter-evidence |
| `submitRuling(disputeId, winner)` | Judge only | Execute ruling, transfer funds |
| `commitEvidence(txKey, evidenceHash)` | Registered | Commit evidence hash on-chain |
| `getJudgeFee(agent)` | View | Get current tier and fee for agent |

---

## 23. Data model and storage strategy

### Current storage: SQLite

Each service uses its own SQLite database with WAL mode:

| Database | Service | Tables |
|----------|---------|--------|
| `verdict_evidence.db` | Evidence service | `clauses`, `receipts`, `anchors` |
| `verdict_judge.db` | Judge service | `verdicts` (dispute state + opinions) |
| `verdict_reputation.db` | Reputation service | `reputation` (agent scores + stats) |
| `verdict.db` | Shared/legacy | General state |

### Schema details

**Evidence service tables:**
```sql
clauses (
  clause_id TEXT PRIMARY KEY,
  agreement_id TEXT UNIQUE,
  chain_id TEXT,
  contract_address TEXT,
  clause_hash TEXT,
  payload_json TEXT,
  created_at TEXT
)

receipts (
  receipt_id TEXT PRIMARY KEY,
  agreement_id TEXT,
  actor_id TEXT,
  sequence INTEGER,
  receipt_hash TEXT,
  prev_hash TEXT,
  payload_json TEXT,
  created_at TEXT,
  UNIQUE(agreement_id, sequence)
)

anchors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agreement_id TEXT UNIQUE,
  root_hash TEXT,
  tx_hash TEXT,
  receipt_ids_json TEXT,
  created_at TEXT
)
```

### Migration path: SQLite → PostgreSQL

For production (Phase 2+):

| Concern | SQLite (current) | PostgreSQL (target) |
|---------|-----------------|-------------------|
| Concurrency | WAL mode, single-writer | Full MVCC, many concurrent writers |
| Replication | None | Streaming replication, read replicas |
| Backup | File copy | pg_dump, continuous archiving |
| Indexing | Basic B-tree | B-tree, GIN, GiST, partial indexes |
| JSON queries | json_extract | JSONB with indexing |
| Connection pooling | N/A | pgBouncer |

Migration plan:
1. Abstract storage behind a `Repository` interface in each service
2. Implement PostgreSQL repository alongside SQLite
3. Add `STORAGE_BACKEND=sqlite|postgres` env var
4. Run both in parallel during migration, compare results
5. Switch to PostgreSQL as default for production

### On-chain data model

The contract stores structured data that is the source of truth for:
- Agent registration and balances
- Service definitions
- Transaction state
- Dispute state and outcomes
- Evidence hash commitments
- Agent stats (transactions, disputes, earnings)

Off-chain services index on-chain events and store enriched data (full receipts, LLM opinions, composite scores) that cannot fit on-chain.

---

## 24. Interoperability and standards

### Standards used

| Standard | Usage | Status |
|----------|-------|--------|
| **x402** | HTTP payment protocol for API monetization | Integrated (Base Sepolia) |
| **ERC-20** | USDC payment token | Integrated |
| **ERC-8004** | On-chain identity and reputation registries | Integrated |
| **EIP-191** | Signed message format for receipt signatures | Integrated |
| **JSON Schema Draft 2020-12** | Validation of clauses, receipts, verdict packages | Integrated |
| **Keccak-256** | Canonical hashing for all protocol objects | Integrated |
| **DID** | `did:8004:0x...` format for agent identification | Integrated |
| **SSE** | Server-Sent Events for real-time streaming | Integrated (demo runner) |

### Future integrations

| Standard/Protocol | Purpose | Phase |
|-------------------|---------|-------|
| **MCP (Model Context Protocol)** | Allow AI agents to discover and invoke Verdict-protected services via MCP tools | V2 |
| **OpenAPI 3.1** | Auto-generate SDK clients and documentation from service specs | V1 |
| **ERC-4337** | Account abstraction for agent wallets (smart contract wallets, gasless transactions) | V2 |
| **IPFS / Arweave** | Permanent evidence storage for long-term audit trails | V2 |
| **Chainlink CCIP** | Cross-chain evidence verification and dispute resolution | V3 |
| **W3C Verifiable Credentials** | Agent capability attestations and credential verification | V3 |

### Agent framework integrations

| Framework | Integration point | Description |
|-----------|------------------|-------------|
| **LangChain** | Tool wrapper | Verdict-protected API as a LangChain tool with automatic payment and evidence |
| **CrewAI** | Agent tool | CrewAI agents can call Verdict services with built-in dispute capability |
| **AutoGen** | Function call | AutoGen function that wraps Verdict consumer SDK |
| **Eliza** | Plugin | Eliza OS plugin for agent-to-agent commerce via Verdict |

---

## 25. Security and threat model

### Trust assumptions

| Component | Trust level | Assumption |
|-----------|------------|-----------|
| AgentCourt contract | Trustless | Code is law. Deployed and immutable. Bugs are permanent. |
| Judge service | Trusted operator | Single judge key controls all rulings. Must not be compromised. |
| Evidence service | Trusted operator | Stores receipts. Could theoretically withhold or fabricate evidence. |
| x402 facilitator | Trusted third party | Validates payment proofs. If compromised, fake payments could pass. |
| LLM provider (Anthropic) | Trusted third party | Provides judicial reasoning. If compromised, rulings could be manipulated. |
| Consumer agents | Adversarial | May fabricate evidence, file frivolous disputes, attempt prompt injection. |
| Provider agents | Adversarial | May deliver bad service, fabricate response hashes, attempt to avoid disputes. |

### Threat matrix

| Threat | Impact | Likelihood | Mitigation |
|--------|--------|-----------|------------|
| **Judge key compromise** | Attacker submits arbitrary rulings | Medium | V1: secure key storage, monitoring. V2: KMS/HSM. V3: multisig judge. |
| **Evidence fabrication** | Consumer submits fake receipts | Medium | Receipt signatures verify actorId. Provider should co-sign response receipts (V2). |
| **Prompt injection via evidence** | Adversarial party embeds instructions in evidence to manipulate LLM judge | High | `_sanitize_user_text()` strips role prefixes and user-content tags. Deterministic checks override LLM. |
| **Frivolous dispute spam** | Attacker drains defender balance through many disputes | Low | Stake + fee cost makes spam expensive. Tier escalation increases cost per dispute. |
| **Self-dealing reputation farming** | Create fake transactions to inflate reputation | Medium | Contract prevents calling own service. Cross-address farming has real cost (deposits, fees, gas). |
| **Evidence service unavailability** | Judge cannot fetch evidence, disputes stall | Medium | Judge service handles missing evidence gracefully (rules based on available data). Add redundancy in V2. |
| **Reentrancy on token transfers** | ERC-20 reentrancy during escrow operations | Low | USDC is not reentrant. State changes before external calls. |
| **Front-running disputes** | Miner/sequencer front-runs fileDispute to drain defendant | Low | Defendant balance check prevents over-draining. GOAT network has lower MEV risk. |
| **LLM hallucination in verdict** | Judge hallucinates facts not in evidence | Medium | Deterministic fact extraction first. LLM only generates narrative. Confidence threshold for auto-submission. |

### Key management

| Key | Current | V1 target | V2 target |
|-----|---------|-----------|-----------|
| Judge private key | `.env` file | Encrypted env var, restricted access | AWS KMS / GCP Cloud HSM |
| Provider private key | `.env` file | Per-provider, env-based | Provider manages own keys |
| Consumer private key | `.env` file | Per-consumer, env-based | Agent wallet (ERC-4337) |
| Webhook signing secret | Not implemented | HMAC-SHA256 per webhook endpoint | Rotate monthly |
| Anthropic API key | `.env` file | Encrypted env var | Vault-managed, auto-rotation |

### Rate limiting

| Endpoint | Limit | Scope |
|----------|-------|-------|
| Evidence service (writes) | 100 req/min | Per agent address |
| Evidence service (reads) | 1000 req/min | Per IP |
| Judge service (verdicts) | 500 req/min | Per IP |
| Reputation service | 1000 req/min | Per IP |
| Provider API | Provider-defined | Per consumer agent |
| Dispute filing (on-chain) | Gas + stake cost | Economic rate limiting |

---

## 26. Repo strategy

### Canonical runtime

Treat `escrow/apps/*` plus the protocol package as the source of truth.

### Legacy paths

Move these to `_legacy/` directory with a README explaining their historical purpose:
- `server/` — early Python backend
- `demo/` — pre-services era demo scripts
- `guardian/` — proxy reference implementation
- old compatibility shims under `judge-frontend/` (`court_watcher.py`, `verdict_api.py`)

### Frontend strategy

Pick one frontend path:
- either finish `verdict-frontend` (React rewrite)
- or keep `judge-frontend` (monolithic SPA) and modularize it

Recommendation:
- Use `judge-frontend` as the short-term canonical console because it is more complete
- Mine it for flows and migrate into `verdict-frontend` only when the React app reaches feature parity
- Do not run both in production simultaneously

### Gateway strategy

Keep `agent-court-rs` as a separate infra repo/product:
- it becomes the production gateway for managed and self-hosted deployments
- the Python `provider_api` stays the reference app, demo service, and SDK middleware example

### Monorepo structure target

```
escrow/
├── apps/
│   ├── evidence_service/    # Canonical
│   ├── provider_api/        # Canonical (reference implementation)
│   ├── judge_service/       # Canonical
│   ├── reputation_service/  # Canonical
│   ├── consumer_agent/      # Canonical (demo + SDK usage example)
│   └── demo_runner/         # Canonical (orchestration + testing)
├── packages/
│   └── protocol/            # Canonical (shared library)
├── contracts/
│   ├── AgentCourt.sol       # Canonical
│   ├── abi/                 # Generated
│   └── scripts/             # Deployment
├── console/                 # Canonical frontend (renamed from judge-frontend or verdict-frontend)
├── docs/                    # Product plan, API docs, onboarding guides
├── _legacy/                 # Historical reference (server/, demo/, guardian/)
├── .github/                 # CI/CD workflows
└── sdk/                     # Published SDK packages (future)
    ├── python/
    └── node/
```

---

## 27. Current gaps and solutions

| # | Gap | Impact | Proposed solution | Phase |
|---|-----|--------|-------------------|-------|
| 1 | Branding split (Verdict Protocol vs Agent Court) | External confusion | Declare Verdict Protocol = platform, Agent Court = arbitration module. Update all docs. | 0 |
| 2 | Evidence trust boundary is mixed (off-chain payloads, on-chain hashes) | Disputes depend on trusted evidence service | V1: receipt signatures + Merkle anchoring. V2: provider co-signed receipts. V3: ZK proofs. | 1-3 |
| 3 | Judge authority is single-key | Single point of failure for all rulings | V1: secure key storage + monitoring. V2: KMS/HSM. V3: multisig or quorum. | 1-3 |
| 4 | Mock payment mode confusion | Testers may think mock mode is real settlement | Add clear `[MOCK MODE]` banner in console and API responses. Separate env profiles. | 0 |
| 5 | Frontend split (judge-frontend vs verdict-frontend) | Maintenance burden, user confusion | Choose one. Rename to `console/`. Retire the other. | 0 |
| 6 | No canonical deployment story | Different docs reference different addresses | Single `.env.example` with canonical testnet values. Deployment guide. | 0 |
| 7 | No production-grade secrets management | Keys in `.env` files | V1: encrypted env vars. V2: KMS/HSM integration. | 1-2 |
| 8 | Simple reputation (additive score) | Gameable, no decay, no composite | V2 reputation model (see section 14). | 1-2 |
| 9 | No automated testing | Low confidence in changes | Add CI: unit tests, protocol tests, one e2e dry-run. | 0-1 |
| 10 | No webhook system | Providers/consumers must poll for updates | Implement webhook delivery (see section 15). | 1 |
| 11 | No provider onboarding flow | Cannot acquire users | SDK + CLI + onboarding guide (see sections 11-12). | 1 |
| 12 | No rate limiting | Services vulnerable to abuse | Add per-agent and per-IP rate limits (see section 25). | 1 |
| 13 | SQLite in production | Single-node, no replication | Migrate to PostgreSQL for production (see section 23). | 2 |
| 14 | No observability | Blind to production issues | Add structured logging, metrics, alerting (see section 31). | 2 |
| 15 | No appeals mechanism | Losers have no recourse on a specific dispute | Design in V1, implement in V2 (see section 17). | 2 |

---

## 28. Delivery phases

### Phase 0: Consolidate the product spine
Timeline: 1-2 weeks

Goals:
- Choose final naming (Verdict Protocol platform, Agent Court arbitration module)
- Define canonical runtime (`apps/*` + `packages/protocol/`)
- Define canonical contract deployment (one address, one ABI, one env template)
- Choose canonical frontend (rename to `console/`)
- Document one happy path and one dispute path
- Move legacy code to `_legacy/`

Concrete tasks:
1. Update README with single getting-started flow
2. Create `.env.example` with all canonical values
3. Write `verdict dev up` bootstrap script (starts all 4 services)
4. Rename chosen frontend directory to `console/`
5. Move `server/`, `demo/`, `guardian/` to `_legacy/`
6. Add `[MOCK MODE]` indicators to mock payment responses
7. Verify clean `git clone → uv sync → verdict dev up → verdict test full` flow

Exit criteria:
- Single README flow that works from scratch
- No ambiguity on which frontend/service path is real
- Env template and startup script work from a clean checkout

### Phase 1: Developer MVP
Timeline: 3-5 weeks

Goals:
- Stable paid API flow end-to-end
- Stable evidence and dispute pipeline
- Stable console for operators
- SDK-based onboarding for one provider integration
- Webhook notifications for key events

Backend work:
- Harden all service APIs (input validation, error responses, idempotency)
- Formalize verdict package output with signatures
- Add service auth (API keys for service-to-service communication)
- Add rate limiting (per-agent and per-IP)
- Implement webhook delivery system
- Add health and readiness endpoints to all services
- Strict env validation on startup (fail fast on missing config)

Frontend work:
- Expose all 9 screens from section 13
- Add explorer links for all on-chain transactions
- Add error states and loading indicators
- Remove demo-only controls and confusion
- Add audit trail export (JSON, CSV)

Contract/protocol work:
- Freeze V1 ABI (no breaking changes after this point)
- Publish contract address and ABI as npm/PyPI packages
- Version evidence and verdict schemas (schemaVersion: "1.0.0")
- Document all contract events and state transitions

SDK work:
- Publish `verdict-protocol` Python package with provider and consumer modules
- Write provider onboarding guide with code examples
- Create sample integration (FastAPI app protected by Verdict)

CLI work:
- Implement `verdict init`, `verdict register`, `verdict service create`
- Implement `verdict test happy-path` and `verdict test dispute-path`
- Implement `verdict dev up/down/logs`

Exit criteria:
- External developer can onboard a sample API in under one hour
- Happy and dispute paths run reliably on testnet
- Webhook notifications fire for all key events
- Console shows complete transaction and dispute lifecycle

### Phase 2: Trust hardening
Timeline: 4-6 weeks

Goals:
- Reduce trust assumptions in judge and evidence systems
- Make all outputs auditable and verifiable
- Make operations safe and recoverable
- Upgrade storage for production workloads

Work:
- Signed verdict packages with stored reasoning metadata and judge signature
- Deterministic SLA checks separated from LLM narrative generation (two-pass evaluation)
- Provider co-signed response receipts (both parties sign)
- KMS/HSM-backed judge signing (AWS KMS or GCP Cloud HSM)
- PostgreSQL migration for all services
- Replay-safe event watchers with persistent cursors
- Idempotency keys for all write operations
- Structured logging with correlation IDs
- Prometheus metrics for all services
- Alerting rules for: judge failure, watcher lag, evidence anchor failure, dispute backlog
- V2 reputation model implementation (composite scores, decay, confidence levels)
- Runbook documentation for common operational scenarios
- Appeals system design finalization (contract changes, judge prompts)

Exit criteria:
- Every dispute produces a verifiable evidence bundle and signed ruling artifact
- Ops can recover from any service failure without manual DB surgery
- All services emit structured logs and Prometheus metrics
- Storage is production-grade (PostgreSQL with replication)

### Phase 3: Pilot launch
Timeline: 4-8 weeks

Goals:
- 2-5 pilot providers with real integrations
- Real usage on paid endpoints (not mock mode)
- Early dispute and reputation data from real transactions
- Production deployment with monitoring and alerting

Work:
- Provider onboarding flow (assisted integration for each pilot)
- SLA template library with pre-built templates for common use cases
- Production deployment on managed infrastructure
- Billing and usage reporting dashboard
- Support process: incident response, escalation path, SLA for platform issues
- Security audit of contract and critical services
- Load testing and performance benchmarking
- Incident runbooks for all critical failure modes
- Appeals system implementation (contract V2, appeal flow)

Exit criteria:
- At least one pilot uses real payment flow (not mock mode)
- At least one real dispute is processed end-to-end in the pilot environment
- Production monitoring alerts are configured and tested
- Security audit complete with no critical findings

### Phase 4: Protocol expansion
Timeline: ongoing after pilot

Work:
- Appeals system (if not completed in Phase 3)
- Judge quorum or multisig (2-of-3 judge panel)
- V2 reputation model (if not completed in Phase 2)
- Multi-agent transaction chains (linked transactions, dispute propagation)
- Streaming and WebSocket evidence capture
- MCP integration for agent framework discovery
- Cross-chain deployment (Base, Arbitrum, Optimism)
- Permissioned marketplace integrations
- Advanced sybil resistance (stake-weighted reputation, social graph analysis)
- Marketplace product built on top of platform
- Token economics exploration (if warranted by usage)

---

## 29. Engineering workstreams

### Workstream 1: Protocol and contract

Tasks:
- Freeze V1 ABI and publish compatibility matrix
- Rename `Escrow` references to `AgentCourt` in all code and docs
- Add event and state transition documentation (see section 7)
- Define verdict package schema with on-chain/off-chain boundaries
- Implement provider co-signed response receipts
- Design V2 ABI for appeals (`fileAppeal`, `appealDeadline`, `parentDispute`)
- Design V2 ABI for partial refunds (`submitRuling` with percentage split)
- Design V2 ABI for linked transactions (`parentTxId`)
- Publish contract ABI as npm package (`@verdict-protocol/abi`)
- Publish protocol schemas as npm/PyPI packages

### Workstream 2: Service reliability

Tasks:
- Health and readiness endpoints on all services (liveness + dependency checks)
- Strict env validation on startup (fail fast with clear error messages)
- Persistent cursors for event watchers (survive restarts without reprocessing or missing events)
- Replay-safe watchers (idempotent event processing, deduplication by event ID)
- Structured error responses (consistent error schema across all services)
- Request correlation IDs (trace a request across services)
- Graceful shutdown (finish in-flight work before exiting)
- CI pipeline: unit tests, protocol tests, linting, type checking
- CI pipeline: one automated end-to-end dry-run (mock payment mode)
- Integration tests: service-to-service communication, contract interaction

### Workstream 3: Console

Tasks:
- Choose canonical frontend path, rename to `console/`
- Implement all 9 screens from section 13
- Connect to all service APIs (runner, evidence, judge, reputation)
- Show audit artifacts cleanly (receipt chains, verdict packages, evidence bundles)
- Add operator actions: retry failed ruling, force auto-complete, export audit trail
- Add environment switcher (local / testnet / pilot / production)
- Add webhook configuration UI
- Mobile-responsive layout
- Dark mode (already partially implemented)

### Workstream 4: SDK and developer experience

Tasks:
- Python provider SDK with FastAPI middleware
- Python consumer SDK with automatic evidence capture
- Node.js provider SDK with Express middleware
- Node.js consumer SDK
- CLI tool (`verdict`) with init, register, service, test, dev commands
- Provider onboarding guide (step-by-step tutorial)
- Consumer integration guide
- API reference documentation (OpenAPI spec for each service)
- Sample integrations: FastAPI provider, Express provider, LangChain tool wrapper

### Workstream 5: Security and operations

Tasks:
- KMS-managed judge signing (AWS KMS integration)
- Secret rotation plan and implementation
- Environment separation: local, testnet, pilot, production (separate configs, separate contract deployments)
- Audit logging (who did what, when, from where)
- Rate limiting on all public endpoints
- Input sanitization review (especially evidence payloads going to LLM)
- Prompt injection hardening for judge service
- Security audit preparation (document trust model, attack surface)
- Incident response playbook
- Monitoring and alerting setup

---

## 30. Testing strategy

### Test levels

| Level | Scope | Tools | Frequency |
|-------|-------|-------|-----------|
| **Unit tests** | Individual functions (hashing, signing, scoring, schema validation) | pytest | Every commit (CI) |
| **Protocol tests** | Receipt chain validation, clause hashing, signature verification | pytest | Every commit (CI) |
| **Service tests** | API endpoint behavior (request/response, error cases, edge cases) | pytest + httpx (TestClient) | Every commit (CI) |
| **Integration tests** | Service-to-service communication (evidence → judge → reputation) | pytest + running services | Daily (CI) |
| **Contract tests** | Solidity contract behavior (Hardhat test suite) | Hardhat + ethers.js | Every contract change |
| **End-to-end tests** | Full flow: register → request → fulfill → confirm/dispute → ruling → reputation | pytest + all services + contract | Daily (CI), pre-release |
| **Load tests** | Throughput, latency under load | locust or k6 | Pre-release |
| **Chaos tests** | Service failures, network partitions, delayed responses | Custom scripts | Pre-release |

### Key test scenarios

**Happy path:**
1. Provider registers → registers service → consumer registers → consumer requests service → provider fulfills → consumer confirms → payment released → reputation updated

**Dispute path:**
2. Same as happy until fulfillment → consumer files dispute → judge evaluates → ruling submitted → stakes transferred → reputation updated

**Edge cases:**
3. Auto-complete after 1 hour timeout
4. Dispute with no defendant response
5. Dispute with low judge confidence (manual review)
6. Receipt chain with invalid hash (should be rejected)
7. Receipt chain with invalid signature (should be rejected)
8. Insufficient balance for dispute filing
9. Double dispute on same transaction (should be rejected)
10. Evidence anchoring with empty receipt list

### Mock mode for testing

The `X402_ALLOW_MOCK=1` flag enables testing without real blockchain payments. In mock mode:
- x402 payment verification is bypassed
- Contract interactions use dry-run mode (SQLite mock DB)
- Evidence anchoring returns mock tx hashes
- All other logic (receipt chains, SLA checks, LLM judge) runs normally

---

## 31. Observability and monitoring

### Structured logging

All services emit JSON-structured logs:

```json
{
  "timestamp": "2025-03-10T12:00:00Z",
  "level": "info",
  "service": "judge_service",
  "correlation_id": "req-abc-123",
  "event": "dispute.processed",
  "dispute_id": 7,
  "tier": 0,
  "confidence": 0.85,
  "winner": "plaintiff",
  "duration_ms": 2340,
  "message": "Dispute #7 processed: plaintiff wins (district, confidence 0.85)"
}
```

### Metrics (Prometheus)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `verdict_transactions_total` | Counter | `status`, `service_id` | Total transactions by status |
| `verdict_disputes_total` | Counter | `tier`, `outcome` | Total disputes by tier and outcome |
| `verdict_ruling_duration_seconds` | Histogram | `tier` | Time from dispute filed to ruling submitted |
| `verdict_evidence_anchor_duration_seconds` | Histogram | | Time to anchor evidence on-chain |
| `verdict_receipt_chain_length` | Histogram | | Number of receipts per agreement |
| `verdict_watcher_lag_blocks` | Gauge | `service` | How far behind the watcher is from chain head |
| `verdict_service_health` | Gauge | `service` | 1 = healthy, 0 = unhealthy |
| `verdict_llm_judge_tokens` | Counter | `tier`, `model` | LLM tokens consumed |
| `verdict_llm_judge_cost_usd` | Counter | `tier` | LLM judge cost in USD |
| `verdict_webhook_deliveries_total` | Counter | `event`, `status` | Webhook delivery attempts |
| `verdict_reputation_updates_total` | Counter | `type` | Reputation score updates |

### Alerting rules

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Judge service down | Health check fails for 2 minutes | Critical | Page on-call, disputes will queue |
| Watcher lag > 100 blocks | `verdict_watcher_lag_blocks > 100` | Warning | Investigate RPC issues |
| Ruling submission failure | `submitRuling` tx reverts | Critical | Manual investigation, possible key issue |
| Evidence anchor failure | Anchor tx reverts 3 times | Warning | Check RPC, gas, contract state |
| LLM judge error rate > 10% | Judge errors / total > 0.1 over 1 hour | Warning | Check Anthropic API status |
| Dispute backlog > 10 | Unprocessed disputes > 10 | Warning | Scale judge service or investigate bottleneck |
| Webhook delivery failure rate > 50% | Failed / total > 0.5 over 1 hour | Warning | Check recipient endpoints |

### Dashboards

**Operational dashboard:**
- Service health status (all 4 services + gateway)
- Transaction throughput (requests/min, completions/min)
- Dispute processing (filed/min, resolved/min, backlog size)
- Watcher lag for all event watchers
- Error rates by service

**Business dashboard:**
- Total transaction volume (USDC)
- Active providers and consumers
- Dispute rate (disputes / total transactions)
- Average resolution time
- Revenue (platform fees + judge fees)

**Judge dashboard:**
- Disputes processed by tier
- LLM token usage and cost
- Confidence distribution
- Manual review queue size
- Appeal rate (V2)

---

## 32. Deployment architecture

### Local development

```
Developer machine
├── Evidence service    (localhost:4001)
├── Provider API        (localhost:4000)
├── Judge service       (localhost:4002)
├── Reputation service  (localhost:4003)
├── Demo runner         (localhost:4005)
├── Console             (localhost:4173)
└── SQLite databases    (data/*.db)

External dependencies:
├── GOAT Testnet3 RPC   (https://rpc.testnet3.goat.network)
├── x402 Facilitator    (https://www.x402.org/facilitator)
└── Anthropic API       (https://api.anthropic.com)
```

### Production deployment (single-node)

```
VPS (72.62.82.57)
├── Docker Compose
│   ├── verdict-evidence    (port 4001)
│   ├── verdict-provider    (port 4000)  [reference only; providers run their own]
│   ├── verdict-judge       (port 4002)
│   ├── verdict-reputation  (port 4003)
│   ├── verdict-console     (port 4173, Nginx)
│   ├── verdict-gateway     (port 8080, Rust binary)
│   └── postgres            (port 5433)
├── Nginx reverse proxy     (port 443, TLS termination)
├── Prometheus              (port 9090)
├── Grafana                 (port 3000)
└── Redis                   (port 6379, for rate limiting and webhook queuing)
```

### Production deployment (managed/scaled)

```
Cloud provider (AWS/GCP)
├── Load balancer (ALB/Cloud Load Balancing)
│   ├── /evidence/*  → Evidence service (auto-scaled)
│   ├── /judge/*     → Judge service (auto-scaled)
│   ├── /reputation/* → Reputation service (auto-scaled)
│   └── /console/*   → Static files (CDN)
├── RDS PostgreSQL (primary + read replica)
├── ElastiCache Redis (rate limiting, webhook queuing)
├── KMS (judge signing key)
├── CloudWatch/Stackdriver (logs, metrics, alerting)
├── SQS/Pub/Sub (webhook delivery queue)
└── S3/GCS (verdict package archive, evidence backups)
```

### Docker Compose template

```yaml
version: '3.8'
services:
  evidence:
    build: ./apps/evidence_service
    ports: ["4001:4001"]
    environment:
      - DATABASE_URL=postgres://admin:pass@postgres:5432/verdict_evidence
      - GOAT_RPC_URL=${GOAT_RPC_URL}
      - ESCROW_CONTRACT_ADDRESS=${ESCROW_CONTRACT_ADDRESS}
    depends_on: [postgres]

  judge:
    build: ./apps/judge_service
    ports: ["4002:4002"]
    environment:
      - DATABASE_URL=postgres://admin:pass@postgres:5432/verdict_judge
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - JUDGE_PRIVATE_KEY=${JUDGE_PRIVATE_KEY}
      - EVIDENCE_SERVICE_URL=http://evidence:4001
    depends_on: [postgres, evidence]

  reputation:
    build: ./apps/reputation_service
    ports: ["4003:4003"]
    environment:
      - DATABASE_URL=postgres://admin:pass@postgres:5432/verdict_reputation
    depends_on: [postgres]

  console:
    build: ./console
    ports: ["4173:80"]

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_PASSWORD=pass
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

## 33. Incident response and runbooks

### Severity levels

| Level | Description | Response time | Examples |
|-------|-------------|---------------|----------|
| **P0** | System down, disputes cannot be processed | 15 minutes | Judge service crashed, contract interaction broken |
| **P1** | Degraded, some features broken | 1 hour | Evidence anchoring failing, webhook delivery broken |
| **P2** | Minor issue, workaround available | 4 hours | Console UI bug, slow reputation updates |
| **P3** | Cosmetic or non-urgent | Next business day | Documentation error, log formatting issue |

### Runbook: Judge service not processing disputes

```
Symptoms: Disputes filed on-chain but no verdicts appearing
Check: GET /health on judge service
If unhealthy:
  1. Check logs for errors (database, RPC, Anthropic API)
  2. Verify JUDGE_PRIVATE_KEY is set and valid
  3. Verify GOAT_RPC_URL is reachable
  4. Verify ANTHROPIC_API_KEY is valid
  5. Restart service
  6. Check watcher cursor (has it fallen behind?)
If healthy but not processing:
  1. Check watcher lag (how far behind chain head?)
  2. Check for disputes in "manual_review" status
  3. Check LLM judge errors in logs
  4. Verify contract address matches deployed contract
```

### Runbook: Evidence anchoring failure

```
Symptoms: POST /anchor returns error or tx reverts
Check:
  1. Is the RPC endpoint reachable?
  2. Does the signer have sufficient gas?
  3. Is the contract address correct?
  4. Are receipts valid (hash verification passes)?
Fix:
  1. Retry anchor (idempotent operation)
  2. If gas issue: top up signer wallet
  3. If RPC issue: switch to backup RPC
  4. If contract issue: verify deployment
```

### Runbook: Ruling submission reverts

```
Symptoms: submitRuling tx reverts on-chain
Check:
  1. Is dispute already resolved? (d.resolved == true)
  2. Is winner address valid? (must be plaintiff or defendant)
  3. Is msg.sender the judge? (onlyJudge modifier)
  4. Is the judge key correct?
Fix:
  1. If already resolved: skip, update local state
  2. If wrong winner: investigate judge logic
  3. If wrong signer: fix JUDGE_PRIVATE_KEY
  4. Log the incident for audit
```

---

## 34. Commercial packaging

### Offer 1: Managed gateway (self-serve)

**What**: Hosted reverse proxy that adds x402 payment, evidence capture, and dispute support to any API.

**How it works**: Provider signs up, points their API endpoint at the Verdict gateway, configures SLA terms and pricing. Gateway handles everything.

**Pricing model**:
- Free tier: 1,000 protected calls/month, 1 service, mock payment only
- Starter: $49/month — 50,000 calls, 5 services, testnet
- Growth: $199/month — 500,000 calls, unlimited services, mainnet
- Enterprise: custom pricing

**Revenue per customer**: $49-199/month + basis-point transaction fees

### Offer 2: Protocol-backed enterprise

**What**: Dedicated deployment with custom SLA terms, priority support, and configurable dispute policies.

**How it works**: Dedicated infrastructure, custom contract deployment (own judge, own fee structure), white-label console, SLA on the platform itself.

**Pricing model**: $2,000-10,000/month depending on volume and customization.

**Target customers**: Large API marketplaces, enterprise agent platforms, financial services requiring audit trails.

### Offer 3: Reputation and audit API

**What**: Public API for querying agent trust data, dispute history, and quality scores.

**How it works**: Third-party marketplaces and agent frameworks query the Verdict Reputation API to make routing decisions (e.g., "only call providers with 90%+ success rate").

**Pricing model**:
- Free tier: 10,000 queries/month
- Pro: $99/month — 1M queries
- Enterprise: custom

### Offer 4: Dispute-as-a-Service (DaaS)

**What**: Stand-alone arbitration for platforms that have their own payment and evidence systems but need dispute resolution.

**How it works**: Platform submits a dispute bundle (evidence, SLA terms, party addresses) to the Verdict Judge API. Verdict processes it and returns a signed verdict package. Platform executes the ruling in their own system.

**Pricing model**: Per-dispute fee ($0.50-5.00 depending on tier and complexity).

---

## 35. Success metrics

### Product metrics

| Metric | Definition | V1 target | Pilot target |
|--------|-----------|-----------|-------------|
| Protected endpoints | Services registered on-chain | 10 | 50 |
| Paid call volume | Transactions completed per week | 100 | 5,000 |
| Dispute rate | Disputes filed / total transactions | Track only | < 5% |
| Dispute resolution time | Time from DisputeFiled to RulingSubmitted | < 60 seconds | < 60 seconds |
| Evidence bundle validity | % of disputes with valid receipt chains | > 95% | > 99% |
| Verdict package verifiability | % of verdicts with valid signatures | 100% | 100% |
| SDK adoption | Providers using SDK vs raw API | Track only | > 50% |
| Onboarding time | Time for new provider to first protected call | < 1 hour | < 30 minutes |

### Business metrics

| Metric | Definition | Pilot target | 6-month target |
|--------|-----------|-------------|----------------|
| Activated providers | Providers with at least 1 active service | 5 | 25 |
| Weekly transacting consumers | Unique consumers with completed transactions | 20 | 200 |
| Pilot conversion rate | Pilot invites → active providers | > 40% | > 50% |
| Revenue per protected endpoint | Monthly revenue / active endpoints | Track only | $10+ |
| Monthly recurring revenue | Total subscription + fee revenue | $0 (free pilots) | $5,000 |
| Net revenue retention | Month-over-month revenue from existing customers | Track only | > 100% |

### Reliability metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| Service uptime | % time all services are healthy | > 99.5% |
| Watcher lag | Blocks behind chain head | < 10 blocks |
| Failed ruling submission rate | % of rulings that fail on-chain | < 1% |
| Evidence anchor failure rate | % of anchoring attempts that fail | < 1% |
| Webhook delivery success rate | % of webhooks delivered on first attempt | > 95% |
| Mean time to recovery (MTTR) | Time from incident detection to resolution | < 30 minutes |
| LLM judge availability | % of disputes where LLM judge responds successfully | > 99% |

---

## 36. Competitive landscape

### Direct competitors

| Competitor | Approach | Strength | Weakness | Verdict advantage |
|-----------|----------|----------|----------|------------------|
| **Kleros** | Decentralized court with PNK token staking and Schelling point jury | Large community, battle-tested mechanism design | Slow (days), expensive, requires human jurors, not designed for machine disputes | Speed (seconds vs days), no token needed, purpose-built for API disputes |
| **Aragon Court** | DAO dispute resolution | Integrated with Aragon DAO ecosystem | Limited to DAO governance disputes, human-centric | Broader scope (any API/agent transaction), automated judging |
| **UMA Optimistic Oracle** | Optimistic assertion with dispute escalation | Well-designed mechanism, broad oracle use | Focused on oracle/data disputes, not API quality | Purpose-built for service quality, evidence chain model |

### Indirect competitors

| Category | Examples | Why they are not direct threats |
|----------|---------|-------------------------------|
| API monitoring | Datadog, Postman | Observe but don't arbitrate |
| API marketplaces | RapidAPI, Replicate | Aggregate but don't escrow or dispute |
| Payment processors | Stripe, Coinbase Commerce | Process payments but don't capture evidence or arbitrate |
| Agent frameworks | LangChain, CrewAI | Orchestrate agents but have no payment/dispute layer |

### Positioning statement

"Kleros is a court for humans. Verdict Protocol is a court for machines."

Kleros handles disputes where humans submit evidence and human jurors deliberate. Verdict handles disputes where machines submit cryptographic evidence and AI judges rule in seconds. They serve fundamentally different markets.

---

## 37. Compliance and regulatory considerations

### Escrow and money transmission

Operating an escrow service may trigger money transmission licensing requirements in some jurisdictions. Key considerations:

| Jurisdiction | Concern | Mitigation |
|-------------|---------|-----------|
| **US (federal)** | FinCEN money transmitter registration | Non-custodial architecture: funds are held by the smart contract, not by Verdict Protocol the company. Evaluate with legal counsel. |
| **US (state)** | State-by-state money transmitter licenses | Same non-custodial argument. Some states exempt smart contract escrow. Legal review needed per target state. |
| **EU** | MiCA (Markets in Crypto-Assets) regulation | USDC is a regulated stablecoin under MiCA. Verdict facilitates transactions but does not issue or hold assets. |
| **Global** | KYC/AML requirements | V1 operates on testnet (no real value). Before mainnet launch, implement KYC for providers above a transaction threshold. |

### Data privacy

| Data type | Storage | Concern | Mitigation |
|-----------|---------|---------|-----------|
| Transaction data | On-chain (public) | Publicly visible | Only hashes stored on-chain, not payload content |
| Evidence payloads | Off-chain (evidence service) | May contain sensitive API data | Encryption at rest, access controls, retention policies |
| Agent addresses | On-chain (public) | Pseudonymous but linkable | Inherent to blockchain — document in privacy policy |
| LLM judge inputs | Sent to Anthropic API | Evidence content visible to LLM provider | Use Anthropic's data usage policy (no training on API inputs). Consider self-hosted models for sensitive disputes. |

### Intellectual property

| Concern | Status |
|---------|--------|
| Evidence payloads may contain proprietary API responses | Evidence service stores hashes, not raw payloads (for on-chain). Off-chain storage should have access controls. |
| LLM judge opinions may reference proprietary data | Judge opinions are between the parties and the judge. Not publicly disclosed unless parties choose to publish. |
| SLA templates may have licensing implications | Templates are created by Verdict Protocol and licensed for use. Custom templates belong to the provider. |

### Recommended legal steps before mainnet

1. Engage crypto-regulatory counsel for money transmission analysis
2. Draft Terms of Service for platform users (providers, consumers)
3. Draft Privacy Policy covering on-chain and off-chain data
4. Evaluate insurance options for escrow failures or judge errors
5. Establish a dispute about the dispute process (what if a party disputes the Verdict ruling in traditional courts?)

---

## 38. Versioning and backward compatibility

### Schema versioning

All protocol objects include `schemaVersion: "1.0.0"`:
- `ArbitrationClause`
- `EventReceipt`
- `VerdictPackage`

Version bump rules:
- **Patch** (1.0.x): backward-compatible additions (new optional fields)
- **Minor** (1.x.0): backward-compatible changes (new event types, new rule operators)
- **Major** (x.0.0): breaking changes (field removals, type changes, hash algorithm changes)

Services must handle receipts and clauses from any supported schema version. Minimum supported version: `1.0.0`.

### Contract versioning

The AgentCourt contract is immutable once deployed. Version changes require new deployments:

| Version | Contract | Status |
|---------|----------|--------|
| V1 | `0xFBf9b5293A1737AC53880d3160a64B49bA54801D` (GOAT Testnet3) | Current |
| V2 | TBD (appeals, partial refunds, linked transactions) | Design phase |

Migration between contract versions:
- Deploy new contract
- Migrate agent registrations (off-chain tooling)
- Update all service configurations
- Old contract remains readable for historical disputes
- No automatic state migration (new contract starts fresh)

Consider a proxy pattern (ERC-1967) for V2 to enable upgradability without redeployment.

### API versioning

Services should support API versioning via URL prefix:
- `GET /v1/verdicts` (current)
- `GET /v2/verdicts` (future, when response format changes)

V1 API will be supported for at least 6 months after V2 launch.

### SDK versioning

SDKs follow semantic versioning:
- `verdict-protocol 1.x.y` — compatible with schema 1.x and contract V1
- `verdict-protocol 2.x.y` — compatible with schema 2.x and contract V2

Breaking changes in the SDK require a major version bump and migration guide.

---

## 39. Immediate 30-day plan

### Week 1: Foundations

1. **Decide brand architecture**: Verdict Protocol = platform, Agent Court = arbitration module. Update README, all docs, console title.
2. **Declare canonical runtime**: `apps/*` + `packages/protocol/` is the source of truth. Move `server/`, `demo/`, `guardian/` to `_legacy/`.
3. **Choose canonical frontend**: Pick one (judge-frontend or verdict-frontend). Rename to `console/`. Archive the other.
4. **Clean environment story**: Update `.env.example` with all canonical values. Remove references to old contract addresses. One file, one source of truth.

### Week 2: Bootstrap and testing

5. **One-command local bootstrap**: `verdict dev up` or equivalent script that starts all 4 services, verifies health, and prints status.
6. **One-command testnet bootstrap**: Script to deploy contract, configure env, and run full demo.
7. **Add CI**: GitHub Actions workflow for unit tests + protocol tests + linting. Run on every push.
8. **Add one automated e2e test**: Full happy path + dispute path in mock mode, running in CI.

### Week 3: Documentation and SDK

9. **Freeze V1 ABI**: Document all contract functions, events, and state transitions. Publish ABI as package.
10. **Publish API docs**: OpenAPI specs for evidence service, judge service, reputation service.
11. **Build provider onboarding guide**: Step-by-step tutorial from zero to first protected endpoint.
12. **Start Python SDK**: `verdict-protocol` package with provider and consumer modules, published to PyPI.

### Week 4: Hardening and outreach

13. **Add signed verdict packages**: Judge service produces and stores signed verdict JSON with judge signature.
14. **Add webhook skeleton**: Implement webhook delivery for `dispute.ruling` events (minimum viable).
15. **Recruit 2 design partners**: Identify and reach out to 2 API providers for pilot feedback.

---

## 40. Decision log

### Product decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| Do not start by building a marketplace | Need supply-side traction first. Trust layer before discovery layer. | Pre-plan | Decided |
| Ship as B2B developer platform first | Concrete buyer (API providers), narrow scope, matches existing code | Pre-plan | Decided |
| USDC-denominated, no governance token for V1 | Avoid token complexity before product-market fit | Pre-plan | Decided |
| Verdict Protocol = platform, Agent Court = arbitration module | Clean naming that matches repo structure and product surfaces | Plan v1 | Decided |

### Technical decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| Keep Python monorepo + Rust gateway as separate codebases | Different deployment profiles, stable interfaces between them | Pre-plan | Decided |
| SQLite for V1, PostgreSQL for V2 | SQLite is zero-config for development. Migrate when production demands it. | Plan v1 | Decided |
| EIP-191 signatures for receipts | Standard, widely supported, easy to verify on-chain and off-chain | Pre-plan | Decided |
| Keccak-256 for all protocol hashing | EVM-native, consistent with on-chain verification | Pre-plan | Decided |
| x402 for payment gating | Emerging standard for HTTP-native payments, already integrated | Pre-plan | Decided |
| Deterministic SLA checks + LLM narrative (two-pass) | Machine decides, LLM explains. Prevents LLM hallucination from affecting outcomes. | Plan v2 | Planned |

### UX decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| One canonical console, retire the other frontend | Maintenance burden of two frontends is not justified | Pre-plan | Decided |
| Mock mode must be visually distinct from real mode | Prevent confusion between test and production flows | Plan v2 | Planned |

### Deferred decisions

| Decision | Context | Decide by |
|----------|---------|-----------|
| Which frontend to keep (judge-frontend vs verdict-frontend) | Need to assess feature parity gap | Phase 0 |
| Proxy pattern (ERC-1967) for contract upgradability | Tradeoff: upgradability vs immutability trust | Phase 2 |
| Self-hosted LLM for sensitive disputes | Tradeoff: cost vs data privacy for evidence content | Phase 3 |
| Token economics | Only if usage warrants governance/staking mechanics | Phase 4+ |
| Multi-chain deployment strategy | Which chains, in what order, with what bridge for identity/reputation | Phase 4 |
