# Proposal: Code-Enforced OpenSpec Close-Out Gate in Crew Preload (`code-enforced-openspec-closeout-gate`)

## Why

When a multi-card `/crew` OpenSpec workflow runs across several turns, Hermes context compaction prunes `skills/crew/SKILL.md` (`[SKILL_PRUNED]`). When the final implementation/verification card's `crew_card.py watch` process returns a `Done` report (`WATCH_REPORT_RX`), `crew_intake_preload` (`__init__.py:1597-1616`) only handled `REJECTED` verdicts and returned `None` on `Done` reports, leaving the Coordinator without the mandatory 6-point close-out checklist (`openspec-verify-change` -> `openspec-sync-specs` -> `openspec_change_archive` -> Post-Archive Audit -> worktree commit, push & `git pull --ff-only`).

## Source Exploration Document

- `openspec/workspace/explorations/2026-11-02-code-enforced-openspec-closeout-gate-exploration.md`

## What Changes

1. **Completed OpenSpec Watcher Report Close-Out Injection (`__init__.py`)**:
   - In `crew_intake_preload` (`__init__.py:1597-1616`), when `WATCH_REPORT_RX` matches a non-`REJECTED` completed (`Done`) watcher report that references `openspec/changes/<change-id>` (in `user_message` or in the card's `kanban.db` body), inject a deterministic `[CREW OPENSPEC CLOSE-OUT GATE]` context block reminding the Coordinator to execute the 6-point close-out sequence on the canonical repository's `OPENSPEC_ROOT` (via its isolated worktree when Zero-Checkout applies).
2. **Unit Test Coverage (`tests/test_crew_intake_create.py`)**:
   - Add tests verifying that a `Done` watcher report referencing `openspec/changes/<change-id>` returns the `[CREW OPENSPEC CLOSE-OUT GATE]` directive without opening an intake card-creation window (preserving `AnsweringReportTests`), while an ordinary non-OpenSpec `Done` report continues returning `None`.

## Impact

- `__init__.py`, `tests/test_crew_intake_create.py`
