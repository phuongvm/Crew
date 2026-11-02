# Spec: Hermes Desktop Flow Graph Extension Pane

## Purpose
Adds a native Hermes Desktop extension pane (`PANES_AREA`) that embeds the Crew Live Flow Graph inside `<SandboxedFrame />` while preserving the existing full-tile view (`asTile: true`) on route `/crew`.

## Requirements

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

### Requirement 5: Crew Card Contract Tab Completeness
The Crew card detail view (`scripts/crew_graph.py` and `ui/src/components/Panel.tsx`) SHALL extract and render the complete contract specification—including `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, and `Proof command`—directly inside the default `Contract` tab of the `Coordinator · card` node.

#### Scenario: Reviewing a card displays Inputs and contract targets in the Contract tab
- **GIVEN** a Crew card whose body contains `GOAL:`, `Artifact:`, `Lands at:`, `Constraints:`, `Inputs:`, `Done when:`, and `proof command:`
- **WHEN** `crew_graph.build_graph()` builds the `card:<id>` node and `Panel.tsx` renders the `Contract` tab (`m.kind === 'card'`, `tab === 'Contract'`)
- **THEN** `card_ev` MUST contain `inputs` (preserving multiline quoted `> ` entries via `crew_card.contract_inputs`) and `constraints` (single-line `body_field` extraction; a multi-line `Constraints:` block exposes only its first line)
- **AND** the `Contract` tab `<dl>` MUST render `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, and `Proof command` as visible key-value rows without requiring the user to open `Details -> Raw fields`.

#### Scenario: Contract tab avoids duplicate 40+ character text with panel subtitle
- **GIVEN** a Crew card where `ev.goal` is identical to `card.card_title` (rendered in the `.ps` panel subtitle)
- **WHEN** `Panel.tsx` renders the `Contract` tab
- **THEN** `Goal` SHALL only be rendered as a separate `<dl>` row when the trimmed `ev.goal` differs from the trimmed `card.card_title`, preserving the panel's zero-duplicate-text invariant (`crew_panel_steps_proof.py`).
