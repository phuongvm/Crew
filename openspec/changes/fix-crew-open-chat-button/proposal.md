# Proposal

## Why

After the upstream merge to Crew `v0.9.11` / `v0.10.0+` (unified React UI in `ui/src/`), the **"Open chat" (`#act-chat`) / "open chat ↗" (`#cardCoOpen`) button** on the Crew card detail page fails across **Hermes Desktop**, **Hermes Web Dashboard**, and **standalone browser views**. Empirical diagnosis against the live `crew` Kanban board and `state.db` proved 5 interlocking regressions:
1. In-process `crew_card_create` / `crew_plan_split` (`scripts/crew_card.py` & `native_tools.py`) reads `os.environ.get("HERMES_SESSION_ID")` instead of `gateway.session_context.get_session_env("HERMES_SESSION_ID")`, stamping unpersisted 0-message draft session IDs (`AIAgent.__init__` side-effect) onto `Coordinator:` and `tasks.session_id`.
2. `scripts/crew_graph.py::find_origin_session` accepts unverified or 0-message session IDs without validating against `state.db` or walking `ancestors()` for child/decomposed cards, and `_Builder.branch` leaves `card.coordinator` unverified.
3. `ui/src/card-format.ts::coordinatorTarget`, `TopArea.tsx`, and `ActionBar.tsx` only inspect `card.coordinator` (`<profile>/<session>`) and ignore `card.session_id` and `card.session_profile`, hiding the button on decomposed child cards, `run_plan` parent/close-out cards, and CLI cards.
4. In Hermes Desktop (`ui/src/components/CrewPage.tsx` & `apps/desktop/src/app/open-session.ts`), opening a chat from the `route-tile:/crew` center tab (`asTile: true`) omits `intent: 'stack'` and fails to front/reveal the target chat tab cleanly.
5. In Hermes Web Dashboard (`dashboard/dist/index.js` & `hermes_cli/web_server_chat.py`) and standalone browser (`ui/src/browser.tsx`), upstream replaced SPA `pushState` navigation with a full reload that unconditionally appends `&profile=default` (causing `web_server_chat.py` to skip `HERMES_TUI_GATEWAY_URL`) and dropped the standalone `hermes_chat_url` fallback.

## What Changes

- **ContextVar-first session capture (`scripts/crew_card.py`)**: Add `_live_session_get(name)` in `crew_card.py` that consults `gateway.session_context.get_session_env(name)` before falling back to `os.environ.get(name)` across `coordinator_id()` and `session_env()`, and update `run_plan` parent/close-out card headers to write `Coordinator: <profile>/<session_id>` instead of bare `<profile>`.
- **Verified origin resolution & ancestor inheritance (`scripts/crew_graph.py`)**: Validate candidate session IDs against `state.db` (`message_count > 0` and non-worker `source != "kanban"`), cross-check against `_origin_from_messages()` when the stamped ID is missing, empty, or contradicted by message evidence, inherit parent origin across `crew_card.ancestors()` for decomposed/child cards, and reconcile `card_ev["coordinator"]` with the verified `(origin_profile, origin_sid)`.
- **Unified card chat target resolution (`ui/src/card-format.ts`, `TopArea.tsx`, `ActionBar.tsx`)**: Add `cardChatTarget(card)` that resolves `{ profile, session }` from verified `session_profile` / `session_id` and `coordinator` (falling back to `"default"` profile when only `session_id` is present), and wire both `#cardCoOpen` (`TopArea.tsx`) and `#act-chat` (`ActionBar.tsx`) through `cardChatTarget(card)`.
- **Desktop tab-aware session opening (`ui/src/components/CrewPage.tsx` & `apps/desktop/src/app/open-session.ts`)**: Pass `{ profile, intent: 'stack' }` when `CrewPage` invokes `sdk.host.openSession(session, ...)` so clicking "Open chat" from `route-tile:/crew` immediately focuses an open chat tab or opens a stacked session tab beside Crew without clobbering active chats, and ensure `open-session.ts` reveals `workspace` when navigating main.
- **Web Dashboard SPA navigation & standalone fallback (`dashboard/dist/index.js`, `ui/src/browser.tsx`, `hermes_cli/web_server_chat.py`)**: Restore SPA `history.pushState` + `PopStateEvent("popstate")` navigation in `dashboard/dist/index.js` (omitting redundant `&profile=` when empty or matching the serving profile), treat the serving profile as `profile_dir = None` in `hermes_cli/web_server_chat.py` so `HERMES_TUI_GATEWAY_URL` remains attached, and restore the `hermes_chat_url` / clipboard fallback in `ui/src/browser.tsx`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kanban-session-traceability`: Harden session capture against multiplexed gateway `os.environ` clobbering via `ContextVar` lookup, verify origin sessions against `state.db` (`message_count > 0`) and ancestor cards in `crew_graph.py`, resolve card chat targets from both `coordinator` and `session_id`/`session_profile` in the React UI, open Desktop sessions with `intent: 'stack'` from `route-tile:/crew`, and restore Web Dashboard SPA navigation plus standalone browser fallback.

## Impact

- **`O:\workspaces\oss\crew`**:
  - `scripts/crew_card.py` (`_live_session_get`, `coordinator_id`, `session_env`, `run_plan`)
  - `scripts/crew_graph.py` (`find_origin_session`, `_origin_from_events`, `_Builder.branch`)
  - `ui/src/card-format.ts`, `ui/src/components/TopArea.tsx`, `ui/src/components/ActionBar.tsx`, `ui/src/components/CrewPage.tsx`, `ui/src/browser.tsx`
  - Built bundles: `desktop/plugin.js`, `scripts/crew_dashboard/app.js`, and `dashboard/dist/index.js`
  - Tests: `tests/test_crew_dashboard_customization.py`, `tests/desktop_action_checks.mjs`, `tests/browser_checks.mjs`
- **`O:\workspaces\oss\hermes-agent`**:
  - `apps/desktop/src/app/open-session.ts`
  - `hermes_cli/web_server_chat.py`
- **Live Runtime (`O:\workspaces\_config\agent4070\hermes`)**:
  - Deployed Crew plugin bundles in `plugins/crew/` and `desktop-plugins/crew/`
