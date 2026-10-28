# Exploration & Specification: Crew Progress & Status Reporting Compliance

- **Date**: 2026-10-28
- **Session Case Study**: `20261028_094029_0a5540` (Cards `t_4b49d8d4`, `t_cf261bbd`)
- **Target Repository**: `O:/workspaces/oss/crew` (developed in isolated worktree `O:/workspaces/.worktrees/wt-crew-progress-reporting`)
- **Governance & Skills**: Matt Pocock (`grilling`, `codebase-design`, `tdd`, `writing-for-agents`, `engineering/code-review`), `commander-communication-protocol`, `task-verification-mandate`

## 1. Problem Statement & Empirical Root Causes

In session `20261028_094029_0a5540`, two Crew cards (`t_4b49d8d4` and `t_cf261bbd`) executed work accurately on disk, and the worker (`@coder`) recorded thorough structured notes in card comments (`#320`). However, the status and progress updates delivered to the Commander failed communication standards due to four shallow module seams in `oss/crew`:

1. **Seam 1 — Dumb-Relay Mandate (`__init__.py` & `skills/crew/SKILL.md`)**:
   - `_banner_open()` in `__init__.py` instructed the Coordinator: `"when its ending comes back, send it to the owner as it is ... do not reword it."`
   - This prevented the Coordinator from synthesizing a self-contained debrief (`Done / Not Done / Blocked / Evidence / Next Action`) in the Commander's resolved language (`SOUL.md`) across all tasks in the session.

2. **Seam 2 — Blind Head-Truncation in `proof_change_ask` & `proof_blocked_ask` (`scripts/crew_coordinator.py`)**:
   - `proof_change_ask()` truncated `new[:100]` and `old[:70]` and omitted the coordinator's `why` and the worker's block context.
   - When `t_cf261bbd`'s proof command differed at character 197 (`len(log)==5` vs `len(log)>=5`), the `Needs you` prompt showed two identical truncated strings with zero explanation of why the change was needed or what work had already succeeded.

3. **Seam 3 — Destructive Flattening in `crew_notify.py` & `crew_watch.py`**:
   - `done_summary()` passed the worker's summary through `short(..., 600)`, which ran `" ".join(str(text or "").split())`, destroying all line breaks, bullet points (`Done / Not Done / Evidence`), and truncating at 600 chars.
   - `_extra()` in `crew_watch.py` omitted the card's execution trajectory (runs count, progress units, self-heal/rescope history, and latest verdict receipt).

4. **Seam 4 — Unstructured Handoff Guidance in Worker/Content/Verifier Skills**:
   - `skills/crew-role-worker/SKILL.md`, `skills/crew-role-content/SKILL.md`, and `skills/crew-verifier/SKILL.md` did not mandate structured `Done / Not Done / Evidence` sections in completion/handoff summaries.

## 2. Approved Design Decisions (Frontier Round 1)

1. **Q1 (Option A — Hybrid Structured Debrief)**:
   - Keep the canonical Crew status header and footer pointer so `WATCH_REPORT_RX` and desktop links remain 100% compatible, while replacing `"do not reword it"` in `__init__.py` and `skills/crew/SKILL.md` with an explicit mandate: after outputting the watcher's card block, the Coordinator MUST append a **Self-Contained Executive Debrief** (`Done / Not Done / Blocked / Evidence / Next Action`) covering the session's tasks in the active profile's conversational language (`SOUL.md`, keeping technical artifacts in English).
2. **Q2 (Option A — Context + Exact Diff + Progress Already Succeeded in `Needs you`)**:
   - Deepen `proof_change_ask()` and `proof_blocked_ask()` in `scripts/crew_coordinator.py` and `needs` formatting in `scripts/crew_notify.py` / `scripts/crew_watch.py`:
     - Surface the coordinator's `why` (reason for rescope/ask) and the worker's latest progress/block summary.
     - Compute and display the exact diff delta between `old` and `new` proof commands (plus full commands in `detail` / markdown) instead of blind `[:100]` / `[:70]` head slices that hide mid/tail changes.
3. **Q3 (Option A — Structured Multi-Line Summary + Verdict Receipt)**:
   - Add `short_multiline(text, n)` in `scripts/crew_notify.py` to preserve line breaks and bullet lists in markdown/report summaries while still redacting secrets and bounding total length (`DONE_SUMMARY_MD_CHARS = 2000`, `NEEDS_REASON_MD_CHARS = 1200`).
   - Update `skills/crew-role-worker/SKILL.md`, `skills/crew-role-content/SKILL.md`, and `skills/crew-verifier/SKILL.md` to require structured `Done / Not Done / Evidence` summaries on completion, review handoff, and block.
4. **Q4 (Option A — Milestone Trajectory in `crew_watch.py`)**:
   - Deepen `crew_watch.py::_extra()` to include a concise **Trajectory / Progress** summary derived from the board (`runs` count, passed/total `Units` from `crew_progress`, coordinator decisions such as `rescope`/`retry`, and latest `crew_verdict` status/exit code).
