# Change Proposal: Crew & Nerve Completion, Proof-Execution, and Verdict Resilience

- **Change Slug**: `crew-nerve-completion-and-verdict-resilience`
- **Primary Repository / `OPENSPEC_ROOT`**: `O:/workspaces/oss/crew` (`O:/workspaces/oss/crew/openspec`)
- **Affected Repositories**: `O:/workspaces/oss/crew`, `O:/workspaces/oss/hermes-nerve`
- **Exploration**: [`explorations/2026-11-26-crew-nerve-completion-and-verdict-resilience-exploration.md`](explorations/2026-11-26-crew-nerve-completion-and-verdict-resilience-exploration.md)
- **Track**: Track A (OpenSpec Governance — Single Target Invariant)

## Why

Live Windows production execution on `AGENT-4070` (including card `t_88d70541` and verifier/coordinator lifecycle passes) revealed four deterministic reliability defects across `oss/crew` and `oss/hermes-nerve` that stall workers, leak orphan processes, crash completion verification, and bypass human/verifier/owner gates:

1. **P0-1 (`oss/crew` — `crew_safety.py::run_proof()`)**: On Windows, the standard Git Bash branch leaves `stdin=None` (inheriting `agent.managed_worker`'s open stdin pipe) and executes via `subprocess.run`, causing `bash.exe` proofs to deadlock until timeout (empirically reproduced: `stdin=None` hung `> 6.02s` / `TIMEOUT dt=5.476s` vs `stdin=subprocess.DEVNULL` `DONE rc=0 dt=0.031s`, matching production `940.551s`/`502.816s`/`495.618s` hangs) and leaking orphaned child process trees (`pytest`, `python`, `node`, `git`) on timeout because `proc.kill()` only kills root `bash.exe`.
2. **P0-2 (`oss/hermes-nerve` — `work/supervisor.py::verify_completion()`, `work/deterministic.py::observe_crew_verdict()`)**: Unbounded semantic verification packets (`24` evidence previews up to `4,000` chars + raw `12,000`-char proposal = `30,000-45,000+` chars / `~10,406` tokens) crash OpenJev/Jev with `HTTP 422` (`10,406 > 8,192` context limit), collapsing completion into `ESCALATE` loops. Simultaneously, `observe_crew_verdict()` ignores CLI `python scripts/crew_card.py verdict` calls via `terminal`, forcing unnecessary semantic calls; and live `reviewer/nerve/profile.json` carries a nested `advanced.work_supervision_mode: enforce` override plus a nested plaintext `advanced.reflex_openjev_token`.
3. **P1-3 (`oss/crew` — `crew_card.py::verifier_block()`, `crew_heal.py::heal_stale_verify()`)**: `verifier_block()` (and sibling review helpers) only recognize `Verify: independent`, omitting `Verify: agent` and `Verify: dual` (whereas `closer_profiles()` already treats all three as verifier-gated). In addition, `heal_stale_verify()` ignores `block_kind`, allowing a passing proof command to automatically unblock cards waiting on Commander input (`block_kind="needs_input"`) or missing capabilities (`block_kind="capability"`).
4. **P1-4 (`oss/crew` — `crew_coordinator.py::handle_card()`, `crew_stop.py::park_card()`)**: `handle_card()` never re-checks `parked_by_owner()` / `stopped_after()` / live `status` after its slow `resolve()` LLM call (`MODEL_TIMEOUT_S = 420s`), so `/crew-stop` during `resolve()` is silently undone when `apply_decision()` calls `apply_retry()` -> `lift_block()`. Separately, `crew_stop.py::park_card()` refuses `status == "review"` (`"cannot park a review card"`), killing the worker while leaving the card stranded in `review`.

## What Changes

### `oss/crew` (Worktree `O:/workspaces/.worktrees/wt-crew-resilience`)
- **P0-1 (`scripts/crew_safety.py`)**: Route `run_proof()` across all platforms (Windows Git Bash, Windows PowerShell, POSIX) through the existing deep module `crew_proc.run_bounded()` so every proof runs with `stdin=subprocess.DEVNULL`, `HeadTail` 64 KiB stream bounding, `CREW_RUN_MARKER`, and full process-tree termination (`%SystemRoot%\System32\taskkill.exe /PID <pid> /T /F` + marker sweep) on timeout (`rc=124`). Also pass `stdin=subprocess.DEVNULL` in `_exe_py_version()`.
- **P1-3 (`scripts/crew_card.py`, `scripts/crew_heal.py`)**: Introduce two distinct predicates: `VERIFIER_VERIFY_MODES = ("independent", "agent", "dual")` / `uses_verifier_lane(body)` (shared by `closer_profiles()` and `verifier_block()` for verifier-owned verdicts and blocks) and `TWO_STAGE_VERIFY_MODES = ("independent", "dual")` / `uses_review_handoff(body)` (shared by `hand_to_writer()`, `repin_for_review()`, and `send_to_verifier()` so standalone `Verify: agent` verifier cards are never hijacked onto `crew-worker`). Guard `crew_heal.heal_card()` / `heal_stale_verify()` with `NON_HEALABLE_BLOCK_KINDS = frozenset({"needs_input", "capability"})` backed by authoritative read-only `tasks.block_kind` DB lookup when omitted from the caller's dict. Update `tests/test_crew_verifier_block.py` stale-block fixtures from `needs_input` to `transient` and add regression tests for `agent`/`dual` verifier blocks and `needs_input`/`capability` protection.
- **P1-4 (`scripts/crew_coordinator.py`, `scripts/crew_stop.py`, `tests/kernel_board.py`)**: Extract `_stop_guard_reason(ctx, card_id, newest_event_id)` in `crew_coordinator.py` and enforce it both pre-`resolve()` and post-`resolve()` immediately before `apply_decision()` (re-reading live DB `status`, `parked_by_owner()`, and `stopped_after()`). Teach `crew_stop.py::park_card()` to park `status == "review"` cards via kernel-native `reopen-review` followed by `block` (when landed in `ready`) or `schedule` (when parent-gated in `todo`), recording a `crew_stop_parked` audit event capturing `prior_status: "review"` and `prior_reviewer`. Add `reopen-review` support to `tests/kernel_board.py::kernel_cli`.

### `oss/hermes-nerve` (Worktree `O:/workspaces/.worktrees/wt-nerve-resilience`)
- **P0-2a (`hermes_nerve/work/packet_bound.py`, `hermes_nerve/work/supervisor.py`)**: Introduce a deep module `bound_completion_packet()` implementing a deterministic 3-pass `<= 8,000`-char bounding ladder adapted from `NervousSystem._bound_assessment_state()`, with criterion-grouped sub-batching fallback (`max_completion_batches = 4`) when unmet criteria alone overflow Pass 1. Preserve semantic fidelity: explicit `evidence_truncated` / `evidence_omitted` metadata and prompt rules ensure truncated or missing evidence yields `RETRY` / `NEEDS_EVIDENCE`, never fabricated `PASS`.
- **P0-2b (`hermes_nerve/work/deterministic.py`)**: Extend `_extract_crew_verdict_call()` and `observe_crew_verdict()` to recognize zero-token (`provider_calls == 0`) CLI invocations of `crew_card.py verdict --card <task_id>` inside `terminal`/`shell`/`bash` tool calls, strictly bound to `identity.task_id` and exit code `0` + structured Crew verdict `PASS`/`FAIL` output.
- **P0-2c (`hermes_nerve/work/hooks.py`, `hermes_nerve/config_resolver.py`, Operational Hygiene)**: Preserve `pre_tool_call()` DoD gating in `shadow` mode (protecting `NERVE-INV-5` `test_crew_dod_and_handoff.py`), surface explicit sidecar override telemetry when `profile.json` overrides `work_supervision_mode`, and schedule a Commander-gated operational task to align `reviewer/nerve/profile.json` (`work_supervision_mode`) and migrate nested plaintext `advanced.reflex_openjev_token` to environment/Vaultwarden.

### Watchdog Invariants & Live Cutover
- Extend `crew-upstream-sync` (`CREW-INV-7` / new `CREW-INV-9`) and `nerve-upstream-sync` (`NERVE-INV-5` / new `NERVE-INV-8`) watchdogs with static anchors and regression suites for P0-1..P1-4.
- Execute Commander-gated live plugin cutovers via `apply-live-crew-cutover.ps1` (7 profiles + Desktop bundle) and `apply-live-nerve-cutover.ps1` (git-aligned plugin target) without mutating live primary checkouts off `main` (§9 Zero-Checkout Invariant).

## Capabilities

### Modified Capabilities
- `proof-safety`: Extend `O:/workspaces/oss/crew/openspec/specs/proof-safety/spec.md` with non-interactive `DEVNULL` stdin isolation, `run_bounded` 64 KiB stream bounding, and full process-tree termination on timeout (`P0-1`).
- `crew-extended-tools`: Extend `Stop Card Tool` in `O:/workspaces/oss/crew/openspec/specs/crew-extended-tools/spec.md` to cover non-destructive parking of `review`-lane Crew cards (`P1-4b`).

### New Capabilities
- `nerve-completion-verdict-resilience`: Bounded `<= 8,000`-char semantic completion packets with semantic fidelity guarantees, zero-token CLI `crew_card.py verdict` deterministic recognition, and `work_supervision_mode` precedence/hygiene (`P0-2`).
- `crew-heal-and-stop-resilience`: Unified verifier-lane block recognition across `independent`/`agent`/`dual`, `needs_input`/`capability` stale-heal protection, coordinator post-resolve stop re-check, and `review`-lane non-destructive parking (`P1-3`, `P1-4`).

## Out of Scope

- Modifying `O:/workspaces/oss/hermes-agent/hermes_cli/kanban_db.py` (all `review` parking uses existing kernel verbs `reopen-review`, `block`, and `schedule`).
- Disabling `hooks.pre_tool_call()` DoD completion gating in `shadow` mode (would regress `NERVE-INV-5` `test_crew_dod_and_handoff.py`).
- Refactoring `crew_graph_serve.py` dashboard rendering or `REQ-CREW-VERDICT-1`/`REQ-CREW-DASHBOARD-1` non-Crew card refusal rules (verified intact and unaffected).
- Automatic Gateway/Dashboard restarts (remain Commander-only manual actions per cutover scripts).

## Impact & Risk

- **KB Blast-Radius Docs (Phase 5 Post-Archive Refresh Checklist)**:
  - `archify:archify-10e2146b1002d340` ("How did we unify OpenSpec, Nerve, Crew, and Kanban DoD gates?")
  - `archify:archify-efa5f5e971561f18` ("How did we stop System One timeouts and zombie failovers?")
  - 2-hop neighbors: `workspaces-docs:hermes-skills-workflows-plugins`, `workspaces-docs:antigravity-hermes-architecture`, `workspaces-docs:hermes-control-architecture`
- **Watchdog Invariants Protected**: `CREW-INV-1..8` (especially `CREW-INV-3` in `crew_safety.py`, `CREW-INV-7` in `crew_proc.py`) and `NERVE-INV-1..7` (especially `NERVE-INV-5` `test_crew_dod_and_handoff.py`, `NERVE-INV-6` nonblocking lifecycle).
- **Risk Summary**:
  1. `crew_safety.py` is a known upstream merge hotspot (`CREW-INV-3`); keeping `run_proof()` delegation to `crew_proc.run_bounded()` minimal isolates merge surface.
  2. Over-aggressive packet truncation in `verify_completion()` could hide criterion evidence and cause false `RETRY` loops; mitigated via priority-ordered criterion-linked evidence retention and explicit `evidence_truncated` metadata.
  3. Changing `crew_heal` to block `needs_input`/`capability` breaks two legacy test fixtures in `test_crew_verifier_block.py` that used `kind="needs_input"` for generic writer blocks; mitigated by updating those fixtures to `kind="transient"` and adding explicit `needs_input`/`capability` negative tests.

## Rollback

- **Code Rollback**: Both `oss/crew` and `oss/hermes-nerve` changes land via isolated worktrees (`O:/workspaces/.worktrees/wt-crew-resilience`, `O:/workspaces/.worktrees/wt-nerve-resilience`) as discrete commits on `origin/main`; rollback is a single `git revert <sha>` per repo in a fresh worktree followed by `apply-live-crew-cutover.ps1` / `apply-live-nerve-cutover.ps1` (which also retain timestamped `<profile>\backups\{crew,nerve}-cutover-<stamp>\` snapshots).
- **Config Hygiene Rollback**: `reviewer/nerve/profile.json` is backed up before applying env/Vaultwarden secret migration and mode alignment.
