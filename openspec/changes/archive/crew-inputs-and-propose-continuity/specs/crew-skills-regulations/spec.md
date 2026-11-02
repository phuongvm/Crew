# Delta Specification: Crew Skills Regulations (`crew-inputs-and-propose-continuity`)

## MODIFIED Requirements

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
