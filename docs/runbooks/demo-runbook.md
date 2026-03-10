# Demo Runbook

Use this branch as the stable demo baseline. The goal is to get from a cold start to a working console in one command, then run the happy and dispute flows from the UI.

## Start the stack

```bash
pnpm demo:console
```

This starts:
- evidence service on `:4001`
- provider API on `:4000`
- judge service on `:4002`
- reputation service on `:4003`
- demo runner on `:4004`
- static console on `:4173`

In mock mode the bootstrap also clears local demo SQLite state so stale disputes and receipts do not leak into the presentation.

Open:
- `http://127.0.0.1:4173`

## Demo order

1. Connect the console to `http://127.0.0.1:4004`
2. Call out the `MOCK` banner and say payments / escrow writes are simulated for repeatable demos
3. Run `happy`
4. Show:
   - agreement creation
   - request / response / payment receipts
   - anchored root
   - reputation changes
5. Run `dispute`
6. Show:
   - bad provider response
   - SLA-check receipt
   - anchored evidence bundle
   - dispute filing artifact and explorer link
   - signed verdict with opinion and submit tx hash
   - reputation changes after the ruling

## Fallback API triggers

If the UI is slow, trigger runs directly:

```bash
curl -X POST http://127.0.0.1:4004/runs \
  -H 'content-type: application/json' \
  -d '{"mode":"happy","startServices":false,"keepServices":true,"autoRun":true,"agreementWindowSec":10}'

curl -X POST http://127.0.0.1:4004/runs \
  -H 'content-type: application/json' \
  -d '{"mode":"dispute","startServices":false,"keepServices":true,"autoRun":true,"agreementWindowSec":10}'
```

## Presenter notes

- Prefer mock mode for reliability.
- The strongest proof points today are the receipt chain, anchored evidence root, signed verdict package, and reputation surfaces.
- In the current mock demo baseline, the dispute flow should finish with a `submitted` verdict and visible reputation updates.
