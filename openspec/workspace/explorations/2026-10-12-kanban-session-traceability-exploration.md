# Exploration: Kanban Card to Original Discussion Session Traceability & Deep-Linking

- **Date**: 2026-10-12
- **Target Project**: `oss/crew` (with `apps/desktop` tile integration)
- **Scope**: Kanban task provenance, Discussion session deep-linking, Desktop Iframe postMessage bridge, Child task inheritance

---

## 1. Context & Motivation

When working across multiple topics, parallel tasks, and multiple AI agent sessions, the Commander frequently initiates tasks via `/crew`, `/crew-no-spec`, or direct Kanban decomposition. As work progresses, cards may become blocked (`blocked`), transition to review (`review`), or produce complex child tasks.

### The Problem: Context Disconnection
Currently, when viewing a card on the Kanban board or Crew Dashboard:
1. **Lost Discussion Context**: The user cannot easily determine *which conversation* gave birth to the task, what user preferences were voiced, what nuances were agreed upon, or why specific constraints were established.
2. **Proliferation of Sub-tasks**: Multi-agent fan-out and coordinator decomposition spawn subsequent child tasks. When a sub-task blocks or encounters difficulty, it is completely dissociated from the original discussion session.
3. **Manual Context Recovery**: To recover context, the user must manually search through hundreds of sessions in the sidebar or query databases, creating substantial cognitive friction.

### The Objective
Establish an end-to-end **Traceability & Deep-Linking Bridge**:
- Every Kanban card (root tasks and decomposed child tasks) carries verifiable provenance to the **Original Discussion Session**.
- On the Crew Dashboard (and Native Kanban Drawer), the card prominently displays a clickable **Discussion Session link/button**.
- Clicking the link seamlessly navigates the Hermes Desktop application directly to the originating chat session, immediately restoring the full discussion context.

---

## 2. Grounded Codebase Audit

### 2.1 What Already Exists (The Untapped Foundation)
1. **Database Schema (`kanban.db`)**:
   - The `tasks` table in SQLite (`_config/agent4070/hermes/kanban.db` and `boards/crew/kanban.db`) **already has a `session_id TEXT` column**.
   - Inspection of live task `t_c2c7ef05` proves `session_id` is populated at task creation time:
     ```sql
     SELECT id, title, session_id FROM tasks WHERE id = 't_c2c7ef05';
     -- Result: t_c2c7ef05 | Setup Crew Daily Upstream Sync Watchdog... | 20261012_092737_07d8d5
     ```
2. **Contract Body Metadata (`crew_card.py`)**:
   - The card body contract explicitly records the coordinator session in the header:
     ```text
     Coordinator: default/20261012_092737_07d8d5
     ```
3. **Desktop Plugin SDK Navigation API (`@hermes/plugin-sdk`)**:
   - `apps/desktop/src/sdk/index.ts` line 670/958 exports `host.openSession`:
     ```typescript
     host.openSession(storedSessionId: string, options?: PluginOpenSessionOptions): Promise<void>
     ```
   - This API instructs the Electron renderer to navigate directly to any stored session across profiles without page reloads.

### 2.2 What Is Missing (The Gaps)
1. **Crew Dashboard UI Gap (`scripts/crew_dashboard/card.js`)**:
   - `card.js` line 1031 renders the coordinator session purely as text with a clipboard copy button (`sitFieldRow(box, "coordinator", state.coordinator, {id: "cardCoCopy", ...})`).
   - It lacks an interactive link or action button to trigger session navigation.
2. **Iframe Communication Seam (`desktop/plugin.js`)**:
   - The Crew Desktop tile embeds the local HTTP dashboard (`http://127.0.0.1:8799/card/<id>`) inside an `<iframe>`.
   - The iframe cannot invoke Desktop renderer JavaScript directly. It requires a `postMessage` protocol.
   - While `desktop/plugin.js` listens for `hermes:theme` and `hermes:board-info`, it does not yet handle `hermes:open-session`.
3. **Child Task Provenance Inheritance (`crew_card.py` & `kanban_tools.py`)**:
   - When child cards are created via `crew_card.py plan` or coordinator sub-task spawning, the child task's `session_id` defaults to the transient worker process session rather than inheriting the root user discussion session.

---

## 3. Architecture & Data Flow

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. PLANNING PHASE (Chat Session)                                            │
│ User & Agent discuss requirements in Session: 20261012_092737_07d8d5        │
│ Command: /crew <ask> or /crew-no-spec <ask>                                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. CARD PROVENANCE CAPTURE (Database & Contract)                            │
│ - kanban_create records: session_id = '20261012_092737_07d8d5'              │
│ - Contract body records: Coordinator: default/20261012_092737_07d8d5         │
│ - Sub-task inheritance: Children inherit root session provenance            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. DASHBOARD VISUALIZATION (scripts/crew_dashboard/card.js)                 │
│ Renders clickable Discussion Session Chip:                                  │
│ [ 💬 Session: default/20261012_092737_07d8d5 ↗ ]                            │
│                                                                             │
│ User clicks the Chip ───► Emits window.parent.postMessage:                  │
│ { type: 'hermes:open-session', sessionId: '...', profile: 'default' }       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. DESKTOP TILE BRIDGE (desktop/plugin.js)                                  │
│ Listens for 'hermes:open-session' event from Iframe:                        │
│ └──► Calls host.openSession(sessionId, { profile })                        │
│                                                                             │
│ Result: Electron switches tab from CREW directly to the Chat Session!       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Key Invariants & Edge Cases

| Area | Challenge | Architectural Guarantee |
| :--- | :--- | :--- |
| **Iframe Security** | Malicious or untrusted iframe messages | Validate event data shape (`type === 'hermes:open-session'`), ensure `sessionId` conforms to alphanumeric regex `^[A-Za-z0-9_-]+$`, and only accept messages from allowed origin `http://127.0.0.1:*`. |
| **Profile Isolation** | Sessions belong to specific profiles | Always preserve qualified identity `<profile>/<session_id>` (e.g. `default/2026...`). Pass `profile` parameter to `host.openSession` to prevent cross-profile database lookups. |
| **Browser Fallback** | Dashboard viewed in Chrome/Edge, not Electron | If `window.parent === window` (standalone web browser) or `host.openSession` is unavailable, clicking copies `@session:<profile>/<id>` to clipboard and displays an informative toast: *"Session link copied. Open in Hermes Desktop to view"*. |
| **Sub-task Lineage** | Coordinator spawns child cards for workers | Child task creation in `crew_card.py plan` explicitly propagates `root_session_id` into child contract bodies and database rows. |
| **Zero-Checkout** | Modifying `oss/crew` code | All development and test verification must be executed in a dedicated worktree (`O:\workspaces\.worktrees\wt-crew-session-traceability`), leaving live `oss/crew` strictly clean on `main`. |

---

## 5. Implementation Seams

1. **`oss/crew/scripts/crew_dashboard/card.js`**:
   - Update `sitFieldRow` for coordinator/session to render a clickable link `<a>` with icon `💬` and class `session-jump-link`.
   - Add handler `openSessionInHermes(profile, sessionId)` that issues `postMessage` to parent window, with clipboard fallback.
2. **`oss/crew/desktop/plugin.js`**:
   - In `window.addEventListener('message', onMsg)`, add handler for `hermes:open-session`.
   - Invoke `host.openSession(data.sessionId, { profile: data.profile })`.
3. **`oss/crew/scripts/crew_card.py`**:
   - In `run_plan` and `open_card`, ensure child cards copy the parent's `session_id` and coordinator origin.
4. **`oss/crew/tests/`**:
   - Unit tests verifying contract parsing, session provenance preservation across children, and dashboard HTML rendering.
