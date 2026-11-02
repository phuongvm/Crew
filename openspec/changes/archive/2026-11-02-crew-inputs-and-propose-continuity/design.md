# Technical Design: Crew Contract `Inputs` Visibility & Exploration-to-Propose Continuity

## Context

In session `20261101_190445_ee2488`, four architectural seams in the Crew plugin (`O:/workspaces/oss/crew`) caused the Exploration Document (`Inputs:`) to be invisible in the Crew UI, dropped from downstream Remediation/Re-Review/Apply card contracts, and bypassed during `/crew` Phase 2 (`openspec-propose`); and a `REJECTED` watcher report stalled remediation until the Commander re-prompted (Seam 5).

This design specifies the surgical changes across `scripts/crew_graph.py`, `ui/src/components/Panel.tsx`, `skills/crew/SKILL.md`, `skills/crew-no-spec/SKILL.md`, and `__init__.py` (`crew_intake_preload`).

---

## 1. Deep Modules & Architecture Seams

### 1.1 Backend Card Evidence Extraction (`O:/workspaces/oss/crew/scripts/crew_graph.py`)
- **File & Lines**: `scripts/crew_graph.py:1957-1979` (`_Builder.branch`)
- **Current Defect**:
  - Line 1971 reads `"inputs": body_field(body, "Inputs")`, which uses a single-line regex `r"^\s*Inputs:\s*(.+)$"` (`crew_graph.py:1110`). If `Inputs:` contains quoted multiline blocks (`> ...`), `body_field` either truncates after line 1 or returns `None`.
  - `"constraints"` is never extracted into `card_ev`.
- **Design Change**:
  - Use `crew_card.contract_inputs(body) or body_field(body, "Inputs")` for `card_ev["inputs"]`.
  - Add `"constraints": body_field(body, "Constraints")` to `card_ev`.
  - **Known limitation (documented, not changed)**: `body_field` is single-line (`crew_graph.py:1103-1111`), the same as `Artifact`, `Lands at`, `Done when` and `Goal`; a multi-line `Constraints:` block renders only its first line in the `Contract` tab. A multiline extractor is out of scope for this change.

### 1.2 Frontend `Contract` Tab Rendering (`O:/workspaces/oss/crew/ui/src/components/Panel.tsx`)
- **File & Lines**: `ui/src/components/Panel.tsx:85-110` (`tabBody` for `m.kind === 'card'`)
- **Current Defect**:
  - When `tab === 'Contract'`, `<dl>` only renders `Done when`, `Writer`, `Verifier`, `Model pin`, `Budget`, and `Result`.
  - `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Goal`, and `Proof command` are omitted from `Contract` and relegated to the collapsed `<details className="raw"><summary>Raw fields</summary>` in `Details` (`Panel.tsx:107`).
- **Design Change**:
  - In `tab === 'Contract'`, render:
    1. `Goal`: `kvRow('Goal', ev.goal && ev.goal.trim() !== (card.card_title || '').trim() ? <Md text={ev.goal} /> : '')` (comparison on trimmed values; omitted when identical to `card.card_title` so `.ps` subtitle and `.kvr dd` never duplicate 40+ char strings under `crew_panel_steps_proof.py:67-69`).
    2. `Inputs`: `kvRow('Inputs', ev.inputs ? <Md text={ev.inputs} /> : '')`
    3. `Artifact`: `kvRow('Artifact', ev.artifact ? <Md text={ev.artifact} /> : '')`
    4. `Lands at`: `kvRow('Lands at', ev.lands_at ? <Md text={ev.lands_at} /> : '')`
    5. `Constraints`: `kvRow('Constraints', ev.constraints ? <Md text={ev.constraints} /> : '')`
    6. `Done when`: `kvRow('Done when', ev.done_when ? <Md text={ev.done_when} /> : '')`
    7. `Proof command`: `kvRow('Proof command', ev.proof_cmd ? <span className="mono">{ev.proof_cmd}</span> : '')`
    8. `Writer`, `Verifier`, `Model pin`, `Budget`, `Result` (existing rows preserved in order).
  - In `tab === 'Details'` (`Panel.tsx:107`), add `goal: 1, inputs: 1, artifact: 1, lands_at: 1, constraints: 1, proof_cmd: 1` to the `skip` object passed to `rawFields([ev], skip)` so promoted contract fields are not duplicated in `Raw fields`.
  - Rebuild `desktop/plugin.js` and `scripts/crew_dashboard/app.js` via `node ui/build.mjs`.

### 1.3 Skill Contract & Track A Propose Continuity (`O:/workspaces/oss/crew/skills/crew/SKILL.md` & `skills/crew-no-spec/SKILL.md`)
- **File & Lines**: `skills/crew/SKILL.md:57-178, 306-325, 440` and `skills/crew-no-spec/SKILL.md:18-65, 199` (tool table; the `:183` heading is an Operational Pitfall, not the table)
- **Current Defects**:
  1. `skills/crew/SKILL.md:122-140` embeds Track B's *"Mode 1 — Exploration-Backed / Clear-Target Fast-Path (Turn-1 Dispatch)"* inside the `/crew` skill, causing `/crew` turns that name a specific target file to skip Step 3 (`openspec-propose`) and open a worker card directly.
  2. `skills/crew/SKILL.md:147` states *"Intake writes nothing to disk; read-only tools only"*, conflicting with Step 2 (`openspec-explore` writing the Exploration Document) and Step 3 (`openspec-propose` writing `proposal.md`, `specs/`, `design.md`, `tasks.md`).
  3. `skills/crew/SKILL.md:86-101` (Step 3b Remediation & Re-Review) and `skills/crew/SKILL.md:440` / `skills/crew-no-spec/SKILL.md:199` (Section 5 `crew_card_create` parameter list) omit `inputs` / `Inputs: <exploration_doc_path>`.
- **Design Changes**:
  1. In `skills/crew/SKILL.md`:
     - Replace the inline Track B Mode 1/Mode 2 block (lines 122–140) with a strict boundary rule: `/crew` (without `--no-spec`) ALWAYS executes Track A (7-stage OpenSpec Governance) and NEVER dispatches an implementation worker card before Step 3 (`openspec-propose` + Independent Proposal Review + Phase Approval Gate), even for a single-file or 1-line code change. Only explicit `/crew-no-spec` or `/crew --no-spec` routes to the `crew-no-spec` skill.
     - In Step 2 & Step 3, specify that if a prior exploration document was written under generic root `O:/workspaces/openspec/workspace/explorations/` before `OPENSPEC_ROOT` was locked to a subproject, the coordinator MUST copy/link it into `<OPENSPEC_ROOT>/workspace/explorations/` and synthesize it into `<OPENSPEC_ROOT>/changes/<change-id>/` (recording `x-exploration:` in `.openspec.yaml` and citing the Exploration Document in `proposal.md`).
     - In Step 3, Step 3b (Card 1 Remediation & Card 2 Re-Review), and Step 4 (Apply), explicitly require `Inputs:` to include the Exploration Document path (`<OPENSPEC_ROOT>/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md`) alongside the OpenSpec change directory and review findings.
     - Scope line 147 (`"Coordinator never edits production source code in chat; in Track A, Coordinator writes only OpenSpec exploration/proposal artifacts under <OPENSPEC_ROOT> before dispatching @reviewer"`).
     - Add `inputs` to the `crew_card_create` parameter list in Section 5 (`crew/SKILL.md:440` and `crew-no-spec/SKILL.md:199`).
     - In Step 3b, add: when a watcher report returns a `REJECTED` review verdict, the Coordinator MUST autonomously dispatch the Card 1 (`@coder` Remediation) + Card 2 (`@reviewer` Re-Review) pipeline in that same turn, without asking the Commander to type `/crew remediate ...` or to re-confirm.
  2. Preserve all 12 `CREW-INV-8` anchor strings across the 5 Crew skills.
  3. Reconcile `skills/crew-no-spec/SKILL.md` frontmatter `version: 0.10.5` to `0.10.7` (the `plugin.yaml` version); every `skills/*/SKILL.md` must carry the same version.

### 1.4 Autonomous Remediation on Rejected Watcher Report (`O:/workspaces/oss/crew/__init__.py`)
- **File & Lines**: `__init__.py:1594-1597` (`crew_intake_preload`), `_open_window` at `__init__.py:1017`, `_note_report` at `:979`.
- **Current Defect**: `if report:` calls `_note_report(session_id, report.group(1))` then returns `None`. By the time a long review's watcher ends, `_CREW_WINDOWS[session_id]` has expired, so `_window_live()` is false and the guard blocks `crew_card_create`; the coordinator can only ask the Commander to re-prompt.
- **Design Change**: when the report text carries a `REJECTED` verdict, call `_open_window(session_id)` beside `_note_report(...)` and return the `crew` skill context (same shape as the owner-reply branch at `__init__.py:1597-1608`, including `_intake_facts()`), instructing the coordinator to run Step 3b immediately. Non-`REJECTED` reports keep the current behavior (`None`, no window), so `AnsweringReportTests` stay valid after narrowing the "report turn opens nothing" assertion to non-`REJECTED` reports. The window closes on the first card opened (`_close_window`), preserving one-report/one-pipeline-start semantics; the Card 2 gated re-review is created in the same turn by `crew_card_create`/`crew_plan` calls inside the window.

---

## 2. Public Testing Seams

1. **`tests/test_crew_panel_steps.py` (Python Unit Seam)**:
   - Add `ContractTabEvidenceTests` verifying that `crew_graph.build_graph()` extracts `inputs` (both single-line comma-separated paths and multiline `> ` quoted blocks) and `constraints` into `card_ev` on the `card:<id>` node.
2. **`tests/desktop_plugin_harness.mjs` (React + jsdom Public Seam)**:
   - On the mounted `.page-card` in `desktop_plugin_harness.mjs`, click the `.node[data-id="card:<id>"] .card` node, verify the `Contract` tab is active, and assert that `<dl>` renders `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, and `Proof command` rows matching `card_ev`.
3. **`tests/test_crew_versions.py` & `check_inv8_anchors.py` (Skill & Invariant Seam)**:
   - Assert version parity across `plugin.yaml` and all `skills/*/SKILL.md`, presence of `inputs` in `crew_card_create` documentation, and `anchors=12 missing=0`.
   - **Proof separation**: worktree repository-contract tests (version/schema/topology/anchors) run before deployment; `test_installed_skills_byte_identical_parity` compares worktree skills with the live runtime copy and is therefore proven only after live deployment (Task 3.1). It is not weakened or skipped globally.
4. **`tests/test_crew_intake_create.py` (Plugin Hook Seam)**:
   - Add `RejectedReportTests`: a `WATCH_REPORT` whose output contains `verdict: REJECTED` makes `crew_intake_preload` open the session window (guard returns `modify`/allow for `crew_card_create` in that turn); a non-`REJECTED` report leaves the guard at `block`.
