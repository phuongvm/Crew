# Proposal: Shareable Ticket Link & In-App Crew Detail Navigation (`crew-shareable-card-links`)

## Why

When a Kanban/Crew card is opened or finishes, the chat message previously rendered the card identifier (`t_d8403bb8`) as static inline code (`` `t_d8403bb8` ``) and appended a manual instruction footer (`> Open it in Crew: the Crew entry in the sidebar, or preview it with Ctrl+J`). Users could neither click the ticket ID directly to inspect its Crew Detail Dashboard nor right-click the ticket ID to copy a shareable link.

## What Changes

1. **Direct Shareable Ticket Hyperlink in Card Messages (`oss/crew`)**:
   - Add `crew_card.card_md_link(card_id, base=None)` returning `"[<id>](<dashboard_url>/crew?card=<id>)"`.
   - Update `__init__.py` (`_link_line`, `_desktop_id_ref`, `_banner_open`), `scripts/crew_notify.py` (`_text_md`), `skills/crew/SKILL.md`, and `skills/crew-no-spec/SKILL.md` so both `**Card open**` and watcher/notifier completion headers embed the shareable link directly on the ticket ID (`[t_d8403bb8](<dashboard>/crew?card=t_d8403bb8)`) and omit the manual instruction blockquote.
2. **Hybrid In-App Hermes Desktop Tab Interception (`oss/crew/ui/src` — Option 2B)**:
   - Extend `ui/src/open-card.ts` with `cardFromHref(href: string): string` and an in-memory card-selection bus (`openCardRoute`, `takePendingCard`, `onOpenCard`).
   - Register a capture-phase document click listener (`watchCardLinks`) in `ui/src/desktop.tsx` that intercepts unmodified primary left-clicks (`button === 0`, no modifier keys) on `<a href=".../crew?card=<id>">`, calls `event.preventDefault()`, and opens the card in the in-app Crew tab while preserving native Copy Link and Ctrl/Cmd-click behavior.
3. **Desktop `asTile: true` Route Tile Navigation (`oss/hermes-agent/apps/desktop`)**:
   - Update `host.navigate(path)` in `apps/desktop/src/sdk/index.ts` so routes whose `SIDEBAR_NAV_AREA` contribution declares `asTile: true` (such as `/crew`) invoke `openRouteTile(basePath, 'center')` without clobbering the active chat session route.

## Capabilities

### New Capabilities
- `crew-shareable-card-links`: Governs shareable `[<id>](<dashboard>/crew?card=<id>)` ticket links in card-open and watcher/notifier messages, capture-phase in-app Desktop click interception, and `asTile: true` center-tab routing.

### Modified Capabilities
- `crew-pane-default-off-and-dynamic-endpoint`: Aligns card detail URL specification with `/crew?card=<id>` and in-app Desktop tab navigation.
