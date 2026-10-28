# Independent Re-review — Crew Skills Remediation

- **Review card:** `t_2fd518a0`
- **Remediation card:** `t_599cf79c`
- **Prior rejected review:** `t_448f679c`
- **Inspected range:** `dde2f781be8d2afa3072567f574fbef5aedebafa..5f85e9e06be29514d7a763779fa01ae2bc4cefbe`
- **Remediation commits:** `b2d22e35cc789a18b4eef97752c478f680450718`, `5f85e9e06be29514d7a763779fa01ae2bc4cefbe`
- **Verdict:** **APPROVED**

## Decision

All five required re-review gates from `reviews/findings-crew-skills-remediation-final.md:131-137` are now satisfied. The focused 127-test acceptance suite passes independently, all six replacement evaluations terminate with exit code 0 on a dedicated `crew-eval` board, the content run no longer times out, provenance is persisted for all six runs, live boards remain unchanged, and documentation is portable. The remediation diff is limited to the evaluation report and the stale test names.

No blocking Standards or Spec-fidelity findings remain.

## Proof gate

Independent acceptance command from `O:/workspaces/oss/crew`:

```text
python -m unittest tests/test_crew_versions.py tests/test_crew_tools_guard.py tests/test_extended_tools.py tests/test_native_tools.py tests/test_role_contracts.py
```

Raw result:

```text
.....................crew: native tools not registered: boom
..........................................................................................................
----------------------------------------------------------------------
Ran 127 tests in 5.211s

OK
FOCUSED_PROOF_EXIT=0
```

## Standards axis

**Result: PASS — 0 blocking findings.**

- `CONTRIBUTING.md:53` portability rule is satisfied. The current report and portable receipt contain no `O:/`, `agent4070`, or `ptdev` strings; repository-local and environment placeholders are used instead.
- `tests/test_crew_tools_guard.py:54,68` now name the full Crew tool catalog rather than the obsolete “six tools,” resolving the prior Mysterious Name advisory.
- The diff is surgical: `git diff --name-status dde2f78..HEAD` reports only:

```text
M reports/crew-skills-agentic-evaluation-report.md
M tests/test_crew_tools_guard.py
```

- `git diff --check dde2f78..HEAD` exits 0.
- No actionable Fowler smell was found in the small test rename/report remediation.

## Spec-fidelity axis

**Result: PASS — 5/5 required re-review gates satisfied.**

1. **Clean isolated-board six-skill evaluation — PASS.** Report §9.2 and the v2 receipt show in-process `run_oneshot` under a dedicated `evalhome`/`crew-eval` board. The receipt records `live_boards_unchanged: true`, 0 new live tasks, 0 eval-attributable live events, and 0 eval session IDs in live state stores.
2. **`crew-role-content` exits 0 — PASS.** Report §9.3 records rc=0 in 137.2 seconds, a PASS proof, and transition to `review`; the former 540-second timeout is gone.
3. **Persisted machine-readable attribution for all six runs — PASS.** `eval_results_v2.json` contains six `attribution_manifest` entries and exact usage-file session IDs. Each tool-using run persists tool traces; the `/crew` clarification run correctly has zero tool calls.
4. **Portable documentation — PASS.** Report paths use `<workspace>`, `<crew-repo>`, `<card-workspace>`, and `$HERMES_HOME`; `eval_results_v2.portable.json` is attached with sha256 `4556c78de9e89463c59bd60b364a615fe11a6e99961a510b1b68cb170f830093`.
5. **All-tests criterion resolved — PASS.** The remediation card explicitly scopes acceptance to the focused 127-test suite. Report §9.1 states that the full 1,100-test suite still has 13 failures and 9 errors, attributes them to pre-existing environment-bound modules, and explicitly says it does not claim the full suite passes. This is transparent rescoping, not a false 100% claim.

## Exactly one extra substantive check

The v2 raw and portable receipts were reconciled directly against the five rejection gates:

```text
EXTRA_CHECK=v2_receipt_contract_reconciliation
RAW_SHA256=99d3c0bbaa45becac781e47cc7eafc4143a0144b309a4d485714b2a1fce77743
PORTABLE_SHA256=4556c78de9e89463c59bd60b364a615fe11a6e99961a510b1b68cb170f830093
RUN crew: rc=0 session=20261027_221117_4d2748 tool_calls=0
RUN crew-diagnose: rc=0 session=20261027_221111_78a9d2 tool_calls=4
RUN crew-no-spec: rc=0 session=20261027_221114_46be55 tool_calls=20
RUN crew-role-content: rc=0 session=20261027_221126_5b4bf9 tool_calls=22
RUN crew-role-worker: rc=0 session=20261027_221121_712a43 tool_calls=18
RUN crew-verifier: rc=0 session=20261027_221124_111218 tool_calls=20
ATTRIBUTION_MANIFEST=6/6
LIVE_BOARDS_UNCHANGED=true
PORTABILITY_FORBIDDEN_MATCHES=0
FULL_SUITE_SCOPE_DISCLOSED=true
```

The reconciliation command exited 0.

## Zero-Checkout gate

All protected production checkouts remain on `main`:

```text
O:/workspaces -> main
O:/workspaces/oss/crew -> main
O:/workspaces/oss/hermes-agent -> main
O:/workspaces/oss/hermes-nerve -> main
```

Every non-primary Crew branch listed by `git worktree list` resides under `O:/workspaces/.worktrees/`.

## Non-blocking follow-ups

The report correctly preserves these as advisories rather than concealing them:

- **P-01:** five tool-using sessions initially supplied an unregistered `reason` argument, were refused, and recovered on retry.
- **P-02:** the content session redundantly attempted `kanban_request_review` after successful `crew_review_handoff`; the second transition was refused.
- **BOOT-1:** owner-root discovery under borrowed `HERMES_HOME` remains an upstream Hermes issue.
- The v1 fixture-only live card `t_cbe1a2fe` remains a coordinator archive decision; the accepted v2 evaluation created no live card.

These do not invalidate the specified remediation acceptance gates.
