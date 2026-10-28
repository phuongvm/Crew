# Tasks

## 1. Backend Session Capture & Graph Origin Verification (`scripts/crew_card.py` & `scripts/crew_graph.py`)

- [x] 1.1 Add `_live_session_get(name)` in `scripts/crew_card.py` that consults `gateway.session_context.get_session_env(name)` before falling back to `os.environ.get(name)`, wire `coordinator_id(session=None)` and `session_env(get=None)` to use `_live_session_get`, and update `run_plan` parent/close-out card headers to write `Coordinator: %s` with `discussion` instead of `current_profile()`; verify with a Python probe under `set_session_vars` and `pytest tests/test_crew_dashboard_customization.py`.
- [x] 1.2 Harden `scripts/crew_graph.py::find_origin_session` and `_Builder.branch` to validate candidate session IDs against `state.db` (`message_count > 0` and `source != "kanban"`), prefer `_origin_from_messages` when the stamped session ID is missing/0-message/contradicted by message evidence, inherit parent origin across `crew_card.ancestors(board_db, card_id)` for child/decomposed cards, and normalize `card_ev["coordinator"]` to `<origin_profile>/<origin_sid>`; verify that all 16 active cards on `O:\workspaces\_config\agent4070\hermes\kanban\boards\crew\kanban.db` resolve to valid `state.db` sessions.
- [x] 1.3 Add unit tests in `tests/test_crew_dashboard_customization.py` covering `ContextVar` session capture over poisoned `os.environ["HERMES_SESSION_ID"]`, `find_origin_session` recovery over phantom draft session IDs, and decomposed child card ancestor inheritance; verify `pytest tests/test_crew_dashboard_customization.py` passes.

## 2. Crew React UI Target Resolution, Desktop Stack Intent & Standalone Fallback (`ui/src/` & `dashboard/dist/index.js`)

- [x] 2.1 Add `cardChatTarget(card)` in `ui/src/card-format.ts` that resolves `{ profile, session }` from `card.coordinator` and falls back to `card.session_id` + `card.session_profile` (defaulting `profile` to `"default"` when empty), and update `ui/src/components/TopArea.tsx` and `ui/src/components/ActionBar.tsx` to use `cardChatTarget(card)`; verify by building bundles with `node ui/build.mjs`.
- [x] 2.2 Update `ui/src/components/CrewPage.tsx` to pass `{ profile, intent: 'stack' }` when invoking `sdk.host.openSession(session, ...)`, and update `ui/src/browser.tsx` to provide a standalone fallback `openChat` (opening `<hermes_chat_url>/chat?resume=<session>` or copying `@session:<profile>/<session>`); rebuild `desktop/plugin.js` and `scripts/crew_dashboard/app.js` with `node ui/build.mjs` and verify `node tests/desktop_action_checks.mjs` and `node tests/browser_checks.mjs` pass.
- [x] 2.3 Update `dashboard/dist/index.js` so `openChat(profile, session)` allows empty `profile`, omits `&profile=` when empty or matching the active dashboard profile, and navigates via SPA `window.history.pushState` + `PopStateEvent("popstate")` with `window.location.assign` fallback; verify with `pytest tests/test_crew_dashboard_embed.py tests/test_crew_dashboard_customization.py`.

## 3. Hermes Host Fixes & Live Runtime Sync (`O:\workspaces\oss\hermes-agent` & `O:\workspaces\_config\agent4070\hermes`)

- [x] 3.1 Update `O:\workspaces\oss\hermes-agent\apps\desktop\src\app\open-session.ts` so navigating the main `workspace` pane (`!focused`) reveals `workspace` (`revealTreePane('workspace')`) even when invoked from `route-tile:/crew`, and update `O:\workspaces\oss\hermes-agent\hermes_cli\web_server_chat.py` so `?profile=default` on the serving profile keeps `profile_dir = None` and preserves `HERMES_TUI_GATEWAY_URL`; verify with unit/regression checks.
- [x] 3.2 Sync updated `O:\workspaces\oss\crew` files (`scripts/`, `desktop/plugin.js`, `dashboard/dist/index.js`) to `O:\workspaces\_config\agent4070\hermes\plugins\crew\` and `O:\workspaces\_config\agent4070\hermes\desktop-plugins\crew\`, and run the full verification suite (`pytest` + `node tests/desktop_action_checks.mjs` + `node tests/browser_checks.mjs`).

## Workflow follow-up

- Run `/openspec-verify-change` to verify all implementation tasks against the spec scenarios.
- Archive the change only after explicit Commander approval.
