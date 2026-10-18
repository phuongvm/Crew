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
The `/crew-no-spec` skill SHALL enforce Turn-1 dispatch of operational and ad-hoc task cards, strictly forbidding autonomous execution, deep research, or conversational self-reviews in the chat session.

#### Scenario: Fast-track operational task intake
- **GIVEN** user invokes `/crew-no-spec <ask>`
- **WHEN** the coordinator processes the request in Turn 1
- **THEN** the coordinator MUST formulate the contract card and call `kanban_create` within the same turn
- **AND** the coordinator MUST NOT write code, perform deep filesystem exploration, or review its own output in chat.

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
- **AND** `version` MUST match `plugin.yaml` (`0.9.12`)
- **AND** the initial trigger phrase of `description` MUST NOT exceed 60 characters.

