# Spec: Shareable Ticket Links & In-App Crew Detail Navigation

## Purpose

Eliminate manual navigation friction when Kanban/Crew tickets are opened or completed by turning every ticket identifier (`t_<id>`) in card-open and watcher/notifier messages into a shareable hyperlink (`[<id>](<dashboard>/crew?card=<id>)`) that opens the Crew Detail Dashboard directly, and intercepting plain left-clicks inside Hermes Desktop to open and focus the dedicated in-app Crew tab on that ticket without clobbering the active chat session.

## Requirements

### Requirement: Shareable Ticket Hyperlink in Card-Open Messages
When a Crew card is opened (`__init__.py` `_banner_open` and `skills/crew/SKILL.md`, `skills/crew-no-spec/SKILL.md`), the card-open message SHALL format the ticket identifier as a Markdown hyperlink pointing to the shareable Crew Detail Dashboard URL (`[<id>](<dashboard_url>/crew?card=<id>)`), and SHALL omit the manual navigation instruction blockquote.

#### Scenario: Card opened in Hermes Desktop chat
- **GIVEN** the user dispatches a Crew card with ID `t_d8403bb8` and title `Fix 9router Claude double-folded prompt_tokens & Antigravity cache locality` in Hermes Desktop
- **AND** `crew_card.dashboard_url()` resolves to `https://crew.example.test`
- **WHEN** `crew_intake_preload` constructs the card-open reply instructions via `_banner_open("desktop")`
- **THEN** the card-open template SHALL render the ticket ID as `[t_d8403bb8](https://crew.example.test/crew?card=t_d8403bb8)`
- **AND** the message SHALL NOT include the manual blockquote `> Open it in Crew: the Crew entry in the sidebar, or preview it with Ctrl+J`.

#### Scenario: Helper `card_md_link` formats shareable Markdown anchor
- **GIVEN** a card ID `t_d8403bb8` and a resolved dashboard URL
- **WHEN** `crew_card.card_md_link("t_d8403bb8", base="https://crew.example.test")` is called
- **THEN** it SHALL return `"[t_d8403bb8](https://crew.example.test/crew?card=t_d8403bb8)"`.

---

### Requirement: Shareable Ticket Hyperlink in Watcher and Notifier Messages
When `crew_notify.py` (`_text_md` for Markdown / Hermes Desktop) formats a card completion, abandonment, or owner-question report, the ticket identifier (`tid`) and any parent `From card:` identifier (`src`) SHALL be formatted as shareable Markdown hyperlinks (`[<id>](<dashboard_url>/crew?card=<id>)`), and the manual navigation blockquote SHALL be omitted.

#### Scenario: Watcher reports a completed card in Hermes Desktop (`--md`)
- **GIVEN** card `t_d8403bb8` transitions to `done` and `crew_card.py watch --card t_d8403bb8 --md` formats the ending message
- **WHEN** `crew_notify._text_md` builds the Markdown output
- **THEN** the lead line SHALL be `**Done** · [t_d8403bb8](<dashboard_url>/crew?card=t_d8403bb8) · <title>`
- **AND** if a parent card `src` is present (`src != tid`), the provenance line SHALL be `From card: [<src>](<dashboard_url>/crew?card=<src>) (this card was created under it)`
- **AND** the output SHALL NOT append `> Open it in Crew: the Crew entry in the sidebar, or preview it with Ctrl+J`.

---

### Requirement: Capture-Phase In-App Click Interception in Hermes Desktop (Option 2B)
When the Crew Desktop plugin (`desktop/plugin.js`, built from `ui/src/desktop.tsx` and `ui/src/open-card.ts`) is registered in Hermes Desktop, it SHALL intercept unmodified primary left-clicks on any anchor (`<a href="...">`) outside Crew's internal board/card controls whose `href` targets `/crew?card=<id>` and navigate the in-app Crew view directly to `<CardPage id="<id>" />`, while preserving native browser and clipboard behavior for modified clicks and context-menu actions.

#### Scenario: User left-clicks a shareable ticket link in Hermes Desktop chat
- **GIVEN** `desktop/plugin.js` is registered in Hermes Desktop with `host.navigate` available
- **AND** a chat message contains `<a href="https://crew.example.test/crew?card=t_d8403bb8">t_d8403bb8</a>`
- **WHEN** the user performs an unmodified left-click (`button === 0`, no `ctrlKey`, `metaKey`, `shiftKey`, or `altKey`) on that link
- **THEN** the capture-phase listener SHALL call `event.preventDefault()` so `<ExternalLink>` does not open an external or preview browser
- **AND** SHALL dispatch `t_d8403bb8` through `openCardRoute` and `host.navigate(cardLink("t_d8403bb8"))`
- **AND** `<CrewPage>` SHALL display `<CardPage id="t_d8403bb8" />`.

#### Scenario: User Ctrl/Cmd-clicks, middle-clicks, or right-clicks the ticket link
- **GIVEN** a chat message contains `<a href="https://crew.example.test/crew?card=t_d8403bb8">t_d8403bb8</a>`
- **WHEN** the user Ctrl-clicks, Cmd-clicks, middle-clicks (`button === 1`), or opens the context menu ("Copy Link")
- **THEN** the capture-phase listener SHALL NOT call `event.preventDefault()`
- **AND** the anchor's full shareable `href` SHALL be preserved for copying or opening in the native browser.

---

### Requirement: Desktop `asTile: true` Route Tile Navigation Without Clobbering Active Chat
When `host.navigate(path)` is invoked in Hermes Desktop (`apps/desktop/src/sdk/index.ts`) for a contributed route whose `SIDEBAR_NAV_AREA` registration declares `asTile: true` (such as `/crew`), `host.navigate` SHALL open or reveal the dedicated route tile (`openRouteTile(basePath, 'center')`) so the active chat session in `workspace` is preserved alongside the Crew tab.

#### Scenario: Navigating to `/crew?card=t_d8403bb8` when Crew has `asTile: true`
- **GIVEN** the user is viewing a chat session in the `workspace` pane and Crew is registered in `SIDEBAR_NAV_AREA` with `{ path: '/crew', asTile: true }`
- **WHEN** `host.navigate('/crew?card=t_d8403bb8&n=123')` is called
- **THEN** `openRouteTile('/crew', 'center')` SHALL open or focus `route-tile:/crew` in the center dock
- **AND** `<CrewPage>` inside `route-tile:/crew` SHALL receive `t_d8403bb8` via `openCardRoute` (`onOpenCard` / `takePendingCard`) and render `<CardPage id="t_d8403bb8" />`.
