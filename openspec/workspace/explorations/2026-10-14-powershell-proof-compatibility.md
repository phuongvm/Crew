# Exploration: PowerShell Proof Command Compatibility & Auto-Routing on Windows

- **Date**: 2026-10-14
- **Target Project**: `oss/crew` (`O:/workspaces/oss/crew`)
- **Scope**: Proof command safety checks, shell compatibility, Windows Git Bash execution, auto-routing

---

## 1. Context & Problem Statement

In `oss/crew/scripts/crew_safety.py` (line 475-482), all unattended proof commands on Windows are executed through Git Bash:
```python
if IS_WINDOWS:
    bash = git_bash()
    argv = [bash, "-c", cmd]
```

When an agent or user drafts a Kanban card with a proof command containing bare PowerShell cmdlets (e.g., `Test-Path "file.txt"`, `Get-ChildItem -Recurse`), execution inside Git Bash fails immediately:
```text
/usr/bin/bash: line 1: Test-Path: command not found (exit code: 127)
```
This causes automated verification to fail even when the underlying work artifact is completely valid.

## 2. Architectural Objectives

1. **Preflight Linter (Tier 2)**:
   - Enhance `crew_safety.py:check_proof()` and `proof_check()` to inspect incoming commands.
   - Detect bare PowerShell cmdlets (`Test-Path`, `Get-ChildItem`, `Get-Content`, `Select-String`, `New-Item`, `Remove-Item`, etc.) lacking a `powershell` or `pwsh` wrapper.
   - Return an informative `flagged:` reason advising the Coordinator to convert to POSIX (e.g. `test -f`) or wrap via `pwsh.exe -NoProfile -Command "..."`.

2. **Runtime Auto-Routing (Tier 3)**:
   - Enhance `crew_safety.py:run_proof()` on Windows.
   - If a bare PowerShell cmdlet is encountered at execution time, automatically route execution to `["pwsh.exe", "-NoProfile", "-Command", cmd]` (falling back to `powershell.exe`) instead of failing inside `bash`.

3. **Multi-Platform Invariant**:
   - POSIX commands (`test -f`, `grep`, `pytest`, `cargo test`, `curl`, `python -c ...`) continue to execute through Git Bash on Windows and native POSIX shells on Linux/macOS without modification or regression.

## 3. Implementation Seams & Touchpoints

- `oss/crew/scripts/crew_safety.py`:
  - Add `POWERSHELL_BARE_CMDLET_RX` and `POWERSHELL_WRAPPER_RX`.
  - Implement `detect_bare_powershell(cmd) -> tuple[bool, str]`.
  - Integrate detection into `check_proof(cmd, mode)`.
  - Add auto-routing in `run_proof(cmd, ...)`.
- `oss/crew/tests/test_crew_safety.py`:
  - Unit test: `test_bare_powershell_flagged_in_safe_mode`.
  - Unit test: `test_powershell_wrapper_passes_safe_mode`.
  - Unit test: `test_bare_powershell_auto_routed_on_windows`.
