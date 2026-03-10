# Judge Reputation Breakdown

Recommended sequence:
1. `JDG-01` because signed verdicts are the main trust artifact missing from the current implementation.
2. `JDG-02` because low-confidence paths need somewhere safe to go.
3. `JDG-03` because production signing cannot stay env-key only.
4. `REP-01` after verdict packaging is stable.
5. `OPS-01` can run in parallel once the core workflow is known.
