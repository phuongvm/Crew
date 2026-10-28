# Independent Re-Review — ASUS-VB Crew Configuration and Parity

**Card:** `t_f5c35edc`
**Remediation reviewed:** `t_3964b75f`
**Reviewer:** Agent Reviewer
**Targets:** `O:/workspaces/_config/asus-vb/hermes`, `O:/workspaces/_config/agent4070/hermes`, and `O:/workspaces/oss/crew`
**Verdict:** **APPROVED**

## Executive finding

The remediation resolves the prior rejection. A fresh, read-only SHA-256 sweep derived from the current `install.py` manifest found **103 unique installed destinations**, **12 configured ASUS-VB homes (1,236/1,236 files)**, and **7 configured agent4070 homes (721/721 files)**. There are zero missing source or deployed files and zero deployed-file mismatches against current clean Crew `main` / `origin/main` at `41dfbd98a28f04f06d9eb3b807ddc2e8dae25c4b`. ASUS-VB also has zero mismatches against the agent4070 root deployment. The desktop plugin SHA-256 is identical across Crew, ASUS-VB, and agent4070: `a6a2191d4c5fa6c551052c9bb99366dfe61dd767ff2a8b281fc9a72a7b0f09a7`.

Both node-local cutover scripts now parameterize the SSH identity with `-GitSshKey` / `$env:HERMES_GIT_SSH_KEY`, contain no `id_rsa_phuongvm`, and retain the contracted main-branch, tracked-clean, immutable SHA, SHA-256, manifest, dry-run, profile-count, desktop-sync, and Commander-only restart gates. Root Crew configuration and scoped Git tracking pass. The production Crew checkout was independently observed clean on `main`, with `HEAD == origin/main == 41dfbd9` before this review artifact was authored in an isolated worktree.

## Scope and method

The audit was read-only against the two deployed Hermes trees, root `.gitignore`, Git tracking state, and the Crew checkout. Inventory was derived from current `install.py` (`PLUGIN_FILES`, `ROLE_FILES`, and `skill_names()`), deduplicated by destination. Files were compared as raw bytes with SHA-256. Audited configurations were not modified. This report and the required Updates Log entry were authored only in `O:/workspaces/.worktrees/wt-crew-parity-rereview` to preserve the Zero-Checkout invariant.

Required governance files `code-review-mandate/spec.md`, a project `AGENTS.md`, and a project `lessons-learned.md` are absent after bounded tracked-file search. The review therefore used the card contract, `CONTRIBUTING.md`, `openspec/specs/worktree-isolation-governance/spec.md`, the available native-tools architecture exploration, the current source/configuration, and the remediation report.

## Contract results

| Clause | Result | Independent evidence |
|---|---:|---|
| 12 configured ASUS-VB profile homes | PASS | Root default plus 11 `profiles/*` directories containing `config.yaml`; unconfigured `profiles/default` is excluded. |
| 103 unique destinations per home; 1,236 ASUS-VB files | PASS | `manifest_unique_destinations=103`; `asus_configured_homes=12`; `asus_expected_files=1236`; `source_missing=0`; `asus_missing=0`. |
| ASUS-VB parity with clean Crew source | PASS | `asus_vs_repo_mismatch=0` across all 1,236 destinations. |
| agent4070 parity with clean Crew source | PASS | Seven configured homes, 721 expected files, `agent4070_missing=0`, `agent4070_vs_repo_mismatch=0`. |
| ASUS-VB parity with agent4070 deployment | PASS | `asus_vs_agent_root_mismatch=0` across all 1,236 ASUS-VB destinations. |
| Desktop plugin parity | PASS | Crew = ASUS-VB = agent4070 = `a6a2191d…f09a7`. |
| ASUS-VB `config.yaml` Crew wiring | PASS | `plugins.enabled` includes `crew`; `allow_tool_override: false`; `kanban.dispatch_in_gateway`, `review_dispatch`, and orchestration settings are enabled; `crew.roles_path`, `source_dir`, and `board` are configured at lines 1481–1484. |
| agent4070 `config.yaml` Crew wiring | PASS | Equivalent plugin/tool override, Kanban, and root `crew` wiring; root block at lines 1530–1533. |
| Parameterized cutover scripts | PASS | Both scripts: `GitSshKey = $env:HERMES_GIT_SSH_KEY`; missing-key refusal; zero `id_rsa_phuongvm`; expected profile counts 12/7; required safety and parity gates present. |
| Scoped Git tracking and `.gitignore` | PASS | All 1,236 expected ASUS-VB profile artifacts tracked; `tracked_crew_total=1240`; config, desktop plugin/marker, and cutover script tracked. `git check-ignore -v` confirms backup and Crew runtime-state rules at `.gitignore:86,127,131`. |
| Clean Crew checkout on current `origin/main` | PASS | Independent pre-artifact state: branch `main`; `HEAD == origin/main == 41dfbd98…`; `status --porcelain` empty. |
| Zero-Checkout branch gate | PASS | `O:/workspaces`, Crew, Hermes Agent, and Hermes Nerve all reported branch `main`; the review used a dedicated Crew worktree. |

## Two-axis review

### Standards / Fowler lens

**Documented standards:** PASS for the contracted remediation. The prior hard-coded user-specific SSH-key path is removed, and the Crew primary checkout was clean on `main` / `origin/main`. The service scripts and deployment report necessarily identify the node-local Windows targets named by this infrastructure card; these paths do not enter the portable Crew plugin manifest and are treated as card-required deployment evidence rather than a new plugin portability regression.

**Judgment-call smells (advisory, non-blocking):** the two 268-line node-local cutover scripts duplicate most operational logic, and each script combines repository synchronization, manifest extraction, backup/deployment, desktop synchronization, and optional daemon lifecycle. This is possible **Duplicated Code / Shotgun Surgery / Divergent Change**, but it predates and is outside the narrowly contracted parity-and-key remediation. No new abstraction was required by this card.

### Spec-fidelity lens

PASS. Every acceptance clause is present and independently evidenced: 12 × 103 ASUS-VB files; 7 × 103 agent4070 files; zero SHA-256 mismatches to current Crew; zero ASUS-VB-to-agent4070 root mismatches; desktop parity; Crew config wiring; parameterized cutover; scoped tracking/ignore behavior; and a clean Crew `main` equal to `origin/main` at the audited point. No functional scope creep was found.

## Operational advisories (not acceptance blockers)

1. Gateway and Dashboard were not restarted by the remediation or this review. Those remain Commander-only actions; deployed files are at parity, but running processes load them only after the Commander-approved restart.
2. The node-local cutover script still contains `git merge --ff-only` for an owner-controlled live cutover. The active card and OpenSpec branch-position requirement are satisfied, but the newer workspace-wide governance reserves production-checkout fast-forwarding for the Commander/offline cutover workflow. Reviewers and workers must not invoke it.
3. The root `O:/workspaces` repository contains unrelated outstanding changes and a stale Crew gitlink outside this card's Crew-cleanliness clause. This review does not classify the entire root monorepo as clean.

## Evidence receipt

```text
CHECK manifest_103=PASS
CHECK asus_12_homes=PASS
CHECK asus_1236_files=PASS
CHECK agent_7_homes=PASS
CHECK all_sources_present=PASS
CHECK asus_all_present=PASS
CHECK asus_repo_parity=PASS
CHECK asus_agent_root_parity=PASS
CHECK agent_all_present=PASS
CHECK agent_repo_parity=PASS
CHECK desktop_parity=PASS
CHECK scripts_parameterized_and_guarded=PASS
CHECK all_expected_asus_files_tracked=PASS
CHECK tracked_crew_total_at_least_1240=PASS
CHECK special_files_tracked=PASS
CHECK protected_repos_on_main=PASS
CHECK crew_clean_equal_origin_main=PASS
manifest_unique_destinations=103
asus_configured_homes=12 asus_expected_files=1236 asus_missing=0
asus_vs_repo_mismatch=0 asus_vs_agent_root_mismatch=0
agent4070_configured_homes=7 agent4070_expected_files=721
agent4070_missing=0 agent4070_vs_repo_mismatch=0
desktop_sha256=a6a2191d4c5fa6c551052c9bb99366dfe61dd767ff2a8b281fc9a72a7b0f09a7
tracked_expected=1236 tracked_missing=0 tracked_crew_total=1240
crew_branch=main
crew_head=41dfbd98a28f04f06d9eb3b807ddc2e8dae25c4b
crew_origin_main=41dfbd98a28f04f06d9eb3b807ddc2e8dae25c4b
crew_porcelain_lines=0
```

The composite audit initially printed two heuristic FAIL labels because its string checks expected nonexistent literal names (`dispatch_enabled`) and literal `.gitignore` phrases. Direct source evidence corrects those probe defects: the actual keys are `kanban.dispatch_in_gateway` / `review_dispatch`, root Crew wiring exists on both nodes, and `git check-ignore -v` proves wildcard rules at `.gitignore:86,127,131` cover backups and runtime state. These were audit-probe defects, not configuration defects.

**Final verdict: APPROVED.**
