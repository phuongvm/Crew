# Exploration: Native Runtime Event Hooks Replacing Background Terminal Watchers

- **Date**: 2026-10-18
- **Target Project**: `oss/crew`
- **Scope**: Card lifecycle observation, runtime event dispatcher, REST notification hooks, desktop sync, elimination of background bash polling
- **Status**: Completed (Explore Phase)

---

## 1. Executive Summary & Context

Crew currently tracks card execution and completion by spawning unattended background polling scripts:
```python
terminal(
    background=True,
    notify_on_complete=True,
    command='sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py watch --card <id>',
)
```
While this mechanism allowed early CLI prototypes to wake up the originating session upon card completion, operational experience across multi-agent workflows has revealed severe reliability gaps:
1. **Notification Regex Fragility**: Hermes Agent wraps completed background processes in messages parsed by regex (`WATCH_REPORT_RX` in `__init__.py`). Variations in process wrapper formats, logging lines, or terminal output truncation cause regex match failures, leaving the session permanently unaware of task completion.
2. **Silent Process Eviction & Termination**: On Windows/MSYS and containerized environments, long-running background bash subprocesses can be silently pruned, terminated by shell idle timeouts, or killed during gateway/worker restarts without triggering `notify_on_complete`.
3. **Polling Overhead & SQLite Concurrency**: `crew_watch.py` polls `kanban.db` every 15 seconds for up to 24 hours. Under heavy multi-card workloads, dozens of concurrent polling processes contend for SQLite read access and WAL checkpointing.
4. **Session Boundary & Compaction Disconnect**: When a user session undergoes context compaction or switches active profiles, the child background process handle dissociates from the active session context, causing wake-up events to be delivered to dead or orphaned handles.
5. **Desktop & UI Lag**: Hermes Desktop (`desktop/plugin.js`) relies on client-side interval polling (`PANE_POLL_MS = 5000ms`) to detect card state changes, leading to stale UI state and delayed frame reloads.

To solve these issues at the root, Crew requires a **native runtime event-driven architecture** (`runtime_events.py`) that hooks directly into the Hermes Gateway/Plugin event lifecycle and exposes REST notification endpoints for real-time state transition dispatches.

---

## 2. Deep Dive: Current Architecture & Failure Modes

### 2.1 `scripts/crew_watch.py` & In-Session Watcher Loop
The in-session watcher executes `watch(db, tid, state_path, poll=15, lifetime=86400)`.
- It repeatedly connects to SQLite (`file:<db>?mode=ro`) and checks whether `crew_notify.card_reports()` yields an action item (`done`, `needs`, `abandoned`).
- For audit chains (cards that failed verification and spawned follow-up cards), `follow()` traverses up to `MAX_CHAIN = 6` parents.
- Upon finding an event, it marks `notify-state.json` and prints the report to `stdout`.
- The mechanism is strictly pull-based (polling) and entirely dependent on the terminal tool's background execution subsystem.

### 2.2 Proof Execution & `scripts/crew_safety.py`
- Proof execution in `crew_safety.py` runs through `run_proof(cmd, cwd, timeout, mode, card)`.
- Proof commands run under scrubbed environments (`proof_env()`) to avoid leaking bot tokens or gateway keys.
- Hash binding (`SCRIPT_CHANGED`) detects script mutations.
- Proof completion writes a verdict (`PASS`, `FAIL`, `PROOF_BLOCKED`) to disk via `crew_card.record_verdict()`.
- Currently, neither `run_proof` nor `cmd_verdict` emits a direct event; they simply write to disk and wait for the polling watcher or coordinator pass to discover the result.

### 2.3 Desktop Integration (`desktop/plugin.js` & `dashboard/plugin_api.py`)
- `dashboard/plugin_api.py` mounts REST routes on `/api/plugins/crew/` (e.g. `/board.json`, `/card/{id}`).
- `desktop/plugin.js` polls `/board.json` every 5 seconds to track active tasks.
- No push notification or webhook mechanism exists to notify the desktop pane or gateway listeners when a card transitions between `ready`, `in_progress`, `review`, and `done`.

---

## 3. Native Event Hook Architecture

### 3.1 Design Principles
1. **Zero Polling in Terminal**: Deprecate spawning background bash processes for card monitoring.
2. **In-Process Lifecycle Hooks**: Hook directly into Hermes Plugin hooks (`on_kanban_dispatch_tick`, `kanban_task_completed`, `kanban_task_blocked`, `kanban_task_claimed`, `on_kanban_task_updated`).
3. **Synchronous & Asynchronous Event Dispatch**: Support synchronous callbacks for critical invariant enforcement and asynchronous/REST notifications for external clients.
4. **State Transition Taxonomy**:
   - `CARD_CREATED`: Card enters board (`ready` / `triage`).
   - `CARD_CLAIMED`: Worker assumes card (`in_progress`).
   - `CARD_BLOCKED`: Card encounters block (`blocked` / `transient` / `needs_input`).
   - `CARD_REVIEW`: Card submitted for verification (`review`).
   - `CARD_COMPLETED`: Card passes verification and audit (`done`).
   - `CARD_ABANDONED`: Card closed without completion (`archived` / `failed`).
5. **REST Notification Dispatch**: Provide an HTTP/REST dispatcher capable of posting payloads to configured endpoints (e.g., local gateway `/api/plugins/crew/events`, webhooks, or desktop listeners) with payload signing and timeout guards.
6. **Graceful Degradation & Error Containment**: A failing listener or unreachable REST endpoint must never fail the underlying card transaction or crash the gateway.

### 3.2 Component Boundaries

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Crew Runtime                                    │
│                                                                              │
│  Kanban DB Events ──────►  runtime_events.py (EventBus)                      │
│  (commit hook)                  │                                            │
│                                 ├──────► Local Callbacks (In-Memory)         │
│  crew_card.py / verdict ────────┤        (e.g., session wake-up, audit)      │
│  (explicit emit)                │                                            │
│                                 ├──────► REST Notification Dispatcher        │
│  Coordinator Tick ──────────────┘        (POST /api/plugins/crew/events,     │
│                                           desktop, webhooks)                 │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technical Specifications for `runtime_events.py`

### 4.1 Core Primitives
1. **`Event` Data Class / NamedTuple**:
   - `event_id`: Unique UUID or sequential identifier.
   - `kind`: State transition kind (`card_completed`, `card_blocked`, `card_claimed`, `card_updated`, etc.).
   - `card_id`: Target Kanban task ID.
   - `status`: New status string (`done`, `blocked`, `in_progress`, etc.).
   - `timestamp`: Float Unix epoch timestamp.
   - `payload`: Arbitrary dictionary with event-specific context (summary, reason, reviewer, run_id).
2. **`EventBus` Class**:
   - Singleton or modular instance managing handler registration:
     - `subscribe(kind, callback)`: Subscribe to specific event types or `*` (all events).
     - `unsubscribe(kind, callback)`: Remove listener.
     - `publish(event)`: Dispatch event to registered callbacks safely.
     - `reset()`: Clear all listeners (essential for testing and reloads).
3. **`RESTNotifier` Class**:
   - Configurable target URL list (or single endpoint).
   - Async/thread-safe or non-blocking POST dispatch with timeout (default: 2.0s).
   - Basic retry policy with circuit-breaker behavior (suppress cascading network errors).
   - Auth header propagation (supports bearer tokens or custom headers).
4. **Convenience Bridge Functions**:
   - `emit_card_event(kind, card_id, status, **payload)`: High-level trigger called by `crew_card.py` or plugin hooks.
   - `handle_kanban_lifecycle_event(event_name, task_id, **fields)`: Translates Hermes core Kanban lifecycle hooks into Crew domain events.

---

## 5. Migration Strategy & Compatibility

1. **Dual-Path Transition**:
   - During rollout, `crew_watch.py` remains available for legacy CLI fallback.
   - `runtime_events.py` provides the canonical programmatic interface for in-session and gateway monitoring.
2. **Zero-Checkout & Git Worktree Invariant**:
   - All code changes reside strictly in the active repository checkout without changing git branches or creating checkout locks.
3. **Zero-Regression Assurance**:
   - All existing tests in `tests/test_crew_watch.py`, `tests/test_crew_card.py`, and `tests/test_crew_dashboard_customization.py` must continue passing.

---

## 6. Verification Plan

1. **Unit Tests (`tests/test_runtime_events.py`)**:
   - Test `EventBus` subscription, event publishing, wildcard handling, and unsubscription.
   - Test callback error isolation (exception in one handler does not abort subsequent handlers).
   - Test `emit_card_event` dispatch and payload integrity.
   - Test REST notification dispatch with mocked HTTP client (success, timeout, HTTP 500 error handling).
   - Test integration with Kanban task lifecycle translation.
2. **OpenSpec Validation**:
   - `openspec validate crew-runtime-events --strict` must return zero errors.
