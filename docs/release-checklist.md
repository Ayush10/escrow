# Release Checklist

Use this checklist before each phase exit or release milestone.

## Pre-release checks

### Code quality

- [ ] All unit tests pass: `uv run pytest`
- [ ] No lint errors: `uv run ruff check .`
- [ ] No type errors in critical paths
- [ ] No hardcoded secrets in committed files
- [ ] `.env.example` is up to date with all required variables

### Functional verification

- [ ] Smoke checklist passes (see `docs/smoke-checklist.md`)
- [ ] Happy path completes end-to-end (mock mode)
- [ ] Dispute path completes end-to-end (mock mode)
- [ ] Console loads and displays all core views
- [ ] Environment panel shows correct chain/contract/mode info
- [ ] Mock mode banner appears when `X402_ALLOW_MOCK=1`

### Documentation

- [ ] README is accurate and reflects current repo structure
- [ ] Provider quickstart is tested and works from scratch
- [ ] Consumer quickstart is tested and works from scratch
- [ ] API endpoints documented match actual service endpoints
- [ ] KNOWN_ISSUES.md is up to date

### Artifacts

- [ ] Contract ABI is current (`contracts/abi/AgentCourt.json`)
- [ ] Schema files are versioned (`schemaVersion: "1.0.0"`)
- [ ] Verdict package schema matches judge service output
- [ ] Evidence receipt schema matches evidence service validation

### Security

- [ ] No private keys in committed files
- [ ] `.env.local` is in `.gitignore`
- [ ] GOATX402_API_SECRET is never logged or exposed
- [ ] Judge service sanitizes user evidence before LLM calls
- [ ] No SQL injection paths in storage queries (parameterized queries)

## Phase exit criteria

### Phase 0: Consolidate

- [ ] Single README flow works from scratch
- [ ] No ambiguity on canonical frontend/service path
- [ ] Env template and startup script work from clean checkout
- [ ] Legacy paths moved to `_legacy/`
- [ ] Branding is consistent (Verdict Protocol / Agent Court)

### Phase 1: Developer MVP

- [ ] External developer can onboard a sample API in under one hour
- [ ] Happy and dispute paths run reliably on testnet
- [ ] Console shows complete transaction and dispute lifecycle
- [ ] Webhook notifications fire for key events
- [ ] SDK published (at least Python)

### Phase 2: Trust hardening

- [ ] Every dispute has a verifiable evidence bundle
- [ ] Every ruling has a signed verdict artifact
- [ ] Ops can recover from service failures without manual DB surgery
- [ ] Structured logging and metrics in place
- [ ] Storage upgraded to PostgreSQL

### Phase 3: Pilot launch

- [ ] At least one pilot uses real payment flow (not mock)
- [ ] At least one real dispute processed end-to-end
- [ ] Production monitoring and alerting configured
- [ ] Security audit complete with no critical findings
- [ ] Support process and incident runbooks documented

## Release process

1. Run full smoke checklist
2. Update `docs/completion.md` with phase status
3. Update `Verdict_Comprehensive_Task_Division.md` with completed tasks
4. Tag release: `git tag -a v<phase>.<version> -m "Phase <N> release"`
5. Update KNOWN_ISSUES.md with any new limitations
6. Log any deviations in `docs/changes.md`

## Sign-off

| Role | Name | Date | Approved |
|------|------|------|----------|
| Engineer A (platform/trust) | | | [ ] |
| Engineer B (product/DX) | | | [ ] |
