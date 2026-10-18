# Tasks: Native Hermes Tools for Crew Plugin

## 1. Native Tools Module Implementation

- [x] 1.1 Create `oss/crew/native_tools.py` with JSON schemas for `crew_card_create`, `crew_diagnose`, `crew_verdict`, `crew_status`
- [x] 1.2 Implement `handle_crew_card_create` wrapping contract preparation and card creation
- [x] 1.3 Implement `handle_crew_diagnose` wrapping board query and card diagnostic logic
- [x] 1.4 Implement `handle_crew_verdict` wrapping proof execution and verdict recording
- [x] 1.5 Implement `handle_crew_status` wrapping in-flight card status and coordinator decision retrieval
- [x] 1.6 Implement `register_native_tools(ctx)` registering all 4 tools under the "crew" toolset

## 2. Plugin Registration Integration

- [x] 2.1 Update `oss/crew/__init__.py` to import and call `register_native_tools(ctx)` in `register(ctx)`

## 3. Automated Test Suite & Verification

- [x] 3.1 Create test suite `oss/crew/tests/test_native_tools.py` verifying tool schemas and registration
- [x] 3.2 Add test cases for `crew_card_create` valid creation and contract validation errors
- [x] 3.3 Add test cases for `crew_diagnose` across board states and single-card lookup
- [x] 3.4 Add test cases for `crew_verdict` PASS/FAIL execution and blocked proof handling
- [x] 3.5 Add test cases for `crew_status` reporting in-flight cards and coordinator questions
- [x] 3.6 Run full test suite via pytest and validate OpenSpec change with `openspec validate native-crew-tools --strict`
