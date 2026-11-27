# Delta Spec: Proof Safety — Non-Interactive Stdin Isolation and Process-Tree Termination

## ADDED Requirements

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
