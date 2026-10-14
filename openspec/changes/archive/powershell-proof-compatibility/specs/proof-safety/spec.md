# Spec: PowerShell Proof Command Compatibility & Auto-Routing

## ADDED Requirements

### Requirement: Preflight Linting of Bare PowerShell Cmdlets
The proof safety evaluator SHALL inspect incoming proof commands during preflight (`proof-check`) and detect bare PowerShell cmdlets when they are invoked without an explicit shell wrapper (`powershell` or `pwsh`).

#### Scenario: Bare Test-Path cmdlet checked in safe mode
- **GIVEN** a proof command containing `Test-Path "some/file.txt"` without a `pwsh` or `powershell` prefix
- **WHEN** `proof_check(cmd)` is evaluated in `safe` mode
- **THEN** the checker SHALL return `flagged: bare PowerShell cmdlet 'Test-Path' without pwsh wrapper (Git Bash on Windows will fail with command not found). Use POSIX (e.g. 'test -f') or wrap as 'pwsh.exe -NoProfile -Command "..."'`
- **AND** the intake coordinator is prevented from opening an invalid card without explicit user override or conversion.

#### Scenario: Wrapped PowerShell command checked in safe mode
- **GIVEN** a proof command formatted as `pwsh.exe -NoProfile -Command "Test-Path 'some/file.txt'"`
- **WHEN** `proof_check(cmd)` is evaluated in `safe` mode
- **THEN** the checker SHALL recognize the valid wrapper and return `ok` (provided no other dangerous patterns exist).

### Requirement: Windows Runtime Auto-Routing for PowerShell Cmdlets
On Windows platforms, when an unattended proof command containing a bare PowerShell cmdlet is executed via `run_proof`, the runtime SHALL automatically dispatch the command through a PowerShell interpreter instead of letting Git Bash fail with exit code 127.

#### Scenario: Unattended execution of bare PowerShell proof command on Windows
- **GIVEN** a proof command `Test-Path "O:/workspaces/AGENTS.md"` executing on Windows
- **WHEN** `run_proof(cmd, ...)` is called
- **THEN** the runtime SHALL detect the bare PowerShell cmdlet
- **AND** the runtime SHALL resolve `pwsh.exe` (or fallback to `powershell.exe`)
- **AND** the command SHALL execute via `[pwsh, "-NoProfile", "-Command", cmd]`
- **AND** the exit code and output reflect the result of PowerShell execution rather than Git Bash `command not found`.

#### Scenario: Execution of standard POSIX proof command on Windows
- **GIVEN** a standard POSIX proof command `test -f "O:/workspaces/AGENTS.md"` executing on Windows
- **WHEN** `run_proof(cmd, ...)` is called
- **THEN** the runtime SHALL route execution through Git Bash (`[bash, "-c", cmd]`) as before.
