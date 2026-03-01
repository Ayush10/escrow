# Verdict Protocol Frontend Plan (Implemented)

## 1) Page structure
- Dashboard home card row:
  - Service health cards (runner, evidence, provider, judge, reputation, explorer links)
  - Run controls (happy/dispute/full + refresh + window input)
  - Optional dashboard payment action controls
- Demo runner panel:
  - Auto-play buttons + current run marker
  - SSE-backed live step timeline
  - Run event log panel
- Agreement explorer:
  - Agreement input and "Load" action
  - receipt count, chain validity, anchor tx/reasoning summary
- Verdicts:
  - Verdict table from judge service
  - open details panel with payload dump
- Reputation:
  - Leaderboard table from reputation service
  - actor history popup

## 2) APIs consumed
- `demo-runner`:
  - `GET /health`
  - `GET /config`
  - `POST /runs`
  - `GET /runs`
  - `GET /runs/{run_id}`
  - `POST /runs/{run_id}/start`
  - `POST /runs/{run_id}/cancel`
  - `GET /runs/{run_id}/stream`
  - `POST /dashboard-payment`
- `evidence_service`:
  - `GET /agreements/{agreement_id}`
- `judge_service`:
  - `GET /verdicts`
  - `GET /verdicts/{dispute_id}`
- `reputation_service`:
  - `GET /reputation`
  - `GET /reputation/{actor_id}`

## 3) Demo flow
1. User clicks mode button (`happy`, `dispute`, `full`).
2. Frontend calls `POST /runs`.
3. UI opens SSE stream and renders events + steps as they arrive.
4. On updates it fetches run state and agreement/verdict/reputation summaries.
5. Final cards show tx links, receipt IDs, root anchoring state and actor reputation.

## 4) Difference vs previous static screen
- Previous UI was chain-centric and read-only.
- New UI is orchestration-centric with live controls and streaming artifacts.
- Includes optional GOAT payment action hook with header "Ayush + Karan and Verdict Protocol".
