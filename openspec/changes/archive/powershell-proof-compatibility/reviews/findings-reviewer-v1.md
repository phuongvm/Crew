# Independent Review Findings v1 — PowerShell Proof Compatibility

## Verdict

**REJECTED**

The focused implementation suite and the three executable feature proofs pass, but the change is not complete and two detector defects violate the shell-routing contract. Three CRITICAL findings block approval.

## Review Target

- Repository: `O:/workspaces/oss/crew`
- Candidate commit: `14bf312776f067ae433ae1298074ef4c28e6488f`
- Parent commit: `9b6c8fe2309f4214ee6c24ed6ef8dc6a8be5e73e`
- Review round: 1 (cold artifact/diff lens plus independent runtime execution)
- Candidate scope: `scripts/crew_safety.py`, `tests/test_crew_safety.py`

## Scope

### Specifications and design reviewed

- `openspec/changes/powershell-proof-compatibility/proposal.md`
- `openspec/changes/powershell-proof-compatibility/design.md`
- `openspec/changes/powershell-proof-compatibility/tasks.md`
- `openspec/changes/powershell-proof-compatibility/specs/proof-safety/spec.md`
- `openspec/specs/worktree-isolation-governance/spec.md`

### Source and tests reviewed

- Full `scripts/crew_safety.py`
- Full `tests/test_crew_safety.py`
- Cold diff `14bf312^..14bf312`
- Installed runtime copies under the default, coder, and reviewer profiles

### Architecture and governance reviewed

- `README.md` proof-safety and deployment model
- `REFERENCE.md` proof-runner and role-profile architecture
- `WINDOWS.md` native Windows proof execution contract
- `SECURITY.md`
- Code-review mandate, collaboration lessons, and active coordination dashboard

### Not Reviewed

- Other Crew implementation modules were not line-reviewed because commit `14bf312` changes only the two files above.
- Profile synchronization was inspected, not executed. Deployment is a state-changing operation outside the Reviewer role and Task 3.2 is explicitly assigned implementation work.
- The broad 834-test suite was executed, but its 103 failures and 38 setup errors are not attributed to this commit because they are dominated by the current Hermes descendant-board read fence, Windows symlink privilege, and unrelated baseline behavior. They are recorded as non-approval evidence only; the focused suite is the relevant regression gate for this candidate.

## Findings Summary

| Severity | Count | Result |
|---|---:|---|
| CRITICAL | 3 | Blocks approval |
| WARNING | 1 | Must be made reproducible |
| INFO | 2 | Verified positive evidence |

## Findings by SDLC Layer

### Specifications / Delivery

#### C-01 — Runtime profile copies were not deployed

- Severity: **CRITICAL**
- Spec reference: `tasks.md:15-19`, Group 3 / Task 3.2; proposal `Impact` requires compatibility across environments.
- Evidence:
  - Source SHA-256: `fef1d64c99be674ccbf402e4502b4a0d6df5c85950e22f92a30488eb690084c2`.
  - Default, coder, and reviewer installed copies all have SHA-256 `850e032006c323efcfd2b4018675e8b5ff94f3c669b3c3156f1aa50bca58fc5d`.
  - `grep -c 'def detect_bare_powershell'` returns `1` for source and `0` for every inspected installed copy.
  - Importing the reviewer runtime copy reports `has_detect_bare_powershell=False`; the acceptance assertion exits 1.
  - `python install.py --check --no-profiles --no-service --no-cron` exits 1 and reports four changes needed, including plugin/runtime copies.
- Impact: The live installed Crew copies continue using the old Git-Bash-only behavior. The source fix cannot prevent exit 127 in the runtime environments this change claims to repair.
- Required correction: Perform Task 3.2 using the approved deployment path, then prove every active installed `crew_safety.py` copy is byte-identical to source and exposes `detect_bare_powershell`. Do not restart the Gateway; report if a user-operated restart is required.

### Code / Runtime Routing

#### C-02 — Executable cmdlets inside double-quoted command substitutions are missed

- Severity: **CRITICAL**
- Spec reference: proof-safety spec `Windows Runtime Auto-Routing for PowerShell Cmdlets`, lines 19-28; preflight requirement lines 5-12.
- Code reference: `scripts/crew_safety.py:309-349` and routing condition `scripts/crew_safety.py:589-591`.
- Evidence:
  - Repro command: `echo "$(Get-Date)"`.
  - `detect_bare_powershell(...)` returns `''` and `proof_check(...)` returns `ok`.
  - `run_proof(...)` stays in Git Bash and outputs `/usr/bin/bash: line 1: Get-Date: command not found` while returning rc 0 because `echo` succeeds.
  - The direct acceptance assertion `detect_bare_powershell('echo "$(Get-Date)"') == 'Get-Date'` exits 1.
- Cause: `_command_words` skips every character inside double quotes at lines 316-323, including `$(`, although shell command substitution remains executable inside double quotes.
- Impact: Preflight silently accepts a PowerShell-bearing proof, runtime does not route it, Bash emits command-not-found, and the proof can falsely PASS with rc 0.
- Required correction: Parse command substitutions as executable contexts even when nested inside double quotes, while preserving literal single-quoted text. Add preflight and real-runtime regression tests proving detection, PowerShell routing, and correct exit/output semantics.

#### C-03 — Shell comments are parsed as executable commands and can reroute POSIX proofs

- Severity: **CRITICAL**
- Spec reference: proof-safety spec `Execution of standard POSIX proof command on Windows`, lines 30-33; proposal line 38 requires 100% POSIX backward compatibility.
- Code reference: `scripts/crew_safety.py:309-349` and `scripts/crew_safety.py:589-599`.
- Evidence:
  - Repro command: `echo ok # ; Get-Date`.
  - Bash treats everything after `#` as a comment, but `detect_bare_powershell(...)` returns `Get-Date` and preflight flags the command.
  - The direct acceptance assertion that detection returns `''` exits 1.
- Cause: `_command_words` has no unquoted `#` comment state; separators after `#` are still scanned as commands.
- Impact: A standard POSIX proof with a comment mentioning a cmdlet is incorrectly blocked at preflight and, if executed, routed to PowerShell instead of Git Bash. That violates the explicit no-regression routing contract and can change command semantics.
- Required correction: Stop command-word scanning at an unquoted shell comment through newline, resume correctly after newline, and add tests for inline comments, comment-only lines, quoted `#`, and a following real command on the next line.

### Tests / Reproducibility

#### W-01 — The literal OpenSpec test command is not reproducible in the declared environment

- Severity: **WARNING**
- Spec reference: `tasks.md:12-13`, Task 2.2.
- Evidence: Literal `python -m pytest O:/workspaces/oss/crew/tests/test_crew_safety.py -q` exits 1 with `No module named pytest`.
- Counter-evidence: Running the same test file with `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe` exits 0 with `39 passed in 11.44s`.
- Required correction: Bind Task 2.2 to a repository-supported interpreter/runner available on Windows, or provision pytest through the approved project toolchain. Keep the command exact and independently reproducible.

### DevOps / Scope

No unrelated source files were changed. `git diff --name-status 14bf312^ 14bf312` lists exactly `scripts/crew_safety.py` and `tests/test_crew_safety.py`; `git diff --check` exits 0. The production checkout remained on `main`; no checkout or switch was performed during review.

## Positive Verification Evidence

### I-01 — Focused suite and direct feature proofs pass

- `O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -m pytest tests/test_crew_safety.py -q`
  - Result: `39 passed in 11.44s`
  - Exit: 0
- Task 1.1 proof
  - Result: `PASS 1.1`
  - Exit: 0
- Task 1.2 real PowerShell proof
  - Result: `PASS 1.2`
  - Exit: 0
- Task 2.1 source-presence proof
  - Result: `PASS 2.1`
  - Exit: 0

### I-02 — POSIX runtime path remains correct for ordinary commands

- `run_proof('test -f O:/workspaces/AGENTS.md')` returned `(0, '', '')`.
- `run_proof('printf posix-ok')` returned `(0, 'posix-ok', '')`.
- Combined independent POSIX runtime probe exited 0.
- Explicit wrapper preflight returned `ok` for `pwsh.exe -NoProfile -Command "Test-Path 'some/file.txt'"`.
- OpenSpec status reported 4/4 artifacts complete; `openspec validate powershell-proof-compatibility --strict` exited 0.

## Broad Suite Observation

Command:

`O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe -m pytest tests -q`

Result:

- 693 passed
- 103 failed
- 38 errors
- 3 skipped
- Exit 1

The failures include widespread `sqlite3.OperationalError: unable to open database file` from the active Hermes descendant-board fence and Windows symlink privilege errors. This run does not establish a clean repository-wide baseline and is not used to attribute a regression to commit `14bf312`. Approval is already blocked by C-01 through C-03.

## Required Re-Review Gate

A round-2 review must receive and independently verify:

1. Correct parsing and runtime routing for PowerShell cmdlets inside double-quoted `$()` substitutions.
2. Correct shell-comment handling with no false PowerShell classification.
3. New negative and real-runtime tests for both defects.
4. Byte-identical deployment across all active Crew profile/plugin copies.
5. A reproducible Task 2.2 command that exits 0 in the declared environment.
6. Focused suite exit 0, exact feature proofs exit 0, POSIX regression probes exit 0, strict OpenSpec validation exit 0, and card artifact proof exit 0.
