# Design

## Context

See `proposal.md` for motivation and `openspec/workspace/explorations/2026-10-28-crew-open-chat-button-exploration.md` for the full empirical audit across the 16 live cards in `O:\workspaces\_config\agent4070\hermes\kanban\boards\crew\kanban.db`.

The Crew plugin operates across two repositories (`O:\workspaces\oss\crew` and `O:\workspaces\oss\hermes-agent`) and three UI hosts:
1. **Hermes Desktop** (`desktop/plugin.js` built from `ui/src/desktop.tsx`), where Crew mounts inside the center dock as `route-tile:/crew` (`asTile: true`).
2. **Hermes Web Dashboard** (`dashboard/dist/index.js` + `scripts/crew_dashboard/app.js` built from `ui/src/browser.tsx`), where Crew mounts at `/crew` and chat sessions run at `/chat?resume=<id>`.
3. **Standalone Crew Server** (`scripts/crew_graph_serve.py` serving `scripts/crew_dashboard/app.js` at `:8799`).

## Goals / Non-Goals

**Goals:**
- Capture the true per-turn `HERMES_SESSION_ID` from `gateway.session_context` when `crew_card_create` / `crew_plan_split` runs in-process inside a multiplexed gateway.
- Self-heal cards whose stored `session_id` / `Coordinator:` is empty, points to an unpersisted 0-message draft session, or was overwritten by a concurrent draft session at creation time, using `state.db` verification and ancestor inheritance in `crew_graph.py`.
- Resolve the chat target in `ui/src/` from both `card.session_id` / `card.session_profile` and `card.coordinator`.
- Make clicking "Open chat" in Hermes Desktop (`route-tile:/crew`) focus the existing chat tab or open a stacked session tab without clobbering active chats or staying hidden behind `route-tile:/crew`.
- Make clicking "open chat ↗" in Hermes Web Dashboard transition via SPA routing without dropping `HERMES_TUI_GATEWAY_URL`, and restore the standalone browser fallback.

**Non-Goals:**
- Mutating historical rows in `kanban.db` via destructive SQL migrations (runtime verification in `crew_graph.py` repairs the resolved payload non-destructively for all existing cards).

## Decisions

### Decision 1: ContextVar-First Session Lookup in `scripts/crew_card.py`
- **Choice**: Introduce `_live_session_get(name: str) -> str` in `scripts/crew_card.py` that checks `gateway.session_context.get_session_env(name)` first (when `gateway` is importable in-process) and falls back to `os.environ.get(name) or ""`. Default both `coordinator_id(session=None)` and `session_env(get=None)` to use `_live_session_get`. Also fix `run_plan` (lines 1699, 1722) to pass `discussion` instead of `current_profile()` into the `Coordinator: %s` header of parent and close-out cards.
- **Rationale**: In `tui_gateway` / `serve`, `AIAgent.__init__` mutates `os.environ["HERMES_SESSION_ID"]` globally whenever a blank draft session is pre-warmed, while the active turn's true session ID is isolated in `gateway.session_context`'s `ContextVar`. Reading `get_session_env` first in `crew_card.py` fixes every in-process caller (`native_tools.py`, `__init__.py`, etc.) at the single source of truth while remaining a no-op for CLI subprocess callers.

### Decision 2: `state.db`-Verified Origin Resolution & Ancestor Walk in `scripts/crew_graph.py`
- **Choice**:
  1. Add a helper `_valid_owner_session(sid: str, run_sessions: set[str]) -> tuple[str, str] | None` in `scripts/crew_graph.py` that rejects `sid` if it is in `run_sessions` or `sid.startswith("local-")` (worker execution sessions) or if `find_session_by_id(sid)` returns `None` or a session row with `(row[7] or 0) <= 0` (`message_count == 0`) or `row[2] == "kanban"`.
  2. In `find_origin_session(board_db, card_id, card_session_id=None, created_at=None)`:
     - Compute `msg_origin = _origin_from_messages(card_id, created_at, run_sessions)` (which finds the earliest non-worker session in `state.db` whose messages mention `card_id` within `ORIGIN_WINDOW_S`).
     - If `msg_origin[1]` is found, prefer `msg_origin` whenever the candidate `sid` (from `origin` event or `card_session_id`) is invalid/missing in `state.db` OR differs from `msg_origin[1]` (handling the case where `os.environ["HERMES_SESSION_ID"]` pointed to another active/draft session while `msg_origin` has the verbatim `Card open · <card_id>` tool output!).
     - If neither direct candidate nor direct `_origin_from_messages` yields a valid owner session, walk `crew_card.ancestors(board_db, card_id)` (`task_links` parents and `from_decompose_of` in `created` event) and recursively resolve the parent card's origin session.
  3. In `_Builder.branch` (`crew_graph.py:1642-1653`), if `origin_sid` is non-empty, set `card_ev["coordinator"] = f"{origin_profile or 'default'}/{origin_sid}"` whenever the raw `Coordinator:` body field is empty, lacks `/<session>`, or its `<session>` differs from the verified `origin_sid`.
- **Rationale**: Directly verified against all 16 active cards on the live `crew` board: this recovers 100% of poisoned cards (`t_af366f7b`, `t_d8403bb8`, `t_cf261bbd`, `t_ec873ef6`, `t_2ab730c4`, `t_4b49d8d4`, `t_b15e9e59`, `t_9b72dd40`, `t_36e2a0c0`) and all decomposed child cards (`t_1fbe2f7f`, `t_934a5e9f`, `t_655fca5e`, `t_643161e9`) without mutating SQLite rows.

### Decision 3: `cardChatTarget(card)` in `ui/src/card-format.ts`
- **Choice**: Add `cardChatTarget(card?: { coordinator?: string | null; session_id?: string | null; session_profile?: string | null } | null): { profile: string; session: string } | null` in `ui/src/card-format.ts`:
  - First check `coordinatorTarget(card?.coordinator)`.
  - If `coordinatorTarget` returns `null`, check `card?.session_id`: if it is a valid session ID (`!== 'no-session'` and matches `/^[A-Za-z0-9_-]{1,128}$/`), resolve `profile` from `card?.session_profile || coordinatorParts(card?.coordinator).profile || 'default'` and return `{ profile, session }`.
  - Wire `TopArea.tsx` and `ActionBar.tsx` to use `cardChatTarget(card)`.
- **Rationale**: Preserves backward compatibility with `coordinatorTarget` while ensuring cards with only `session_id` / `session_profile` always render a working button.

### Decision 4: Desktop `intent: 'stack'` & Main Pane Reveal (`ui/src/components/CrewPage.tsx` & `apps/desktop/src/app/open-session.ts`)
- **Choice**:
  1. In `ui/src/components/CrewPage.tsx:36`, invoke `openSession.call(host, session, { profile, intent: 'stack' })`.
  2. In `apps/desktop/src/app/open-session.ts:225`, when `!focused` (navigating the main `workspace` pane to a session not yet open), call `revealTreePane('workspace')` and `noteActiveTreeGroup(null)` unconditionally rather than gating on `frontMainIfSelected(storedSessionId)` (which fails synchronously before `HashRouter` processes the hash update).
- **Rationale**: `intent: 'stack'` is the canonical Desktop contract for opening a chat from outside the chat thread (used by Command Palette and Notifications). It focuses an existing tile/workspace tab if open, uses `workspace` if it is a blank draft, or opens a new stacked `session-tile` beside `route-tile:/crew` without clobbering an active conversation.

### Decision 5: Web Dashboard SPA Navigation & Serving-Profile Gateway Attachment (`dashboard/dist/index.js`, `ui/src/browser.tsx`, `hermes_cli/web_server_chat.py`)
- **Choice**:
  1. In `dashboard/dist/index.js`, allow `profile` to be empty or match `PROFILE_RE`, omit `&profile=` when `profile` is empty or `"default"`, and navigate via `window.history.pushState({}, "", url)` + `window.dispatchEvent(new window.PopStateEvent("popstate"))` (falling back to `window.location.assign(url)` only if `history.pushState` throws).
  2. In `hermes_cli/web_server_chat.py:523`, only resolve a secondary `profile_dir` when `_is_other_profile(requested)` is `True` (so `?profile=default` on the default dashboard keeps `profile_dir = None` and attaches `HERMES_TUI_GATEWAY_URL`).
  3. In `ui/src/browser.tsx`, provide a default `openChat` when `opts.openChat` and `window.__crewOpenChat` are absent: open `<hermes_chat_url>/chat?resume=<session>` via `window.open(..., "_blank", "noopener")` (and copy `@session:<profile>/<session>` to clipboard).

## Risks / Trade-offs

- **[Risk] `_origin_from_messages` SQLite scan cost on board load** → **Mitigation**: `board_data()` (`crew_graph_serve.py`) does NOT call `find_origin_session`; `find_origin_session` only runs inside `build_graph(card_id)` when viewing a single card's detail JSON (`/card/<id>.json`), where scanning `state.db` takes `< 15ms`.
- **[Risk] Rebuilding UI bundles (`desktop/plugin.js`, `scripts/crew_dashboard/app.js`)** → **Mitigation**: Run `node ui/build.mjs` in `O:\workspaces\oss\crew`, sync the built artifacts to `O:\workspaces\_config\agent4070\hermes\plugins\crew\` and `O:\workspaces\_config\agent4070\hermes\desktop-plugins\crew\`, and verify with `tests/desktop_action_checks.mjs`, `tests/browser_checks.mjs`, and `pytest`.
