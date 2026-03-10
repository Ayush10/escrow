# V1 ABI Compatibility Matrix

This file freezes the current Verdict Protocol V1 contract/client interface.

Canonical ABI:
- `contracts/abi/AgentCourt.json`

Canonical live network manifest:
- `contracts/deployments/goat-testnet3.json`

## Required V1 calls

| Capability | Contract call | Used by | Notes |
| --- | --- | --- | --- |
| Agent registration | `register(uint256 depositAmount)` | provider and consumer onboarding | Required for identity/bonded participation |
| Service registration | `registerService(bytes32,uint256,uint256)` | providers | Terms hash, price, bond |
| Request service | `requestService(uint256,bytes32)` | consumer flow | Creates transaction |
| Fulfill transaction | `fulfillTransaction(uint256,bytes32)` | provider flow | Records response hash |
| Confirm transaction | `confirmTransaction(uint256)` | consumer flow | Releases payment |
| Auto-complete | `autoComplete(uint256)` | operator or timeout path | Releases payment after timeout |
| Commit evidence | `commitEvidence(bytes32,bytes32)` | evidence service | Current on-chain evidence root commit |
| File dispute | `fileDispute(uint256,uint256,bytes32)` | consumer flow | Current canonical dispute ABI |
| Respond dispute | `respondDispute(uint256,bytes32)` | defendant | Optional counter-evidence |
| Submit ruling | `submitRuling(uint256,address)` | judge service | Current canonical ruling ABI |
| Read dispute | `getDispute(uint256)` | judge/reputation/console | Canonical dispute read path |
| Read transaction | `getTransaction(uint256)` | judge/console | Canonical transaction read path |
| Read service | `getService(uint256)` | console | Canonical service read path |

## Dual-compat support retained in client

The protocol client still contains additive fallback support for older or target-style ABIs, but V1 execution assumes the methods below:

| Client helper | V1 expectation | Fallback still tolerated |
| --- | --- | --- |
| `deposit_pool()` | `deposit(uint256)` or `deposit()` | yes |
| `post_bond()` | `deposit(uint256)` or `deposit()` | yes |
| `commit_evidence_hash()` | `commitEvidence(bytes32,bytes32)` | `commitEvidenceHash(...)` if present |
| `file_dispute()` | `fileDispute(uint256,uint256,bytes32)` | legacy address-based dispute ABI |
| `submit_ruling()` | `submitRuling(uint256,address)` | bytes/string verdict payload ABI |

## Freeze rule

V1-compatible code in this repo must not assume any contract method outside the matrix above unless:
- the ABI freeze is explicitly revised, and
- `contracts/deployments/*.json` and this document are updated in the same change
