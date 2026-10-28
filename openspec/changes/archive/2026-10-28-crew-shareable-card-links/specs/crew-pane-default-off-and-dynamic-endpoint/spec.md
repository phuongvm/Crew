# Delta Spec: Crew Desktop Pane Default OFF & Dynamic Dashboard Endpoint Detection

## MODIFIED Requirements

### Requirement: Dynamic Card Detail Link
The Crew Card Page component and all outward Python/UI card link producers SHALL provide dynamic link resolution for card details using the `/crew?card=<id>` query convention matching the dashboard endpoint, and clicking a shareable card link inside Hermes Desktop SHALL open the card inside the in-app Crew view.

#### Scenario: Card detail link resolution
- **GIVEN** the Crew Card Page component or backend message producer formats a shareable card URL
- **WHEN** resolving the link for `<id>`
- **THEN** the URL SHALL use the detected dashboard endpoint and format `<dashboard>/crew?card=<id>`
- **AND** clicking that link inside Hermes Desktop chat SHALL intercept the navigation in-app and display `<CardPage id="<id>" />` without launching an external browser.
