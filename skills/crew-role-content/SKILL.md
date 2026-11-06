---
name: crew-role-content
description: "Create crew card content: reports, pages, posts, and media."
version: 0.10.7
---
# Crew content pass

Loaded on a crew card whose role is content (posts, reports, video, pages, every social channel).

## When to Use
Any crew card with `Role: content`: produce the artifact the reader will see, judged by the card's `Done when` and proof command.

## Do
1. Read the card: GOAL, `Done when`, `Verify:` line, target channel/format, every `Inputs` entry (paths, URLs, quoted text, exploration docs).
2. Produce the artifact and keep its raw source next to it. Apply the matching pattern: interactive prototypes (`prototype`, single self-contained HTML), visual architecture reports (`improve-codebase-architecture` + `codebase-design`, Before/After diagrams), async questionnaires (`to-questionnaire`). Never touch `.crew/`.
3. Render it the way the reader will see it (image, page, preview) and check the render yourself.
4. Run the proof through the tool, never by hand: `crew_verdict(card="<card id>")`. `"verdict": "BLOCKED"` → `kanban_block(kind="needs_input")`.
5. Finish with rendered path, source path and figure sources by the `Verify:` line — `proof`: `kanban_complete` · `independent`: skip verdict, `crew_review_handoff` · `dual`: `crew_verdict` PASS then `crew_review_handoff` (never `kanban_complete`) · `agent`: misrouted, `kanban_block` · `closeout`: `kanban_complete`. Two FAILs → `kanban_block` and end.

## Handoff summary (mandatory)
`- Done:` rendered artifact path, raw source path · `- Not done:` · `- Evidence:` crew_verdict PASS/FAIL (rc) and render/source checks · (`kanban_block` adds `- Decision needed:`).

## Never
Edit `.crew/`, change the proof line, self-complete a `dual`/`independent` card, ship an unrendered artifact, or skip `crew_verdict`.

5-mode verification table, pipeline topologies and content tool guidance: `references/content-pass.md`.
