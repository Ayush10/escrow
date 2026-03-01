# Known Issues & Limitations

What actually works end-to-end, for real:
- Two agents deposit real USDC, transact, file disputes, submit arguments through the public API, AI judge generates an opinion, ruling gets submitted on-chain. This is real and it worked (dispute #2, tx 0xcb6cb644).

What doesn't work / is fake / would break in real life:

1. **There's no way for the defendant to commit evidence on-chain.** The contract's `commitEvidence` takes `(bytes32, bytes32)` — plaintiff and defendant hashes together. But there's no flow where the defendant separately commits their hash before the dispute is filed. Every dispute so far has the defendant's evidence hash as `0x000...000`. The judge notices this and holds it against the defendant every time.

2. **The tiered escalation is broken.** The contract uses `disputeLossCount` per address and caps tier at `min(losses, 2)`. But it's per-address, not per-dispute-chain. There's no concept of "appealing dispute #2" — you just file a NEW dispute about a NEW transaction. The "appeals" and "supreme" tiers are just more expensive judges for repeat losers, not actual appeals of prior rulings.

3. **The AI judge has no access to the actual evidence.** It gets the hashes but can't verify them against anything. The arguments are just text that anyone can submit — no cryptographic link between what the agents claim happened and what's on-chain. The evidence service exists in the monorepo but isn't deployed or connected.

4. **Anyone can submit arguments for either side.** There's zero auth on `/api/disputes/{id}/argue` and `/api/disputes/{id}/respond`. No signature verification, no address check. Anyone could submit the defendant's argument as the plaintiff.

5. **The judge fee isn't actually paid to the judge.** The contract deducts it from the loser's balance but it goes into the contract, not to the judge's wallet. There's no `withdrawJudgeFee()`.

6. **The watcher auto-processed dispute #1 before arguments arrived** and submitted the wrong ruling on-chain. The 60s grace period is a band-aid — in real life you'd need the contract to enforce an argument submission window.

7. **No service discovery.** An agent has no way to find services to use. The contract stores `termsHash` as a bytes32 but there's no way to read what the terms actually are without the off-chain evidence service.

8. **Single judge, single key.** One private key controls all rulings. If it's compromised, every dispute can be manipulated. There's no multisig, no judge rotation, no randomized selection.

9. **No appeal mechanism in the contract.** There's no `fileAppeal(disputeId)`. The "tiered court" is just repeat-offender escalation, not real appellate review.

10. **The USDC amounts are tiny test values.** $0.005 per service, $0.001 stakes. The gas to file a dispute costs more than the dispute is worth.

**Bottom line:** It's a working prototype that demonstrates the concept. The on-chain parts are real. The AI judge is real. But the evidence integrity layer — the thing that would make this trustworthy — is basically missing. An agent could lie about anything in its arguments and the judge has no way to verify.
