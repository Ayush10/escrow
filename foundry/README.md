# Foundry V3 Contracts

This workspace contains the split contract architecture for the next protocol iteration:

- `src/Vault.sol`: custody, deposits, bonds, and authorized fund movement
- `src/JudgeRegistry.sol`: judge registration, superior-chain hierarchy, bonds, slashing, and response windows
- `src/Court.sol`: contracts, disputes, evidence submission, appeals, completion flow, abandonment, and timeout escalation

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

## Current notes

- `Court.sol` now emits the actual contract ID in `Completed`.
- Judge timeout slashing now transfers the slashed amount to `charity` instead of leaving it stranded in vault accounting.
- `main` now has an initial protocol bridge for split mode:
  - `EscrowClient` can target `Court`, `Vault`, and `JudgeRegistry`
  - consumer flows can propose and accept Court contracts before filing disputes
  - judge service can resolve the assigned judge per dispute
- Evidence roots are still stored off-chain first in split mode because there is no dedicated anchor contract yet.
- Full app cutover is not complete; the legacy monolithic contract remains the default runtime target.
