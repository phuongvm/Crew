# Exploration: Zero-Checkout in Production Workspaces & Dedicated Worktree Mandate

- **Date**: 2026-10-11
- **Target Project**: `oss/crew` & `rules/`
- **Scope**: Multi-agent safety governance, git worktree isolation, profile synchronization

---

## 1. Context & Motivation

During parallel multi-session operations, agents frequently switched branches directly within primary repositories (`O:\workspaces\oss\crew`, `O:\workspaces\oss\hermes-agent`, `O:\workspaces`).
Because persistent services run 24/7 directly from `origin/main` in these checkouts (Hermes Web UI, Gateway, Crew Dashboard on port 8799, Desktop Electron app), checking out feature branches caused:
1. Missing files and 404 errors in Web/Desktop UI (`dashboard/` missing on bugfix branches).
2. Daemon crashes and connection resets on port 8799 due to partial runtime code reloads.
3. Git index collisions (`.git/index.lock` locks) preventing parallel operations.

## 2. Invariants to Codify

1. **Zero-Checkout Invariant**:
   - Production repositories hosting live services (`oss/crew`, `oss/hermes-agent`, `O:\workspaces`) must strictly remain anchored on `origin/main`.
   - Running `git checkout <branch>` directly in these checkouts is strictly forbidden.
2. **Dedicated Worktree Mandate**:
   - All branch development, upstream sync reconciliation, PR preparation, and experimental changes must occur in an isolated git worktree under `O:\workspaces\.worktrees\<task-name>`.
3. **Commander Approval Gate**:
   - Code developed in worktrees must never be merged or fast-forwarded into `origin/main` without explicit Commander review and approval.
4. **Universal Profile Synchronization**:
   - Rules must be embedded not just in the active chat context, but in `rules/shared/safety.md`, `rules/AGENTS.md`, and all crew skill definitions (`crew`, `crew-no-spec`, `crew-role-worker`, `crew-verifier`) distributed across all profiles (`default`, `coder`, `reviewer`, `leader`, `designer`, `qa`, `researcher`).

## 3. Implementation Seams

- `rules/shared/safety.md`: Add Rule 2 section on Git Worktree Isolation & Production Checkout Protection.
- `rules/AGENTS.md`: Add Invariant to Section VII Operational Safeguards.
- `oss/crew/skills/crew/SKILL.md`: Update intake constraints requiring worktree isolation in task contracts.
- `oss/crew/skills/crew-no-spec/SKILL.md`: Mirror worktree isolation requirements.
- `oss/crew/skills/crew-role-worker/SKILL.md`: Add explicit `## Do` and `## Never` rules forbidding in-tree branch checkout.
- `oss/crew/skills/crew-verifier/SKILL.md`: Add verification check ensuring worker did not violate worktree boundaries.
- `oss/crew/install.py`: Synchronize updated skills across all specialist profiles.
