# Design: Zero-Checkout and Dedicated Worktree Mandate Architecture

## Architectural Overview

This design addresses multi-agent concurrency risks where agents checking out feature branches in shared production repositories broke live 24/7 background services (Hermes Web Server, Gateway, Desktop App, Crew Dashboard daemon).

### Component Layers

1. **System Governance Layer (`rules/`)**:
   - `rules/shared/safety.md`: Forms the primary policy filter for all tools. Contains the explicit prohibition against branch-switching in primary repositories and mandates dedicated worktrees.
   - `rules/AGENTS.md`: Loaded during boot protocol before greeting the user or taking tasks. Codifies the Zero-Checkout invariant.

2. **Crew Plugin Skill Layer (`oss/crew/skills/`)**:
   - `skills/crew/SKILL.md` (Track A): Intake coordinator injects worktree constraints into created Kanban cards.
   - `skills/crew-no-spec/SKILL.md` (Track B): Fast-track coordinator injects worktree constraints into single direct cards.
   - `skills/crew-role-worker/SKILL.md`: Worker role instructions define the operational workflow:
     1. Create worktree under `O:\workspaces\.worktrees\<name>`.
     2. Execute work within worktree.
     3. Verify proofs within worktree.
     4. Call `kanban_complete` / `kanban_request_review`.
     5. Never checkout branches in the parent checkout.
   - `skills/crew-verifier/SKILL.md`: Verifier audits whether the worker violated repository boundaries.

3. **Multi-Profile Distribution Layer**:
   - Uses `oss/crew/install.py` (`step_skills` and `step_other_copies`) plus direct runtime deployment to copy updated skills into all profile directories:
     - `_config/agent4070/hermes/profiles/coder/skills/`
     - `_config/agent4070/hermes/profiles/reviewer/skills/`
     - `_config/agent4070/hermes/profiles/leader/skills/`
     - `_config/agent4070/hermes/profiles/designer/skills/`
     - `_config/agent4070/hermes/profiles/qa/skills/`
     - `_config/agent4070/hermes/profiles/researcher/skills/`
     - `_config/agent4070/hermes/skills/` (default profile)
