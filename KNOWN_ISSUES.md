# Known Issues & Limitations

This file tracks known limitations observed in live and dry-run demos.
It is intentionally candid so contributors can prioritize real fixes.

What currently works end-to-end:
- Python services run with one-click orchestration (`demo_runner`) and frontend timeline.
- Happy and dispute flows execute with evidence receipts, anchoring, judge processing, and reputation updates.
- x402 flow is wired for Base Sepolia, with local mock fallback for development.
- GOAT dashboard payment helper can publish testnet transfer activity.

What remains limited or non-production:

1. **Evidence trust boundary is still mixed.**
   On-chain evidence is hash-based, but most semantic dispute facts still come from off-chain payloads.
   Full trustless evidence reveal/verification remains incomplete.

2. **Judge authority is single-key.**
   Rulings are submitted by a single judge signer. There is no multisig or quorum path.

3. **Dispute lifecycle depends on off-chain timing.**
   Service watcher timing and polling can affect when a dispute is processed.
   This is acceptable for hackathon flows but needs stricter on-chain windows for production.

4. **Demo contract address drift can cause confusion.**
   Different branches/docs referenced different addresses.
   Runtime is now env-driven, but docs still need consolidation to one canonical deployed contract.

5. **x402 in local mode can be mocked.**
   `X402_ALLOW_MOCK=1` is useful for repeatable demos but is not a real payment settlement path.

6. **Backend health is required for frontend autoplay.**
   Frontend controls depend on runner/service availability.
   The UI now handles failures better, but missing services still block full execution by design.

7. **Reputation semantics are simple.**
   Current scoring is deterministic and hackathon-focused; anti-sybil and historical weighting are not implemented.

8. **No production-grade key management in repo scripts.**
   Env-based secret loading exists, but HSM/KMS/rotation workflows are not implemented here.

9. **Legacy branches contain experimental scripts.**
   Some legacy scripts were useful for rapid experiments but are not the canonical runtime path.
   `apps/*` services and `judge-frontend/index.html` are the authoritative flow.

10. **Test coverage is focused, not exhaustive.**
   Core protocol tests pass, but full multi-service/network integration coverage still needs expansion.
