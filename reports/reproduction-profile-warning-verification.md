# Subagent Execution Reproduction & Profile Conflict Warning Verification Report

> **Card ID**: `t_ae6bdd43`  
> **Author**: `@coder` (Implementation Specialist)  
> **Verifier**: `@reviewer` (Audit Task `t_aa25c4b7`)  
> **Target Audience**: Commander  
> **Date**: October 19, 2026  
> **Repository**: `oss/crew`  
> **Target Artifact**: `oss/crew/reports/reproduction-profile-warning-verification.md`  
> **Status**: COMPLETED / VERIFIED (All Acceptance Criteria Satisfied)

---

## 1. Executive Summary & Verdict

### Final Verdict: RESOLVED (Zero Shared Profile Warnings, Complete Install ID Parity)

This reproduction report delivers rigorous empirical verification of child subagent process identity resolution and ledger concurrency under the Crew evaluation harness (`eval_crew_skills.py`). 

Following the remediation in task `t_9d7194e9` (which pinned Hermes binary invocation to `O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe` with fallback to `sys.executable -m hermes_cli.main`) and the subsequent `--verify-only` approval in `t_ba475a34`, this investigation reproduced live, active subagent execution to determine whether conflicting `install_id` entries appear in `spawn-ledger.json` or whether `shared_profile_warning` triggers during active concurrent runs.

### Empirical Reproduction Summary Table

| Metric | Measured Baseline / Observation | Target Invariant | Compliance Status |
| :--- | :---: | :---: | :---: |
| **Active Subagents Executed** | 3 parallel subagents (`crew-diagnose`, `crew-verifier`, `crew-role-worker`) | $\ge 1$ live subagent runs | **PASS** (100% executed) |
| **Subagent Exit Codes** | All `rc=0` (diagnose: 45.9s, verifier: 56.9s, worker: 63.3s) | `rc == 0` | **PASS** (3/3 succeeded) |
| **Total Ledger Polls During Run** | 1,256 polls (50ms interval across 63.3s active window) | High-frequency continuous | **PASS** (Complete coverage) |
| **Peak Concurrent Subagents in Ledger** | 3 active CLI subagents simultaneously (+ 1 dashboard) | Multi-process concurrency | **PASS** (Concurrent execution captured) |
| **Observed Install IDs in Ledger** | `["59b350e06553"]` exclusively | `59b350e06553` | **PASS** (100% consistent) |
| **Foreign / Conflicting Install IDs** | **0** detected | 0 | **PASS** (Zero conflicts) |
| **`shared_profile_warning` Triggers** | **0** triggered (`""` returned on all 1,256 polls) | 0 triggers | **PASS** (Zero warnings) |
| **Warning Mentions in Process Logs** | **0** in stdout/stderr | 0 warnings | **PASS** (Clean logs) |
| **Post-Execution Ledger Hygiene** | 1 entry (Dashboard PID 11908); all subagents pruned | Clean process unmount | **PASS** (Zero stale locks) |
| **Zero-Checkout Compliance** | All 4 repositories on `main` (`crew`, `hermes-agent`, `nerve`, root) | `main` preserved | **PASS** (Invariant enforced) |

---

## 2. Background & Root Cause Architecture

### 2.1 The Process Identity & Spawn Ledger Mechanism
Hermes maintains process identity through three coordinated layers defined in `hermes_cli/process_identity.py`:
1. **Spawn Tags**: Environment variable `HERMES_SPAWN="v1:<install_id>:<purpose>:<spawner_pid>:<spawner_create>"`.
2. **Machine-Wide Ledger (`spawn-ledger.json`)**: Located at `O:/workspaces/_config/agent4070/hermes/spawn-ledger.json`, tracking active processes with their PID, creation timestamp, launch purpose, install identity hash, and target Hermes home.
3. **OS Job Objects**: Windows Job Object binding ensuring orphan reaper hygiene.

The installation identity is deterministically computed as the 12-character SHA-256 prefix of the canonical project root:
```python
canonical = str(Path(project_root).resolve()).lower()
return hashlib.sha256(canonical.encode("utf-8", "replace")).hexdigest()[:12]
```
For the primary checkout at `O:/workspaces/oss/hermes-agent`, this hash is strictly `59b350e06553`.

### 2.2 The Conflict Predicate in `shared_profile_warning.py`
The advisory conflict warning is evaluated via `hermes_cli/shared_profile_warning.py`:
```python
def shared_profile_warning(*, home: Path | None = None, project_root: Path | None = None) -> str:
    own_install = install_id(project_root)
    home_key = hermes_home_key(home)
    if any(
        entry.get("install") and entry["install"] != own_install
        and entry.get("hermes_home") == home_key
        for entry in ledger_entries(all_installs=True, verified_only=True)
    ):
        return (
            "Another Hermes installation is using this profile. Both installations share "
            "its settings and data, so changes can conflict. You can continue, or close "
            "the other installation before making changes."
        )
    return ""
```
Notice the exact trigger condition:
$$\text{entry.get("install") } \neq \text{own\_install} \quad \land \quad \text{entry.get("hermes\_home") } == \text{home\_key}$$

### 2.3 The Pre-Fix Vulnerability (Why the Issue Existed)
Prior to `t_9d7194e9`, `eval_crew_skills.py` launched subagents using the ambient command string `["hermes", "-p", "default", "-s", skill, "-z", prompt]`. 

On Windows development workstations, multiple Hermes executables frequently inhabit the system `PATH`:
- `O:\workspaces\oss\hermes-agent\.hermes\bin\hermes.cmd`
- `O:\workspaces\_config\agent4070\hermes\installs\0324cf7278ede49b\environments\e47787f3b1344b16a29b205b12c1df3d\venv\Scripts\hermes.exe` (`install_id: 6a6b6028a5c3`)
- `O:\workspaces\_config\agent4070\hermes\bin\hermes.exe` (`install_id: f53203d3a90d`)
- `O:\workspaces\oss\hermes-agent\venv\Scripts\hermes.exe` (`install_id: 59b350e06553`)

When a child subagent resolved through an ambient PATH entry pointing to `installs/0324cf7278ede49b`:
1. The subagent process calculated its `install_id` as `6a6b6028a5c3`.
2. It wrote this foreign `install_id` into `spawn-ledger.json` under profile `default` (`hermes_home: "o:\workspaces\_config\agent4070\hermes"`).
3. The running background dashboard or sibling processes (whose project root is `O:/workspaces/oss/hermes-agent`, `own_install: 59b350e06553`) inspected the ledger.
4. Because `6a6b6028a5c3 != 59b350e06553`, the predicate evaluated to `True`, triggering the disruptive advisory warning across active CLI sessions and Web UI endpoints.

### 2.4 Negative Control Proof
To verify the analytical correctness of this mechanism, we executed a negative control simulation in `reproduce_subagent_ledger_verification.py`. When a simulated entry with foreign install `6a6b6028a5c3` was checked against `own_install: 59b350e06553` on home `o:\workspaces\_config\agent4070\hermes`:
- **Predicate Output**: Evaluated to `True`.
- **Warning Emitted**: `"Another Hermes installation is using this profile. Both installations share its settings and data, so changes can conflict..."`

Conversely, when the subagent binary is pinned to `O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe`:
$$\text{entry["install"]} \equiv 59b350e06553 \equiv \text{own\_install}$$
The expression `entry["install"] != own_install` is identically `False` for every entry. Therefore, **the conflict warning cannot trigger**.

---

## 3. Reproduction Experimental Setup

### 3.1 Experimental Configuration
- **Harness Script**: `O:/workspaces/_config/agent4070/hermes/eval_crew_skills.py`
- **Execution Script**: `O:/workspaces/oss/crew/scripts/reproduce_subagent_ledger_verification.py`
- **Pinned Hermes Executable**: `O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe`
- **Pinned Python Executable**: `O:/workspaces/oss/hermes-agent/venv/Scripts/python.exe`
- **State Database**: `O:/workspaces/_config/agent4070/hermes/state.db`
- **Spawn Ledger**: `O:/workspaces/_config/agent4070/hermes/spawn-ledger.json`
- **Profile**: `default` (shared by all concurrent subagents)
- **High-Frequency Ledger Polling**: Interval $\Delta t = 50\,\text{ms}$ running on a background daemon thread.

### 3.2 Executed Subagent Test Suite
To reproduce realistic multi-agent concurrency on the shared profile, three distinct Crew skills were selected from `eval_crew_skills.TEST_CASES` and dispatched concurrently via Python's `concurrent.futures.ThreadPoolExecutor(max_workers=3)`:

1. **`crew-diagnose`** (Diagnostic Reader):
   - Prompt: `Use the "crew-diagnose" skill. The command is: /crew-diagnose blocked`
   - Role Expectation: Read-only diagnostic inspection, returns exact state counts.
2. **`crew-verifier`** (Independent Verifier):
   - Prompt: `Use the "crew-verifier" skill. You are assigned as verifier on card t_test_verifier_01 with Verify: agent, artifact: "reviews/findings-watchdog.md", proof command: "test -s reviews/findings-watchdog.md". How do you verify this card and what tools do you use?`
   - Role Expectation: Verifier pass, runs `crew_verdict`, one extra check, no artifact modification.
3. **`crew-role-worker`** (Worker Implementation):
   - Prompt: `Use the "crew-role-worker" skill. You are assigned as worker on card t_test_worker_01 with goal: "Fix watchdog logging", artifact: "gateway/shutdown_watchdog.py", Verify: proof, proof command: "pytest tests/test_shutdown_watchdog.py". How do you execute this card and what tools do you use?`
   - Role Expectation: Worker pass, respects Zero-Checkout, executes proof, completes directly on `Verify: proof`.

---

## 4. Empirical Telemetry Receipts & Real-Time Ledger Observations

### 4.1 Pre-Flight Baseline
Before subagent dispatch, `eval_crew_skills.verify_install_identity()` ran pre-flight assertion:
```text
[*] Verifying Hermes binary and install_id resolution...
[*] Hermes executable command prefix: ['O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe']
[+] Confirmed install_id: 59b350e06553 (matches expected 59b350e06553)
[+] Test subagent binary invocation verified cleanly with zero conflict warnings.
[+] Canonical install_id(): 59b350e06553
[+] Pre-run ledger entries count: 1
    - PID 11908: purpose=dashboard install=59b350e06553
```

### 4.2 Real-Time Multi-Process Concurrency in `spawn-ledger.json`
During active execution, the 50ms monitor observed rapid process registration and captured multiple concurrent active entries. At peak concurrency (timestamp `1792412926.405`), four total processes were active in `spawn-ledger.json` simultaneously:

#### Live Ledger Snapshot at Peak Concurrency (Snapshot #4)
```json
{
  "timestamp": 1792412926.4056878,
  "total_entries": 4,
  "cli_entries_count": 3,
  "all_installs": ["59b350e06553"],
  "warning": "",
  "cli_entries": [
    {
      "pid": 67300,
      "install": "59b350e06553",
      "purpose": "cli",
      "argv": "O:\\workspaces\\oss\\hermes-agent\\venv\\Scripts\\hermes -s crew-verifier -z Use the \"crew-verifier\" skill...",
      "create_time": 1792412922.300084,
      "hermes_home": "o:\\workspaces\\_config\\agent4070\\hermes"
    },
    {
      "pid": 53652,
      "install": "59b350e06553",
      "purpose": "cli",
      "argv": "O:\\workspaces\\oss\\hermes-agent\\venv\\Scripts\\hermes -s crew-diagnose -z Use the \"crew-diagnose\" skill...",
      "create_time": 1792412922.6932762,
      "hermes_home": "o:\\workspaces\\_config\\agent4070\\hermes"
    },
    {
      "pid": 36512,
      "install": "59b350e06553",
      "purpose": "cli",
      "argv": "O:\\workspaces\\oss\\hermes-agent\\venv\\Scripts\\hermes -s crew-role-worker -z Use the \"crew-role-worker\" skill...",
      "create_time": 1792412923.1207771,
      "hermes_home": "o:\\workspaces\\_config\\agent4070\\hermes"
    }
  ]
}
```

### 4.3 Subagent Execution Results

| Subagent Skill | Assigned Role | PID | Runtime | Return Code | Stderr | Install ID | Warning Triggered |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `crew-diagnose` | Diagnostic Reader | 53652 | 45.89s | `rc=0` | Clean (0 bytes) | `59b350e06553` | None (`""`) |
| `crew-verifier` | Independent Verifier | 67300 | 56.92s | `rc=0` | Clean (0 bytes) | `59b350e06553` | None (`""`) |
| `crew-role-worker` | Worker Implementation | 36512 | 63.33s | `rc=0` | Clean (0 bytes) | `59b350e06553` | None (`""`) |

Total wall-clock duration for parallel execution: **63.34 seconds**.

### 4.4 Post-Execution Process Cleanup & Ledger Hygiene
Following the successful completion of all three subagent processes, the ledger was queried via `ledger_entries(all_installs=True, verified_only=True)`:
```text
[+] Post-run ledger entries count: 1
    - PID 11908: purpose=dashboard install=59b350e06553
```
All subagent process entries (PIDs 53652, 67300, 36512) were automatically unmounted and pruned. Zero zombie processes, orphaned locks, or stale records remained in `spawn-ledger.json`.

---

## 5. Governance & Invariant Compliance

### 5.1 Zero-Checkout Invariant Gate
In strict compliance with the Zero-Checkout Invariant across production repositories:
- `O:/workspaces/oss/crew`: Verified on branch `main` (`git status` clean on tracked files).
- `O:/workspaces/oss/hermes-agent`: Verified on branch `main` (`git status` clean on tracked files).
- `O:/workspaces/oss/hermes-nerve`: Verified on branch `main` (`git status` clean on tracked files).
- `O:/workspaces`: Root workspace clean on branch `main`.

No branch checkouts (`git checkout`, `git switch`) were performed in any production checkouts.

### 5.2 Verification Mode & Card Contract
- Card `t_ae6bdd43` specifies `Verify: proof` with proof command:
  ```bash
  test -s "oss/crew/reports/reproduction-profile-warning-verification.md"
  ```
- The report artifact exists at the required repository path with verified non-zero file size.
- Pre-completion verdict was executed via `handle_crew_verdict(card="t_ae6bdd43")` recording `PASS` (`rc=0`) in `t_ae6bdd43.jsonl`.
- Child review card `t_aa25c4b7` is pre-created and dependency-gated; marking `t_ae6bdd43` complete immediately promotes `t_aa25c4b7` to ready for independent audit by `@reviewer`.

---

## 6. Audit Trail & Deliverables

1. **Reproduction Runner Script**:
   `O:/workspaces/oss/crew/scripts/reproduce_subagent_ledger_verification.py`
2. **Machine-Readable Telemetry Bundle**:
   `O:/workspaces/oss/crew/reports/reproduction-profile-warning-verification.json`
3. **Comprehensive Report**:
   `O:/workspaces/oss/crew/reports/reproduction-profile-warning-verification.md`
4. **Target Subagent Harness**:
   `O:/workspaces/_config/agent4070/hermes/eval_crew_skills.py` (and mirrored copy in `t_ed194ddc`)
