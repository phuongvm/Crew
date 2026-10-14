# Proposal: PowerShell Proof Command Compatibility & Auto-Routing on Windows

## Why

In `oss/crew/scripts/crew_safety.py`, unattended proof commands on Windows are executed through Git Bash (`argv = [bash, "-c", cmd]`).
When an agent, coordinator, or human user drafts a Kanban card with a proof command containing bare PowerShell cmdlets (such as `Test-Path "file.txt"` or `Get-ChildItem -Recurse`), Git Bash fails with `command not found: Test-Path` (exit code 127).
This creates a critical operational failure mode where valid work is falsely marked as failed, blocking card completion and requiring manual intervention.

To eliminate this friction permanently across all environments:
1. The preflight check (`proof_check`) must detect bare PowerShell cmdlets and flag them with actionable remediation advice before a card opens.
2. The runtime executor (`run_proof`) on Windows must automatically route bare PowerShell commands through `pwsh.exe -NoProfile -Command` instead of letting `bash` fail with exit code 127.

## What Changes

1. **Preflight Linter in `crew_safety.py`**:
   - Define `POWERSHELL_BARE_CMDLET_RX` identifying common cmdlets (`Test-Path`, `Get-ChildItem`, `Get-Content`, `Select-String`, etc.).
   - Define `POWERSHELL_WRAPPER_RX` identifying explicit wrappers (`powershell`, `pwsh`).
   - In `check_proof(cmd, mode="safe")`, flag bare PowerShell cmdlets with explicit guidance to use POSIX (`test -f`) or wrap in `pwsh.exe -NoProfile -Command "..."`.
2. **Runtime Auto-Routing in `crew_safety.py`**:
   - In `run_proof(cmd, ...)` on Windows, detect bare PowerShell cmdlets and execute via `[pwsh_bin, "-NoProfile", "-Command", cmd]`.
   - Fall back gracefully to `powershell.exe` if `pwsh.exe` is not in PATH.
3. **Unit Tests in `tests/test_crew_safety.py`**:
   - Add test cases verifying preflight flagging of bare cmdlets.
   - Add test cases verifying that wrapped PowerShell commands pass preflight.
   - Add test cases verifying that runtime execution on Windows successfully dispatches bare cmdlets via PowerShell.

## Capabilities

### New Capabilities
- `powershell-proof-compatibility`: Automatic detection, preflight linting, and runtime auto-routing of PowerShell proof commands on Windows.

### Modified Capabilities
- `proof-safety`: Enhanced safety evaluator supporting dual-shell (Git Bash + PowerShell) execution semantics on Windows hosts.

## Impact

- Eliminates false-positive proof failures (exit code 127) when tasks utilize Windows-native commands.
- Maintains 100% backward compatibility for standard POSIX commands (`test -f`, `grep`, `pytest`, `cargo test`, `curl`).
- Prevents invalid card creation through coordinator preflight validation.
