# Independent Review: Profile-Warning Reproduction

**Review card:** `t_aa25c4b7`  
**Input card:** `t_ae6bdd43`  
**Reviewer:** Agent Reviewer  
**Date:** 2026-10-19  
**Inspected Crew commit:** `53071a9`  
**Inspected Hermes-Agent commit:** `eba886378af`  
**Verdict:** **APPROVED WITH WARNING**

## Summary

| Severity | Count |
|---|---:|
| CRITICAL | 0 |
| WARNING | 1 |
| INFO | 1 |

The reproduction result is approved as a bounded runtime observation. Three concurrent Hermes subagents completed with return codes `[0, 0, 0]`. The retained telemetry contains four distinct active-ledger snapshots, reaches peak concurrency of three CLI processes, contains only install ID `59b350e06553`, and contains zero non-empty `warning` values. This is sufficient to establish that no profile conflict was captured during the observed run; it does not prove that no warning can ever recur.

The parent report overstates the monitor semantics when it says `shared_profile_warning()` returned an empty string on all 1,256 polls. The implementation evaluates the warning only when raw ledger text changes, and the retained JSON contains four such snapshots. This wording defect does not invalidate the four captured states or the three successful subagent runs, but downstream users must interpret the result as bounded evidence.

## Scope

### Files reviewed

- `reports/reproduction-profile-warning-verification.md`
- `reports/reproduction-profile-warning-verification.json`
- `scripts/reproduce_subagent_ledger_verification.py`
- `O:/workspaces/oss/hermes-agent/hermes_cli/shared_profile_warning.py`
- `O:/workspaces/oss/hermes-agent/hermes_cli/process_identity.py`
- `openspec/changes/archive/worktree-isolation-governance/specs/worktree-isolation-governance/spec.md`
- `openspec/changes/archive/worktree-isolation-governance/design.md`
- `O:/workspaces/ai_agents/collaboration/openspec/specs/code-review-mandate/spec.md`
- `O:/workspaces/ai_agents/collaboration/docs/lessons/lessons-learned.md`
- `O:/workspaces/openspec/workspace/sessions/agent_share.md`

### SDLC layers reviewed

- Card contract and acceptance criterion
- Runtime telemetry and reproduction harness
- Profile-warning predicate and ledger filtering
- Zero-Checkout governance

## Evaluation by SDLC Layer

### Specifications

The card requires an independent verdict on whether the reproduction captured profile conflicts during active subagent execution. The retained telemetry directly represents active CLI ledger states and records the expected install identity, warning value, subagent return codes, and concurrency. The acceptance criterion is satisfied on a bounded-run basis.

### Architecture

The production predicate at `hermes_cli/shared_profile_warning.py:10-24` emits the warning only when a verified live ledger entry has the same Hermes home and an install identity different from the current installation. The ledger reader at `hermes_cli/process_identity.py:375-399` filters verified entries by exact live PID/create-time identity. The reproduction's captured active entries all use the same Hermes home and install ID `59b350e06553`; therefore the predicate is false for every retained snapshot.

The worktree boundary gate passed. Raw output:

```text
REPO=O:/workspaces
main
O:/workspaces a592373b [main]
REPO=O:/workspaces/oss/crew
main
O:/workspaces/.git/modules/oss/crew               53071a9 [main]
O:/workspaces/.worktrees/crew-extended-tools      682418b [feat/crew-extended-tools]
O:/workspaces/.worktrees/crew-upstream-pr         39c8a37 [feat/native-tools]
O:/workspaces/.worktrees/wt-crew-desktop-pane     52d1e41 [feat/desktop-flow-graph-pane]
O:/workspaces/.worktrees/wt-crew-pane-toggle      236e9de [fix/desktop-pane-toggle]
O:/workspaces/.worktrees/wt-crew-powershell-proof 0542d11 [feat/powershell-proof-compat]
O:/workspaces/.worktrees/wt-crew-pr-child-guard   9231584 [fix/guard-child-cards]
O:/workspaces/.worktrees/wt-crew-pr-flow-pane     e71b6e2 [feat/desktop-flow-pane]
O:/workspaces/.worktrees/wt-crew-pr-traceability  43b78e8 [feat/card-session-traceability]
O:/workspaces/.worktrees/wt-crew-sync-daily       46482a1 [sync/upstream-main-daily]
O:/workspaces/.worktrees/wt-crew-tool-card-alias  52e3b74 [fix/tool-card-alias]
REPO=O:/workspaces/oss/hermes-agent
main
O:/workspaces/.git/modules/oss/hermes-agent         eba886378af [main]
O:/workspaces/.worktrees/hermes-terminal-notify-pr  a553dc7c73d [fix/terminal-notify-on-complete-schema]
O:/workspaces/.worktrees/wt-fix-process-tree        f6e2d979536 [fix/windows-process-tree-and-sweep-storm]
O:/workspaces/.worktrees/wt-hermes-sync-daily       dddee3a4678 [sync/upstream-daily]
O:/workspaces/.worktrees/wt-hermes-watchdog-test-pr 5d51284ce82 [test/watchdog-dump-mkdir-fallback]
O:/workspaces/.worktrees/wt-intel-nuc-sentinel      b2667665176 [feat/intel-nuc-sentinel]
REPO=O:/workspaces/oss/hermes-nerve
main
O:/workspaces/oss/hermes-nerve                         1bc559f [main]
O:/workspaces/.worktrees/wt-nerve-url-case-insensitive 6e76f63 [fix/progress-integrity-url-case]
```

All four protected production checkouts remain on `main`; every listed non-primary branch is isolated under `O:/workspaces/.worktrees/`.

### Code

The monitor polls every 50 ms, reads the ledger, and records a snapshot only when raw ledger text changes (`scripts/reproduce_subagent_ledger_verification.py:50-99`). It checks every recorded install ID against `59b350e06553` and invokes `shared_profile_warning()` for each changed state. Three selected test cases are dispatched concurrently through the pinned evaluation harness (`:122-146`).

The monitor catches all exceptions without recording them (`:97-98`). This limits the evidentiary strength because read/parse failures are not observable in the saved JSON. No malformed or missing snapshot is evident in the retained four-state progression, so this is an auditability warning rather than a demonstrated runtime failure.

### Tests and Runtime Evidence

The card's one independent extra check read the machine-readable input and recomputed the decisive metrics without trusting the prose report. Raw output:

```text
EXTRA_CHECK snapshots=4 peak=3 cli_install_ids=['59b350e06553'] warning_snapshots=0 subagent_rcs=[0, 0, 0] total_monitor_polls=1256
```

This confirms:

1. Four retained active-ledger states were captured.
2. Peak concurrent CLI subagents was three.
3. Every captured CLI entry used install ID `59b350e06553`.
4. No retained state contained a warning.
5. All three subagent processes exited successfully.

### DevOps / Process Isolation

The reproduction used the repository Hermes executable recorded in each active entry's `argv`. All captured CLI entries target the same Hermes home and installation. Production checkouts remained on `main`, satisfying the independent Zero-Checkout branch gate.

## Findings

### WARNING W-01 — Report claims 1,256 warning evaluations, but only four are retained/evaluated

- **Spec reference:** Card goal; code-review mandate evidence/no-hiding requirements.
- **File/line:** `reports/reproduction-profile-warning-verification.md:28,32`; `scripts/reproduce_subagent_ledger_verification.py:50-99`; telemetry JSON lines 7-10 and 46-147.
- **Evidence:** `total_monitor_polls=1256`, but warning evaluation occurs inside the `raw_text != self._last_raw` branch; the JSON records `total_state_snapshots=4` and four warning values.
- **Impact:** The phrase “returned on all 1,256 polls” is unsupported. The correct conclusion is zero warnings in four captured unique ledger states across a 1,256-poll observation window.
- **Resolution:** Treat this review's bounded wording as authoritative. In future reports, distinguish poll count from evaluated state-transition count.

### INFO I-01 — Monitor exceptions are not persisted

- **Spec reference:** Code-review mandate observability requirement.
- **File/line:** `scripts/reproduce_subagent_ledger_verification.py:97-98`.
- **Evidence:** The `except Exception` branch executes only `pass`; the telemetry has no monitor-error counter.
- **Impact:** A transient ledger read or JSON parse failure would be invisible in the saved evidence. No such failure was demonstrated in this run.
- **Resolution:** Future reproduction tooling should persist `monitor_error_count` and representative error text. No rework is required for this bounded review card.

## Not Reviewed

- The model content produced by the three subagents was not evaluated; only execution identity, warning state, concurrency, and return codes are in scope.
- The full reproduction was not rerun because the card requires review of the supplied run, and the verifier contract permits exactly one independent extra check beyond the owner-confirmed proof.
- Historical ledger states before the captured run and future states after it are not represented.
- No claim is made that profile conflicts can never recur.

## Final Verdict

**APPROVED WITH WARNING.** The retained reproduction evidence supports a bounded conclusion: during four captured active-ledger states across the concurrent three-subagent run, all entries used install ID `59b350e06553`, no profile warning was recorded, and all subagents exited `0`. The parent report's “all 1,256 polls” phrasing is overstated and is narrowed by this independent review; it does not invalidate the captured zero-warning result.