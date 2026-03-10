# Schema Versions

Verdict Protocol V1 uses schema version `1.0.0` for the three core payload families below.

## Arbitration clause

Schema file:
- `packages/protocol/src/verdict_protocol/schemas/arbitration_clause.schema.json`

Purpose:
- defines the commercial and dispute terms for an agreement

Key invariants:
- `clauseHash` is the canonical hash of the payload without the `clauseHash` field
- `disputeWindowSec` and `evidenceWindowSec` are part of the signed clause terms

## Event receipt

Schema file:
- `packages/protocol/src/verdict_protocol/schemas/event_receipt.schema.json`

Purpose:
- defines the evidence chain for requests, responses, payments, SLA checks, and disputes

Key invariants:
- `receiptHash` is the canonical hash of the payload without `receiptHash` and `signature`
- `signature` is EIP-191 over `receiptHash`
- `prevHash` links the receipt chain

## Verdict package

Schema file:
- `packages/protocol/src/verdict_protocol/schemas/verdict_package.schema.json`

Purpose:
- defines the signed adjudication artifact produced by the judge service

Key invariants:
- `verdictHash` is the canonical hash of the package without `verdictHash` and `judgeSignature`
- `judgeSignature` is EIP-191 over `verdictHash`
- `judgeSignerBackend` records which signer implementation produced the package
- `disputeTxHash` is optional source-trace metadata for the original dispute filing transaction
- `processedAtMs` is the package creation timestamp, not UI state

## Versioning rule

Patch-compatible changes:
- non-breaking docs updates
- additive implementation details outside the schema payloads

Minor version bump:
- additive optional fields that old consumers can ignore

Major version bump:
- removing fields
- changing hash inputs
- changing signature semantics
- changing field types or meanings
