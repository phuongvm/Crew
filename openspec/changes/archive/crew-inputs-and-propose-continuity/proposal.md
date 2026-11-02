# Proposal: Crew Contract `Inputs` Visibility & Exploration-to-Propose Continuity (`crew-inputs-and-propose-continuity`)

## Why

Post-mortem inspection of session `20261101_190445_ee2488` (`state.db` messages `455143`–`458798` and 11 Kanban cards in `kanban/boards/crew/kanban.db`) identified four root causes breaking traceability between Exploration Documents, OpenSpec Proposals, and Crew Kanban tickets:

1. **Crew UI `Contract` Tab Hides `Inputs` (`Panel.tsx:86-96` & `crew_graph.py:1957-1979`)**:
   - When reviewing a ticket on the Crew Card page, the `Contract` tab of the `Coordinator · card` node only renders `Done when`, `Writer`, `Verifier`, `Model pin`, `Budget`, and `Result`. It omits `Inputs` (as well as `Goal`, `Artifact`, `Lands at`, `Constraints`, and `Proof command`), hiding `Inputs` inside a collapsed `<details class="raw"><summary>Raw fields</summary>` block at the bottom of the `Details` tab (`Panel.tsx:107`).
   - Additionally, `scripts/crew_graph.py:1971` extracts `"inputs"` with single-line `body_field(body, "Inputs")` instead of multiline-aware `crew_card.contract_inputs(body)`, and omits `"constraints"` from `card_ev`.
2. **`crew` and `crew-no-spec` Skills Omit `inputs` from Tool Guidance & Remediation Templates (`skills/crew/SKILL.md` & `skills/crew-no-spec/SKILL.md`)**:
   - Section 5 (`Complete 17-Tool Decision Matrix & Guidance`, `crew/SKILL.md:440` and the `crew_card_create` row of the `crew-no-spec/SKILL.md` tool table at `:199`) omits `inputs` from the `crew_card_create` parameter list.
   - Step 3b (`Phase 2b: Remediation & Re-Review Loop`, `crew/SKILL.md:86-101`) omits `Inputs:` from both Card 1 (`@coder` remediation) and Card 2 (`@reviewer` re-review) templates. Consequently, in session `20261101_190445_ee2488`, all 7 remediation, re-review, and final Apply cards (`t_3991e153` → `t_b7fb6209`) dropped the Exploration Document path (`2026-11-01-hermes-security-protection-exploration.md`) from `Inputs:`.
3. **`/crew` Bypasses Phase 2 (`openspec-propose`) Due to Inline Track B Fast-Path & Read-Only Intake Contradictions (`skills/crew/SKILL.md:122-148, 211`)**:
   - `skills/crew/SKILL.md` embeds Track B's *"Mode 1 — Exploration-Backed / Clear-Target Fast-Path (Turn-1 Dispatch)"* (lines 122–140) alongside the upstream rule *"Intake writes nothing to disk; read-only tools only"* (line 147) and *"Complete -> show the draft, open the card, end the turn - quickly"* (line 211).
   - When Commander invoked `/crew vá 1 dòng trong apps/desktop/src/store/gateway-persistence.ts...` (`MSG 458599`), the coordinator matched the inline Clear-Target Fast-Path rule and bypassed Phase 2 (`openspec-propose` + Phase Approval Gate), opening worker card `t_d3f51f1a` directly instead of synthesizing the Exploration Document into an OpenSpec Proposal.
   - Furthermore, when an initial exploration was started under `/crew-no-spec` without a project gate, the exploration file was saved under generic root `O:/workspaces/openspec/workspace/explorations/` instead of the subproject's `<OPENSPEC_ROOT>/workspace/explorations/`, splitting discovery artifacts from the subproject's `openspec/changes/` directory.
4. **Rejected Review Reports Stall Until the Commander Re-Prompts (`__init__.py:1594-1597` & `skills/crew/SKILL.md:86-101`, Exploration Seam 5)**:
   - When the `crew_card.py watch` background process ends with a `REJECTED` review report, `crew_intake_preload` only calls `_note_report(session_id, report.group(1))` (`__init__.py:1596`) and waits for an owner reply. The `/crew` intake window (`_CREW_WINDOWS`, `INTAKE_WINDOW_SECONDS`) has long expired for a review that ran 30+ minutes, so the guard blocks card creation and the coordinator asks the Commander to type `/crew remediate ...` even though Step 3b already mandates an automated closed-loop remediation pipeline.

## Source Exploration Document

- `O:/workspaces/oss/crew/openspec/workspace/explorations/2026-11-02-crew-inputs-and-propose-continuity-exploration.md`

## What Changes

1. **Crew Backend Card Graph (`O:/workspaces/oss/crew/scripts/crew_graph.py`)**:
   - Update `_Builder.branch` (`crew_graph.py:1968-1974`) so `card_ev` extracts `"inputs": crew_card.contract_inputs(body) or body_field(body, "Inputs")` and `"constraints": body_field(body, "Constraints")`. `Constraints` is read with the existing single-line `body_field` (consistent with `Artifact`, `Lands at`, `Done when`); a multi-line `Constraints:` block renders only its first line, and this limitation is documented rather than changed here.
2. **Crew Card UI `Contract` Tab (`O:/workspaces/oss/crew/ui/src/components/Panel.tsx` + rebuilt `desktop/plugin.js` & `scripts/crew_dashboard/app.js`)**:
   - Update `tabBody()` for `m.kind === 'card'` and `tab === 'Contract'` (`Panel.tsx:86-96`) to display `Goal` (when distinct from `card.card_title` so `.ps` and `.kvr dd` never duplicate 40+ char strings), `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, `Proof command`, `Writer`, `Verifier`, `Model pin`, `Budget`, and `Result`.
   - `Goal` is compared with `card.card_title` after trimming surrounding whitespace.
   - Add `goal`, `inputs`, `artifact`, `lands_at`, `constraints`, and `proof_cmd` to the `skip` map of `rawFields([ev], skip)` in the `Details` tab (`Panel.tsx:107`).
3. **Crew Skills Governance (`O:/workspaces/oss/crew/skills/crew/SKILL.md` & `skills/crew-no-spec/SKILL.md`)**:
   - Remove inline Track B execution instructions from `skills/crew/SKILL.md` (keeping only a boundary pointer to `crew-no-spec`), and explicitly forbid `/crew` from bypassing Phase 2 (`openspec-propose`) even for single-file or 1-line asks.
   - Reconcile line 147 of `skills/crew/SKILL.md` so Track A explicitly requires persisting the Phase 1 Exploration Document (`<OPENSPEC_ROOT>/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md`) and synthesizing it into Phase 2 OpenSpec Proposal artifacts (`<OPENSPEC_ROOT>/changes/<change-id>/` with `.openspec.yaml` `x-exploration`, `proposal.md`, `specs/`, `design.md`, `tasks.md`) before dispatching the `@reviewer` Proposal Review card (or dispatching a Two-Card Propose + Review chain with `Inputs: <exploration_doc>`).
   - Mandate `Inputs:` carrying the Exploration Document path in Step 3 (Proposal Review card), Step 3b (Remediation Card 1 & Re-Review Card 2), Step 4 (Apply cards), Section 2 Contract Table, and Section 5 (`crew_card_create` parameter list) across `crew/SKILL.md` and `crew-no-spec/SKILL.md`.
   - Enforce single-target `OPENSPEC_ROOT` resolution across both `/crew` and `/crew-no-spec` (migrating/linking any prior root exploration document into `<OPENSPEC_ROOT>/workspace/explorations/` when entering Phase 2 Propose).
   - Reconcile every shipped Crew skill frontmatter `version` (including `skills/crew-no-spec/SKILL.md`, currently `0.10.5`) to the `plugin.yaml` version (`0.10.7`) so `test_every_shipped_skill_carries_the_plugin_version` passes.
   - Mandate in Step 3b that when a watcher report returns a `REJECTED` review verdict, the Coordinator autonomously dispatches the 2-card Remediation (`@coder`) + Re-Review (`@reviewer`) pipeline in that same turn, with no Commander re-confirmation.
4. **Crew Plugin Watcher-Report Window (`O:/workspaces/oss/crew/__init__.py` + `tests/test_crew_intake_create.py`)**:
   - In `crew_intake_preload` (`__init__.py:1594-1597`), when the matched `WATCH_REPORT_RX` report text carries a `REJECTED` verdict, call `_open_window(session_id)` (defined at `__init__.py:1017`) beside `_note_report(...)` at `:1596` and return the already-loaded `crew` skill context (same shape as the owner-reply branch at `:1597-1608`), so the guard allows the remediation `crew_card_create` calls in the report turn. Reports without a `REJECTED` verdict keep the current no-op behavior (`AnsweringReportTests`, `tests/test_crew_intake_create.py:367-389`); the existing "report turn itself opens nothing" assertion is narrowed to non-`REJECTED` reports.

## Capabilities

- **Modified Capabilities**:
  - `customize-hermes-crew-plugin`: Strengthen `Full-Lifecycle OpenSpec Workflow Execution` with Exploration-to-Propose synthesis and mandatory `Inputs:` propagation across Proposal Review, Remediation, Re-Review, and Apply cards; add `Crew Card Contract Tab Completeness` requirement for rendering `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, and `Proof command` in the Crew UI `Contract` tab.

## Impact

- **Repository (`O:/workspaces/oss/crew` via isolated worktree `O:/workspaces/.worktrees/wt-crew-inputs-and-propose-continuity`)**:
  - `scripts/crew_graph.py`
  - `ui/src/components/Panel.tsx`
  - `desktop/plugin.js` & `scripts/crew_dashboard/app.js` (rebuilt via `node ui/build.mjs`)
  - `skills/crew/SKILL.md` & `skills/crew-no-spec/SKILL.md` (including frontmatter `version` reconciliation to `0.10.7`)
  - `__init__.py` (`crew_intake_preload`)
  - `tests/desktop_plugin_harness.mjs`, `tests/test_crew_panel_steps.py` & `tests/test_crew_intake_create.py`
- **Live Runtime (`O:/workspaces/_config/agent4070/hermes`)**:
  - Synced (including `__init__.py`) to `plugins/crew/`, `skills/crew/`, and `desktop-plugins/crew/plugin.js` after worktree verification and push to `origin/main`.
