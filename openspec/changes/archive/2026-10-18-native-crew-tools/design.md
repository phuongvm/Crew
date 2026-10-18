# Design: Native Hermes Tools for Crew Plugin

## Context

Crew coordinates multi-agent Kanban operations in Hermes. To date, all card creation, diagnostics, verification, and status monitoring operations performed by AI agents have relied on launching terminal commands (`terminal(command='python scripts/crew_card.py ...')`). On Windows hosts running MSYS2 bash, this architecture encounters severe path mismatches, argument truncations, shell quoting errors, and interactive write-approval prompts. 

By providing native tools registered via `ctx.register_tool()`, agents can invoke Crew primitives directly as structured tool calls with JSON schema validation, avoiding shell subprocess overhead entirely.

## Goals / Non-Goals

**Goals:**
- Provide four first-class native tools: `crew_card_create`, `crew_diagnose`, `crew_verdict`, and `crew_status`.
- Validate input parameters using rigorous JSON schemas.
- Route requests directly to Crew's internal Python functions without subprocess shell overhead.
- Ensure 100% compatibility with Windows and POSIX environments.
- Provide comprehensive automated test coverage for tool registration and handler execution.

**Non-Goals:**
- Removing or deprecating the existing CLI commands (`scripts/crew_card.py`, `scripts/crew_diagnose.py`) or slash commands (`/crew-status`, etc.); they remain intact for human operators and legacy workflows.
- Rewriting the underlying Kanban database schema or task state machine.
- Introducing direct LLM model calls into tool handlers (all tools remain deterministic).

## Decisions

### Decision 1: Dedicated `native_tools.py` Module
- **Choice**: Implement schemas and handlers in `oss/crew/native_tools.py` and import/register them from `oss/crew/__init__.py`.
- **Rationale**: Keeps `__init__.py` focused on lifecycle hooks and plugin registration. Isolates schema definitions and handler adapters into a clean, testable module.
- **Alternatives Considered**: Inlining all schemas and handlers directly in `__init__.py` was rejected due to file size (already 1600+ lines) and reduced testability.

### Decision 2: Reuse Proven Backend Primitives
- **Choice**: Adapt existing functions in `crew_card.py` (`open_card`, `create_card`, `cmd_verdict`, `status_cards`) and `crew_diagnose.py` (`board_rows`, `cards_from_rows`, `render`).
- **Rationale**: Avoids logic duplication. The existing scripts have extensive test suites and edge-case handling for budget calculation, proof command resolution, and safety filtering.
- **Alternatives Considered**: Rewriting database queries from scratch was rejected because it introduces risk of behavior divergence between CLI scripts and native tools.

### Decision 3: Structured JSON and Human-Readable Formats
- **Choice**: Allow `format="text"` or `format="json"` on read tools (`crew_diagnose`, `crew_status`), defaulting to compact text while allowing structured data when required.
- **Rationale**: Minimizes context token bloat when plain summaries suffice, while giving agents access to raw JSON when programmatic downstream filtering is needed.

### Decision 4: Safe Exception Trapping
- **Choice**: All handlers catch top-level exceptions and return informative JSON error dictionaries (e.g. `{"error": "...", "status": "failed"}`) rather than allowing unhandled exceptions to crash the agent turn.
- **Rationale**: Conforms to Hermes tool conventions and prevents session disruption.

## Risks / Trade-offs

- **[Risk] Database Concurrency / SQLite Locks** → **Mitigation**: All read queries use `mode=ro` URI connections and short-lived transactions. Write operations (`crew_card_create`, `crew_verdict`) follow existing transaction retry logic.
- **[Risk] Path/Environment Discrepancies** → **Mitigation**: Use existing path resolution helpers (`kanban_db()`, `base_home()`, `hermes_home()`) that already handle Windows %LOCALAPPDATA% and POSIX `~/.hermes`.
- **[Risk] Proof Command Escaping in `crew_verdict`** → **Mitigation**: `crew_verdict` invokes `crew_safety.run_proof`, preserving all existing safety and auto-routing checks.

## Migration Plan

1. Create `oss/crew/native_tools.py` with the 4 tool definitions and handler functions.
2. Update `oss/crew/__init__.py` to import and call `register_native_tools(ctx)` within `register(ctx)`.
3. Add unit and integration tests in `oss/crew/tests/test_native_tools.py`.
4. Validate with `pytest` and `openspec validate native-crew-tools --strict`.
5. Rollback strategy: If issues arise, native tool registration can be disabled via feature flag or reverting the `register_native_tools` call in `__init__.py` without affecting CLI scripts.

## Open Questions

- None. The schema design and internal APIs are already established in sibling plugins and Crew's internal scripts.
