# Proposal: Extended Native Tools for Crew Plugin

## Why

The first native-tool change (`native-crew-tools`) gave agents five structured tools (`crew_card_create`, `crew_diagnose`, `crew_verdict`, `crew_status`, `crew_event_subscribe`). Every other Crew operation an agent performs during a card's life - stopping a card, handing it to a verifier, returning it with requested changes, splitting a goal into parallel cards, creating and removing the dedicated worktrees the Zero-Checkout invariant mandates, drawing the card's flow, recording a lesson - still runs through a terminal subshell (`crew_stop.py`, `crew_card.py plan|lesson`, raw `git worktree`, `crew_graph.py`). On Windows/MSYS hosts that path is where quoting, path-translation and approval failures happen, and raw `git` in an agent shell is exactly where the Zero-Checkout invariant gets broken.

## What Changes

- Add 8 native tools to `oss/crew/native_tools.py`, grouped by ops area:
  - **Core ops**: `crew_stop_card` - park (or archive) one crew card through `crew_stop.stop_card`.
  - **Pipeline ops**: `crew_review_handoff` (verifier handoff for independent cards, or hand-off preview), `crew_request_changes` (kernel `request_changes` on an active review run), `crew_plan_split` (validated `crew_card.run_plan`, dry run by default).
  - **Workspace ops**: `crew_worktree_create` and `crew_worktree_cleanup` - guarded, hardened (`git_safe`) `git worktree add/remove` that never checks out a branch in the source checkout.
  - **Intelligence ops**: `crew_flow_graph` (card process flow as a Mermaid flowchart or JSON) and `crew_lesson_record` (add/show role lessons through `crew_lessons`).
- Add typed validators to `oss/crew/contracts.py`: `is_valid_card_id`, `is_valid_worktree_name`, `branch_name_gaps`, `lesson_gaps`, `change_request_gaps`, `PlanSplitSpec`.
- Register the 8 tools under the `crew` toolset from `register(ctx)` via `register_extended_tools(ctx)` and declare them in `plugin.yaml` `provides_tools`.
- Add `oss/crew/tests/test_extended_tools.py` covering every tool on a throwaway kernel board, a throwaway git repository and a scratch lessons home.

## Capabilities

### New Capabilities
- `crew-extended-tools`: Eight additional native Crew tools for Core, Pipeline, Workspace and Intelligence operations with typed contract validation.

### Modified Capabilities
<!-- None: the five native-crew-tools requirements are unchanged; extended tools register alongside them. -->

## Impact

- **Affected code**: `oss/crew/native_tools.py`, `oss/crew/contracts.py`, `oss/crew/__init__.py`, `oss/crew/plugin.yaml`, `oss/crew/tests/test_extended_tools.py` (new).
- **APIs**: 8 new tools in the Hermes tool registry when the Crew plugin loads (13 total).
- **Dependencies**: none added; standard library plus existing Crew script modules and Hermes's kernel (`hermes_cli.kanban_db`) where the CLI already uses it.
- **Safety**: no tool runs an unconfirmed proof, switches a branch in a source checkout, removes the main worktree, or lets a caller set an owner-only field (`closeout_proof`, `--role all` lessons from an agent run).
