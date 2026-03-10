# Two-Person Execution Plan

This document maps the lane-based operating system onto a two-developer team.

Replace `Engineer A` and `Engineer B` with real names when you are ready.

## Current status

As of `2026-03-10`, Engineer A's independent execution block is complete:

- `PRT-01`
- `PRT-02`
- `PRT-03`
- `PRT-04`
- `JDG-01`
- `JDG-02`
- `JDG-03`
- `REP-01`
- `OPS-01`

Engineer B's frontend, onboarding, operator-flow, and release-usability block is also complete:

- `FND-02`
- `FND-03`
- `FND-04`
- `PAY-01`
- `PAY-02`
- `PAY-03`
- `PAY-04`
- `OPS-02`
- `CON-01`
- `CON-02`
- `CON-03`
- `CON-04`
- `OPS-04`

Engineer A has now also completed the shared follow-on task:

- `PAY-05`

The current tracked execution matrix is fully complete.

## Team model

### Engineer A

Role:
- platform/trust/integration lead

Primary ownership:
- protocol and contract correctness
- judge and reputation systems
- service-to-service integration
- CI and release gating

Default review role:
- reviews backend-facing changes from Engineer B that affect APIs, schemas, or runtime behavior

### Engineer B

Role:
- product/dx/frontend lead

Primary ownership:
- payments and evidence UX
- provider and consumer onboarding
- canonical console
- demo runner and operator flow
- docs and release usability

Default review role:
- reviews Engineer A changes that affect operator UX, frontend data shape, or developer onboarding

## Lane split

| Lane | Primary person | Support person |
| --- | --- | --- |
| `protocol_contracts` | `Engineer A` | `Engineer B` |
| `payments_evidence` | `Engineer B` | `Engineer A` |
| `judge_reputation` | `Engineer A` | `Engineer B` |
| `console_ops` | `Engineer B` | `Engineer A` |

## Global responsibility split

### Engineer A owns

- API and schema contract stability
- deploy and environment correctness
- integration tests and CI gates
- trust and audit artifacts
- release-blocking backend issues

### Engineer B owns

- frontend and operator workflow
- demo ergonomics
- provider and consumer onboarding
- mock/live UX clarity
- documentation and release usability

## Task assignment

| Task ID | Primary | Support | Why |
| --- | --- | --- | --- |
| `FND-02` | `Engineer B` | `Engineer A` | Canonical console decision is primarily product and frontend scope, but it affects service integration. |
| `FND-03` | `Engineer B` | `Engineer A` | Repo cleanup and frontend consolidation belong with the product/dx owner. |
| `FND-04` | `Engineer B` | `Engineer A` | Branding touches README, console copy, and external-facing surfaces first. |
| `PRT-01` | `Engineer A` | `Engineer B` | ABI freeze is the foundation for all downstream API and console work. |
| `PRT-02` | `Engineer A` | `Engineer B` | Canonical deployment manifest is platform ownership. |
| `PRT-03` | `Engineer A` | `Engineer B` | Lifecycle smoke coverage is an integration-quality task anchored in protocol correctness. |
| `PRT-04` | `Engineer A` | `Engineer B` | Schema publication must be driven by the platform owner, with frontend/dx validation. |
| `PAY-01` | `Engineer B` | `Engineer A` | Mock/live clarity is primarily a developer and operator UX problem. |
| `PAY-02` | `Engineer B` | `Engineer A` | Provider onboarding kit is product packaging around existing backend primitives. |
| `PAY-03` | `Engineer B` | `Engineer A` | Consumer SDK/CLI should optimize adoption, while A validates protocol correctness. |
| `PAY-04` | `Engineer B` | `Engineer A` | Evidence export is user-facing, but schema and artifact correctness need A review. |
| `PAY-05` | `Engineer A` | `Engineer B` | Idempotency and replay handling are cross-service integrity concerns. |
| `OPS-02` | `Engineer B` | `Engineer A` | Runbooks are operator-facing and should be written from the usability side. |
| `JDG-01` | `Engineer A` | `Engineer B` | Signed verdict packages are core trust infrastructure. |
| `JDG-02` | `Engineer A` | `Engineer B` | Manual review queue is judge-domain logic first, then surfaced in the console. |
| `JDG-03` | `Engineer A` | `Engineer B` | Judge signer abstraction is platform security work. |
| `REP-01` | `Engineer A` | `Engineer B` | Reputation model evolution belongs with trust and scoring logic. |
| `OPS-01` | `Engineer A` | `Engineer B` | CI and release gates should be owned by the integration lead. |
| `CON-01` | `Engineer B` | `Engineer A` | Canonical console parity is primarily frontend and operator-flow work. |
| `CON-02` | `Engineer B` | `Engineer A` | Audit views are UI work built on artifacts that A owns. |
| `CON-03` | `Engineer B` | `Engineer A` | Service/env panel is part of the operator UX, with A validating correctness. |
| `CON-04` | `Engineer B` | `Engineer A` | One-command demo and smoke checklist are DX and onboarding work. |
| `OPS-04` | `Engineer B` | `Engineer A` | Milestone review and release checklist are process-facing artifacts for shipping. |

## Workload summary

### Engineer A

Primary tasks:
- `PRT-01`
- `PRT-02`
- `PRT-03`
- `PRT-04`
- `PAY-05`
- `JDG-01`
- `JDG-02`
- `JDG-03`
- `REP-01`
- `OPS-01`

Theme:
- make the backend trustworthy, stable, testable, and ready to ship

### Engineer B

Primary tasks:
- `FND-02`
- `FND-03`
- `FND-04`
- `PAY-01`
- `PAY-02`
- `PAY-03`
- `PAY-04`
- `OPS-02`
- `CON-01`
- `CON-02`
- `CON-03`
- `CON-04`
- `OPS-04`

Theme:
- make the product understandable, usable, and operable by someone other than the current builders

## Frontend and integration coverage

To avoid the usual failure mode where frontend or integration work is treated as "supporting" and never owned:

### Frontend

Engineer B is explicitly responsible for:
- `FND-02`
- `FND-03`
- `CON-01`
- `CON-02`
- `CON-03`
- `CON-04`

That means one person fully owns:
- canonical frontend decision
- parity work
- audit views
- service visibility
- demo usability

### Integration

Engineer A is explicitly responsible for:
- `PRT-03`
- `PAY-05`
- `OPS-01`

That means one person fully owns:
- lifecycle smoke coverage
- cross-service integrity
- CI quality gate

### Shared integration points

These are mandatory pairing checkpoints, not optional:

1. After `FND-02` and `PRT-01`
   - confirm frontend choice and API/ABI freeze are compatible
2. After `PAY-01`, `CON-03`, and `PRT-02`
   - confirm environment status, contract identity, and mock/live markers are coherent
3. After `PAY-04`, `JDG-01`, and `CON-02`
   - confirm evidence export, verdict package format, and audit UI all match
4. After `OPS-01` and `CON-04`
   - run a release rehearsal from clean setup

## Suggested execution sequence

### Wave 1: Remove ambiguity

Engineer B:
- `FND-02`
- `FND-04`
- `PAY-01`

Engineer A:
- `PRT-01`
- `PRT-02`

Joint checkpoint:
- finalize canonical console + ABI + environment story

### Wave 2: Make the canonical path usable

Engineer B:
- `FND-03`
- `CON-01`
- `CON-03`
- `PAY-02`

Engineer A:
- `PRT-04`
- `PAY-05`
- `JDG-01`

Joint checkpoint:
- confirm the console can show canonical data from canonical services and artifacts

### Wave 3: Make it auditable and testable

Engineer B:
- `PAY-03`
- `PAY-04`
- `CON-02`

Engineer A:
- `PRT-03`
- `JDG-02`
- `OPS-01`

Joint checkpoint:
- run end-to-end from fresh environment and validate exported evidence plus verdict artifacts

### Wave 4: Make it pilot-ready

Engineer B:
- `OPS-02`
- `CON-04`
- `OPS-04`

Engineer A:
- `JDG-03`
- `REP-01`

Joint checkpoint:
- release rehearsal and pilot readiness review

## PR and review rule for a two-person team

If Engineer A is primary:
- Engineer B reviews anything user-visible or DX-visible

If Engineer B is primary:
- Engineer A reviews anything that changes APIs, schemas, persistence, or flow guarantees

No task is considered done until:
- the primary owner updates the task matrix
- the support owner reviews or signs off
- docs are updated

## Recommended weekly operating rhythm

### Monday

- choose active task IDs for each person
- identify any blocked dependencies

### Midweek

- update lane notes
- record deviations in `docs/changes.md`
- do one integration sync

### Friday

- update `docs/completion.md`
- close completed task rows
- decide the next wave

## If you later add a third person

The clean split is:
- keep Engineer A on platform/trust
- keep Engineer B on product/console
- add Engineer C for payments/evidence/onboarding

Until then, the current two-person split is balanced enough to keep momentum without hiding frontend or integration work.
