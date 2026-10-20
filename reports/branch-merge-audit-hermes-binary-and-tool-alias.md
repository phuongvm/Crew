# Branch merge audit: `origin/fix/hermes-binary-resolution` and `origin/fix/tool-card-alias`

- **Card:** t_4dfe1c60 (Role: worker, Verify: dual) · **For:** Commander
- **Repo:** `O:/workspaces/oss/crew` (submodule; gitdir `O:/workspaces/.git/modules/oss/crew`)
- **Audited:** 2026-10-20, after `git fetch --all --prune` (origin = `phuongvm/Crew`, upstream = `macd2/Crew`)
- **Method:** read-only. No checkout, merge, cherry-pick or push was performed. Production checkout stayed on `main` at `ed42341`. The only working-tree change is this report itself, which is untracked and not committed: `git status --short` → `?? reports/branch-merge-audit-hermes-binary-and-tool-alias.md`. No tracked file was modified and nothing is staged.

## 1. Verdict (TL;DR)

| Branch | Tip | Commits not on `main` | Content already on `main`? | Upstream PR | Needs integration? |
|---|---|---|---|---|---|
| `origin/fix/hermes-binary-resolution` | `1b233f9` | 1 (`1b233f9`) | **Yes — 100%.** Its change was re-applied inside `daa9340` (byte-identical +/- lines) | macd2/Crew **#18 OPEN**, maintainer asked for one change | **No** for `main`. **Yes** for upstream: PR #18 needs the requested fix pushed |
| `origin/fix/tool-card-alias` | `52e3b74` | 1 (`52e3b74`) | **No.** Not on `main` in any form | macd2/Crew **#17 CLOSED, not merged** (rejected by design) | **Do NOT integrate** (would go against upstream 0.9.14). A **separate skills defect** on `main` was found instead — see §4 |

Neither branch tip is an ancestor of `main`. `git cherry` marks both commits `+` because patch-ids differ. For hermes-binary the patch-id differs only because the change was folded into a larger commit, not because the code differs.

## 2. Refs and merge-base

| Ref | SHA |
|---|---|
| `main` = `origin/main` | `ed423410b62948bb1a35bd97efa4b088fc3620ac` (2026-10-20 08:21 +0700, merge of upstream/main via sync/upstream-main-daily) |
| `upstream/main` | `92053331fe1ea0da82d3a9c4a4962c6e806dc851` (`main...upstream/main` = 66 / 0 → main has all of upstream) |
| `origin/fix/hermes-binary-resolution` (= local branch) | `1b233f9a2f64e93eb62d479a000b798c5e607727` |
| `origin/fix/tool-card-alias` (= local branch, worktree `O:/workspaces/.worktrees/wt-crew-tool-card-alias`) | `52e3b74407bbd4485f68b0ad423f98c40b320d2b` |

```
$ git merge-base main origin/fix/hermes-binary-resolution
fe602d8aa4f430ca315dec25338bf5a59f6c4427
$ git merge-base main origin/fix/tool-card-alias
fe602d8aa4f430ca315dec25338bf5a59f6c4427
$ git merge-base upstream/main origin/<either branch>
fe602d8aa4f430ca315dec25338bf5a59f6c4427
```

The merge-base `fe602d8` is upstream's `crew 0.9.13: the roles call crew's functions as tools, not through a shell line (idea: #16)` (2026-10-18 20:35 +0200). Both branches are single-commit topic branches cut from upstream 0.9.13.

```
$ git rev-list --left-right --count main...origin/fix/hermes-binary-resolution
69	1
$ git rev-list --left-right --count main...origin/fix/tool-card-alias
69	1
$ git merge-base --is-ancestor origin/fix/hermes-binary-resolution main  → no
$ git merge-base --is-ancestor origin/fix/tool-card-alias main           → no
$ git cherry -v main origin/fix/hermes-binary-resolution
+ 1b233f9a2f64e93eb62d479a000b798c5e607727 fix(windows): resolve checkout hermes.exe launcher and ignore isolated PM venvs
$ git cherry -v main origin/fix/tool-card-alias
+ 52e3b74407bbd4485f68b0ad423f98c40b320d2b fix(tools): accept card_id alias for card in crew_verdict, crew_diagnose, and crew_progress
```

Trial merges (`git merge-tree --write-tree`, nothing written to refs) both exit 0 with **no conflicts**: hermes-binary → tree `5e674da…`, tool-card-alias → tree `797039f…`.

> **Note:** `git diff --stat main origin/<branch>` (two-dot) shows ~267 files / −47k lines. That is only the 69 newer main commits the branch lacks. The branch's own change (`git diff main...origin/<branch>`, three-dot) is 2 files each, listed below.

## 3. `origin/fix/hermes-binary-resolution` — already landed (equivalent content)

### 3.1 Branch commit
`1b233f9` · Phuong Lambert · 2026-10-19 20:20:53 +0700 · `fix(windows): resolve checkout hermes.exe launcher and ignore isolated PM venvs`

```
scripts/crew_card.py               | 31 ++++++++++++++++++++++++++-----
tests/test_crew_windows_support.py | 20 +++++++++++++++++++-
```
- `hermes_exe()`: try the checkout launcher (`<root>/.hermes/bin/hermes.exe`, `<root>/bin/hermes.exe`) first, then `<home>/bin/hermes.exe`, then the venv beside Hermes's python — skipping any python under `…\installs\…` (PM package environments, #124627).
- `hermes_root()`: first tries `hermes_constants.PROJECT_ROOT`.
- New test `test_hermes_exe_prefers_checkout_launcher_and_ignores_pm_installs`, plus a `hermes_exe` mock in the existing `hermes_bin` test.

### 3.2 Where it landed on `main`
`daa9340` · Phuong Lambert · 2026-10-19 20:27:41 +0700 (7 minutes later) · `feat(windows,skills): resolve checkout hermes launcher, isolate PM venvs, and update 5-mode verification docs`. Ancestor of `main`: **yes**. This 23-file commit bundles the same two-file change with skills docs, reports and eval scripts. That bundling is why `git cherry` gives a different patch-id.

Evidence that the content is identical:
```
$ git log -S'os.sep + "installs" + os.sep' main          → daa9340 (only commit)
$ git log -S'test_hermes_exe_prefers_checkout_launcher' main → daa9340 (only commit)
$ diff <(+/- lines of 1b233f9 for crew_card.py + test_crew_windows_support.py) \
       <(+/- lines of daa9340 for the same two files)      → IDENTICAL +/- lines
$ diff branch:hermes_exe()  main:hermes_exe()              → IDENTICAL
$ diff branch:hermes_root() main:hermes_root()             → IDENTICAL
$ diff branch:test_hermes_exe_prefers…  main:same test     → IDENTICAL
```
On `main` today: `scripts/crew_card.py:228` (`hermes_exe`), `scripts/crew_card.py:1255` (`hermes_root` with the `PROJECT_ROOT` block at 1257–1263), `tests/test_crew_windows_support.py:86`.

### 3.3 Upstream PR status
**macd2/Crew #18** — OPEN, `MERGEABLE`, head `1b233f9`, base `main`, opened 2026-10-19T13:21:29Z, not merged. Maintainer (macd2, 2026-10-19T16:04Z) review:
> The `hermes_exe()` change is right … **Needs one change before merge:** the `hermes_constants.PROJECT_ROOT` block in `hermes_root()` is dead code: `hermes_constants` has no `PROJECT_ROOT` … If the name ever appears, the block would silently outrank `HERMES_AGENT_DIR` / `HERMES_SRC`. **Fix:** drop the block and the docstring change; keep the `hermes_exe()` change and the new test as they are. Push that and I will merge.

Upstream `upstream/main` contains neither the `installs` filter nor `PROJECT_ROOT` (`git grep` empty).

### 3.4 Conclusion
- **Into fork `main`: nothing to integrate.** Merging the branch would be a content no-op for these two files.
- **Open items (decision for Commander, not done by this card):**
  1. Push a follow-up commit to `fix/hermes-binary-resolution` that removes the `PROJECT_ROOT` block and its docstring wording from `hermes_root()`, so PR #18 can merge upstream.
  2. The same dead block also sits on fork `main` (`scripts/crew_card.py:1257-1263`). When #18 merges upstream with the block removed, the next `sync/upstream-main-daily` merge will hit a change on the same lines. Removing it on `main` too (or accepting upstream's side during reconciliation) keeps fork and upstream aligned.

## 4. `origin/fix/tool-card-alias` — not landed, rejected upstream, superseded

### 4.1 Branch commit
`52e3b74` · Phuong Lambert · 2026-10-19 15:42:34 +0700 · `fix(tools): accept card_id alias for card in crew_verdict, crew_diagnose, and crew_progress`
```
scripts/crew_tools.py    | 33 +++++++++++++++++++++------------
tests/test_crew_tools.py | 28 ++++++++++++++++++++++++++++
```
Adds `_card_arg()` (accepts `card` or `card_id`), declares `card_id` in three schemas, **drops `required: ["card"]`** from `crew_verdict` / `crew_progress`, re-indents three other schemas, and adds 4 tests.

### 4.2 Status on `main`
Not present in any form: `git grep '_card_arg\|"card_id"'` finds nothing in `scripts/crew_tools.py` on `main` or `upstream/main`, and none of the 4 new test names exist on `main`. Since the merge-base, only one commit has touched `scripts/crew_tools.py` / `tests/test_crew_tools.py` on `main`:

`d4c3e33` · macd2 · 2026-10-19 14:53:55 +0200 · `crew 0.9.14: … the crew tools refuse an argument their schema does not declare instead of ignoring it (idea: #17)` — in `upstream/main`, so it reached fork `main` through the sync merge. It adds a guard in `_guarded()` (`scripts/crew_tools.py:38-44`) plus the tests `test_diagnose_refuses_a_key_its_schema_does_not_declare_instead_of_listing` and `test_verdict_refuses_an_extra_key_beside_a_valid_one`. These **assert that `card_id` is refused**. The branch's design is now the opposite of upstream behaviour.

### 4.3 Upstream PR status
**macd2/Crew #17** — **CLOSED, not merged**, head `52e3b74`, closed 2026-10-19T16:12:31Z. Maintainer:
> Closing this one: nothing in Crew or Hermes tells a model to pass `card_id` … (1) the skills call these tools with `card` … Hermes's kanban tools name the id `task_id` … (2) the schema change drops `required: ["card"]` … Your PR did show a real gap … crew 0.9.14 fixes this for all six tools: they refuse undeclared arguments … The commit credits this PR.

### 4.4 Conclusion
- **Do not merge or cherry-pick `52e3b74` into `main`.** It merges textually (no conflicts), but it would: reverse upstream's 0.9.14 decision; make `d4c3e33`'s two refusal tests fail (`card_id` would become a declared key); drop `required: ["card"]`; and add drift that every future upstream sync would have to reconcile.
- The branch, its local copy and the worktree `O:/workspaces/.worktrees/wt-crew-tool-card-alias` are stale. They can be cleaned up when the Commander decides (not done here — out of scope).

### 4.5 ⚠️ Related live defect found on `main` (skills ↔ tools contract)
Fork `main`'s skills tell agents to call the tools with `card_id=`, and the same `main` refuses that argument:
```
$ git grep -n 'crew_verdict(card_id' main -- skills   → 20+ hits, e.g.
  skills/crew-role-worker/SKILL.md:28   crew_verdict(card_id="<card id>")
  skills/crew-verifier/SKILL.md:39,67   crew_verdict(card_id="<id>")
  skills/crew-role-content/SKILL.md:22,31,64,67,71
  skills/crew-no-spec/SKILL.md:50,81,86
  skills/crew/SKILL.md:206
```
Live probe against `main`'s `scripts/crew_tools.py` (scratch script, read-only):
```
crew_verdict  card_id=... -> {"error": "refused: unknown argument(s) card_id; this tool takes: card, timeout"}
crew_progress card_id=... -> {"error": "refused: unknown argument(s) card_id; this tool takes: card, evidence, result, unit"}
crew_diagnose card_id=... -> {"error": "refused: unknown argument(s) card_id; this tool takes: card, state"}
declared/required: crew_verdict [card, timeout] req [card]; crew_progress [card, evidence, result, unit] req [card]; crew_diagnose [card, state] req []
```
Effect: an agent that follows the skill text exactly gets a refusal on its first `crew_verdict` call. It recovers only by reading the error, which names `card`. Upstream's skills use `crew_verdict(card="<card id>")`. The card bodies use `crew_verdict(card=<this card id>)`, which matches.
**Recommendation (follow-up card, not this one):** fix the skills, not the tools. Change `crew_verdict/crew_progress/crew_diagnose(card_id=…)` → `(card=…)` across `skills/*/SKILL.md` on `main`. For `crew_review_handoff(card_id=…)` / `crew_request_changes(card_id=…)`: neither tool is defined in `main`'s `scripts/` or `__init__.py` (`git grep` empty; they come from outside this checkout, e.g. the `feat/crew-extended-tools` worktree), so check their real schema before deciding which argument name the skills should use. Then add a test that parses every `crew_*(<arg>=` in `skills/` and checks it against `SCHEMAS`.

## 5. Test evidence (this host, `main` @ `ed42341`)
```
$ python -m unittest tests.test_crew_windows_support tests.test_crew_tools
Ran 41 tests in 0.196s
FAILED (errors=9)
```
All 9 errors are environmental: `sqlite3.OperationalError: unable to open database file` in `hermes_cli/kanban_db_connect.py:728` (`?mode=ro` connect from the `VerdictTests` / kernel-board `OtherToolTests` fixtures under a kanban-worker process). They are not assertion failures in the audited code, and they happen even with `HERMES_KANBAN_*` unset. The 32 tests that do not touch the kernel board pass, including `test_hermes_exe_prefers_checkout_launcher_and_ignores_pm_installs`. pytest is not installed in the active interpreter, so unittest was used. A full green run of the d4c3e33 refusal tests needs a host where the kernel board fixture can open its DB.

## 6. Reproduce
```bash
cd O:/workspaces/oss/crew && git fetch --all --prune
for b in fix/hermes-binary-resolution fix/tool-card-alias; do
  git merge-base main origin/$b
  git rev-list --left-right --count main...origin/$b
  git cherry -v main origin/$b
  git merge-base --is-ancestor origin/$b main && echo ancestor || echo not-ancestor
  git diff --stat main...origin/$b
done
git log -S'os.sep + "installs" + os.sep' main            # -> daa9340
git log --format='%h %s' fe602d8..main -- scripts/crew_tools.py   # -> d4c3e33
gh pr view 18 -R macd2/Crew --json state,comments
gh pr view 17 -R macd2/Crew --json state,closedAt,comments
git grep -n 'crew_verdict(card_id' main -- skills
```
