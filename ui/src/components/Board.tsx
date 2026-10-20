import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import type { AckResult, CrewApi } from '../api'
import { useBoard } from '../data'
import { useCrewHost } from '../host'
import { MARK_URI } from '../mark'
import { cardUrl } from '../open-card'
import { injectCss } from '../css'
import type { AttentionRow, Board as BoardData } from '../types'
import baseCss from '../styles/base.css'
import boardCss from '../styles/board.css'
import { fmt, hhmm, store } from './boardUtil'
import { Lane } from './Lane'

export interface BoardFlags {
  all?: boolean
  older?: boolean
}
interface Props {
  api: CrewApi
  onOpenCard(id: string): void
  flags?: BoardFlags                 // ?all=1 and "Show older"; when absent the board reads ?all=1 from the page URL
  onFlags?(f: BoardFlags): void
  home?(): void                      // the header mark's click; without it the mark is a plain link to "/"
}

// The header's status counts: (tone class, word, statuses).
const HEADER: [string, string, string[]][] = [['running', 'running', ['running']], ['blocked', 'blocked', ['blocked', 'triage']], ['done', 'done', ['done']]]

const BELL = (
  <svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
    <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
  </svg>
)

// The header's "link": where this board is reached from the viewer's side. The server's dashboard_url is authoritative
// only when it names a real host (the tailnet/public URL install.py --publish records, or CREW_DASHBOARD_URL); its
// default is the local http service on loopback (crew_card.dashboard_url), which is wrong for anyone not on that
// machine, so a loopback value yields to what the viewer actually used: Desktop's gateway connection, the Hermes web
// dashboard's own origin (+ its base path + the Crew tab), or the served shell's origin.
export const CREW_TAB = '/crew'   // dashboard/manifest.json tab.path
const LOOPBACK = /^(localhost|127(?:\.\d{1,3}){3}|\[::1\]|0\.0\.0\.0)$/i
const isHttp = (u: string): boolean => /^https?:\/\/[^/]/i.test(u)
const trim = (u: string): string => u.trim().replace(/\/+$/, '')
export function isLoopbackUrl(u: string): boolean {
  try { return LOOPBACK.test(new URL(u).hostname) } catch { return false }
}
export interface LinkEnv {
  desktop?: boolean        // inside Hermes Desktop: the renderer's own origin (file:// or a dev server) is never the board
  gatewayBase?: string     // Desktop: window.hermesDesktop.getConnection().baseUrl
  origin?: string          // the browser page's location.origin
  dashboardTab?: boolean   // mounted by the Hermes web dashboard tab (window.__HERMES_PLUGIN_SDK__)
  basePath?: string        // the dashboard's reverse-proxy prefix (window.__HERMES_BASE_PATH__)
}
export function resolveDashboardLink(serverUrl: string | undefined, env: LinkEnv): string {
  const server = trim(serverUrl || '')
  if (server && isHttp(server) && !isLoopbackUrl(server)) return server + '/'
  if (env.desktop) return env.gatewayBase && isHttp(env.gatewayBase) ? trim(env.gatewayBase) + CREW_TAB : (server || '') + '/'
  const origin = env.origin && isHttp(env.origin) ? trim(env.origin) : ''
  if (!origin) return (server || '') + '/'
  if (!env.dashboardTab) return origin + '/'
  const base = trim(env.basePath || '')
  return origin + (base && !base.startsWith('/') ? '/' : '') + base + CREW_TAB
}

// The viewer's side of resolveDashboardLink, read from the page; Desktop's connection is an IPC round-trip, so it lands
// on a later render (until then, and when it fails or wedges, the server's URL stands).
export function useDashboardLink(serverUrl: string | undefined): string {
  const w: any = typeof window !== 'undefined' ? window : undefined
  const desk = w?.hermesDesktop
  const desktop = !!desk
  const [gatewayBase, setGatewayBase] = useState('')
  useEffect(() => {
    if (typeof desk?.getConnection !== 'function') return
    let live = true
    Promise.resolve()
      .then(() => desk.getConnection())
      .then((c: any) => { if (live && typeof c?.baseUrl === 'string') setGatewayBase(c.baseUrl) }, () => { /* gateway down: keep the fallback */ })
    return () => { live = false }
  }, [desk])
  let origin = ''
  try { origin = w?.location?.origin || '' } catch { /* sandboxed */ }
  return resolveDashboardLink(serverUrl, {
    desktop, gatewayBase, origin, dashboardTab: !!w?.__HERMES_PLUGIN_SDK__,
    basePath: typeof w?.__HERMES_BASE_PATH__ === 'string' ? w.__HERMES_BASE_PATH__ : ''
  })
}

// The board (ui-spec section 4), ported from scripts/crew_dashboard/board.js: one header line with the board's own
// facts, the lanes in the order the server sends them, the bell with its list. Same DOM and class names as the old
// page, so the ported board.css applies unchanged.
export function Board({ api, onOpenCard, flags, onFlags, home }: Props) {
  injectCss('base', baseCss)
  injectCss('board', boardCss)
  const { kanbanRow } = useCrewHost()
  const all = flags?.all ?? (typeof location !== 'undefined' && /[?&]all=1/.test(location.search))
  const [older, setOlder] = useState(() => flags?.older ?? !!store('older'))
  useEffect(() => { if (flags?.older !== undefined) setOlder(flags.older) }, [flags?.older])
  const [archivedOpen, setArchivedOpen] = useState(() => {
    if (typeof location !== 'undefined' && location.hash === '#archived') store('archived.open', '1')   // a link that opens the column
    return !!store('archived.open')
  })
  const query = [all ? 'all=1' : '', older ? 'older=1' : ''].filter(Boolean).join('&')
  const { board, error, loading, refresh } = useBoard(api, 2000, query)
  const link = useDashboardLink(board?.dashboard_url)

  const setOlderFlag = (on: boolean) => {
    store('older', on ? '1' : null)
    setOlder(on)
    onFlags?.({ all, older: on })
  }
  const toggleArchived = () => {
    const next = !archivedOpen
    store('archived.open', next ? '1' : null)
    setArchivedOpen(next)
  }

  const [staleSince, setStaleSince] = useState<Date | null>(null)
  useEffect(() => { setStaleSince(s => (error ? s || new Date() : null)) }, [error])
  const when = useMemo(() => (board ? new Date().toLocaleTimeString() : ''), [board])

  // The bell: rows cleared here disappear at once; the next poll is the truth.
  const [cleared, setCleared] = useState<Set<string>>(new Set())
  useEffect(() => { setCleared(new Set()) }, [board])
  const [notesOpen, setNotesOpen] = useState(false)
  const wrap = useRef<HTMLSpanElement>(null)
  useEffect(() => {
    const away = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setNotesOpen(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setNotesOpen(false) }
    document.addEventListener('click', away)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('click', away); document.removeEventListener('keydown', esc) }
  }, [])
  const ack = (path: string, ids: string[]) => {
    setCleared(c => new Set([...c, ...ids]))
    api.post<AckResult>(path).then(refresh, refresh)
  }

  if (!board) {
    const box: CSSProperties = { padding: 16, fontFamily: 'var(--crew-font)' }
    return <div style={box}>{error ? 'Crew could not load: ' + error : loading ? 'Loading...' : ''}</div>
  }
  const att = board.attention || {}
  const rows: AttentionRow[] = (att.rows || []).filter(r => !cleared.has(r.id))
  const live = board.live || 0
  const cards = board.cards || 0
  const counts = board.counts || {}
  const brand = (
    <a className="brand" href="/" title="overview" aria-label="crew overview" onClick={home ? e => { e.preventDefault(); home() } : undefined}>
      <img src={MARK_URI} alt="" width={26} height={26} />
    </a>
  )
  return (
    <div className="page-board crew-scope">
      <header>
        {brand}
        <span className={'badge' + (error ? ' stale' : '')} id="badge" title={error ? 'the board server is not answering' : 'the board server answers'}>
          <i></i>LIVE
        </span>
        <h1>crew board</h1>
        <span className="meta" id="cards">{cards + ' card' + (cards === 1 ? '' : 's')}</span>
        <span className={'meta' + (live ? ' on' : '')} id="live">{live ? live + ' working now' : 'nothing running'}</span>
        <div className="stats" id="counts">
          {HEADER.map(([cls, word, statuses]) => {
            const n = statuses.reduce((a, s) => a + (counts[s] || 0), 0)
            return <span key={cls} className={cls + (n ? '' : ' none')}><b>{n}</b>{word}</span>
          })}
        </div>
        <span className="meta" id="when">{'updated ' + when}</span>
        <span className="stale" id="stale" hidden={!error}>{staleSince ? 'stale since ' + hhmm(staleSince) : ''}</span>
        <span className="hright">
          {kanbanRow ? (
            <label className="kswitch" title="Hermes shows its own Kanban row in the sidebar; Crew hides it unless this is on">
              <input type="checkbox" role="switch" checked={kanbanRow.show} onChange={e => kanbanRow.set(e.target.checked)} />
              <i aria-hidden="true"></i>Show Hermes Kanban row
            </label>
          ) : null}
          <span id="bellwrap" ref={wrap}>
            <button id="bell" className={'bell' + (rows.length ? ' waiting' : '')} aria-label="notifications"
              title={rows.length ? rows.length + ' waiting - click for the list' : 'nothing waiting'} onClick={() => setNotesOpen(o => !o)}>
              {BELL}<span className="n" id="belln">{rows.length}</span>
            </button>
            <div id="notes" hidden={!notesOpen}>
              <div className="nh">
                <span id="notehead">needs you - <b>{+(att.stuck || 0)}</b> stuck - <b>{+(att.done || 0)}</b> done</span>
                <button id="clearall" title="clear every listed row" onClick={() => ack('/ack/all', rows.map(r => r.id))}>clear all</button>
              </div>
              <div id="noterows">
                {rows.length ? rows.map(r => (
                  <div key={r.id} className={'ar' + (r.status !== 'done' ? ' stuck' : '')}>
                    <span className="st">{r.status}</span>
                    <a className="t" href={cardUrl('', r.id)} onClick={e => { e.preventDefault(); setNotesOpen(false); onOpenCard(r.id) }}>
                      {r.id + ' - ' + (r.title || '(untitled)')}
                    </a>
                    <span className="w">{r.who || '-'}</span>
                    <span className="ag">{fmt(+r.age_s)}</span>
                    <button title="clear this one" onClick={() => ack('/ack/' + r.id, [r.id])}>✕</button>
                  </div>
                )) : <div className="empty">nothing waiting</div>}
              </div>
            </div>
          </span>
          <span className="node">
            {(board.node || '') + ' - kanban' + (board.board && board.board !== 'default' ? ' ' + board.board : '') + ' '}
            <a className="tailnet" href={link}>link</a>
          </span>
        </span>
      </header>
      {board.dispatcher && board.dispatcher.alive === false ? (
        <div className="dispatcher-down" id="dispatcher-down" role="alert">
          <b>Cards will not start.</b>{' ' + (board.dispatcher.detail || 'The gateway is not running') + '. Start it with '}
          <code>{board.dispatcher.command || 'hermes gateway run'}</code>
        </div>
      ) : null}
      <main id="board">
        {board.lanes.map(l => (
          <Lane key={l.key} lane={l} api={api} archivedOpen={archivedOpen} older={older} onToggleArchived={toggleArchived}
            onOlder={setOlderFlag} onOpenCard={onOpenCard} />
        ))}
      </main>
    </div>
  )
}
