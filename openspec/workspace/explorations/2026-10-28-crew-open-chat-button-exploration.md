# Exploration: Crew Plugin "Open chat" Button Regression Across Hermes Desktop & Hermes Dashboard

- **Date**: 2026-10-28
- **Target Project**: `crew` (`O:\workspaces\oss\crew`) & `hermes-agent` (`O:\workspaces\oss\hermes-agent`)
- **Methodology**: `/openspec-explore` + Matt Pocock's `diagnosing-bugs` (Empirical Root-Cause Reproduction)
- **Status**: Explore Complete — Ready for OpenSpec Change Proposal

---

## 1. Executive Summary & Context

Previously, in commits `033ce47`, `1ca4b4b`, and `7626d07` (OpenSpec `kanban-session-traceability`), we implemented end-to-end traceability from every Crew Kanban card back to its originating discussion session across **Hermes Desktop**, **Hermes Web Dashboard**, and **standalone browsers**.

Subsequently, upstream (`macd2/Crew`) adopted the idea in `527598a` / `beeaa6d` (`crew 0.9.11`) and then replaced the legacy DOM dashboard with a unified React UI in `9205333` (`crew 0.10.0`), rendering:
- `<Button id="act-chat">Open chat</Button>` inside `ActionBar.tsx` on **Hermes Desktop**
- `<button id="cardCoOpen">open chat ↗</button>` inside `TopArea.tsx` on **Hermes Web Dashboard**

Following the upstream merge into `O:\workspaces\oss\crew`, the **"Open chat" button either fails to open the originating chat, opens the wrong/blank session, fails to switch tabs, or fails to render at all** in both Hermes Desktop and Hermes Web Dashboard.

Using a `< 2s` deterministic reproduction probe against the live `kanban.db` (`O:\workspaces\_config\agent4070\hermes\kanban\boards\crew\kanban.db`), the 7 profile `state.db` files, and the Desktop/Dashboard UI code paths, we isolated **5 interlocking root causes** across 3 architectural layers.

---

## 2. Architecture & Failure-Point Map

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: CARD CREATION & GRAPH RESOLUTION (Python Backend)                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  [Chat Turn in Session S_real (e.g. 20261028_130239_206c6f)]                           │
│   ├── ContextVar `HERMES_SESSION_ID` = "20261028_130239_206c6f" (TRUE session)         │
│   └── Process `os.environ["HERMES_SESSION_ID"]` = "20261028_151118_f84517"             │
│        ▲                                                                               │
│        └── Clobbered globally by `AIAgent.__init__` (`agent/agent_init.py:1093`)       │
│            whenever Desktop pre-creates an unpersisted 0-message draft session!        │
│                                                                                        │
│  ❌ ROOT CAUSE 1 (`native_tools.py:323` + `crew_card.py:747,1433`):                    │
│     `handle_crew_card_create` calls `crew_card.open_card()` in-process.                │
│     `coordinator_id()` and `session_env()` read `os.environ.get("HERMES_SESSION_ID")`  │
│     instead of `gateway.session_context.get_session_env("HERMES_SESSION_ID")`!         │
│     ──► Stamps `Coordinator: default/<ghost_draft_id>` & `tasks.session_id`!           │
│                                                                                        │
│  ❌ ROOT CAUSE 2 (`crew_graph.py:369-397, 1642-1653`):                                 │
│     `find_origin_session()` sees `card_session_id = <ghost_draft_id>` and returns      │
│     `("", <ghost_draft_id>)` immediately even when `find_session_by_id()` returns      │
│     `None` (not in any `state.db`) or `message_count == 0`, NEVER falling through      │
│     to `_origin_from_messages()` and NEVER walking `ancestors()` for child cards!      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: CARD PAGE TARGET RESOLUTION (`ui/src/card-format.ts`, `TopArea`, `ActionBar`) │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  ❌ ROOT CAUSE 3 (`card-format.ts:144`, `TopArea.tsx:55`, `ActionBar.tsx:124`):        │
│     Upstream replaced `discussionCoord(card)` with `coordinatorTarget(card.coordinator)`│
│     which ONLY parses `card.coordinator` (`<profile>/<session>`) and completely        │
│     ignores `card.session_id` and `card.session_profile`!                              │
│     ──► Decomposed child cards (`coord=""`), `run_plan` parent/close-out cards         │
│         (`Coordinator: default`), and cards whose true session was recovered by        │
│         `find_origin_session` either get `target = null` (no button) or use the        │
│         poisoned `card.coordinator` value!                                             │
└──────────────────────┬──────────────────────────────────────────┬──────────────────────┘
                       │                                          │
                       ▼                                          ▼
┌──────────────────────────────────────────┐ ┌───────────────────────────────────────────┐
│ LAYER 3A: HERMES DESKTOP (`CrewPage.tsx`)│ │ LAYER 3B: HERMES DASHBOARD (`index.js`)   │
├──────────────────────────────────────────┤ ├───────────────────────────────────────────┤
│                                          │ │                                           │
│ ❌ ROOT CAUSE 4:                         │ │ ❌ ROOT CAUSE 5:                          │
│ 1. Passing `<ghost_draft_id>` to         │ │ 1. `PROFILE_RE` rejects `profile === ""`  │
│    `host.openSession` hits 404 ->        │ │    when only `session_id` is known.       │
│    `goneSessionVerdict` == `'draft'` ->  │ │ 2. `window.location.assign("/chat?resume= │
│    resets main workspace to New Chat!    │ │    ...&profile=default")` forces a full   │
│ 2. Crew runs inside `route-tile:/crew`   │ │    page reload instead of SPA `pushState` │
│    (`asTile: true` in center dock).      │ │    + `popstate` (`1ca4b4b`).              │
│    `CrewPage.tsx:36` calls               │ │ 3. Appending `&profile=default` when      │
│    `host.openSession(s, { profile })`    │ │    `"default"` is already the serving     │
│    without `intent: 'stack'`. When       │ │    profile causes `web_server_chat.py:523`│
│    opening another session `S2`,         │ │    to set `profile_dir != None` and skip  │
│    `frontMainIfSelected('S2')` runs      │ │    `HERMES_TUI_GATEWAY_URL` (line 583)!   │
│    before async `hashchange` updates     │ │ 4. Standalone `:8799` (`browser.tsx:56`)  │
│    `$selectedStoredSessionId` (and       │ │    dropped the `hermes_chat_url` fallback │
│    `bootResumeRef` suppresses workspace  │ │    so `openChat` is `undefined`.          │
│    reveal), leaving `route-tile:/crew`   │ │                                           │
│    covering the screen or clobbering     │ │                                           │
│     the existing chat in `workspace`!     │ │                                           │
└──────────────────────────────────────────┘ └───────────────────────────────────────────┘
```

---

## 3. Empirical Reproduction & Live Database Audit (`diagnosing-bugs` Phases 1–3)

### 3.1 Reproduction Command (< 2s Deterministic Probe)

```bash
HERMES_HOME="O:/workspaces/_config/agent4070/hermes" python -c '
import os, sys
sys.path.insert(0, "O:/workspaces/oss/crew/scripts")
import crew_card, crew_graph, crew_graph_serve
from gateway.session_context import set_session_vars, clear_session_vars, get_session_env

REAL_SID = "20261028_130239_206c6f"
GHOST_DRAFT_SID = "20261028_151118_f84517"
tokens = set_session_vars(session_key=REAL_SID, session_id=REAL_SID, source="desktop", profile="default")
os.environ["HERMES_SESSION_ID"] = GHOST_DRAFT_SID
try:
    print("ContextVar:", get_session_env("HERMES_SESSION_ID"))
    print("coordinator_id():", crew_card.coordinator_id())
    print("session_env():", crew_card.session_env()["session"])
finally:
    clear_session_vars(tokens)
'
```

### 3.2 Actual Probe Output

```text
ContextVar: 20261028_130239_206c6f
coordinator_id(): default/20261028_151118_f84517
session_env(): 20261028_151118_f84517
```

### 3.3 Live Board Audit (`O:\workspaces\_config\agent4070\hermes\kanban\boards\crew\kanban.db`)

Running `crew_graph.build_graph()` across all **16 non-archived cards** on the live `crew` board and cross-checking against all 7 profile `state.db` files (`default`, `coder`, `designer`, `leader`, `qa`, `researcher`, `reviewer`) produced the following exact table:

| Card ID | Status | `g["coordinator"]` (What "Open chat" Currently Uses) | Exists in `state.db`? | True Originating Session in `state.db` (`_origin_from_messages` / Parent) | Failure Symptom When Clicking "Open chat" |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `t_d8403bb8` | `running` | `default/20261028_145813_756258` | Wrong session | `default/20261028_140136_77f67b` | Opens wrong chat (`145813` was an idle draft when `140136` created the card) |
| `t_af366f7b` | `done` | `default/20261028_151118_f84517` | **NO (`None`)** | `default/20261028_130239_206c6f` | **404 Session not found** -> resets to blank New Chat or dead click |
| `t_cf261bbd` | `done` | `default/20261028_104627_667587` | **0 msgs (`title=None`)** | `default/20261028_094029_0a5540` | Opens empty 0-message session instead of the real chat |
| `t_1fbe2f7f` | `done` | `""` (decomposed child of `t_2ab730c4`) | N/A | `default/20261028_084327_96fbde` | **Button missing (`target = null`)** |
| `t_934a5e9f` | `done` | `""` (decomposed child of `t_2ab730c4`) | N/A | `default/20261028_084327_96fbde` | **Button missing (`target = null`)** |
| `t_655fca5e` | `done` | `""` (decomposed child of `t_2ab730c4`) | N/A | `default/20261028_084327_96fbde` | **Button missing (`target = null`)** |
| `t_643161e9` | `done` | `""` (decomposed child of `t_2ab730c4`) | N/A | `default/20261028_084327_96fbde` | **Button missing (`target = null`)** |
| `t_ec873ef6` | `done` | `default/20261028_104322_5ba09f` | **NO (`None`)** | `default/20261028_094330_82ae4a` | **404 Session not found** |
| `t_2ab730c4` | `done` | `default/20261028_102544_8b22da` | **NO (`None`)** | `default/20261028_084327_96fbde` | **404 Session not found** |
| `t_4b49d8d4` | `done` | `default/20261028_101132_393112` | **NO (`None`)** | `default/20261028_094029_0a5540` | **404 Session not found** |
| `t_b15e9e59` | `done` | `default/20261028_092458_32e5b4` | **NO (`None`)** | `default/20261028_091704_ae6505` | **404 Session not found** |
| `t_9b72dd40` | `done` | `default/20261028_092458_32e5b4` | **NO (`None`)** | `default/20261028_091704_ae6505` | **404 Session not found** |
| `t_df56a1e8` | `done` | `default/20261028_084327_96fbde` | Yes (172 msgs) | `default/20261028_084327_96fbde` | Fails to switch focus from `route-tile:/crew` or reloads Dashboard with `profile_dir != None` |
| `t_36e2a0c0` | `done` | `default/20261025_145327_74816a` | Wrong session | `default/20261028_062415_6d5f05` | Opens 3-day-old session `20261025_145327_74816a` instead of `20261028_062415_6d5f05` |
| `t_10c10af2` | `done` | `default/20261025_145327_74816a` | Yes (107 msgs) | `default/20261025_145327_74816a` | Fails to switch focus from `route-tile:/crew` or reloads Dashboard with `profile_dir != None` |
| `t_2fd518a0` | `done` | `""` | N/A | `default/20261019_142500_4703fd` | **Button missing (`target = null`)** |

**Summary of Live Board Impact**: **14 out of 16 active cards (87.5%)** on the board have a missing, non-existent, or wrong session target due to Root Causes 1–3, and the remaining 2 cards hit the UI/routing defects in Root Causes 4–5!

---

## 4. Detailed Root-Cause Breakdown & Remediation Design

### 4.1 Root Cause 1: ContextVar-Aware Session Resolution at Card Creation (`scripts/crew_card.py` & `native_tools.py`)
- **Problem**:
  - `crew_card.py::coordinator_id(session=None)` (line 740) and `crew_card.py::session_env(get=None)` (line 1428) read `os.environ.get("HERMES_SESSION_ID")`.
  - When `native_tools.py::handle_crew_card_create` (or `handle_crew_plan_split`) runs in-process inside the multiplexed gateway, `os.environ["HERMES_SESSION_ID"]` has been overwritten by `AIAgent.__init__()` for the latest pre-warmed draft session, whereas the turn's actual session ID lives in `gateway.session_context.get_session_env("HERMES_SESSION_ID")`.
  - Additionally, `crew_card.py::run_plan` (lines 1699, 1722) writes `Coordinator: %s` using `current_profile()` (`"default"`) instead of `discussion` (`"default/<session_id>"`) on parent and close-out cards.
- **Remediation**:
  1. In `scripts/crew_card.py`, add a helper `_live_session_get(name)` that consults `gateway.session_context.get_session_env(name)` first (when `gateway.session_context.session_context_engaged()` or non-empty) before falling back to `os.environ.get(name)`.
  2. Use `_live_session_get` by default in `coordinator_id(session=None)` and `session_env(get=None)`.
  3. In `scripts/crew_card.py::run_plan` (lines 1699, 1722), write `Coordinator: %s` using `discussion` (not bare `current_profile()`).

### 4.2 Root Cause 2: Verified Session Lookup & Ancestor Fallback in `scripts/crew_graph.py`
- **Problem**:
  - `find_origin_session(board_db, card_id, card_session_id=None, created_at=None)` (line 369) and `_origin_from_events` (line 339) accept `card_session_id` / `origin.session` even when `find_session_by_id(sid)` returns `(None, None, None)` (not in `state.db`) or when `row[7]` (`message_count`) is `0` (an unstarted draft session), and even when `_origin_from_messages(card_id, created_at, run_sessions)` proves a different session actually created the card!
  - Furthermore, `find_origin_session` does not walk parent/ancestor cards (`crew_card.ancestors(board_db, card_id)`) when a child card (`from_decompose_of` or `task_links`) has no owner session of its own, causing `_origin_from_messages` on decomposed child cards (`t_1fbe2f7f`) to match the `coder` worker session instead of the parent card's owner discussion session.
- **Remediation**:
  1. In `scripts/crew_graph.py`, validate candidate session IDs against `state.db` (`find_session_by_id(sid)` must find a row with `(message_count or 0) > 0` and `source != 'kanban'`) AND verify that `_origin_from_messages(card_id, created_at, run_sessions)` (which checks which non-worker session actually received the card creation output within `ORIGIN_WINDOW_S`) is preferred whenever the stamped `sid` is missing from `state.db`, has `0` messages, or disagrees with the session whose messages actually contain the card creation receipt!
  2. When a card is a child/decomposed card (`task_links` or `from_decompose_of` via `crew_card.ancestors(board_db, card_id)`), inherit the parent card's resolved origin session before scanning worker messages.
  3. In `_Builder.branch` (`crew_graph.py:1642-1653`), when `origin_sid` is resolved and `coordinator` is empty, lacks `/<session>`, or carries a dead/superseded session ID, normalize `card_ev["coordinator"]` to `"%s/%s" % (origin_profile or "default", origin_sid)` so both the `coordinator` field display and `card.coordinator` consumers always see the true discussion session.

### 4.3 Root Cause 3: Restore `discussionTarget(card)` in `ui/src/card-format.ts`, `TopArea.tsx`, and `ActionBar.tsx`
- **Problem**:
  - `TopArea.tsx:55` and `ActionBar.tsx:124` call `coordinatorTarget(card.coordinator)`, ignoring `card.session_id` and `card.session_profile`.
- **Remediation**:
  1. In `ui/src/card-format.ts`, extend `coordinatorTarget` (or add `cardChatTarget(card: Pick<CardJson, 'coordinator' | 'session_id' | 'session_profile'>)`) so that it:
     - Prefers a valid `<profile>/<session>` from `card.coordinator`, EXCEPT when `card.session_id` is a different valid session ID resolved by `crew_graph.py` (`session_profile` + `session_id`).
     - Falls back to `{ profile: card.session_profile || coordProfile || 'default', session: card.session_id }` whenever `card.coordinator` is empty or lacks a session ID (`"default"`, `"default/no-session"`).
  2. Use `cardChatTarget(card)` in both `TopArea.tsx` and `ActionBar.tsx`.

### 4.4 Root Cause 4: Hermes Desktop Tab/Tile Navigation (`ui/src/components/CrewPage.tsx` & `apps/desktop/src/app/open-session.ts`)
- **Problem**:
  - In Hermes Desktop, Crew is mounted as a center-dock route tile (`route-tile:/crew`, `asTile: true`).
  - `CrewPage.tsx:36` calls `openSession.call(host, session, { profile })` without `intent`, defaulting to `intent: 'in-place'`.
  - When `route-tile:/crew` is the active tab in the center group:
    - If `workspace` already holds an active chat `S1` and the user clicks "Open chat" for `S2`, `'in-place'` clobbers `S1` in `workspace` instead of opening/focusing `S2` as a tab (`intent: 'stack'`).
    - If `S2` is loaded into `workspace` via `navigate(sessionRoute(S2))`, `frontMainIfSelected(S2)` in `open-session.ts:226` checks `$selectedStoredSessionId.get()` synchronously before `HashRouter` processes the hash change, returning `false` and failing to call `revealTreePane('workspace')` immediately (and if `bootResumeRef.current` is `true`, `markSelectionRestore()` suppresses the async reveal too).
- **Remediation**:
  1. In `O:\workspaces\oss\crew\ui\src\components\CrewPage.tsx:36`, pass `{ profile, intent: 'stack' }`:
     ```ts
     const openChat = typeof openSession === 'function'
       ? (profile: string, session: string) => { void openSession.call(host, session, { profile, intent: 'stack' }) }
       : undefined
     ```
     With `intent: 'stack'`, clicking "Open chat" from the Crew tab:
     - Immediately fronts and focuses the chat's existing tab (`workspace` or `session-tile:<id>`) if it is already open on screen;
     - Uses `workspace` (and reveals it) if `workspace` is an empty draft;
     - Opens and fronts a new session tab (`session-tile:<id>`) in the center tab strip beside `[Chat 1]` and `[Crew]` if `workspace` is occupied by another chat!
  2. In `O:\workspaces\oss\hermes-agent\apps\desktop\src\app\open-session.ts:214-227`, when `focusedSessionNeedsRoute` navigates the main `workspace` pane (`!focused`), call `revealTreePane('workspace')` and `noteActiveTreeGroup(null)` so a route tile (`route-tile:/crew`) never masks a main-pane session navigation.

### 4.5 Root Cause 5: Hermes Web Dashboard SPA Navigation & Standalone Browser Fallback (`dashboard/dist/index.js` & `ui/src/browser.tsx`)
- **Problem**:
  - In `O:\workspaces\oss\crew\dashboard\dist/index.js:47-52`:
    1. `PROFILE_RE` requires non-empty `profile`, dropping clicks when `profile` is `""`.
    2. `window.location.assign(...)` forces a full page reload instead of SPA `history.pushState` + `PopStateEvent("popstate")`.
    3. Unconditionally appending `&profile=default` when the dashboard is already serving `default` causes `hermes_cli/web_server_chat.py:523` to set `profile_dir != None` and skip `HERMES_TUI_GATEWAY_URL` at line 583.
  - In `O:\workspaces\oss\crew\ui\src\browser.tsx:56-57`:
    Standalone browser pages (`:8799`) have neither `opts.openChat` nor `window.__crewOpenChat`, so `openChat` is `undefined` and the button is hidden instead of opening `card.hermes_chat_url` or copying `@session:<profile>/<session>`.
- **Remediation**:
  1. In `dashboard/dist/index.js`, allow optional `profile` (`""` or matching `PROFILE_RE`), omit `&profile=` when `profile` is empty or matches `window.__HERMES_DASHBOARD_PROFILE__ || "default"`, and navigate via SPA `history.pushState` + `new window.PopStateEvent("popstate")` with `window.location.assign` as fallback (matching `1ca4b4b` / `7626d07`).
  2. In `hermes_cli/web_server_chat.py:523`, treat `not _is_other_profile(requested)` the same as `"current"` (`profile_dir = None`) so `/api/pty?profile=default` on the default dashboard still attaches to `HERMES_TUI_GATEWAY_URL`.
  3. In `ui/src/browser.tsx`, provide a standalone fallback for `openChat` that opens `<hermes_chat_url>/chat?resume=<session>` in a new tab (when `hermes_chat_url` is present on the card) or copies `@session:<profile>/<session>`.
