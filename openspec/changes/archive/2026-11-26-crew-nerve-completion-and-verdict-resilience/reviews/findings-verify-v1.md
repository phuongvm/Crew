# Phase 3 Implementation Review: `crew-nerve-completion-and-verdict-resilience` (Round 1)

Verdict: APPROVED

- **Change**: `crew-nerve-completion-and-verdict-resilience` (`O:/workspaces/oss/crew/openspec/changes/crew-nerve-completion-and-verdict-resilience/`)
- **Reviewer**: `@reviewer` (independent two-axis Phase 3 implementation audit)
- **Date**: 2026-11-26
- **Audited Targets**:
  - Crew worktree: `O:/workspaces/.worktrees/wt-crew-resilience` (`fix/crew-resilience` @ `53f0103c18e6ffc3c956f24f54fb0f34fadac764`, 13 files changed, `+594/-48`)
  - Nerve worktree: `O:/workspaces/.worktrees/wt-nerve-resilience` (`fix/nerve-resilience` @ `53bd61fce73e74a3c8d7003c69703b1c5623d824`, 5 files changed, `+1479/-56`)
  - Root watchdogs: `O:/workspaces/.agents/skills/{crew,nerve}-upstream-sync/{SKILL.md,scripts/daily-sync-watchdog.ps1}`

---

## Independent Verification Proof Ledger (Zero-Trust I/O)

1. **Crew Watchdog Gate (`-GateOnly`)**:
   - Command: `& "C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -File O:\workspaces\.agents\skills\crew-upstream-sync\scripts\daily-sync-watchdog.ps1 -GateOnly -Target O:\workspaces\.worktrees\wt-crew-resilience`
   - Result: Exit `0` — `CREW-INV-1..9` static anchors pass, `compiled 65`, `plugin.yaml: valid YAML manifest`, `probes failed: 0`, `127 passed, 1 warning, 2 subtests passed in 36.02s`, `[RESULT] GATE PASS target=O:\workspaces\.worktrees\wt-crew-resilience head=53f0103c18e6ffc3c956f24f54fb0f34fadac764`.
2. **Nerve Watchdog Gate (`-GateOnly`)**:
   - Command: `& "C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -File O:\workspaces\.agents\skills\nerve-upstream-sync\scripts\daily-sync-watchdog.ps1 -GateOnly -Target O:\workspaces\.worktrees\wt-nerve-resilience`
   - Result: Exit `0` — `NERVE-INV-1..8` static anchors pass, `compiled 89 files in memory`, `probes failed: 0`, `199 passed, 139 subtests passed in 19.92s`, `[RESULT] GATE PASS target=O:\workspaces\.worktrees\wt-nerve-resilience head=53bd61fce73e74a3c8d7003c69703b1c5623d824`.
3. **Additional Crew Suites (outside `$InvariantTests`)**:
   - Command: `O:\workspaces\oss\hermes-agent\.venv\Scripts\python.exe -B -E -m pytest -p no:cacheprovider -q tests/test_crew_proc.py tests/test_crew_safety.py tests/test_crew_heal.py tests/test_role_contracts.py tests/test_crew_two_stage.py tests/test_crew_coordinator.py` (in `wt-crew-resilience`)
   - Result: Exit `0` — `206 passed, 87 subtests passed in 14.55s`.
4. **Additional Nerve Slice 2 & 3 Suites**:
   - Command: `O:\workspaces\oss\hermes-agent\.venv\Scripts\python.exe -B -E -m pytest -p no:cacheprovider -q tests/test_completion_packet_and_cli_verdict.py tests/test_work_supervision.py tests/test_nervous.py tests/test_crew_dod_and_handoff.py tests/test_dev16_nerve_budget.py tests/test_shadow_completion_gate.py tests/test_sidecar_authority.py` (in `wt-nerve-resilience`)
   - Result: Exit `0` — `77 passed, 36 subtests passed in 25.48s`.
5. **Direct Crew Proof Scripts (Scratch Isolated)**:
   - `crew_heal_proof.py`: Exit `0` — 7/7 checks `PASS` (`PROOF OK`).
   - `crew_stop_proof.py` (pinned to scratch temp `crew_proof_board.init_board()` DB via `KANBAN_DB` & `HERMES_KANBAN_DB`, zero live `kanban.db` mutation): Exit `0` — `crew_stop_proof.py: 14 check(s), 0 failed`.
6. **Diff & Cleanliness Hygiene**:
   - `git --no-pager -C O:/workspaces/.worktrees/wt-crew-resilience diff --check origin/main` -> Exit `0`.
   - `git --no-pager -C O:/workspaces/.worktrees/wt-nerve-resilience diff --check origin/main` -> Exit `0`.
   - `git --no-pager -C O:/workspaces diff --check -- .agents/skills/crew-upstream-sync .agents/skills/nerve-upstream-sync` -> Exit `0`.
   - `git -C O:/workspaces/oss/crew status --porcelain -- scripts tests` -> Empty (untouched on `main`).
   - `git -C O:/workspaces/oss/hermes-nerve status --porcelain` -> Empty (untouched on `main`).
   - `[DEBUG-` scan across all modified files -> `0` matches; zero plaintext secrets leaked.

---

## Axis 1: Standards, Security & Hygiene

| Check | Status | Evidence |
| :--- | :--- | :--- |
| Coding Standards & 12 Fowler Smells | PASS | Deep single-purpose modules (`packet_bound.py`, `_stop_guard_reason()`, `uses_verifier_lane()` / `uses_review_handoff()`), shallow nesting, no feature envy or shotgun surgery across diffs. Minor non-blocking duplication note in `crew_stop.py:268-286` (repeated `subprocess.run` call for `reopen-review` + `block`/`schedule` retry). |
| Diff Hygiene & Debug Cleanliness | PASS | `git diff --check` exits `0` on both worktrees and root watchdogs; zero `[DEBUG-` tags; zero plaintext secrets. |
| §9 Zero-Checkout Invariant | PASS | Primary checkouts `O:/workspaces/oss/crew` (`scripts`/`tests`) and `O:/workspaces/oss/hermes-nerve` remain clean on `main`. |
| `NERVE-INV-6` Lifecycle Hygiene | PASS | `tests/test_completion_packet_and_cli_verdict.py` scopes `tempfile.TemporaryDirectory()` cleanly with `tearDown`/`addCleanup` and no dangling `NervousSystem` threads; `NERVE-INV-6` probe and `test_nervous.py` pass on Windows NTFS. |
| TDD Anti-Tautology | PASS | `test_crew_run_proof_resilience.py` exercises real child stdin-pipe workers, live descendant sleeper PIDs, `> 256 KiB` stream floods, and isolated `importlib` loading; `test_crew_stop_park.py` & `test_crew_verifier_block.py` exercise real `hermes_cli.kanban_db` transitions; `test_completion_packet_and_cli_verdict.py` exercises real `CardSupervisor` SQLite + `hooks.pre_tool_call` + `resolve_config`. |

### Axis 1 Non-Blocking Warnings & Info

- **[WARNING] W1-1 (`.agents/skills/crew-upstream-sync/scripts/daily-sync-watchdog.ps1`, `.agents/skills/nerve-upstream-sync/SKILL.md`) — CRLF-to-LF line-ending diff across untouched lines**:
  - `git diff` on the root repo shows `1048` / `276` changed lines due to CRLF -> LF conversion on untouched lines (`git diff -w` confirms only the intended `CREW-INV-9` and `NERVE-INV-8` edits changed functionally). Verify `core.autocrlf` / line endings before committing the root watchdog files.
- **[INFO] I1-1 (`tests/test_cli_panel_equivalence.py:109`) — Pre-existing venv `sys.modules` artifact unrelated to change**:
  - Running `test_cli_panel_equivalence.py` alone under `hermes-agent/.venv/Scripts/python.exe` passes `5/6` and fails pre-existing on `test_cli_show_reflects_panel_applied_state` (`Running: in-process host detected` because `hermes_cli` is importable from that venv, `cli.py:154`). Confirmed `cli.py` and `control_panel.py` were not modified and `ResolvedNerveConfig` preserves all callers (`test_sidecar_authority.py` and `test_deep_review_regressions.py` pass).

---

## Axis 2: Spec & Design Fidelity

| Spec / Design Area | Status | Verified Implementation Evidence |
| :--- | :--- | :--- |
| **P0-1 (`proof-safety`, Slice 1)** | PASS | `scripts/crew_safety.py`: `HERE` `sys.path` guard + `import crew_proc` (`L36-39`), `stdin=subprocess.DEVNULL` in `_exe_py_version()` (`L298`), `run_proof()` delegates all OS branches to `crew_proc.run_bounded()` (`L741-754`), preserving `Result(124, "proof command timed out after %ss" % timeout, "")` and `Result(127, ...)`. `tests/test_crew_proc.py:93-102` and `tests/test_crew_safety.py:514-525` aligned to `crew_safety.crew_proc.run_bounded`; 5 new resilience tests in `tests/test_crew_run_proof_resilience.py`. |
| **P0-2a (`nerve-completion-verdict-resilience`, Slice 2)** | PASS | `hermes_nerve/work/packet_bound.py`: `MAX_COMPLETION_PACKET_CHARS = 8000`, `MAX_COMPLETION_BATCHES = 4`, `safe_json_len()`, 3-pass ladder, criterion-linked evidence prioritization, `evidence_truncated` & `omitted_evidence_count` metadata, `partition_completion_batches()`, anti-false-PASS `COMPLETION_BATCH_INSTRUCTIONS`. `hermes_nerve/work/supervisor.py`: empty evidence -> `NEEDS_EVIDENCE` (0 calls), single/multi-batch execution, per-batch usage recording, fail-closed `ESCALATE` on batch cap overflow, `VERIFIED_PASS` persisted only when all batches `PASS`. |
| **P0-2b (`nerve-completion-verdict-resilience`, Slice 3)** | PASS | `hermes_nerve/work/deterministic.py`: `_parse_cli_verdict_command()` + `_parse_cli_verdict_result()` + `_extract_crew_verdict_call()` (`L311-379`) bind `crew_card.py verdict --card <id>` to `identity.task_id`, reject piped/spoofed/mismatched commands, parse `verdict: PASS`/`verdict: FAIL` + `rc=0|1|3` + JSON; `L400` updates guard to `tn not in {"crew_verdict", "crew_verdict_cli"}` so CLI `FAIL` is recorded; `L417` dispatches `crew_verdict_cli` in `observe_test_result()` ahead of the `pytest` check. |
| **P0-2c (`nerve-completion-verdict-resilience`, Slice 3)** | PASS | `hermes_nerve/config_resolver.py`: adds backward-compatible `advanced_override_sources` field (`L22`) recording `"work_supervision_mode": "profile.json:advanced"` (`L104-108`) without polluting `override_sources` (`module_override_sources`); `NERVE-INV-5` `pre_tool_call` DoD gating in `shadow` mode verified intact. |
| **P1-3 (`crew-heal-and-stop-resilience`, Slice 4)** | PASS | `scripts/crew_card.py`: separates `VERIFIER_VERIFY_MODES` / `uses_verifier_lane()` (`closer_profiles`, `verifier_block`) from `TWO_STAGE_VERIFY_MODES` / `uses_review_handoff()` (`repin_for_review`, `send_to_verifier`, `hand_to_writer`), keeping `hand_to_writer()` a no-op on standalone `Verify: agent`. `scripts/crew_heal.py`: `NON_HEALABLE_BLOCK_KINDS = frozenset({"needs_input", "capability"})` + `_card_block_kind()` DB fallback enforced in both `heal_card()` and `heal_stale_verify()`. `tests/test_crew_verifier_block.py` & `tests/test_crew_heal.py` updated and expanded. |
| **P1-4 (`crew-heal-and-stop-resilience` & `crew-extended-tools`, Slice 5)** | PASS | `scripts/crew_coordinator.py`: `_stop_guard_reason()` enforced both pre-`resolve()` and post-`resolve()` immediately before `apply_decision()`. `scripts/crew_stop.py`: `park_card()` transitions `review` cards via `reopen-review`, dispatches `block` (`ready`) or `schedule` (`todo`) with retry-once `0.2s` backoff, appends `crew_stop_parked` event (`prior_status`, `prior_reviewer`, `landed_status`, `park_verb`), and updates module docstring; `tests/kernel_board.py` adds `reopen-review`. |
| **Watchdogs & Scope (`Slice 6`)** | PASS | `CREW-INV-9` and `NERVE-INV-8` added cleanly; zero Stage 2 drift; Slice 7 (`7.1` publication/cutover, `7.2` live `profile.json` hygiene) properly left pending Commander approval. |

---

## Conclusion

Zero CRITICAL defects across both worktrees. All Stage 1C review conditions (`C2-1`, `C2-2`, `C2-3`, `W1-1`, `W1-2`, `W2-1`, `W2-2`, `W2-3`) and all Slices 1–6 requirements are verified green with independent L4 execution evidence. Ready for Coordinator Phase 4/5 and Commander-gated Slice 7 cutover.
