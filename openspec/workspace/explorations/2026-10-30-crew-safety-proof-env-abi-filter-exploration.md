# Exploration: Filter `crew_safety.proof_env()` `site-packages` by Proof Interpreter Python ABI Version

- **Date**: 2026-10-30
- **Project**: `O:/workspaces/oss/crew` (`scripts/crew_safety.py`, `tests/test_crew_safety_resolution.py`)
- **Triggering Card**: `t_9145e18f` (`Implement Slice 3 (Tasks 1.1-3.2) of hermes-openspec-slice3-ux-and-subproject-fixes in worktree`)

---

## Problem Statement

When `crew_safety.run_proof(cmd, ...)` executes a card's `proof command`, `crew_safety.proof_env()` (`scripts/crew_safety.py:219-266`) unconditionally prepends every discovered Hermes venv `site-packages` directory (`installs/*/environments/*/venv/Lib/site-packages`, `oss/hermes-agent/venv/Lib/site-packages`, `oss/hermes-agent/.venv/Lib/site-packages`) onto `PYTHONPATH`, alongside the pure-Python `oss/hermes-agent` source checkout.

On multi-Python hosts (such as `AGENT-4070`, where Hermes PM environments use CPython `3.14` (`cp314`) while workspace virtualenvs like `O:/workspaces/.venv` use CPython `3.12` (`cp312`)), prepending `cp314` `site-packages` ahead of a `cp312` proof interpreter's own packages causes `ImportError` / binary ABI crashes whenever the `cp312` interpreter imports compiled C/Rust extensions (`pydantic_core._pydantic_core.cp314-win_amd64.pyd`, `numpy`, etc.).

Clearing `PYTHONPATH` completely (`-E` or `env -u PYTHONPATH`) breaks proof commands that still rely on pure-Python Hermes source modules (`hermes_constants`, `hermes_cli`, etc.) from `oss/hermes-agent`!

---

## Empirical Root Cause (`scripts/crew_safety.py:231-265`)

1. `proof_env(extra=None)` collects two distinct categories of paths into `extra_py_paths`:
   - **Pure-Python Hermes source roots** (`for src in _find_hermes_sources(): extra_py_paths.append(src)`), which are ABI-agnostic across Python 3.x minor versions.
   - **Compiled virtualenv `site-packages` directories** (`installs/*/environments/*/venv/.../site-packages` and `<hermes_src>/{venv,.venv}/.../site-packages`), which contain version-specific C/Rust extension binaries (`.cp314-win_amd64.pyd`, `.cpython-314-x86_64-linux-gnu.so`) and metadata recorded in `<venv>/pyvenv.cfg` (`version = 3.14.x` / `version_info = 3.14.x`) or `<venv>/lib/python3.14/site-packages`.
2. Furthermore, `proof_env()` currently puts `extra_py_paths` **ahead** of `existing_pp`, and `run_proof(cmd, ...)` calls `proof_env()` without passing `cmd` — so `proof_env()` cannot inspect which Python interpreter `cmd` invokes (or default to `sys.version_info[:2]` when no explicit interpreter path is in `cmd`).

---

## Solution & Deep Module Interface

### 1. Interpreter ABI Detection (`_site_packages_py_version` & `_cmd_python_version`)
- **`_venv_py_version(sp_dir: str) -> tuple[int, int] | None`**:
  1. Check POSIX path segment `.../lib/pythonX.Y/site-packages` -> `(int(X), int(Y))`.
  2. Check `<venv>/pyvenv.cfg` (`os.path.dirname(os.path.dirname(sp_dir))` on Windows `Lib/site-packages`, or `os.path.dirname(os.path.dirname(os.path.dirname(sp_dir)))` on POSIX `lib/pythonX.Y/site-packages`) for `version = X.Y...` or `version_info = X.Y...` -> `(int(X), int(Y))`.
  3. Scan compiled extension filenames directly inside common binary packages or `sp_dir` (`*.cp314-*.pyd`, `*.cpython-314-*.so`) if `pyvenv.cfg` is absent -> `(3, 14)`.
  4. Return `None` if version cannot be determined.
- **`_target_python_version(cmd: str | None = None) -> tuple[int, int]`**:
  - When `cmd` names an explicit Python executable path (e.g. `"O:/workspaces/.venv/Scripts/python.exe"`, `/path/to/.venv/bin/python3`, `python3.12`), inspect the adjacent `pyvenv.cfg` (`<venv>/pyvenv.cfg`) first (zero subprocess overhead, `< 1ms`!). If no `pyvenv.cfg` exists next to the executable, parse `python3.XX` from the executable basename or fall back to probing `<exe> -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"` (with a 2s timeout) or `sys.version_info[:2]`.
  - When `cmd` is `None` or uses bare `python` / `python3` / `pytest`, resolve via `shutil.which` -> `pyvenv.cfg` or fall back to `(sys.version_info[0], sys.version_info[1])`.
- **`proof_env(extra=None, *, cmd=None)`**:
  - Always include pure-Python Hermes source checkouts (`_find_hermes_sources()`) in `PYTHONPATH`.
  - Include a candidate `site-packages` directory **ONLY IF** `_venv_py_version(sp)` equals `_target_python_version(cmd)`! (If `_venv_py_version(sp)` is `(3, 14)` and the proof interpreter is `(3, 12)`, that `site-packages` directory is skipped so the `(3, 12)` venv uses its own compatible `site-packages` while still importing `hermes_constants` from `oss/hermes-agent`!).
  - Preserve existing `proof_env(extra=None)` call signature (`cmd` is optional keyword/second parameter defaulting to `None`) so all existing callers (`crew_coordinator.py`, `crew_observe.py`, tests) remain 100% compatible, while `run_proof` passes `env=proof_env(cmd=cmd)`.

---

## Preserved Crew Invariants

- **`CREW-INV-3`**: `_find_hermes_sources()`, `os.path.join("oss", "hermes-agent")`, and `"openspec", "changes", "archive"` remain untouched.
- **`test_no_hardcoded_drive_or_workspace_paths_in_module`**: Zero hardcoded `O:/`, `O:\`, or `.venv/Lib/site-packages` literals in `crew_safety.py`.
- **Zero-Checkout**: Implement in isolated worktree `O:/workspaces/.worktrees/wt-crew-proof-env-abi`, verify with `daily-sync-watchdog.ps1 -GateOnly -Target ...`, publish to `origin/main`, and run `apply-live-crew-cutover.ps1` across all 7 profiles.
