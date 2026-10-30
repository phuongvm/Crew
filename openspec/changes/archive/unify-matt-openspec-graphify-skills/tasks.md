# Tasks

Implementation commit: `50cf7e1969721e6e7f3bce8c4dbe80a59867fc14` (`feat(skills): unify Matt Pocock, OpenSpec, and Graphify MCP into Crew skills (CREW-INV-8)`, 5 files, +131/-43; ancestor of `main` HEAD `746f3f3`). Exploration input: `openspec/workspace/explorations/2026-10-29-crew-matt-openspec-unification-exploration.md`. Paths are relative to `O:/workspaces/oss/crew`. Proofs re-run for this change on 2026-10-29 (card `t_92149755`).

## 1. Coordinator Skills (`crew`, `crew-no-spec`)

- [x] 1.1 `skills/crew/SKILL.md` (0.10.4 -> 0.10.5): add section 0.1 Unified Cognitive & Tool Routing Matrix; Phase 1 Explore reuses an existing Exploration Document and runs Graphify first; Phase 2-3 apply `to-spec` / `to-tickets`; card `Inputs:` carries the change directory and the Exploration Document; Track B documents the dual-entry intake.
  - Evidence: `git show --stat 50cf7e1` lists `skills/crew/SKILL.md | 66 +++---`; anchors present.
  - Proof: `cd "O:/workspaces/oss/crew" && grep -q "Unified Cognitive & Tool Routing Matrix" skills/crew/SKILL.md && grep -q "mcp__graphify__" skills/crew/SKILL.md`
- [x] 1.2 `skills/crew-no-spec/SKILL.md` (0.10.2 -> 0.10.5): replace the Turn-1-only mandate with Adaptive Dual-Entry Intake (Mode 1 Exploration-Backed or Clear-Target Fast-Path; Mode 2 Guided Discovery & Root-Cause Loop), add the Automatic Cognitive & Tool Routing Matrix and the optional late spec promotion line in the debrief.
  - Evidence: `skills/crew-no-spec/SKILL.md | 78 ++++++---` in the commit; anchors present.
  - Proof: `cd "O:/workspaces/oss/crew" && grep -q "Adaptive Dual-Entry Intake" skills/crew-no-spec/SKILL.md && grep -q "diagnosing-bugs" skills/crew-no-spec/SKILL.md && grep -q "grilling" skills/crew-no-spec/SKILL.md && grep -q "mcp__graphify__" skills/crew-no-spec/SKILL.md`

## 2. Specialist Role Skills

- [x] 2.1 `skills/crew-role-worker/SKILL.md`: Unified Engineering Discipline (Graphify Sibling Seam Audit, Deep Modules & Domain Language, TDD at Public Seams) and the `Blast radius` handoff line; Before -> After evidence.
  - Evidence: anchors present; `git show 50cf7e1 -- skills/crew-role-worker/SKILL.md` adds both lines.
  - Proof: `cd "O:/workspaces/oss/crew" && grep -q "Unified Engineering Discipline" skills/crew-role-worker/SKILL.md && grep -q "TDD at Public Seams" skills/crew-role-worker/SKILL.md && grep -q "Blast radius" skills/crew-role-worker/SKILL.md`
- [x] 2.2 `skills/crew-role-content/SKILL.md`: Interactive Prototypes, Visual Architecture Reports (`improve-codebase-architecture` + `codebase-design`), Async Stakeholder Questionnaires.
  - Evidence: anchors present.
  - Proof: `cd "O:/workspaces/oss/crew" && grep -q "Interactive Prototypes" skills/crew-role-content/SKILL.md && grep -q "improve-codebase-architecture" skills/crew-role-content/SKILL.md`
- [x] 2.3 `skills/crew-verifier/SKILL.md`: Unified Verification Lenses (3D Specification & Seam Audit, TDD Anti-Tautology & Multi-Perspective Review, Graphify Impact Check) against `Inputs` including Exploration Documents.
  - Evidence: anchors present.
  - Proof: `cd "O:/workspaces/oss/crew" && grep -q "Unified Verification Lenses" skills/crew-verifier/SKILL.md && grep -q "TDD Anti-Tautology" skills/crew-verifier/SKILL.md`

## 3. CREW-INV-8 Static Anchors and Sync Gate

- [x] 3.1 Register the 12 CREW-INV-8 anchors in `O:/workspaces/.agents/skills/crew-upstream-sync/scripts/daily-sync-watchdog.ps1` and `references/invariant-checklist.md`; ship a read-only stdlib check in this change.
  - Evidence: `anchors=12 missing=0`, rc=0.
  - Proof: `cd "O:/workspaces/oss/crew" && python openspec/changes/unify-matt-openspec-graphify-skills/proofs/check_inv8_anchors.py .`
- [x] 3.2 Run the full upstream-sync verification gate (anchors, CREW-INV-7 probes, isolated invariant tests).
  - Evidence: `probes failed: 0`; `95 passed in 34.54s`; `Verification gate PASS (CREW-INV-1..8 preserved)`; `[RESULT] GATE PASS ... head=746f3f3e3381c0c14df80aa6143d355f4ea243d6`, rc=0.
  - Proof: `pwsh -NoProfile -File "O:/workspaces/.agents/skills/crew-upstream-sync/scripts/daily-sync-watchdog.ps1" -GateOnly`

## 4. OpenSpec Artifacts

- [x] 4.1 Author `.openspec.yaml`, `proposal.md`, `design.md`, delta specs for `crew-skills-regulations` and `crew-role-prompts`, and this `tasks.md`; validate strictly.
  - Evidence: `Change 'unify-matt-openspec-graphify-skills' is valid`, rc=0.
  - Proof: `cd "O:/workspaces/oss/crew" && openspec validate unify-matt-openspec-graphify-skills --strict`

## Workflow follow-up

- Do NOT run `openspec-sync-specs` or archive this change until the Commander explicitly approves; canonical `openspec/specs/` stays untouched.
- Multi-profile SHA-256 parity (`apply-live-crew-cutover.ps1`) is an operational rollout outside this change.
