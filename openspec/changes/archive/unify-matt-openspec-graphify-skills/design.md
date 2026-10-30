# Design: Unified Matt Pocock + OpenSpec + Graphify Routing inside the Crew Skills

## 1. Problem Statement

Crew skills are the coordinator's and specialists' operating prompts. Before this change they ignored the surrounding skill ecosystem: `crew-no-spec` forced Turn-1 dispatch even when discovery was needed and ignored an Exploration Document produced in chat, and no skill said which cognitive skill or Graphify tool to use for which task. The exploration document (`openspec/workspace/explorations/2026-10-29-crew-matt-openspec-unification-exploration.md`) settled the approach; this design records it.

## 2. Deep Module Shape

The module is each `SKILL.md`; its interface is the section vocabulary the model reads, and its seam is the file path loaded by name. The routing logic is embedded rather than split into a new skill, because a coordinator loading `crew` must get the matrix without a second load that can be skipped.

| Skill | Added interface | Hidden behavior |
|---|---|---|
| `crew` | section 0.1 Unified Cognitive & Tool Routing Matrix; Phase 1 continuity; `to-spec` / `to-tickets` in Phase 2-3 | skill and tool selection per context |
| `crew-no-spec` | Adaptive Dual-Entry Intake (Mode 1 fast-path, Mode 2 guided loop); Automatic Cognitive & Tool Routing Matrix | Graphify-first recon, repro probe, exploration persistence |
| `crew-role-worker` | Unified Engineering Discipline; `Blast radius` handoff line | seam audit, Red -> Green slices |
| `crew-role-content` | Interactive Prototypes and visual-report patterns | prototype and report scaffolds |
| `crew-verifier` | Unified Verification Lenses | 3D audit, anti-tautology, impact check |

## 3. Decisions

1. **Dual entry, not removal of the fast path**: Mode 1 keeps Turn-1 dispatch when a target and end state are named or an Exploration Document exists; Mode 2 explores first only when facts are missing. Rejected: always exploring (slows hotfixes), always dispatching (the old failure).
2. **Facts are the agent's job**: bug or metric causes are found by a read-only repro probe under five seconds with cleanup, never by asking the Commander.
3. **Exploration Document is the handoff artifact**: path goes into `Inputs:`, so worker and verifier judge against it; it replaces `proposal.md`/`design.md`/`tasks.md` in no-spec mode, and `/crew` reuses it as Phase 1.
4. **Static anchors over behavior tests for prompt text**: CREW-INV-8 lists 12 literal strings enforced by the existing watchdog gate (`daily-sync-watchdog.ps1`), the same mechanism as CREW-INV-1..7. A literal anchor is cheap, deterministic and fails on a merge that silently drops the text.
5. **Zero-Checkout and `.crew/` boundaries untouched**: the new text adds discipline, never relaxes a prohibition.

## 4. Public Testing Seams

1. The five `skills/*/SKILL.md` files: anchor presence via `proofs/check_inv8_anchors.py` (12 anchors).
2. Gate: `daily-sync-watchdog.ps1 -GateOnly` (anchors + CREW-INV-7 probes + isolated invariant tests, `CREW-INV-1..8 preserved`).
3. Frontmatter/version parity tests under `tests/` run by the gate.

## 5. Risks

- Prompt growth: `crew` and `crew-no-spec` are longer; mitigated by tables over prose and by keeping one matrix per skill.
- Matrix drift between `crew` and `crew-no-spec`: both are covered by anchors; a later change should dedupe if they diverge.
- Skills named in the matrix may not be installed on every profile: the matrix names capabilities, and a missing skill degrades to the base Crew behavior.

## 6. Out of Scope

Python/JS runtime changes, changing the `Verify:` taxonomy, new Crew tools, multi-profile cutover (`apply-live-crew-cutover.ps1`) and syncing these deltas into canonical `openspec/specs/` (separate Commander approval).
