---
name: crew-role-worker
description: "Crew worker pass: code, config, infra and web work on a crew card; one writer, proof on disk."
version: 0.9.13
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

       crew_verdict(card_id="<card id>")

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
   - `Verify: dual` - on PASS of `crew_verdict`, call `crew_review_handoff(card_id="<card id>", summary="<summary>")`
     with artifact paths and proof output. Never `kanban_complete`; the verifier independently checks and completes.
   - `Verify: agent` - call `crew_review_handoff(card_id="<card id>", summary="<summary>")`.
   - `Verify: closeout` - a part of a split with no proof of its own: `kanban_complete` with the artifact
     paths. The close-out card runs the split card's proof once every part is done.
5. A FAIL: fix the work and run the tool again. Two FAILs stop you: call `kanban_block` and end.

## Worker Tool Guidance

Workers utilize the following native tools:

| Tool | When to Use | Arguments | Safety / Mutability | Next Action |
|---|---|---|---|---|
| `crew_verdict` | Execute verified proof command unattended | `card_id="<id>"` | Controlled execution | On PASS: complete or handoff; On FAIL: fix work |
| `crew_review_handoff` | Hand off card to reviewer for `independent`, `dual`, `agent` modes | `card_id="<id>"`, `summary="..."` | Mutating (moves to review) | End turn |
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
