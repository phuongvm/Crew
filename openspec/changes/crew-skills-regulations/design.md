## Context

Crew operates as a distributed multi-agent workflow framework on top of Hermes Agent, leveraging the Kanban board for task dispatch, execution, and verification. In past versions, skill documentation leaned heavily on POSIX-centric shell command patterns (`sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" ...`) to invoke underlying Python helper utilities.

On Windows 11 host environments running Git Bash / MSYS, this created persistent operational friction:
1. Argument strings with quotes or whitespace passed through subshells experienced quote stripping.
2. Hermes runtime security heuristics blocked commands executing through `sh` or nested interpreters, prompting human approval interruptions.
3. Agents frequently missed using Hermes's rich set of typed native tools (`kanban_create`, `kanban_complete`, `kanban_block`, etc.) because the skills directed them to shell syntax.
4. Version drift between `plugin.yaml` (`0.9.12`) and `crew-no-spec` (`0.9.0`) broke automated version consistency checks.
5. Verbose descriptions failed the standard 60-character trigger guideline for optimal skill selection.

## Goals / Non-Goals

**Goals:**
- Modernize all 4 primary Crew skills (`crew`, `crew-diagnose`, `crew-no-spec`, and `crew-verifier`) to establish deterministic, tool-first execution regulations.
- Mandate native typed tools (`kanban_*`, `openspec_*`, `read_file`, `write_file`) as first-class operations, providing clean CLI fallbacks for environments without typed tools.
- Eliminate brittle subshell wrapping and escaping errors on Windows/MSYS.
- Align all skill descriptions so their trigger phrases are <= 60 characters and self-contained.
- Synchronize version strings to `0.9.12` matching `plugin.yaml`.
- Enforce the Zero-Checkout Invariant across all skill guidance.

**Non-Goals:**
- Modifying backend SQLite schemas (`kanban.db`) or core coordinator daemon logic (`crew_coordinator.py`).
- Changing the public command options registered in `__init__.py` (`/crew-status`, `/crew-stop`, etc.).
- Deprecating POSIX compatibility on Linux/macOS systems.

## Decisions

### Decision 1: Tool-First Precedence Hierarchy
- **Context:** Agents have access to native Hermes tools (`kanban_create`, `kanban_complete`, etc.) that provide structured schemas, automatic serialization, and clean audit logs, but skills previously showcased shell commands.
- **Decision:** Mandate a 3-tier execution precedence in all skills:
  1. *Tier 1 (Native Typed Tools):* Always call `kanban_create`, `kanban_show`, `kanban_complete`, `kanban_block`, `kanban_request_review`, `kanban_request_changes`, `read_file`, `write_file` directly.
  2. *Tier 2 (Direct Python Invocations):* For crew-specific script operations (verdicts, diagnosis, lessons), invoke python directly within the agent environment without subshell string escaping.
  3. *Tier 3 (CLI Fallback):* Provide clean `hermes kanban ...` or `crew-run.sh` fallback commands for sessions or environments where typed tools are absent.
- **Alternatives Considered:**
  - *Keep shell commands only:* Rejected; causes recurring quotation bugs on Windows and blocks approval queues.
  - *Remove CLI fallbacks entirely:* Rejected; would break older Hermes profiles or non-tool environments where typed tools are not injected.

### Decision 2: Cross-Platform Script Invocation Cleanliness
- **Context:** `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh"` was intended to locate an interpreter, but creates nested quoting problems when passed to `terminal()`.
- **Decision:** Replace brittle bash nested quoting with clean invocation patterns. Prefer direct script paths resolved via `$HERMES_HOME` or project root, and ensure no skill text instructs running `python3` (which violates Windows test `test_crew_run_launcher.py`).
- **Alternatives Considered:**
  - *Using `python3` unconditionally:* Rejected; fails on Windows without python3 symlink and breaks `test_crew_run_launcher.py`.

### Decision 3: Standardized Frontmatter & Trigger Formatting
- **Context:** Skill selection algorithms evaluate the first sentence of the skill description. Verbose descriptions dilute keyword matching and can cause trigger ambiguity.
- **Decision:** Restructure all 4 skills to use the canonical pattern:
  `description: "Use when <trigger>. <one-line behavior>."` where the trigger phrase is <= 60 characters.
  - `crew`: `Use when running /crew. Coordinator intake & contract.` (55 chars)
  - `crew-diagnose`: `Use when /crew-diagnose [state]. Read-only card diagnosis.` (58 chars)
  - `crew-no-spec`: `Use when /crew-no-spec <ask>. Fast-track direct card intake.` (59 chars)
  - `crew-verifier`: `Use when verifying an independent card. Proof-first review.` (59 chars)
- **Alternatives Considered:**
  - *Leave legacy verbose descriptions:* Rejected; violates authoring guidelines and causes inconsistent discovery.

### Decision 4: Zero-Checkout Invariant Reaffirmation
- **Context:** Agents modifying code repositories can accidentally disrupt running background services if they switch branches in primary checkouts.
- **Decision:** All skills touching code cards must explicitly reiterate the Zero-Checkout invariant: production checkouts stay on `main`; branch development happens strictly in `O:/workspaces/.worktrees/<name>`.

## Risks / Trade-offs

- **[Risk]** Agent sessions without native kanban tools cannot call `kanban_create`.
  - **Mitigation:** Document explicit CLI fallback commands in each skill, showing exact argument flags.
- **[Risk]** Inconsistent interpreter environments across Windows, WSL, and Linux.
  - **Mitigation:** Maintain `scripts/crew-run.sh` on disk as a supported launcher while standardizing the invocation syntax in skill text.
- **[Risk]** Breaking existing test assertions during skill rewrites.
  - **Mitigation:** Run `pytest tests/test_crew_versions.py` and `pytest tests/test_crew_run_launcher.py` to continuously verify compliance.

## Migration Plan

1. Author OpenSpec change artifacts (`proposal.md`, `specs/.../spec.md`, `design.md`, `tasks.md`).
2. Update `skills/crew/SKILL.md` with Track A / Track B regulations, tool-first instructions, and trigger <= 60 chars.
3. Update `skills/crew-diagnose/SKILL.md` with read-only rules, tool-first diagnosis, and trigger <= 60 chars.
4. Update `skills/crew-no-spec/SKILL.md` with Turn-1 dispatch mandate, version 0.9.12, and trigger <= 60 chars.
5. Update `skills/crew-verifier/SKILL.md` with proof script creation rules, verdict execution, and trigger <= 60 chars.
6. Validate OpenSpec via `openspec validate crew-skills-regulations --strict`.
7. Execute pytest test suite to confirm zero regressions.

## Open Questions

- None. Requirements and design decisions are fully bounded and verified against repository constraints.
