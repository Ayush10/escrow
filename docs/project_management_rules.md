# Verdict Protocol Project Management Rules

## Purpose

This repo is managed through files in the repository, not through scattered chat state.

The goal is simple:
- any contributor can see what the current priorities are
- ownership is explicit
- changes in scope are recorded
- completion is visible without asking around

## File hierarchy

Strategic direction:
1. `PRODUCT_PLAN.md`

Execution and ownership:
2. `Verdict_Comprehensive_Task_Division.md`
3. `AGENTS.md`
4. `docs/project_management_rules.md`
5. `docs/completion.md`
6. `docs/changes.md`
7. `docs/<lane>/README.md`
8. `docs/<lane>/task_list.md`
9. `docs/<lane>/task_breakdown.md`
10. `docs/<lane>/notes.md`

Rule:
- `PRODUCT_PLAN.md` decides what the product is.
- `Verdict_Comprehensive_Task_Division.md` decides what work exists now, who owns it, and what depends on what.

## Lane folders

The repo is divided into four lanes:
- `protocol_contracts`
- `payments_evidence`
- `judge_reputation`
- `console_ops`

Each lane folder must contain:
- `README.md`: scope of the lane
- `task_list.md`: task status for that lane
- `task_breakdown.md`: near-term sequencing
- `notes.md`: durable findings, blockers, and context

## Task rules

Every active task must have:
- a task ID
- a primary owner lane
- a module or file scope
- a dependency list
- an acceptance condition
- a status

Allowed statuses:
- `Not started`
- `In progress`
- `Blocked`
- `Review`
- `Completed`

## Scope-change rule

If implementation reveals a better approach:
1. update the task row
2. add a note in `docs/changes.md`
3. update the lane notes if the decision affects future work

Do not silently redefine tasks in code only.

## Branch and PR rules

- One PR should map to one or more task IDs from `Verdict_Comprehensive_Task_Division.md`.
- PRs must say whether docs were updated.
- If a PR intentionally deviates from the task matrix, the PR must point to the corresponding entry in `docs/changes.md`.

## Completion rules

A task is only complete when:
- the implementation exists
- the acceptance criteria are met
- the relevant docs are updated
- the task row and lane task list are updated

## Weekly rhythm

Suggested operating cadence:
- Monday: pick work from the task matrix
- Midweek: update notes and blockers
- Friday: refresh `docs/completion.md`, review `docs/changes.md`, and decide whether priorities need to move

## What not to do

Do not:
- keep separate personal TODO lists as the real source of truth
- start work that is not represented in the task matrix
- change ownership informally
- leave completed work unreflected in the docs
