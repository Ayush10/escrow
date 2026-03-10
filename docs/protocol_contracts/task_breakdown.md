# Protocol Contracts Breakdown

Recommended sequence:
1. `PRT-01` because all downstream service work depends on one stable contract/client story.
2. `PRT-02` so every lane uses the same deployment and environment assumptions.
3. `PRT-04` to formalize schemas before signed verdict packages and audit export work.
4. `PRT-03` to lock the lifecycle into repeatable tests.

Current blocker:
- No single published compatibility matrix yet.
