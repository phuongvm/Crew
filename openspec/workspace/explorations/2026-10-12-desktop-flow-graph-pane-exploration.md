# Exploration: Hermes Desktop Flow Graph Extension Pane via SandboxedFrame with Dual-Mode Tile Coexistence

- **Date**: 2026-10-12
- **Target Project**: `oss/crew` (with `apps/desktop` Hermes Plugin SDK)
- **Scope**: Hermes Desktop integration, Upstream Issue #10 alignment, Dual-mode coexistence (`asTile: true` alongside Extension Pane), SandboxedFrame, Gateway API proxying
- **Invariants**: CREW-INV-1..6 (Zero-Checkout, preserve existing local tile until transition complete)

---

## 1. Executive Summary & Objective

Upstream maintainer `macd2` opened **Issue #10**: *"[Feature]: Hermes Desktop: crew's flow graph and card view inside the Desktop app"*, inviting a fresh, clean PR that aligns with Hermes Desktop architectural principles:
1. Do not replace the native Desktop Kanban board.
2. Render the Crew Flow Graph in a side extension pane using the SDK's `<SandboxedFrame />` component.
3. Eliminate client-side daemon auto-spawning on port 8799; route all graph and card queries through the authenticated Gateway plugin REST proxy (`/api/plugins/crew/`).
4. Support remote backends seamlessly without raw localhost port exposure.

### Commander's Invariant: Dual-Mode Coexistence
The Commander has established a strict transition invariant:
> **"When we change to this approach I don't want to lose current change (Local Tile)! We will only remove current change until new design are fully implemented."**

The local tile (`asTile: true`) on port 8799 MUST remain functional and accessible as the primary workspace view during Phase 1 & 2. The new Extension Pane (`PANES_AREA`) will be registered and mounted side-by-side, allowing direct visual comparison, validation, and zero disruption to daily workflows.

---

## 2. Grounded Codebase Audit & Architectural Seams

### 2.1 Hermes Desktop Plugin SDK Capabilities (`@hermes/plugin-sdk`)
Inspection of `oss/hermes-agent/website/docs/developer-guide/desktop-plugin-sdk.md` and `apps/desktop/src/sdk/index.ts` reveals:
1. **Contribution Areas**:
   - `ROUTES_AREA`: Full page routing (used by existing `/crew` route).
   - `SIDEBAR_NAV_AREA`: Sidebar button registration (used by existing `asTile: true` tile entry).
   - `PANES_AREA` (`'panes'`): Layout tree pane registration (`placement: 'right' | 'bottom'`, `dock`, `render: () => jsx(...)`).
2. **Component Security (`SandboxedFrame`)**:
   - `interface SandboxedFrameProps { src: string, title: string, sandbox?: string, className?: string, style?: CSSProperties }`
   - Opaque origin isolation: prevents embedded guest frames from touching Desktop window globals, tokens, or Electron bridge.
   - Enforces `loading="lazy"` and `referrerPolicy="no-referrer"`.
   - Allows only strict token allowlist: `allow-scripts`, `allow-forms`, etc.
3. **Gateway REST Proxy Seam (`dashboard/plugin_api.py`)**:
   - Already mounted in Hermes Agent core under `/api/plugins/crew/`.
   - Proxies `/card/{card_id}` (HTML/SVG flow graph) and `/card/{card_id}.json` (JSON graph nodes/edges).
   - Proxies `/board.json` and `/healthz`.

### 2.2 Dual-Mode Architectural Architecture in `desktop/plugin.js`
In `desktop/plugin.js`, `plugin.register(ctx)` can register multiple contributions simultaneously:
1. **Local Tile (Existing)**:
   - Route: `/crew` (renders `CrewPage` with iframe to `127.0.0.1:8799` or gateway board proxy).
   - Nav item: `{ codicon: 'organization', label: 'Crew', path: '/crew', asTile: true, order: 55 }`.
2. **Extension Pane (New)**:
   - Pane: `{ id: 'crew-flow-graph-pane', area: 'panes', title: 'Crew Flow Graph', data: { placement: 'right', width: '380px' }, render: () => jsx(CrewFlowGraphPane, {}) }`.
   - The pane extracts the active card from Kanban selection or displays live flow graph via `<SandboxedFrame src={graphUrl} title="Crew Flow Graph" />`.

---

## 3. Verification Criteria (Proof Gates)

1. **Gate 1 (Tile Invariant)**: The `/crew` local tile continues to launch and connect to `http://127.0.0.1:8799` without regressions.
2. **Gate 2 (Pane Invariant)**: The `crew-flow-graph-pane` renders in Hermes Desktop layout using `SandboxedFrame`, resolving graph endpoints via Gateway REST proxy `/api/plugins/crew/card/<id>`.
3. **Gate 3 (Test Suite 100%)**: All 197 unit and integration tests in `oss/crew/tests/` continue to pass with zero regressions.
