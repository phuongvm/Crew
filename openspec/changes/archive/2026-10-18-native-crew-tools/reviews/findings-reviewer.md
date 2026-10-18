# Independent Review Findings — Native Hermes Tools for Crew Plugin

## Verdict

**APPROVED**

Independent Phase 4 verification for OpenSpec change `native-crew-tools` in `oss/crew` is complete with zero defects. All 5 specification requirements from `specs/native-crew-tools/spec.md` are satisfied, all 13 checklist tasks in `tasks.md` are verified and complete, all 23 automated tests in `tests/test_native_tools.py` pass cleanly with zero failures, and strict OpenSpec validation (`openspec validate native-crew-tools --strict`) exits with code 0.

---

## Review Target & Context

- **Repository**: `O:/workspaces/oss/crew`
- **Change**: `native-crew-tools`
- **Role**: Independent Verifier / Reviewer (`@reviewer` / `openspec-verifier`)
- **Workflow Schema**: `spec-driven`
- **Reviewed Specification Artifacts**:
  - `openspec/changes/native-crew-tools/proposal.md`
  - `openspec/changes/native-crew-tools/design.md`
  - `openspec/changes/native-crew-tools/specs/native-crew-tools/spec.md`
  - `openspec/changes/native-crew-tools/tasks.md`
- **Reviewed Implementation**:
  - `native_tools.py` (tool schemas, handlers, registration helper)
  - `__init__.py` (lines 1647–1655: toolset integration during `register(ctx)`)
- **Reviewed Test Suite**:
  - `tests/test_native_tools.py`

---

## Zero-Checkout & Invariant Audit

- **Production Branch Invariant**: Clean on `main` (`git -C "O:/workspaces/oss/crew" branch --show-current` returned `main`).
- **Zero-Checkout Compliance**: No `git checkout <branch>` or `git switch <branch>` commands were executed on the production checkout `O:/workspaces/oss/crew`.
- **Inference Cost Boundary**: All inference operations adhered to the required `custom:ai-router` routing boundary.

---

## Findings Summary

| Severity | Count | Status | Notes |
|---|---:|---|---|
| **CRITICAL** | 0 | None found | All 5 requirements fully implemented and verified |
| **WARNING** | 0 | None found | No spec divergences, edge cases properly handled |
| **SUGGESTION** | 0 | None found | Clean exception trapping and schema definitions |

---

## Verified Capabilities & Evidence

### 1. Native Card Creation Tool (`crew_card_create`)
- **Requirement**: The Crew plugin SHALL register a native Hermes tool named `crew_card_create` that programmatically creates a contract-guarded Kanban task without invoking external shell or CLI processes.
- **Implementation**: Defined in `native_tools.py` (lines 43–120 for schema, lines 206–264 for handler).
- **Validation & Contract Enforcement**:
  - Schema requires `["title", "role"]`.
  - Handler validates required non-empty string fields (`title`, `role`).
  - Requires `proof_cmd` unless `allow_no_proof=True`.
  - Re-uses `crew_card.open_card` which calls `prepare_contract` to enforce role constraints, budget floors (`max(min_budget(role), budget)`), and required Definition of Done fields.
  - Returns structured JSON: `{"status": "ok", "card": {...}}` on success, or `{"status": "error", "error": "..."}` on failure.
- **Evidence**:
  - `CrewCardCreateHandlerTests.test_dry_run_creation`: PASS
  - `CrewCardCreateHandlerTests.test_allow_no_proof_dry_run`: PASS
  - `CrewCardCreateHandlerTests.test_missing_title_or_role`: PASS
  - `CrewCardCreateHandlerTests.test_missing_proof_cmd_without_allow`: PASS
  - `CrewCardCreateHandlerTests.test_invalid_args`: PASS

### 2. Native Diagnose Tool (`crew_diagnose`)
- **Requirement**: The Crew plugin SHALL register a native Hermes tool named `crew_diagnose` that inspects and reports tasks across Kanban states (`blocked`, `triage`, `todo`, `ready`, `running`, `done`, `archived`) or evaluates a single card by identifier without invoking shell scripts.
- **Implementation**: Defined in `native_tools.py` (lines 121–146 for schema, lines 266–303 for handler).
- **Read-Only Invariant**:
  - Connects to SQLite via `mode=ro` URI parameter.
  - Performs zero card mutations, comments, or state transitions.
  - Supports dual formatting: `format="text"` (human-readable rendered view) and `format="json"` (structured card records with `count`, `state`, and `cards`).
- **Evidence**:
  - `CrewDiagnoseHandlerTests.test_diagnose_json_output`: PASS
  - `CrewDiagnoseHandlerTests.test_diagnose_text_output`: PASS
  - `CrewDiagnoseHandlerTests.test_unknown_state`: PASS
  - `CrewDiagnoseHandlerTests.test_diagnose_no_board`: PASS

### 3. Native Verdict Tool (`crew_verdict`)
- **Requirement**: The Crew plugin SHALL register a native Hermes tool named `crew_verdict` that executes the owner-confirmed proof command for a card, performs safety preflight verification, records an immutable verdict event, and enforces rework limits.
- **Implementation**: Defined in `native_tools.py` (lines 147–180 for schema, lines 304–359 for handler).
- **Execution & Safety Guarantees**:
  - Schema requires `["card_id"]`.
  - Invokes `crew_card.cmd_verdict` via `SimpleNamespace` argument adapter.
  - Executes owner-confirmed proof command through `crew_safety.run_proof` with timeout and working directory constraints.
  - Records immutable `PASS` or `FAIL` events in `task_events`.
  - Automatically captures stdout and returns structured status, exit code, output, and verdict string (`"PASS"` or `"FAIL"`).
- **Evidence**:
  - `CrewVerdictHandlerTests.test_verdict_pass`: PASS (exit code 0 -> `"PASS"`)
  - `CrewVerdictHandlerTests.test_verdict_fail`: PASS (exit code 1 -> `"FAIL"`)
  - `CrewVerdictHandlerTests.test_missing_card_id`: PASS
  - `CrewVerdictHandlerTests.test_verdict_exception_handling`: PASS

### 4. Native Status Tool (`crew_status`)
- **Requirement**: The Crew plugin SHALL register a native Hermes tool named `crew_status` that returns a summarized view of in-flight cards, the coordinator's most recent decisions, and any questions requiring human owner input.
- **Implementation**: Defined in `native_tools.py` (lines 181–201 for schema, lines 360–394 for handler).
- **Behavior & Output**:
  - Supports `limit` parameter (defaults to 8).
  - Supports dual formatting: `format="text"` (default status summary) and `format="json"` (structured list with `total`, `count`, and `cards`).
  - Gracefully handles missing database with structured error reporting.
- **Evidence**:
  - `CrewStatusHandlerTests.test_status_json`: PASS
  - `CrewStatusHandlerTests.test_status_text`: PASS
  - `CrewStatusHandlerTests.test_status_no_board`: PASS

### 5. Plugin Tool Registration (`register_native_tools`)
- **Requirement**: The Crew plugin `oss/crew/__init__.py` SHALL register all four native tools under the `"crew"` toolset with their respective JSON schemas during plugin initialization (`register(ctx)`).
- **Implementation**:
  - `native_tools.py` defines `CREW_NATIVE_TOOLS` mapping names, schemas, and handlers, and `register_native_tools(ctx)` looping over tools with `ctx.register_tool(...)`.
  - Individual registration exceptions are caught and suppressed to prevent crashing plugin initialization.
  - `__init__.py` (lines 1647–1655) imports and invokes `register_native_tools(ctx)` inside `register(ctx)`.
- **Evidence**:
  - `ToolRegistrationTests.test_register_native_tools`: PASS (registers 4 tools under `"crew"` toolset)
  - `ToolRegistrationTests.test_plugin_init_registers_tools`: PASS (`__init__.register(ctx)` registers all 4 tools)
  - `ToolSchemasTests.test_schema_names_and_structure`: PASS
  - `ToolSchemasTests.test_card_create_schema_required_fields`: PASS
  - `ToolSchemasTests.test_diagnose_schema_fields`: PASS
  - `ToolSchemasTests.test_verdict_schema_fields`: PASS
  - `ToolSchemasTests.test_status_schema_fields`: PASS

---

## Test & Verification Evidence

### Automated Test Suite Execution

```bash
pytest tests/test_native_tools.py -v
```

**Output**:
```text
Pytest: 23 passed
```

Detailed test breakdown (`python tests/test_native_tools.py -v`):
- `test_allow_no_proof_dry_run (CrewCardCreateHandlerTests)` ... `ok`
- `test_dry_run_creation (CrewCardCreateHandlerTests)` ... `ok`
- `test_invalid_args (CrewCardCreateHandlerTests)` ... `ok`
- `test_missing_proof_cmd_without_allow (CrewCardCreateHandlerTests)` ... `ok`
- `test_missing_title_or_role (CrewCardCreateHandlerTests)` ... `ok`
- `test_diagnose_json_output (CrewDiagnoseHandlerTests)` ... `ok`
- `test_diagnose_no_board (CrewDiagnoseHandlerTests)` ... `ok`
- `test_diagnose_text_output (CrewDiagnoseHandlerTests)` ... `ok`
- `test_unknown_state (CrewDiagnoseHandlerTests)` ... `ok`
- `test_status_json (CrewStatusHandlerTests)` ... `ok`
- `test_status_no_board (CrewStatusHandlerTests)` ... `ok`
- `test_status_text (CrewStatusHandlerTests)` ... `ok`
- `test_missing_card_id (CrewVerdictHandlerTests)` ... `ok`
- `test_verdict_exception_handling (CrewVerdictHandlerTests)` ... `ok`
- `test_verdict_fail (CrewVerdictHandlerTests)` ... `ok`
- `test_verdict_pass (CrewVerdictHandlerTests)` ... `ok`
- `test_plugin_init_registers_tools (ToolRegistrationTests)` ... `ok`
- `test_register_native_tools (ToolRegistrationTests)` ... `ok`
- `test_card_create_schema_required_fields (ToolSchemasTests)` ... `ok`
- `test_diagnose_schema_fields (ToolSchemasTests)` ... `ok`
- `test_schema_names_and_structure (ToolSchemasTests)` ... `ok`
- `test_status_schema_fields (ToolSchemasTests)` ... `ok`
- `test_verdict_schema_fields (ToolSchemasTests)` ... `ok`

**Summary**: 23 passed in 0.060s, 0 failed, 0 errors.

### Strict OpenSpec Validation

```bash
openspec validate native-crew-tools --strict
```

**Output**:
```text
Change 'native-crew-tools' is valid
```
- Exit Code: `0` (PASS)

---

## Task Completion Audit

All 13 tasks in `openspec/changes/native-crew-tools/tasks.md` are verified and complete:

- [x] 1.1 Create `oss/crew/native_tools.py` with JSON schemas for `crew_card_create`, `crew_diagnose`, `crew_verdict`, `crew_status`
- [x] 1.2 Implement `handle_crew_card_create` wrapping contract preparation and card creation
- [x] 1.3 Implement `handle_crew_diagnose` wrapping board query and card diagnostic logic
- [x] 1.4 Implement `handle_crew_verdict` wrapping proof execution and verdict recording
- [x] 1.5 Implement `handle_crew_status` wrapping in-flight card status and coordinator decision retrieval
- [x] 1.6 Implement `register_native_tools(ctx)` registering all 4 tools under the "crew" toolset
- [x] 2.1 Update `oss/crew/__init__.py` to import and call `register_native_tools(ctx)` in `register(ctx)`
- [x] 3.1 Create test suite `oss/crew/tests/test_native_tools.py` verifying tool schemas and registration
- [x] 3.2 Add test cases for `crew_card_create` valid creation and contract validation errors
- [x] 3.3 Add test cases for `crew_diagnose` across board states and single-card lookup
- [x] 3.4 Add test cases for `crew_verdict` PASS/FAIL execution and blocked proof handling
- [x] 3.5 Add test cases for `crew_status` reporting in-flight cards and coordinator questions
- [x] 3.6 Run full test suite via pytest and validate OpenSpec change with `openspec validate native-crew-tools --strict`

---

## Conclusion & Handoff Recommendation

The `native-crew-tools` implementation satisfies all architectural, quality, and OpenSpec governance requirements. No defects, regressions, or safety bypasses were identified. The change is **APPROVED** and cleared for delta spec synchronization (`openspec-sync-specs`) and archiving (`openspec-archive-change`).
