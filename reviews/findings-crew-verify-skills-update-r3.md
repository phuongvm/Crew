# Final verification: five-mode taxonomy, `REFERENCE.md`, and commit state

## Verdict: REJECTED

## Scope and acceptance criteria

- `REFERENCE.md` must align with the canonical five-mode verification taxonomy and both dual-review topologies.
- `1b61b79` must be the clean `main` integration state.
- The requested `175/175` tests must pass.
- Repository guidance and rendered lifecycle contract must not contradict the taxonomy.

## Evidence

### Confirmed

1. `git rev-parse HEAD` returned `1b61b7959d66668d3b7ecdde3fd67a910064885f`, and `git show -s 1b61b79` identifies the intended taxonomy/dashboard commit on `main`.
2. `REFERENCE.md:152-157` now enumerates `proof`, `independent`, `agent`, `dual`, and `closeout`; it also defines Single-Card Dual and the two-card chained pipeline at `REFERENCE.md:156`.
3. `REFERENCE.md:155` specifies the standalone `agent` lifecycle: verifier-owned findings, `crew_verdict`, direct `kanban_complete`, and refusal of `crew_review_handoff`.
4. Renderer and semantic-contract alignment is present in `contracts.py:638-651`, `scripts/crew_card.py:864-877`, and `tests/test_role_contracts.py:473-575`.
5. Independent focused execution passed: `python -m unittest tests/test_role_contracts.py tests/test_crew_versions.py tests/test_crew_two_stage.py tests/test_extended_tools.py tests/test_crew_dashboard_customization.py tests/test_crew_tools_guard.py -q` -> `Ran 182 tests ... OK`, exit 0. `git diff --check daa9340..1b61b79` also exited 0.
6. The Zero-Checkout branch gate passed: all four protected production checkouts reported `main`.

### Blocking findings

#### [Severity: High] `main` is not clean at the claimed integration commit

The direct status probe in `O:/workspaces/oss/crew` returned:

```text
?? fixtures/
?? reports/snapshots/kanban_telemetry_snapshot.db
BRANCH=main
HEAD=1b61b7959d66668d3b7ecdde3fd67a910064885f
```

The required commit is checked out, but the production checkout contains two untracked paths. This does not meet a literal "clean commit state 1b61b79 on main" acceptance criterion or the clean-primary invariant in `O:/workspaces/rules/AGENTS.md:213-219`.

#### [Severity: High] Full suite does not establish the requested `175/175` result

Independent full-suite execution of `python -m unittest discover -s tests -p 'test*.py' -q` exited 1 after `Ran 1046 tests in 58.991s` with `FAILED (failures=9, errors=88, skipped=3)`. Recurrent errors originate from `tests/kernel_board.py:29` opening temporary boards read-only (`sqlite3.OperationalError: unable to open database file`); additional observed failures include desktop SDK export drift and skill-slimming assertions. Regardless of whether some are environmental/pre-existing, this run cannot prove the card's required `175/175 tests passing` claim.

## Required remediation

1. Restore or otherwise account for the two untracked paths so the protected Crew checkout is clean while remaining at `1b61b79` on `main`.
2. Supply and independently reproduce the exact 175-test command/environment, or remediate the full-suite failures and update the acceptance criterion with explicit Commander approval. Do not claim 175/175 from the successful 182-test focused suite.

## Review boundary

No implementation, skills, commit, configuration, or service changes were made by Reviewer. This artifact records a rejected acceptance audit; its existence-only proof does not convert the substantive verdict to approval.
