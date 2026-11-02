# Exploration: Crew Contract `Inputs` Visibility, Exploration Document Continuity, `/crew` Track A Propose Governance & Full Close-Out Archive Compliance

- **Date**: 2026-11-02
- **Author**: Coordinator (`default/20261102_092114_ecab47`)
- **Reference Session Inspected**: `20261101_190445_ee2488` (`kanban.db` cards `t_23cba6d8` .. `t_d3f51f1a`)
- **Target Repository**: `O:/workspaces/oss/crew` (executed in isolated worktree `O:/workspaces/.worktrees/wt-crew-inputs-and-propose-continuity`)
- **Live Runtime Targets**:
  - `O:/workspaces/_config/agent4070/hermes/plugins/crew`
  - `O:/workspaces/_config/agent4070/hermes/skills/crew`
  - `O:/workspaces/_config/agent4070/hermes/desktop-plugins/crew/plugin.js`

---

## 1. Problem Statement

Post-mortem inspection of session `20261101_190445_ee2488` and follow-up review of session `20261102_092114_ecab47` revealed six distinct root causes across the Crew UI, graph payload builder, intake preload hook, and Crew skill governance:

1. **Defect 1A — Crew UI `Contract` tab hides `Inputs`, `Goal`, `Artifact`, `Lands at`, `Constraints`, and `Proof command` (`ui/src/components/Panel.tsx:86-96` & `scripts/crew_graph.py:1966-1979`)**:
   - In `Panel.tsx`, when `m.kind === "card"`, the default **`Contract`** tab only rendered 6 fields (`Done when`, `Writer`, `Verifier`, `Model pin`, `Budget`, `Result`).
   - Meanwhile, `Inputs`, `Goal`, `Artifact`, `Lands at`, and `Proof command` were buried inside a collapsed `<details class="raw"><summary>Raw fields</summary>` accordion at the bottom of the secondary **`Details`** tab (`Panel.tsx:101-108`).
   - Additionally, `scripts/crew_graph.py:1971` extracted `inputs` via single-line `body_field(body, "Inputs")` instead of `crew_card.contract_inputs(body)` (dropping multi-line `> ` input blocks) and omitted `Constraints:` from `card_ev`.

2. **Defect 1B — `skills/crew/SKILL.md` & `skills/crew-no-spec/SKILL.md` omit `inputs` from Section 5 (`crew_card_create` matrix) and drop Exploration Document paths across Rework/Re-Review/Apply chains**:
   - In session `20261101_190445_ee2488`, 7 out of 11 cards (`t_3991e153`, `t_59004c9a`, `t_4673e876`, `t_8debfe7a`, `t_182327bd`, `t_147ff316`, `t_b7fb6209`) dropped `O:/workspaces/openspec/workspace/explorations/2026-11-01-hermes-security-protection-exploration.md` from `Inputs:`.
   - Root cause: Section 5 (`crew_card_create` arguments table) omitted the `inputs` parameter in both `skills/crew/SKILL.md` and `skills/crew-no-spec/SKILL.md`, and Step 3b / Step 4 did not require preserving the Exploration Document path in `Inputs:` across every downstream card.

3. **Defect 2A — `skills/crew/SKILL.md` line 42 Track B Fast-Path escape hatch allows `/crew` to skip Phase 2 (`openspec-propose`)**:
   - Line 42 permitted skipping OpenSpec whenever the user prompt named an exact file or line.
   - In session `20261101_190445_ee2488` (`MSG 458599`), Commander invoked `/crew` (Track A) with an authored Exploration Document (`2026-11-02-desktop-gateway-persistence-reauth-pause-exploration.md`), and the Coordinator used that escape hatch to skip Phase 2 (`openspec-propose`) and dispatch worker card `t_d3f51f1a` directly.

4. **Defect 2B — Contradictory upstream rule `"Intake writes nothing to disk; read-only tools only"` in `skills/crew/SKILL.md` line 147**:
   - Directly contradicted Track A Step 2 (`openspec-explore`) and Step 3 (`openspec-propose`), which require writing the Exploration Document and the 4 OpenSpec proposal artifacts (`proposal.md`, `specs/<capability>/spec.md`, `design.md`, `tasks.md`) to disk under `<OPENSPEC_ROOT>` before dispatching cards.

5. **Defect 3 — Reviewer `REJECTED` watcher reports did not open the intake window for autonomous Step 3b remediation (`__init__.py:1594-1597`)**:
   - When a background `crew_card.py watch` process returned a report whose body or linked findings carried a `REJECTED` verdict, `crew_intake_preload` did not call `_open_window(session_id)` and `_record_crew_turn(session_id, turn_id)`, forcing the Coordinator to pester the Commander for another `/crew` confirmation just to dispatch the Remediation + Re-Review chain.

6. **Defect 4 — OpenSpec Project-Root Worktree Misrouting & Incomplete Phase 5/6 Close-Out (`skills/crew/SKILL.md` Step 1 & Step 5)**:
   - When targeting a repository governed by Zero-Checkout (`O:/workspaces/oss/crew`), the Coordinator misrouted `OPENSPEC_ROOT` to `O:/workspaces/ai_agents/hermes-agent/openspec` instead of authoring, syncing, and archiving inside the target repository's isolated worktree (`O:/workspaces/.worktrees/wt-<slug>/openspec`) and fast-forwarding `O:/workspaces/oss/crew` (`os_54792d`).
   - During Phase 5/6 Close-Out, the Coordinator also failed to copy the Exploration Document into `changes/<change>/explorations/` before archiving (leaving `hasExplorations: False` on the archived change), failed to sync the target repository's canonical specs (`oss/crew/openspec/specs/crew-skills-regulations/spec.md` and `desktop-flow-graph-pane/spec.md`), and failed to transition the completed Kanban cards (`tasks.status`) from `done` to `archived`.

---

## 2. Solution & Public Testing Seams

### Seam 1: Backend Graph Contract Extraction (`scripts/crew_graph.py`)
- In `_Builder.branch` (`scripts/crew_graph.py:1966-1979`), extract:
  - `"inputs": crew_card.contract_inputs(body) or body_field(body, "Inputs")`
  - `"constraints": body_field(body, "Constraints")`

### Seam 2: UI `Contract` Tab Completeness (`ui/src/components/Panel.tsx` & `desktop/plugin.js`)
- In `Panel.tsx`, when `m.kind === "card"`, render `Goal` (when trimmed text differs from `card_title`), `Inputs`, `Artifact`, `Lands at`, `Constraints`, `Done when`, `Proof command`, `Writer`, `Verifier`, `Model pin`, `Budget`, and `Result` directly in the default **`Contract`** tab.

### Seam 3: `/crew` Track A Propose Continuity & `Inputs` Preservation (`skills/crew/SKILL.md` & `skills/crew-no-spec/SKILL.md`)
- Remove the Track B Fast-Path escape hatch from `skills/crew/SKILL.md`.
- Replace `"Intake writes nothing to disk"` with explicit permission to write OpenSpec artifacts under `<OPENSPEC_ROOT>` (or `<worktree>/openspec` for Zero-Checkout repos) while forbidding application source edits in chat.
- Document `inputs` in Section 5 (`crew_card_create`) of both `skills/crew/SKILL.md` and `skills/crew-no-spec/SKILL.md`, and mandate passing the Exploration Document path in `Inputs:` across Proposal Review, Remediation, Re-Review, and Apply cards.

### Seam 5: Autonomous Zero-Prompt Remediation on Reviewer Rejection (`__init__.py` & `skills/crew/SKILL.md` Step 3b)
- In `crew_intake_preload` (`__init__.py`), when `WATCH_REPORT_RX` matches a watcher report with a `REJECTED` verdict (inline or in a referenced `findings-*.md` file), call `_open_window(session_id)` and `_record_crew_turn(session_id, turn_id)` and inject `[CREW AUTONOMOUS REMEDIATION DIRECTIVE]` so the Coordinator dispatches the Remediation + Re-Review card pair in the same turn without asking the Commander.

### Seam 6: Worktree-Backed `OPENSPEC_ROOT` & Mandatory 6-Point Close-Out Gate (`skills/crew/SKILL.md` Step 1 & Step 5)
- Codify in `skills/crew/SKILL.md`:
  1. **Zero-Checkout Project Root Rule (Step 1)**: When `<project>` is a Zero-Checkout production repo (`oss/crew`, `oss/hermes-agent`, `oss/hermes-nerve`, `O:/workspaces`), `OPENSPEC_ROOT` MUST still be `<project>/openspec` (never a different repo's `openspec/`!), with all file mutations performed inside `<worktree>/openspec/`, committed/pushed to `origin/main`, and fast-forwarded into `<project>` via `git -C <project> pull --ff-only origin main`.
  2. **Exploration Packaging Before Archive (Step 3 & Step 5d)**: Copy/move `<OPENSPEC_ROOT>/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` into `<OPENSPEC_ROOT>/changes/<change>/explorations/` before archiving so `hasExplorations: True` is preserved inside `changes/archive/YYYY-MM-DD-<change>/explorations/`.
  3. **Canonical Spec Sync & Archive Verification (Step 5b–5e)**: Merge delta specs into `<OPENSPEC_ROOT>/specs/<capability>/spec.md`, archive into `<OPENSPEC_ROOT>/changes/archive/YYYY-MM-DD-<change>/`, write `<OPENSPEC_ROOT>/workspace/audits/YYYY-MM-DD/<change>-audit.md`, transition the change's Kanban cards to `status='archived'`, and commit + push + fast-forward `<project>` so `git status --short` is clean and the OpenSpec UI board reflects the archived change and updated specs immediately.

---

## 3. Out of Scope
- Autonomous restart of Hermes Gateway or Dashboard services.
