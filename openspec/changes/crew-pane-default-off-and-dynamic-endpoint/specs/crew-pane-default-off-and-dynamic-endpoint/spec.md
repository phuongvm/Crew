# Specification Delta: Crew Desktop Pane Default OFF & Dynamic Dashboard Endpoint Detection

## ADDED Requirements

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
The Crew Card Page component SHALL provide dynamic link resolution for card details matching the dashboard endpoint.

#### Scenario: Card detail link resolution
- **GIVEN** the Crew Card Page component renders in a browser or web dashboard
- **WHEN** formatting the shareable card URL
- **THEN** the URL SHALL use the detected dashboard endpoint and append `/card/<id>` (or hosted equivalent).

### Requirement: Build Integrity
Frontend bundles SHALL build cleanly without TypeScript or packaging errors.

#### Scenario: Node build check
- **GIVEN** changes in `ui/src/`
- **WHEN** running `node ui/build.mjs --check`
- **THEN** the process SHALL exit with code 0 and verify byte-for-byte consistency.
