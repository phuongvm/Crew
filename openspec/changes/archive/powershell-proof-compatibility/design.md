# Design: PowerShell Proof Command Compatibility & Auto-Routing Architecture

## Architectural Overview

This design enhances the proof safety pipeline in `oss/crew/scripts/crew_safety.py` to support dual-shell execution on Windows hosts. It eliminates false failure exits (exit code 127) when commands use PowerShell cmdlets, while preserving strict security boundaries.

### Component Layers

1. **Preflight Linter Layer (`crew_safety.py:check_proof`)**:
   - Analyzes command strings before cards are opened on Kanban.
   - Utilizes regex `POWERSHELL_BARE_CMDLET_RX` to recognize standard cmdlets:
     `Test-Path`, `Get-ChildItem`, `Get-Content`, `Set-Content`, `Add-Content`, `Select-String`, `Set-Location`, `New-Item`, `Remove-Item`, `Get-Process`, `Start-Process`, `Stop-Process`.
   - Utilizes `POWERSHELL_WRAPPER_RX` to recognize existing wrappers: `powershell`, `pwsh`.
   - If a bare cmdlet is detected without a wrapper, `check_proof` returns `flagged: bare PowerShell cmdlet '<name>' without pwsh wrapper...`.
   - The coordinator intake tool `crew_card.py proof-check` surfaces this flag, allowing the coordinator to rewrite the command into POSIX or add the wrapper before `kanban_create`.

2. **Runtime Execution Layer (`crew_safety.py:run_proof`)**:
   - Governs execution of unattended proofs on Windows.
   - Detects if `cmd` contains bare PowerShell cmdlets.
   - Resolves the best available PowerShell executable on Windows:
     1. `pwsh` (PowerShell 7 Core)
     2. `powershell` (Windows PowerShell 5.1)
     3. Fallback `pwsh.exe`
   - Dispatches execution via `[pwsh, "-NoProfile", "-Command", cmd]`.
   - For all standard POSIX commands, retains the existing Git Bash execution path: `[bash, "-c", cmd]`.

3. **Verification Layer (`tests/test_crew_safety.py`)**:
   - Automated unit tests validating detection, wrapper bypass, and runtime execution.
