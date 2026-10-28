# Remediation — ASUS-VB Crew Parity, Cutover SSH Key, Clean `oss/crew`

**Card:** `t_3964b75f` (Verify: proof)  
**Remediates:** `reviews/findings-asus-vb-crew-config-review.md` (card `t_a45fe168`, REJECTED)  
**Baseline commit:** `7b069d8819e847412c8aa084fb19e22e1837872d` (`origin/main` when the cutover ran; this docs commit sits on top of it and touches no deployed file)  
**Date:** 2026-10-28

## Outcome per finding

| # | Finding (t_a45fe168) | Remediation | Status |
|---|---|---|---|
| 1 | Node parity false: ASUS-VB vs agent4070, 132 instances / 11 paths, desktop differs | Both nodes redeployed from the same baseline with `apply-live-crew-cutover.ps1 -SkipRepoSync -ExpectedSha 7b069d8` | FIXED: 0 mismatches |
| 2 | Immutable-baseline parity false: 492 instances / 41 paths vs `3757fde` | Baseline moved to clean `origin/main` `7b069d8` (see #3). 36 of the 41 paths differed only by CRLF conversion in the live checkout (`core.autocrlf=true` overriding `.gitattributes eol=lf`); those 106 tracked files were checked out again as LF before the cutover | FIXED: 0 mismatches vs git blobs |
| 3 | Baseline identity unstable (live `1507553` vs gitlink `3757fde`) | Card re-scoped to current `origin/main`. Live checkout HEAD == `origin/main` == `7b069d8`; manifest and blobs come from that commit | FIXED |
| 4 | Production `oss/crew` checkout dirty | In-flight WIP parked on its own branch (below). Live checkout restored to `origin/main` | FIXED: `status --porcelain` empty |
| 5 | Machine-specific SSH key path in cutover script | `-GitSshKey` parameter, default `$env:HERMES_GIT_SSH_KEY`, on both nodes' scripts | FIXED |
| 6 | Original proof structurally invalid (13 dirs / 109 entries) | This card's proof filters by `config.yaml` and deduplicates destinations (12 × 103) | N/A (proof-side) |

## 1. `oss/crew` clean on `origin/main`

- Live checkout: branch `main`, `HEAD == origin/main == 7b069d8` (Zero-Checkout: no `checkout` or `switch` was run in the live checkout).
- The uncommitted WIP from another writer (the `fix-crew-open-chat-button` Open-chat fixes and the `crew-shareable-card-links` / `fix-crew-open-chat-button` OpenSpec artifacts) was **parked, not dropped**:
  - branch `wip/crew-inflight-20261028`, commit `1774c28` (parent `7b069d8`)
  - worktree `O:/workspaces/.worktrees/wt-crew-inflight-wip`
  - 11 modified + 13 added files (24 total; `agent_share.md` is handled separately below). Each one was confirmed byte-identical to the live copy with `git hash-object` (0 differences) before the live copies were restored.
  - Patch and tar snapshots of the pre-clean state are kept in the coder scratch dir.
- The reviewer docs (the `agent_share.md` Updates Log and `findings-asus-vb-crew-config-review.md`) and this report are committed to `main` from worktree `wt-crew-parity-docs`. They are not left uncommitted in the live checkout.
- The WIP owner resumes from `wip/crew-inflight-20261028` (rebase onto `main`).

## 2. Cutover SSH key parameterized

Both `_config/asus-vb/hermes/services/apply-live-crew-cutover.ps1` and `_config/agent4070/hermes/services/apply-live-crew-cutover.ps1`:

```powershell
[string]$GitSshKey = $env:HERMES_GIT_SSH_KEY,
...
if ($GitSshKey) {
    if (-not (Test-Path -LiteralPath $GitSshKey -PathType Leaf)) { "[REFUSED] SSH key not found"; exit 1 }
    $env:GIT_SSH_COMMAND = "ssh -i `"$GitSshKey`" -o IdentitiesOnly=yes"
}
```

When neither the parameter nor the variable is set, git falls back to an inherited `GIT_SSH_COMMAND`, `core.sshCommand` or `~/.ssh/config`. The script no longer has a user-specific default.

| Check | Result |
|---|---|
| hard-coded key string in either script | 0 occurrences |
| PowerShell `ParseFile` errors | 0 / 0 |
| `HERMES_GIT_SSH_KEY=<missing>` `-DryRun` | `[REFUSED] SSH key not found`, rc=1 |
| `-GitSshKey <missing>` `-DryRun` | `[REFUSED]`, rc=1 |
| `HERMES_GIT_SSH_KEY=<real key>` `-DryRun` (real `git fetch origin main`) | rc=0, `Live checkout already at origin/main (7b069d8)`, `updated=0` |

## 3. Cutover and parity

| Node | Command | Result |
|---|---|---|
| asus-vb | `apply-live-crew-cutover.ps1 -SkipRepoSync -ExpectedSha 7b069d8…` | rc=0, 12 profiles, 588 updates (49 × 12), each profile `103 files at parity`, desktop root synced |
| agent4070 | same | rc=0, 7 profiles, 340 updates, each profile `103 files at parity`, desktop root synced |

Replaced files were backed up to `<profile>/backups/crew-cutover-20261028-1834xx/` (gitignored).

SHA-256 sweep, comparing installed files with the git blobs at `7b069d8`:

```text
pairs 103 asus_homes 12 asus_cmp 1236 asus_vs_7b069d8_mismatch 0
a4070_homes 7 a4070_cmp 721 a4070_vs_7b069d8_mismatch 0
desktop a6a2191d4c5fa6c551052c9bb99366dfe61dd767ff2a8b281fc9a72a7b0f09a7 True   (7b069d8 == agent4070 == asus-vb)
```

## Not done / owner actions

- **No Gateway or Dashboard restart was performed** (Commander-only). The deployed `dashboard/dist/index.js` and the plugin scripts changed on both nodes. The Hermes Dashboard and Gateway on agent4070 pick them up at the next Commander-initiated restart.
- The deployed plugin code is now `origin/main` `7b069d8`. That code does **not** include the uncommitted Open-chat WIP that had been hand-synced into agent4070 runtime (17:14 / 18:1x). That WIP lives only on `wip/crew-inflight-20261028` until its owner lands it.
- Updating the root `O:/workspaces` gitlink for `oss/crew` (`3757fde` → `7b069d8`) and committing the two cutover scripts happen in the root repository's own worktree flow. The real ASUS-VB host needs fleet-sync followed by this cutover.
