# Proposal: Hermes Desktop Flow Graph Extension Pane via SandboxedFrame with Dual-Mode Tile Coexistence

## Why

Upstream maintainer `macd2` opened **Issue #10**: *"[Feature]: Hermes Desktop: crew's flow graph and card view inside the Desktop app"*, inviting a clean PR aligning Crew with native Hermes Desktop architecture.

Currently, our local fork implements Crew in Hermes Desktop as a full-window tile (`asTile: true`) connected to a background HTTP daemon on port 8799. While this provides immediate full-board visualization, it replaces the native Desktop Kanban and cannot serve remote backend topologies.

To transition gracefully without breaking daily operational workflows:
1. **Preserve Current Changes (Commander's Non-Negotiable Gate)**: The existing local tile (`asTile: true`) and daemon connectivity MUST remain 100% functional throughout the transition.
2. **Implement Upstream-Aligned Extension Pane**: Add a dedicated `PANES_AREA` layout pane rendering the live Flow Graph via the SDK's `<SandboxedFrame />` component, drawing data from the authenticated Gateway REST proxy (`/api/plugins/crew/card/<id>`).
3. **Pave the Way for Upstream PR 3**: Provide a clean, isolated PR that fulfills Issue #10 without regressing local invariants.

## What Changes

1. **Dual-Mode Registration in `desktop/plugin.js`**:
   - Maintain the existing `ROUTES_AREA` (`/crew`) and `SIDEBAR_NAV_AREA` (`asTile: true`) untouched.
   - Register a new contribution in `PANES_AREA` (`'panes'`):
     ```javascript
     {
       id: 'crew-flow-graph-pane',
       area: 'panes',
       title: 'Crew Flow Graph',
       data: { placement: 'right', width: '380px' },
       render: () => jsx(CrewFlowGraphPane, {})
     }
     ```
2. **Extension Pane Component (`CrewFlowGraphPane`)**:
   - Uses `SandboxedFrame` from `@hermes/plugin-sdk`.
   - Resolves the active card or board graph URL via the gateway proxy `/api/plugins/crew/card/...` using `window.hermesDesktop.getConnection()` or fallback.
   - Renders with opaque sandbox isolation, preventing script escapes or token leakage into the embedded frame.
3. **Gateway Proxy Endpoint Support (`dashboard/plugin_api.py`)**:
   - Verify that `/api/plugins/crew/card/{card_id}` and `/api/plugins/crew/board.json` properly format responses for `SandboxedFrame` rendering.

## Capabilities

### New Capabilities
- `desktop-flow-graph-pane`: Side-panel visualization of the Crew agent coordination graph inside Hermes Desktop using `SandboxedFrame`.

### Modified Capabilities
- `crew-desktop-integration`: Dual-mode support allowing both the full-window tile and the side extension pane to run concurrently.

## Impact

- **Affected Files**:
  - `desktop/plugin.js`: Dual-mode registration and `CrewFlowGraphPane` component.
  - `dashboard/plugin_api.py`: Route verification for sandboxed requests.
  - Unit tests in `tests/test_crew_dashboard_customization.py`.
- **Zero-Checkout Invariant**: Work executed in isolated worktree `O:\workspaces\.worktrees\wt-crew-desktop-pane`.
- **Local Invariant Preservation**: Local tile on port 8799 remains active; no breaking changes to existing setups.
