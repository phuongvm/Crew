# Proposal: Codify Zero-Checkout and Dedicated Worktree Mandate

## Why

During multi-agent and multi-session operations on the AGENT-4070 cluster, agents frequently executed `git checkout <branch>` directly within production repositories (`oss/crew`, `oss/hermes-agent`, and the root workspace `O:\workspaces`).
Because persistent services run 24/7 directly from `origin/main` in these checkouts (Hermes Web UI, Gateway, Crew Dashboard on port 8799, Desktop Electron app), checking out feature branches caused:
1. Missing files and 404 errors in Web/Desktop UI (`dashboard/` missing on bugfix branches).
2. Daemon crashes and connection resets on port 8799 due to partial runtime code reloads.
3. Git index collisions (`.git/index.lock` locks) preventing parallel operations across concurrent sessions.

To permanently prevent service disruptions, this invariant must be codified across all governance documentation and role skills so that every agent—regardless of profile or session—internalizes and enforces the Zero-Checkout and Dedicated Worktree mandate.

## What Changes

1. **Global Governance (`rules/`)**:
   - Update `rules/shared/safety.md` under Git Operations with mandatory Worktree Isolation and Zero-Checkout rules.
   - Update `rules/AGENTS.md` with explicit operational rules forbidding `git checkout <branch>` in primary checkouts.
2. **Crew Skills (`oss/crew/skills/`)**:
   - Update `skills/crew/SKILL.md` (Track A) to mandate worktree isolation for codebase tasks.
   - Update `skills/crew-no-spec/SKILL.md` (Track B) to mandate worktree isolation for fast-track tasks.
   - Update `skills/crew-role-worker/SKILL.md` to add explicit `## Do` (use dedicated worktree under `.worktrees/`) and `## Never` (never checkout branches in production checkouts).
   - Update `skills/crew-verifier/SKILL.md` to verify that workers respected worktree boundaries before granting approval.
3. **Multi-Profile Distribution**:
   - Run `install.py` / deployment sync to distribute the revised skills across all specialist profiles (`default`, `coder`, `reviewer`, `leader`, `designer`, `qa`, `researcher`).

## Capabilities

### New Capabilities
- `worktree-isolation-governance`: Mandatory enforcement of git worktree isolation for all branch creation, testing, and PR preparation across all profiles.

### Modified Capabilities
- `crew`: Coordinator includes worktree constraints in task contracts.
- `crew-no-spec`: Fast-track coordinator includes worktree constraints.
- `crew-role-worker`: Coder role strictly develops in dedicated worktrees.
- `crew-verifier`: Reviewer verifies worktree isolation compliance.

## Impact

- Prevents live service downtime on ports 9119, 8799, and desktop app.
- Eliminates git `index.lock` contention across concurrent sessions.
- Ensures clean branch isolation for upstream PR contributions.
