# Architecture Exploration: Native Hermes Tools for Crew Plugin

**Date:** 2026-10-18  
**Author:** AI Agent (Subagent `crew-native-tools`)  
**Status:** Approved for Proposal  
**Topic:** Transitioning Crew from CLI/Subshell execution to First-Class Hermes Native Tools (`ctx.register_tool`)

---

## 1. Executive Summary & Context

Crew is the multi-agent role and contract management system for Hermes Agent, orchestrating specialized profiles (`coordinator`, `worker`, `content`, `verifier`) over a Kanban spine. Historically, Crew exposed its capabilities to agents through two primary interfaces:
1. User-facing slash commands (`/crew-status`, `/crew-graph`, `/crew-stop`, `/crew-unstuck`) registered in `oss/crew/__init__.py` via `ctx.register_command`.
2. Model-facing skills (`crew`, `crew-diagnose`, `crew-verifier`) that instruct LLM agents to execute CLI python/shell scripts (`crew_card.py`, `crew-run.sh`, `crew_diagnose.py`) via the generic Hermes `terminal` tool.

While other Hermes plugins (such as `OpenSpec` with 21 tools, `S3` with 4 tools, and `DeskRPG` with 3 tools) expose structured, deterministic native tools directly in the agent's function-calling registry via `ctx.register_tool`, Crew has had zero native tools.

This exploration establishes the technical foundation for registering first-class native tools in the Crew plugin.

---

## 2. Problem Statement & Root Cause Analysis

### 2.1 The Terminal Subshell Bottleneck
When agents invoke Crew operations via the `terminal` tool (e.g., executing `python scripts/crew_card.py open ...` or `python scripts/crew_diagnose.py`), several failure modes arise:
1. **Windows Path Translation Failures**: On Windows 11 host environments running MSYS2/Git-Bash, POSIX `/c/Users/...` vs Windows `C:\Users\...` path discrepancies cause batch script launchers (`hermes.cmd`) to truncate arguments at newlines or fail path existence checks.
2. **Shell Quoting & Escaping Breakage**: Passing multi-line contract bodies, goals, complex regexes, or proof commands through nested bash quotes frequently triggers shell parsing errors, syntax errors, or accidental command substitution (`$()`).
3. **Smart Approval Hangs & Friction**: In interactive or semi-supervised modes, running shell commands prompts native write/terminal approval gates, hanging background agent dispatch or requiring redundant user confirmation.
4. **Token & Latency Overhead**: Subshell execution spawns heavy OS processes, loads the Python interpreter repeatedly, and passes raw terminal output instead of compact structured JSON into the model context.
5. **Lack of Type-Safe Schema Validation**: Subshell parameters cannot be schema-enforced by the LLM function calling engine before execution, leading to runtime CLI parse errors.

### 2.2 Sibling Plugin Precedents
- **OpenSpec Plugin**: Registers 21 native tools (`openspec_change_create`, `openspec_validate`, etc.) via `ctx.register_tool`, enabling schema validation and zero-subshell operation.
- **DeskRPG Plugin**: Registers `artifact_save`, `deskrpg_ask_user`, and `propose_kanban_card` via `ctx.register_tool(name, toolset, schema, handler, description, emoji)`.
- **Nerve Plugin**: Registers 16 typed decision and supervision tools (`nerve_decide`, `nerve_supervise_card`, etc.) via `ctx.register_tool`.

Crew must adopt this standard to ensure reliability, speed, and safety.

---

## 3. Investigation of Existing Script Entry Points

Inspection of `oss/crew/__init__.py` and `oss/crew/scripts/` reveals clean internal Python primitives that can be directly adapted into native tool handlers without modifying existing CLI behavior:

### 3.1 Card Creation (`crew_card.py`)
- **Primitives**: `prepare_contract(c, allow_no_proof=False)`, `create_card(...)`, `open_card(c, dry_run=False, ...)`
- **Behavior**: Validates contract fields (`role`, `goal`/`title`, `artifact`, `verify`/`proof_cmd`, `budget`), enforces budget floor, registers child tasks and event ledger, and inserts into `tasks` table in `kanban.db`.
- **Target Native Tool**: `crew_card_create(title, role, goal, artifact, verify, proof_cmd, budget, skills, parents, dry_run)`

### 3.2 System & Task Diagnosis (`crew_diagnose.py`)
- **Primitives**: `board_rows(state, card)`, `cards_from_rows(rows, now=None)`, `render(cards, state, card)`
- **Behavior**: Inspects SQLite database directly in read-only mode (`mode=ro`), parses task events, token expenditures, consecutive failures, and coordinator decisions across states (`blocked`, `triage`, `todo`, `ready`, `running`, `done`, `archived`).
- **Target Native Tool**: `crew_diagnose(state, card_id, format)`

### 3.3 Verification & Verdict Enforcement (`crew_card.py`)
- **Primitives**: `cmd_verdict(args)`, `record_verdict(card_id, command, rc, output, duration, by, for_event)`, `close_proof_command(card_id)`, `crew_safety.run_proof(...)`
- **Behavior**: Fetches owner-confirmed proof command from task metadata, enforces safety preflight (`check_proof`), runs the proof command, records the immutable PASS/FAIL verdict, and triggers automatic request-changes or hand-back after 2 fails.
- **Target Native Tool**: `crew_verdict(card_id, command, timeout, by, no_hand_back)`

### 3.4 In-Flight Board Status (`crew_card.py` & `__init__.py`)
- **Primitives**: `status_cards(limit=8)`, `status_text(limit=8)`
- **Behavior**: Reads active cards in flight (`triage`, `ready`, `running`, `blocked`, `review`), extracts latest coordinator decision, extracts pending owner questions, and formats concise status summary.
- **Target Native Tool**: `crew_status(limit, format)`

---

## 4. Proposed Native Tools Architecture

### 4.1 Modular Layout
To preserve clean separation of concerns and avoid bloat in `oss/crew/__init__.py`:
1. **`oss/crew/native_tools.py`**:
   - Contains JSON schemas (`CREW_CARD_CREATE_SCHEMA`, `CREW_DIAGNOSE_SCHEMA`, `CREW_VERDICT_SCHEMA`, `CREW_STATUS_SCHEMA`).
   - Implements handler functions `handle_crew_card_create`, `handle_crew_diagnose`, `handle_crew_verdict`, `handle_crew_status`.
   - Normalizes inputs, handles exceptions gracefully, and returns structured JSON or clean human-readable summaries.
2. **`oss/crew/__init__.py`**:
   - In `register(ctx)`:
     ```python
     from .native_tools import register_native_tools
     register_native_tools(ctx)
     ```
   - Each tool is registered under the `"crew"` toolset with its schema, description, and callable handler.
3. **`oss/crew/tests/test_native_tools.py`**:
   - Unit and integration tests mocking or exercising `kanban.db` and validating schema conformance, success execution, and error handling.

### 4.2 Security & Invariants
- **Zero-Checkout Invariant**: All implementation occurs directly on `origin/main` without switching branches.
- **Proof Safety Invariant**: `crew_verdict` strictly honors the owner-confirmed proof command and Hermes safety filters (`crew_safety`).
- **Fail-Safe Operation**: If the kanban database is not initialized or unreachable, tools return informative error messages rather than raising unhandled Python exceptions.
- **Zero Model Inference Boundary**: Native tools execute purely local deterministic Python logic; no direct model API calls are made.

---

## 5. Next Steps
1. Advance to Phase 2: OpenSpec change proposal `native-crew-tools` with:
   - `proposal.md`
   - `specs/native-crew-tools/spec.md`
   - `design.md`
   - `tasks.md`
2. Implement `native_tools.py` and hook into `__init__.py`.
3. Verify test coverage and validate via `openspec validate native-crew-tools --strict`.
