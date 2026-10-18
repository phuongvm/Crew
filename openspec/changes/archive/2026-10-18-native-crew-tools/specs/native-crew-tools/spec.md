# Spec: Native Hermes Tools for Crew Plugin

## ADDED Requirements

### Requirement: Native Card Creation Tool
The Crew plugin SHALL register a native Hermes tool named `crew_card_create` that programmatically creates a contract-guarded Kanban task without invoking external shell or CLI processes. The tool SHALL validate role contracts, enforce budget floors, and return structured card metadata.

#### Scenario: Agent creates a valid Crew card via tool
- **WHEN** an agent calls `crew_card_create` with a valid `title`, `role`, and contract details
- **THEN** the system MUST validate the contract against role constraints
- **AND** create the task record in the Kanban database
- **AND** return a JSON result containing the card `id`, `title`, `assignee`, and `status`.

#### Scenario: Agent submits invalid role or incomplete contract
- **WHEN** an agent calls `crew_card_create` with an unrecognized role or missing required contract fields
- **THEN** the system MUST return a structured error message detailing the missing or invalid contract fields
- **AND** no task record SHALL be created.

### Requirement: Native Diagnose Tool
The Crew plugin SHALL register a native Hermes tool named `crew_diagnose` that inspects and reports tasks across Kanban states (`blocked`, `triage`, `todo`, `ready`, `running`, `done`, `archived`) or evaluates a single card by identifier without invoking shell scripts.

#### Scenario: Agent diagnoses blocked cards
- **WHEN** an agent calls `crew_diagnose` with `state="blocked"`
- **THEN** the system MUST query the Kanban database in read-only mode
- **AND** return the list of matching cards, including their ID, status, wait duration, failure counts, spend, and coordinator decisions.

#### Scenario: Agent inspects specific card id
- **WHEN** an agent calls `crew_diagnose` with a specific `card_id`
- **THEN** the system MUST locate and return the diagnostic state for that specific card regardless of its current state.

### Requirement: Native Verdict Tool
The Crew plugin SHALL register a native Hermes tool named `crew_verdict` that executes the owner-confirmed proof command for a card, performs safety preflight verification, records an immutable verdict event, and enforces rework limits.

#### Scenario: Verifier executes owner-confirmed proof command
- **WHEN** a verifier agent calls `crew_verdict` for a card with an owner-confirmed proof command
- **THEN** the system MUST validate the proof command against Hermes safety constraints
- **AND** execute the command within the specified timeout and working directory
- **AND** record the PASS or FAIL verdict in the card's history
- **AND** return the execution exit code, duration, raw output, and verdict result.

#### Scenario: Proof command blocked by safety preflight
- **WHEN** `crew_verdict` is called for a card whose proof command violates safety policy or contains unsafe constructs
- **THEN** the command MUST NOT be executed
- **AND** the system SHALL return a status indicating the proof command was blocked.

### Requirement: Native Status Tool
The Crew plugin SHALL register a native Hermes tool named `crew_status` that returns a summarized view of in-flight cards, the coordinator's most recent decisions, and any questions requiring human owner input.

#### Scenario: Agent queries in-flight cards and decisions
- **WHEN** an agent calls `crew_status`
- **THEN** the system MUST retrieve active cards in flight (`triage`, `ready`, `running`, `blocked`, `review`)
- **AND** return a list of active cards with their status, assignee, last coordinator decision, and pending owner questions.

### Requirement: Plugin Tool Registration
The Crew plugin `oss/crew/__init__.py` SHALL register all four native tools (`crew_card_create`, `crew_diagnose`, `crew_verdict`, `crew_status`) under the `"crew"` toolset with their respective JSON schemas during plugin initialization (`register(ctx)`).

#### Scenario: Plugin initializes and registers crew tools with context
- **WHEN** the Hermes plugin loader executes `register(ctx)` for the Crew plugin
- **THEN** the plugin MUST invoke `ctx.register_tool` for each of the four native tools with valid schema descriptions and callable handlers.
