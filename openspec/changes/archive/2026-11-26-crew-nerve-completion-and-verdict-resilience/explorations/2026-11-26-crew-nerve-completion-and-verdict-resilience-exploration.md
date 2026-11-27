# Exploration: Crew & Nerve Completion, Proof-Execution, and Verdict Resilience (`crew-nerve-completion-and-verdict-resilience`)

- **Date**: 2026-11-26
- **Primary Project / `OPENSPEC_ROOT`**: `O:/workspaces/oss/crew` (`O:/workspaces/oss/crew/openspec`)
- **Change Slug**: `crew-nerve-completion-and-verdict-resilience`
- **Track**: Track A (OpenSpec Governance — Single Target Invariant; zero cross-root mirrors)
- **Secondary Spec Roots (Read-Only Cross-Checked)**:
  - `O:/workspaces/openspec/specs/nerve-lifecycle-and-watchdog-invariants/spec.md` (`NERVE-INV-6`/`NERVE-INV-7`)
  - `O:/workspaces/oss/hermes-agent/openspec/specs/crew-verdict-boundary-hardening/spec.md` (`REQ-CREW-VERDICT-1`, `REQ-CREW-DASHBOARD-1`)
  - `O:/workspaces/oss/crew/openspec/specs/proof-safety/spec.md`, `native-crew-tools/spec.md`, `crew-extended-tools/spec.md`, `worktree-isolation-governance/spec.md`
- **Pinned Repository Commits**: `oss/crew@e6123f78b2`, `oss/hermes-nerve@7b4a9b2113`
- **KB Blast-Radius Citations**: `archify:archify-10e2146b1002d340`, `archify:archify-efa5f5e971561f18` (2-hop: `workspaces-docs:hermes-skills-workflows-plugins`, `workspaces-docs:antigravity-hermes-architecture`, `workspaces-docs:hermes-control-architecture`)

---

## 1. Evidence-Backed Problem Statement (P0-1 through P1-4)

Production Kanban/Crew execution on Windows (`AGENT-4070`, card `t_88d70541` and sibling verifier/coordinator flows) exposed four coupled resilience failures spanning `oss/crew` and `oss/hermes-nerve`. Each defect was empirically verified against live HEAD source code (`#3` recon + Coordinator empirical repro + direct source/test audit).

### Failure Topology (End-to-End ASCII Map)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                 CREW + NERVE RESILIENCE FAILURE SURFACE                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  [P0-1] crew_safety.py::run_proof() (L689-758)                             │
│    Windows Git Bash branch leaves stdin=None (inherits managed_worker      │
│    open pipe) -> DEADLOCK (>500s-940s hangs) + subprocess.run timeout      │
│    only kills root bash.exe -> ORPHANED CHILD TREE (pytest/python/node)    │
│                                                                            │
│  [P0-2] hermes_nerve/work/supervisor.py::verify_completion() (L463-490)    │
│    Unbounded packet (24 evidence previews up to 4k chars + 12k proposal)   │
│    -> 30k-45k chars (~10,406 tokens) -> OpenJev HTTP 422 (> 8,192 ctx)     │
│    + deterministic.py::observe_crew_verdict() misses CLI crew_card verdict │
│    + reviewer profile.json overrides mode=enforce & holds nested token     │
│                                                                            │
│  [P1-3] crew_card.py::verifier_block() (L2554) + crew_heal.py (L183-262)   │
│    verifier_block() only checks verify_mode == "independent" (drops        │
│    "agent" and "dual") + heal_stale_verify() ignores block_kind            │
│    ("needs_input", "capability") -> passing proof AUTO-UNBLOCKS gates      │
│                                                                            │
│  [P1-4] crew_coordinator.py::handle_card() (L963-1005)                     │
│         + crew_stop.py::park_card() (L293-312)                             │
│    1) /crew-stop parks card during slow resolve() LLM call ->              │
│       apply_decision() never re-checks parked_by_owner()/stopped_after()   │
│       -> apply_retry() silently RESURRECTS stopped card                    │
│    2) park_card() returns "cannot park a review card" -> worker killed,    │
│       card stranded in status='review'                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Receipts by Defect

#### P0-1: Windows Git Bash Stdin Deadlock & Process-Tree Leak in `run_proof()`
- **Exact Seam**: `O:/workspaces/oss/crew/scripts/crew_safety.py:689-758`.
- **Root Cause**:
  1. Line 739 initializes `stdin = None`. Line 742 sets `stdin = subprocess.DEVNULL` **only** inside `if IS_WINDOWS and detect_bare_powershell(cmd):`. The standard Windows Git Bash branch (`elif IS_WINDOWS:`, lines 743-750) leaves `stdin = None`, and line 752 passes `stdin=stdin` to `subprocess.run(...)`.
  2. When called from `agent.managed_worker` (`gateway/session_managed_worker.py:609-610`), the parent holds `stdin=PIPE` with a reader thread blocked in `sys.stdin.readline()`. Inheriting `stdin=None` causes Git Bash / child processes to block indefinitely on standard input until timeout or parent pipe closure.
  3. On `subprocess.TimeoutExpired` (lines 755-756), `subprocess.run` invokes `proc.kill()` (`TerminateProcess` on Windows), killing **only** the root `bash.exe` and stranding descendant `pytest`/`python`/`node`/`git` processes holding file locks and ports.
- **Empirical Repro Receipt (Coordinator Verified)**:
  - Harness matching `agent.managed_worker` (`stdin=PIPE` + reader thread blocked in `sys.stdin.readline()`) invoking `[git_bash, "-c", "test -s '...'"]` with `timeout=3`:
    - `stdin=None` (current code): **HUNG > 6.02s** until parent closed stdin pipe (`TIMEOUT dt=5.476s`, reproducing production `940.551s`, `502.816s`, and `495.618s` hangs observed on card `t_88d70541`).
    - `stdin=subprocess.DEVNULL` (fix): **`DONE rc=0 dt=0.031s`** (100% deterministic reproduction).
- **Existing Reusable Module**: `O:/workspaces/oss/crew/scripts/crew_proc.py::run_bounded()` (lines 271-319, protected by `CREW-INV-7`) already implements `stdin=subprocess.DEVNULL`, `HeadTail` 64 KiB stream bounding, `CREW_RUN_MARKER` environment tagging, `CREATE_NEW_PROCESS_GROUP` / `start_new_session`, and `terminate_tree(proc.pid, 0.5, run_marker=marker)` via absolute `%SystemRoot%\System32\taskkill.exe /PID <pid> /T /F`.

#### P0-2: Unbounded Semantic Verification Packet Overflow (`HTTP 422`), CLI Verdict Blindspot, and Mode/Config Precedence
- **Exact Seams**:
  - `O:/workspaces/oss/hermes-nerve/hermes_nerve/work/supervisor.py:412-535` (`CardSupervisor.verify_completion`)
  - `O:/workspaces/oss/hermes-nerve/hermes_nerve/nervous.py:2675-2790` (`NervousSystem._bound_assessment_state`, 8,000-char 3-pass reference ladder)
  - `O:/workspaces/oss/hermes-nerve/hermes_nerve/work/deterministic.py:49-175, 1042-1060` (`_extract_crew_verdict_call`, `observe_crew_verdict`, `observe_test_result`, `_evaluate_criterion`)
  - `O:/workspaces/oss/hermes-nerve/hermes_nerve/work/hooks.py:567-846` (`pre_tool_call`)
  - `O:/workspaces/oss/hermes-nerve/hermes_nerve/config_resolver.py:88-92` (`profile.json` `advanced` precedence)
- **Root Causes**:
  1. **Unbounded Packet**: `verify_completion()` (lines 463-477) serializes all unmet `remaining_criteria`, the last `24` raw evidence entries (`preview` up to `self.preview_chars` = 1,200..4,000 chars each), and uncurated `redact(proposal or {})` (up to 12,000+ chars). Total serialized JSON reaches 30,000-45,000+ chars (~10,406 tokens), triggering deterministic OpenJev/Jev `HTTP 422` (`10,406 > 8,192` context limit) and collapsing `verify_completion()` into `CompletionVerdict(allow=False, value="ESCALATE")`, trapping workers in completion loops.
  2. **CLI Crew Verdict Blindspot**: `observe_crew_verdict()` (lines 49-165) only intercepts native tool calls (`crew_verdict`, `crew_review_handoff`, `crew_review`, or `tool_call` wrappers thereof). When a worker invokes `python scripts/crew_card.py verdict --card <id>` via `terminal`/`shell`/`bash`, `_extract_crew_verdict_call()` returns `None` and `observe_test_result()` (line 177) skips commands without `pytest`/`unittest`. Consequently, a passing Crew verdict executed via CLI fails to mark the locked Crew verdict criterion deterministically (`provider_calls == 0`) and forces an unnecessary semantic verification call.
  3. **Mode Precedence & Live Profile Hygiene (Coordinator Zero-Trust Verification)**:
     - Live `O:/workspaces/_config/agent4070/hermes/profiles/reviewer/nerve/profile.json` contains nested keys under `advanced`: `"work_supervision_mode": "enforce"` (silently overriding `config.yaml`'s `shadow`) AND a nested plaintext `advanced.reflex_openjev_token` (secret hygiene violation — must be migrated to env/Vaultwarden under Commander-gated operational task; zero secret values are logged or copied here).
     - **Critical Test-Verified Finding on `shadow` Mode**: Inspection of `oss/hermes-nerve/tests/test_crew_dod_and_handoff.py:49-54, 103-112, 289-318` confirms that `NERVE-INV-5` runs `runtime.configure(enabled=True, store_path=..., provider_decisions_enabled=False)` with **default `mode="shadow"`** and explicitly asserts that `hooks.pre_tool_call()` **blocks** premature `kanban_complete` and premature `crew_review_handoff`. Therefore, `work_supervision_mode` (`shadow` | `advisory` | `enforce`) scopes **mid-run trajectory controls** (`_should_request_control()`), whereas DoD completion gating in `pre_tool_call()` is intentionally governed by `work_supervision_enabled` (`enabled()`). Disabling `pre_tool_call` completion gating in `shadow` mode would directly regress `NERVE-INV-5`.

#### P1-3: Verifier & Human/Capability Block Bypass in `crew_heal`
- **Exact Seams**:
  - `O:/workspaces/oss/crew/scripts/crew_card.py:607, 1415, 2024, 2063-2065, 2543-2599`
  - `O:/workspaces/oss/crew/scripts/crew_heal.py:183-218, 238-262`
- **Root Causes**:
  1. `closer_profiles()` (`crew_card.py:2064`) already treats `("independent", "agent", "dual")` as verifier-gated modes, yet `verifier_block()` (line 2554) checks `verify_mode(...) != "independent"` only. On `Verify: agent` (standalone verifier card, `crew_card.py:974-988`) or `Verify: dual` (two-stage review-handoff card) blocked by a verifier/reviewer, `verifier_block()` returns `None`, allowing `heal_stale_verify()` to run the proof script and auto-unblock the card over the verifier's quality judgement. Meanwhile, two-stage review-handoff helpers (`hand_to_writer()` at line 2583, `repin_for_review()` at line 1415, and `send_to_verifier()` at line 2024) also omit `Verify: dual`, while MUST NOT include `Verify: agent` (a standalone `Role: verifier` card that never hands off to a separate writer).
  2. Neither `heal_card()` (lines 238-262) nor `heal_stale_verify()` (lines 183-218) inspects `block_kind`. Against `kanban_db.VALID_BLOCK_KINDS = {"dependency", "needs_input", "capability", "transient"}` (plus `None` for untyped failure-breaker blocks), a card explicitly blocked with `block_kind="needs_input"` (waiting for Commander decision) or `block_kind="capability"` (missing tool/permission/credentials) is silently unblocked whenever its proof command exits `0`.
  3. **Existing Test Compatibility Finding**: `O:/workspaces/oss/crew/tests/test_crew_verifier_block.py:69, 89-99` creates non-verifier stale-block fixtures using `kb.block_task(..., kind="needs_input")` while passing `card = {"id": cid, "status": "blocked", "body": BODY}` (omitting `block_kind`). Because `heal_stale_verify()` must read `block_kind` from the card dict with authoritative fallback to `tasks.block_kind` in `KANBAN_DB` (preventing minimal-dict bypasses), those two stale-block fixture tests must be updated to `kind="transient"` (matching real transient failure blocks), alongside new explicit tests proving `needs_input` and `capability` blocks never auto-heal.

#### P1-4: Coordinator Post-Resolve `/crew-stop` Race & `review`-Lane Parking Failure
- **Exact Seams**:
  - `O:/workspaces/oss/crew/scripts/crew_coordinator.py:941-1015` (`handle_card`)
  - `O:/workspaces/oss/crew/scripts/crew_stop.py:293-312, 314-361` (`park_card`, `stop_card`)
  - `O:/workspaces/oss/hermes-agent/hermes_cli/kanban_db.py:3139-3227, 3620-3655, 3886-3906` (`block_task`, `reopen_review_task`, `schedule_task`)
- **Root Causes**:
  1. **Race Window**: `handle_card()` checks `parked_by_owner()` and `stopped_after()` at lines 963-969, then invokes `resolve()` at line 994 (an LLM call bounded by `MODEL_TIMEOUT_S = 420s`). If the owner runs `/crew-stop <card>` while `resolve()` is in flight, `stop_card()` parks the card in SQLite (`blocked`/`scheduled` with `OWNER_STOP_MARK`). When `resolve()` returns, line 1004 executes `apply_decision()` unconditionally with the stale `card` dict — `apply_retry()` calls `crew_card.retry_card(..., unblock=True)` -> `lift_block()`, silently resurrecting the owner-stopped card.
  2. **Review-Lane Parking Gap**: `kanban_db.block_task()` restricts `WHERE status IN ('running', 'ready')` (line 3213) and `schedule_task()` restricts `WHERE status IN ('todo', 'ready', 'running', 'blocked')` (line 3901); both refuse `status == 'review'`. `crew_stop.py::park_card()` falls into `else: return "cannot park a %s card" % status, ""` (line 306), leaving `review` cards unparked and reporting `NOT DOWN` (exit 1) after killing the worker.
  3. **Kernel Transition Nuance Verified from `kanban_db.py:3620-3655`**: `reopen_review_task(conn, task_id)` transitions `review -> ready` **or `todo`** (via `_landing_status_after_parents`) and restores `assignee = implementer` from the latest `review_requested` event while preserving `consecutive_failures`. Therefore, parking a `review` card MUST inspect the post-`reopen-review` status and dispatch `block` (if `ready`) OR `schedule` (if parent-gated `todo`), while recording prior review-lane metadata (previous status `review` + reviewer assignee) before mutating.

---

## 2. Matt Pocock `codebase-design` Analysis (Deep Modules, Seams, Deletion Test)

Using strict `codebase-design` vocabulary (**Module**, **Interface**, **Implementation**, **Depth**, **Seam**, **Adapter**, **Leverage**, **Locality**):

| Problem | Candidate Option A (Recommended Deep Module) | Candidate Option B (Alternative / Shallow Wrapper) | Deletion Test & Seam Verdict |
| :--- | :--- | :--- | :--- |
| **P0-1 (`run_proof`)** | **Reuse `crew_proc.run_bounded()`** inside `crew_safety.run_proof()` for all OS branches (Windows Git Bash, Windows PowerShell, POSIX). | Patch only `stdin=subprocess.DEVNULL` + hand-roll `Popen` + `terminate_tree` inside `crew_safety.py`. | **Option A wins decisively.** `crew_proc.run_bounded()` is already a proven deep module (`CREW-INV-7`) hiding `DEVNULL` stdin, 64 KiB `HeadTail` stream caps, `CREATE_NEW_PROCESS_GROUP`/`start_new_session`, `CREW_RUN_MARKER`, and absolute `System32\taskkill.exe /T /F` behind one interface. Duplicating `Popen` + `terminate_tree` in `crew_safety.py` destroys locality and splits bug fixes across two runners. One tiny detail: preserve `run_proof()`'s exact `Result(rc, out, blocked)` interface and timeout message (`"proof command timed out after %ss" % timeout` when `br.timed_out`, optionally appending bounded tail or keeping exact contract so existing callers/tests pass unchanged) while also fixing `_exe_py_version()` (`crew_safety.py:291`) to pass `stdin=subprocess.DEVNULL`. |
| **P0-2a (`verify_completion` packet cap)** | **Shared deep module `hermes_nerve/work/packet_bound.py` (or `CardSupervisor._bound_completion_packet`)** implementing a deterministic **3-pass 8,000-char ladder** adapted from `NervousSystem._bound_assessment_state()` **plus** criterion-grouped batching fallback only when `remaining_criteria` alone exceed Pass 1 budget. | (B1) Truncate only `evidence[-24:]` to `evidence[-6:]` ad hoc in `verify_completion()`.<br>(B2) Always split every criterion into individual provider calls (1 call per criterion). | **Hybrid Option A wins.** Deleting `_bound_completion_packet()` causes token-cap math, UTF-8/ASCII JSON sizing, and fidelity guarantees to spill across `verify_completion()` and every future semantic verifier call site. **Why not B1?** Raw slice reduction still overflows if `proposal` (12k chars) or a large `remaining_criteria` list dominates; a hard `<= 8000` char post-serialization invariant (Pass 1 compact previews -> Pass 2 priority criterion-linked evidence + compact proposal -> Pass 3 minimal envelope with explicit `evidence_truncated: true` metadata) mathematically eliminates `HTTP 422`. **Why not unconditional B2?** Unconditional 1-call-per-criterion multiplies supervisor token spend and latency (violating `NERVE-INV-5` budget discipline). **Semantic Fidelity Invariant**: When truncation drops evidence or evidence is empty, the packet carries explicit `truncated_evidence_count` / `evidence_omitted: true` signals and the prompt instructs the verifier to return `RETRY`/`NEEDS_EVIDENCE` (never fabricate `PASS` from truncated/missing evidence). |
| **P0-2b (CLI `crew_card.py verdict` observer)** | **Deepen `deterministic.py::_extract_crew_verdict_call()` + `observe_crew_verdict()`** to recognize both native `crew_verdict` tool calls AND `terminal`/`shell`/`bash` invocations of `crew_card.py verdict --card <task_id>` with card-ID binding. | Add a separate regex hook inside `hooks.py::post_tool_call()`. | **Deepening `deterministic.py` wins.** `observe_crew_verdict()` is already the single seam for zero-token Crew verdict observation (`provider_calls == 0`). Keeping CLI verdict extraction behind `_extract_crew_verdict_call()` gives `post_tool_call()` and `observe_test_result()` immediate leverage with zero new hook branching. **Security Guard**: CLI verdict extraction MUST verify `--card <id>` matches `identity.task_id` (preventing a worker from passing another card's verdict) AND require exit code `0` + structured Crew verdict `PASS` line (never trusting bare `echo PASS`). |
| **P0-2c (`shadow` vs `enforce` in `hooks.py`)** | **Preserve `pre_tool_call()` DoD gating in `shadow` mode** (protecting `NERVE-INV-5` `test_crew_dod_and_handoff.py`), while ensuring bounded packets prevent `HTTP 422` crashes AND adding an explicit config-override diagnostic when `profile.json` overrides `config.yaml`'s `work_supervision_mode` (plus Commander-gated cleanup of `reviewer/nerve/profile.json`). | Skip `pre_tool_call()` blocking whenever `sup.mode == "shadow"`. | **Preserving DoD gating wins.** Empirical check of `test_crew_dod_and_handoff.py:49-53` proved `NERVE-INV-5` runs `runtime.configure(enabled=True)` (default `mode="shadow"`) and asserts `pre_tool_call()` blocks premature `kanban_complete`/`crew_review_handoff`. Bypassing `pre_tool_call` in `shadow` breaks an active watchdog invariant and creates silent unverified completions. |
| **P1-3 (`verifier_block` + `block_kind` guard)** | **Two explicit predicates in `crew_card.py`** — `VERIFIER_VERIFY_MODES = ("independent", "agent", "dual")` (`uses_verifier_lane(body)` for `closer_profiles` & `verifier_block`) separated from `TWO_STAGE_VERIFY_MODES = ("independent", "dual")` (`uses_review_handoff(body)` for `hand_to_writer`, `repin_for_review`, `send_to_verifier`) — plus **authoritative `NON_HEALABLE_BLOCK_KINDS = frozenset({"needs_input", "capability"})`** guard in `crew_heal._card_block_kind(card)` (reading `card.get("block_kind")` with read-only DB fallback). | Single predicate conflating `agent` into `hand_to_writer()`, or patching `card.get("block_kind")` without DB fallback. | **Two separated predicates + DB-backed guard wins.** `Verify: agent` is a standalone `Role: verifier` card (`crew_card.py:974-988`) that is never handed off to a writer — passing it to `hand_to_writer()` (`crew_card.py:2586-2596`) resolves `Role: verifier` -> `"worker"` and hijacks the card onto `crew-worker`. Splitting `uses_verifier_lane()` from `uses_review_handoff()` protects `agent` and `dual` verifier blocks while ensuring `hand_to_writer()` stays a no-op for `Verify: agent` and properly handles `Verify: dual`. Reading `tasks.block_kind` from `KANBAN_DB` when `card` dict omits it prevents shallow callers from bypassing the human/capability gate. |
| **P1-4a (Post-resolve `/crew-stop` race)** | **Extract `_stop_guard_reason(ctx, card_id, newest_event_id)`** in `crew_coordinator.py` and invoke it **both** pre-`resolve()` (fast skip) and post-`resolve()` immediately before `apply_decision()` (re-reading live DB state for `status in ("archived", "done")`, `parked_by_owner()`, and `stopped_after()`). | Inline duplicate `if parked_by_owner(...)` check before `apply_decision()` without re-reading `card["status"]`. | **Unified `_stop_guard_reason()` seam wins.** Re-checking only `parked_by_owner()` would still miss `/crew-stop --archive` (which moves the card to `archived` without writing a `blocked`/`scheduled` owner-stop event!). Re-reading live `get_card(ctx, card_id)` inside `_stop_guard_reason()` closes **both** park and `--archive` race windows in one place and skips mutating `apply_decision()` + skips recording a phantom `retry` decision. |
| **P1-4b (`review`-lane parking in `crew_stop.py`)** | **Two-step kernel-native parking in `park_card()`**: capture prior `review` lane + reviewer assignee -> run `hermes kanban reopen-review <card_id>` -> inspect live post-reopen status (`ready` -> `block --kind <park_kind> <reason>`, `todo` -> `schedule <reason>`) -> record non-destructive audit note (`prior_status=review`, `prior_reviewer=<assignee>`) via `crew_card._append_card_event(..., "crew_stop_parked", ...)` (or comment). | Add a new `review -> blocked` SQL exception in `oss/hermes-agent/hermes_cli/kanban_db.py::block_task()`. | **Two-step kernel-native parking wins.** Mutating `hermes-agent/kanban_db.py` crosses into a third protected repository (`oss/hermes-agent`) and risks breaking Kanban state-machine invariants (`_retry_status_for_run`, `block_recurrences`, dashboard review-lane contracts). Using the kernel's own `reopen-review` + `block`/`schedule` verbs stays 100% inside `oss/crew`, handles parent-gated `todo` landings safely, and preserves reviewer provenance in the card's event trail. |

---

## 3. Explicit Operator Tradeoffs

1. **P0-1 (`run_proof` output size & timeout behavior)**:
   - *Tradeoff*: Routing `run_proof()` through `crew_proc.run_bounded()` caps captured `stdout` and `stderr` at 64 KiB each (`HeadTail` head+tail preservation) instead of unbounded RAM buffering.
   - *Assessment*: Strictly beneficial — prevents OOM on noisy proof runs while keeping both opening context and failing traceback tail. Exact `Result(rc=124, out="proof command timed out after %ss" % timeout, blocked="")` contract is preserved on timeout so downstream callers (`crew_card`, `crew_heal`, `crew_coordinator`) see zero breaking changes.
2. **P0-2 (`verify_completion` packet truncation vs multi-call batching)**:
   - *Tradeoff*: Capping packets at `8,000` chars (3-pass ladder) avoids `HTTP 422` in 1 provider call (`provider_calls == 1`). If a card has an unusually large number of unmet prose criteria (> 6) where Pass 1 cannot fit all criterion descriptions + minimum evidence previews inside `8,000` chars, chunking `remaining_criteria` into <= 2-3 sub-batches preserves full criterion fidelity at the cost of extra bounded provider calls (strictly capped by `max_completion_batches = 4`, failing closed to `ESCALATE`/`RETRY` if exceeded).
   - *Assessment*: 99% of runs stay at 1 bounded call (<= 8,000 chars); extreme contracts degrade gracefully instead of crashing with `HTTP 422` or hallucinating `PASS`.
3. **P0-2 (`shadow` mode vs `enforce` mode & `profile.json` hygiene)**:
   - *Tradeoff*: Keeping `pre_tool_call` DoD gating active in `shadow` mode means a misconfigured `work_supervision_enabled: true` still gates `kanban_complete`, whereas operators who want pure zero-gating observation must set `work_supervision_enabled: false`. Meanwhile, migrating `reviewer/nerve/profile.json` (`advanced.work_supervision_mode` alignment + removing nested plaintext `advanced.reflex_openjev_token` in favor of env/Vaultwarden) mutates live `_config/agent4070/hermes/` and therefore MUST remain an explicit Commander-approved operational task.
4. **P1-3 (`block_kind` guard impact on `test_crew_verifier_block.py`)**:
   - *Tradeoff*: Refusing `stale_verify` healing on `block_kind in ("needs_input", "capability")` closes the human-gate bypass but means cards blocked with `needs_input` will wait for the coordinator or owner even if a stale proof passes. Existing unit test fixtures in `test_crew_verifier_block.py` that used `kind="needs_input"` for generic writer blocks must be updated to `kind="transient"`.
5. **P1-4b (`reopen-review` restores implementer assignee on `/crew-unstuck`)**:
   - *Tradeoff*: Because `kanban_db.reopen_review_task()` restores `assignee = implementer` from the `review_requested` event, parking a `review` card and later running `/crew-unstuck` returns it to `ready` assigned to the implementer (rather than resuming directly inside `review` for the reviewer).
   - *Assessment*: Acceptable and actually safer after an explicit owner `/crew-stop` mid-review (the owner usually stops a card to inspect or adjust before re-submitting). Recording `{"prior_status": "review", "prior_reviewer": <assignee>}` in a `crew_stop_parked` event ensures zero reviewer provenance is lost and leaves room for a future `--resume-review` flag if ever desired.

---

## 4. Exploration Exit Readiness

All four defects (P0-1..P1-4) have proven root causes, verified source seams, test-verified compatibility constraints (`CREW-INV-7`, `NERVE-INV-5`, `test_crew_verifier_block.py`, `kernel_board.py`), and clear deep-module designs. Ready to proceed immediately to Stage 1B OpenSpec artifacts (`.openspec.yaml`, `proposal.md`, delta `specs/`, `design.md`, `tasks.md`) strictly under `O:/workspaces/oss/crew/openspec/changes/crew-nerve-completion-and-verdict-resilience/`.
