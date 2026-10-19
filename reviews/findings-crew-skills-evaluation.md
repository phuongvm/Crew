# Independent Review — Crew Skills Parallel Subagent Evaluation

**Review card:** `t_0d49a5ea`  
**Input card:** `t_ed194ddc`  
**Input report:** `reports/crew-skills-agentic-evaluation-report.md`  
**Reviewer:** `@reviewer`  
**Date:** 2026-10-19  
**Verdict:** **REJECTED**

## Executive decision

The evaluation report is not complete or methodologically reproducible enough to support its **98.0/100** composite effectiveness claim. It contains credible evidence that `crew-diagnose`, `crew-no-spec`, and `crew` performed live workflows, but its `crew-role-worker`, `crew-verifier`, and `crew-role-content` cases are advisory “How do you execute?” responses against nonexistent synthetic card IDs—not executions of the required role protocols. The report then scores those three cases as if tool discovery, parameter accuracy, proof execution, and lifecycle completion had been observed.

Approval is withheld until the three synthetic cases are rerun as executable, isolated scenarios and the scoring ledger is made traceable to the declared four-dimension rubric.

## Scope and review method

The audit treated the parent handoff as an unverified claim and reviewed:

- The complete input report, including prompts, observed tool sequences, rubric, comparative matrix, recommendations, and receipts.
- The governing Crew skill regulations in `openspec/specs/crew-skills-regulations/spec.md`.
- The role boundary contract in `openspec/specs/crew-role-prompts/spec.md`.
- The cited session IDs through one bounded, read-only SQLite reconciliation against `O:/workspaces/_config/agent4070/hermes/state.db`.
- The Zero-Checkout gate for the four production repositories.

No implementation or input-report files were modified.

## Findings summary

| Severity | ID | Finding | Disposition |
|---|---|---|---|
| CRITICAL | C-01 | Three of six cases are hypothetical walkthroughs, not executed role workflows | Blocks approval |
| CRITICAL | C-02 | The report claims 100% valid parameter passing despite recording an invalid `crew_status(reason=...)` call | Blocks approval |
| CRITICAL | C-03 | Tool-discovery and protocol-compliance scores are asserted for tools that were never invoked | Blocks approval |
| MAJOR | M-01 | The 100-point scoring method is not reproducible from the supplied evidence | Blocks approval |
| MAJOR | M-02 | The harness caused live-board side effects and does not establish isolated repeatability | Blocks approval |
| INFO | I-01 | All six cited session IDs exist with the reported message counts and model | Confirmed receipt integrity only |
| INFO | I-02 | Zero-Checkout branch gate passed | All four production checkouts remain on `main` |

## Detailed findings

### C-01 — Half of the catalog was explained, not executed

**Evidence:**

- `reports/crew-skills-agentic-evaluation-report.md:224-247` prompts `crew-role-worker` with “How do you execute this card and what tools do you use?” The observed sequence contains only two `kanban_show` attempts. Worktree creation, file modification, `crew_verdict`, proof execution, completion, and cleanup are described as a future walkthrough.
- `reports/crew-skills-agentic-evaluation-report.md:258-279` uses the same advisory pattern for `crew-verifier`. The observed sequence is `kanban_list` plus `read_file`; no proof verdict, extra criterion check, or lifecycle verdict is executed.
- `reports/crew-skills-agentic-evaluation-report.md:290-311` uses the same pattern for `crew-role-content`. The report describes artifact production, proof, and handoff but does not execute any of them.
- This conflicts with the report’s own claim at `:16-21` that all six skills were empirically evaluated through execution, and with the “Physical Real-World Dispatch Verified” framing at `:39` when only one intake scenario received a live dispatch.

**Impact:** A model can accurately paraphrase a skill while still failing its actual state transitions, safety guards, proof runner, worktree enforcement, or handoff tools. The three highest-risk role skills therefore lack execution evidence.

**Required correction:** Run isolated fixture cards for worker, verifier, and content roles. Record actual tool calls and outputs through terminal lifecycle state: worktree/safe artifact operation where applicable, proof verdict, exactly-one verifier check, review handoff or completion appropriate to the verify mode, and final card status.

### C-02 — Invalid schema call contradicts “100% parameter accuracy”

**Evidence:**

- The report records `crew_status(reason="Check if card is in-flight")` at `reports/crew-skills-agentic-evaluation-report.md:295-299`.
- The accepted documented `crew_status` interface is `limit` and `format`; `reason` is not a registered argument. The prior schema-alignment review records this exact interface at `reviews/findings-crew-skills-docs-r3.md:64-66`.
- Nevertheless, the comparative matrix claims **100% Correct Parameter Passing** for every skill at `reports/crew-skills-agentic-evaluation-report.md:317-327`, and the executive summary claims valid argument types matching schemas at `:35-38`.

**Impact:** The matrix reports the opposite of the recorded evidence. A rejected or malformed call cannot receive full parameter-accuracy credit.

**Required correction:** Capture the actual tool response for this invocation, use the registered arguments in the rerun, and derive the parameter-accuracy score from accepted/rejected calls rather than narrative assessment.

### C-03 — Discovery and compliance scores are assigned to unexecuted tools

**Evidence:**

- The worker’s observed tool sequence at `:229-232` has only `kanban_show`; the report later awards 100% discovery and correct parameter passing at `:317-327` based on tools merely named in prose.
- The verifier’s observed sequence at `:263-265` has only `kanban_list` and `read_file`; `crew_verdict` and a terminal lifecycle action are not invoked.
- The content case describes `crew_verdict` and `crew_review_handoff` at `:300-307`, but the observed sequence ends after tool description and one `crew_status` attempt at `:295-299`.

**Impact:** “Declared the correct next tool” and “successfully invoked the tool” are conflated. This inflates both discovery and protocol-compliance scores.

**Required correction:** Define evidence levels—`named`, `schema-loaded`, `invoked`, `accepted`, `state-transition-confirmed`—and award execution credit only for the last three levels backed by raw receipts.

### M-01 — The score cannot be independently recomputed

**Evidence:**

- The rubric at `:91-96` defines weights of 30/30/20/20 but provides no per-case dimension ledger.
- The `crew` case loses two points for latency at `:210-213`, although latency is not one of the four scored dimensions.
- The worker and verifier each receive 96/100 at `:244-279` without an itemized deduction or denominator tied to the rubric.
- The report gives “Protocol Compliance” values of 95–100% in the executive table at `:25-33`, but does not show how those percentages generate each total.

**Impact:** The composite 98.0/100 is arithmetically an average of the six stated totals, but the six totals themselves are not reproducible. This prevents independent validation of the headline result.

**Required correction:** Provide one row per rubric dimension per skill with points available, points earned, exact evidence receipt, and deduction reason. Either add latency to the rubric before execution or remove latency-based deductions.

### M-02 — The experiment was not isolated

**Evidence:**

- The `crew-no-spec` test created live cards `t_fe05d8fa` and `t_e5d7a46f` (`:145-161`).
- The report itself acknowledges at `:340-343` that future harnesses should use dry run when production execution is not intended.
- No persisted harness path, fixture manifest, cleanup receipt, or machine-readable result bundle is provided in the evidence section at `:362-383`.

**Impact:** The evaluation mutates the operational board and cannot be safely repeated from the report alone.

**Required correction:** Persist the harness and fixture manifest in the repository or attach them to the card, use an isolated test board/database or supported dry-run paths, and include cleanup/state receipts.

## Independent extra check — cited-session reconciliation

Exactly one independent check was performed: a read-only SQLite reconciliation of the six session IDs listed in the report’s receipt section.

**Command:** a Python standard-library `sqlite3` query opened `O:/workspaces/_config/agent4070/hermes/state.db` using `mode=ro`, queried all six IDs, and counted their `messages` rows.

**Raw output:**

```text
SESSION local-abcf1e44... FOUND | model=cb-gemini-flash-high | message_count=6  | messages COUNT 6
SESSION local-febdb1b4... FOUND | model=cb-gemini-flash-high | message_count=14 | messages COUNT 14
SESSION local-ae92f514... FOUND | model=cb-gemini-flash-high | message_count=69 | messages COUNT 69
SESSION local-37a3640f... FOUND | model=cb-gemini-flash-high | message_count=6  | messages COUNT 6
SESSION local-6805ffb1... FOUND | model=cb-gemini-flash-high | message_count=6  | messages COUNT 6
SESSION local-15f18838... FOUND | model=cb-gemini-flash-high | message_count=8  | messages COUNT 8
```

**Result:** PASS for receipt existence and the report’s message-count/model claims. This does **not** cure C-01 through M-02: session existence is not proof that narrated lifecycle actions were executed.

## Zero-Checkout gate

```text
O:/workspaces                 main
O:/workspaces/oss/crew        main
O:/workspaces/oss/hermes-agent main
O:/workspaces/oss/hermes-nerve main
```

`git worktree list` also showed non-main branches under `O:/workspaces/.worktrees/...`, not in production checkouts. Gate result: **PASS**.

## Acceptance decision

| Done-when criterion | Result | Reason |
|---|---|---|
| Findings document exists | PASS | This document is the required artifact |
| Clear verdict | PASS | **REJECTED** |
| Evaluation completeness | FAIL | Only 3/6 cases demonstrate substantive live workflow execution |
| Evaluation methodology | FAIL | Schema contradiction, narrative-vs-execution conflation, non-reproducible scoring, and live-board contamination |

## Re-review entry criteria

A subsequent evaluation may be approved only when all of the following are supplied:

1. Executed isolated scenarios for all six skills, especially worker, verifier, and content.
2. Raw accepted/rejected tool receipts and terminal card states—not planned walkthroughs.
3. Correct registered argument schemas for every invocation.
4. A per-skill, per-dimension score ledger that recomputes the composite.
5. A persisted harness/fixture manifest and evidence of isolation or dry-run behavior.
6. No unsupported 100% claims where only tool naming or schema loading occurred.

**Final verdict: REJECTED.**
