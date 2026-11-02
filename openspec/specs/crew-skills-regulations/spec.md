# crew-skills-regulations Specification

## Purpose
Establish deterministic workflow regulations, tool-first execution rules, robust cross-platform command execution, and frontmatter compliance across all Crew skills (`crew`, `crew-diagnose`, `crew-no-spec`, and `crew-verifier`).

## Requirements
### Requirement: Tool-First Kanban Board Operations
When interacting with the Hermes Kanban board, agents executing Crew skills SHALL prioritize typed native tools (`kanban_create`, `kanban_show`, `kanban_complete`, `kanban_block`, `kanban_request_review`, `kanban_request_changes`, `kanban_list`) over shell CLI commands whenever the native tools are available in the session toolset.

#### Scenario: Agent dispatches a work card during intake
- **GIVEN** an agent executing `/crew` or `/crew-no-spec` with active `kanban_create` tool
- **WHEN** the card contract is drafted and ready for dispatch
- **THEN** the agent MUST invoke `kanban_create` as a typed tool call
- **AND** the agent SHALL NOT execute `hermes kanban create` or shell scripts via `terminal()` to create the card.

#### Scenario: Fallback when native tool is unavailable
- **GIVEN** an agent operating in an environment where native `kanban_create` is omitted from the toolset
- **WHEN** the agent needs to create a task card
- **THEN** the agent SHALL execute the documented CLI fallback command with properly quoted arguments
- **AND** the command MUST adhere to platform shell escaping rules.

### Requirement: Cross-Platform Deterministic Script Execution
When Crew workflow steps require executing helper scripts (`crew_card.py`, `crew_diagnose.py`, `crew_stop.py`, or verification scripts), instructions SHALL provide deterministic command invocations that avoid brittle nested subshells (`sh "$HERMES_HOME/..."`) and prevent quote-stripping errors on Windows/MSYS.

#### Scenario: Launching card watcher in background
- **GIVEN** a card has been opened with ID `<card_id>`
- **WHEN** the coordinator launches the background watcher
- **THEN** the skill instructions SHALL specify a clean background command
- **AND** the command SHALL NOT use fragile double-quoted subshell wrapping that breaks under MSYS argument conversion.

#### Scenario: Absence of bare python3 command references
- **GIVEN** skill instructions in `skills/*/SKILL.md`
- **WHEN** python execution syntax is documented
- **THEN** the instructions MUST NOT mandate bare `python3` command syntax that fails on Windows systems lacking python3 aliases.

### Requirement: Deterministic Read-Only Card Diagnosis
The `/crew-diagnose` skill SHALL govern read-only diagnostic passes without performing mutations on the board or filesystem, presenting exact diagnostic fields and actionable resume steps.

#### Scenario: Executing diagnosis on blocked cards
- **GIVEN** user invokes `/crew-diagnose blocked`
- **WHEN** the diagnostic reader executes
- **THEN** the turn SHALL remain strictly read-only with zero board modifications
- **AND** the output MUST report each card's ID, status, wait duration, reason, and concrete `RESUME:` / `WHO:` paths.

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

### Requirement: Independent Verifier Proof Execution Protocol
The `crew-verifier` skill SHALL mandate that independent verification passes run owner-confirmed proof commands, write `.crew/` proof scripts using native file tools, perform independent inspection, and record verdicts using native kanban tools.

#### Scenario: Verifier authors missing proof script
- **GIVEN** a card with `Verify: independent` whose proof script under `.crew/` does not exist
- **WHEN** the verifier claims the card
- **THEN** the verifier MUST author the verification script using `write_file`
- **AND** the checks MUST be derived strictly from the card's `Done when` and `Inputs` clauses using only Python standard library.

#### Scenario: Verifier records evaluation verdict
- **GIVEN** the verifier has executed the proof command and completed the secondary check
- **WHEN** the proof passes all criteria
- **THEN** the verifier MUST call `kanban_complete` with the raw proof evidence
- **AND** if any check fails, the verifier MUST call `kanban_request_changes` detailing the exact deficiency.

### Requirement: Skill Frontmatter and Trigger Compliance
Every Crew skill (`SKILL.md`) SHALL contain valid YAML frontmatter starting at byte 0, a synchronized version field matching `plugin.yaml`, and a description whose opening trigger is concise and self-contained (<= 60 characters).

#### Scenario: Frontmatter validation across all Crew skills
- **GIVEN** the skill files under `skills/*/SKILL.md`
- **WHEN** validated against package metadata and authoring rules
- **THEN** each file's frontmatter MUST parse as valid YAML
- **AND** `version` MUST match `plugin.yaml`
- **AND** the initial trigger phrase of `description` MUST NOT exceed 60 characters.

#### Scenario: Worktree contract proof is separated from installed-runtime parity
- **GIVEN** the skills in the worktree were changed but not yet deployed to `O:/workspaces/_config/agent4070/hermes/skills/crew`
- **WHEN** the repository-contract proof runs before live deployment
- **THEN** it SHALL run the `VersionTests` suite excluding `test_installed_skills_byte_identical_parity`, plus `check_inv8_anchors.py <worktree>` expecting `anchors=12 missing=0`
- **AND** after live deployment the full `test_crew_versions.py` (including `test_installed_skills_byte_identical_parity`) MUST pass without being weakened or skipped.

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
Both `/crew` and `/crew-no-spec` SHALL check whether the current conversation or `<project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` already holds a completed Exploration Document and SHALL reuse it. Cards dispatched afterwards MUST list its path in `Inputs:`. In Track A (`/crew`), the coordinator SHALL supervise the unbroken 7-stage OpenSpec lifecycle (Project Activation $\rightarrow$ Explore $\rightarrow$ Propose $\rightarrow$ Apply $\rightarrow$ Verify $\rightarrow$ Sync $\rightarrow$ Archive) inside the canonical repository's `OPENSPEC_ROOT` (via its isolated worktree when Zero-Checkout applies).

#### Scenario: Crew reuses an existing exploration as Phase 1
- **GIVEN** a settled Exploration Document already exists for the topic of a `/crew` request
- **WHEN** the coordinator reaches the Explore phase
- **THEN** it MUST treat that document as Phase 1 completion and advance to `openspec-propose`
- **AND** it MUST NOT repeat the exploration.

#### Scenario: Single-file or one-line ask under /crew still executes Phase 2 Propose
- **GIVEN** a user invokes `/crew <ask>` (without `--no-spec`) naming a concrete file or single-line code fix and an Exploration Document exists or is produced in Phase 1
- **WHEN** Phase 1 Explore completes
- **THEN** the coordinator MUST advance to Phase 2 (`openspec-propose`) using the Exploration Document to produce the OpenSpec change artifacts and dispatch independent proposal review
- **AND** the coordinator SHALL NOT bypass Phase 2 Propose or dispatch a direct code-implementation worker card before the Phase Approval Gate.

#### Scenario: Track A persists only OpenSpec exploration and proposal artifacts before proposal review
- **GIVEN** a `/crew` Track A turn with `OPENSPEC_ROOT` locked by the Project Activation Gate to the target repository's `openspec/` (or `<worktree>/openspec/` under Zero-Checkout)
- **WHEN** the coordinator completes Phase 1 Explore and Phase 2 Propose before dispatching the independent `@reviewer` Proposal Review card
- **THEN** it SHALL write the Exploration Document `<OPENSPEC_ROOT>/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` (plus a copy in `<OPENSPEC_ROOT>/changes/<change-id>/explorations/`) and the Phase 2 artifacts under `<OPENSPEC_ROOT>/changes/<change-id>/` (`.openspec.yaml` `x-exploration`, `proposal.md`, `specs/`, `design.md`, `tasks.md`) directly
- **AND** `skills/crew/SKILL.md` SHALL NOT contain the blanket instruction "Intake writes nothing to disk; read-only tools only" and SHALL scope the prohibition to production application source code (the coordinator never edits production source in chat).

#### Scenario: Generic-root exploration is migrated or linked into the locked project root
- **GIVEN** an Exploration Document was saved under the generic root `O:/workspaces/openspec/workspace/explorations/` before the Project Activation Gate locked `OPENSPEC_ROOT` to a subproject
- **WHEN** the coordinator enters Phase 2 Propose
- **THEN** it MUST copy or link that document into `<OPENSPEC_ROOT>/workspace/explorations/` and `<OPENSPEC_ROOT>/changes/<change-id>/explorations/` before dispatching Phase 2 authoring or review cards
- **AND** it MUST record the migrated path in `.openspec.yaml` `x-exploration` and cite the Exploration Document in `proposal.md`
- **AND** `skills/crew/SKILL.md` and `skills/crew-no-spec/SKILL.md` SHALL forbid writing a new exploration to the generic root or to a different repository's `openspec/` when a subproject owns the target.

#### Scenario: Rejected watcher report triggers autonomous zero-prompt Phase 2b remediation
- **GIVEN** a Phase 2 (or Phase 3) independent review card whose `crew_card.py watch` background process ends with a report carrying `verdict: REJECTED`, after the original `/crew` intake window has expired
- **WHEN** `crew_intake_preload` receives the `WATCH_REPORT_RX` report turn (`__init__.py:1596`)
- **THEN** the plugin SHALL call `_open_window(session_id)` and `_record_crew_turn(session_id, turn_id)` for that session so the intake guard permits two-card creation in the report turn
- **AND** the coordinator MUST, in that same turn, dispatch the Phase 2b Remediation (`@coder`) card and its gated Re-Review (`@reviewer`) card, each with `Inputs:` carrying the Exploration Document path, the change directory and the rejecting `reviews/findings-*.md`, without asking the Commander to re-confirm or to type `/crew remediate ...`
- **AND** a watcher report without a `REJECTED` verdict SHALL leave the session's intake window unchanged and open no card.

#### Scenario: Exploration Document path is preserved in Inputs across Proposal Review, Remediation, Re-Review, and Apply cards
- **GIVEN** an Exploration Document `<OPENSPEC_ROOT>/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` was authored or reused for an OpenSpec change
- **WHEN** the coordinator dispatches any Proposal authoring card, Independent Proposal Review card, Phase 2b Proposal Remediation card, Phase 2b Re-Review card, or Phase 3 Apply card via `crew_card_create` or `kanban_create`
- **THEN** the card's `Inputs:` field MUST include the absolute path to the Exploration Document alongside the change directory and any review findings artifacts
- **AND** both `skills/crew/SKILL.md` and `skills/crew-no-spec/SKILL.md` MUST list `inputs` in the `crew_card_create` tool parameter matrix.

#### Scenario: Mandatory 6-point close-out syncs canonical repository specs, packages explorations, verifies terminal Kanban state, and fast-forwards production checkout
- **GIVEN** all implementation and verification tasks for a `/crew` Track A change have passed (`rc=0`)
- **WHEN** the coordinator executes Phase 5 (`Sync`) and Phase 6 (`Archive`)
- **THEN** it MUST merge delta specs into the target repository's canonical `<OPENSPEC_ROOT>/specs/<capability>/spec.md`, ensure `<OPENSPEC_ROOT>/changes/<change-id>/explorations/` and `reviews/` are packaged, move the change into `<OPENSPEC_ROOT>/changes/archive/<change-id>`, write `<OPENSPEC_ROOT>/workspace/audits/YYYY-MM-DD/<change-id>-audit.md`, confirm all associated Crew cards are in terminal `done` state, and commit + push + fast-forward `<project-path>` so the OpenSpec UI source is clean and up to date.

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
- **WHEN** `python openspec/changes/archive/unify-matt-openspec-graphify-skills/proofs/check_inv8_anchors.py` is run from the Crew repository root
- **THEN** it SHALL report `anchors=12 missing=0` and exit with code 0.

#### Scenario: Sync gate preserves CREW-INV-1..8
- **WHEN** `daily-sync-watchdog.ps1 -GateOnly` is run against the Crew checkout
- **THEN** it SHALL print `Verification gate PASS (CREW-INV-1..8 preserved)`
- **AND** a merge that removes any CREW-INV-8 anchor MUST fail the gate.

