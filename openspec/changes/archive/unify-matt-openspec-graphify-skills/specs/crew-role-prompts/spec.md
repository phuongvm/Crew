## ADDED Requirements

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
