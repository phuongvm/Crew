# Spec: Zero-Checkout in Production Workspaces & Dedicated Worktree Mandate

## ADDED Requirements

### Requirement: Zero-Checkout in Production Workspaces
Primary repositories hosting live 24/7 background services (`O:\workspaces\oss\hermes-agent`, `O:\workspaces\oss\crew`, `O:\workspaces\oss\hermes-nerve`, and root `O:\workspaces`) SHALL permanently remain on their primary integration branch (`origin/main`). Agents SHALL NOT run `git checkout <branch>` or switch branches directly in these working trees.

#### Scenario: Agent attempts branch checkout in primary repository
- **GIVEN** an active production checkout at `O:\workspaces\oss\crew` running the live dashboard daemon on port 8799
- **WHEN** an agent prepares to implement a feature, bugfix, or upstream PR
- **THEN** the agent MUST NOT run `git checkout -b <branch>` or `git checkout <branch>` in `O:\workspaces\oss\crew`
- **AND** the primary working tree MUST remain clean and on `origin/main`.

### Requirement: Dedicated Git Worktree Mandate
For any task requiring branch development, feature prototyping, upstream PR preparation, or merge reconciliation, agents SHALL create and operate strictly within a dedicated git worktree located under `O:\workspaces\.worktrees\<task-name>`.

#### Scenario: Worker executes task in isolated worktree
- **GIVEN** a Kanban task assigned to `@coder` targeting `oss/crew`
- **WHEN** the worker begins implementation
- **THEN** the worker MUST initialize a dedicated worktree via `git worktree add O:\workspaces\.worktrees\<slug> -b <branch>`
- **AND** all code edits, dependency builds, and unit test executions MUST occur within that worktree directory
- **AND** the live production checkout remains untouched during execution.

### Requirement: Multi-Profile Skill Synchronization
Updated safety rules and worktree invariants SHALL be synchronized across all configured Hermes profiles on the node (`default`, `coder`, `reviewer`, `leader`, `designer`, `qa`, `researcher`), ensuring that isolated worker processes inherit the invariant upon startup.

#### Scenario: Worker profile boots up
- **GIVEN** a worker spawned in profile `coder` via `hermes -p coder chat -q "work kanban task..."`
- **WHEN** the worker reads `rules/shared/safety.md` and `skills/crew/crew-role-worker/SKILL.md`
- **THEN** the worker recognizes the worktree invariant and obeys the prohibition against in-tree branch checkout.
