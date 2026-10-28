# Exploration: Shareable Ticket Link & In-App Crew Detail Navigation (Option 2B)

- **Date**: 2026-10-28
- **Primary Project**: `crew` (`O:\workspaces\oss\crew`, `OPENSPEC_ROOT = O:\workspaces\oss\crew\openspec`)
- **Companion Seam**: `hermes-agent` (`O:\workspaces\oss\hermes-agent\apps\desktop\src\sdk\index.ts`)
- **Status**: Complete & Verified in Production Session `20261018_133507_6040a2`

## 1. Problem Statement & Settled Design Tree

When a new ticket is dispatched on the Kanban/Crew board, the ticket identifier (`t_<id>`) is formatted as a shareable Markdown hyperlink `[<id>](<dashboard>/crew?card=<id>)`:
- Right-click / Copy Link or external click opens `<dashboard>/crew?card=<id>`.
- Plain left-click inside Hermes Desktop is intercepted in capture phase (`desktop.tsx` `watchCardLinks`) to open/focus the dedicated `Crew` center tab (`asTile: true`) directly on `<CardPage id="<id>" />`.

## 2. Live Verification in Session `20261018_133507_6040a2`

- Message `[428860]` (`20261018_133507_6040a2`) emitted:
  `**Card open** · [t_821b36db](https://agent4070-dashboard.ptdev.vip/crew?card=t_821b36db) · [intel_nuc] Execute safe WSL storage cleanup and configure D: drive build targets`
- Clicking `t_821b36db` opened the Crew Detail Dashboard directly as designed.
- Note on trailing `> Open it in Crew...` in `[428860]`: `skills/crew/crew-no-spec/SKILL.md` was read fresh from disk (giving the shareable link `[t_821b36db](...)`), while the long-running Gateway Python process still held the pre-update `plugins/crew/__init__.py` (`_banner_open`) in memory until the next Gateway reload.
