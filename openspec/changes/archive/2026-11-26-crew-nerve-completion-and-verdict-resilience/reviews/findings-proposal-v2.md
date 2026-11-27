# Stage 1C Proposal Review: `crew-nerve-completion-and-verdict-resilience` (Round 2)

Verdict: APPROVED

- **Change**: `crew-nerve-completion-and-verdict-resilience` (`O:/workspaces/oss/crew/openspec/changes/crew-nerve-completion-and-verdict-resilience/`)
- **Reviewer**: `@reviewer` (independent two-axis Stage 1C re-review)
- **Date**: 2026-11-26
- **Inputs Inspected**: `#7` (`findings-proposal-v1.md`), `#8` (`@designer` remediation delivery), `proposal.md`, `specs/{proof-safety,crew-extended-tools,nerve-completion-verdict-resilience,crew-heal-and-stop-resilience}/spec.md`, `design.md`, `tasks.md`, and live source/tests.
- **OpenSpec Strict Validation Re-Proof**:
  - Command: `Set-Location O:\workspaces\oss\crew; C:\nvm4w\nodejs\openspec.cmd validate crew-nerve-completion-and-verdict-resilience --strict --json`
  - Exit Code: `0` (`"valid": true`, `"issues": []`, `"passed": 1`, `"failed": 0`, `durationMs: 27`)

---

## Round 1 Remediation Verification

| Prior Finding | Severity | Verification Status | Verified On-Disk Evidence |
| :--- | :--- | :--- | :--- |
| **C2-1** (`Verify: agent` vs `independent`/`dual` separation) | CRITICAL | **RESOLVED** | `proposal.md:22`, `specs/crew-heal-and-stop-resilience/spec.md:8-24`, `design.md:175-193`, `tasks.md:87-105` cleanly split `VERIFIER_VERIFY_MODES = ("independent", "agent", "dual")` / `uses_verifier_lane()` (`closer_profiles()`, `verifier_block()`) from `TWO_STAGE_VERIFY_MODES = ("independent", "dual")` / `uses_review_handoff()` (`hand_to_writer()`, `repin_for_review()`, `send_to_verifier()`), keeping `hand_to_writer()` a safe no-op on standalone `Verify: agent` (`Role: verifier`). |
| **C2-2** (`crew_safety` mock seams & `HERE` `sys.path` guard) | CRITICAL | **RESOLVED** | `design.md:75, 90` and `tasks.md:28-36` specify the `HERE` `sys.path` guard before `import crew_proc`, align `tests/test_crew_proc.py:75-93` and `tests/test_crew_safety.py:511-534` mock seams to `crew_safety.crew_proc.run_bounded`, and include both suites in Task `1.2`'s `Proof:` command. |
| **C2-3** (`crew_verdict_cli` FAIL drop & `observe_test_result` routing) | CRITICAL | **RESOLVED** | `specs/nerve-completion-verdict-resilience/spec.md:36-44`, `design.md:139-160`, `tasks.md:67-79` explicitly update `deterministic.py:108` (`tn not in {"crew_verdict", "crew_verdict_cli"}`), `deterministic.py:170` (`tn in {"crew_verdict", "crew_verdict_cli"}`), and `crew_card.py verdict` text parsing (`verdict: PASS` / `verdict: FAIL`, `rc=0|1|3`). |
| **W1-1** (Unambiguous test file & Slice 1 scope) | WARNING | **RESOLVED** | `tasks.md:21, 26, 36` unconditionally targets `tests/test_crew_run_proof_resilience.py` and runs all 6 relevant Crew safety/proc suites. |
| **W1-2** (`facts.parked: true` schema alignment) | WARNING | **RESOLVED** | `specs/crew-extended-tools/spec.md:17` and `design.md:259` clarify `facts.parked: true` matching `native_tools.py:831-838` and `crew_stop.py:349`. |
| **W2-1** (`advanced_override_sources` isolation) | WARNING | **RESOLVED** | `specs/nerve-completion-verdict-resilience/spec.md:52, 63`, `design.md:31, 165-166`, `tasks.md:70, 80` introduce `ResolvedNerveConfig.advanced_override_sources` so `override_sources` (`module_override_sources`) stays module-scoped. |
| **W2-2** (`park_card()` retry-once alignment) | WARNING | **RESOLVED** | `design.md:22, 257, 271` and `tasks.md:124` align on one retry after `0.2s` backoff on transient lock failure. |
| **W2-3** (Wrapper token headroom) | WARNING | **RESOLVED** | `design.md:104-105` documents `8,000`-char `state` + wrapper headroom under `8,192` tokens; `tasks.md:46` enforces `safe_json_len(state) + len(instructions) <= 9500`. |

---

## Axis 1 & Axis 2 Final Check

- **Axis 1 (Governance, Executability & Pre-Merge Safety)**: **PASS**
  - Single Target Invariant verified (`rg` returned zero mirrors across `O:/workspaces/openspec`, `oss/hermes-nerve/openspec`, `oss/hermes-agent/openspec`).
  - Pre-Merge Safety Gate verified: `specs/crew-extended-tools/spec.md` preserves all 3 baseline scenarios of `Stop Card Tool` verbatim and adds `Agent parks a review-lane crew card`; `specs/proof-safety/spec.md` uses `## ADDED Requirements` only.
  - Zero stale references (`test_crew_resilience_p0_p1` / `override_sources["work_supervision_mode"]`), zero plaintext secrets, all tasks bound to `O:/workspaces/.worktrees/wt-{crew,nerve}-resilience` with ABI-isolated `-B -E -m pytest -p no:cacheprovider` proofs.
- **Axis 2 (Technical Fidelity & Seam Accuracy)**: **PASS**
  - Zero CRITICAL defects remaining; all 4 designs (`P0-1`, `P0-2`, `P1-3`, `P1-4`) match verified live source signatures, test fixtures, and watchdog invariants (`CREW-INV-1..8`, `NERVE-INV-1..7`).
  - **Advisory Note (INFO)**: `design.md:319` (`$InvariantTests` in §6) lists `tests/test_crew_run_proof_resilience.py`, `tests/test_crew_verifier_block.py`, and `tests/test_crew_stop_park.py` while `tasks.md:133` notes adding new Crew invariant tests; during Phase 2 Slice 6 (`6.1`), ensure `test_crew_proc.py` / `test_crew_safety.py` Windows-safe subsets (or `test_crew_run_proof_resilience.py` + `test_crew_verifier_block.py` + `test_crew_stop_park.py`) are verified under `-GateOnly` on Windows without tripping pre-existing POSIX-only tests (`crew-upstream-sync/SKILL.md:122-124`).

Ready for Stage 2 implementation under §9 isolated worktrees.
