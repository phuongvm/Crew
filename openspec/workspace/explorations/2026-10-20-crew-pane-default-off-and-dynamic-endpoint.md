# Exploration: Crew Desktop Pane Default OFF & Dynamic Dashboard Endpoint Detection

- **Date**: 2026-10-20
- **Author**: Coordinator / default-agent4070
- **Project**: `crew` (`O:/workspaces/oss/crew`)
- **Target Seams**: `ui/src/desktop.tsx`, `desktop/plugin.js`, `ui/src/components/Board.tsx`, `ui/src/components/CardPage.tsx`, `scripts/crew_card.py`, `dashboard/plugin_api.py`

---

## 1. Problem Statement & Background

Following upstream merge `crew 0.10.0` (commit `9205333`), Crew transitioned to a unified React SPA built via `ui/build.mjs` serving:
1. **Hermes Desktop**: Embedded via `desktop/plugin.js` (compiled from `ui/src/desktop.tsx`).
2. **Hermes Web Dashboard**: Embedded via `dashboard/dist/index.js` (fetching `scripts/crew_dashboard/app.js` compiled from `ui/src/browser.tsx`).

The Commander identified three critical issues:
1. **Issue 1 (Desktop Pane Window Auto-Open)**: The right-hand `FlowPane` (`Crew flow`) opens automatically by default on Desktop startup, stealing 260px horizontal width from chat and workspaces. The Commander requests it to be toggled off / disabled by default.
2. **Issue 2 (Hardcoded 127.0.0.1:8799 Link)**: On the top right of the Crew board (and card detail), the header displays a link pointing to `http://127.0.0.1:8799/`. When accessed over network/remote gateway or within the Hermes dashboard, this link fails or routes to the client's local loopback. The Commander requests dynamic detection of the dashboard endpoint.
3. **Issue 3 (Standalone Dashboard)**: Confirmed with the Commander: Standalone daemon on port 8799 is retired in favor of the unified Hermes Desktop and Web Dashboard interfaces.

---

## 2. Root Cause Analysis

### Issue 1: Desktop Pane Default State
- In `ui/src/desktop.tsx` (lines 133–142):
  ```tsx
  {
    id: 'flow',
    area: PANES_AREA,
    title: 'Crew flow',
    data: { placement: 'right', width: '260px', hideOnly: true, collapsible: true },
    render: () => <Pane api={api} />
  }
  ```
- In Hermes Desktop's pane shell (`apps/desktop/src/components/pane-shell/tree/store.ts` line 1614–1618), newly registered panes check `dataOf(pane.id)?.defaultCollapsed`:
  ```ts
  for (const pane of missing) {
    if (dataOf(pane.id)?.defaultCollapsed) {
      setPaneCollapsed(pane.id, true)
    }
  }
  ```
- Because `ui/src/desktop.tsx` omitted `defaultCollapsed: true`, Hermes Desktop defaults to expanding the pane upon adoption. Adding `defaultCollapsed: true` ensures the pane arrives minimized on the right rail without user disruption.

### Issue 2: Hardcoded Loopback Link
- In `ui/src/components/Board.tsx` (lines 86 & 149–152):
  ```tsx
  const link = (board.dashboard_url || (typeof location !== 'undefined' ? location.origin : '')) + '/'
  ...
  <span className="node">
    {(board.node || '') + ' - kanban' + (board.board && board.board !== 'default' ? ' ' + board.board : '') + ' '}
    <a className="tailnet" href={link}>link</a>
  </span>
  ```
- In `scripts/crew_card.py` (lines 148–149):
  ```python
  def dashboard_url():
      ...
      return "http://127.0.0.1:%s" % (os.environ.get("CREW_GRAPH_PORT") or "8799")
  ```
- The backend `/board.json` automatically supplies `dashboard_url: "http://127.0.0.1:8799"`.
- Because `board.dashboard_url` is truthy, `Board.tsx` never evaluates `location.origin`. Consequently, `link` is always hardcoded to `http://127.0.0.1:8799/`.
- In Hermes Web Dashboard, `location.origin` (and path `/plugins/crew`) represents the actual accessible URL.
- In Hermes Desktop, Electron exposes `window.hermesDesktop.getConnection()` which provides the active gateway's `baseUrl` or port.
- On card detail (`CardPage.tsx`), there should likewise be a dynamic link or copy button for the card URL based on the detected endpoint.

---

## 3. Architectural Design & Proposed Solution

```
┌─────────────────────────────────────────────────────────────┐
│                       HERMES RUNTIME                        │
│                                                             │
│   ┌─────────────────────┐         ┌─────────────────────┐   │
│   │   Hermes Desktop    │         │ Hermes Web Dashboard│   │
│   │ (Electron / plugin) │         │ (Browser / gateway) │   │
│   └──────────┬──────────┘         └──────────┬──────────┘   │
│              │                               │              │
│   defaultCollapsed: true          Detect window.location    │
│   FlowPane arrives closed         origin + /plugins/crew    │
│              │                               │              │
│              ▼                               ▼              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │           Unified Crew React UI Components          │   │
│   │                                                     │   │
│   │   - Board.tsx: dynamic link resolution             │   │
│   │   - CardPage.tsx: dynamic card detail link          │   │
│   │   - desktop.tsx: defaultCollapsed: true             │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Remediation Steps:
1. **Desktop Pane Configuration**:
   - Update `ui/src/desktop.tsx`: Add `defaultCollapsed: true` to the `flow` pane registration in `PANES_AREA`.
2. **Dynamic Endpoint Detection in Frontend**:
   - In `ui/src/components/Board.tsx`:
     - If `typeof location !== 'undefined'` and `location.origin` is present, check whether `board.dashboard_url` is a dummy loopback (`127.0.0.1:8799` or `localhost:8799`). If so, prefer `location.origin + (hosted ? '/plugins/crew' : '/')`.
     - In Desktop context, query `window.hermesDesktop.getConnection()` to obtain `baseUrl` if remote, or fall back cleanly.
   - In `ui/src/components/CardPage.tsx`:
     - Provide the matching dynamic endpoint link for the specific card.
3. **Backend Fallback Hardening**:
   - In `scripts/crew_card.py`:
     - Inspect `~/.hermes/config.yaml` for `dashboard.public_url`. If defined, use it as `dashboard_url()`.
4. **Bundle Recompilation**:
   - Execute `node ui/build.mjs` to recompile `desktop/plugin.js` and `scripts/crew_dashboard/app.js`.
   - Verify with `node ui/build.mjs --check`.
5. **Runtime Synchronization**:
   - Deploy updated bundles to active profile runtime plugin directories:
     `_config/agent4070/hermes/plugins/crew/desktop/plugin.js`
     `_config/agent4070/hermes/plugins/crew/scripts/crew_dashboard/app.js`

---

## 4. Verification Plan

1. **Syntax & Bundle Verification**:
   - Run `node ui/build.mjs --check` -> Exit code 0.
2. **Automated Unit Tests**:
   - Test in `tests/test_crew_desktop_plugin.py` verifying `defaultCollapsed: true` in `desktop/plugin.js`.
   - Test in `tests/test_crew_dashboard_customization.py` verifying dynamic dashboard URL resolution.
3. **Zero-Checkout Enforcement**:
   - All code edits performed in isolated worktree `O:/workspaces/.worktrees/crew-pane-endpoint-fix`.
