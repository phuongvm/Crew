# Implementation Tasks: Hermes Desktop Flow Graph Extension Pane

## Task Breakdown

- [x] **Task 1: Isolate Worktree & Author Flow Graph Pane Component**
  - Path: `desktop/plugin.js`
  - Action: Import `SandboxedFrame` and `PANES_AREA` from `@hermes/plugin-sdk`. Create `CrewFlowGraphPane` component with safe fallback and theme sync. Register `pane` under `PANES_AREA` alongside existing `page` and `nav`.
  - Invariant: Zero-Checkout in worktree `.worktrees/wt-crew-desktop-pane`. Preserve `asTile: true` and `CrewPage`.
  - Proof: `"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -Command "Select-String -Path 'O:\workspaces\oss\crew\desktop\plugin.js' -Pattern 'PANES_AREA', 'SandboxedFrame' | Measure-Object | ForEach-Object { if ($_.Count -ge 2) { exit 0 } else { exit 1 } }"`

- [x] **Task 2: Author Integration Tests for Dual-Mode Registration**
  - Path: `tests/test_crew_dashboard_customization.py`
  - Action: Add test verifying `plugin.js` declares both `asTile: true` tile navigation and `PANES_AREA` pane contribution.
  - Proof: `"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -Command "& 'O:\workspaces\.venv\Scripts\pytest.exe' 'O:\workspaces\oss\crew\tests\test_crew_dashboard_customization.py' -k 'dual_mode or pane or tile'"`

- [x] **Task 3: Full Regression Verification Gate**
  - Path: `tests/`
  - Action: Run full test suite across all 40 test files to guarantee zero regressions.
  - Proof: `"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -Command "& 'O:\workspaces\.venv\Scripts\pytest.exe' 'O:\workspaces\oss\crew\tests\test_crew_dashboard_customization.py' 'O:\workspaces\oss\crew\tests\test_crew_card.py' 'O:\workspaces\oss\crew\tests\test_crew_graph.py'"`

- [x] **Task 4: Sync & Live Cutover Across All 7 Profiles**
  - Path: `_config/agent4070/hermes/services/apply-live-crew-cutover.ps1`
  - Action: Execute live cutover script, syncing updated `desktop/plugin.js` to all profile runtime targets and verifying daemon health.
  - Proof: `"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8799/healthz' -Method Get | ForEach-Object { if ($_ -match 'ok') { exit 0 } else { exit 1 } }"`

## Implementation Notes (t_90c1d96f, coder, 2026-10-12)

- Commit `0e4d981` on `feat/desktop-flow-graph-pane` (worktree `O:/workspaces/.worktrees/wt-crew-desktop-pane`),
  fast-forwarded into `oss/crew` main (local; not pushed).
- The pane registers with `data.hideOnly: true`: in Desktop, closing the *only* pane of a plugin disables the whole
  plugin (`closeTreePane` -> `setPluginEnabled(false)`), which would also remove the `/crew` tile. Hide-only turns
  Close into hide/show (tab menu, ⌘K), so the tile can't be lost through the pane.
- Frame src ladder: local backend -> `http://127.0.0.1:8799/card/<id>`; any gateway -> `<base>/api/plugins/crew/card/<id>?ticket=<ws-ticket>`
  (single-use); remote without a ticket -> the local daemon; else an in-pane message. `conn.token` is never put in a URL.
  The card list comes from `ctx.rest('/board.json')`, so the pane needs the backend's crew dashboard plugin (`plugin_api.py`).
- Task 3: the named gate files pass, 203/203. The full suite has failures that were already there and are unchanged by
  this change (baseline on 11b2de4 and after 0e4d981 give identical per-file results, apart from +6 passing dual-mode tests).
- Task 4: `apply-live-crew-cutover.ps1 -SkipRepoSync -NoRestart`, 7 profiles at parity. Desktop must reload its plugins
  before the pane appears (Commander action).
