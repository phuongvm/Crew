# Final acceptance review — Crew repository clean state and test suite (R4)

**Card:** `t_677dd0b6`  
**Reviewer:** `reviewer`  
**Repository:** `O:/workspaces/oss/crew`  
**Commit inspected:** `902012f` on `main`  
**Verdict: REJECTED**

## Acceptance decision

The acceptance requirement is conjunctive: a clean working tree on `main`, a passing **182/182 focused suite**, and zero remaining repository contradictions. It is not satisfied.

## Independent evidence

| Criterion | Result | Reproduction / raw result |
|---|---|---|
| Primary checkout branch | PASS | `git -C O:/workspaces/oss/crew branch --show-current` → `main` |
| Zero-Checkout boundary | PASS | `O:/workspaces`, `oss/hermes-agent`, and `oss/hermes-nerve` each reported `main`; Crew worktree branches are listed under `O:/workspaces/.worktrees/` rather than the Crew primary checkout. |
| Clean Crew working tree | **FAIL** | `git -C O:/workspaces/oss/crew status --short` → `?? reviews/findings-crew-verify-skills-update-r3.md` |
| Focused-suite claim | **NOT PROVED** | The exact claimed `182/182` command is not specified by the contract and is not encoded in repository test configuration. The independently run taxonomy-focused set passes, but it contains only `94` tests: `python -m unittest tests/test_role_contracts.py tests/test_crew_versions.py tests/test_crew_two_stage.py tests/test_extended_tools.py` → `Ran 94 tests in 5.786s`, `OK` (rc 0). This cannot establish 182/182. |
| Repository suite / contradiction gate | **FAIL** | `python -m unittest discover -s tests -p 'test_*.py'` → rc `1`; `Ran 1046 tests in 59.468s`; `FAILED (failures=9, errors=88, skipped=3)`. Representative failures include `test_crew_desktop_plugin` (missing `Codicon` export), `test_crew_intake_create` (expected verifier value mismatch), and multiple database-opening failures in board-dependent tests. |
| Taxonomy contract consistency (bounded source/test check) | PASS, non-sufficient | `REFERENCE.md:152-157` documents all five modes, including direct verifier completion for `agent`; `contracts.py:638-651` renders that lifecycle. The 94-test focused suite above passes. This does not override the failing full suite or unclean checkout. |

## Findings

### [Severity: High] Clean-state requirement is false

`git status --short` identifies the untracked `reviews/findings-crew-verify-skills-update-r3.md`. The parent handoff described an exception for that file, but this card's literal Done-when clause requires a **clean working tree** and contains no exception. Therefore the condition is not met.

### [Severity: High] The required 182/182 result is not reproducible from this card

The contract supplies no exact focused-test command. The nearest explicit relevant suite in repository history executes 94 tests, not 182. A passing 94-test result is evidence for that bounded suite only. It cannot substantiate the declared 182/182 acceptance result.

### [Severity: High] Repository-wide execution demonstrates unresolved failures

The full deterministic discovery suite exits nonzero with 9 failures and 88 errors. Even if some failures are environment-dependent, the requested acceptance says “zero remaining contradictions in repository” and does not authorize a baseline exception or exclude the failing tests. No green repository-suite acceptance claim is supportable.

## Required remediation before re-review

1. Remove, commit, or explicitly amend the contract to exclude every untracked file; then provide `git status --short` with no output.
2. Put the exact 182-test focused command in the card contract or a versioned test target, and independently run it to an exit-0 result showing `Ran 182 tests`.
3. Resolve the full-suite failures or obtain a Commander-approved, versioned exclusion/baseline policy that names each excluded test and distinguishes environment limitations from product defects.
4. Re-run final acceptance from the primary Crew checkout after the above evidence exists.

## Scope and reviewer boundary

No implementation, configuration, service, branch, or commit was modified by the reviewer. This finding is based on fresh commands executed in the primary Crew checkout and read-only source inspection.
