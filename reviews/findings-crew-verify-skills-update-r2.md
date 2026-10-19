# Re-review: `Verify: agent` contract rendering

## Verdict: REJECTED

## Scope reviewed

- `contracts.py` renderer for canonical card contracts.
- `scripts/crew_card.py` renderer used by the Crew CLI.
- `tests/test_role_contracts.py` semantic lifecycle coverage.
- Shipped Crew role and verifier skills.
- Architecture authority: `REFERENCE.md`.

## Confirmed remediation

1. `contracts.py:638-651` has a dedicated `verify_mode == "agent"` branch. Its rendered footer assigns the verifier as the sole writer, requires the verifier's own proof receipt, directs `kanban_complete(summary=...)` after PASS, and refuses `crew_review_handoff`.
2. `scripts/crew_card.py:864-877` implements the equivalent dedicated `mode == "agent"` branch using the native `crew_verdict(card=...)` form.
3. `tests/test_role_contracts.py:473-575` adds semantic tests for both renderers, round-trip parsing, forbidden legacy footer terms, and all five verification modes.
4. `skills/crew-verifier/SKILL.md:17-21,44-51` and `skills/crew/SKILL.md:195-201,213-218` define `agent` as a standalone verifier card that completes directly rather than requesting review.

## Blocking findings

### [Severity: High] Architecture reference still describes only two verification modes

`REFERENCE.md:152-164` states that the `Verify:` line selects only `proof` or `independent`, then defines the verifier path only for `independent`. That is inconsistent with the current five-mode taxonomy in the reviewed skills and does not document the direct-completion lifecycle for `agent` now rendered by both code paths.

**Required remediation:** Update `REFERENCE.md` to enumerate `proof`, `independent`, `agent`, `dual`, and `closeout`; specify that a standalone `Verify: agent` card is assigned to the verifier, records its own verdict, then calls `kanban_complete`, never `kanban_request_review` or `crew_review_handoff`.

### [Severity: High] Remediation resides as uncommitted changes in the protected primary checkout

The reviewed renderer and test changes are present as uncommitted modifications in `O:/workspaces/oss/crew`, which is the protected production checkout on `main`. This conflicts with the zero-checkout/clean-primary requirement in `O:/workspaces/rules/AGENTS.md:213-219`. A clean primary checkout is an explicit governance invariant; code and test remediation must be isolated in a dedicated worktree until integrated through the approved path.

**Required remediation:** Move the pending changes to an approved worktree under `O:/workspaces/.worktrees/`, restore the production checkout to a clean `main`, and present the integration evidence for re-review.

## Evidence

- Static source/skill inspection cited above confirms the localized renderer remediation and test intent.
- The card's formal artifact proof and one independent semantic suite run are recorded separately in the verifier's Kanban evidence after this document is written.

## Re-review disposition

The renderer behavior and regression-test design address the stale `agent` footer, but the architecture documentation remains contradictory and the code is not isolated from the protected production checkout. The requested "zero contradictions" condition is therefore not met.
