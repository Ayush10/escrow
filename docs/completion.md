# Completion Tracker

Last updated: 2026-03-10

## Current backlog snapshot

- Total active productization tasks: `25`
- Completed: `25`
- In progress: `0`
- Blocked: `0`
- Remaining: `0`

## Completed now

- `FND-01` Repo-local project management operating system created.
- `FND-02` Canonical console decision made and recorded.
- `FND-03` Canonical frontend consolidated under `console/` and legacy frontend paths archived.
- `FND-04` Branding unified across active docs, console surfaces, payment defaults, and assets.
- `PRT-01` V1 ABI freeze and compatibility matrix published.
- `PRT-02` Canonical deployment manifest published for local and GOAT testnet3.
- `PRT-03` Dry-run lifecycle smoke coverage added to protocol tests and CI.
- `PRT-04` Verdict package and evidence schema version docs published.
- `PAY-01` Mock/live state is explicit in runner config, console UI, and fallback config.
- `PAY-02` Provider onboarding kit shipped with working middleware example and sample env file.
- `PAY-03` Consumer quickstart and demo flow packaged.
- `PAY-04` Evidence bundle export endpoint and console download path shipped.
- `PAY-05` Idempotency and replay handling added for duplicate receipts, repeat anchors, and repeated dry-run dispute submissions.
- `OPS-02` Provider and operator runbooks published.
- `JDG-01` Signed verdict packages added to the judge pipeline.
- `JDG-02` Manual review queue and API endpoints added for low-confidence disputes.
- `JDG-03` Judge signer abstraction added with pluggable backend support.
- `REP-01` Reputation V2 profile scaffold added without breaking the current API.
- `OPS-01` CI workflow added for lint, unit tests, and one dry-run end-to-end flow.
- `CON-01` Canonical console parity reached across runs, agreements, verdicts, and reputation.
- `CON-02` Audit views added for verdict packages, evidence bundles, receipt chains, and tx links.
- `CON-03` Environment panel and service status surfaced in the canonical console.
- `CON-04` One-command demo path and smoke checklist verified end to end.
- `OPS-03` Issue and PR templates added for task-driven execution.
- `OPS-04` Release checklist and milestone review ritual published.

## By lane

| Lane | Total | Completed | Remaining |
| --- | ---: | ---: | ---: |
| `protocol_contracts` | 4 | 4 | 0 |
| `payments_evidence` | 6 | 6 | 0 |
| `judge_reputation` | 5 | 5 | 0 |
| `console_ops` | 10 | 10 | 0 |

## Current focus order

- No remaining tracked productization tasks in the current matrix.

## Notes

- This tracker starts from the current repo baseline, not from the repo's original inception.
- Engineer A's independent execution block is complete.
- Engineer B's frontend, onboarding, operator-flow, and release-usability block is complete.
- `PAY-05` closed the final gap by making retries safe for receipt, anchor, and dispute paths.
