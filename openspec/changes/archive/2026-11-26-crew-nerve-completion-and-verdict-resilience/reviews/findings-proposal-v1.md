# Stage 1C Proposal Review: `crew-nerve-completion-and-verdict-resilience` (Round 1)

Verdict: REJECTED

- **Change**: `crew-nerve-completion-and-verdict-resilience` (`O:/workspaces/oss/crew/openspec/changes/crew-nerve-completion-and-verdict-resilience/`)
- **Reviewer**: `@reviewer` (independent two-axis Stage 1C review)
- **Date**: 2026-11-26
- **Inputs Inspected**: `#3` (`@researcher` recon), `#5` (`@designer` delivery), `.openspec.yaml`, `explorations/2026-11-26-crew-nerve-completion-and-verdict-resilience-exploration.md`, `proposal.md`, `specs/{proof-safety,crew-extended-tools,nerve-completion-verdict-resilience,crew-heal-and-stop-resilience}/spec.md`, `design.md`, `tasks.md`, canonical specs, and live source/tests across `oss/crew`, `oss/hermes-nerve`, and `oss/hermes-agent`.
- **OpenSpec Strict Validation Proof**:
  - Command: `Set-Location O:\workspaces\oss\crew; C:\nvm4w\nodejs\openspec.cmd validate crew-nerve-completion-and-verdict-resilience --strict --json`
  - Exit Code: `0` (`"valid": true`, `"issues": []`, `"passed": 1`, `"failed": 0`)

---

## Axis 1: Governance, Executability & Pre-Merge Safety

| Check | Status | Evidence |
| :--- | :--- | :--- |
| Single Target Invariant | PASS | `rg` across `O:/workspaces/openspec`, `O:/workspaces/oss/hermes-nerve/openspec`, `O:/workspaces/oss/hermes-agent/openspec` found zero mirror files for `crew-nerve-completion-and-verdict-resilience`. |
| Stage 1A Exploration & Link | PASS | `explorations/2026-11-26-crew-nerve-completion-and-verdict-resilience-exploration.md` (138 lines) exists and is linked by `.openspec.yaml:3` (`x-exploration`). |
| Strict OpenSpec CLI Gate | PASS | Independently re-ran `openspec.cmd validate ... --strict --json` -> exit `0`, zero errors, zero warnings. |
| Pre-Merge Safety Gate (`MODIFIED Requirements`) | PASS | `specs/crew-extended-tools/spec.md` modifies `Stop Card Tool` while preserving all 3 canonical scenarios (`Agent parks a running crew card`, `Agent archives a card`, `Non-crew card or dry run` from `O:/workspaces/oss/crew/openspec/specs/crew-extended-tools/spec.md:6-21`) verbatim and adding `Agent parks a review-lane crew card`. `specs/proof-safety/spec.md` uses `## ADDED Requirements` only. |
| Spec Formatting & Design Sections | PASS | Uppercase `SHALL`/`MUST` and `#### Scenario:` (`- GIVEN`/`- WHEN`/`- THEN`) used consistently; both new specs have `## Purpose` >= 50 chars; `design.md` includes `## Architecture Updates`, 3-row `## Negative Impact Analysis`, §9 worktree plan, and watchdog updates; zero plaintext secrets leaked. |
| `tasks.md` Executability & Scope | WARNING | See **W1-1** below (ambiguous test file name in `1.1`, missing existing `crew_safety` test files in `1.2`, and `facts["parked"]` placement vs top-level in `specs/crew-extended-tools/spec.md:17`). |

### Axis 1 Findings

- **[WARNING] W1-1 (`tasks.md:21, 26, 35`) — Ambiguous new test filename and omitted regression suites in Slice 1**:
  - Task `1.1` (`tasks.md:21`) lists `tests/test_crew_safety_resolution.py (or dedicated tests/test_crew_run_proof_resilience.py)`, while its `Proof:` command (`tasks.md:26`) and Task `1.2`'s `Proof:` (`tasks.md:35`) hardcode `tests/test_crew_run_proof_resilience.py`. Commit unconditionally to `tests/test_crew_run_proof_resilience.py`.
  - Task `1.2` (`tasks.md:35`) omits `tests/test_crew_proc.py` and `tests/test_crew_safety.py`, both of which directly exercise `crew_safety.run_proof()` (and break under the proposed change — see **C2-2**).
- **[WARNING] W1-2 (`specs/crew-extended-tools/spec.md:17`) — `parked: true` field placement in `crew_stop_card` JSON response**:
  - `specs/crew-extended-tools/spec.md:17` requires `the result MUST report status: ok, stopped: true, and parked: true`. On disk, `O:/workspaces/oss/crew/native_tools.py:831-838` returns top-level `status`, `card_id`, `stopped`, `archived`, `facts`, `report`, with `parked` inside `facts["parked"]` (`crew_stop.py:349`). Clarify in the spec/design whether `facts.parked: true` satisfies this or whether top-level `parked` should also be emitted without breaking existing callers.

---

## Axis 2: Technical Fidelity & Seam Accuracy (Ground-Truth Cross-Check)

### CRITICAL Findings (Blocking — Must Fix Before Approval)

- **[CRITICAL] C2-1 (`design.md:151-164`, `specs/crew-heal-and-stop-resilience/spec.md:8-17`, `tasks.md:91, 99`) — P1-3 conflates `Verify: agent` (standalone verifier card) with two-stage `Verify: independent` / `Verify: dual`, causing `hand_to_writer()` to hijack `Verify: agent` cards onto `crew-worker`**:
  - **Ground Truth on Disk**:
    - `O:/workspaces/oss/crew/scripts/crew_card.py:974-988`: `Verify: agent` is explicitly `"a standalone verifier card: %s is its only writer, writes the findings artifact, runs the proof command itself... This card is never handed off for review: crew_review_handoff is refused."`
    - `O:/workspaces/oss/crew/tests/test_role_contracts.py:490-576`: Verifies `("independent", "dual")` are the two-stage review-handoff modes (`kanban_request_review`), whereas `("proof", "agent", "closeout")` are direct-completion modes.
    - `O:/workspaces/oss/crew/__init__.py:1326-1333`, `O:/workspaces/oss/crew/native_tools.py:887-891`, `O:/workspaces/oss/crew/tests/test_crew_two_stage.py:80-95`: `Verify: agent` explicitly refuses `kanban_request_review` and `crew_review_handoff`.
  - **Defect in Proposal/Design/Spec**:
    - `design.md:153-164` defines a single predicate `VERIFIER_VERIFY_MODES = ("independent", "agent", "dual")` (`uses_verifier_lane(body)`) and applies it across **all 5** functions: `closer_profiles()`, `verifier_block()`, `hand_to_writer()`, `repin_for_review()`, and `send_to_verifier()`.
    - `specs/crew-heal-and-stop-resilience/spec.md:11-16` and `tasks.md:91` explicitly require `Verify: agent` cards to be `"handed back to the writer by crew_card.hand_to_writer()"`.
    - **Regression**: On a `Verify: agent` card (`Role: verifier`, `assignee = role_profile("verifier")`), `crew_card.hand_to_writer()` (`crew_card.py:2586-2596`) checks `role if role in WRITER_ROLES else "worker"` (`WRITER_ROLES = ("worker", "content")` at `crew_card.py:45`), resolves `writer = role_profile("worker")` (`crew-worker`), sees `now[3] in judges` is `True`, and **reassigns the standalone verifier card to `crew-worker`** — violating the standalone verifier contract! Similarly, `repin_for_review()` (`crew_card.py:1404`) and `send_to_verifier()` (`crew_card.py:2016`) are strictly two-stage review-handoff operations for `("independent", "dual")` only.
  - **Required Fix**:
    - Separate the two distinct concepts cleanly in `crew_card.py`, `design.md`, `specs/crew-heal-and-stop-resilience/spec.md`, and `tasks.md`:
      1. `VERIFIER_VERIFY_MODES = ("independent", "agent", "dual")` / `uses_verifier_lane(body)` — modes whose closing verdict and verifier block belong to the verifier (`closer_profiles()`, `verifier_block()`).
      2. `TWO_STAGE_VERIFY_MODES = ("independent", "dual")` / `uses_review_handoff(body)` — modes that hand off from a separate writer to a verifier `review` lane (`hand_to_writer()`, `repin_for_review()`, `send_to_verifier()`). `hand_to_writer()` MUST remain a no-op (`{"reopened": False, "assigned": ""}`) for `Verify: agent`.

- **[CRITICAL] C2-2 (`design.md:70-88`, `tasks.md:19-36`) — P0-1 switching `crew_safety.run_proof()` to `crew_proc.run_bounded()` breaks existing `crew_safety.subprocess.run` mock seams in `tests/test_crew_proc.py:83` and `tests/test_crew_safety.py:520` and lacks a `sys.path` import guard**:
  - **Ground Truth on Disk**:
    - `O:/workspaces/oss/crew/tests/test_crew_proc.py:75-93`: Patches `mock.patch.object(crew_safety.subprocess, "run", fake_run)` (`L83`) and asserts `run_proof("echo hi", ...)` invoked `fake_run` (`L86-87`).
    - `O:/workspaces/oss/crew/tests/test_crew_safety.py:511-534`: `SafetyCase.routed_argv` patches `mock.patch.object(crew_safety.subprocess, "run", side_effect=fake_run)` (`L520`), calls `crew_safety.run_proof(...)`, and indexes `seen[0]` (`L523`), which raises `IndexError` when `run_proof()` calls `crew_proc.run_bounded()` (`crew_proc.subprocess.Popen`) instead of `crew_safety.subprocess.run`.
    - `O:/workspaces/oss/crew/scripts/crew_safety.py:1-35`: Does NOT add `HERE` (`scripts/`) to `sys.path` (unlike `crew_card.py:36-38` and `crew_heal.py:27-29`), so bare `import crew_proc` fails if a caller loads `crew_safety.py` without `scripts/` on `sys.path`.
  - **Required Fix**:
    - Update `design.md` §2.1 and `tasks.md` Slice 1 (`1.1` / `1.2`) to explicitly update the `crew_safety.subprocess.run` mock seams in `tests/test_crew_proc.py:83` and `tests/test_crew_safety.py:520` (e.g., patching `crew_proc.subprocess.Popen` or `crew_proc.run_bounded`), include `tests/test_crew_proc.py` and `tests/test_crew_safety.py` in Task `1.2`'s `Proof:` command, and specify a `HERE` `sys.path` guard before importing `crew_proc` in `scripts/crew_safety.py`.

- **[CRITICAL] C2-3 (`design.md:125-138`, `tasks.md:62-80`) — P0-2b returning `tn = "crew_verdict_cli"` causes `observe_crew_verdict()` (`deterministic.py:108`) to drop ALL CLI `FAIL` verdicts and `observe_test_result()` (`deterministic.py:170`) to skip CLI verdict calls**:
  - **Ground Truth on Disk**:
    - `O:/workspaces/oss/hermes-nerve/hermes_nerve/work/deterministic.py:108`:
      ```python
      if tn != "crew_verdict" and verdict != "PASS":
          return {"observed": False, "passed": False, "failed": False, "provider_calls": 0}
      ```
      Any tool tag other than `"crew_verdict"` is ignored whenever `verdict != "PASS"`.
    - `O:/workspaces/oss/hermes-nerve/hermes_nerve/work/deterministic.py:169-178` (`observe_test_result`): Dispatches `observe_crew_verdict()` **only** `if tn == "crew_verdict":`. If a worker invokes `crew_card.py verdict --card <id> --command "pytest -q"`, `observe_test_result()` enters the `"pytest" in command` branch (`L177`), marks `TEST_PASSED` / `observed=True` (`L198`) or `observed=True, failed=True` (`L247`), and **prevents `hooks.py:928` (`if not test_observation.get("observed"): observe_crew_verdict(...)`) from calling `observe_crew_verdict()`**.
    - `O:/workspaces/oss/crew/scripts/crew_card.py:2240, 2246, 2249, 2266`: `crew_card.py verdict` prints text starting with `"verdict: PASS"` (`rc=0`) or `"verdict: FAIL ..."` (`rc=1` or `rc=3` on second failure), NOT JSON.
  - **Defect in Proposal/Design**:
    - `design.md:136` specifies returning `("crew_verdict_cli", {"verdict": parsed_verdict, "rc": parsed_rc, "card": cid})` from `_extract_crew_verdict_call()`, without updating `deterministic.py:108` or `observe_test_result()` (`deterministic.py:170`). Under that design, `FAIL` verdicts (`rc=1` / `rc=3`) from `crew_card.py verdict --card <id>` return `{"observed": False, ...}`, directly violating `specs/nerve-completion-verdict-resilience/spec.md:40-44` and `tasks.md:67`.
  - **Required Fix**:
    - Update `design.md` §2.2 P0-2b and `tasks.md:77` to explicitly:
      1. Update `deterministic.py:108` to `if tn not in {"crew_verdict", "crew_verdict_cli"} and verdict != "PASS":`.
      2. Update `deterministic.py:170` (`observe_test_result`) to `if tn in {"crew_verdict", "crew_verdict_cli"}:`.
      3. Explicitly parse `crew_card.py verdict`'s real text header (`verdict: PASS` / `verdict: FAIL`) and `rc=0` / non-zero exit codes (`1`, `3`).

---

### Non-Blocking Warnings & Info (Axis 2)

- **[WARNING] W2-1 (`design.md:141`, `hermes_nerve/config_resolver.py:128-141`, `control_panel.py:212`) — `override_sources` namespace mixing**:
  - `config_resolver.py:128-141` populates `ResolvedNerveConfig.override_sources` strictly with module names (`MODULES`), and `control_panel.py:212` exposes it as `"module_override_sources"`. Writing `"work_supervision_mode": "profile.json:advanced"` into `override_sources` mixes an `advanced` key into `module_override_sources`. Consider adding a separate `advanced_override_sources: dict[str, str]` field (default `{}`) on `ResolvedNerveConfig` or explicitly scoping `control_panel.py` / `test_deep_review_regressions.py` if `override_sources` is shared.
- **[WARNING] W2-2 (`design.md:228-229` vs `design.md:241`) — Retry-once discrepancy in `park_card()`**:
  - Negative Impact #3 (`design.md:241`) states `park_card()` retries the follow-up `block`/`schedule` once on transient failure, whereas §2.4 P1-4b (`design.md:228-229`) shows a single `hermes kanban <argv>` call. Align §2.4 P1-4b with the retry-once safeguard in §3.
- **[WARNING] W2-3 (`design.md:95-123`) — Wrapper token headroom vs `8,192` token limit**:
  - `MAX_COMPLETION_PACKET_CHARS = 8000` bounds `state` only; `DecisionEngine.verify()` (`engine.py:263-283`) + `OpenJevClient.system_one()` (`openjev.py:253-260`) also send `questions.decision.instructions` + `criteria` (`PASS`/`RETRY`/`REPLAN`/`ESCALATE`) + OpenJev's server prompt template. While 8,000 chars of JSON + ~850 chars of instructions/criteria normally fits well under 8,192 tokens, dense hex/ID payloads tokenize denser (~2 chars/token); document why `8000` leaves wrapper headroom and add a character-count sanity assertion on the full request payload (`state` + `instructions`) in tests.
- **[INFO] I2-1 (Verified Sound Components)**:
  - **P1-3 `block_kind` guard**: Confirmed `tests/test_crew_verifier_block.py:69, 89-99` uses `kind="needs_input"` for stale-block fixtures and passes minimal dicts (`{"id": cid, "status": "blocked", "body": BODY}`); `crew_heal._card_block_kind()` with `KANBAN_DB` fallback and updating those two fixtures to `kind="transient"` is accurate.
  - **P1-4a `_stop_guard_reason()`**: Confirmed `crew_coordinator.py:960-1004` lacks post-`resolve()` re-check and `crew_coordinator.py:222` (`stopped_after`) + `crew_card.py:2489` (`parked_by_owner`) match cited signatures.
  - **P1-4b `reopen-review` + `block`/`schedule`**: Confirmed `kanban_db.py:3620-3655` (`reopen_review_task`) transitions `review -> ready|todo`, `tests/kernel_board.py:66-99` (`kernel_cli`) lacks `reopen-review`, and `crew_card.py:1280` (`_append_card_event`) accepts `(card_id, kind, payload, run_id=None, db=None)`.
  - **P0-2c `shadow` mode**: Confirmed `tests/test_crew_dod_and_handoff.py:49-54, 103-112` enforces `pre_tool_call()` completion gating under default `mode="shadow"`, matching `NERVE-INV-5`.
