# Independent Review — ASUS-VB Crew Configuration and Parity

**Card:** `t_a45fe168`  
**Reviewer:** Agent Reviewer  
**Target:** `O:/workspaces/_config/asus-vb/hermes`  
**Required baselines:** `O:/workspaces/_config/agent4070/hermes` and `O:/workspaces/oss/crew` at `3757fde`  
**Verdict:** **REJECTED**

## Executive finding

ASUS-VB has the expected 12 configured profile homes and all 1,236 unique Crew files are present, tracked, and internally consistent. Its root Crew/Kanban configuration, cutover guard structure, and scoped Git tracking pass inspection. Acceptance nevertheless fails against both contracted references: a fresh byte comparison finds **132 profile-file mismatches** against the current agent4070 root baseline (11 unique destinations repeated across 12 configured homes) and **492 profile-file mismatches** against immutable `oss/crew@3757fde` (41 unique destinations repeated across 12 homes). The ASUS-VB desktop plugin matches `3757fde` byte-for-byte but differs from current agent4070. The live `oss/crew` checkout is `1507553b2a8285d04702a93106365cc29cd74885`, while the card and root Git gitlink require `3757fdefa02a922ced1447108fdc31912510e85c`; it is also dirty with tracked and untracked concurrent changes, so only the branch-position portion of Zero-Checkout passes.

## Scope and method

The audit was performed read-only against:

- `O:/workspaces/_config/asus-vb/hermes`
- `O:/workspaces/_config/agent4070/hermes`
- `O:/workspaces/oss/crew`
- `O:/workspaces/.gitignore`

The profile/file inventory was derived from `install.py` (`PLUGIN_FILES`, `skill_names()`, and `ROLE_FILES`), deduplicated by destination path. SHA-256 comparisons read the files as bytes. No audited configuration was modified.

## Contract results

| Clause | Result | Evidence |
|---|---:|---|
| 12 configured profile homes | PASS | Root default plus `aziz`, `coder`, `designer`, `lambert`, `leader`, `nazla`, `productservices`, `pupu`, `qa`, `researcher`, and `reviewer` = 12. `profiles/default` has no `config.yaml` and is correctly excluded as an unconfigured stub directory. |
| 103 unique Crew files per profile, 1,236 total | PASS | `unique_manifest_files=103`; `12 × 103 = 1236`; `missing=0`. |
| SHA-256 parity with agent4070 | **FAIL** | Fresh comparison across all 12 configured homes × 103 files finds `MISMATCHES=132`: 11 unique destinations differ in all 12 homes. |
| SHA-256 parity with `oss/crew@3757fde` | **FAIL** | Direct immutable-tree comparison finds `MISMATCHES=492`: 41 unique destinations differ in all 12 homes. |
| Desktop plugin parity | **PARTIAL** | ASUS-VB: `5aca7f06bf70ae8c48ab699b6f34e1b16b8d488d8ec22da6507e85dd66721314`; agent4070: `8588873da80aaa3d93c17656565f80acb7ef593270294d76fc2c8467c3939eb7`; immutable `3757fde`: `5aca7f06bf70ae8c48ab699b6f34e1b16b8d488d8ec22da6507e85dd66721314`. ASUS-VB matches the immutable baseline but not current agent4070. |
| Crew checkout identity | **FAIL** | Live `oss/crew` HEAD is `1507553b2a8285d04702a93106365cc29cd74885`; the card and root Git gitlink still identify `3757fdefa02a922ced1447108fdc31912510e85c`. |
| Git tracking | PASS | All 1,236 expected profile artifacts are tracked (`missing_tracked=0`); Crew-containing paths total 1,240, comprising the profile artifacts plus desktop plugin, marker, and cutover references. Root `config.yaml`, desktop plugin/marker, and cutover script are tracked. Scoped Git status is clean (`HEAD == origin/main == 0fa7dd22`). |
| Root `config.yaml` | PASS | `plugins.enabled` contains `crew`; `plugins.entries.crew.allow_tool_override=false`; `crew.roles_path`, `crew.source_dir`, and `crew.board` resolve to ASUS-VB/Crew; dispatch/review/orchestrator settings are enabled as contracted. |
| Cutover script | PASS | Structural checks found all required gates: main branch, tracked-clean check, `merge --ff-only`, `ExpectedSha`, SHA-256, expected 12 profiles, manifest-derived file list, desktop sync, dry-run, and no automatic Gateway/Dashboard restart. `apply-live-crew-cutover.ps1` correctly reflects 12 profiles. |
| Zero-Checkout invariant | **PARTIAL / FAIL** | All four protected repositories report branch `main`, but `O:/workspaces/oss/crew` is dirty with 10 tracked modifications and several untracked concurrent artifacts. The branch-position gate passes; the clean-production-checkout requirement in `openspec/specs/worktree-isolation-governance/spec.md:15` does not. |

## Two-axis review

### Standards / Fowler lens

- **Hard standard:** `services/apply-live-crew-cutover.ps1:37` embeds a user-specific SSH key path, contrary to `CONTRIBUTING.md:53` (`Never put machine-specific strings ... in code, tests or docs`). Its node-local purpose does not override the written repository standard.
- **Hard standard:** the production `oss/crew` checkout is dirty. `openspec/specs/worktree-isolation-governance/spec.md:15` requires the primary working tree to remain clean on `origin/main`; branch `main` alone is insufficient.
- **Judgment-call smell — Divergent Change:** the cutover script combines repository synchronization, manifest extraction, profile deployment/backups, desktop registration, and daemon management. Dry-run and deterministic gates reduce operational risk but not the concentration of responsibilities.

### Spec-fidelity lens

- PASS: 12 configured homes, 103 unique destinations each, 1,236 files present, zero internal ASUS-VB drift.
- PASS: `config.yaml`, cutover structure, scoped ASUS-VB Git tracking, and `.gitignore`.
- **FAIL:** parity against current agent4070: 132 profile-file mismatches (11 unique destinations × 12 homes) plus desktop root mismatch.
- **FAIL:** direct immutable-baseline parity: 492 profile-file mismatches (41 unique destinations × 12 homes) against `oss/crew@3757fde`; the desktop plugin alone matches that baseline.
- **FAIL:** immutable Crew baseline identity: live checkout `1507553` differs from required/root-gitlink `3757fde`.
- **FAIL:** production checkout cleanliness: `oss/crew` is on `main` but dirty.
- **WARNING:** original proof enumerates 13 directories because it includes unconfigured `profiles/default`, and 109 entries because six skill destinations are duplicated; owner-approved revised proof now validates the review artifact rather than the malformed parity expression.

## Critical findings and remediation

1. **CRITICAL — node parity is false.** The current agent4070 root differs from ASUS-VB in 11 unique destinations across all 12 configured homes. Decide the authoritative release state, deploy it to both nodes, then rerun full parity.
2. **CRITICAL — immutable baseline parity is false.** ASUS-VB differs from `oss/crew@3757fde` in 41 unique installed destinations across all 12 homes (492 instances), even though its desktop plugin matches that baseline. Synchronize all manifest-derived artifacts from one immutable commit.
3. **CRITICAL — baseline identity is unstable.** Pin the manifest and source blobs to one immutable commit, or rescope the card to current Crew HEAD and redeploy both node baselines.
4. **HIGH — production checkout is dirty.** Restore the `oss/crew` primary checkout to the mandated clean-on-main state through the owner-controlled workflow; do not mutate it from this verifier task.
5. **HIGH — machine-specific path violates repository policy.** Replace the hard-coded SSH key path with a node-local environment/config input in a separate implementation card.
6. **WARNING — original proof command is structurally invalid.** Filter profiles by `config.yaml` and deduplicate installed destination paths; the owner-confirmed revised proof correctly limits itself to review-artifact existence and explicit verdict.

## Not reviewed

The mutating cutover script was not executed because the card prohibits audited configuration changes. Gateway/Dashboard restarts were not performed; those are Commander-only operations.

## Evidence receipt

```text
VALID_PROFILE_HOMES=12 VALID_UNIQUE_FILES=1236
ASUS_INTERNAL_DRIFT=0
CURRENT_ASUS_VS_AGENT4070_MISMATCHES=132 UNIQUE_PATHS=11
ASUS_VS_3757FDE_MISMATCHES=492 UNIQUE_PATHS=41
asus_desktop_sha256=5aca7f06bf70ae8c48ab699b6f34e1b16b8d488d8ec22da6507e85dd66721314
agent4070_desktop_sha256=8588873da80aaa3d93c17656565f80acb7ef593270294d76fc2c8467c3939eb7
baseline_3757fde_desktop_sha256=5aca7f06bf70ae8c48ab699b6f34e1b16b8d488d8ec22da6507e85dd66721314
branches={"O:/workspaces":"main","O:/workspaces/oss/crew":"main","O:/workspaces/oss/hermes-agent":"main","O:/workspaces/oss/hermes-nerve":"main"}
CREW_PRIMARY_DIRTY_TRACKED=10
CREW_HEAD=1507553b2a8285d04702a93106365cc29cd74885
ROOT_CREW_GITLINK=3757fdefa02a922ced1447108fdc31912510e85c
GIT_EXPECTED_PROFILE_ARTIFACTS=1236 GIT_EXPECTED_MISSING=0 GIT_CREW_TRACKED_TOTAL=1240
```

Reproduction: `python audit_asus_vb_crew.py` from this card's Kanban scratch workspace; complete output is `audit.json` there.

**Final verdict: REJECTED.**
