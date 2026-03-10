# Verdict Comprehensive Task Division

## 1. Purpose

This is the execution source of truth for productizing Verdict Protocol from the current repo baseline.

It translates `PRODUCT_PLAN.md` into:
- owned lanes
- concrete tasks
- dependencies
- acceptance criteria
- visible status

For the current two-person staffing overlay, see `docs/two_person_execution_plan.md`.

## 2. Current baseline

Already present in the repo:
- contract and ABI
- protocol package
- provider API
- evidence service
- judge service
- reputation service
- consumer demo flows
- demo runner
- canonical `console/` frontend
- archived React rewrite in `_legacy/verdict-frontend/`

This document tracks the next layer of work: consolidation, hardening, and division of work.

## 3. Lane ownership

| Lane | Primary scope | Key repo areas |
| --- | --- | --- |
| `protocol_contracts` | ABI, contract lifecycle, protocol schemas, deploy story | `contracts/`, `packages/protocol/` |
| `payments_evidence` | x402, provider integration, evidence capture, consumer flows | `apps/provider_api/`, `apps/evidence_service/`, `apps/consumer_agent/` |
| `judge_reputation` | judge pipeline, verdict packages, reputation model, CI for service flows | `apps/judge_service/`, `apps/reputation_service/` |
| `console_ops` | canonical console, demo runner, repo governance, release process | `console/`, `_legacy/judge-frontend/`, `_legacy/verdict-frontend/`, `apps/demo_runner/`, `.github/`, docs |

## 4. Module ownership map

- `contracts/` -> `protocol_contracts`
- `packages/protocol/` -> `protocol_contracts`
- `apps/provider_api/` -> `payments_evidence`
- `apps/evidence_service/` -> `payments_evidence`
- `apps/consumer_agent/` -> `payments_evidence`
- `apps/judge_service/` -> `judge_reputation`
- `apps/reputation_service/` -> `judge_reputation`
- `apps/demo_runner/` -> `console_ops`
- `console/` and archived frontend paths -> `console_ops`
- repo governance docs and templates -> `console_ops`

## 5. Status legend

- `Not started`
- `In progress`
- `Blocked`
- `Review`
- `Completed`

## 6. Delivery phases

### Phase 0

Consolidate the operating system:
- repo governance
- canonical frontend decision
- canonical contract/runtime story
- consistent branding

### Phase 1

Developer MVP hardening:
- stable happy/dispute flows
- explicit mock/live handling
- canonical console
- ABI freeze

### Phase 2

Trust hardening:
- signed verdict packages
- audit exports
- key-management abstraction
- stronger CI and runbooks

### Phase 3

Pilot readiness:
- onboarding kits
- release ritual
- operator tooling

## 7. Task matrix

### Epic E01: Governance and canonical paths

| Task ID | Owner | Module | Task | Depends on | Acceptance | Status | Completed by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FND-01` | `console_ops` | repo governance | Create repo-local task matrix, rules, completion tracker, changes log, lane folders, and templates. | none | Governance files exist and are internally consistent. | `Completed` | `codex` |
| `FND-02` | `console_ops` | `judge-frontend/`, `verdict-frontend/` | Choose the canonical console path. Decision: `judge-frontend` is canonical (complete, shipping). `verdict-frontend` archived to `_legacy/`. | `FND-01` | One frontend is declared canonical in docs and backlog. | `Completed` | `Engineer B` |
| `FND-03` | `console_ops` | chosen frontend path | Rename the canonical frontend to `console/` and archive the other path. `judge-frontend/` moved to `_legacy/judge-frontend/`, `verdict-frontend/` moved to `_legacy/verdict-frontend/`, and legacy paths (`server/`, `demo/`, `guardian/`) were archived under `_legacy/`. Scripts and docs now point to `console/`. | `FND-02` | Repo has one production frontend path and scripts/docs point to it. | `Completed` | `Engineer B` |
| `FND-04` | `console_ops` | README, docs, UI titles | Unify the brand split: Verdict Protocol as platform, Agent Court as arbitration module. README, console copy, dashboard payment defaults, and active logo assets now use Verdict Protocol naming. | `FND-01` | External surfaces use one consistent naming rule. | `Completed` | `Engineer B` |

### Epic E02: Protocol and contracts

| Task ID | Owner | Module | Task | Depends on | Acceptance | Status | Completed by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PRT-01` | `protocol_contracts` | `contracts/`, `packages/protocol/` | Freeze the V1 ABI and publish the compatibility matrix. | `FND-01` | One compatibility doc maps contract methods to client capabilities. | `Completed` | `codex` |
| `PRT-02` | `protocol_contracts` | deploy tooling and env docs | Publish the canonical deployment manifest for local and GOAT testnet3. | `PRT-01` | One deploy document lists chain, address, env vars, and verification steps. | `Completed` | `codex` |
| `PRT-03` | `protocol_contracts` | contract/protocol tests | Add smoke coverage for register -> request -> fulfill -> dispute -> rule lifecycle. | `PRT-01` | Lifecycle can be tested repeatably in local and CI contexts. | `Completed` | `codex` |
| `PRT-04` | `protocol_contracts` | schema docs | Publish verdict package and evidence schema version docs. | `PRT-01` | Schema docs exist and match current payloads. | `Completed` | `codex` |

### Epic E03: Payments and evidence

| Task ID | Owner | Module | Task | Depends on | Acceptance | Status | Completed by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PAY-01` | `payments_evidence` | provider/evidence/runner/console | Split mock vs live profiles and expose explicit mock markers. `mockMode` and `dryRun` fields ship from runner `/config`, the console proxy fallback preserves them, and the console surfaces a mock banner plus MOCK/LIVE environment chip. | `FND-01` | Mock mode is visually and programmatically obvious. | `Completed` | `Engineer B` |
| `PAY-02` | `payments_evidence` | provider integration | Package a provider onboarding kit with middleware, sample config, and quickstart. `docs/provider-quickstart.md`, `examples/provider.env.example`, and `examples/fastapi_provider.py` now show the real x402 middleware path, evidence hashing, and the same `/api/data` flow used by the demo stack. | `PAY-01` | An external provider can protect an endpoint in under one hour. | `Completed` | `Engineer B` |
| `PAY-03` | `payments_evidence` | consumer integration | Package the consumer SDK or CLI for paid call plus dispute flow. Created `docs/consumer-quickstart.md` (happy path + dispute path guides with programmatic usage) and `examples/consumer_demo.py` (self-contained consumer script with progress callbacks and mode selection). | `PAY-01` | An external consumer can execute happy and dispute flows from docs. | `Completed` | `Engineer B` |
| `PAY-04` | `payments_evidence` | evidence service | Add agreement/evidence bundle export and audit-download path. Added `GET /agreements/{agreement_id}/export` endpoint to evidence service returning complete JSON bundle with clause, receipts, anchor, receipt chain validation, integrity checks, and schema version. Console has export button in agreement explorer. | `PRT-04` | Evidence bundle can be downloaded without manual DB access. | `Completed` | `Engineer B` |
| `PAY-05` | `payments_evidence` | flow reliability | Harden idempotency and replay handling for anchor, payment, and dispute flows. Evidence service now treats duplicate logical receipts as idempotent, returns existing anchors for repeat anchor requests, rejects conflicting re-anchors, and the dry-run escrow client deduplicates repeated evidence commits and dispute submissions. Focused retry tests and a live dry-run dispute demo were run to verify the behavior. | `PAY-01` | Repeated requests do not duplicate or corrupt state. | `Completed` | `codex` |
| `OPS-02` | `payments_evidence` | docs/runbooks | Publish provider and operator runbooks for canonical flows. Created `docs/runbooks/provider-runbook.md` (daily ops, dispute response, troubleshooting) and `docs/runbooks/operator-runbook.md` (architecture, service management, common issues, DB management, monitoring, escalation). | `FND-01` | Two role-specific runbooks exist and point to canonical paths only. | `Completed` | `Engineer B` |

### Epic E04: Judge and reputation

| Task ID | Owner | Module | Task | Depends on | Acceptance | Status | Completed by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `JDG-01` | `judge_reputation` | judge service | Produce signed verdict packages for every resolved dispute. | `PRT-04` | Each resolved dispute has stored verdict JSON and signature. | `Completed` | `codex` |
| `JDG-02` | `judge_reputation` | judge service + console | Add a manual review queue for low-confidence or failed disputes. | `JDG-01` | Low-confidence cases stop auto-submit and surface in the console. | `Completed` | `codex` |
| `JDG-03` | `judge_reputation` | judge signing path | Add a KMS/HSM-ready abstraction for judge key management. | `JDG-01` | Signer backend is pluggable instead of raw env-key only. | `Completed` | `codex` |
| `REP-01` | `judge_reputation` | reputation service | Scaffold the V2 reputation model and migration plan. V2 model implemented with service/court/reliability dimensional scoring, confidence calculation, and event tracking (model_version "2.0.0-draft"). Migration plan published at `docs/judge_reputation/reputation_v2_migration.md` covering replay-from-event-log strategy, rollback path, PostgreSQL migration, and verification queries. | `JDG-01` | Service can store richer score fields without breaking current API. | `Completed` | `codex` |
| `OPS-01` | `judge_reputation` | CI/workflows | Add CI for unit tests, lint, and one dry-run end-to-end flow. | `FND-01` | Pull requests have an automated quality gate. | `Completed` | `codex` |

### Epic E05: Console and orchestration

| Task ID | Owner | Module | Task | Depends on | Acceptance | Status | Completed by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CON-01` | `console_ops` | canonical console + runner | Reach parity on runs, agreements, verdicts, and reputation. `console/` covers Control Panel, Agent Court, and Network Explorer, and the reputation table/detail view now matches the current reputation API shape. | `FND-02` | Canonical console covers all core flows without legacy fallback. | `Completed` | `Engineer B` |
| `CON-02` | `console_ops` | canonical console | Add audit views for evidence bundle, verdict package, and tx links. Verdict modal shows the signed package plus ruling/dispute tx links, and agreement explorer includes receipt-chain visualization with exportable evidence bundles. | `CON-01`, `PAY-04`, `JDG-01` | Operators can inspect dispute artifacts from the UI. | `Completed` | `Engineer B` |
| `CON-03` | `console_ops` | canonical console + runner | Add service/env status panel with contract address and mock/live state. The environment panel is populated from runner config, and the console proxy fallback still reports contract, explorer, service URLs, and MOCK/LIVE state when the runner is unavailable. | `FND-02`, `PAY-01` | Operators can identify exact environment state at a glance. | `Completed` | `Engineer B` |
| `CON-04` | `console_ops` | scripts/docs | Create a one-command demo path and operator smoke checklist. `scripts/demo.sh` now starts services plus demo-runner, creates a full run via the runner API, and was verified end-to-end in dry-run mode; `docs/smoke-checklist.md` reflects that canonical flow. | `CON-01` | New contributors can boot and verify the demo in under ten minutes. | `Completed` | `Engineer B` |

### Epic E06: Release and execution hygiene

| Task ID | Owner | Module | Task | Depends on | Acceptance | Status | Completed by |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `OPS-03` | `console_ops` | `.github/` | Add issue and PR templates for task-driven execution. | `FND-01` | Repo templates require task IDs, verification, docs updates, and deviations. | `Completed` | `codex` |
| `OPS-04` | `console_ops` | release docs | Add milestone review ritual and release checklist. Created `docs/release-checklist.md` with pre-release checks (code quality, functional verification, documentation, artifacts, security), phase exit criteria for all 4 phases, release process steps, and sign-off table. | `OPS-01` | Each phase exit has an explicit sign-off list. | `Completed` | `Engineer B` |

## 8. Near-term execution order

### Block 1: Stop the repo from drifting

- `FND-02`
- `FND-04`
- `PRT-01`
- `PAY-01`

### Block 2: Make the canonical path real

- `FND-03`
- `CON-01`
- `CON-03`
- `PRT-02`
- `PAY-02`
- `PAY-03`

### Block 3: Make trust artifacts exportable

- `PRT-04`
- `PAY-04`
- `JDG-01`
- `CON-02`

### Block 4: Make the repo release-ready

- `PAY-05`
- `JDG-02`
- `JDG-03`
- `REP-01`
- `OPS-01`
- `OPS-02`
- `CON-04`
- `OPS-04`

## 9. Update rule

When a task changes status:
1. update this file
2. update the relevant lane `task_list.md`
3. update `docs/completion.md`
4. log major sequencing or scope changes in `docs/changes.md`
