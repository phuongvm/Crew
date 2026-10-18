# Proposal: Native Runtime Event Hooks Replacing Background Terminal Watchers

## Why

Crew currently tracks card execution and completion by spawning unattended background polling scripts (`terminal(background=true, command='python3 crew_card.py watch --card <id>')`).
This approach is brittle: notification regex filters miss exit signals, background processes can be silently terminated or hang across session compaction/restarts, and continuous polling creates unnecessary SQLite contention.
Native in-process event hooks and REST notification dispatch provide reliable, deterministic, real-time card state tracking without terminal subprocesses.

## What Changes

- Introduce `runtime_events.py` providing an `EventBus` pub/sub registry for synchronous and asynchronous card lifecycle state transitions (`card_created`, `card_claimed`, `card_blocked`, `card_review`, `card_completed`, `card_abandoned`).
- Implement `RESTNotifier` within `runtime_events.py` to dispatch card lifecycle event payloads to configured REST endpoints with timeout safety and error containment.
- Add bridge functions connecting Hermes Kanban lifecycle hooks (`kanban_task_completed`, `kanban_task_blocked`, `kanban_task_claimed`, `on_kanban_task_updated`) directly to the Crew runtime event dispatcher.
- Expose programmatic card subscription APIs allowing sessions, plugins, and desktop interfaces to register callbacks without spawning background terminal polling commands.
- Provide comprehensive unit tests verifying callback dispatch, completion notification, and error isolation under failed REST calls or subscriber exceptions.

## Capabilities

### New Capabilities
- `crew-runtime-events`: Native event-driven lifecycle hooks, in-process event bus, and REST notification dispatch for Crew card state transitions.

### Modified Capabilities

## Impact

- **Affected Code**:
  - `O:/workspaces/oss/crew/runtime_events.py` (new runtime event engine).
  - `O:/workspaces/oss/crew/tests/test_runtime_events.py` (new unit and integration test suite).
  - `O:/workspaces/oss/crew/__init__.py` (hook registration points).
- **APIs**: Exposes `EventBus`, `Event`, `RESTNotifier`, `emit_card_event`, `handle_kanban_lifecycle_event`.
- **Dependencies**: Uses Python standard library (`urllib.request`, `json`, `dataclasses`, `logging`, `typing`, `time`, `threading`). Zero new third-party dependencies.
- **Operational Invariants**: Preserves Zero-Checkout and Worktree Isolation invariants; no git branch switching on the live repository.
