import * as sdk from '@hermes/plugin-sdk'
import type { MouseEvent, PointerEvent } from 'react'
import type { CrewApi } from '../api'
import { injectCss } from '../css'
import { useBoard } from '../data'
import { CREW_ROUTE, cardUrl } from '../open-card'
import { liveTiles, type Board, type Tile } from '../types'

// The global Crew chip in Desktop's status bar (STATUSBAR_AREAS.right): the Crew icon and how many tickets are running on
// the Kanban board, whatever chat session is showing. A radar sweep rings the chip while it shows; it hides when nothing
// runs (open-but-idle and done tickets never light it). One click opens the Crew tab. Desktop only: browser.tsx never mounts it.
// CrewSessionRowChip (below) is the same chip on a sidebar session row, counting only that session's running tickets.
export interface CrewChipState {
  visible: boolean
  count: number     // running tickets; the chip shows only while at least one runs, so count === running
  running: number
  radar: boolean
  title: string
}

// The chip's tooltip, one wording for the status bar chip and every session-row chip.
export function formatCrewChipTitle(running: number): string {
  return 'Crew: ' + running + ' running ticket' + (running === 1 ? '' : 's')
}

export function crewChipState(board: Board | null): CrewChipState {
  if (!board) return { visible: false, count: 0, running: 0, radar: false, title: 'Crew' }
  const running = Math.max(board.counts?.running ?? 0, board.live ?? 0, liveTiles(board).length)
  return { visible: running > 0, count: running, running, radar: running > 0, title: running > 0 ? formatCrewChipTitle(running) : 'Crew' }
}

export interface CrewSessionChipState extends CrewChipState {
  target: string    // where a click goes: the card of the session's single running ticket, else the Crew board
}

// One chat session's running tickets (its tiles by session_id, status 'running' or a live run; never archived or a
// proof-suite test card). Open-but-idle and done tickets are not counted: with none running the chip is hidden, however
// many tickets the session has. Another session's run does not light this row.
export function crewSessionChipState(board: Board | null, sessionId: string): CrewSessionChipState {
  const hidden: CrewSessionChipState = { visible: false, count: 0, running: 0, radar: false, title: 'Crew', target: CREW_ROUTE }
  if (!board || board.error || !sessionId) return hidden
  const live = new Map<string, Tile>()
  for (const lane of board.lanes ?? []) {
    if (lane.key === 'archived') continue
    for (const t of lane.tiles)
      if (t.session_id === sessionId && t.status !== 'archived' && !t.test && (t.status === 'running' || Boolean(t.active))) live.set(t.id, t)
  }
  const tiles = [...live.values()]
  const running = tiles.length
  if (!running) return hidden
  return { visible: true, count: running, running, radar: true, title: formatCrewChipTitle(running), target: running === 1 ? cardUrl(CREW_ROUTE, tiles[0].id) : CREW_ROUTE }
}

// @property --crew-arc and @keyframes crewarc are the board's own (styles/board.css) restated word for word, because the
// chip lives in the status bar where the board stylesheet may not be loaded; the same definition twice is harmless.
const CHIP_CSS =
  '@property --crew-arc { syntax: "<angle>"; inherits: false; initial-value: 0deg; }' +
  '@keyframes crewarc { to { --crew-arc: 360deg; } }' +
  '@keyframes crewglow { 0%, 100% { opacity: 1; } 50% { opacity: 0.55; } }' +
  '.crew-chip { position: relative; display: flex; align-items: center; gap: 5px; border: 0; background: none; cursor: pointer; font-size: 11px; align-self: center; flex-shrink: 0; height: 16px; margin: 0 2px; padding: 0 6px; box-sizing: border-box; line-height: 1; border-radius: 4px; color: var(--ui-text-tertiary); }' +
  '.crew-chip:hover { color: var(--ui-text-primary); }' +
  '.crew-chip b { font-weight: 600; color: var(--ui-accent, #60a5fa); }' +
  '.crew-chip.live { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--ui-success, #22c55e) 28%, transparent); }' +
  '.crew-chip.live::after { content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1px; pointer-events: none;' +
  ' background: conic-gradient(from var(--crew-arc), transparent 0 68%, var(--ui-success, #22c55e) 88%, transparent 100%);' +
  ' -webkit-mask: linear-gradient(rgb(0 0 0 / 0.78) 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask: linear-gradient(rgb(0 0 0 / 0.78) 0 0) content-box exclude, linear-gradient(#000 0 0);' +
  ' animation: crewarc 2.2s linear infinite; }' +
  '.crew-chip.live .codicon, .crew-chip.live svg { color: var(--ui-success, #22c55e); animation: crewglow 2.2s ease-in-out infinite; }' +
  '@media (prefers-reduced-motion: reduce) { .crew-chip.live, .crew-chip.live::after, .crew-chip.live .codicon, .crew-chip.live svg { animation: none; } }'

// The icon: the app's Codicon `organization` when the shell exports it, else three joined dots (an org chart) inline.
function CrewIcon() {
  const Codicon = sdk.Codicon
  if (Codicon) return <Codicon name="organization" />
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden="true">
      <circle cx="8" cy="3.5" r="1.8" />
      <circle cx="3.5" cy="12.5" r="1.8" />
      <circle cx="12.5" cy="12.5" r="1.8" />
      <path d="M8 5.3v2.7M8 8H3.5v2.7M8 8h4.5v2.7" />
    </svg>
  )
}

export function CrewStatusChip({ api, navigate }: { api: CrewApi; navigate: (path: string) => void }) {
  const { board } = useBoard(api, 5000)
  const state = crewChipState(board)
  if (!state.visible) return null
  injectCss('chip', CHIP_CSS)
  return (
    <button
      type="button"
      className={'crew-chip' + (state.radar ? ' live' : '')}
      data-crew-chip="true"
      data-radar={state.radar ? 'running' : undefined}
      title={state.title}
      onClick={() => navigate(CREW_ROUTE)}
    >
      <CrewIcon />
      <b>{state.count}</b>
    </button>
  )
}

// The same chip on a sidebar session row (SESSION_ROW_AREAS.trailing): that session's running tickets only, the radar
// while it shows, nothing at all when none of them runs. The row is draggable and a plain click resumes the session, so the
// chip swallows the pointer and the click; it opens the card (one running ticket) or the Crew board (several).
export function CrewSessionRowChip({ api, sessionId, navigate }: { api: CrewApi; sessionId: string; navigate: (path: string) => void }) {
  const { board } = useBoard(api, 5000)
  const state = crewSessionChipState(board, sessionId)
  if (!state.visible) return null
  injectCss('chip', CHIP_CSS)
  return (
    <button
      type="button"
      className={'crew-chip' + (state.radar ? ' live' : '')}
      data-crew-session-chip={sessionId}
      data-radar={state.radar ? 'running' : undefined}
      title={state.title}
      onPointerDown={(e: PointerEvent) => e.stopPropagation()}
      onClick={(e: MouseEvent) => { e.preventDefault(); e.stopPropagation(); navigate(state.target) }}
    >
      <CrewIcon />
      <b>{state.count}</b>
    </button>
  )
}
