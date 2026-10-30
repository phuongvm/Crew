# Proposal: Unify Matt Pocock Skills, OpenSpec Governance and Graphify MCP into the Crew Skills

## Why

Four capability pillars were used side by side but not wired together: Matt Pocock engineering skills (`diagnosing-bugs`, `grilling`, `codebase-design`, `domain-modeling`, `to-spec`, `to-tickets`, `tdd`, `code-review`, `pr`, `prototype`, `wizard` and others), OpenSpec workflow governance (`openspec-explore`, `-propose`, `-verify-change` and others), Graphify MCP codebase intelligence (`mcp__graphify__*`), and the Crew plugin skills.

Two concrete frictions (see `openspec/workspace/explorations/2026-10-29-crew-matt-openspec-unification-exploration.md`):

1. `crew-no-spec` v0.10.2 enforced a rigid "Turn-1 Dispatch Mandate" that forbade any exploring or diagnosing before a card existed and ignored an Exploration Document already produced in chat.
2. No Crew skill told the coordinator or the specialist roles when to use Graphify on a large codebase, when `diagnosing-bugs` applies instead of `grilling` + `codebase-design`, how to slice work (`to-tickets`), or how to enforce `tdd` at public seams in worker execution and verifier review.

Commit `50cf7e1969721e6e7f3bce8c4dbe80a59867fc14` ("feat(skills): unify Matt Pocock, OpenSpec, and Graphify MCP into Crew skills (CREW-INV-8)") delivered the five skill edits. This change records that behavior as OpenSpec deltas so the sync gate and future upstream merges preserve it.

## What Changes

1. **`skills/crew/SKILL.md`**: adds section 0.1 "Unified Cognitive & Tool Routing Matrix"; Phase 1 Explore reuses an existing Exploration Document (Exploration Doc continuity) and runs Graphify first; Phase 2/3 apply `to-spec` / `to-tickets`; card `Inputs:` carries the change directory AND the Exploration Document; Track B documents the dual-entry intake.
2. **`skills/crew-no-spec/SKILL.md`** (0.10.2 -> 0.10.5): replaces the Turn-1-only mandate with "Adaptive Dual-Entry Intake": Mode 1 (Exploration-Backed or Clear-Target Fast-Path, Turn-1 dispatch) and Mode 2 (Guided Discovery & Root-Cause Loop: project gate, Graphify, auto-routed Matt skills, persisted Exploration Document, then dispatch). Formal OpenSpec artifacts stay bypassed; the debrief offers optional late spec promotion.
3. **`skills/crew-role-worker/SKILL.md`**: "Unified Engineering Discipline" (Graphify Sibling Seam Audit, Deep Modules & Domain Language, "TDD at Public Seams") and a `Blast radius` line in the structured handoff.
4. **`skills/crew-role-content/SKILL.md`**: "Interactive Prototypes", visual architecture reports (`improve-codebase-architecture`) and async questionnaires.
5. **`skills/crew-verifier/SKILL.md`**: "Unified Verification Lenses" (3D spec and seam audit, "TDD Anti-Tautology" and multi-perspective review, Graphify impact check).
6. **CREW-INV-8 static anchors**: 12 required strings across the five skills are enforced by `.agents/skills/crew-upstream-sync/scripts/daily-sync-watchdog.ps1` and listed in `references/invariant-checklist.md`.

No Python/JS runtime code changes. The verifier-written `.crew/` proof boundary, Zero-Checkout invariant and all of `CREW-INV-1..7` are unchanged.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `crew-skills-regulations`: modifies "Fast-Track Direct Dispatch Protocol" (Turn-1-only becomes Adaptive Dual-Entry Intake); adds the Unified Cognitive & Tool Routing Matrix, Exploration Document continuity and CREW-INV-8 static anchor requirements.
- `crew-role-prompts`: adds role-skill requirements for worker (Unified Engineering Discipline), content (design and discovery patterns) and verifier (Unified Verification Lenses).

## Impact

- **Files**: `skills/{crew,crew-no-spec,crew-role-worker,crew-role-content,crew-verifier}/SKILL.md` (commit `50cf7e1`), `.agents/skills/crew-upstream-sync/{scripts/daily-sync-watchdog.ps1,references/invariant-checklist.md}`.
- **Blast radius**: two-way door (prompt text); callers are every coordinator/worker/content/verifier session that loads these skills. A future upstream merge that drops an anchor is caught by the sync gate.
- **Provenance**: exploration document above; implementation commit `50cf7e1`; sync gate run on HEAD `746f3f3` in this card: `GATE PASS`, 95 invariant tests passed.
