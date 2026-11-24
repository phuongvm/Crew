---
name: crew
description: "Plan and coordinate /crew cards, intake, and contracts."
version: 0.10.10
---
# /crew - coordinator intake

## When to Use
The turn starts with `/crew <ask>` (OpenSpec governance track) or `/crew-no-spec <ask>` (fast-track card). You turn the ask into a complete card contract; you never do the work.

## Rules
1. **Clarify vague asks via `clarify`**: open nothing until GOAL, `Done when`, `Inputs`, `Verify:` and proof command are concrete; ask once in one batch.
2. **Be critical first**: challenge scope, hidden assumptions, missing inputs, unverifiable clauses.
3. **Contract fields**: GOAL · Role (worker/content/verifier) · Inputs · Done when · Verify (`proof`|`independent`|`dual`|`agent`|`closeout`) · proof command · Artifact · Safety choice.
4. **Verify mode**: command → `proof`; verifier script → `independent`; tests + audit → `dual`; standalone review → `agent`; split part → `closeout`. Remediation + re-review = Card 1 (`proof`) → Card 2 (`verifier`, `agent`, `parents=[card_1]`).
5. **Dispatch**: `crew_proof_check` → `clarify` if `safety_mode == 'safe'` → `crew_card_create` → background `crew_card.py watch --card <id>`.
6. **Never** bypass Kanban with `delegate_task` on `/crew` or hardcode model/provider (profile `config.yaml` rules).
7. **Unified Cognitive & Tool Routing Matrix**: use `openspec-explore`/`grilling`/`codebase-design` for discovery, `mcp__graphify__` for topology, `diagnosing-bugs` for defects, and **Zero-Checkout** (`O:/workspaces/.worktrees/<name>` for all branch work).

## Answering crew's report
Read the handoff (`Done / Not done / Evidence / Blast radius`), re-run the proof where the coordinator audits, report with evidence. REJECTED → remediation + chained re-review card.

Full guide & 17-tool matrix: `references/coordinator-intake.md`.
