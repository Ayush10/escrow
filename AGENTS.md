# Verdict Protocol Repo Operating System

This repo uses file-based project management. Contributors and coding agents must treat the files below as the working system for planning, task ownership, and status updates.

## Source of truth

Product direction:
- `PRODUCT_PLAN.md`

Execution and division of work:
- `Verdict_Comprehensive_Task_Division.md`
- `docs/two_person_execution_plan.md`
- `docs/project_management_rules.md`
- `docs/completion.md`
- `docs/changes.md`

Lane folders:
- `docs/protocol_contracts/`
- `docs/payments_evidence/`
- `docs/judge_reputation/`
- `docs/console_ops/`

## Lane mapping

Until individual owners are finalized, work is divided by lane:
- `protocol_contracts`: contract, ABI, schemas, protocol client, deploy story
- `payments_evidence`: x402, provider API, evidence service, consumer flows
- `judge_reputation`: judge service, verdict packages, reputation service, CI for service flows
- `console_ops`: console/frontend, demo runner, repo governance, release process

If named owners are assigned later, keep the same structure and update the mapping in `Verdict_Comprehensive_Task_Division.md`.

## Two-person mode

Current active staffing model:
- `Engineer A`: platform/trust/integration lead
- `Engineer B`: product/dx/frontend lead

The full assignment and handoff plan lives in `docs/two_person_execution_plan.md`.

## Start-of-work checklist

Before starting any task:
1. Read the relevant rows in `Verdict_Comprehensive_Task_Division.md`.
2. Read the lane folder docs for the lane you are working in.
3. Confirm dependencies are completed or explicitly unblockable.
4. If the task changes scope, update the task matrix before coding.

## During work

- Keep status changes in `Verdict_Comprehensive_Task_Division.md`.
- Update lane notes when you learn something durable.
- Record process or scope deviations in `docs/changes.md`.
- Do not create parallel task lists outside this system.

## Close-out checklist

When a task is completed:
1. Mark the task complete in `Verdict_Comprehensive_Task_Division.md`.
2. Update the lane `task_list.md`.
3. Update `docs/completion.md`.
4. Add a short note to `docs/changes.md` if the implementation changed plan, scope, or ownership assumptions.

## Shared-task rule

If a task touches multiple lanes, keep one primary owner and list the other lanes in the task description or notes. Avoid splitting one deliverable into multiple owners unless the handoff boundary is explicit.
