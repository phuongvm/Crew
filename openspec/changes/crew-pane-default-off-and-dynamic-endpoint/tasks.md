# Tasks: Crew Desktop Pane Default OFF & Dynamic Dashboard Endpoint Detection

- [ ] 1. Configure FlowPane to arrive collapsed by default <!-- id: task-1-pane-default-collapsed -->
  - **Description**: Add `defaultCollapsed: true` to `flow` pane registration in `ui/src/desktop.tsx`.
  - **Inputs**: `ui/src/desktop.tsx`, `apps/desktop/src/components/pane-shell/tree/store.ts`
  - **Proof**: `grep -q "defaultCollapsed: true" "ui/src/desktop.tsx"`

- [ ] 2. Implement dynamic dashboard endpoint detection <!-- id: task-2-dynamic-endpoint -->
  - **Description**: Update `ui/src/components/Board.tsx` and `scripts/crew_card.py` so that board and detail links resolve to the detected client origin/dashboard endpoint instead of defaulting to loopback `8799`.
  - **Inputs**: `ui/src/components/Board.tsx`, `scripts/crew_card.py`
  - **Proof**: `python -m pytest tests/test_crew_dashboard_customization.py -k "test_dashboard_url or test_endpoint" -v`

- [ ] 3. Rebuild frontend bundles and verify byte consistency <!-- id: task-3-rebuild-bundles -->
  - **Description**: Run `node ui/build.mjs` to regenerate `desktop/plugin.js` and `scripts/crew_dashboard/app.js`, then run `--check` to verify consistency.
  - **Inputs**: `ui/build.mjs`, `ui/src/`
  - **Proof**: `node ui/build.mjs --check`

- [ ] 4. Run full desktop and dashboard test suite <!-- id: task-4-run-tests -->
  - **Description**: Execute all existing and new unit tests to guarantee zero regressions.
  - **Inputs**: `tests/`
  - **Proof**: `python -m pytest tests/test_crew_desktop_plugin.py tests/test_crew_dashboard_customization.py -v`
