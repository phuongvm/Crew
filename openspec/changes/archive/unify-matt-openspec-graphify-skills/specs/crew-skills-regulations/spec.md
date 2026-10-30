## MODIFIED Requirements

### Requirement: Fast-Track Direct Dispatch Protocol
The `/crew-no-spec` skill SHALL apply an Adaptive Dual-Entry Intake: an Exploration-Backed or Clear-Target Fast-Path that dispatches task cards in Turn 1, and a Guided Discovery & Root-Cause Loop for asks whose root cause or design is unsettled. In both modes the coordinator MUST NOT edit production source code or review its own work in the chat session, and formal OpenSpec change artifacts remain bypassed.

#### Scenario: Fast-track operational task intake
- **GIVEN** user invokes `/crew-no-spec <ask>` and the ask names a concrete target and a measurable end state
- **WHEN** the coordinator processes the request in Turn 1
- **THEN** the coordinator MUST formulate the contract card and call `crew_card_create` (or `kanban_create`) within the same turn
- **AND** the coordinator MUST NOT write code, run blind recursive filesystem searches, or review its own output in chat.

#### Scenario: Exploration-backed fast-path attaches the Exploration Document
- **GIVEN** an Exploration Document exists under `<project>/openspec/workspace/explorations/` and settles scope, target and done-when
- **WHEN** the coordinator dispatches the card in Turn 1
- **THEN** the card's `Inputs:` MUST include the absolute path of that Exploration Document
- **AND** the coordinator MUST NOT re-interview the Commander about decisions the document already settles.

#### Scenario: Unsettled ask enters the guided discovery loop
- **GIVEN** user invokes `/crew-no-spec <ask>` to investigate an unknown bug root cause or to design a feature whose seams are not settled
- **WHEN** the coordinator starts intake
- **THEN** it MUST run the project gate, query Graphify MCP on large codebases, and persist an Exploration Document before dispatching the card
- **AND** it MUST NOT ask the Commander why a bug or metric is broken.

## ADDED Requirements

### Requirement: Unified Cognitive and Tool Routing Matrix
The `crew` skill SHALL contain a "Unified Cognitive & Tool Routing Matrix" mapping each task context to the Matt Pocock skills, OpenSpec skills and Graphify MCP or Crew tools that the coordinator and dispatched roles activate without being named in the Commander's prompt. `crew-no-spec` SHALL carry the same matrix as its "Automatic Cognitive & Tool Routing Matrix".

#### Scenario: Matrix covers every task context
- **WHEN** the matrix is read
- **THEN** it MUST contain a row for codebase reconnaissance, bug or anomaly, feature or architecture discovery, exploration-to-contract synthesis, human credential setup, worker implementation and independent verification.

#### Scenario: Matrix routes a bug to diagnosis without asking the Commander
- **GIVEN** the ask describes a bug, regression or metric anomaly
- **WHEN** the coordinator consults the matrix
- **THEN** it MUST route to `diagnosing-bugs` and `triage` with a reproduction probe under five seconds
- **AND** it MUST present the proven root cause for approval instead of asking the Commander why the defect occurs.

#### Scenario: Matrix routes large codebase reconnaissance to Graphify
- **GIVEN** the target repository is large or multi-package
- **WHEN** the coordinator maps its structure
- **THEN** it MUST query `mcp__graphify__graph_stats`, `god_nodes`, `query_graph` or `get_neighbors` before any broad `grep -r` or `find` sweep.

### Requirement: Exploration Document Continuity
Both `/crew` and `/crew-no-spec` SHALL check whether the current conversation or `<project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` already holds a completed Exploration Document and SHALL reuse it. Cards dispatched afterwards MUST list its path in `Inputs:`.

#### Scenario: Crew reuses an existing exploration as Phase 1
- **GIVEN** a settled Exploration Document already exists for the topic of a `/crew` request
- **WHEN** the coordinator reaches the Explore phase
- **THEN** it MUST treat that document as Phase 1 completion and advance to `openspec-propose`
- **AND** it MUST NOT repeat the exploration.

#### Scenario: New exploration is persisted incrementally
- **GIVEN** no Exploration Document exists and discovery is required
- **WHEN** the coordinator starts exploring
- **THEN** it MUST scaffold the document early with `write_file` and patch findings into it every three to five read or search calls
- **AND** the document MUST use the sections Problem Statement, Solution, Public Testing Seams, Implementation Decisions and Out of Scope.

### Requirement: CREW-INV-8 Static Anchors
The five Crew skills SHALL keep the CREW-INV-8 anchor strings so the upstream-sync gate can detect a regression. The authoritative list is the CREW-INV-8 block of `daily-sync-watchdog.ps1` and `references/invariant-checklist.md`.

#### Scenario: Anchors are distributed across all five skills
- **WHEN** the CREW-INV-8 list is read
- **THEN** it MUST include "Unified Cognitive & Tool Routing Matrix" and "mcp__graphify__" for `crew`; "Adaptive Dual-Entry Intake", "mcp__graphify__", "diagnosing-bugs" and "grilling" for `crew-no-spec`; "Unified Engineering Discipline" and "TDD at Public Seams" for `crew-role-worker`; "Interactive Prototypes" and "improve-codebase-architecture" for `crew-role-content`; "Unified Verification Lenses" and "TDD Anti-Tautology" for `crew-verifier`.

#### Scenario: All twelve anchors are present
- **WHEN** `python openspec/changes/unify-matt-openspec-graphify-skills/proofs/check_inv8_anchors.py` is run from the Crew repository root
- **THEN** it SHALL report `anchors=12 missing=0` and exit with code 0.

#### Scenario: Sync gate preserves CREW-INV-1..8
- **WHEN** `daily-sync-watchdog.ps1 -GateOnly` is run against the Crew checkout
- **THEN** it SHALL print `Verification gate PASS (CREW-INV-1..8 preserved)`
- **AND** a merge that removes any CREW-INV-8 anchor MUST fail the gate.
