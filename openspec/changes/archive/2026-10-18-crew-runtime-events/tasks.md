# Implementation Tasks: Native Runtime Event Hooks

## 1. Event Bus and Core Primitives

- [x] 1.1 Implement immutable `Event` data class with JSON serialization in `runtime_events.py`
- [x] 1.2 Implement `EventBus` pub/sub registry supporting targeted and wildcard (`*`) subscriptions in `runtime_events.py`
- [x] 1.3 Implement subscriber exception isolation and listener unregistration mechanics

## 2. Card Domain Events and Bridge Integration

- [x] 2.1 Implement `emit_card_event` supporting `card_created`, `card_claimed`, `card_blocked`, `card_review`, `card_completed`, and `card_abandoned`
- [x] 2.2 Implement `handle_kanban_lifecycle_event` translating Hermes Kanban lifecycle hooks into Crew domain events

## 3. REST Notification Dispatcher

- [x] 3.1 Implement `RESTNotifier` with configurable endpoints, timeouts, and custom headers in `runtime_events.py`
- [x] 3.2 Implement network error containment and non-fatal logging for unreachable REST endpoints

## 4. Test Suite and Verification

- [x] 4.1 Author comprehensive test suite in `tests/test_runtime_events.py` covering event bus mechanics, callbacks, and error handling
- [x] 4.2 Author tests verifying card completion events and REST dispatch without background bash polling
- [x] 4.3 Validate OpenSpec change with `openspec validate crew-runtime-events --strict`
