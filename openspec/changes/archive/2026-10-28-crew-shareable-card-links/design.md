# Design: Shareable Ticket Link & In-App Crew Detail Navigation (`crew-shareable-card-links`)

## Deep-Module Seams

1. **Outward Link Producer (`scripts/crew_card.py`, `scripts/crew_notify.py`, `__init__.py`, `skills/`)**:
   - `crew_card.card_md_link(card_id, base=None)` formats `"[<id>](<dashboard>/crew?card=<id>)"`.
   - `_banner_open("desktop")` and `crew_notify._text_md` embed the shareable link directly on `<id>` and omit the `> Open it in Crew...` blockquote.
2. **Capture-Phase Click Interception & Card Selection Bus (`ui/src/open-card.ts`, `ui/src/desktop.tsx`, `ui/src/components/CrewPage.tsx`)**:
   - `cardFromHref(href)` extracts valid `CARD_ID` values from `/crew?card=<id>` URLs.
   - `openCardRoute(path, navigate)` updates `pendingCard` and notifies `onOpenCard` subscribers before calling `host.navigate(path)`.
   - `watchCardLinks(doc)` in `ui/src/desktop.tsx` listens on `document` in capture phase (`true`), intercepts unmodified primary clicks (`button === 0`, no modifier keys) on `<a href=".../crew?card=<id>">` outside `.crew-scope`, calls `e.preventDefault()`, and dispatches `openCardRoute`.
3. **Desktop `asTile: true` Route Tile Navigation (`apps/desktop/src/sdk/index.ts`)**:
   - `host.navigate(path)` checks if `routePathname(to)` matches a `SIDEBAR_NAV_AREA` contribution with `asTile: true` and calls `openRouteTile(basePath, 'center')` so the active chat session route in `workspace` is preserved.
