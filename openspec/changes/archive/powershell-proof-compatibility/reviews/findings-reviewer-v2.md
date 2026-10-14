# Independent Re-Review Findings v2 — PowerShell Proof Compatibility

## Verdict

**APPROVED**

All three CRITICAL findings and the W-01 reproducibility warning from Reviewer v1 are resolved on candidate `0542d11f797716edd581820bb2fd14c0de04c8af`. Independent round-2 execution verified the scanner fixes, real Windows shell routing, seven installed runtime copies, the declared Windows test runner, strict OpenSpec validation, and the corrected parent proof command. No blocking regressions were found.

## Review Target

- Repository: `O:/workspaces/oss/crew`
- Candidate commit: `0542d11f797716edd581820bb2fd14c0de04c8af`
- Reviewed parent: `14bf312776f067ae433ae1298074ef4c28e6488f`
- Review round: 2 (execution, negative cases, runtime parity, and prior-finding closure)
- Implementation diff: `scripts/crew_safety.py`, `tests/test_crew_safety.py`
- OpenSpec evidence artifact: `openspec/changes/powershell-proof-compatibility/tasks.md`

## Context and Scope Audit

Reviewed:

- Reviewer v1 findings
- Active proposal, design, tasks, and `specs/proof-safety/spec.md`
- Full changed source and test files
- Crew architecture in `REFERENCE.md`
- Windows execution contract in `WINDOWS.md`
- Security boundary in `SECURITY.md`
- Collaboration dashboard and available review/lessons authorities

The specifically named `code-review-mandate/spec.md` and project `lessons-learned.md` do not exist in this repository or the rules tree. The available authorities `rules/skills/code-review.md`, `rules/skills/code-review-expert.md`, `rules/shared/lessons-digest.md`, and `rules/guides/templates/lessons-learned.md` were loaded instead. This absence did not prevent independent code and execution verification.

Scope evidence:

- `git diff --name-status 14bf312..0542d11` lists only:
  - `M scripts/crew_safety.py`
  - `M tests/test_crew_safety.py`
- `git diff --check 14bf312..0542d11` exited `0`.
- `git merge-base --is-ancestor 14bf312 0542d11` exited `0`.
- Exact inspected commit: `0542d11f797716edd581820bb2fd14c0de04c8af`.
- No checkout/switch, implementation edit, configuration mutation, service restart, commit, or push was performed by Reviewer.

## Findings Summary

| Severity | Count | Result |
|---|---:|---|
| CRITICAL | 0 | All v1 criticals resolved |
| WARNING | 0 | W-01 resolved |
| INFO | 2 | Non-blocking state disclosures |

## Prior-Finding Closure

### C-01 — Runtime profile copies were not deployed

**Status: RESOLVED**

Evidence:

- Source SHA-256: `961780666c32d570d40a262386fbc6833776e0f733b2a248e3f2707c61cf9a4c`.
- Seven installed copies were discovered and independently loaded:
  - default
  - coder
  - designer
  - leader
  - qa
  - researcher
  - reviewer
- Every installed copy has the same SHA-256 as source.
- Every imported installed copy returns:
  - `detect_bare_powershell('echo "$(Get-Date)"') == 'Get-Date'`
  - `detect_bare_powershell('echo ok # ; Get-Date') == ''`
- Runtime parity probe result: `copy_count=7`, `PARITY_EXIT=0`.

The full installer check still exits `1`, but its only reported change is unrelated configuration drift: `config set crew.roles_path`. It reports no plugin/runtime file drift. Therefore this does not invalidate C-01 runtime deployment closure.

### C-02 — Executable cmdlets inside double-quoted command substitutions were missed

**Status: RESOLVED**

Code and tests:

- `scripts/crew_safety.py:329-352` creates/restores nested command-substitution contexts independently of surrounding double quotes.
- `tests/test_crew_safety.py:453-471` covers double-quoted substitutions, nesting, multiple substitutions, grouping, comments inside substitution, and literal exclusions.
- `tests/test_crew_safety.py:561-566` executes real PowerShell substitutions and verifies output and exit propagation.

Independent direct probes:

- `echo "$(Get-Date)"` → `Get-Date` detected.
- Nested `echo "$(echo "$(Get-Date)")"` → `Get-Date` detected.
- Single-quoted and escaped substitutions → no cmdlet detected.
- Real runtime `echo "$(Get-Date -Format yyyy)"` → rc `0`, output `2026`, no block.
- Edge probe exit: `EDGE_EXIT=0`.

### C-03 — Shell comments were parsed as executable commands

**Status: RESOLVED**

Code and tests:

- `scripts/crew_safety.py:339-343` skips an unquoted word-initial `#` through newline and resumes scanning after the newline.
- `tests/test_crew_safety.py:473-487` covers inline comments, comment-only lines, quoted/escaped/embedded `#`, and real commands after newline.
- `tests/test_crew_safety.py:568-578` executes POSIX comment and literal-substitution cases through real Git Bash.

Independent direct probes:

- `echo ok # ; Get-Date` → no PowerShell cmdlet detected.
- `echo ok # ignored\nGet-Date` → `Get-Date` detected after newline.
- Quoted, escaped, and embedded `#` cases preserve executable text correctly.
- Real runtime `printf ok # ; Get-Date` stayed in Bash and returned `(rc=0, output='ok', blocked='')`.
- Edge probe exit: `EDGE_EXIT=0`.

### W-01 — Literal OpenSpec test command was not reproducible

**Status: RESOLVED**

- `tasks.md:12-14` now binds Task 2.2 to the installed Hermes venv interpreter in the isolated worktree.
- Exact command executed independently:
  - `"O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe" -m pytest tests/test_crew_safety.py -q`
  - Result: `43 passed, 27 subtests passed in 15.17s`
  - Exit: `0`
- Combined focused command:
  - `"O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe" -m pytest tests/test_crew_safety.py tests/test_crew_safety_resolution.py -q`
  - Result: `50 passed, 27 subtests passed in 15.73s`
  - Exit: `0`

## Exact Feature and Contract Proofs

All independently executed with exit code `0`:

1. Task 1.1 preflight proof → `PASS 1.1`.
2. Task 1.2 real Windows PowerShell routing proof → `PASS 1.2`.
3. Task 2.1 test-presence proof → `PASS 2.1`.
4. `openspec status --change powershell-proof-compatibility` → `4/4 artifacts complete`.
5. `openspec validate powershell-proof-compatibility --strict` → `Change 'powershell-proof-compatibility' is valid`.
6. Corrected parent-card proof → `PROOF OK: C-02 and C-03 resolved`, `PARENT_PROOF_EXIT=0`.
7. Runtime parity/import probe → seven matching copies, `PARITY_EXIT=0`.
8. Scope/whitespace proof → `SCOPE_EXIT=0`.

## Non-Blocking Information

### I-01 — Installer configuration drift is separate from runtime deployment

`HERMES_HOME=O:/workspaces/_config/agent4070/hermes python install.py --check --no-profiles --no-service --no-cron` reports:

- `would change: config - config set crew.roles_path`
- `1 change(s) needed`
- Installer exit: `1`

The independent byte and import parity probe proves that this is not stale plugin code. No Reviewer configuration change was made.

### I-02 — Historical failure text remains in tasks.md

`tasks.md:28-29` records the earlier immutable-proof failure and says coordinator correction was required. The parent card now has an owner-authorized corrected proof and an independently reproduced exit-0 result. The stale text is historical evidence, not a current implementation defect, but it should be normalized during later artifact housekeeping so readers do not mistake it for current state.

## Residual Scope

- The broad repository suite was not rerun in v2. Reviewer v1 already established that its unrelated Windows/board baseline failures are not attributable to this two-file remediation.
- Approval is confined to the PowerShell proof compatibility remediation and does not claim that unrelated `crew.roles_path` configuration drift is resolved.
- No Gateway or Dashboard restart was required or performed.

## Approval Gate

The round-2 gate from Reviewer v1 is satisfied:

1. Double-quoted `$()` detection and routing: **PASS**.
2. Shell-comment handling with no false classification: **PASS**.
3. Negative and real-runtime regressions: **PASS**.
4. Byte-identical active runtime deployment: **PASS (7/7)**.
5. Reproducible Task 2.2 runner: **PASS**.
6. Focused suites, exact feature proofs, POSIX probes, strict OpenSpec validation, parent proof, and report artifact proof: **PASS / exit 0**.
