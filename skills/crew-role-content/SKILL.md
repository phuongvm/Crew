---
name: crew-role-content
description: "Crew content pass: posts, reports, video, pages and social on a crew card; rendered artifact plus source."
version: 0.10.1
---

# Crew content pass

Loaded on a crew card whose role is content (posts, reports, video, pages, every social channel).

## Do
1. Read the card: GOAL, `Done when`, the `Verify:` line, target channel and format.
2. Produce the artifact and keep its raw source next to it. Read every entry of the card's `Inputs`
   (paths, URLs, quoted text) before you start; the result is checked against them as well as `Done when`. A proof
   script the proof command names (`<folder>/.crew/<card folder>/verify.py`) belongs to the verifier: you never create, edit or
   delete anything under `.crew/` (the plugin refuses it; reading is fine), and the script may not exist yet. Fix the
   work, not the proof.
3. Render it the way the reader will see it (image, page, preview) and check the render yourself.
4. A card whose proof command runs a `.crew/` script is `Verify: independent` and its script is the verifier's to
   write: skip the verdict and go to step 5 (`crew_review_handoff`). Otherwise run the card's proof through the
   tool, never by hand, so the PASS/FAIL line lands in the verdict log:
   `crew_verdict(card="<card id>")` (the proof command the card was
   opened with; editing the line on the card changes nothing). A `"verdict": "BLOCKED"` result means Hermes safety
   refused the proof and nothing ran (no verdict line): `kanban_block` with kind `needs_input` and the `blocked` reason.
5. Finish with the rendered artifact path, the source path and any figures with their source, by the canonical `Verify:`
   line:
   - `Verify: proof` - `kanban_complete` after the PASS (no verifier session; `crew_review_handoff` is refused; the
     coordinator runs the proof once more afterwards).
   - `Verify: independent` - `crew_review_handoff(card_id="<card id>", summary="<summary>")` (or `kanban_request_review`),
     never `kanban_complete`.
   - `Verify: dual` - on PASS of `crew_verdict(card="<card id>")`, call `crew_review_handoff(card_id="<card id>", summary="<summary>")`
     with output paths. Never `kanban_complete`.
   - `Verify: agent` - **Not a valid content creator route**:
     `Verify: agent` is reserved exclusively for standalone cognitive review cards assigned directly to `@reviewer` (`Role: verifier`). A content card must never be `Verify: agent`. If an active content card is configured with `Verify: agent`, it is misrouted: do NOT attempt `kanban_request_review` or `crew_review_handoff` (the kernel review guard will refuse it). Instead, call `kanban_block(kind="needs_input", reason="misrouted card: Verify: agent is a standalone verifier card (Role: verifier assigned to @reviewer), not a content task. Reconfigure to Verify: dual for content tasks requiring independent reviewer audit.")` and stop.
   - `Verify: closeout` - (a part of a split, no proof of its own) `kanban_complete` with the paths.

## Verification Taxonomy: Canonical 5-Mode State Table

Content creators determine their delivery and handoff workflow based on the card's `Verify:` line:

| Mode | Verification Nature | Who Proves / Who Reviews | Content Completion Protocol |
|---|---|---|---|
| `proof` | Deterministic automated command (exit code 0) | Creator proves via `crew_verdict`; coordinator audits | On PASS: call `kanban_complete` with artifacts. `crew_review_handoff` is refused. |
| `independent` | Verifier-authored script (`.crew/<folder>/verify.py`) | Verifier writes script, runs `crew_verdict`, extra check | Skip verdict; call `crew_review_handoff`. Never `kanban_complete`. |
| `agent` | Standalone cognitive review or evaluation | Verifier (`@reviewer`) evaluates artifact vs criteria | Invalid content route. If assigned, call `kanban_block`. |
| `dual` | Automated tests PASS + independent reviewer audit | Creator runs `crew_verdict` PASS; verifier performs 2nd check | Run `crew_verdict` PASS, then call `crew_review_handoff`. Never `kanban_complete`. |
| `closeout` | Subtask part of a split plan with no proof of its own | Creator completes split subtask | Call `kanban_complete` directly. Aggregator/closeout card runs parent proof. |

## Pipeline Topologies: Single-Card Dual vs. Two-Card Chain Guidance for Content Creators

When working on deliverables that require editorial review or independent validation, content creators operate within one of two topologies:

| Feature | Single-Card Dual | Two-Card Chain |
|---|---|---|
| **Card Configuration** | Single card with `Verify: dual` | Card 1 with `Verify: proof` linked to Card 2 with `Verify: agent` |
| **Creator Assignment** | Creator assigned to the single card | Creator assigned to Card 1 only |
| **Verification Tool** | `crew_verdict` | `crew_verdict` |
| **Terminal Action** | `crew_review_handoff` | `kanban_complete` on Card 1 |
| **Completion Rule** | **FORBIDDEN** from calling `kanban_complete` | **REQUIRED** to call `kanban_complete` on Card 1 |
| **What Unblocks Review** | Card transitions to `review` column | Card 1 completion unblocks Card 2 in `todo (gated)` → `ready` |

### Working in Topology 1: Single-Card Dual (`Verify: dual`)
1. Create content deliverables (rendered artifact and raw source).
2. Run `crew_verdict(card="<id>")` to verify automated render/lint/proof command passes (exit code 0).
3. On PASS: You are **STRICTLY FORBIDDEN** from calling `kanban_complete`.
4. Call `crew_review_handoff(card_id="<id>", summary="<summary>")` (or `kanban_request_review`) with rendered artifact and source paths. This transfers the card to `@reviewer`.
5. If reviewer returns the card via `crew_request_changes(card_id="<id>", reason="<reason>")`, revise the content, re-verify with `crew_verdict(card="<id>")`, and hand off again via `crew_review_handoff(card_id="<id>", summary="<summary>")`.

### Working in Topology 2: Two-Card Chain (`Verify: proof` → `Verify: agent`)
1. Content creator is assigned Card 1 (`Role: content`, `Verify: proof`). A separate downstream review card (Card 2) is assigned to `@reviewer` (`Role: verifier`, `Verify: agent`, `parents=[card_1_id]`).
2. Run `crew_verdict(card="<id>")` to verify Card 1's proof command passes (exit code 0).
3. On PASS: Call `kanban_complete(summary="...", artifacts=[...])` with the artifact paths and raw proof output.
4. Calling `crew_review_handoff` on Card 1 is refused by the review guard (Card 1 is `Verify: proof`). Calling `kanban_complete` is **mandatory** because Card 1's completion is what releases Card 2 for `@reviewer`.

## Content Tool Guidance

Content creators utilize the following native tools:

| Tool | When to Use | Arguments | Safety / Mutability | Next Action |
|---|---|---|---|---|
| `crew_verdict` | Execute verified proof command unattended | `card="<id>"` | Controlled execution | On PASS: complete or handoff |
| `crew_review_handoff` | Hand off deliverable to reviewer for `independent`, `dual` modes | `card_id="<id>"`, `summary="..."` | Mutating (moves to review) | End turn |
| `crew_progress` | Mark multi-unit deliverable units | `card="<id>"`, `unit="..."`, `result="pass"`, `evidence="..."` | Mutating (updates units) | Continue next unit |
| `crew_status` | Inspect card state | `limit=10`, `format="text"\|"json"` | Read-only | Coordinate workflow |
| `crew_flow_graph` | Generate Mermaid dependency diagram | `card_id="<id>"`, `direction="TD"`, `format="mermaid"\|"json"` | Read-only | Inspect pipeline |
| `crew_lesson_record` | Record operational learning with validation | `action="add"\|"show"`, `role="content"`, `text="..."` | Mutating (appends lesson) | Finish card |
| `crew_lesson` | Quick lesson recording | `role="content"`, `text="..."` | Mutating (appends lesson) | Finish card |

## Never
- Publish or send without the owner's approval on the card.
- Use a number that is not computed or cited.
- Put internal data in anything outward-facing.
- Edit a skill file (crew's skills are shipped and overwritten on update). A lesson worth keeping: `crew_lesson(role=<role>, text="...")` (role = who it applies to: worker, content, verifier, coordinator or all).
