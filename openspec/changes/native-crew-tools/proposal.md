# Proposal: Native Hermes Tools for Crew Plugin

## Why

Crew currently lacks first-class native tool registration (`ctx.register_tool`) within the Hermes Agent ecosystem. Agents interacting with Crew are forced to spawn terminal subshells to run CLI Python and Bash scripts (`crew_card.py`, `crew-run.sh`, `crew_diagnose.py`), which causes recurring Windows path translation issues (MSYS2 `/c/` vs Windows `C:\`), complex shell quoting and escaping failures on multi-line contracts, and approval friction/hangs. Implementing native Hermes tools provides type-safe JSON schema validation, zero-subshell execution, improved token efficiency, and cross-platform reliability.

## What Changes

- Implement native Hermes tool handlers and JSON schemas in `oss/crew/native_tools.py` for:
  - `crew_card_create`: Programmatic creation of contract-guarded Crew cards without shell spawning.
  - `crew_diagnose`: Structured inspection and diagnosis of cards across board states (`blocked`, `triage`, `todo`, `ready`, etc.) or by specific card ID.
  - `crew_verdict`: Direct execution and recording of owner-confirmed proof commands with safety preflight and automatic rework limits.
  - `crew_status`: In-flight card and coordinator decision status reporting for rapid context retrieval.
- Register all four native tools under the `"crew"` toolset in `oss/crew/__init__.py` during plugin registration (`ctx.register_tool`).
- Maintain full backwards compatibility with existing CLI commands and slash commands.
- Provide comprehensive automated test coverage in `oss/crew/tests/test_native_tools.py`.

## Capabilities

### New Capabilities
- `native-crew-tools`: First-class native Hermes tools (`crew_card_create`, `crew_diagnose`, `crew_verdict`, `crew_status`) exposed directly via the plugin tool registry with structured JSON schemas and robust error handling.

### Modified Capabilities
<!-- No requirement changes to existing capabilities -->

## Impact

- **Affected Code**: `oss/crew/__init__.py`, `oss/crew/native_tools.py` (new), `oss/crew/tests/test_native_tools.py` (new).
- **APIs**: Exposes 4 new native tools in the Hermes tool registry when the Crew plugin is loaded.
- **Dependencies**: No external dependencies added; uses standard library and existing Hermes / Crew modules.
- **Systems**: Eliminates subshell and terminal escaping failures across Windows and POSIX hosts.
