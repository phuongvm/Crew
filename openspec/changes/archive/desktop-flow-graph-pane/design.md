# Design: Hermes Desktop Flow Graph Extension Pane & Dual-Mode Coexistence

## Architectural Overview

The integration follows a dual-mode coexistence pattern:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Hermes Desktop Workspace                        │
├──────────────────────────┬─────────────────────────────┬───────────────┤
│    Sidebar Navigation    │      Center Area            │   Right Pane  │
│                          │                             │               │
│ [Crew Tile Button] ─────┼────► /crew Route             │               │
│ (asTile: true)           │      (Full Board via        │               │
│                          │       Daemon :8799 or       │               │
│                          │       Gateway Proxy)        │               │
│                          │                             │               │
│ [Native Kanban Tab] ─────┼────► Standard Kanban View   │               │
│                          │      (Hermes Core Tasks)    │               │
│                          │             │               │               │
│                          │             ▼ Selection     │               │
│                          │                             │               │
│                          │       crew-flow-graph-pane ─┼───────────────┤
│                          │       (PANES_AREA)          │ SandboxedFrame│
│                          │                             │ (Live SVG     │
│                          │                             │  Flow Graph)  │
└──────────────────────────┴─────────────────────────────┴───────────────┘
```

## Component Architecture

1. **`CrewFlowGraphPane` Component (`desktop/plugin.js`)**:
   - Subscribes to active card changes or polls the active card ID.
   - Computes target graph URL: `withThemeQuery(base + '/api/plugins/crew/card/' + activeCardId)`.
   - Mounts `<SandboxedFrame src={graphUrl} title="Crew Flow Graph" className="crew-flow-pane" />`.
2. **`desktop/plugin.js` Registration**:
   ```javascript
   ctx.registerMany([
     { id: 'page', area: ROUTES_AREA, data: { path: '/crew' }, render: () => jsx(CrewPage, {}) },
     { id: 'nav', area: SIDEBAR_NAV_AREA, order: 55, data: { codicon: 'organization', label: 'Crew', path: '/crew', asTile: true } },
     { id: 'pane', area: PANES_AREA, title: 'Crew Flow Graph', data: { placement: 'right', width: '380px' }, render: () => jsx(CrewFlowGraphPane, {}) }
   ])
   ```
3. **Safety & Fallback**:
   - If the extension pane fails to load, the user can continue using the full tile on route `/crew`.
   - If port 8799 is offline, the pane gracefully displays connection status instead of crashing the Electron window.
