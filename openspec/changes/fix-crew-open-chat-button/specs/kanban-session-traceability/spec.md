# Spec Delta

## MODIFIED Requirements

### Requirement: Clickable Discussion Session in Card View
The Crew React card view (`ui/src/components/TopArea.tsx` and `ui/src/components/ActionBar.tsx`) SHALL render an interactive **Open chat** control (`#act-chat` in Desktop action bar and `#cardCoOpen` in Web/Browser situation header) whenever `cardChatTarget(card)` resolves a valid discussion session identifier from `card.session_id` / `card.session_profile` or `card.coordinator`.

#### Scenario: User clicks discussion session in Desktop embedded iframe
- **GIVEN** a card with `coordinator = "default/20261012_092737_07d8d5"` (or `session_id = "20261012_092737_07d8d5"`, `session_profile = "default"`) viewed within the Hermes Desktop Crew tab (`route-tile:/crew`)
- **WHEN** the user clicks the `#act-chat` ("Open chat") button
- **THEN** `ActionBar` MUST invoke `openChat("default", "20261012_092737_07d8d5")`
- **AND** `CrewPage` MUST call `sdk.host.openSession("20261012_092737_07d8d5", { profile: "default", intent: "stack" })`.

#### Scenario: User clicks discussion session in Web Dashboard embedded iframe
- **GIVEN** a card viewed within the Hermes Web Dashboard Crew tab (`/crew`)
- **WHEN** the user clicks the `#cardCoOpen` ("open chat ↗") button
- **THEN** `TopArea` MUST invoke `openChat(target.profile, target.session)` without throwing errors even when `target.profile` is empty or matches the serving profile.

#### Scenario: User clicks discussion session in standalone external browser
- **GIVEN** a card viewed on the standalone Crew HTTP server (`scripts/crew_dashboard/app.js`) where `window.__crewOpenChat` is not injected by a host shell
- **WHEN** the user clicks the `#cardCoOpen` ("open chat ↗") button
- **THEN** the application SHALL open `<hermes_chat_url>/chat?resume=<sessionId>` in a new tab via `window.open` when `hermes_chat_url` is available and copy `@session:<profile>/<session_id>` to the clipboard as fallback.

---

### Requirement: Desktop PostMessage Session Navigation Bridge
The Crew Desktop plugin (`ui/src/desktop.tsx` and `ui/src/components/CrewPage.tsx`) and Desktop host (`apps/desktop/src/app/open-session.ts`) SHALL navigate directly to the originating chat session and bring its tab to the front when invoked from the Crew center route tile (`route-tile:/crew`).

#### Scenario: Desktop plugin receives valid open-session message
- **GIVEN** Hermes Desktop has loaded `desktop/plugin.js` and the user is viewing a card inside `route-tile:/crew` (`asTile: true`)
- **WHEN** the user clicks `#act-chat` ("Open chat") for session `"20261012_092737_07d8d5"` on profile `"default"`
- **THEN** `CrewPage` MUST invoke `host.openSession("20261012_092737_07d8d5", { profile: "default", intent: "stack" })`
- **AND** if `"20261012_092737_07d8d5"` is already open in `workspace` or a `session-tile`, Desktop SHALL immediately reveal and focus that tab in front of `route-tile:/crew`
- **AND** if `"20261012_092737_07d8d5"` is not yet open and `workspace` holds another conversation, Desktop SHALL open and focus `"20261012_092737_07d8d5"` in a stacked session tab without overwriting the other conversation.

#### Scenario: Desktop plugin rejects malformed or unverified payloads
- **GIVEN** a card payload carrying an empty session, `"no-session"`, or an identifier outside `^[A-Za-z0-9_.-]+$`
- **WHEN** `cardChatTarget(card)` evaluates the payload
- **THEN** `cardChatTarget(card)` MUST return `null` and MUST NOT render `#act-chat` or invoke `host.openSession`.

---

### Requirement: Web Dashboard PostMessage Session Navigation Bridge
The Crew Web Dashboard plugin (`dashboard/dist/index.js`) and Web Dashboard PTY chat endpoint (`hermes_cli/web_server_chat.py`) SHALL navigate the dashboard SPA to `/chat?resume=<sessionId>` and attach to the active gateway session cleanly.

#### Scenario: Web dashboard receives valid open-session message
- **GIVEN** Hermes Web Dashboard has mounted the Crew page (`/crew`)
- **WHEN** the user clicks `#cardCoOpen` ("open chat ↗") for session `"20261012_092737_07d8d5"` and profile `"default"`
- **THEN** `dashboard/dist/index.js` MUST validate that `session` conforms to `^[A-Za-z0-9_-]{1,128}$` and optional `profile` is empty or conforms to `^[A-Za-z0-9_.-]{1,64}$`
- **AND** MUST transition the dashboard to `/chat?resume=20261012_092737_07d8d5` (appending `&profile=<profile>` only when `<profile>` is non-empty and differs from the dashboard's serving profile) using SPA history navigation (`window.history.pushState` + `PopStateEvent("popstate")`)
- **AND** `hermes_cli/web_server_chat.py` MUST treat the serving profile as `profile_dir = None` so `HERMES_TUI_GATEWAY_URL` remains attached.

#### Scenario: Web dashboard rejects messages from untrusted origins or malformed payloads
- **GIVEN** an `openChat(profile, session)` call with an invalid `session` or invalid `profile` (e.g. path traversal, whitespace, or shell characters)
- **WHEN** `dashboard/dist/index.js` processes the call
- **THEN** `dashboard/dist/index.js` MUST ignore the call without navigating.

---

### Requirement: Originating Session Auto-Discovery for External and Legacy Tasks
The backend card creator (`scripts/crew_card.py`) and graph builder (`scripts/crew_graph.py`) SHALL capture the active turn's `ContextVar` session ID at creation time and automatically verify or recover the true originating owner chat session from `state.db` when `tasks.session_id` or `Coordinator:` is missing, empty, or holds an unpersisted/poisoned draft session ID.

#### Scenario: Card created via CLI or external tooling without session metadata
- **GIVEN** a card in `kanban.db` whose `session_id` or `Coordinator:` is `NULL`, empty, `"no-session"`, absent from `state.db`, has `message_count == 0`, or disagrees with the non-worker session in `state.db` whose messages contain the card creation output within 15 minutes of creation
- **WHEN** `crew_graph.py` resolves the card's fields
- **THEN** `find_origin_session` SHALL recover the verified `(origin_profile, origin_sid)` from `state.db` (or ancestor cards)
- **AND** SHALL populate `session_id`, `session_profile`, and `coordinator = "<origin_profile>/<origin_sid>"` so the card renders a working Open chat button pointing to the true conversation.

#### Scenario: Card created in-process inside multiplexed gateway with draft session in os.environ
- **GIVEN** an active chat turn in session `"20261028_130239_206c6f"` bound via `gateway.session_context` while `os.environ["HERMES_SESSION_ID"]` has been overwritten by an unpersisted draft session `"20261028_151118_f84517"`
- **WHEN** `crew_card_create` or `crew_card.open_card` creates a card
- **THEN** `coordinator_id()` and `session_env()` MUST read `gateway.session_context.get_session_env("HERMES_SESSION_ID")` first and stamp `"default/20261028_130239_206c6f"` and `session_id = "20261028_130239_206c6f"`.

---

### Requirement: Child Task Session Provenance Inheritance
When a parent task is decomposed into child tasks via `crew_card.py plan`, `crew_plan_split`, or `auto-decomposer`, both parent/close-out cards and child tasks SHALL inherit and resolve the root task's originating discussion session.

#### Scenario: Coordinator decomposes plan into child tasks
- **GIVEN** a parent task originating from session `"default/20261028_084327_96fbde"`
- **WHEN** `crew_card.py::run_plan` creates parent/close-out/child cards or `auto-decomposer` creates child cards (`from_decompose_of` / `task_links`)
- **THEN** `run_plan` MUST write `Coordinator: default/20261028_084327_96fbde` on parent, child, and close-out cards
- **AND** `crew_graph.py::find_origin_session` MUST walk `crew_card.ancestors(board_db, card_id)` so child cards without an explicit owner session inherit `"default/20261028_084327_96fbde"` rather than matching the worker session that decomposed them.

---

### Requirement: Graceful Fallback for Legacy Tasks
The system SHALL handle legacy tasks for which no originating session exists in `kanban.db` or `state.db` without errors.

#### Scenario: Card lacks session identifier
- **GIVEN** a legacy Kanban card with `session_id = NULL`, no session in `coordinator`, and no matching message in `state.db`
- **WHEN** the Crew UI renders the card
- **THEN** `cardChatTarget(card)` SHALL return `null` and the UI SHALL omit the Open chat button cleanly without throwing JavaScript exceptions.
