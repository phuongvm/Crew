# Tasks: PowerShell Proof Command Compatibility & Auto-Routing

## Group 1: Safety Preflight and Runtime Auto-Routing Implementation
- [x] 1.1 Implement `detect_bare_powershell` and integrate into `check_proof` in `oss/crew/scripts/crew_safety.py`
  - **Proof**: `python -c "import sys; sys.path.insert(0, 'O:/workspaces/oss/crew/scripts'); import crew_safety; ok, why = crew_safety.check_proof('Test-Path foo', 'safe'); assert not ok and 'PowerShell' in why; print('PASS 1.1')"`
- [x] 1.2 Implement runtime auto-routing for PowerShell cmdlets in `run_proof` in `oss/crew/scripts/crew_safety.py`
  - **Proof**: `python -c "import sys; sys.path.insert(0, 'O:/workspaces/oss/crew/scripts'); import crew_safety; res = crew_safety.run_proof('Test-Path O:/workspaces/AGENTS.md'); assert res.rc == 0 and 'True' in res.output; print('PASS 1.2')"`

## Group 2: Unit Testing & Verification
- [x] 2.1 Add automated test cases to `oss/crew/tests/test_crew_safety.py`
  - **Proof**: `python -c "import sys; sys.path.insert(0, 'O:/workspaces/oss/crew/tests'); content = open('O:/workspaces/oss/crew/tests/test_crew_safety.py', encoding='utf-8').read(); assert 'test_bare_powershell' in content; print('PASS 2.1')"`
- [x] 2.2 Execute pytest suite verifying clean execution across `test_crew_safety.py`
  - **Proof**: `cd O:/workspaces/.worktrees/wt-crew-powershell-proof && "O:/workspaces/oss/hermes-agent/.venv/Scripts/python.exe" -m pytest tests/test_crew_safety.py -q`
  - W-01: use the installed Hermes venv interpreter; bare `python` does not provide pytest on this Windows host. Tests import `scripts` from the isolated worktree, not the installed plugin.

## Group 3: Multi-Profile Deployment & Commit
- [x] 3.1 Commit changes to `oss/crew` fork in isolated worktree and fast-forward to `main`
  - **Proof**: `git -C O:/workspaces/oss/crew status -s`
- [x] 3.2 Synchronize updated plugin runtime across all profiles via `install.py`
  - Closed at archive (t_e3dca8be): runtime-copy parity verified by Reviewer v2 (`copy_count=7`, `PARITY_EXIT=0`, SHA-256 match); remaining `--check` drift is the unrelated `crew.roles_path` config only.
  - **Proof**: `python O:/workspaces/oss/crew/install.py --check --no-profiles --no-service --no-cron`

## Review v1 remediation (t_5cb2469f)
- C-02: scan executable `$()` contexts inside double quotes, including nested substitutions and balanced groups; restore surrounding quote state. Preserve single-quoted and escaped literals.
- C-03: ignore word-initial unquoted shell comments through newline; retain quoted/escaped/embedded `#`, and resume detection after newline.
- Regression evidence: pre-fix focused run reproduced 8 failing subtests. After the scanner fix, `test_crew_safety.py` plus `test_crew_safety_resolution.py`: 50 passed, 27 subtests passed (exit 0). Includes real PowerShell substitution output/exit-code tests and real Bash comment/literal regression tests.
- Deployment evidence: commit `0542d11` fast-forwarded to production `main` without checkout/switch. `install.py.step_plugin` synchronized all seven existing plugin homes (default, coder, designer, leader, qa, researcher, reviewer), with automatic backups and no service restart or config/skill changes. Read-back SHA-256 and imported detector assertions pass for every copy: `961780666c32d570d40a262386fbc6833776e0f733b2a248e3f2707c61cf9a4c`.
- Full installer `--check` is **not green**: only `crew.roles_path` configuration drift remains; runtime-copy parity is green. This unrelated config was not changed.
- Immutable card verdict was executed through the installed `crew_card.py`: **FAIL**, rc=1, `SyntaxError: unterminated string literal`. Strict OpenSpec validation within that command passed. Coordinator must repair the proof contract; task is not complete.
- The card's immutable proof embeds an unescaped `$()` inside the shell's double-quoted Python argument. That evaluates the substitution before Python can test it; it is not literal test data. The worker must not alter this proof or exempt it from detection. Coordinator correction may be required.
