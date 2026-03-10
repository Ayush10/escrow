# Payments Evidence Breakdown

Recommended sequence:
1. `PAY-01` first. The repo currently has both mock and live paths, and that ambiguity leaks into developer UX.
2. `PAY-02` and `PAY-03` second. External adoption depends on onboarding, not internal knowledge.
3. `PAY-04` third so disputes become exportable and auditable.
4. `PAY-05` after core surfaces are clear, to harden repeatability.
5. `OPS-02` after canonical flows are stable.
