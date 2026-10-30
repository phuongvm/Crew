# crew-role-prompts Specification

## Purpose
Define structured contract representations, tolerant Markdown parsing, bidirectional serialization, programmatic role specifications, and unified engineering/design/verification disciplines for all Crew specialist roles (`worker`, `content`, `verifier`, `coordinator`, `diagnose`).

## Requirements
### Requirement: Structured Contract Representation and Validation
The system SHALL provide structured contract models (`ContractCard`, `ContractGaps`, `Role`, `VerifyMode`, `ProofMode`) to represent and validate Crew task cards deterministically. Contract cards MUST enforce all required fields (`role`, `goal`, `artifact`, `lands`, `audience`, `done_when`, and `proof_cmd` unless explicitly exempted). The validation engine SHALL detect gaps, enforce the token budget floor, and identify proof script path collisions.

#### Scenario: Valid complete contract card validation
- **WHEN** a contract card contains valid non-empty values for role, goal, artifact, lands, audience, done_when, and proof_cmd
- **THEN** contract validation succeeds with zero gaps reported
- **AND** the token budget is defaulted or raised to meet the minimum budget floor.

#### Scenario: Missing required contract fields reported in deterministic order
- **WHEN** a contract card is evaluated with missing or whitespace-only required fields
- **THEN** the validation engine returns a list of gaps identifying each missing field in canonical contract order
- **AND** invalid role values are reported with accepted roles.

### Requirement: Tolerant Markdown Contract Parsing
The contract parser SHALL parse Markdown card bodies and extract all contract fields even when keys contain Markdown formatting (such as `**Key:**`, `*Key:*`, or backticks) or when field content spans multiple lines. Multiline fields (including `Done when:`, `Constraints:`, `Inputs:`, and `GOAL:`) MUST preserve indentation and bulleted continuation lines rather than truncating at the first newline.

#### Scenario: Markdown-decorated card body parsed accurately
- **WHEN** a card body formats field labels with markdown asterisks (e.g. `**Role:** worker` and `**GOAL:** implement feature`)
- **THEN** the parser strips markdown decorations and correctly maps values to their respective contract fields.

#### Scenario: Multiline Done when criteria preserved without truncation
- **WHEN** a card body specifies a `Done when:` field containing multiple lines or bullet points
- **THEN** the parser preserves the complete multiline criteria in the `done_when` attribute of the contract card.

### Requirement: Bidirectional Serialization (JSON and Canonical Markdown)
The contract system SHALL support bidirectional conversion between structured `ContractCard` instances, JSON representations, and canonical Markdown card bodies. Deserializing a rendered canonical Markdown body or JSON payload MUST reconstruct an equivalent contract card without losing core contract parameters.

#### Scenario: Round-trip JSON serialization
- **WHEN** a valid `ContractCard` is serialized to a JSON dictionary or string and subsequently deserialized
- **THEN** the deserialized instance matches the original card fields identically.

#### Scenario: Round-trip Canonical Markdown rendering
- **WHEN** a `ContractCard` is rendered into canonical Markdown via `render()` and parsed back via `from_markdown()`
- **THEN** all contract fields (role, goal, artifact, lands, for, done when, proof command, budget, verify) match the source card.

### Requirement: Role Prompt and Persona Specification
The system SHALL provide formal, programmatic role specifications (`RoleSpecification`) for Crew roles (`worker`, `content`, `verifier`, `coordinator`, `diagnose`). Each specification MUST define the role's identity persona, core responsibilities, allowed actions, strict prohibitions (including mandatory Zero-Checkout enforcement for code tasks), and concrete completion protocols.

#### Scenario: Worker role specification enforces execution and Zero-Checkout boundaries
- **WHEN** the `worker` role specification is retrieved
- **THEN** it specifies primary code/config implementation duties, restricts branch work to dedicated worktrees, and explicitly forbids `git checkout` or `git switch` in production checkouts.

#### Scenario: Verifier role specification enforces independent evaluation
- **WHEN** the `verifier` role specification is retrieved
- **THEN** it mandates independent verification execution, forbids modifying the artifact under evaluation, and restricts file writes exclusively to `.crew/` proof scripts when `Verify: independent`.

### Requirement: Worker Role Unified Engineering Discipline
The `crew-role-worker` skill SHALL apply a "Unified Engineering Discipline" on code and architecture cards: a Graphify Sibling Seam Audit of callers and callees of modified symbols, deep modules behind a narrow interface using the project's domain language, and "TDD at Public Seams". Its structured handoff MUST include a `Blast radius` line stating whether the change is a one-way or two-way door.

#### Scenario: Worker tests at the public seam without tautologies
- **GIVEN** a code card with `Inputs:` naming a public seam
- **WHEN** the worker implements a slice
- **THEN** it MUST write a failing behavioral test at that seam first and then the minimal implementation
- **AND** it MUST NOT write assertions that recompute the code's own formula or mocks of private internals.

#### Scenario: Worker handoff carries blast radius and before-after evidence
- **WHEN** the worker calls `crew_review_handoff`, `kanban_complete` or `kanban_block`
- **THEN** the summary MUST contain `Done`, `Not done`, `Evidence` (with Before -> After output) and `Blast radius` lines.

### Requirement: Content Role Design and Discovery Patterns
The `crew-role-content` skill SHALL apply specialized patterns when the deliverable matches: "Interactive Prototypes" (self-contained HTML demo with free-play controls and live state, or switchable variants clearly marked throwaway), visual architecture reports using `improve-codebase-architecture` and `codebase-design` (Before / After module deepening), and async stakeholder questionnaires.

#### Scenario: Prototype card yields a self-contained throwaway demo
- **GIVEN** a content card asking to validate UI layout or a state machine
- **WHEN** the content role produces the artifact
- **THEN** the artifact MUST be a single HTML file with its raw source beside it
- **AND** it MUST be marked throwaway.

### Requirement: Verifier Role Unified Verification Lenses
The `crew-verifier` skill SHALL judge the single extra check against the card's `Inputs` (including any Exploration Document or OpenSpec change specs) using the "Unified Verification Lenses": a three-dimension audit of Completeness, Correctness and Coherence, a "TDD Anti-Tautology" and multi-perspective review, and a read-only Graphify impact check on multi-module diffs.

#### Scenario: Verifier rejects a tautological test
- **GIVEN** a code diff whose test recomputes the formula under test or mocks a private internal
- **WHEN** the verifier performs its extra check
- **THEN** it MUST fail the check and call `kanban_request_changes` naming the offending test.

#### Scenario: Verifier compares the artifact with an Exploration Document
- **GIVEN** a card whose `Inputs:` lists an Exploration Document
- **WHEN** the verifier reads the artifact back with a read-only tool
- **THEN** it MUST compare the artifact with both `Done when` and that document
- **AND** it MUST quote the raw output of that comparison in its verdict.

