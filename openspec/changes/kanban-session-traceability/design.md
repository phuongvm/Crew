# Design: Kanban Card to Discussion Session Traceability & Deep-Linking

## Architecture Overview

This design connects three loosely coupled layers in the Hermes ecosystem:
1. **The Core / Kanban Store** (`kanban.db` and `tools/kanban_tools.py`): Durable storage of `session_id` on task records.
2. **The Coordinator Engine** (`scripts/crew_card.py`): Provenance propagation and contract generation.
3. **The Presentation & Desktop Bridge** (`scripts/crew_dashboard/card.js` & `desktop/plugin.js`): Cross-frame event messaging and Electron navigation.

```text
┌──────────────────────────────────────────────────────────┐
│                   Hermes Desktop                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │ desktop/plugin.js (CREW Tile)                      │  │
│  │                                                    │  │
│  │  window.addEventListener('message', (e) => {       │  │
│  │    if (e.data.type === 'hermes:open-session') {    │  │
│  │      host.openSession(sessionId, { profile });     │  │
│  │    }                                               │  │
│  │  });                                               │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │ <iframe> http://127.0.0.1:8799/card/<id>     │  │  │
│  │  │                                              │  │  │
│  │  │ scripts/crew_dashboard/card.js               │  │  │
│  │  │                                              │  │  │
│  │  │ Click [ 💬 Session: default/2026... ↗ ]      │  │  │
│  │  │   └──► window.parent.postMessage(...)        │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Detailed Component Specifications

### 1. Iframe Communication Protocol (`scripts/crew_dashboard/card.js`)

In `card.js`, when rendering the situation box and header metadata:
- Introduce helper function:
  ```javascript
  function parseSessionCoord(str) {
    if (!str || typeof str !== 'string') return null;
    var parts = str.trim().split('/');
    if (parts.length === 2 && parts[1]) {
      return { profile: parts[0], sessionId: parts[1] };
    }
    return null;
  }
  ```
- Render the session row in `sitBox`:
  ```javascript
  var coord = parseSessionCoord(state.coordinator || state.session_id);
  if (coord) {
    var label = coord.profile + "/" + shortId(coord.sessionId);
    sitFieldRow(box, "discussion", label, {
      id: "cardSessionJump",
      icon: "💬",
      title: "Jump to discussion session in Hermes Desktop",
      onClick: function() {
        if (window.parent && window.parent !== window) {
          window.parent.postMessage({
            type: "hermes:open-session",
            sessionId: coord.sessionId,
            profile: coord.profile
          }, "*");
        } else if (navigator.clipboard) {
          navigator.clipboard.writeText("@session:" + coord.profile + "/" + coord.sessionId);
          showToast("Session link copied: @session:" + coord.profile + "/" + coord.sessionId);
        }
      }
    });
  }
  ```

### 2. Desktop Tile Bridge (`desktop/plugin.js`)

In `desktop/plugin.js`, expand the existing `window.addEventListener('message', onMsg)` hook:
```javascript
function onMsg(e) {
  if (!e || !e.data) return;
  if (e.data.type === 'hermes:board-info') {
    var name = String(e.data.board_name || e.data.board || '').trim();
    if (name) setBoardTitle(name);
  } else if (e.data.type === 'hermes:open-session') {
    var sid = String(e.data.sessionId || '').trim();
    var prof = String(e.data.profile || '').trim();
    // Validate session identifier characters to prevent injection
    if (/^[A-Za-z0-9_-]+$/.test(sid)) {
      if (host && typeof host.openSession === 'function') {
        host.openSession(sid, { profile: prof || undefined }).catch(function(err) {
          console.warn('[Crew] host.openSession failed:', err);
        });
      }
    }
  }
}
```

### 3. Sub-Task Provenance Engine (`scripts/crew_card.py`)

In `crew_card.py`:
- In `run_plan`: Extract `parent_session` from the parent card's `session_id` or `coordinator` string.
- When generating child cards:
  ```python
  child_spec["session_id"] = parent_session
  child_spec["coordinator"] = parent_coordinator
  ```
- In `kanban_create` calls for child tasks: pass `session_id=parent_session` so SQLite persists the link on the child row.

---

## Security & Boundary Invariants

1. **Origin & Message Sanitization**:
   - `postMessage` listeners strictly filter on `e.data.type === 'hermes:open-session'`.
   - `sessionId` is validated against `/^[A-Za-z0-9_-]+$/` before being passed to `host.openSession`.
2. **Zero-Checkout Compliance**:
   - Modifications are developed in dedicated worktree `O:\workspaces\.worktrees\wt-crew-session-traceability`.
   - Live checkout `O:\workspaces\oss\crew` remains on `origin/main`.
3. **No Breaking Changes**:
   - Cards without `session_id` continue to render gracefully.
   - Non-Desktop browsers fall back to clean clipboard copy with toast feedback.
