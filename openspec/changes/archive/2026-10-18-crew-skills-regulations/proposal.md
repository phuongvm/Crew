## Why

Crew skills currently mandate complex, brittle shell command lines of the form `sh "$HERMES_HOME/plugins/crew/scripts/crew-run.sh" ...`. In Windows/MSYS and Git Bash environments, this causes subshell quotation stripping, path escaping bugs, and unnecessary security approval blocking. Furthermore, agents frequently default to terminal CLI commands instead of invoking typed native tools (`kanban_create`, `kanban_show`, `kanban_complete`, `kanban_block`, `openspec_*`, `read_file`, `write_file`), violating tool-first execution guidelines. Modernizing Crew skills establishes deterministic workflow regulations, enforces tool-first execution with graceful CLI fallbacks, aligns frontmatter triggers with Hermes discovery standards (<= 60 chars), and fixes version desynchronization across the package.

## What Changes

- **Tool-First Execution Hierarchy:** Update `skills/crew/SKILL.md`, `skills/crew-diagnose/SKILL.md`, `skills/crew-no-spec/SKILL.md`, and `skills/crew-verifier/SKILL.md` to instruct agents to use typed native tools whenever available, falling back to clean CLI invocations only when tools are absent.
- **Elimination of Brittle Shell Command Lines:** Replace nested subshell invocations (`sh "$HERMES_HOME/..."`) with robust direct interpreter commands or standardized platform helpers that avoid quote escaping bugs on Windows/MSYS.
- **Skill Frontmatter & Trigger Standardization:** Standardize YAML frontmatter across all 4 skills:
  - Enforce version `0.9.12` matching `plugin.yaml` (fixing the `0.9.0` version drift in `crew-no-spec`).
  - Restructure descriptions so the first sentence is a concise, self-contained trigger of <= 60 characters.
  - Ensure zero references to bare `python3` CLI command, adhering to `test_crew_run_launcher.py`.
- **Deterministic Workflow Regulations:**
  - Formalize Track A (OpenSpec 7-stage governance) and Track B (Fast-Track direct card) in `crew`.
  - Reiterate read-only execution constraints in `crew-diagnose`.
  - Enforce Turn-1 dispatch without chat execution in `crew-no-spec`.
  - Codify proof script creation (`write_file`), independent verification, and verdict recording in `crew-verifier`.
  - Reaffirm the Zero-Checkout invariant across all skills.

## Capabilities

### New Capabilities
- `crew-skills-regulations`: Modernized workflow regulations and tool-first execution contracts across Crew coordinator, diagnostic, fast-track, and verifier skills.

### Modified Capabilities
- None.

## Impact

- Affected files:
  - `skills/crew/SKILL.md`
  - `skills/crew-diagnose/SKILL.md`
  - `skills/crew-no-spec/SKILL.md`
  - `skills/crew-verifier/SKILL.md`
- Tests and verification:
  - `tests/test_crew_versions.py` (resolves version mismatch failure in `crew-no-spec`)
  - `tests/test_crew_run_launcher.py` (verifies absence of prohibited `python3` command strings)
  - `openspec validate crew-skills-regulations --strict`
