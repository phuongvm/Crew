# Proposal: Kanban Card to Discussion Session Traceability & Deep-Linking

## Why

When orchestrating complex development across multiple parallel chat sessions and topics, the Commander frequently initiates tasks via `/crew`, `/crew-no-spec`, or Kanban decomposition. As tasks progress, cards may block (`blocked`), enter review (`review`), or fan out into multiple sub-tasks.

Currently, following up on these cards suffers from **Context Disconnection**:
1. When viewing a card on the Kanban board or Crew Dashboard, there is no direct link to the chat session where the task was originally discussed.
2. The user cannot easily recall *why* certain constraints were imposed, what specific instructions were given, or what nuances were explored.
3. Sub-tasks generated through coordinator decomposition lose the root discussion session ID, making multi-tier workflows opaque.

This proposal establishes a bidirectional traceability bridge between Kanban cards and their originating Hermes chat sessions, allowing the Commander to click directly on a card in the Crew Dashboard (or Hermes Desktop Tile) to navigate immediately back to the discussion session.

## What Changes

1. **Dashboard Visualization (`scripts/crew_dashboard/card.js`)**:
   - Update `sitFieldRow` and the card header to render a clickable **Discussion Session Chip** (`💬 default/20261012_... ↗`) instead of a plain copy-only string.
   - When clicked, dispatch a secure `postMessage` event to the parent window:
     ```javascript
     window.parent.postMessage({
       type: "hermes:open-session",
       sessionId: "<session_id>",
       profile: "<profile>"
     }, "*");
     ```
   - Provide standalone browser fallback: if `window.parent === window` (viewed in an external web browser), clicking copies `@session:<profile>/<id>` to clipboard and displays a toast notification.

2. **Desktop Tile Navigation Bridge (`desktop/plugin.js`)**:
   - In the Crew Desktop plugin, expand the `window.addEventListener('message')` listener to intercept `hermes:open-session`.
   - Validate payload integrity (alphanumeric `sessionId`, valid `profile`).
   - Call `host.openSession(sessionId, { profile })` from `@hermes/plugin-sdk` to switch the Desktop view from the CREW tab directly to the chat conversation.

3. **Sub-Task Provenance Inheritance (`scripts/crew_card.py`)**:
   - Update `run_plan` and sub-task creation routines so that child cards explicitly inherit the root task's `session_id` and coordinator origin.
   - Prevent child cards from overwriting the discussion session with transient worker session IDs.

4. **API Payload Alignment (`scripts/crew_graph_serve.py`)**:
   - Ensure `/card/<id>.json` and `/board.json` serialize `session_id` and qualified `coordinator` (`<profile>/<session_id>`) for consumption by `card.js`.

## Capabilities

### New Capabilities
- `kanban-session-traceability`: Deep-linking and provenance tracking between Kanban cards, sub-tasks, and Hermes chat sessions across Desktop and standalone browser surfaces.

### Modified Capabilities
- `crew`: Enhanced card visualization with interactive session navigation and sub-task session provenance inheritance.

## Impact

- **Affected Files**:
  - `scripts/crew_dashboard/card.js`
  - `desktop/plugin.js`
  - `scripts/crew_card.py`
  - `scripts/crew_graph_serve.py`
  - Unit tests in `tests/test_crew_dashboard_customization.py` and `tests/test_crew_card.py`
- **Zero-Checkout Invariant**: All implementation and testing must be performed in dedicated worktree `O:\workspaces\.worktrees\wt-crew-session-traceability`, leaving live `oss/crew` on `origin/main`.
- **Backward Compatibility**: Fully non-breaking. Cards lacking a `session_id` gracefully fall back to the existing coordinator display without errors.
