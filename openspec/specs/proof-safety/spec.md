# Spec: Proof Safety — PowerShell Proof Command Compatibility & Auto-Routing Specification

## Purpose

Keep crew proof commands runnable on Windows hosts where proofs execute under Git Bash: lint bare PowerShell cmdlets at intake preflight and route unattended PowerShell proofs through a PowerShell interpreter at runtime.

## Requirements

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

### Requirement: Non-Interactive Stdin Isolation and Process-Tree Termination for Proof Execution
Every unattended proof command executed through `run_proof` SHALL attach a null standard input (`DEVNULL`) across all operating systems and shell adapters (Windows Git Bash, Windows PowerShell, and POSIX) and MUST execute via the bounded runner so timeouts terminate the full descendant process tree and cap captured streams.

#### Scenario: Windows Git Bash proof runs under a parent holding an open stdin pipe
- **GIVEN** a Windows host where the parent process holds an open `stdin=PIPE` handle with a blocked reader thread (such as `agent.managed_worker`)
- **WHEN** `run_proof` executes a standard POSIX command such as `test -s 'path/to/file'` via `[git_bash, "-c", cmd]`
- **THEN** the runner SHALL bind `stdin` to `DEVNULL` before process creation
- **AND** the command MUST complete without blocking on the parent stdin pipe.

#### Scenario: Proof execution times out with nested descendant processes
- **GIVEN** a proof command executing on Windows or POSIX that spawns child processes (such as `python`, `pytest`, or `node`) and exceeds `timeout`
- **WHEN** `run_proof` reaches the monotonic timeout deadline
- **THEN** the runner MUST terminate the entire process tree (via absolute `%SystemRoot%\System32\taskkill.exe /PID <pid> /T /F` on Windows or process-group signaling on POSIX) and sweep any surviving processes tagged with `CREW_RUN_MARKER`
- **AND** `run_proof` SHALL return `Result(rc=124, out="proof command timed out after <timeout>s", blocked="")` with zero surviving descendant processes.

#### Scenario: Noisy proof output stays memory-bounded
- **GIVEN** a proof command that writes megabytes to stdout or stderr
- **WHEN** `run_proof` captures process output through `crew_proc.run_bounded()`
- **THEN** each captured stream SHALL be bounded to 64 KiB head-plus-tail storage without halting the child process or exhausting host memory.

#### Scenario: Auxiliary Python version probe isolates stdin
- **GIVEN** `_exe_py_version` probes an external Python interpreter on Windows inside a non-interactive worker
- **WHEN** the subprocess runs to read `sys.version_info`
- **THEN** the subprocess MUST attach `stdin=DEVNULL` so it cannot inherit or stall on the parent's stdin handle.
