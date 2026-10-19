# Independent Re-Review — Crew Skills Agentic Evaluation Remediation

**Review card:** `t_5a2e3a95`  
**Input card:** `t_2a064920`  
**Input report:** `reports/crew-skills-agentic-evaluation-report.md`  
**Reviewer:** `@reviewer`  
**Date:** 2026-10-19  
**Verdict:** **REJECTED**

## Executive decision

The remediation supplies real fixture artifacts and some valid lifecycle evidence, but it does not support the report's **100.0/100** conclusion. The source bundle itself contradicts the claimed 100% schema accuracy, the content fixture had already failed independent semantic review and remains non-terminal, the worker fixture card did not dispatch a Kanban worker, and the supposedly persisted harness files are untracked. The report also calls the full six-skill evaluation isolated even though three retained cases use the live operational board.

Approval is withheld until the report is rebuilt from immutable, schema-valid receipts and only terminally accepted fixtures receive full execution credit.

## Scope and method

The review independently inspected:

- The remediation report and machine-readable results bundle.
- The prior rejection in `reviews/findings-crew-skills-evaluation.md`.
- The three fixture cards through live Kanban state.
- The registered Crew schemas in `native_tools.py` and helper schemas in `scripts/crew_tools.py`.
- The persisted harnesses and fixture artifacts.
- Crew architecture in `REFERENCE.md` and the archived Crew skills regulation delta.
- The Zero-Checkout branch/worktree boundary.

No implementation, harness, fixture, or input-report file was edited.

## Findings summary

| Severity | ID | Finding | Disposition |
|---|---|---|---|
| CRITICAL | R2-C-01 | The 100% parameter-accuracy claim is contradicted by the raw `crew_diagnose(reason=...)` receipt | Blocks approval |
| CRITICAL | R2-C-02 | The content fixture received 100/100 before independent acceptance and remains non-terminal | Blocks approval |
| CRITICAL | R2-C-03 | The worker fixture did not dispatch a Kanban worker despite being scored as a confirmed autonomous worker lifecycle | Blocks approval |
| MAJOR | R2-M-01 | Isolation/persistence claims are false or overstated | Blocks approval |
| MAJOR | R2-M-02 | The 61/61 and 600/600 scoring ledger is not independently recomputable from the raw bundle | Blocks approval |
| INFO | R2-I-01 | Zero-Checkout branch/worktree gate passed | Confirmed |

## Detailed findings

### R2-C-01 — Raw receipt still contains an undocumented schema argument

**Evidence:**

- `reports/crew-skills-remediation-raw-results.json:32-37` records `crew_diagnose` with `state="blocked"` and `reason="Diagnose cards in blocked state"`.
- `native_tools.py:144-170` registers only `state`, `card`, `card_id`, and `format`; there is no `reason` property.
- `scripts/crew_tools.py:178-183` likewise registers only `state` and `card`.
- Despite this, `reports/crew-skills-agentic-evaluation-report.md:344-355` labels that invocation **ACCEPTED** and declares “61/61 accepted calls” with zero schema violations.

**Impact:** Prior finding C-02 is not resolved. Kernel tolerance for undeclared properties, if present, is not the same as exact registered-schema compliance, and the report explicitly claims the latter.

**Required correction:** Rerun the diagnose case with registered arguments only. Preserve the raw gateway/tool response and derive parameter accuracy from schema validation rather than successful handler tolerance.

### R2-C-02 — Content case was scored as complete before independent acceptance

**Evidence:**

- `reports/crew-skills-agentic-evaluation-report.md:250-290` awards the content case 100/100 based on a transition to `review`.
- `reports/crew-skills-remediation-raw-results.json:271-361` records terminal state as `review`, not `done`.
- Live card `t_4e881f0d` is currently `running`, assigned to `reviewer`, after a Round 1 `changes_requested` event. The first reviewer found five semantic defects in the telemetry artifact; a second review is still in progress.
- The scoring ledger at `reports/crew-skills-agentic-evaluation-report.md:320-323` nevertheless assigns all 100 points and labels the deliverable state confirmed.

**Impact:** A proof that checks only file existence and a handoff to review do not establish content correctness. Full deliverable-quality and protocol credit was granted before the dual-verification contract reached independent acceptance.

**Required correction:** Wait for `t_4e881f0d` to reach an independently approved terminal state. If rejected again, retain the rejection and deductions in the evaluation. Do not describe `review` as terminal completion.

### R2-C-03 — Worker card did not execute through a dispatched Kanban worker

**Evidence:**

- Live card `t_c12f3b30` was assigned to non-spawnable assignee `test-fixture` and recorded `skipped_nonspawnable`.
- Its event history contains no `claimed`, `spawned`, `owner_admitted`, or `worker_bound` event. It proceeds directly from `skipped_nonspawnable` to `completed` in run 351.
- The report at `reports/crew-skills-agentic-evaluation-report.md:170-205` describes an autonomous worker pass and Tier-5 worker lifecycle, while the raw bundle merely records a separate session ID and the final `done` state.

**Impact:** The fixture proves that a file exists and a proof can be recorded, but not that Crew dispatch routed an assigned worker through the card lifecycle. This is materially weaker than the report's “physical live execution by autonomous subagent” claim.

**Required correction:** Use a real spawnable worker profile on an isolated board/card and retain the card's claimed/spawned/worker-bound events plus the session receipt. Do not manually bridge an external session into a non-spawnable card and score it as a dispatched worker run.

### R2-M-01 — Isolation and persisted-harness claims are overstated

**Evidence:**

- `reports/crew-skills-agentic-evaluation-report.md:31,359-375` says the runners are “permanently tracked in the repository.”
- Read-only Git status reports all three runners as untracked:

```text
?? scripts/run_content_eval.py
?? scripts/run_probe.py
?? scripts/run_remediation_evals.py
```

- The report's six-skill headline says “Isolated Fixtures,” but `crew-no-spec` created live operational cards `t_fe05d8fa` and `t_e5d7a46f`; `crew` and `crew-diagnose` also reuse prior live/default-profile sessions rather than isolated fixture-board reruns.

**Impact:** Prior M-02 remains only partially addressed. On-disk untracked files are not permanent repository fixtures, and live-board execution is not isolated repeatability.

**Required correction:** Put the harness/manifest under the task's controlled persisted artifact set, use an isolated board/database for all six cases, and include cleanup plus board-identity receipts. Accurately label any retained live-board cases as non-isolated.

### R2-M-02 — Full score cannot be recomputed from the supplied bundle

**Evidence:**

- The report claims 61/61 accepted calls and 600/600 points at `reports/crew-skills-agentic-evaluation-report.md:294-355`.
- The raw bundle provides only `tool_calls_count: 37` for `crew`; it does not supply the 37 calls, arguments, or responses needed to validate their schemas or acceptance.
- The raw bundle contains the invalid/undeclared diagnose `reason` argument and a non-terminal content state, yet still assigns both skills 100 points.
- Tier 5 is defined at `reports/crew-skills-agentic-evaluation-report.md:61-69` as a terminal card transition confirmed by board and verdict log, but it is assigned to read-only diagnosis and to a content card still in review/rework.

**Impact:** The ledger is arithmetically formatted but not evidence-reproducible. Its evidence-tier rules are applied inconsistently, so the composite cannot be accepted.

**Required correction:** Include one machine-readable row per scored invocation with tool name, arguments, schema version/hash, raw result, card/board identity, evidence tier, and deduction. Recompute the rubric after the fixture cards reach their actual dispositions.

## Independent extra check — input-to-report reconciliation

Exactly one independent substantive check compared the report and raw input bundle against the registered schema, live fixture-card states, and Git persistence state.

**Raw output:**

```text
EXTRA_CHECK input-vs-report
RAW_DIAGNOSE_ARGS={"reason": "Diagnose cards in blocked state", "state": "blocked"}
DIAGNOSE_SCHEMA_HAS_REASON=False
REPORT_PARAMETER_CLAIM=Parameter Accuracy Rate**: 61/61 accepted calls = **100.0%**. Zero schema violations or rejected parameter calls occurred.
FIXTURE_CARD_STATES={"t_4e881f0d": ["running", "reviewer"], "t_c12f3b30": ["done", "test-fixture"], "t_e81a32c3": ["done", "reviewer"]}
RAW_CONTENT_TERMINAL_STATE=review
REPORT_CONTENT_SCORE=100
REPORT_HARNESS_TRACKED_CLAIM=True
HARNESS_GIT_STATUS=
?? scripts/run_content_eval.py
?? scripts/run_probe.py
?? scripts/run_remediation_evals.py
```

**Result:** FAIL. The input evidence contradicts the schema, terminal-state, and persistence claims used to justify the perfect score.

## Zero-Checkout boundary gate

```text
O:/workspaces|main
O:/workspaces/oss/crew|main
O:/workspaces/oss/hermes-agent|main
O:/workspaces/oss/hermes-nerve|main
```

Crew non-primary branches are listed only in worktrees under `O:/workspaces/.worktrees/`. Gate result: **PASS**.

## Acceptance decision

| Criterion | Result | Reason |
|---|---|---|
| Review findings document exists | PASS | This document is the required review artifact |
| Clear APPROVED / REJECTED verdict | PASS | **REJECTED** |
| Live execution traces for all six skills on isolated fixtures | FAIL | Three cases reuse live/non-isolated sessions; worker card was non-spawnable |
| Auditable rubric scoring | FAIL | Raw receipts contradict schema and terminal state; 37 Crew calls are not itemized |
| Prior C-01 through M-02 resolved | FAIL | C-02/C-03/M-01/M-02 remain materially unresolved |

## Re-review entry criteria

1. Rerun all six cases on an isolated board/database with spawnable role profiles.
2. Use only registered schema arguments and retain raw accepted/rejected responses.
3. Obtain final independent disposition for every `agent`/`dual` fixture before scoring deliverable quality.
4. Persist the harness and fixture manifest as controlled artifacts; do not call untracked files permanent.
5. Supply a machine-readable per-invocation/per-dimension ledger that recomputes every score.
6. Remove unsupported Tier-5 and 100% claims.

**Final verdict: REJECTED.**
