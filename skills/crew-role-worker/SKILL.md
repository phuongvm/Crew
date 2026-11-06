---
name: crew-role-worker
description: "Implement crew card code, config, and infra with disk proof"
version: 0.10.7
---
# Crew worker pass

Loaded on a crew card whose role is worker. You are the only writer on this card.

## When to Use
Any crew card with `Role: worker`: code, config, infra and service work judged by the card's `Done when` and `proof command`.

## Do
1. Read the card: GOAL, `Done when`, `Verify:` line, proof command, every `Inputs` entry (paths, URLs, exploration docs, OpenSpec artifacts).
2. Zero-Checkout: live checkouts (`O:/workspaces`, `oss/crew`, `oss/hermes-agent`, `oss/hermes-nerve`) stay on `main`; branch work happens in `O:/workspaces/.worktrees/<name>` via `crew_worktree_create`, cleaned with `crew_worktree_cleanup`.
3. Do the work inside the card's scope with deep modules at clean seams (`codebase-design`), domain terms (`GLOSSARY.md`), TDD at public seams (Red → Green, no tautological tests), surgical edits (no drive-by refactors). Never touch `.crew/` (the verifier's proof scripts).
4. Run the proof through the tool, never by hand: `crew_verdict(card="<card id>")`. `"verdict": "BLOCKED"` → `kanban_block(kind="needs_input")`.
5. Finish by the `Verify:` line — `proof`: `kanban_complete` on PASS · `independent`: skip verdict, `crew_review_handoff` · `dual`: `crew_verdict` PASS then `crew_review_handoff` (never `kanban_complete`) · `agent`: misrouted, `kanban_block` · `closeout`: `kanban_complete`. Two FAILs → `kanban_block` and end.

## Handoff summary (mandatory)
`- Done:` deliverables, files, SHAs · `- Not done:` · `- Evidence:` crew_verdict PASS/FAIL, before → after output · `- Blast radius:` · (`kanban_block` adds `- Decision needed:`).

## Never
Edit `.crew/`, change the proof line, complete a `dual`/`independent` card yourself, work outside the worktree, or skip `crew_verdict`.

5-mode verification table, pipeline topologies (single-card dual vs two-card chain) and tool guidance: `references/worker-pass.md`.
