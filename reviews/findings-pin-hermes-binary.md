# Independent Review: Pin Absolute Hermes Binary in Crew Evaluation Harness

**Card:** `t_ba475a34`  
**Remediation reviewed:** `t_9d7194e9`  
**Reviewer:** Agent Reviewer  
**Date:** 2026-10-19  
**Verdict:** **APPROVED**

## Summary

| Severity | Count |
|---|---:|
| CRITICAL | 0 |
| WARNING | 0 |
| INFO | 1 |

The two required harness copies are byte-identical and resolve subagent execution to the explicit repository Hermes executable, not an ambient `hermes` command. A fresh `--verify-only` execution returned exit code 0, resolved `install_id` `59b350e06553`, and emitted no conflict warning. The post-run `spawn-ledger.json` contained one unique install identity, `59b350e06553`; therefore the card's binary-pinning and bounded process-isolation acceptance criteria are satisfied.

## Scope

### Files reviewed

- `O:/workspaces/_config/agent4070/hermes/kanban/boards/crew/workspaces/t_ed194ddc/eval_crew_skills.py`
- `O:/workspaces/_config/agent4070/hermes/eval_crew_skills.py`
- `O:/workspaces/_config/agent4070/hermes/spawn-ledger.json`
- `O:/workspaces/oss/crew/REFERENCE.md`
- `O:/workspaces/oss/crew/openspec/changes/archive/worktree-isolation-governance/specs/worktree-isolation-governance/spec.md`
- `O:/workspaces/oss/crew/openspec/changes/archive/worktree-isolation-governance/design.md`
- `O:/workspaces/ai_agents/collaboration/openspec/specs/code-review-mandate/spec.md`
- `O:/workspaces/ai_agents/collaboration/docs/lessons/lessons-learned.md`
- `O:/workspaces/openspec/workspace/sessions/agent_share.md`

### SDLC layers reviewed

- Specifications and card contract
- Architecture and process isolation
- Python implementation
- Runtime verification
- Zero-Checkout governance

## Evaluation by SDLC Layer

### Specifications

The task requires a clear verdict on binary path pinning and process isolation. The implementation satisfies this contract by centralizing command construction in `get_hermes_cmd()` and routing both the pre-flight version invocation and every subagent launch through that resolver (`eval_crew_skills.py:30-42`, `:70-75`, `:138-152`). Both input copies are identical.

### Architecture

The command path is no longer dependent on ambient `PATH`. When present, `O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe` is selected first; the repository venv Python module invocation is the secondary path, with `sys.executable -m hermes_cli.main` as the final fallback (`eval_crew_skills.py:24-42`). This is consistent with the task contract and isolates spawned evaluations to a known Hermes installation on the reviewed host.

The Zero-Checkout gate passed: all four protected production checkouts remained on `main`; every listed non-primary Crew, Hermes-Agent, and Hermes-Nerve branch was attached to a worktree under `O:/workspaces/.worktrees/`.

### Code

No blocking defects were found. The implementation:

1. Pins `HERMES_BIN` and `HERMES_PYTHON` to the repository venv (`:24-27`).
2. Uses argument lists rather than shell command strings (`:30-42`, `:146-152`).
3. Checks the resolved process identity against the expected install ID (`:45-67`).
4. Rejects conflict indicators in combined stdout/stderr (`:69-83`).
5. Applies the resolver to all six subagent executions (`:138-152`).

### Tests and Runtime Evidence

One consolidated independent extra check compared both declared input files, loaded the resolver, executed `--verify-only`, and inspected the resulting spawn ledger. Raw output:

```text
INPUT O:\workspaces\_config\agent4070\hermes\kanban\boards\crew\workspaces\t_ed194ddc\eval_crew_skills.py bytes=16746 sha256=dcd72d2c4a836977e88b9f202f6cb52c6bdb2acf90d5f19a178de8ef778a0372
INPUT O:\workspaces\_config\agent4070\hermes\eval_crew_skills.py bytes=16746 sha256=dcd72d2c4a836977e88b9f202f6cb52c6bdb2acf90d5f19a178de8ef778a0372
INPUTS_IDENTICAL True
RESOLVED_CMD ["O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe", "--version"]
VERIFY_ONLY_RC 0
VERIFY_ONLY_STDOUT_BEGIN
[*] Verifying Hermes binary and install_id resolution...
[*] Hermes executable command prefix: ['O:/workspaces/oss/hermes-agent/venv/Scripts/hermes.exe']
[+] Confirmed install_id: 59b350e06553 (matches expected 59b350e06553)
[+] Test subagent binary invocation verified cleanly with zero conflict warnings.
[✓] Pre-flight verification completed successfully.
VERIFY_ONLY_STDOUT_END
VERIFY_ONLY_STDERR_BEGIN

VERIFY_ONLY_STDERR_END
LEDGER_INSTALL_IDS ["59b350e06553"]
LEDGER_ROW {"argv": "-c dashboard --host 0.0.0.0 --port 9119 --no-open", "install": "59b350e06553", "isolated": false, "pid": 11908, "profile": "", "purpose": "dashboard"}
LEDGER_ROW {"argv": "O:\\workspaces\\oss\\hermes-agent\\venv\\Scripts\\hermes -z Describe crew_verdict tool", "install": "59b350e06553", "isolated": false, "pid": 4236, "profile": "", "purpose": "cli"}
ZERO_INSTALL_ID_CONFLICTS True
```

The consolidated check exited `0`.

### DevOps / Process Isolation

At the bounded post-run observation point, the active ledger contained two rows and exactly one unique installation identity. No `install_id` conflict existed. This is a point-in-time process-isolation conclusion, not a claim that historical or future ledger states can never contain another install identity.

## Findings

### INFO I-01 — Isolation evidence is intentionally bounded

- **Spec reference:** Card acceptance criterion; code-review mandate Scope/No-Hiding requirement.
- **File/line:** `eval_crew_skills.py:45-83`; `spawn-ledger.json` live post-run state.
- **Evidence:** Fresh verifier execution returned `VERIFY_ONLY_RC 0`; the ledger reported `LEDGER_INSTALL_IDS ["59b350e06553"]` and `ZERO_INSTALL_ID_CONFLICTS True`.
- **Impact:** None blocking. The evidence establishes the reviewed run and current active ledger state, not a permanent guarantee.
- **Resolution:** No change required.

## Not Reviewed

- The full six-subagent evaluation suite was not rerun; the card concerns binary selection and install-identity isolation, and `--verify-only` directly exercises that pre-flight contract without launching six long-lived model sessions.
- Functional correctness of the six Crew skill scoring scenarios is outside this remediation's scope.
- Historical terminated ledger entries are not represented in the active JSON ledger and were not reconstructed.

## Final Verdict

**APPROVED.** Binary path pinning is present and used at every Hermes launch site in both identical input copies. Fresh runtime verification exited 0 and the active post-run ledger contained zero conflicting installation identities. Zero-Checkout governance also passed.
