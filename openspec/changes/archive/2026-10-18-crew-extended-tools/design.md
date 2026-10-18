# Design: Extended Native Tools for Crew Plugin

## Context

`native_tools.py` already wraps Crew's script modules as in-process tool handlers (schema + handler + `_string_response_adapter`). The extended set follows the same pattern: each handler validates its arguments with `contracts.py` helpers, then calls the one existing implementation of the operation, so the CLI, slash commands and tools cannot drift apart.

## Goals / Non-Goals

**Goals**
- Eight deterministic tools, one per operation, each returning a dict with `status` in `ok | error | refused | dry_run` and never raising.
- Reuse the existing implementation of every operation (`crew_stop.stop_card`, `crew_card.lift_into_review`, kernel `request_changes`, `crew_card.run_plan`, `crew_graph.build_graph`, `crew_lessons.add`).
- Enforce the Zero-Checkout invariant in code for worktree operations.

**Non-Goals**
- No new board states or kernel changes; no LLM calls inside handlers.
- No bulk stop (the all-cards stop stays an owner CLI action); the tool stops exactly one named card.
- No owner-confirmed close-out proof through `crew_plan_split`.

## Decisions

### D1. Per-call board resolution for import-bound modules
`crew_stop` and `crew_handoff` bind `KANBAN_DB` at import. The handlers resolve the board with `crew_card.kanban_db()` on every call, swap it into the module for the call, and restore it in `finally`, so a long-lived gateway process always acts on the current board and never leaks the swap.

### D2. Review handoff follows the card's `Verify:` line
Mirrors the plugin's `_review_guard`: `proof` and `closeout` cards are refused with the step that does finish them; `independent|agent|dual` cards get `repin_for_review` (best effort) then `lift_into_review` to the verifier profile (or an explicit reviewer). `action=preview` returns `crew_handoff.handoff_text` read-only.

### D3. Request-changes goes straight to the kernel
`hermes_cli.kanban_db.request_changes` through `crew_card.kb_conn()` - the same call `hermes kanban request-changes` makes - with a pre-check (`change_request_gaps`) that demands a card id and a concrete reason of at least 10 characters. A card that is not in a review run claimed from `review` is reported as `refused`.

### D4. Plan split is dry-run by default and cannot carry an owner proof
`PlanSplitSpec` drops unknown keys (including `closeout_proof`), refuses `Verify: closeout` children, duplicate artifacts and incomplete child contracts before `run_plan` is called. `dry_run` defaults to `true`; a real split must be asked for explicitly.

### D5. Worktree tools: hardened git, never a checkout
All git calls go through `scripts/git_safe.run_git` (pinned config: no hooks, fsmonitor, external diff or filter drivers). `crew_worktree_create` runs only `git worktree add <root>/<name> -b <branch> <base>` - a new branch in a new folder - and refuses protected branches (`main`, `master`, `HEAD`), existing branches, existing paths, unsafe names (one segment of `[A-Za-z0-9._-]`, no `..`), option-like bases, and roots that overlap the repository. The worktrees root resolves as explicit argument > `$CREW_WORKTREES_ROOT` > nearest ancestor `.worktrees` folder (`O:/workspaces/.worktrees` for `O:/workspaces/oss/crew`) > `<repo parent>/.worktrees`. `crew_worktree_cleanup` removes only a path registered in `git worktree list --porcelain` that is not the main worktree, refuses a dirty worktree unless `force`, then prunes; branch deletion is opt-in, safe (`-d`) unless forced, and never touches a protected branch.

### D6. Mermaid rendering is a pure function
`graph_to_mermaid(graph, direction)` maps `build_graph` nodes to stable ids `n0..nN` in graph order, escapes Mermaid-significant characters as entity codes, drops edges to unknown nodes and emits one `classDef` per status. Same graph in, same text out.

### D7. Lessons keep the existing write rules
`lesson_gaps` validates role and length before `crew_lessons.add`, which still owns dedupe, the 50-entry/8 KB cap, the atomic write and the rule that an agent run may not write an `all` lesson (reported as `refused`).

## Risks / Trade-offs

- **Kernel availability**: `crew_request_changes` and `crew_review_handoff` need `hermes_cli` importable (true inside the Hermes process); otherwise they return `status: error` with the import reason rather than failing silently.
- **Dispatcher fence in tests**: a dispatcher-spawned worker fences writes to the board named by `HERMES_KANBAN_DB`; the test module therefore names its throwaway board via `KANBAN_DB` and unsets `HERMES_KANBAN_DB` for its own duration only.
