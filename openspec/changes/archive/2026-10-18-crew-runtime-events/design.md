# Design: Native Runtime Event Hooks & REST Notification Dispatch

## Context

Crew currently relies on spawning background terminal processes executing `python3 crew_card.py watch --card <id>` to track card completion and notify the parent session.
This mechanism is brittle:
- Notification regex wrappers can miss exit signals or be truncated.
- Long-running bash processes on Windows/MSYS are prone to silent termination or disconnection.
- Periodic polling (every 15s) generates repetitive SQLite queries.
- Desktop UI lag occurs because `desktop/plugin.js` polls `/board.json` on a 5000ms timer.

This design introduces `runtime_events.py`, implementing a lightweight, in-process, deterministic event bus and REST notification dispatcher for card state transitions.

## Goals / Non-Goals

**Goals:**
- Provide a clean in-process pub/sub event bus (`EventBus`) with subscriber error isolation.
- Support wildcard subscriptions (`*`) and targeted event kind subscriptions.
- Emit structured domain events for all primary card lifecycle transitions: `card_created`, `card_claimed`, `card_blocked`, `card_review`, `card_completed`, `card_abandoned`.
- Provide an extensible `RESTNotifier` that dispatches event JSON to remote/local endpoints (e.g. Gateway `/api/plugins/crew/events` or webhooks) with configurable timeout and error handling.
- Eliminate dependency on background terminal bash polling processes for session notifications.
- Maintain 100% backward compatibility with existing tests and scripts.

**Non-Goals:**
- Replacing SQLite as the source of truth for persistent Kanban state.
- Requiring an external message broker (RabbitMQ, Redis, Kafka) — all event dispatch must remain lightweight in-memory and HTTP-native.
- Immediately deleting `crew_watch.py` (it will remain as a legacy CLI fallback during transition).

## Architecture & Decisions

### 1. In-Process Event Bus (`EventBus`)
```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Event Lifecycle                                 │
│                                                                              │
│   Kanban Lifecycle Hook / crew_card.py                                       │
│                    │                                                         │
│                    ▼                                                         │
│          emit_card_event(kind, card_id, status, **payload)                   │
│                    │                                                         │
│                    ▼                                                         │
│          EventBus.publish(Event)                                             │
│          ┌───────────────────────┬───────────────────────┐                   │
│          ▼                       ▼                       ▼                   │
│   Subscriber (Sync)       Subscriber (Async)       RESTNotifier              │
│   (Session Turn Callback) (Audit Handler)        (POST /api/.../events)      │
│          │                       │                       │                   │
│          └───────────────┬───────┴───────────────────────┘                   │
│                          ▼                                                   │
│             Isolated Exception Handling                                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Decision D1: Dedicated `Event` Data Structure**
  An immutable `Event` dataclass / namedtuple containing:
  - `event_id`: str (UUID)
  - `kind`: str (e.g., `card_completed`, `card_blocked`)
  - `card_id`: str
  - `status`: str
  - `timestamp`: float (time.time())
  - `payload`: dict
  *Rationale*: Immutable event objects ensure subscribers cannot mutate event data and cause side-effects for subsequent subscribers.

- **Decision D2: Fail-Safe Subscriber Error Isolation**
  Every callback invoked by `EventBus.publish()` is executed inside a `try/except` guard.
  *Rationale*: A misbehaving subscriber or transient exception must never abort subsequent subscribers or crash the core transaction.

- **Decision D3: REST Notification Dispatcher (`RESTNotifier`)**
  A dedicated dispatcher component that translates `Event` instances into HTTP POST requests using standard Python libraries (`urllib.request`), supporting:
  - Custom target URL(s)
  - Authentication headers (Bearer tokens or session tokens)
  - Configurable network timeout (default 2.0s)
  - Circuit-breaker / error suppression for offline endpoints
  *Rationale*: Standard library implementation avoids introducing heavyweight HTTP client dependencies (like `requests` or `aiohttp`) into the core plugin.

- **Decision D4: Bridge Functions for Core Hooks**
  `handle_kanban_lifecycle_event(event_name, task_id, **fields)` maps Hermes Kanban DB hooks:
  - `kanban_task_completed` -> `card_completed`
  - `kanban_task_blocked` -> `card_blocked`
  - `kanban_task_claimed` -> `card_claimed`
  - `on_kanban_task_updated` -> `card_updated`
  *Rationale*: Seamlessly bridges Hermes platform events into Crew domain events without requiring changes to Hermes core.

## Risks / Trade-offs

- **[Risk] REST Notification Latency**: Synchronous network calls to slow endpoints could delay the publisher.
  → *Mitigation*: Short default timeout (2.0s), optional background execution via thread pool or non-blocking dispatch, and exception suppression.
- **[Risk] In-Memory Event Loss on Gateway Crash**: In-memory callbacks do not survive hard process crashes.
  → *Mitigation*: Kanban DB remains the durable source of truth. Events are ephemeral signaling notifications; durable recovery falls back to querying the Kanban board state upon gateway restart.
- **[Risk] Duplicate Event Delivery**: If both REST notification and coordinator poll run simultaneously.
  → *Mitigation*: Event IDs and state tracking keys (similar to `notify-state.json`) ensure deduplication across delivery channels.
