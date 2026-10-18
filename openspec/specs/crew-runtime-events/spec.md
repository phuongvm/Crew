# crew-runtime-events Specification

## Purpose
TBD - created by archiving change crew-runtime-events. Update Purpose after archive.
## Requirements
### Requirement: In-Process Event Bus & Subscriber Lifecycle
The runtime MUST provide an in-process `EventBus` mechanism enabling synchronous and asynchronous subscriptions to card state events without terminal polling.

#### Scenario: Registering and dispatching specific event handlers
- **WHEN** a subscriber registers a callback for an event kind `card_completed`
- **THEN** the event bus MUST invoke the callback when a matching event is published
- **AND** the callback MUST receive the immutable `Event` object containing `card_id`, `kind`, `status`, and `payload`

#### Scenario: Wildcard event subscription
- **WHEN** a subscriber registers a callback for wildcard kind `*`
- **THEN** the event bus MUST invoke the callback for any event published across all event kinds

#### Scenario: Subscriber error isolation
- **WHEN** a registered subscriber raises an unhandled exception during event publication
- **THEN** the event bus MUST catch and log the exception
- **AND** the event bus MUST continue executing all other registered subscribers without crashing the caller

#### Scenario: Subscriber unregistration
- **WHEN** a subscriber unregisters from an event kind
- **THEN** subsequent publications of that event kind MUST NOT invoke the unregistered callback

---

### Requirement: Card State Transition Events
The runtime MUST emit standardized domain events upon card state transitions (`card_created`, `card_claimed`, `card_blocked`, `card_review`, `card_completed`, `card_abandoned`).

#### Scenario: Card completion event emission
- **WHEN** a card finishes execution and passes verification
- **THEN** the runtime MUST emit an event with kind `card_completed` and status `done`
- **AND** the payload MUST contain the execution summary and completion timestamp

#### Scenario: Card blocked event emission
- **WHEN** a card encounters an operational or verification failure
- **THEN** the runtime MUST emit an event with kind `card_blocked` and status `blocked`
- **AND** the payload MUST include the failure reason and blockage kind

#### Scenario: Card claimed event emission
- **WHEN** a worker agent claims a card for execution
- **THEN** the runtime MUST emit an event with kind `card_claimed` and status `in_progress`
- **AND** the payload MUST include the worker assignee and run ID

---

### Requirement: REST Notification Dispatcher
The runtime MUST support dispatching event notifications over HTTP/REST to configured endpoints without blocking core workflow execution.

#### Scenario: Successful REST notification delivery
- **WHEN** an event is published and a `RESTNotifier` is registered with a valid HTTP endpoint
- **THEN** the notifier MUST post a JSON-encoded payload containing event metadata to the target URL
- **AND** the dispatch MUST complete successfully within the configured timeout window

#### Scenario: REST endpoint network failure containment
- **WHEN** the target REST endpoint is unreachable, times out, or returns a 5xx status code
- **THEN** the notifier MUST capture the failure and log a diagnostic warning
- **AND** the failure MUST NOT interrupt the local event bus or raise an unhandled exception to the card runner

#### Scenario: Authorization header propagation
- **WHEN** the `RESTNotifier` is configured with an authorization token or custom headers
- **THEN** outgoing HTTP requests MUST include the configured headers in the request headers

