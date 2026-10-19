---
name: crew-role-content
description: "Crew content pass: posts, reports, video, pages and social on a crew card; rendered artifact plus source."
version: 0.9.13
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
   `crew_verdict(card_id="<card id>")` (the proof command the card was
   opened with; editing the line on the card changes nothing). A `"verdict": "BLOCKED"` result means Hermes safety
   refused the proof and nothing ran (no verdict line): `kanban_block` with kind `needs_input` and the `blocked` reason.
5. Finish with the rendered artifact path, the source path and any figures with their source, by the canonical `Verify:`
   line:
   - `Verify: proof` - `kanban_complete` after the PASS (no verifier session; `crew_review_handoff` is refused; the
     coordinator runs the proof once more afterwards).
   - `Verify: independent` - `crew_review_handoff(card_id="<card id>", summary="<summary>")` (or `kanban_request_review`),
     never `kanban_complete`.
   - `Verify: dual` - on PASS of `crew_verdict`, call `crew_review_handoff(card_id="<card id>", summary="<summary>")`
     with output paths. Never `kanban_complete`.
   - `Verify: agent` - call `crew_review_handoff(card_id="<card id>", summary="<summary>")`.
   - `Verify: closeout` - (a part of a split, no proof of its own) `kanban_complete` with the paths.

## Content Tool Guidance

Content creators utilize the following native tools:

| Tool | When to Use | Arguments | Safety / Mutability | Next Action |
|---|---|---|---|---|
| `crew_verdict` | Execute verified proof command unattended | `card_id="<id>"` | Controlled execution | On PASS: complete or handoff |
| `crew_review_handoff` | Hand off deliverable to reviewer for `independent`, `dual`, `agent` modes | `card_id="<id>"`, `summary="..."` | Mutating (moves to review) | End turn |
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
