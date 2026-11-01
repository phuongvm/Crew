import * as sdk from '@hermes/plugin-sdk'
import type { MouseEvent, PointerEvent } from 'react'
import type { CrewApi } from '../api'
import { injectCss } from '../css'
import { useBoard } from '../data'
import { CREW_ROUTE, cardUrl } from '../open-card'
import { liveTiles, type Board, type Tile } from '../types'

// The global Crew chip in Desktop's status bar (STATUSBAR_AREAS.right): the Crew icon and how many tickets are open on
// the Kanban board, whatever chat session is showing. A radar sweep rings the chip while any ticket runs; it hides when
// nothing is open. One click opens the Crew tab. Desktop only: browser.tsx never mounts it.
// CrewSessionRowChip (below) is the same chip on a sidebar session row, counting only that session's tickets (done ones
// too, as a static badge while nothing of the session runs; only archived and proof-suite test cards are left out).
const CLOSED = ['done', 'archived']

export interface CrewChipState {
  visible: boolean
  count: number     // open tickets (everything except done and archived); at least the running ones
  running: number
  radar: boolean
  title: string
}

// The chip's tooltip, one wording for the status bar chip and every session-row chip.
export function formatCrewChipTitle(count: number, running: number): string {
  return 'Crew: ' + count + ' open ticket' + (count === 1 ? '' : 's') + (running ? ' · ' + running + ' running' : '')
}

// Open = the board's counts minus done and archived; a board that sent no counts is read from its lanes instead.
function openTickets(board: Board): number {
  const counts = board.counts ?? {}
  if (Object.keys(counts).length)
    return Object.entries(counts).reduce((n, [status, c]) => n + (CLOSED.includes(status) ? 0 : Number(c) || 0), 0)
  return (board.lanes ?? []).reduce((n, lane) => n + (CLOSED.includes(lane.key) ? 0 : lane.tiles.filter(t => !CLOSED.includes(t.status)).length), 0)
}

export function crewChipState(board: Board | null): CrewChipState {
  if (!board) return { visible: false, count: 0, running: 0, radar: false, title: 'Crew' }
  const open = openTickets(board)
  const running = Math.max(board.counts?.running ?? 0, board.live ?? 0, liveTiles(board).length)
  const count = Math.max(open, running)
  return { visible: count > 0, count, running, radar: running > 0, title: formatCrewChipTitle(count, running) }
}

export interface CrewSessionChipState extends CrewChipState {
  done: number      // of count, the tickets already done (count includes them: a finished session keeps its chip)
  target: string    // where a click goes: the card when the session has exactly one ticket, else the Crew board
}

// One chat session's tickets (its tiles by session_id; never archived or a proof-suite test card). Done tickets count, so
// the chip stays as a static badge once a session's work is finished. The radar rings only while one of THIS session's
// tickets runs, so another session's run does not light the row.
export function crewSessionChipState(board: Board | null, sessionId: string): CrewSessionChipState {
  const hidden: CrewSessionChipState = { visible: false, count: 0, running: 0, radar: false, title: 'Crew', done: 0, target: CREW_ROUTE }
  if (!board || board.error || !sessionId) return hidden
  const open = new Map<string, Tile>()
  for (const lane of board.lanes ?? []) {
    if (lane.key === 'archived') continue
    for (const t of lane.tiles) if (t.session_id === sessionId && t.status !== 'archived' && !t.test) open.set(t.id, t)
  }
  const tiles = [...open.values()]
  const running = tiles.filter(t => t.status === 'running' || Boolean(t.active)).length
  const count = tiles.length
  if (!count) return hidden
  const done = tiles.filter(t => t.status === 'done').length
  const title = done
    ? 'Crew: ' + count + ' ticket' + (count === 1 ? '' : 's') + ' · ' + done + ' done' + (running ? ' · ' + running + ' running' : '')
    : formatCrewChipTitle(count, running)
  return { visible: true, count, running, radar: running > 0, title, done, target: count === 1 ? cardUrl(CREW_ROUTE, tiles[0].id) : CREW_ROUTE }
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

// The same chip on a sidebar session row (SESSION_ROW_AREAS.trailing): that session's open tickets only, the radar while
// one of them runs, nothing at all when it has none. The row is draggable and a plain click resumes the session, so the
// chip swallows the pointer and the click; it opens the card (one ticket) or the Crew board (several).
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
