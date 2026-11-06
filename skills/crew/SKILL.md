---
name: crew
description: "Plan and coordinate /crew cards, intake, and contracts."
version: 0.10.7
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

Tracks A/B, routing matrix, taxonomy, topologies, 17-tool decision matrix: `references/coordinator-intake.md`.
