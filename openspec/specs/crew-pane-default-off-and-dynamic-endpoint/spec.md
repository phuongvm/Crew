# Spec: Crew Desktop Pane Default OFF & Dynamic Dashboard Endpoint Detection

## Purpose
Establishes default minimized arrival posture for the Hermes Desktop FlowPane to optimize workspace screen real estate, and guarantees robust dynamic endpoint resolution for board and card detail links across Web Dashboard, Desktop, and network clients without hardcoded loopback fallbacks.

## Requirements

### Requirement: Desktop Flow Pane Arrival State
The Crew flow pane registered in Hermes Desktop SHALL arrive collapsed by default as a minimized rail tab.

#### Scenario: Flow pane default registration
- **GIVEN** Hermes Desktop loads the Crew plugin (`desktop/plugin.js`)
- **WHEN** the `flow` pane is registered into `PANES_AREA`
- **THEN** its contribution data SHALL specify `defaultCollapsed: true`
- **AND** the pane shell SHALL dock the pane in a collapsed state by default.

### Requirement: Dynamic Board Header Link
The Crew Board component SHALL dynamically detect and use the active dashboard endpoint instead of hardcoded loopback port 8799.

#### Scenario: Board rendered in remote web dashboard
- **GIVEN** the Crew Board component renders inside a browser
- **WHEN** resolving the top-right header `link`
- **THEN** it SHALL NOT default to `http://127.0.0.1:8799/` if accessed from a remote origin or web dashboard
- **AND** it SHALL detect `window.location.origin` (and `/plugins/crew` if hosted).

#### Scenario: Board rendered in Hermes Desktop
- **GIVEN** the Crew Board component renders inside Hermes Desktop
- **WHEN** resolving the top-right header `link`
- **THEN** it SHALL resolve using the active gateway connection base URL or configured public URL.

### Requirement: Dynamic Card Detail Link
The Crew Card Page component and all outward Python/UI card link producers SHALL provide dynamic link resolution for card details using the `/crew?card=<id>` query convention matching the dashboard endpoint, and clicking a shareable card link inside Hermes Desktop SHALL open the card inside the in-app Crew view.

#### Scenario: Card detail link resolution
- **GIVEN** the Crew Card Page component or backend message producer formats a shareable card URL
- **WHEN** resolving the link for `<id>`
- **THEN** the URL SHALL use the detected dashboard endpoint and format `<dashboard>/crew?card=<id>`
- **AND** clicking that link inside Hermes Desktop chat SHALL intercept the navigation in-app and display `<CardPage id="<id>" />` without launching an external browser.

### Requirement: Build Integrity
Frontend bundles SHALL build cleanly without TypeScript or packaging errors.

#### Scenario: Node build check
- **GIVEN** changes in `ui/src/`
- **WHEN** running `node ui/build.mjs --check`
- **THEN** the process SHALL exit with code 0 and verify byte-for-byte consistency.
