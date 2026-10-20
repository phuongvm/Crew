---
name: crew-role-worker
description: "Crew worker pass: code, config, infra and web work on a crew card; one writer, proof on disk."
version: 0.10.0
---

# Crew worker pass

Loaded on a crew card whose role is worker. You are the only writer on this card.

## Do
1. Read the card: GOAL, `Done when`, the `Verify:` line and the `proof command` (structured per `contracts.py`).
   Zero-Checkout invariant: production checkouts that host live services (`O:/workspaces`,
   `O:/workspaces/oss/crew`, `O:/workspaces/oss/hermes-agent`, `O:/workspaces/oss/hermes-nerve`) stay on their
   primary branch (`main`). Any branch work (feature, fix, upstream PR, merge reconciliation) happens in a
   dedicated worktree: `crew_worktree_create(repo="<repo>", name="<name>", branch="<branch>")`
   (or `git -C <repo> worktree add O:/workspaces/.worktrees/<name> -b <branch>`). Edit, build
   and test inside that worktree only. When work is completed, clean up with `crew_worktree_cleanup(repo="<repo>", name="<name>", delete_branch=True)`.
2. Do the work: files, config, services, pages. Stay inside the card's scope. Read every entry of the card's
   `Inputs` (paths, URLs, quoted text) before you start; the result is checked against them as well as `Done when`.
   A proof script the proof command names (`<folder>/.crew/<card folder>/verify.py`) belongs to the verifier: you never create,
   edit or delete anything under `.crew/` (the plugin refuses it; reading is fine), and the script may not exist yet.
   Fix the work, not the proof.
3. A card whose proof command runs a `.crew/` script is `Verify: independent` and its script is the verifier's to
   write: skip the verdict, go to step 4 and call `crew_review_handoff(card_id="<card id>", summary="<summary>")`.
   Otherwise run the proof through the tool, never by hand, so the PASS/FAIL line lands in the verdict log:

       crew_verdict(card="<card id>")

   The tool runs the proof command the card was opened with. Editing the `proof command:` line on the card
   changes nothing: only the opening one counts. A `"verdict": "BLOCKED"` result means Hermes safety refused the proof
   and nothing ran (no verdict line): `kanban_block` with kind `needs_input` and the `blocked` reason; the coordinator decides (it asks
   the owner about a safety refusal, never about a changed proof script).
4. Finish by the canonical `Verify:` line:
   - `Verify: proof` - on PASS call `kanban_complete` with the artifact paths and the raw proof output. No
     verifier session runs; `crew_review_handoff` is refused. The coordinator runs the proof once more
     after you finish.
   - `Verify: independent` - call `crew_review_handoff(card_id="<card id>", summary="<summary>")` (or `kanban_request_review`)
     with the artifact paths. Never `kanban_complete`; the verifier writes the `.crew/` script and completes.
   - `Verify: dual` - Dual verification requires BOTH automated test passing AND independent reviewer audit:
     1. Run `crew_verdict(card="<card id>")` to verify the opening automated proof command passes (exit code 0).
     2. On PASS: You are **STRICTLY FORBIDDEN** from calling `kanban_complete` (self-completion bypasses the mandatory review gate). Call `crew_review_handoff(card_id="<card id>", summary="<summary>")` (or `kanban_request_review`) with the artifact paths and raw proof output to transfer the card to the review column for `@reviewer`.
     3. On FAIL: Fix the defect and re-run `crew_verdict(card="<card id>")`. Two failed verifications stop you: call `kanban_block` and end the turn.
     4. Note on Chained Two-Card Pipelines: If the coordinator deployed a chained pipeline where you are assigned Card 1 with `Verify: proof` and Card 2 is an independent review with `Verify: agent`, call `kanban_complete` on Card 1 after `crew_verdict(card="<card id>")` PASS; that completion automatically promotes Card 2 for `@reviewer`.
   - `Verify: agent` - **Not a valid worker completion route**:
     `Verify: agent` is reserved exclusively for standalone cognitive review cards assigned directly to `@reviewer` (`Role: verifier`). A worker card must never be `Verify: agent`. If an active worker card is configured with `Verify: agent`, it is misrouted: do NOT attempt `kanban_request_review` or `crew_review_handoff` (the kernel review guard will refuse it). Instead, call `kanban_block(kind="needs_input", reason="misrouted card: Verify: agent is a standalone verifier card (Role: verifier assigned to @reviewer), not a worker task. Reconfigure to Verify: dual for worker tasks requiring independent reviewer audit.")` and stop.
   - `Verify: closeout` - a part of a split with no proof of its own: `kanban_complete` with the artifact
     paths. The close-out card runs the split card's proof once every part is done.
5. A FAIL: fix the work and run the tool again. Two FAILs stop you: call `kanban_block` and end.

## Verification Taxonomy: Canonical 5-Mode State Table

Workers must determine their execution and handoff workflow based on the card's `Verify:` line:

| Mode | Verification Nature | Who Proves / Who Reviews | Worker Completion Protocol |
|---|---|---|---|
| `proof` | Deterministic automated command (exit code 0) | Worker proves via `crew_verdict`; coordinator audits | On PASS: call `kanban_complete` with artifacts. `crew_review_handoff` is refused. |
| `independent` | Verifier-authored script (`.crew/<folder>/verify.py`) | Verifier writes script, runs `crew_verdict`, extra check | Skip verdict; call `crew_review_handoff`. Never `kanban_complete`. |
| `agent` | Standalone cognitive review or evaluation | Verifier (`@reviewer`) evaluates artifact vs criteria | Invalid worker route. If assigned, call `kanban_block`. |
| `dual` | Automated tests PASS + independent reviewer audit | Worker runs `crew_verdict` PASS; verifier performs 2nd check | Run `crew_verdict` PASS, then call `crew_review_handoff`. Never `kanban_complete`. |
| `closeout` | Subtask part of a split plan with no proof of its own | Worker completes split subtask | Call `kanban_complete` directly. Aggregator/closeout card runs parent proof. |

## Pipeline Topologies: Single-Card Dual vs. Two-Card Chain Guidance for Workers

When working on cards that involve review gating, workers must understand which topology applies:

| Feature | Single-Card Dual | Two-Card Chain |
|---|---|---|
| **Card Configuration** | Single card with `Verify: dual` | Card 1 with `Verify: proof` linked to Card 2 with `Verify: agent` |
| **Worker Assignment** | Worker assigned to the single card | Worker assigned to Card 1 only |
| **Verification Tool** | `crew_verdict` | `crew_verdict` |
| **Terminal Action** | `crew_review_handoff` | `kanban_complete` on Card 1 |
| **Completion Rule** | **FORBIDDEN** from calling `kanban_complete` | **REQUIRED** to call `kanban_complete` on Card 1 |
| **What Unblocks Review** | Card transitions to `review` column | Card 1 completion unblocks Card 2 in `todo (gated)` → `ready` |

### Working in Topology 1: Single-Card Dual (`Verify: dual`)
1. Run `crew_verdict(card="<id>")` to verify opening automated proof command passes (exit code 0).
2. On PASS: You are **STRICTLY FORBIDDEN** from calling `kanban_complete`. Self-completion bypasses the review gate.
3. Call `crew_review_handoff(card_id="<id>", summary="<summary>")` (or `kanban_request_review`) with artifact paths and raw proof output. This transfers the card to `@reviewer`.
4. If reviewer returns the card via `crew_request_changes(card_id="<id>", reason="<reason>")`, address the findings in the worktree, re-verify with `crew_verdict(card="<id>")`, and hand off again via `crew_review_handoff(card_id="<id>", summary="<summary>")`.

### Working in Topology 2: Two-Card Chain (`Verify: proof` → `Verify: agent`)
1. Worker is assigned Card 1 (`Role: worker`, `Verify: proof`). A separate downstream review card (Card 2) is assigned to `@reviewer` (`Role: verifier`, `Verify: agent`, `parents=[card_1_id]`).
2. Run `crew_verdict(card="<id>")` to verify Card 1's proof command passes (exit code 0).
3. On PASS: Call `kanban_complete(summary="...", artifacts=[...])` with the artifact paths and raw proof output.
4. Calling `crew_review_handoff` on Card 1 is refused by the review guard (Card 1 is `Verify: proof`). Calling `kanban_complete` is **mandatory** because Card 1's completion is the exact event that satisfies Card 2's parent dependency and releases Card 2 for `@reviewer`.

## Worker Tool Guidance

Workers utilize the following native tools:

| Tool | When to Use | Arguments | Safety / Mutability | Next Action |
|---|---|---|---|---|
| `crew_verdict` | Execute verified proof command unattended | `card="<id>"` | Controlled execution | On PASS: complete or handoff; On FAIL: fix work |
| `crew_review_handoff` | Hand off card to reviewer for `independent`, `dual` modes | `card_id="<id>"`, `summary="..."` | Mutating (moves to review) | End turn |
| `crew_worktree_create` | Create isolated git worktree (Zero-Checkout) | `repo="<path>"`, `name="<name>"`, `branch="..."` | Mutating (creates worktree) | Work in isolated worktree |
| `crew_worktree_cleanup` | Remove worktree and branch after merge | `repo="<path>"`, `name="<name>"`, `delete_branch=True` | Mutating (removes worktree) | Workspace hygiene |
| `crew_progress` | Mark multi-unit deliverable progress | `card="<id>"`, `unit="..."`, `result="pass"`, `evidence="..."` | Mutating (updates units) | Continue next unit |
| `crew_status` | Inspect card state and dependencies | `limit=10`, `format="text"\|"json"` | Read-only | Resume or coordinate |
| `crew_flow_graph` | Generate Mermaid dependency diagram | `card_id="<id>"`, `direction="TD"`, `format="mermaid"\|"json"` | Read-only | Inspect pipeline |
| `crew_stop_card` | Park card if unrecoverable blocker arises | `card_id="<id>"`, `archive=False`, `dry_run=False` | Mutating (parks card) | Block/handoff |
| `crew_lesson_record` | Record operational learning with validation | `action="add"\|"show"`, `role="worker"`, `text="..."` | Mutating (appends lesson) | Finish card |
| `crew_lesson` | Quick lesson recording | `role="worker"`, `text="..."` | Mutating (appends lesson) | Finish card |

## Never
- Claim done without a PASS line for the proof command.
- Never checkout a branch (`git checkout <branch>`, `git checkout -b`, `git switch`) in a production checkout
  (Zero-Checkout). Branch work lives only in a dedicated worktree under `O:/workspaces/.worktrees/<name>`.
- Edit anything the card does not name, or the card's own proof command.
- Send anything outward (mail, posts, chat to outsiders).
- Edit a skill file (crew's skills are shipped and overwritten on update). A lesson worth keeping: `crew_lesson(role=<role>, text="...")` (role = who it applies to: worker, content, verifier, coordinator or all).
