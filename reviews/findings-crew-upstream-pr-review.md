# Independent Review Report: macd2/Crew Upstream PR #23

- **Task**: `t_105fafe3` (Contribute shareable ticket links and desktop in-app navigation upstream to macd2/Crew)
- **Reviewer**: `@reviewer` (Agent Reviewer — Domain: Code Quality)
- **Role**: Verifier (`Verify: dual`)
- **Date**: 2026-10-28 22:45 UTC+7
- **PR URL**: [https://github.com/macd2/Crew/pull/23](https://github.com/macd2/Crew/pull/23)
- **Base Ref**: `upstream/main` (`de4a468` — Crew 0.10.4)
- **Head Ref**: `contrib/shareable-ticket-links` (`f9e7e8f`)
- **Worktree**: `O:/workspaces/.worktrees/wt-crew-upstream-pr`
- **Verdict**: **APPROVED**

---

## 1. Executive Summary

Task `t_105fafe3` required porting the shareable ticket link formatting and in-app Desktop click interception from the local Crew fork to a clean upstream contribution branch based on `upstream/main` (`macd2/Crew`), verifying full test and harness coverage, pushing to origin, and opening a Pull Request on `macd2/Crew`.

Implementation by `@coder` was audited across both review axes (Standards & Spec fidelity), and all automated proof suites and harnesses were independently executed by `@reviewer`. Canonical `crew_card.py verdict --card t_105fafe3` yielded **PASS** (rc=0), worktree test suite passed (187/187 tests + bundle check rc=0), Desktop harness passed (589/589 checks), browser app harness passed (48/48 checks), and PR #23 was verified open and cleanly structured on GitHub.

The change is **APPROVED** without blocking defects.

---

## 2. Commit & Scope Traceability

Branch `contrib/shareable-ticket-links` consists of 3 atomic Conventional Commits directly atop `de4a468`:

1. `e58f889 fix(links): card links are <dashboard>/crew?card=<id>, the address every Crew page opens`
   - Introduces `crew_card.card_url(card_id, base=None)` and `CARD_ROUTE = "/crew?card="`.
   - Adds `/crew?card=<id>` and `/crew` routing support to `crew_graph_serve.py` with backward-compatible preservation of `/card/<id>`.
   - Adds `cardFromSearch` handling to `ui/src/route.ts`, `ui/src/browser.tsx`, and `ui/src/components/CrewPage.tsx`.
2. `1c01b41 feat(links): ticket ids in Desktop card-open and watcher endings are shareable card links`
   - Formats ticket IDs as `[<id>](<dashboard>/crew?card=<id>)` via `card_md_link` in `crew_card.py`.
   - Updates `__init__.py` Desktop card-open reply template and watcher endings (`--md`).
   - Removes obsolete static `DESKTOP_LINE` ("Open it in Crew: the Crew entry in the sidebar...").
   - Updates `skills/crew/SKILL.md` instructions.
3. `f9e7e8f feat(desktop): a plain left-click on a shareable ticket link opens the card in the in-app Crew tab`
   - Implements capture-phase click interception (`watchCardLinks`) in `ui/src/desktop.tsx`.
   - Handles unmodified primary clicks (`button === 0`, no modifiers) while preserving Ctrl/Cmd-click, middle click, right click (Copy Link).
   - Introduces card bus (`openCardRoute`, `onOpenCard`, `takePendingCard`, `cardFromHref`).
   - Adds comprehensive test coverage in `tests/desktop_card_link_checks.mjs`.

Total diff: 22 files changed, 632 insertions(+), 97 deletions(-).

---

## 3. Two-Axis Review Analysis

### Axis 1: Documented Standards & Code Smell Baseline

- **Repository Standards (`CONTRIBUTING.md`)**:
  - *One logical change per PR / No drive-by reformatting*: **PASS**. Strictly focused on shareable ticket links and navigation.
  - *Conventional Commits*: **PASS**. `fix(links)`, `feat(links)`, `feat(desktop)`.
  - *Cross-platform Compatibility*: **PASS**. Clean URI manipulation, no hardcoded POSIX-only commands or `/tmp` paths.
  - *Zero Machine-Specific Strings*: **PASS**. Fixtures and tests exclusively utilize RFC-reserved domains (`crew.example.test`, `dash.example.test`, `http://crew.invalid`, `127.0.0.1`).
  - *Dependency Footprint*: **PASS**. Zero added third-party dependencies; uses Python standard library `urllib.parse`.
  - *Python 3.11+*: **PASS**. Fully compatible.
- **Code Smell Baseline (Fowler Heuristics)**:
  - *Duplicated Code (Minor)*: URL query extraction in `route.ts` vs `open-card.ts` and response dispatch in `crew_graph_serve.py`. Evaluated as acceptable given separation between client-side routing modules and HTTP server dispatch.
  - *Middle Man (Advisory)*: Pass-through delegate functions in `crew_notify.py` (`card_url`, `card_md`). Evaluated as intentional for module-level API stability.
  - *No Mysterious Names, Feature Envy, or Broken Abstractions*.

### Axis 2: Spec Fidelity & Acceptance Criteria

- **Requirement 1 (Hyperlinks in Card-Open Messages)**: **PASS**. Rendered as `[<id>](<url>/crew?card=<id>)`, manual blockquote omitted.
- **Requirement 2 (Hyperlinks in Watcher/Notifier Messages)**: **PASS**. `_text_md` and `watch` format primary `tid` and parent `src` as Markdown links.
- **Requirement 3 (Capture-Phase Desktop Click Interception)**: **PASS**. Capture listener intercepts primary left-clicks on `/crew?card=` links, calls `preventDefault()`, dispatches to card bus, while modified clicks and context menu open/copy natively.
- **Scope Discipline & Boundary Integrity**: **PASS**. Fork-only assets (e.g. `skills/crew-no-spec/SKILL.md` and machine-specific configs) were intentionally excluded from the upstream PR.

---

## 4. Independent Verification & Proof Evidence

All verifications executed independently by `@reviewer`:

1. **Canonical Crew Proof Command & Verdict**:
   - Command: `env -u HERMES_SESSION_SOURCE -u HERMES_SESSION_PLATFORM python -m unittest tests/test_crew_card.py tests/test_crew_notify.py tests/test_crew_watch.py tests/test_crew_intake_create.py tests/test_crew_graph_serve_shell.py && node ui/build.mjs --check`
   - Execution: `python O:/workspaces/oss/crew/scripts/crew_card.py verdict --card t_105fafe3`
   - Outcome: **PASS** (rc=0)
   - Suite results: `Ran 199 tests in 27.898s. OK.`
   - Rebuilt bundles: `desktop/plugin.js` (226,398 bytes), `scripts/crew_dashboard/app.js` (820,287 bytes).
   - Durable receipt: `O:\workspaces\_config\agent4070\hermes\profiles\reviewer\crew\verdicts\t_105fafe3.jsonl`
2. **Worktree Suite Execution**:
   - Execution directory: `O:/workspaces/.worktrees/wt-crew-upstream-pr`
   - Command: `env -u HERMES_SESSION_SOURCE -u HERMES_SESSION_PLATFORM -u HERMES_DELEGATED_CHILD_CONTEXT python -m unittest tests/test_crew_card.py tests/test_crew_notify.py tests/test_crew_watch.py tests/test_crew_intake_create.py tests/test_crew_graph_serve_shell.py && node ui/build.mjs --check`
   - Outcome: **PASS** (rc=0, 187 tests OK in 24.962s, bundle check exit code 0).
3. **Desktop Plugin Harness**:
   - Command: `node tests/desktop_plugin_harness.mjs desktop/plugin.js C:/Users/phuong/AppData/Local/Temp`
   - Outcome: **PASS** (`OK 589 checks`).
4. **Browser App Harness**:
   - Command: `node tests/browser_app_harness.mjs scripts/crew_dashboard/app.js dashboard/dist/index.js`
   - Outcome: **PASS** (`OK 48 checks`).
5. **Live GitHub PR Verification**:
   - Command: `gh pr view 23 -R macd2/Crew`
   - Outcome: PR #23 is **OPEN**, title `feat(links): shareable /crew?card=<id> ticket links that open in-app in Hermes Desktop`, author `phuongvm`, base `macd2/Crew:main`, head `phuongvm:contrib/shareable-ticket-links` (`f9e7e8f`).
6. **Task Progress Units**:
   - All 3 units verified and recorded PASS by verifier in `O:\workspaces\_config\agent4070\hermes\profiles\reviewer\crew\progress\t_105fafe3.json`.
7. **Zero-Checkout & Invariant Preservation**:
   - Production repositories (`O:/workspaces`, `O:/workspaces/oss/crew`) remained strictly on `main` without uncommitted drift.
   - Work conducted cleanly in isolated worktree `wt-crew-upstream-pr`.
   - Reviewer performed zero edits on implementation source code.

---

## 5. Verdict

**APPROVED**. Task `t_105fafe3` satisfies all contract goals and acceptance criteria.
