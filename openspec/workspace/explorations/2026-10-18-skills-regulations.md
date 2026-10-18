# Exploration: Modernizing Crew Skills and Workflow Regulations for Native Tool-First Execution

- **Date:** 2026-10-18
- **Author:** Hermes Agent (Subagent)
- **Active Project:** `oss/crew` (locked via `O:/workspaces/oss/crew/.active_project`)
- **Target Repository:** `O:/workspaces/oss/crew`
- **Scope:** Architectural audit and modernization analysis of Crew skills (`skills/crew/SKILL.md`, `skills/crew-diagnose/SKILL.md`, `skills/crew-no-spec/SKILL.md`, `skills/crew-verifier/SKILL.md`) to transition from brittle shell command lines to deterministic, native tool-first execution regulations with backward-compatible CLI support.

---

## 1. Context & Problem Statement

Crew skills coordinate multi-agent and single-agent workflows across the Hermes Kanban board and OpenSpec governance lifecycles. Currently, the skills mandate complex shell commands of the form:
```bash
sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" <script.py> [args...]
```

While designed as a cross-platform helper, this shell-centric approach introduces several severe failure modes:

1. **Subshell Quoting & Escaping Failures:**
   - In MSYS/Git-Bash on Windows (the default shell environment on Windows 11 hosts), string arguments containing quotes, backslashes, spaces, or JSON strings (such as `--command '<proof command>'` or `--text "..."`) frequently suffer from quote-stripping or double-escaping bugs when piped through `sh`.
2. **Path Translation & Environment Fragility:**
   - In Hermes on Windows, MSYS automatic path translation is disabled (`MSYS_NO_PATHCONV=1`). Passing Windows paths (`C:\...` or `O:\...`) into `sh` or mixing POSIX `/c/...` paths into Windows-native Python binaries causes `file not found` or `invalid path` runtime errors.
   - `$HERMES_HOME` is frequently unset or contains mixed backslashes, requiring fragile path canonicalization loops inside bash scripts.
3. **Approval Blocking & Security Friction:**
   - Shell command lines passed to `terminal()` often match generic security heuristics (e.g. executing `sh`, background subshells, or commands touching script paths), prompting unnecessary manual user approval blocks or failing security scans.
4. **Tool-First Execution Gap:**
   - Hermes provides typed native tools (`kanban_create`, `kanban_show`, `kanban_complete`, `kanban_block`, `kanban_request_review`, `kanban_request_changes`, `openspec_*`, `read_file`, `write_file`). Mandating shell commands instead of native tools violates the tool-use enforcement principles, bypasses typed schema validation, and increases cognitive overhead for models.
5. **Specification & Version Drift:**
   - `skills/crew-no-spec/SKILL.md` was found pinned to version `0.9.0` while `plugin.yaml` is `0.9.12`, causing test failures in `tests/test_crew_versions.py`.
   - Skill descriptions lack compact, self-contained triggers (violating the `< 60` characters trigger rule for optimal routing and discovery).

---

## 2. Inventory and Audit of Existing Skills

### 2.1. `skills/crew/SKILL.md` (Coordinator Intake — Track A OpenSpec & Track B Fast-Track)
- **Role:** Main intake coordinator. Gathers user intent, formulates contract, gates execution.
- **Current Brittle Shell Calls:**
  - `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py safety` (line 224)
  - `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py proof-check --command '<the proof command>'` (line 244)
  - `terminal(..., command='sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py watch --card <id>')` (line 266)
  - `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py plan --spec <plan.json>` (line 279)
  - `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py lesson --role <role> --text "..."` (line 305)
- **Defects & Gaps:**
  - `crew_card.py safety` is called via shell even though the `<crew-facts>` block already injects the proof safety mode into context.
  - The watcher command uses nested quotes inside `terminal()` that can fail under MSYS bash.
  - Card creation instructions correctly illustrate `kanban_create(...)`, but lacked explicit instructions on choosing native tool calls over terminal CLI commands when available.
  - Description is 138 characters long without a compact <= 60 char trigger.

### 2.2. `skills/crew-diagnose/SKILL.md` (Read-Only Card Diagnosis)
- **Role:** Inspects cards sitting in a given state (`blocked`, `triage`, etc.) and determines the resume path.
- **Current Brittle Shell Calls:**
  - `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_diagnose.py [--state STATE]` (line 20)
- **Defects & Gaps:**
  - Mandates *only* the shell reader call, prohibiting `kanban_list` or direct read-only inspection even when native tools are faster and avoid subshell quotation.
  - Rigid command format fails if `$HERMES_HOME` is not set in the subshell.
  - Description is 162 characters long; trigger exceeds 60 characters.

### 2.3. `skills/crew-no-spec/SKILL.md` (Fast-Track Coordinator Intake)
- **Role:** Direct Kanban card intake for operational fixes, ad-hoc investigations, and hotfixes bypassing OpenSpec.
- **Current Brittle Shell Calls:**
  - `terminal(..., command='sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py watch --card <id>')` (line 102)
- **Defects & Gaps:**
  - Frontmatter version is `0.9.0` (out of sync with package version `0.9.12`).
  - Lacks tool-first priority rules and explicit fallback guidelines.
  - Description trigger exceeds 60 characters.

### 2.4. `skills/crew-verifier/SKILL.md` (Independent Verifier Pass)
- **Role:** Verifier role pass for cards with `Verify: independent`. Writes proof scripts and runs verdicts.
- **Current Brittle Shell Calls:**
  - `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py verdict --card <card id>` (line 26)
  - `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" crew_card.py lesson --role <role> --text "..."` (line 62)
- **Defects & Gaps:**
  - Script proof creation under `.crew/` uses `write_file` (good), but the verdict check is locked into the brittle `crew-run.sh` invocation.
  - Lacks clean python fallback handling or native status checks.
  - Description trigger exceeds 60 characters.

---

## 3. Tool-First Modernization Architecture

To eliminate brittle shell execution while ensuring continuous backwards compatibility across environments (POSIX, Git Bash on Windows, Linux, macOS), the updated skills must embody the following deterministic regulations:

### Regulation 1: The Tool-First Hierarchy
1. **Priority 1 (Native Typed Tools):**
   - For board mutations and queries: Use native `kanban_create`, `kanban_show`, `kanban_complete`, `kanban_block`, `kanban_request_review`, `kanban_request_changes`, `kanban_comment`, `kanban_list`.
   - For OpenSpec lifecycle operations: Use `openspec_change_create`, `openspec_validate`, `openspec_status`, `openspec_instructions`, `openspec_show`.
   - For file and inspection operations: Use `read_file`, `write_file`, `patch`, `search_files`.
   - For contextual facts: Read directly from injected `<crew-facts>` blocks rather than shelling out to CLI probes.
2. **Priority 2 (Clean Python Invocations):**
   - When running Crew-specific utilities (`crew_diagnose.py`, `crew_card.py verdict`, `crew_card.py watch`, `crew_card.py lesson`), execute using the current interpreter environment:
     ```bash
     python "$HERMES_HOME/plugins/crew/scripts/<script>.py" [args...]
     ```
     or invoke via `crew-run.sh` where platform-specific interpreter resolution is strictly necessary.
3. **Priority 3 (Graceful CLI Fallback):**
   - If a typed tool is unavailable in the session toolset or encounters a platform refusal, fall back to the CLI command while observing Windows/POSIX argument quoting rules.

### Regulation 2: Zero-Checkout Invariant Enforcement
All updated skills must explicitly reinforce the Zero-Checkout Invariant:
- Primary checkouts (`O:/workspaces`, `O:/workspaces/oss/crew`, `O:/workspaces/oss/hermes-agent`, `O:/workspaces/oss/hermes-nerve`) MUST stay on `main`.
- Any branch work MUST take place in an isolated worktree under `O:/workspaces/.worktrees/<name>`.

### Regulation 3: Skill Frontmatter & Trigger Compliance
Per Hermes skill authoring guidelines:
- YAML frontmatter must start at byte 0 with `---` and close with `\n---\n`.
- The `description` field must start with a concise, self-contained trigger of <= 60 characters:
  - `crew`: `Use when running /crew. Coordinator intake & contract.` (55 chars)
  - `crew-diagnose`: `Use when /crew-diagnose [state]. Read-only card diagnosis.` (58 chars)
  - `crew-no-spec`: `Use when /crew-no-spec <ask>. Fast-track direct card intake.` (59 chars)
  - `crew-verifier`: `Use when verifying an independent card. Proof-first review.` (59 chars)
- Version field in all skills must strictly match `plugin.yaml` (`0.9.12`).

---

## 4. Next Steps for OpenSpec Proposal

1. Create OpenSpec change `crew-skills-regulations` under `openspec/changes/crew-skills-regulations/`.
2. Draft the 4 required OpenSpec artifacts:
   - `proposal.md`: Problem statement, scope, proposed modernization regulations.
   - `specs/crew-skills-regulations/spec.md`: Formal behavioral requirements and scenarios for tool-first routing, CLI fallback, and frontmatter compliance.
   - `design.md`: Technical architecture, execution precedence matrix, Windows path escaping mitigations.
   - `tasks.md`: Verifiable implementation checklist with exact proof commands.
3. Apply changes to `skills/crew/SKILL.md`, `skills/crew-diagnose/SKILL.md`, `skills/crew-no-spec/SKILL.md`, and `skills/crew-verifier/SKILL.md`.
4. Run strict validation with `openspec validate crew-skills-regulations --strict` and execute test suite (`pytest tests/test_crew_versions.py tests/test_crew_run_launcher.py`).
