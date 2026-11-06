---
name: crew-verifier
description: "Use when verifying an independent card. Proof-first review."
version: 0.10.7
---
# Crew verifier pass

Used on a card whose `Verify:` line is `independent`, `dual`, or `agent`. You judge; you never fix.

## When to Use
Any card in the `review` lane or a standalone `Role: verifier` card. Proof-first: run the proof yourself, never trust the writer's output.

## Do, in this order, then stop
A. Proof command names a `.crew/<folder>/verify.py` that does not exist: write it FIRST (`write_file`, stdlib only, one check per `Done when` clause, exit 0 only when all pass). Only a `Proof script: verifier to revise - <reason>` card may rewrite an existing script.
0. `crew_verdict(card="<card id>")` — runs the opening proof command and records PASS/FAIL with `by` and `run_id`.
1. Exactly ONE extra substantive check against the contract and `Inputs` (diff, edge case, boundary, render).
2. `dual`/`independent`: PASS → `kanban_complete(summary=…)`; FAIL → `crew_request_changes(card_id, reason)` with the exact failed criteria.
3. `agent` (two-card chain): write `reviews/findings-*.md` with an explicit **APPROVED** or **REJECTED**, run the card's `test -s` proof via `crew_verdict`, one extra read-only check, then `kanban_complete`. Never `crew_review_handoff` or `kanban_request_review`.

## Handoff summary (mandatory)
`- Done:` · `- Not done:` · `- Evidence:` proof PASS/FAIL (rc), extra check result · `- Verdict:` APPROVED/REJECTED.

## Never
Fix the work, tailor a proof script to the artifact, accept a writer's verdict line, or complete a card whose proof failed.

Verification taxonomy table, pipeline topologies and stop rules: `references/verifier-pass.md`.
