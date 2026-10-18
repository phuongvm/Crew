# Independent Review: Crew Intake Dispatch and Verification Taxonomy

- **Card:** `t_5fad288d`
- **Reviewed artifact:** `openspec/workspace/explorations/2026-10-14-crew-intake-and-verify-taxonomy.md`
- **Repository:** `O:/workspaces/oss/crew`
- **Inspected commit:** `026e5f4c9b8c8edef4809eab8110e3070c4e9090`
- **Review date:** 2026-10-14
- **Reviewer:** `@reviewer` (`cb-agent-reviewer`)
- **Implementation edits by reviewer:** none

## Verdict

**Verdict: REJECTED**

The exploration accurately identifies the principal production root cause and several secondary defects, and its current-baseline test results reproduce. The proposed remediation is not ready to become an implementation contract, however. It contains lifecycle deadlocks, an intake-command bypass that permits the same class of side effect the design says it prevents, unsafe rollout ordering, incomplete review handoff state changes, and missing tests for those paths.

Finding count: **4 CRITICAL, 6 HIGH, 4 MEDIUM, 2 INFO**.

Approval requires resolving C-01 through C-04 and H-01 through H-06 in the design and test plan before implementation or profile activation.

## Scope and acceptance audit

| Required audit area | Result | Evidence |
|---|---|---|
| Root-cause coverage | PASS WITH CORRECTIONS | Plugin activation, missing `crew.role`, parent bypass, inert taxonomy branches, and watcher limitation reproduce against source and live profile state. M-01 corrects one overclaim. |
| Hook-guard design | FAIL | C-01, C-02, H-03, H-04, H-05, M-02. |
| `proof` / `agent` / `dual` lifecycle | FAIL | C-03, H-01, H-02, H-06, M-03. |
| Activation/remediation ordering | FAIL | C-04. |
| Test verification and plan | FAIL | Current failures reproduce; proposed X1-X15 omit blocking transitions and bypasses (M-04). |
| Zero-Checkout | PASS | `oss/crew` remained on `main`; no checkout/switch or implementation edit was performed. |

## Independently reproduced evidence

### 1. Live plugin/role state

Command:

```sh
for p in coder reviewer leader designer qa researcher default; do
  hermes -p "$p" plugins list --plain | grep -E 'crew($|[[:space:]])'
done
```

Observed:

```text
coder      not enabled  user  0.9.9  crew
reviewer   not enabled  user  0.9.9  crew
leader     not enabled  user  0.9.9  crew
designer   not enabled  user  0.9.9  crew
qa         not enabled  user  0.9.9  crew
researcher not enabled  user  0.9.9  crew
default    enabled      user  0.9.9  crew
```

Independent YAML reads found `crew.role == None` in all six specialist profiles. This confirms the exploration's primary finding: `gate_manifest()` refuses unenabled user plugins (`oss/hermes-agent/hermes_cli/plugins_discovery.py:257-303`), while `_crew_role()` returns an empty role when the profile config lacks `crew.role` (`__init__.py:669-689`). Therefore the worker/verifier guard branches at `__init__.py:1285-1346` are inactive in dispatched specialist runs.

The reviewer log also contains repeated physical warnings that `completed-handoff-review` is unavailable, including 2026-10-14 09:53:13, 10:37:35, and 11:42:57. This supports the parent-create/canonical-skill defect.

### 2. Board behavior

The board records both `t_78d7dad8` and `t_cad1a3fe` as completed by real `reviewer` runs, followed by a coordinator `owner_close` decision saying no PASS line existed. Those were not owner CLI overrides. This reproduces the false attribution described in the exploration and follows directly from `audit_completion()` treating every failed close check as `owner_close` (`scripts/crew_coordinator.py:889-907`).

The board also records a functioning same-card review loop on `t_a18f20c9`: coder `review_requested`, reviewer `changes_requested`, coder `review_requested`, reviewer `completed`, then coordinator audit PASS. This is valid evidence that the kernel supports a same-card dual loop. It does not prove that the proposed Crew-specific guard, routing, skill, and model transitions are correct.

### 3. Current test baseline

Interpreter:

```text
O:/workspaces/_config/agent4070/hermes/hermes-agent/venv/Scripts/python.exe
```

Commands and results:

```text
python -m unittest tests.test_crew_intake_create
Ran 37 tests
FAILED (failures=1)
exit 1

python -m unittest tests.test_crew_two_stage
Ran 9 tests
OK
exit 0

python -m unittest tests.test_crew_verifier_block tests.test_crew_watch
Ran 16 tests
FAILED (errors=16)
exit 1
```

The intake failure is the stale `Verifier: crew-verifier` expectation at `tests/test_crew_intake_create.py:114`; the rendered value is `Verifier: default` in the isolated profile environment. All 16 other errors originate at `tests/kernel_board.py:22`, where the current Hermes `connect()` opens a fresh path read-only and raises `sqlite3.OperationalError: unable to open database file`. This independently confirms the report's measured baseline.

### 4. Static bypass and taxonomy probes

Probe output:

```text
DUAL_CLOSERS=['crew-coordinator', 'crew-verifier', 'leader', 'reviewer']
WRITE_RX_PROBES=[
  ('python restore_buzz_definitions.py --apply', False),
  ('echo change 1> file.txt', False),
  ('powershell -NoProfile -Command Set-Content', False)
]
MAX_REVIEW_ROUNDS=None
```

This output is produced directly from `crew_card.closer_profiles`, `VERIFIER_WRITE_RX`, and `roles/roles.json` at the inspected commit.

## Blocking findings

### C-01 — CRITICAL — Proposed `dual` writer-PASS gate is internally inconsistent

**Evidence:**

- Exploration T2 leaves `agent`/`independent`/`dual` closer selection unchanged (`...taxonomy.md:195`).
- Exploration T5 requires the writer's PASS to satisfy a `close_check`-based gate before `kanban_request_review` (`...taxonomy.md:198`).
- `closer_profiles()` permits only verifier/coordinator for `dual` (`scripts/crew_card.py:1886-1900`).
- `close_check()` rejects a PASS whose `by` profile is not in that closer set (`scripts/crew_card.py:1955-1984`).

A coder PASS can therefore never satisfy ordinary `close_check()` on a `dual` card. The proposed helper name `writer_pass(card)` does not resolve the contradiction because its required semantics are not defined separately from `close_check`.

**Required correction:** Define a distinct writer-PASS predicate that validates the immutable proof command, newest claim, newest verdict ordering, and the card's writer profile without using the final closer set. Add a test in which a coder PASS permits review while the same coder PASS still cannot permit final completion.

### C-02 — CRITICAL — D2 does not make intake side effects impossible

**Evidence:**

- D2 blocks terminal only when the command matches `VERIFIER_WRITE_RX` (`...taxonomy.md:223`).
- The regex only catches `python -c`, not execution of a script with mutating flags (`__init__.py:578-584`).
- Independent probes show no match for `python restore_buzz_definitions.py --apply`, `echo change 1> file.txt`, or `powershell ... Set-Content`.
- The incident itself used a Python script with `--apply` (`...taxonomy.md:50`).

This is a direct bypass of the proposed enforcement boundary. It contradicts the report's own correct principle that wrong actions must be impossible (`...taxonomy.md:87`). A negative shell blocklist cannot establish that guarantee.

**Required correction:** Use a positive allow-list for intake terminal calls, limited to enumerated read-only commands and Crew proof/watch/show operations. Do not permit arbitrary script interpreters, PowerShell, SSH, shell redirection, or unparsed compound commands. Add positive and negative tests for Windows and POSIX command forms, including the exact historical `python <script> --apply` class.

### C-03 — CRITICAL — Same-card review does not transition task skills or restore the worker model

**Evidence:**

- `_create_guard()` writes the worker card's forced skills once (`__init__.py:1097-1099`).
- The dispatcher passes every persisted task skill to every later run (`oss/hermes-agent/hermes_cli/kanban_db_dispatch.py:2753-2757`); review claims only append `sdlc-review` in memory (`:2115-2119`).
- Proposed T3 expands `repin_for_review()` to `dual`, while T10/T11 only change skill text (`...taxonomy.md:196,203-204`). No task-skill transition is designed.
- `request_changes()` returns the task to the implementer but does not modify `model_override`, `provider_override`, or persisted skills (`oss/hermes-agent/hermes_cli/kanban_db.py:3448-3516`).

Result: the reviewer run force-loads `crew-role-worker`, not `crew-verifier`; after a rejection, the coder can inherit the review model pin. The successful ad-hoc `t_a18f20c9` flow does not validate these proposed Crew transitions because that card was not created through the proposed canonical dual-card guard.

**Required correction:** Specify and test both directions of the transition:

1. writer → review: force-load verifier instructions and apply the review route;
2. reviewer → changes requested: restore worker instructions and the worker route/profile default.

The design must identify the authoritative mutation seam and failure behavior; prose changes alone are insufficient.

### C-04 — CRITICAL — P1 activates live guards before the lifecycle implementation is complete

**Evidence:**

The remediation table orders P0 → **P1 activation** → P2 intake guards → P3 agent/dual lifecycle and skill work (`...taxonomy.md:281-289`). At P1, role processes begin enforcing Crew, but these items remain deferred to P3:

- repinning and verifier handback for `dual` (`crew_card.py:1244,2348,2377`);
- writer-PASS and review-round guards;
- agent audit semantics;
- watcher child traversal;
- worker and verifier instructions.

This creates a live intermediate state in which `agent` and `dual` are accepted and guarded but only partially implemented.

**Required correction:** Build and verify P0, P2, and P3 together in an isolated worktree/runtime fixture. Activation of specialist profiles must be the final deployment phase, followed immediately by parity checks and scratch-board live dry runs. No production specialist profile should be enabled between partial implementation phases.

### H-01 — HIGH — New completion decisions are not integrated with idempotency/reporting

T8 replaces `owner_close` with `guard_bypass` for dispatched closer runs (`...taxonomy.md:201`). However:

- `audit_completion()` considers only `owner_close` and `audit` terminal for an event (`scripts/crew_coordinator.py:897-899`).
- `crew_notify.audit_outcome()` also recognizes only `audit` and `owner_close` (`scripts/crew_notify.py:212-228`).

A standalone `guard_bypass` decision would be re-evaluated on every coordinator pass and would not be a settled watcher/notifier outcome. T7's proposed `review_verdict` has the same problem if it replaces rather than supplements an `audit` event.

**Required correction:** Define one terminal completion-decision taxonomy and update coordinator idempotency, notifier/watcher settlement, graph rendering, and tests together. Prefer an `audit` decision with explicit outcome/subtype over introducing unrelated terminal kinds.

### H-02 — HIGH — Existing two-FAIL stop conflicts with the proposed three-round cap

The proposed `max_review_rounds` default is three (`...taxonomy.md:199,301`), but:

- `roles/roles.json:1-66` has no `max_review_rounds` field;
- the current guard stops `kanban_request_review`/completion after two FAIL verdicts (`__init__.py:1310-1315`);
- `rework_fails()` counts FAIL lines since the last coordinator fix (`scripts/crew_card.py:1987-2009`).

Two reviewer FAIL verdicts can preempt the third review round with a different stop kind than T6 describes.

**Required correction:** Add the configuration field and define one round-counting source of truth. Reconcile or remove the cumulative two-FAIL guard for `dual`, and test the exact boundary: rounds 1–3 allowed as intended, the next transition blocked once with `needs_input`.

### H-03 — HIGH — D1 does not define state for clarification-answer turns

The design stores `_INTAKE[(sid, turn)]` when the slash/expanded skill is detected (`...taxonomy.md:222`), but D2/D3 apply whenever `_is_crew_turn()` is true (`:218`). The existing `_is_crew_turn()` also returns true for any live session window (`__init__.py:1006-1008`), and later owner messages extend that window without being slash/skill invocations (`__init__.py:1462-1465`).

A clarification answer turn therefore has no specified `_INTAKE[(sid, new_turn)]` record, track, read count, or outcome state. A direct lookup fails; lazy creation loses the original `spec` versus `no-spec` track.

**Required correction:** Define session-level intake state plus turn-local counters explicitly, and carry track/brief across clarification and discussion turns. Add a multi-turn test: slash → clarify → answer → bounded reads → two-card or one-card creation → turn close.

### H-04 — HIGH — D8 omits manifest changes and misstates hook sequencing

- `plugin.yaml:19-25` does not declare `transform_llm_output` or `post_llm_call`.
- `plugin_validate.py:416-438` rejects hooks registered but not declared.
- Hermes invokes `transform_llm_output` before `post_llm_call` (`oss/hermes-agent/agent/turn_finalizer.py:453-480`; normal text path also transforms before persistence at `agent/turn_final_response.py:344-360`).

The proposed plan does not name a `plugin.yaml` update or a manifest-parity test. State written in `post_llm_call` cannot drive the earlier transform.

**Required correction:** Declare both hooks, have pre/post-tool hooks maintain all state needed by the transform, use `post_llm_call` only for final logging/cleanup, and add plugin validation plus sequencing tests.

### H-05 — HIGH — D2 breaks Track A before the unresolved authoring decision is made

The current `/crew` skill requires the coordinator to write the exploration and four OpenSpec artifacts during Phases 1–2 (`skills/crew/SKILL.md:40-60`). D2 forbids all writes during intake (`...taxonomy.md:223`). Section 8 correctly marks the replacement behavior as a Commander decision (`:297-301`), but P2 schedules D2 without first resolving and updating the Track A contract.

**Required correction:** Resolve Decision 8.2 before implementation. If Track A authoring becomes a `dual` worker card, update the skill, intake state machine, approval gate, watcher behavior, and tests as one contract. Do not activate a guard that makes the documented workflow impossible.

### H-06 — HIGH — `agent` rejection outcome is underspecified across board, proof, and notification semantics

The proposed `agent` card writes either `Verdict: APPROVED` or `Verdict: REJECTED`, then runs a file-existence proof and calls `kanban_complete` (`...taxonomy.md:178`). A REJECTED report therefore yields proof exit 0 and board status `done`; only the proposed parsed secondary decision distinguishes rejection.

This can be valid if `done` means “the review was delivered,” but the design must state that contract and guarantee that watchers, dashboard tiles, and remediation offers surface REJECTED as a negative outcome rather than a generic green completion.

**Required correction:** Define the user-visible and machine-visible terminal semantics for APPROVED, REJECTED, and MISSING, including watcher text, graph status, notification dedupe, and whether rejection may satisfy a parent dependency. Add end-to-end tests for all three.

## Non-blocking corrections

### M-01 — MEDIUM — D2 cannot cover the 14:16 plain-chat incident

The 14:16 production action began from plain “can you restore this?” (`...taxonomy.md:50`), while D1-D9 explicitly apply only to Crew intake turns (`:218`). Correct the statement that D2 covers that incident. It covers the same action class only when it occurs inside `/crew`; general-chat operational safety requires a separate control.

### M-02 — MEDIUM — Multi-card brief/window semantics are incomplete

D4 delays `_close_window` until turn end to permit two cards (`...taxonomy.md:225`), but `_finish_created_card()` consumes the session brief with `pop()` on the first card (`__init__.py:1163`). The second linked card loses the originating brief. Specify whether both cards inherit the brief and add a test.

### M-03 — MEDIUM — Verifier artifact allow-list is OpenSpec-specific in a no-spec taxonomy

For `dual`, section 5.3 permits `<Lands at>/openspec/**/reviews/` or an optional `Review artifact:` field (`...taxonomy.md:207-214`). `/crew-no-spec` explicitly bypasses OpenSpec (`skills/crew-no-spec/SKILL.md:7-12`), and the canonical dual contract does not require `Review artifact:`. Define a safe non-OpenSpec review-artifact location and use normalized, case-insensitive containment checks on Windows.

### M-04 — MEDIUM — X1-X15 omit the blocking paths

Add tests for:

1. writer PASS versus final closer semantics on `dual`;
2. exact terminal bypasses, including script execution and Windows shells;
3. slash → clarify → answer state carryover;
4. task-skill transition and restoration;
5. review model restoration after `request_changes`;
6. completion-decision idempotency and watcher settlement;
7. two-FAIL versus round-cap interaction;
8. Track A after D2;
9. non-OpenSpec verifier artifact paths and Windows case/path traversal;
10. plugin manifest/register parity;
11. both cards receiving the origin brief;
12. `agent` APPROVED/REJECTED/MISSING end-to-end behavior.

## Confirmed valid findings in the exploration

### I-01 — INFO — Primary root cause and current false attribution are well supported

The live activation/config state, hook source, board events, and reviewer logs independently support sections 2–4. The report correctly warns not to enable the reviewer guard before allowing the named review artifact.

### I-02 — INFO — Single-card `dual` is a defensible direction, not yet a complete design

The kernel review loop demonstrated on `t_a18f20c9` supports the recommendation to prefer one card for implement/review/rework. The Crew layer still needs explicit writer/verifier proof predicates, skill/model transitions, round accounting, and notification semantics before that direction is safe.

## Required revision checklist

1. Replace the `dual` writer gate with an explicitly separate writer-PASS predicate.
2. Replace terminal mutation detection with a positive intake allow-list.
3. Define role skill and model transitions in both review directions.
4. Move specialist-profile activation after all code, skills, manifest, tests, and scratch-board verification.
5. Unify terminal audit decisions across coordinator, watcher, notifier, and graph.
6. Reconcile the two-FAIL and review-round limits; add `max_review_rounds` to the actual config contract.
7. Define session/turn intake state across clarification and discussion turns.
8. Add and declare the two new hooks with ordering-correct behavior.
9. Resolve Track A authoring before D2 is implemented.
10. Define `agent` REJECTED semantics and non-OpenSpec review artifact paths.
11. Expand the test plan with all cases under M-04.
12. Keep the valid activation/root-cause evidence and baseline-test disclosures.

## Review proof and completeness

This review performed no implementation, configuration, service, board-schema, or branch changes. The only repository write is this report. No gateway or dispatcher restart was performed.

The repository has no `agent_share.md`; therefore no Updates Log could be modified without violating the collaboration rule that only a Leader creates the shared dashboard. The Kanban completion metadata must carry the required `agent_share_update_payload` with `dashboard_visibility: pending-sync`.

Card proof command:

```sh
test -s "O:/workspaces/oss/crew/openspec/workspace/reviews/2026-10-14-crew-intake-and-verify-taxonomy-review.md"
```

Expected result after this report is written: exit code `0`.
