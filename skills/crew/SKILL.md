---
name: crew
description: "Crew intake: /crew <ask> - the coordinator checks the ask critically, asks what is missing, then opens one contract card and hands it over."
version: 0.10.9
---
# /crew - coordinator intake

## When to Use
The turn starts with `/crew <ask>` (OpenSpec governance track) or `/crew-no-spec <ask>` (fast-track card). You turn the ask into a complete card contract; you never do the work.

## Rules
1. **A vague ask gets questions, through `clarify`**: open nothing until GOAL, `Done when`, `Inputs`, `Verify:` and proof command are concrete; ask only what the result needs, in one batch.
2. **Be critical first**: challenge scope, hidden assumptions, missing inputs, unverifiable clauses.
3. **The contract — every field required**: GOAL · Role (worker/content/verifier) · Inputs · Done when · Verify (`proof`|`independent`|`dual`|`agent`|`closeout`) · proof command · Artifact · Safety choice.
4. **Verification mode**: deterministic command → `proof`; verifier script → `independent`; tests + reviewer audit → `dual`; standalone review for `@reviewer` → `agent`; split part → `closeout`. Remediation + re-review = Card 1 (`proof`) → Card 2 (`verifier`, `agent`, `parents=[card_1]`).
5. **Complete → show the draft, open the card, end the turn**: `crew_proof_check` → `clarify` when `safety_mode == 'safe'` → `crew_card_create` → background `crew_card.py watch --card <id>`.
6. **Never** bypass Kanban with `delegate_task` on a `/crew` turn or hardcode model/provider (the profile `config.yaml` rules).

## Answering crew's report
Read the handoff (`Done / Not done / Evidence / Blast radius`), re-run the proof where the coordinator audits, report with evidence. REJECTED → remediation card + chained re-review card.

## Unified Cognitive & Tool Routing Matrix
- **Guided Discovery Loop:** use `openspec-explore`, `grilling`, `codebase-design`, `to-spec`, and `to-tickets` when the ask lacks a settled contract; persist the Exploration Document before dispatch.
- **Codebase intelligence:** use `mcp__graphify__graph_stats`, `mcp__graphify__god_nodes`, `mcp__graphify__get_neighbors`, and `mcp__graphify__shortest_path` for topology, then verify implementation details with bounded source reads.
- **Verification routing:** use `diagnosing-bugs` for defects, `wizard` for manual setup, `crew_verdict` for proof, and `openspec-verify-change` for contract fidelity. Never hardcode a model or provider.

## Zero-Checkout
Production checkouts (`O:/workspaces`, `oss/crew`, `oss/hermes-agent`, `oss/hermes-nerve`) stay on `main`; all branch work uses `O:/workspaces/.worktrees/<name>`. Every codebase card's `Constraints:` carries this rule. The `/crew-no-spec` direct-card track remains shipped separately.

Tracks A/B, routing matrix, taxonomy, topologies, 17-tool decision matrix: `references/coordinator-intake.md`.
