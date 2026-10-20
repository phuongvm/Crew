# Independent Re-review Findings — F-01 Remediation

- **Verdict: APPROVED**
- **Reviewer:** reviewer
- **Review card:** `t_18ecd8bc`
- **Reviewed repository state:** `4b0cbbd` on `main`; F-01 remediation commit `855abc7`
- **Scope:** Re-review of the prior F-01 rejection only: the change proposal, design, tasks, prior review, relevant permanent specs, `ui/src/open-card.ts`, `ui/src/components/EventLine.tsx`, `ui/src/components/CrewPage.tsx`, `ui/src/browser.tsx`, regenerated bundles, and the two F-01 harness sections. The change has no `specs/` delta directory; the proposal/design/tasks are the available change-contract artifacts.

## Findings summary

| Severity | Count | Result |
|---|---:|---|
| CRITICAL | 0 | None |
| WARNING | 0 | None |
| INFO | 1 | The change remains `proposed`; archival/synchronization is outside this review card. |

## Requirement and remediation matrix

| SDLC layer | Requirement / prior finding | Evidence | Result |
|---|---|---|---|
| Specs | Prior F-01 at `findings-reviewer-v1.md:24-34`: Desktop’s producer emitted `<gateway>/crew?card=<id>` but `CrewPage` read only the hash, so a fresh shared URL opened the board. | `open-card.ts:18-33` establishes `cardFromSearch()` and one `cardUrl()` convention: hosted Crew tabs use `?card=<id>`, served shell uses `/card/<id>`. | PASS |
| Architecture / design | `design.md:62-71` requires endpoint-aware links and graceful client-context behavior; proposal scope includes card-detail links. | `EventLine.tsx:65-75` is the sole producer through `cardUrl()`; `CrewPage.tsx:20-29` consumes hosted query links at arrival while retaining the existing hash-route listener; `browser.tsx:36-43` consumes the same query form in the hosted tab. | PASS |
| Code | F-01 producer/consumer compatibility. | `cardUrl()` emits `<tab>?card=<id>` only for resolved links ending in `/crew`; `cardFromSearch()` validates IDs before either receiving page sets a card route. Served-shell routing remains `parseLocation(pathname, search)`. | PASS |
| Tests | F-01 must be demonstrated on every target, not inferred from source only. | Desktop harness asserts produced `https://hermes.remote.example:9119/crew?card=<id>`, loads that URL, verifies `.page-card` rather than `.page-board`, and observes the requested `/card/<id>` fetch (`tests/desktop_plugin_harness.mjs:168-193`). Browser harness covers served-shell production/fresh load (`101-110`) and hosted-dashboard fresh load/fetch/producer (`232-242`). | PASS |
| Build | Generated deliverables must match reviewed source. | Independent `node ui/build.mjs --check` passed and reported `desktop/plugin.js 222454 bytes`, `scripts/crew_dashboard/app.js 818762 bytes`. | PASS |

## Independent execution evidence

```text
python -m unittest discover -s tests -p 'test_crew_desktop_plugin.py'
Ran 8 tests in 19.824s
OK

python -m unittest discover -s tests -p 'test_crew_dashboard_customization.py'
Ran 16 tests in 1.730s
OK

node ui/build.mjs --check
desktop/plugin.js  222454 bytes
scripts/crew_dashboard/app.js  818762 bytes
INDEPENDENT_REMEDIATION_SUITE_RC=0
```

The dashboard suite emitted an expected mocked `RuntimeError: secret-path /home/x/kanban.db locked` health-path traceback and still completed `OK`; it is fixture behavior, not a test failure.

## Extra substantive check — F-01 contract trace

The source-to-harness trace independently confirmed the corrected convention across every recipient:

```text
tests/desktop_plugin_harness.mjs:182 ... gateway Crew tab + ?card=<id>
tests/desktop_plugin_harness.mjs:188 ... page loaded at the shared card link opens the card, not the board
tests/browser_app_harness.mjs:107 ... served shell ... /card/<id>
tests/browser_app_harness.mjs:236 ... dashboard tab: a ?card=<id> address opens that card, not the board
```

This specifically closes the prior defect: `CrewPage.tsx:24-25` now calls `cardFromSearch(window.location.search)` before mounting the board and routes a valid shared ID to the card page.

## Worktree and scope gates

- **Zero-Checkout:** PASS. The production checkout remained on `main`; `git worktree list` showed feature branches only under `O:/workspaces/.worktrees/...`.
- **Scope:** PASS. `855abc7` changes only the F-01 routing helper, producer/consumers, generated bundles, and the two target harnesses. `git diff --check 855abc7^ 855abc7` exited 0.

## Not reviewed

- No end-to-end browser against a live Desktop/Gateway instance was executed; the repository’s real jsdom harnesses exercised the generated Desktop plugin, served shell, and hosted dashboard implementations.
- No OpenSpec archival or spec synchronization was performed; this card is an implementation re-review only.

## Disposition

F-01 is remediated. The producer and all three receivers use compatible, tested link conventions, independent regression/build checks pass, and no blocking finding remains.
