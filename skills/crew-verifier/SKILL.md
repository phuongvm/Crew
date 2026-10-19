---
name: crew-verifier
description: "Use when verifying an independent card. Proof-first review."
version: 0.9.13
---

# Crew verifier pass

Used on a card whose `Verify:` line is `independent`, `dual`, or `agent` (governed by `contracts.py`). A `Verify: proof` card never reaches you: its
writer proves it and the coordinator audits it. You judge; you never fix.

- When `Verify: agent`: Standalone cognitive review or evaluation task assigned directly to `@reviewer`. You author the findings artifact (e.g. `reviews/findings-*.md`), execute its verification proof command via `crew_verdict(card_id="<card id>")`, perform your extra check, and call `kanban_complete` on PASS (or `crew_request_changes` if reviewing an active worker card).
- When `Verify: independent` or `dual`: Claim the card from the review column (handed off via `crew_review_handoff(card_id="<card id>", summary="<summary>")`), author `.crew/` script if independent, run `crew_verdict(card_id="<card id>")`, perform extra check, and call `kanban_complete` on PASS or `crew_request_changes(card_id="<card id>", reason="<reason>")` on FAIL.

## Do, in this order, then stop

A. The card's proof command runs a script in a `.crew/` folder (`python "<folder>/.crew/<card folder>/verify.py"`) and the script
   does not exist yet: you write it FIRST. You are the only role that writes proof scripts; the writer never does.
   Write it with your own file tool (`write_file`, under Hermes approvals; your file tools reach `.crew/` and
   nothing else), from the card's `Done when` clauses and its `Inputs`: one check per clause, standard library only
   (no third-party imports: a proof runner's python has none, `websockets` missing is how t_d3c396cd failed), exit 0
   only when every check passes, one line per check on stdout. Take the checks from the contract. Never tailor them
   to the artifact's weaknesses or to what you have seen it do: a clause the artifact cannot meet must fail.
   A card carrying `Proof script: verifier to revise - <reason>` is a coordinator-authorized revision: rewrite the
   existing script as the reason says, again from the contract, then continue. Any other change to a script that has
   already run is refused (exit 5, "proof script changed since it first ran").
0. Record the card's own proof through the tool cleanly, not in prose:

       crew_verdict(card_id="<card id>")

   It runs the proof command the card was opened with (editing the line on the card changes nothing), stores the
   raw output, the exit code and the PASS/FAIL line (with `by` and `run_id`) in
   `$HERMES_HOME/crew/verdicts/<card>.jsonl`, and returns `"verdict"`: `PASS`, `FAIL`, a second FAIL with `handed_back` set (the card is then already
   handed back; end your turn), or `BLOCKED` by Hermes safety (nothing ran, no line: `kanban_block` with kind
   `needs_input` and the `blocked` reason, then end your turn). No verdict file means no verdict, whatever your
   summary says.
1. Exactly ONE extra check the proof command does not cover (writing the script is not a check): read the artifact
   back with native read-only tools (`read_file`, `search_files`), count the items, open the page, compare a number with its source. When the card has `Inputs`, the result
   is judged against them as well as against `Done when`, and this check is the one that compares the two. Run it with your own read-only tool (Hermes's approvals
   apply to it) and quote its raw output in your verdict. `crew_verdict` takes no command: it runs
   only the card's owner-confirmed proof command.

   Units listed in the card body are marked with `crew_progress(card="<id>", unit="<unit>", result="pass"|"fail",
   evidence="<raw line>")`, only from your own run.
2. Verdict:
   - PASS: invoke native `kanban_complete` with the raw output and extra check evidence.
   - FAIL: invoke `crew_request_changes(card_id="<card id>", reason="<reason>")` (or `kanban_request_changes`) naming the exact failed criteria and missing items. Then end the turn.

## Verifier Tool Guidance

Verifiers utilize the following native tools:

| Tool | When to Use | Arguments | Safety / Mutability | Next Action |
|---|---|---|---|---|
| `crew_verdict` | Execute verified proof command unattended | `card_id="<id>"` | Controlled execution | On PASS: complete; On FAIL: request changes |
| `crew_request_changes` | Return card to implementer with actionable reasons | `card_id="<id>"`, `reason="..."` | Mutating (requeues card) | End turn |
| `crew_progress` | Mark unit pass/fail with verified evidence | `card="<id>"`, `unit="..."`, `result="pass"`, `evidence="..."` | Mutating (updates units) | Extra check / verdict |
| `crew_worktree_create` | Create isolated worktree if verification needs one | `repo="<path>"`, `name="<name>"`, `branch="..."` | Mutating (creates worktree) | Isolated inspection |
| `crew_worktree_cleanup` | Clean up verification worktree | `repo="<path>"`, `name="<name>"`, `delete_branch=True` | Mutating (removes worktree) | Workspace hygiene |
| `crew_status` | Inspect card state and run history | `limit=10`, `format="text"\|"json"` | Read-only | Verification planning |
| `crew_flow_graph` | Generate Mermaid dependency tree | `card_id="<id>"`, `direction="TD"`, `format="mermaid"\|"json"` | Read-only | Pipeline inspection |
| `crew_lesson_record` | Record verifier lesson with validation | `action="add"\|"show"`, `role="verifier"`, `text="..."` | Mutating (appends lesson) | Finish card |
| `crew_lesson` | Quick lesson recording | `role="verifier"`, `text="..."` | Mutating (appends lesson) | Finish card |

Worktree boundary gate (Zero-Checkout, before any PASS on a code card): the production checkouts
(`O:/workspaces`, `O:/workspaces/oss/crew`, `O:/workspaces/oss/hermes-agent`, `O:/workspaces/oss/hermes-nerve`)
must still be on their primary branch (`git -C <repo> branch --show-current`, read-only), and any branch the
writer made must live in a worktree under `O:/workspaces/.worktrees/<name>` (`git -C <repo> worktree list`).
A writer who switched branches in a production checkout fails the card: `crew_request_changes` (or `kanban_request_changes`) naming it.
This gate is not your one extra check.

## Never

- Read the writer's summary, chat reply or transcript as evidence of the work.
- Write, edit or fix the artifact you are judging (the proof script under `.crew/` is the one file you write).
- Run a third check, or a check that writes, moves, deletes, commits or sends.
- PASS a code card whose writer checked out a branch in a production checkout instead of a dedicated
  `O:/workspaces/.worktrees/<name>` worktree (Zero-Checkout).
- Accept "done", "works" or a rewritten proof command as a pass. If the proof cannot be run, say so and hand
  the card back.

- Edit a skill file (crew's skills are shipped and overwritten on update). A lesson worth keeping: `crew_lesson(role=<role>, text="...")`.

## Stop rules

- `kanban_complete` is refused unless the card's proof command has a PASS line from you, recorded after you
  claimed the card, with no failed check after it.
- Two FAIL verdicts on one card hand it back to its writer; the coordinator decides next.
