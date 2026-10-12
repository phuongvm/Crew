# Spec: Hermes Desktop Flow Graph Extension Pane

## Spec Summary
Adds a native Hermes Desktop extension pane (`PANES_AREA`) that embeds the Crew Live Flow Graph inside `<SandboxedFrame />` while preserving the existing full-tile view (`asTile: true`) on route `/crew`.

---

## REQUIREMENTS

### Requirement 1: Dual-Mode Plugin Registration
The Desktop plugin MUST register both the legacy tile contribution and the new extension pane contribution simultaneously.

#### Acceptance Criteria
- `desktop/plugin.js` registers:
  1. `ROUTES_AREA` for path `/crew` (rendering `CrewPage`).
  2. `SIDEBAR_NAV_AREA` with `asTile: true` and label `Crew`.
  3. `PANES_AREA` with `id: 'crew-flow-graph-pane'`, `placement: 'right'`, `title: 'Crew Flow Graph'`, and `data.hideOnly: true`.
- Disabling or closing the pane does NOT disable the tile, and vice versa.

### Requirement 2: SandboxedFrame Isolation
The extension pane component MUST embed the graph using `SandboxedFrame` from `@hermes/plugin-sdk`.

#### Acceptance Criteria
- Component imports `SandboxedFrame` directly from `@hermes/plugin-sdk`.
- `SandboxedFrame` is rendered with `title="Crew Flow Graph"` and strict sandbox posture (no raw `<webview>`, no direct token query strings).

### Requirement 3: Gateway Authenticated Proxy Resolution
The extension pane MUST construct graph URLs through the Hermes Gateway API proxy (`/api/plugins/crew/card/<id>`).

#### Acceptance Criteria
- When connected to a remote or local gateway, URLs resolve against `conn.baseUrl + '/api/plugins/crew/...'`.
- Local daemon port 8799 serves as transparent fallback when gateway connection is unauthenticated.

### Requirement 4: Test Suite Zero Regression Gate
All 197+ existing tests across `tests/` MUST continue to pass with 0 failures.
