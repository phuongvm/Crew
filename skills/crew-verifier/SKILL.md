---
name: crew-verifier
description: "Verification pass for a crew card with `Verify: independent`. Runs the proof itself, never trusts the writer."
version: 0.10.9
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

## Unified Verification Lenses
- **Contract lens:** compare the result against every `Done when` clause and every `Inputs` entry, including Exploration Documents and OpenSpec references.
- **Runtime lens:** re-run the owner-confirmed proof with `crew_verdict`, then perform exactly one independent substantive check.
- **TDD Anti-Tautology:** reject tests that only restate implementation details; require a public-seam behavior check and report the exact failed criterion.

## Zero-Checkout
Reviewers never switch branches or mutate production checkouts (`O:/workspaces`, `oss/crew`, `oss/hermes-agent`, `oss/hermes-nerve`); all branch inspection and review work uses `O:/workspaces/.worktrees/<name>`.


## Handoff summary (mandatory)
`- Done:` · `- Not done:` · `- Evidence:` proof PASS/FAIL (rc), extra check result · `- Verdict:` APPROVED/REJECTED.

## Never
Fix the work, tailor a proof script to the artifact, accept a writer's verdict line, or complete a card whose proof failed.

Verification taxonomy table, pipeline topologies and stop rules: `references/verifier-pass.md`.
