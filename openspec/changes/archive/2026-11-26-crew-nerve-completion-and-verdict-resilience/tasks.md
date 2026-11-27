# Implementation Tasks: `crew-nerve-completion-and-verdict-resilience`

> **Execution Discipline**: Every implementation slice follows vertical tracer-bullet TDD (failing test first -> minimal deep-module implementation -> full regression verification) inside isolated §9 git worktrees (`O:/workspaces/.worktrees/wt-*`). Primary checkouts (`O:/workspaces/oss/crew`, `O:/workspaces/oss/hermes-nerve`) MUST remain clean and on `main` throughout implementation.

---

## Phase 0: Isolated Worktree Provisioning (§9 Zero-Checkout Gate)

- [x] **0.1 Create isolated git worktrees for `oss/crew` and `oss/hermes-nerve`**
  - **Worktrees**:
    - `O:/workspaces/.worktrees/wt-crew-resilience` (branch `fix/crew-resilience` from `O:/workspaces/oss/crew` `origin/main`)
    - `O:/workspaces/.worktrees/wt-nerve-resilience` (branch `fix/nerve-resilience` from `O:/workspaces/oss/hermes-nerve` `origin/main`)
  - **Proof**: `git -C O:/workspaces/.worktrees/wt-crew-resilience rev-parse --abbrev-ref HEAD && git -C O:/workspaces/.worktrees/wt-nerve-resilience rev-parse --abbrev-ref HEAD && git -C O:/workspaces/oss/crew status --porcelain && git -C O:/workspaces/oss/hermes-nerve status --porcelain`

---

## Slice 1 (P0-1): Windows Git Bash Stdin Isolation & Process-Tree Termination in `crew_safety.run_proof()`

- [x] **1.1 Write failing regression tests for `run_proof()` stdin-pipe deadlock, child-tree cleanup on timeout, and `_exe_py_version()` stdin isolation**
  - **Worktree**: `O:/workspaces/.worktrees/wt-crew-resilience`
  - **Files**: `tests/test_crew_run_proof_resilience.py`
  - **Scope**: Add deterministic tests that:
    1. Spawn a managed-worker-style child holding `stdin=PIPE` with a reader thread blocked in `sys.stdin.readline()`, invoke `crew_safety.run_proof("test -s '...'")` via Windows Git Bash, and assert `rc == 0` in `< 2.0s` (reproducing the `stdin=None` deadlock before fix).
    2. Spawn a proof command that creates a child Python sleeper process, trigger `timeout=1`, assert `res.rc == 124`, `res.out == "proof command timed out after 1s"`, and assert the descendant PID is dead (`crew_proc.alive(child_pid) is False`).
    3. Verify stdout/stderr flood (`> 256 KiB`) is bounded via `crew_proc.HeadTail` without OOM.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_run_proof_resilience.py` (fails red before 1.2)

- [x] **1.2 Route `crew_safety.run_proof()` through `crew_proc.run_bounded()`, add `HERE` `sys.path` guard & `_exe_py_version()` `DEVNULL`, and align existing `crew_safety` test mock seams**
  - **Worktree**: `O:/workspaces/.worktrees/wt-crew-resilience`
  - **Files**: `scripts/crew_safety.py`, `tests/test_crew_proc.py`, `tests/test_crew_safety.py`
  - **Scope**:
    - Add a `HERE = os.path.dirname(os.path.abspath(__file__))` / `if HERE not in sys.path: sys.path.insert(0, HERE)` guard before `import crew_proc` in `scripts/crew_safety.py`.
    - Replace `subprocess.run(...)` in `run_proof()` with `crew_proc.run_bounded(argv, timeout_s=timeout, cwd=cwd, env=proof_env(cmd=cmd))` across Windows PowerShell, Windows Git Bash, and POSIX branches, preserving exact `Result(rc, out, blocked)` semantics (including `rc=124` timeout message and `rc=127` spawn failure).
    - Pass `stdin=subprocess.DEVNULL` to `subprocess.run(...)` inside `_exe_py_version()`.
    - Update the `mock.patch.object(crew_safety.subprocess, "run", ...)` mock seams in `tests/test_crew_proc.py:75-93` and `tests/test_crew_safety.py:511-534` to patch `crew_safety.crew_proc.run_bounded` (asserting routed `argv`, list-vs-str shell semantics, and `BoundedResult` conversion).
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_run_proof_resilience.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_proc.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_safety.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_safety_resolution.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_bounded_runner.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_windows_support.py`

---

## Slice 2 (P0-2a): Bounded `<= 8,000`-Char Semantic Completion Packet & Criterion Sub-Batching in `hermes-nerve`

- [x] **2.1 Write failing TDD tests for `bound_completion_packet()`, `partition_completion_batches()`, and `CardSupervisor.verify_completion()` overflow & semantic fidelity**
  - **Worktree**: `O:/workspaces/.worktrees/wt-nerve-resilience`
  - **Files**: `tests/test_completion_packet_and_cli_verdict.py`
  - **Scope**: Add deterministic tests asserting:
    1. A 45,000-char input (`24` evidence entries x `1,500`-char previews + `12,000`-char proposal) serializes to `<= 8,000` chars under both ASCII and UTF-8 JSON via the 3-pass ladder, retaining unmet criteria IDs and prioritizing `criterion_id`-linked evidence, AND the combined request payload (`safe_json_len(state) + len(instructions)`) stays `<= 9,500` chars (leaving safe wrapper headroom under the `8,192`-token OpenJev context window).
    2. When `evidence_truncated` is `True`, truncation metadata (`evidence_truncated`, `omitted_evidence_count`) is included in the packet and prompt forbids false `PASS` on omitted evidence; empty evidence returns `NEEDS_EVIDENCE` with `0` provider calls.
    3. Contracts with large unmet criteria lists partition into `<= 4` bounded sub-batches (`<= 8,000` chars each), passing only when every batch returns `PASS` and failing closed (`ESCALATE`) if batch cap is exceeded.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_completion_packet_and_cli_verdict.py` (fails red before 2.2)

- [x] **2.2 Implement `hermes_nerve/work/packet_bound.py` and wire `CardSupervisor.verify_completion()` to bounded packets & sub-batches**
  - **Worktree**: `O:/workspaces/.worktrees/wt-nerve-resilience`
  - **Files**: `hermes_nerve/work/packet_bound.py`, `hermes_nerve/work/supervisor.py`
  - **Scope**:
    - Implement `MAX_COMPLETION_PACKET_CHARS = 8000`, `MAX_COMPLETION_BATCHES = 4`, `safe_json_len()`, `bound_completion_packet()`, and `partition_completion_batches()`.
    - Wire `CardSupervisor.verify_completion()` to build bounded packets/batches, include the anti-false-PASS semantic fidelity clause in `instructions`, record usage per batch, and only persist `VERIFIED_PASS` when all batches return `PASS`.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_completion_packet_and_cli_verdict.py O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_work_supervision.py O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_nervous.py`

---

## Slice 3 (P0-2b & P0-2c): CLI `crew_card.py verdict` Zero-Token Observer & Supervision Mode Precedence Visibility

- [x] **3.1 Write failing TDD tests for CLI `crew_card.py verdict` recognition, FAIL routing, card-ID anti-spoofing, `advanced_override_sources`, and `NERVE-INV-5` shadow-mode gating**
  - **Worktree**: `O:/workspaces/.worktrees/wt-nerve-resilience`
  - **Files**: `tests/test_completion_packet_and_cli_verdict.py`
  - **Scope**: Add tests proving:
    1. `terminal` running `python scripts/crew_card.py verdict --card <task_id>` with `rc=0` and `verdict: PASS` text output marks matching locked Crew verdict criterion `VERIFIED_PASS` with `provider_calls == 0`.
    2. `terminal` running `crew_card.py verdict --card <task_id>` (including with `--command "pytest -q"`) returning `rc=1` or `rc=3` and `verdict: FAIL ...` routes through `observe_test_result()` -> `observe_crew_verdict()` and records authoritative deterministic `FAIL` (never silently dropped by `deterministic.py:108` or swallowed by the `pytest` branch at `L177`).
    3. Mismatched `--card <other_id>` or bare `echo "PASS"` is ignored (`observed: False`, `marked: 0`).
    4. `resolve_config()` sets `advanced_override_sources["work_supervision_mode"] = "profile.json:advanced"` without polluting `override_sources` (`module_override_sources`) when sidecar overrides `config.yaml`.
    5. `hooks.pre_tool_call()` continues blocking premature `kanban_complete` / `crew_review_handoff` in `shadow` mode (`NERVE-INV-5`).
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_completion_packet_and_cli_verdict.py` (fails red before 3.2)

- [x] **3.2 Implement CLI verdict parsing in `hermes_nerve/work/deterministic.py` and `advanced_override_sources` in `hermes_nerve/config_resolver.py`**
  - **Worktree**: `O:/workspaces/.worktrees/wt-nerve-resilience`
  - **Files**: `hermes_nerve/work/deterministic.py`, `hermes_nerve/config_resolver.py`
  - **Scope**:
    - Extend `_extract_crew_verdict_call()` and `observe_crew_verdict()` with strict `crew_card.py verdict --card <task_id>` parsing bound to `identity.task_id`, recognizing `crew_card.py`'s real text format (`verdict: PASS` / `verdict: FAIL`, `rc=0|1|3`) as well as JSON envelopes.
    - Update `deterministic.py:108` to `if tn not in {"crew_verdict", "crew_verdict_cli"} and verdict != "PASS":` and `deterministic.py:170` (`observe_test_result`) to `if tn in {"crew_verdict", "crew_verdict_cli"}:`.
    - Add `advanced_override_sources: dict[str, str] = field(default_factory=dict)` on `ResolvedNerveConfig` in `config_resolver.py` and populate `advanced_override_sources["work_supervision_mode"] = "profile.json:advanced"` whenever sidecar overrides `config.yaml`.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_completion_packet_and_cli_verdict.py O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_crew_dod_and_handoff.py O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_dev16_nerve_budget.py O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_shadow_completion_gate.py O:/workspaces/.worktrees/wt-nerve-resilience/tests/test_sidecar_authority.py`

---

## Slice 4 (P1-3): Verifier-Lane vs Two-Stage Predicates & Human/Capability Block Protection in `crew_card` & `crew_heal`

- [x] **4.1 Add TDD regression tests for `Verify: dual`/`agent` verifier blocks, `Verify: agent` no-op in `hand_to_writer()`, and `needs_input`/`capability` heal protection**
  - **Worktree**: `O:/workspaces/.worktrees/wt-crew-resilience`
  - **Files**: `tests/test_crew_verifier_block.py`, `tests/test_crew_heal.py`
  - **Scope**:
    - Update `blocked_card(..., kind="transient")` in `test_crew_verifier_block.py` for the two non-verifier stale-block tests (`test_a_stale_block_that_is_not_the_verifiers_still_heals` and `test_a_proof_card_blocked_by_its_verifier_run_still_heals`).
    - Add failing tests asserting:
      1. `Verify: dual` verifier-blocked cards are recognized by `crew_card.verifier_block()`, refused by `crew_heal.heal_card()`, and handed back to the writer by `crew_card.hand_to_writer()`.
      2. Standalone `Verify: agent` verifier-blocked cards (`Role: verifier`) are recognized by `crew_card.verifier_block()` and refused by `crew_heal.heal_card()`, while `crew_card.hand_to_writer()` returns `{"reopened": False, "assigned": ""}` and leaves the card assigned to the verifier profile (never reassigned to `crew-worker`).
      3. Cards blocked with `block_kind="needs_input"` or `block_kind="capability"` (both via `card["block_kind"]` and via DB fallback when `card` dict omits `"block_kind"`) are NEVER auto-healed by `heal_card()` or `heal_stale_verify()`.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_verifier_block.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_heal.py` (fails red before 4.2)

- [x] **4.2 Implement `uses_verifier_lane()` + `uses_review_handoff()` in `crew_card.py` and `NON_HEALABLE_BLOCK_KINDS` / `_card_block_kind()` in `crew_heal.py`**
  - **Worktree**: `O:/workspaces/.worktrees/wt-crew-resilience`
  - **Files**: `scripts/crew_card.py`, `scripts/crew_heal.py`
  - **Scope**:
    - Define `VERIFIER_VERIFY_MODES = ("independent", "agent", "dual")` / `uses_verifier_lane(body)` (used in `closer_profiles()` and `verifier_block()`) and `TWO_STAGE_VERIFY_MODES = ("independent", "dual")` / `uses_review_handoff(body)` (used in `hand_to_writer()`, `repin_for_review()`, and `send_to_verifier()`) in `scripts/crew_card.py`.
    - Define `NON_HEALABLE_BLOCK_KINDS = frozenset({"needs_input", "capability"})` and `_card_block_kind(card)` in `scripts/crew_heal.py` and enforce it in both `heal_card()` and `heal_stale_verify()`.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_verifier_block.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_heal.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_role_contracts.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_two_stage.py && O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E O:/workspaces/.worktrees/wt-crew-resilience/scripts/crew_heal_proof.py`

---

## Slice 5 (P1-4): Coordinator Post-Resolve Stop Guard & `review`-Lane Non-Destructive Parking

- [x] **5.1 Add `reopen-review` stand-in in `tests/kernel_board.py` and write failing TDD tests for post-resolve `/crew-stop` race & `review`-lane parking**
  - **Worktree**: `O:/workspaces/.worktrees/wt-crew-resilience`
  - **Files**: `tests/kernel_board.py`, `tests/test_crew_stop_park.py`, `tests/test_crew_coordinator.py`
  - **Scope**:
    - Add `elif verb == "reopen-review": ok = kb.reopen_review_task(conn, cid)` in `tests/kernel_board.py::kernel_cli`.
    - Add failing test in `test_crew_coordinator.py` (or `test_crew_stop_park.py`) where the stub `decider` invokes `crew_stop.main([cid])` (and separately `--archive`) *during* `resolve()` and returns `{"decision": "retry", "fix": "..."}` — assert `handle_card()` returns `action == "skip"`, leaves the card parked/archived, and writes zero `unblocked` or applied `retry` events.
    - Add failing tests in `test_crew_stop_park.py` for: (a) parking an open `review` card (`review -> ready -> blocked`, exit `0`, `parked_by_owner > 0`, `crew_stop_parked` event records `prior_status: "review"` and `prior_reviewer`); (b) parking a parent-gated `review` card (`review -> todo -> scheduled`, stays down across `recompute_ready()`); (c) `--dry-run` on a `review` card makes zero board mutations.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_stop_park.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_coordinator.py` (fails red before 5.2)

- [x] **5.2 Implement `_stop_guard_reason()` in `scripts/crew_coordinator.py` and two-step `review` parking in `scripts/crew_stop.py`**
  - **Worktree**: `O:/workspaces/.worktrees/wt-crew-resilience`
  - **Files**: `scripts/crew_coordinator.py`, `scripts/crew_stop.py`
  - **Scope**:
    - Extract `_stop_guard_reason(ctx, card_id, newest_event_id)` in `scripts/crew_coordinator.py` and call it both pre-`resolve()` and immediately post-`resolve()` before `apply_decision()`.
    - Teach `scripts/crew_stop.py::park_card()` to park `status == "review"` via `reopen-review`, inspect post-reopen status (`ready` -> `block`, `todo` -> `schedule`), retry the follow-up park once on transient refusal, and append a `crew_stop_parked` audit event with `prior_status` and `prior_reviewer`. Update `crew_stop.py` module docstring to reflect `review` parking support.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -m pytest -p no:cacheprovider -q O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_stop_park.py O:/workspaces/.worktrees/wt-crew-resilience/tests/test_crew_coordinator.py && O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E O:/workspaces/.worktrees/wt-crew-resilience/scripts/crew_stop_proof.py`

---

## Slice 6: Watchdog Invariants, Full Invariant Gates & Diff Hygiene

- [x] **6.1 Update `crew-upstream-sync` and `nerve-upstream-sync` watchdog scripts and skill invariant matrices**
  - **Worktree / Scope**: `O:/workspaces/.agents/skills/crew-upstream-sync/{SKILL.md,scripts/daily-sync-watchdog.ps1}`, `O:/workspaces/.agents/skills/nerve-upstream-sync/{SKILL.md,scripts/daily-sync-watchdog.ps1}`
  - **Scope**: Add `CREW-INV-9` (or extend `CREW-INV-7`) static anchors + new Crew invariant tests, and add `NERVE-INV-8` static anchors + 45,000-char bounding probe + `tests/test_completion_packet_and_cli_verdict.py` to `$InvariantTests`.
  - **Proof**: `& "C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -File O:\workspaces\.agents\skills\crew-upstream-sync\scripts\daily-sync-watchdog.ps1 -GateOnly -Target O:\workspaces\.worktrees\wt-crew-resilience && & "C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -File O:\workspaces\.agents\skills\nerve-upstream-sync\scripts\daily-sync-watchdog.ps1 -GateOnly -Target O:\workspaces\.worktrees\wt-nerve-resilience`

- [x] **6.2 Run range diff hygiene (`git diff --check`) and verify primary checkouts remain clean (§9)**
  - **Worktrees**: `O:/workspaces/.worktrees/wt-crew-resilience`, `O:/workspaces/.worktrees/wt-nerve-resilience`
  - **Proof**: `git --no-pager -C O:/workspaces/.worktrees/wt-crew-resilience diff --check origin/main && git --no-pager -C O:/workspaces/.worktrees/wt-nerve-resilience diff --check origin/main && git -C O:/workspaces/oss/crew status --porcelain -- scripts tests && git -C O:/workspaces/oss/hermes-nerve status --porcelain`

---

## Slice 7: Commander-Gated Publication, Live Plugin Cutover & Profile Secret Hygiene

- [x] **7.1 [COMMANDER APPROVAL GATE] Publish verified worktree commits to `origin/main` and execute live Crew & Nerve cutovers**
  - **Gate**: Requires explicit Commander approval after Phase 3 independent `@reviewer` (`findings-verify-vN.md` `Verdict: APPROVED`) and QA compliance pass.
  - **Scope**:
    1. Push `wt-crew-resilience` (`HEAD:main`) and `wt-nerve-resilience` (`HEAD:main`).
    2. Run `pwsh -NoProfile -File O:/workspaces/_config/agent4070/hermes/services/apply-live-crew-cutover.ps1 -ExpectedSha <crew_sha>` (verifies 7-profile SHA-256 parity + Desktop hot-reload).
    3. Run `pwsh -NoProfile -File O:/workspaces/_config/agent4070/hermes/services/apply-live-nerve-cutover.ps1 -ExpectedSha <nerve_sha>` (verifies plugin git alignment + SHA-256 parity).
    4. Surface any `MANUAL:` Hermes Gateway (`:8642`) / Dashboard (`:9119`) restart requirements without autonomously restarting live services.
  - **Proof**: `& "C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -File O:\workspaces\_config\agent4070\hermes\services\apply-live-crew-cutover.ps1 -DryRun && & "C:\Program Files\PowerShell\7\pwsh.exe" -NoProfile -File O:\workspaces\_config\agent4070\hermes\services\apply-live-nerve-cutover.ps1 -DryRun`

- [x] **7.2 [COMMANDER APPROVAL GATE] Live `profile.json` secret hygiene & `work_supervision_mode` alignment**
  - **Gate**: Requires explicit Commander approval before mutating `O:/workspaces/_config/agent4070/hermes/profiles/reviewer/nerve/profile.json`.
  - **Scope**:
    1. Back up `O:/workspaces/_config/agent4070/hermes/profiles/reviewer/nerve/profile.json` to `<profile>\backups\`.
    2. Remove nested plaintext `advanced.reflex_openjev_token` (confirming token is supplied via Vaultwarden-populated environment variable) and align `advanced.work_supervision_mode` with Commander policy (`shadow` or explicit `enforce`).
    3. Recursively scan all 7 profiles' `nerve/profile.json` for nested secret key names (`*token*`, `*secret*`, `*api_key*`, `*password*`) without printing any values, asserting `0` matches.
  - **Proof**: `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -B -E -c "import json, pathlib, re, sys; base=pathlib.Path('O:/workspaces/_config/agent4070/hermes'); rx=re.compile(r'(token|secret|api_key|password)', re.I); bad=[]; files=[base/'nerve'/'profile.json', *(base/'profiles').glob('*/nerve/profile.json')]; walk=lambda o,p='': [k for key,val in o.items() for k in (([f'{p}.{key}' if p else key] if rx.search(key) else []) + (walk(val, f'{p}.{key}' if p else key) if isinstance(val, dict) else []))] if isinstance(o, dict) else []; [bad.append((str(f), k)) for f in files if f.exists() for k in walk(json.loads(f.read_text(encoding='utf-8')))]; print('OK: 0 nested secret keys' if not bad else f'FAIL: {bad}'); sys.exit(1 if bad else 0)"`
