# Foundry V3 Contracts

This workspace contains the split contract architecture for the next protocol iteration:

- `src/Vault.sol`: custody, deposits, bonds, and authorized fund movement
- `src/JudgeRegistry.sol`: judge registration, superior-chain hierarchy, bonds, slashing, and response windows
- `src/Court.sol`: contracts, disputes, evidence submission, appeals, completion flow, abandonment, and timeout escalation
- `src/EvidenceAnchor.sol`: on-chain anchor for agreement root hashes and IPFS evidence bundle hashes

## Why it exists

The legacy contract in `contracts/AgentCourt.sol` is still the runtime target for the current app stack.

This Foundry workspace is the newer protocol core. It separates:

- escrow and custody
- judge governance and hierarchy
- dispute lifecycle and appeals

That separation is the base for the hierarchical court model with up to 5 tiers of judges.

## Local usage

Install dependencies once:

```bash
cd foundry
forge install foundry-rs/forge-std OpenZeppelin/openzeppelin-contracts --no-commit
```

Run tests:

```bash
forge test
```

Run deployment script:

```bash
USDC_ADDRESS=0x... \
CHARITY_ADDRESS=0x... \
forge script script/Deploy.s.sol:Deploy --broadcast
```

Bootstrap a full local split stack:

```bash
cd ..
bash ./scripts/bootstrap_split_local.sh
```

## Current notes

- `Court.sol` now emits the actual contract ID in `Completed`.
- Judge timeout slashing now transfers the slashed amount to `charity` instead of leaving it stranded in vault accounting.
- `main` now has an initial protocol bridge for split mode:
  - `EscrowClient` can target `Court`, `Vault`, and `JudgeRegistry`
  - `EscrowClient` can also target `EvidenceAnchor` via `ESCROW_EVIDENCE_ANCHOR_ADDRESS`
  - split-mode vault deposits can auto-approve the underlying USDC before bonding
  - `EscrowClient.register_judge(...)` can pre-bond and register judges for the split registry
  - consumer flows can propose and accept Court contracts before filing disputes
  - judge service can resolve the assigned judge per dispute
- evidence service can pin canonical evidence bundles and anchor their hashes on-chain when `EvidenceAnchor` is deployed
- Full app cutover is not complete; the legacy monolithic contract remains the default runtime target.
