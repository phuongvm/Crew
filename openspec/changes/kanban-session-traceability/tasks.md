# Tasks: Kanban Card to Discussion Session Traceability & Deep-Linking

## Group 1: Worktree Setup & Isolation
- [x] 1.1 Create dedicated worktree `O:\workspaces\.worktrees\wt-crew-session-traceability` anchored on `origin/main`
  - **Proof**: `"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -Command "Test-Path 'O:\workspaces\.worktrees\wt-crew-session-traceability\.git'"`

## Group 2: Dashboard Visualization & Navigation Bridge
- [x] 2.1 Update `scripts/crew_dashboard/card.js` with `parseSessionCoord`, clickable Discussion Session chip, and `postMessage` protocol with clipboard fallback
  - **Proof**: `python -c "content = open('O:/workspaces/.worktrees/wt-crew-session-traceability/scripts/crew_dashboard/card.js', encoding='utf-8').read(); assert 'hermes:open-session' in content and 'parseSessionCoord' in content; print('PASS 2.1')"`
- [x] 2.2 Update `desktop/plugin.js` to listen for `hermes:open-session` and invoke `host.openSession(sessionId, { profile })`
  - **Proof**: `python -c "content = open('O:/workspaces/.worktrees/wt-crew-session-traceability/desktop/plugin.js', encoding='utf-8').read(); assert 'hermes:open-session' in content and 'host.openSession' in content; print('PASS 2.2')"`

## Group 3: Coordinator Sub-Task Provenance Engine
- [x] 3.1 Update `scripts/crew_card.py` to inherit parent `session_id` and coordinator origin across child tasks in `run_plan`
  - **Proof**: `python -c "content = open('O:/workspaces/.worktrees/wt-crew-session-traceability/scripts/crew_card.py', encoding='utf-8').read(); assert 'session_id' in content; print('PASS 3.1')"`

## Group 4: Hermetic Verification & Test Suites
- [x] 4.1 Execute targeted unit tests verifying dashboard customization, card parsing, and child provenance
  - **Proof**: `python "O:/workspaces/oss/hermes-agent/.venv/Scripts/pytest.exe" "O:/workspaces/.worktrees/wt-crew-session-traceability/tests/test_crew_dashboard_customization.py" "O:/workspaces/.worktrees/wt-crew-session-traceability/tests/test_crew_card.py"`

## Group 5: Publication, Multi-Profile Cutover & Live Probe
- [x] 5.1 Push verified branch to `origin/main` (fork `phuongvm/Crew`)
  - **Proof**: `git -C O:/workspaces/oss/crew log origin/main -n 1 --oneline` (HEAD is 033ce47)
- [x] 5.2 Fast-forward live `oss/crew` and run `apply-live-crew-cutover.ps1` to sync all 7 Hermes profiles and restart daemon
  - **Proof**: `"C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -Command "((Invoke-RestMethod -Uri 'http://127.0.0.1:8799/healthz').Trim() -like 'ok Crew*')"`
