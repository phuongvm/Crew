# Independent Review Findings — crew-pane-default-off-and-dynamic-endpoint

- **Verdict: REJECTED**
- **Reviewer:** reviewer
- **Review card:** `t_c28a4237`
- **Reviewed repository state:** `b122300` (`main`); implementation commits `3f56ba8`, `6744fbe`, and `a44753f`
- **Worktree gate:** PASS. `O:/workspaces/oss/crew` remained on `main`; `git worktree list` showed no writer branch checked out in that production checkout.

## Scope and required context

The change delta declares four requirements in `specs/crew-pane-default-off-and-dynamic-endpoint/spec.md`. The repository has no tracked `ARCHITECTURE.md`, `architecture.md`, `docs/ARCHITECTURE.md`, `docs/lessons/lessons-learned.md`, or `code-review-mandate/spec.md`; architecture was therefore assessed from the change design and source topology.

## Requirement matrix

| Delta requirement | Evidence | Result |
|---|---|---|
| Desktop Flow Pane Arrival State | `ui/src/desktop.tsx:134-138` registers `flow` with `defaultCollapsed: true`; generated `desktop/plugin.js:3564-3568` carries the same data. `test_flow_pane_arrives_collapsed` passed. | PASS |
| Dynamic Board Header Link | `ui/src/components/Board.tsx:53-84` rejects loopback server URLs and resolves Desktop gateway, hosted dashboard, and served-shell origins. Desktop and browser harnesses passed in the independent suite. | PASS |
| Dynamic Card Detail Link | **F-01 below.** The Desktop-target link emitted by `EventLine.tsx:65-68` is not consumable by the Desktop card router in `CrewPage.tsx:20-25`. | FAIL |
| Build Integrity | Independent `unittest` suite passed all 24 tests; it includes `node ui/build.mjs --check`, generated-bundle freshness, the Desktop stub harness, and browser/dashboard harness. | PASS |

## Blocking finding

### F-01 — HIGH: Desktop dynamic card link does not open the requested card

- **Requirement:** Delta requirement “Dynamic Card Detail Link,” scenario at `spec.md:28-34`: the detected endpoint must append `/card/<id>` or a hosted equivalent.
- **Producer:** `ui/src/components/EventLine.tsx:65-68` emits `https://<gateway>/crew?card=<id>` whenever the resolved dashboard URL ends in `/crew`.
- **Consumer:** `ui/src/components/CrewPage.tsx:20-25` accepts an external card ID only from `window.location.hash`, via `cardFromHash(window.location.hash)`. `ui/src/open-card.ts:10-13` accepts only `#/crew?card=<id>` (or the equivalent hash without its leading `#`), not the URL query produced by `EventLine`.
- **Reproduction / extra substantive check:** source-path comparison returned the incompatible pair:
  - `EventLine.tsx:66-68`: `dashLink.endsWith('/crew') ? \`${dashLink}?card=...\` : .../card/...`
  - `CrewPage.tsx:22`: `cardFromHash(window.location.hash)`
  - `open-card.ts:11-13`: regex `^#?/crew\\?(.*)$` applied only to the hash.
- **Impact:** A Desktop gateway link such as `https://hermes.remote.example:9119/crew?card=t_123` loads the Crew route but is ignored by the Desktop page, which remains on the board. The link is neither `/card/<id>` nor a valid Desktop-hosted equivalent (`#/crew?card=<id>`). Current harnesses verify the board-header link but contain no assertion for the `EventLine` card link.
- **Required remediation:** Make producer and consumer use one documented, tested convention. Either emit a hash route accepted by `cardFromHash` (`<gateway>/#/crew?card=<id>`) for Desktop, or add query parsing in `CrewPage` and test that a freshly loaded Desktop page opens the linked card. Add coverage for Desktop, hosted dashboard, and served-shell card-detail links.

## Independent execution evidence

```text
python -m unittest discover -s tests -p 'test_crew_desktop_plugin.py' -v
Ran 8 tests in 29.655s
OK

python -m unittest discover -s tests -p 'test_crew_dashboard_customization.py' -v
Ran 16 tests in 1.932s
OK
UNITTEST_ACCEPTANCE_RC=0
```

The card’s requested `pytest` command could not run under this reviewer environment because the active interpreter reports `No module named pytest`; this is an environment limitation, not substituted evidence. The stdlib test execution above independently exercised the same two test modules and their Node harnesses.

## Non-blocking observations

- `scripts/crew_card.py:149-167` correctly returns `dashboard.public_url` when `HERMES_HOME` points to a home containing `config.yaml`; isolated probe output was `CONFIG_PROBE_URL=https://review.example.test/hermes`.
- The backend fallback is outside the delta’s four formal requirements but is within the proposal/design scope.

## Required disposition

Do not approve or archive this OpenSpec change until F-01 is remediated and independently re-reviewed.
