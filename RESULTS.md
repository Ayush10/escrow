# Agent Court — Demo Results

## Contract Deployed (v4 — USDC + ERC-8004 enforced)
- **Address**: `0xFBf9b5293A1737AC53880d3160a64B49bA54801D`
- **Network**: GOAT Testnet3 (Chain ID: 48816)
- **Explorer**: https://explorer.testnet3.goat.network/address/0xFBf9b5293A1737AC53880d3160a64B49bA54801D
- **USDC Token**: `0x29d1ee93e9ecf6e50f309f498e40a6b42d352fa1`
- **ERC-8004 ENFORCED**: requireIdentity=true — agents without on-chain identity cannot register

## Judge Wallet
- **Address**: `0x00289Dbbb86b64881CEA492D14178CF886b066Be`
- **Balance**: ~0.000016 BTC remaining

## Persistent Agent Wallets
- **Good Agent**: `0xC633f39CbE3E8bdF549789325a98004d86536472`
- **Bad Provider**: `0x9D6Cc5556aB60779193517da30E1Bb18aeEd3f80`

## Constructor Parameters
- Payment token: USDC (0x29d1ee93...)
- Judge fees: [$0.005, $0.01, $0.02] (district/appeals/supreme) — 1/10th for testing
- Production fees: [$0.05, $0.10, $0.20]
- Min deposit: 0.01 USDC
- Service fee rate: 1% (100 basis points)
- Identity registry: 0x556089008Fc0a60cD09390Eca93477ca254A5522
- Reputation registry: 0x52B2e79558ea853D58C2Ac5Ddf9a4387d942b4B4
- **Require identity: TRUE (enforced)**

## Demo Run 3 — FULL SUCCESS (all 12 steps)
1. Fund agents: 0.000005 BTC each ✅
2. ERC-8004 identity registration (both agents) ✅
3. AgentCourt registration + deposit ✅
4. Service registration (weather API) ✅
5. **Happy path**: request → fulfill → confirm → payment released ✅
6. **Dispute path**: request → bad data (999°F) → dispute → respond → judge ruling ✅
7. Tier escalation: Bad Provider now at appeals tier ✅

## AI Judge Test — All Three Tiers

### District Court (Haiku, $0.05)
> **Winner: Plaintiff**
>
> The transaction data clearly shows the provider returned physically impossible values: 999°F (exceeding any recorded Earth temperature by over 200°F), -50% humidity (humidity cannot be negative), and a nonsensical condition 'Raining fire'. The SLA explicitly requires 'accurate data', which in the context of weather services means factually correct meteorological information that could plausibly occur in the real world. The provider's argument that 'accurate data' merely means whatever their sensors produced is unreasonable—no legitimate weather sensor would return such impossible values, and if it did, the provider's obligation under the SLA would be to validate the data for accuracy before delivery or flag it as erroneous. The response constitutes either fabricated data or a complete system failure. Either way, the service was not delivered as agreed. The plaintiff is entitled to relief.

### Appeals Court (Sonnet, $0.10)
> **Winner: Plaintiff**
>
> The transaction data clearly shows the provider returned a temperature of 999°F, a condition of 'Raining fire', and a humidity of -50% for San Francisco. These values are physically impossible: 999°F would be incompatible with Earth's atmosphere and any known weather phenomenon, humidity cannot be negative, and 'Raining fire' is not a meteorological condition. The SLA explicitly requires 'accurate data,' which must be interpreted according to its ordinary meaning — data that reflects real-world conditions. The defendant's argument that 'accurate' merely means 'from our sensors' is a self-serving redefinition that no reasonable interpretation supports. A sensor reading of 999°F with -50% humidity is either a catastrophic sensor malfunction or fabricated data, neither of which satisfies an accuracy obligation. The provider failed to deliver the agreed service, and the plaintiff is entitled to prevail.

### Supreme Court (Opus, $0.20)
> **Winner: Plaintiff**
>
> The transaction data clearly shows the provider returned a temperature of 999°F, a condition of 'Raining fire', and a humidity of -50% for San Francisco. These values are physically impossible: 999°F far exceeds any temperature ever recorded on Earth, humidity cannot be negative, and 'Raining fire' is not a real meteorological condition. The SLA explicitly requires 'accurate data,' which by any reasonable interpretation means data that reflects actual real-world weather conditions. The defendant's argument that 'accurate' merely means whatever their sensors output is untenable — if a provider could redefine accuracy to mean any arbitrary output from their system, the SLA requirement would be meaningless. The provider clearly failed to deliver accurate weather data as required by the service agreement.

## Transaction Costs (GOAT Testnet3)
| Operation | Gas Used | Cost (BTC) | Cost (USD) |
|---|---|---|---|
| Deploy contract | 2,898,999 | 0.000000377 | $0.036 |
| Register agent | 71,529 | 0.0000000093 | $0.0009 |
| Register service | 126,927-144,027 | 0.0000000165 | $0.0016 |
| Request service | 179,794-248,194 | 0.0000000280 | $0.0027 |
| Full happy path | ~500,000 | 0.0000000650 | $0.006 |

## Integration Status
- ✅ Contract deployed on-chain with ERC-8004 **enforced** (requireIdentity=true)
- ✅ Agents without ERC-8004 identity are rejected (verified — tx reverts)
- ✅ Persistent wallets — reputation carries over across runs
- ✅ AI judge tested across all 3 tiers (Haiku/Sonnet/Opus via Anthropic API)
- ✅ Full lifecycle: ERC-8004 → register → service → request → fulfill → confirm/dispute → ruling
- ✅ Tier escalation: dispute losses increase judge fees ($0.05 → $0.10 → $0.20)
- ✅ Judge wired through server — demo calls /dispute/argue, /dispute/respond, /rule endpoints
- ✅ USDC payments — all transfers visible on GOAT dashboard
- ✅ Withdraw works — agents pull real USDC from contract
- ✅ ERC-8004 reputation via giveFeedback() (best-effort, try/catch in contract)

## What's Built
1. **AgentCourt.sol** — singleton clearinghouse contract (deployed, live)
2. **server/judge.py** — AI judge with tiered court system (Haiku/Sonnet/Opus)
3. **server/app.py** — FastAPI backend bridging off-chain judge to on-chain
4. **guardian/guardian.py** — reputation-gated API proxy
5. **demo/weather_api.py** — fake weather API for testing
6. **demo/demo.py** — full lifecycle demo script
7. **demo/test_judge.py** — judge test across all three tiers
8. **judge-frontend/index.html** — web UI for judge panel

## Repo
- https://github.com/Ayush10/escrow
- Branch: python-backend
