# Spec: Kanban Card to Discussion Session Traceability & Deep-Linking

## Purpose
Provide bidirectional traceability and interactive navigation between Kanban cards, child tasks, and the originating Hermes chat session across Hermes Desktop and external browsers.

## Requirements

### Requirement: Clickable Discussion Session in Card View
The Crew Dashboard card view (`scripts/crew_dashboard/card.js`) SHALL render an interactive **Discussion Session** link or chip whenever the card carries a valid coordinator or discussion session identifier (`<profile>/<session_id>`).

#### Scenario: User clicks discussion session in Desktop embedded iframe
- **GIVEN** a card with `coordinator = "default/20261012_092737_07d8d5"` viewed within the Hermes Desktop CREW tab
- **WHEN** the user clicks the Discussion Session chip
- **THEN** `card.js` MUST emit `window.parent.postMessage({ type: "hermes:open-session", sessionId: "20261012_092737_07d8d5", profile: "default" }, "*")`
- **AND** the chip MUST provide visual click feedback.

#### Scenario: User clicks discussion session in standalone external browser
- **GIVEN** a card viewed in a standard web browser where `window.parent === window`
- **WHEN** the user clicks the Discussion Session chip
- **THEN** the application SHALL copy the formatted link `@session:default/20261012_092737_07d8d5` to the system clipboard
- **AND** SHALL display a toast notification informing the user that the session link was copied.

---

### Requirement: Desktop PostMessage Session Navigation Bridge
The Crew Desktop plugin (`desktop/plugin.js`) SHALL listen for `hermes:open-session` messages dispatched by the embedded dashboard iframe and invoke the Desktop SDK to navigate directly to the target session.

#### Scenario: Desktop plugin receives valid open-session message
- **GIVEN** Hermes Desktop has loaded `desktop/plugin.js` and mounted the CREW tile
- **WHEN** the embedded iframe posts `{ type: "hermes:open-session", sessionId: "20261012_092737_07d8d5", profile: "default" }`
- **THEN** `plugin.js` MUST validate that `sessionId` contains only valid identifier characters (`^[A-Za-z0-9_-]+$`)
- **AND** MUST invoke `host.openSession("20261012_092737_07d8d5", { profile: "default" })` from `@hermes/plugin-sdk`
- **AND** the Desktop view SHALL transition to the specified conversation without reloading the application window.

#### Scenario: Desktop plugin rejects malformed or unverified payloads
- **GIVEN** an arbitrary message event arriving from an untrusted origin or carrying an invalid `sessionId` (e.g. containing path traversal or shell characters)
- **WHEN** `plugin.js` processes the event
- **THEN** `plugin.js` MUST ignore the event and MUST NOT invoke `host.openSession`.

---

### Requirement: Child Task Session Provenance Inheritance
When a parent task is decomposed into child tasks via `crew_card.py plan` or coordinator sub-task spawning, the child tasks SHALL inherit the root task's `session_id` and coordinator origin.

#### Scenario: Coordinator decomposes plan into child tasks
- **GIVEN** a parent task with `session_id = "20261012_092737_07d8d5"` and coordinator `"default/20261012_092737_07d8d5"`
- **WHEN** `crew_card.py plan` or `kanban_create` generates child cards
- **THEN** each child card MUST inherit `session_id = "20261012_092737_07d8d5"` in its database record
- **AND** the child card's contract body MUST record `Coordinator: default/20261012_092737_07d8d5` (or explicit `Discussion-Session: default/20261012_092737_07d8d5`)
- **AND** the child card view SHALL display the discussion session link pointing to the original discussion session.

---

### Requirement: Graceful Fallback for Legacy Tasks
The system SHALL handle tasks created prior to this enhancement without errors.

#### Scenario: Card lacks session identifier
- **GIVEN** a legacy Kanban card with `session_id = NULL` and no session in `coordinator`
- **WHEN** the dashboard renders the card
- **THEN** the dashboard SHALL omit the discussion session chip or render a dimmed non-clickable badge
- **AND** no JavaScript exceptions SHALL be thrown.
