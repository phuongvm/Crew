# Independent Review — Crew 0.10.2 Remediation and Skill Evaluation

- **Review card:** `t_448f679c`
- **Implementation card:** `t_5059c6ba`
- **Inspected commits:** `890ace916c47f7d31d7328a0403f52fd7df7a6a9`, `dde2f781be8d2afa3072567f574fbef5aedebafa`
- **Fixed point:** `be364d5e4a2def472214354c02a6cbbc367e3cad`
- **Verdict:** **REJECTED**

## Decision

The two narrow regression fixes are correct and the designated 127-test proof suite passes independently. The overall card is rejected because the required isolated live evaluation did not remain isolated, the report records a timed-out role run as a behavioral pass, the literal “all Crew unit tests pass 100%” criterion is not met, and the committed report violates the repository’s prohibition on machine-specific paths in documentation.

## Proof gate

Command run independently from `O:/workspaces/oss/crew`:

```text
python -m unittest tests/test_crew_versions.py tests/test_crew_tools_guard.py tests/test_extended_tools.py tests/test_native_tools.py tests/test_role_contracts.py
```

Raw result:

```text
.....................crew: native tools not registered: boom
..........................................................................................................
----------------------------------------------------------------------
Ran 127 tests in 5.494s

OK

PROOF_EXIT=0
```

The mechanical proof gate passes. This does not override failed acceptance or standards checks.

## Standards axis

### [High] `reports/crew-skills-agentic-evaluation-report.md:433-434,461` — machine-specific paths are committed in documentation

`CONTRIBUTING.md:50-53` says: “Never put machine-specific strings (usernames, hostnames, home paths) in code, tests or docs.” The new section commits paths rooted at `O:/workspaces/_config/agent4070/...` and `O:/workspaces/_config/agent4070/hermes/state.db`.

**Required correction:** replace these with portable placeholders such as `<card-workspace>/`, `$HERMES_HOME/state.db`, or artifact attachment names while retaining enough information to reproduce the audit.

### [Low / advisory] `tests/test_crew_tools_guard.py:54,68` — stale test names

The fixture now enumerates 18 tools, including `crew_observe`, while test names still say `adds_the_six_tools` and `declares_the_six`. This is a Fowler **Mysterious Name** smell: names no longer describe the assertions.

**Required correction:** rename the tests to describe the complete Crew tool set. This item alone would not block approval.

### Standards positives

- `skills/crew-no-spec/SKILL.md:4` now matches plugin version `0.10.2`.
- `tests/test_crew_tools_guard.py:26-32` now includes `crew_observe` in the expected registered tool set.
- `git diff --check be364d5..dde2f78` passed.
- The change set is confined to the two regression files and the requested evaluation report.

## Spec-fidelity axis

### [High] `reports/crew-skills-agentic-evaluation-report.md:449-460,478-485` — the required isolated evaluation was not isolated

The implementation card requires “isolated live execution traces.” The report itself establishes that gateway sessions dropped the `HERMES_*` board pins, five of six runs were not isolation-clean, `crew-diagnose` read the live board instead of its seeded blocked fixture, and `/crew-no-spec` created live-board card `t_cbe1a2fe`.

This is not merely an advisory harness observation: it means the evaluation did not exercise the intended isolated board topology and caused an out-of-scope live-board mutation.

**Required correction:** rerun the six-skill evaluation in a gateway-visible, dedicated evaluation profile/board; demonstrate that all native Kanban/Crew calls resolve only to that board; confirm no live-board card is created; replace Section 9 evidence with the clean receipts.

### [High] `reports/crew-skills-agentic-evaluation-report.md:470,476-485` — a timed-out run receives a PASS classification

The raw bundle records:

```text
RAW crew-role-content: rc=timeout duration_s=540.0 ... board=review
```

The report discloses the timeout but still assigns `PASS w/ finding`. A harness timeout is not a clean completed execution. The card’s request was to execute live skill evaluations, not only observe a partial terminal transition.

**Required correction:** rerun `crew-role-content` to process exit code 0, retain proof and review-handoff evidence, and score the run from the completed receipt.

### [Medium] Implementation card Done-when is not literally satisfied

`t_5059c6ba` states: “All Crew unit tests pass 100% with exit code 0.” Section 9.1 records the 1,100-test suite with 13 failures and 9 errors. Baseline comparison may show that these are pre-existing and unrelated to the two patches, but it does not make the written all-tests criterion true. The designated proof command only covers 127 tests.

**Required correction:** either make the full suite green, or have the coordinator explicitly rescope the acceptance criterion to the designated focused suite plus documented baseline exceptions before re-review. Do not claim literal 100% full-suite passage while 22 cases remain non-green.

### [Medium] Report provenance is incomplete for three sessions

The attached `eval_results.json` has `session_id: null` and empty `tool_calls` for `crew`, `crew-diagnose`, and `crew-no-spec`. The report supplies session IDs and call counts from `state.db`, and those sessions exist, but it does not document the reconciliation/backfill method in the persisted bundle.

**Required correction:** make the harness persist the resolved session IDs/tool traces directly, or add a machine-readable reconciliation manifest that maps each prompt/time window to its `state.db` session and explains the attribution.

### Spec positives

- The version-drift and missing-tool regression changes are correct.
- The 127-test designated proof passes with exit code 0.
- The report candidly discloses ISO-1, invalid `reason` arguments, the stray live card, the timeout, and full-suite failures instead of concealing them.
- Worker, verifier, and content fixture artifacts reached the reported scratch-board states; this is useful diagnostic evidence, but it is insufficient for approval because the required isolation failed.

## Exactly one extra substantive check

The attached raw bundle was reconciled against the report and `state.db`:

```text
EXTRA_CHECK=report_receipt_reconciliation
RAW_BUNDLE_SHA256=d8da04bce0cdb44d558e2ffb48507594d84458777b64a92e45f316628136cfea
RAW crew: rc=0 duration_s=62.6 session_id=None board=None new_cards=0
RAW crew-diagnose: rc=0 duration_s=85.6 session_id=None board=blocked new_cards=0
RAW crew-no-spec: rc=0 duration_s=95.2 session_id=None board=None new_cards=0
RAW crew-role-content: rc=timeout duration_s=540.0 session_id=local-b16758dc57685f38d17ef8d458e3902d1a016b0c9fff4f1e972be7b2dbbbbc7f board=review new_cards=0
RAW crew-role-worker: rc=0 duration_s=444.7 session_id=local-ebefb00b02140a05a51b35175c9efdef54f183487c3741dc94c5433edfe0ba9a board=done new_cards=0
RAW crew-verifier: rc=0 duration_s=480.1 session_id=local-0ff562a5ba11239c5686250af55be4ff280e558688864d20ec310fb76f32030a board=done new_cards=0
STATE crew: session_exists=True messages=2
STATE crew-diagnose: session_exists=True messages=6
STATE crew-no-spec: session_exists=True messages=11
REPORT admits_isolation_failure=True
REPORT admits_live_card=True
REPORT absolute_O_paths=2
REPORT content_timeout_disclosed=True
```

## Zero-Checkout gate

All protected production checkouts remained on `main`; branch worktrees, where present, are under `O:/workspaces/.worktrees/`:

```text
O:/workspaces -> main
O:/workspaces/oss/crew -> main
O:/workspaces/oss/hermes-agent -> main
O:/workspaces/oss/hermes-nerve -> main
```

## Required re-review evidence

1. A clean isolated-board six-skill evaluation with no live-board access or mutation.
2. `crew-role-content` run exits 0 rather than timing out.
3. Persisted machine-readable session/tool-call attribution for all six runs.
4. Portable documentation paths.
5. Coordinator resolution of the “all tests” criterion versus the focused 127-test proof command.
