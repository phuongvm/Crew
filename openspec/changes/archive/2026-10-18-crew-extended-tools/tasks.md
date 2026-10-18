# Tasks: Extended Native Tools for Crew Plugin

## 1. Contracts

- [x] 1.1 Add `is_valid_card_id`, `is_valid_worktree_name`, `branch_name_gaps`, `lesson_gaps`, `change_request_gaps` to `oss/crew/contracts.py`
- [x] 1.2 Add `PlanSplitSpec` (from_dict, validate_gaps, to_dict) that drops owner-only fields and refuses closeout children

## 2. Core ops

- [x] 2.1 Implement `crew_stop_card` schema and handler (park / archive / dry run, crew-card guard, per-call board binding restored)

## 3. Pipeline ops

- [x] 3.1 Implement `crew_review_handoff` (Verify-line routing, repin + lift into review, preview action)
- [x] 3.2 Implement `crew_request_changes` (reason gate, kernel request_changes, refused outside a review run)
- [x] 3.3 Implement `crew_plan_split` (PlanSplitSpec validation, run_plan, dry run by default)

## 4. Workspace ops

- [x] 4.1 Implement `crew_worktree_create` via `git_safe` with protected-branch, name, base, path and overlap guards
- [x] 4.2 Implement `crew_worktree_cleanup` with registered-path, main-worktree, dirty and protected-branch guards

## 5. Intelligence ops

- [x] 5.1 Implement `graph_to_mermaid` and `crew_flow_graph` (mermaid | json)
- [x] 5.2 Implement `crew_lesson_record` (add | show) over `crew_lessons`

## 6. Registration

- [x] 6.1 Add `CREW_EXTENDED_TOOLS` and `register_extended_tools(ctx)`; call it from `register(ctx)` in `oss/crew/__init__.py`
- [x] 6.2 Declare the 8 tools in `oss/crew/plugin.yaml` `provides_tools`

## 7. Verification

- [x] 7.1 Add `oss/crew/tests/test_extended_tools.py` (registration, contracts, each tool on a throwaway board / repo / lessons home)
- [x] 7.2 Run `pytest tests/test_extended_tools.py` and the neighbouring native-tool, stop, lessons and graph suites
- [x] 7.3 Run `openspec validate crew-extended-tools --strict`
