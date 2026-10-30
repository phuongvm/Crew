# Exploration: Unifying Matt Pocock Skills, OpenSpec Governance, and Graphify MCP into Crew Plugin Skills

- **Date**: 2026-10-29
- **Project**: `O:/workspaces/oss/crew`
- **Status**: Approved for Implementation (Steps 1 & 2)

## 1. Problem Statement

Currently, our engineering and operational workflows span four distinct capability pillars:
1. **Matt Pocock Skills (`O:/workspaces/oss/skills-mattpocock/skills/`)**: High-leverage cognitive and engineering disciplines (`diagnosing-bugs`, `grilling`, `grill-with-docs`, `codebase-design`, `improve-codebase-architecture`, `domain-modeling`, `triage`, `to-spec`, `to-tickets`, `implement`, `implement-spec`, `tdd`, `code-review`, `pr`, `prototype`, `wayfinder`, `wizard`, `retro`, `wait-what`, `to-questionnaire`).
2. **OpenSpec Workflow Governance (`.agents/skills/openspec/` & `rules/skills/`)**: Structured artifact persistence and specification lifecycle (`activate-project`, `openspec-zero-trust-baseline`, `openspec-explore`, `openspec-propose`, `openspec-apply-change`, `openspec-verify-change`, `openspec-sync-specs`, `openspec-archive-change`, `openspec-director`, `openspec-developer`, `openspec-verifier`).
3. **Codebase Intelligence (`graphify-knowledge-graph` & `gsd-ns-context`)**: Fast AST/graph navigation over large repositories via `mcp__graphify__*` (`graph_stats`, `god_nodes`, `query_graph`, `get_neighbors`, `get_community`, `shortest_path`, `get_pr_impact`).
4. **Crew Plugin (`O:/workspaces/oss/crew/skills/`)**: Multi-agent Kanban execution with deterministic proof verification (`crew`, `crew-no-spec`, `crew-role-worker`, `crew-role-content`, `crew-verifier`, `crew-diagnose`).

### Root Cause of Operational Friction
- `crew-no-spec/SKILL.md` v0.10.2 enforced a rigid "Turn-1 Dispatch Mandate (Zero Autonomous Chat Execution)" that forbade exploring, diagnosing, or synthesizing an exploration document before creating a Kanban card, and ignored any pre-existing Exploration Document produced during interactive chat.
- Neither `crew` nor `crew-no-spec` contained an automatic **Cognitive & Tool Routing Matrix** telling the coordinator and specialist roles when to invoke `mcp__graphify__*` on large codebases, when to use `diagnosing-bugs` vs. `grilling` + `codebase-design`, how to slice work via `to-tickets`, or how to enforce `tdd` at public seams during worker execution and verifier review.

## 2. Solution Architecture & Seam Design

We embed the unified routing and execution rules directly inside the five core Crew skills (`crew`, `crew-no-spec`, `crew-role-worker`, `crew-role-content`, `crew-verifier`) while preserving 100% of `CREW-INV-1..7` anchors.

### 2.1 Shared Interactive Exploration & Context Continuity (`crew` & `crew-no-spec`)
- **Exploration Document Continuity**: Both `/crew` and `/crew-no-spec` check whether the current conversation or `<project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` already holds a crystallized exploration artifact.
  - If an Exploration Document already exists and settles scope/target/done-when:
    - `/crew-no-spec` enters **Mode 1 (Fast-Path / Exploration-Backed Dispatch)**: immediately opens the contract card(s) in Turn 1 with `Inputs: <exploration_doc_path>` (skipping `proposal.md`, `specs/`, `design.md`, `tasks.md`).
    - `/crew` reuses the existing Exploration Document as Phase 1 completion and advances directly to Phase 2 (`openspec-propose`).
  - If the ask is an uninvestigated bug, an open architectural question, or a multi-part feature needing discovery:
    - Both tracks run the **Guided Discovery & Root-Cause Loop**:
      - **Large Codebase Navigation**: Use `mcp__graphify__graph_stats`, `god_nodes`, `query_graph`, `get_neighbors`, `shortest_path` first instead of blind recursive `grep -r`/`find`.
      - **Defect / Anomaly Routing**: Pair `openspec-explore` with Matt's `diagnosing-bugs` + `triage` (run a `< 5s` empirical reproduction probe to isolate the root cause; never ask the Commander why a bug happens).
      - **Feature / Architecture Routing**: Pair `openspec-explore` with Matt's `grilling` (frontier decision rounds `❓ Q1 ... ➡️ Recommended`), `codebase-design` (deep modules, public seams), `domain-modeling` (`GLOSSARY.md` / ADRs), and `prototype` (when UI/state-machine feel needs validation).
      - **Persistence**: Scaffold `<project>/openspec/workspace/explorations/YYYY-MM-DD-<topic>-exploration.md` early via `write_file` and incrementally `patch` every 3–5 read/search calls (preventing Nerve progress guard pauses), structured using Matt's `to-spec` sections (Problem Statement, Solution, Public Testing Seams, Implementation Decisions, Testing Decisions, Out of Scope).
- **Task Slicing & Human Setup**:
  - Multi-part work is decomposed using Matt's `to-tickets` discipline (vertical tracer-bullet slices or expand–contract batches for wide refactors) via `crew_plan_split`.
  - Manual human setup/credential steps generate an interactive bash script via Matt's `wizard` skill.

### 2.2 Worker Execution Discipline (`crew-role-worker`)
- **Graphify Sibling Seam Audit**: Use `mcp__graphify__get_neighbors` on modified symbols to inspect callers/callees and fix the entire bug class across sibling call paths.
- **TDD at Pre-Agreed Public Seams (`tdd` + `codebase-design` + `openspec-developer`)**:
  - Test external behavior at public seams defined in `Inputs:` / `Done when:`, never internal implementation details or tautological assertions.
  - Follow Red → Green per vertical slice, keeping changes surgical (`openspec-developer`).
- **PR-Grade Structured Handoff (`pr`)**: Include `Before -> After` execution evidence, call-tree/diff sketch when helpful, and `Blast Radius (One-way vs. Two-way door)` in the structured completion/handoff summary.

### 2.3 Content & Prototype Discipline (`crew-role-content`)
- Integrate Matt's `prototype` (interactive HTML logic demo or multi-variant UI switchable bar), `improve-codebase-architecture` (Tailwind + Mermaid before/after deepening cards), and `to-questionnaire` (async stakeholder discovery docs).

### 2.4 Independent Verification Discipline (`crew-verifier`)
- Combine Crew's `crew_verdict` + `Zero-Checkout` worktree gate with:
  - **OpenSpec 3-Dimension Audit (`openspec-verify-change`)**: Completeness, Correctness, Coherence against `Inputs:` (including the Exploration Document or OpenSpec specs).
  - **Matt's `tdd` & `code-review` Audit**: Reject tautological tests or implementation-coupled mocks; evaluate across Product, Lead Eng, QA, Security, DevOps, and UX perspectives; use `mcp__graphify__get_pr_impact` on code changes to verify zero unbroken downstream callers.

## 3. Public Testing Seams & Verification Plan
- **Seam 1**: `O:/workspaces/oss/crew/skills/{crew,crew-no-spec,crew-role-worker,crew-role-content,crew-verifier}/SKILL.md`
- **Verification**:
  - Static anchor verification via `O:/workspaces/.agents/skills/crew-upstream-sync/scripts/daily-sync-watchdog.ps1 -GateOnly`.
  - Hermetic pytest invariant suite on `O:/workspaces/oss/crew/tests/`.
  - Multi-profile SHA-256 parity verification across all 7 Hermes profiles via `apply-live-crew-cutover.ps1`.
