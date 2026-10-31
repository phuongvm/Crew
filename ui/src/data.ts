import { useCallback, useEffect, useRef, useState } from 'react'
import type { CrewApi } from './api'
import type { CardJson } from './card-types'
import type { Board } from './types'

// One /board.json poll per (api, query), shared by every useBoard consumer of it: the status bar chip, the flow pane and
// every mounted sidebar session-row chip would otherwise each hold their own timer and request. The store keeps one
// snapshot, one in-flight load and ONE timer, armed at the smallest positive interval any live subscriber asked for.
interface BoardSnap { board: Board | null; error: string | null; loading: boolean }
type BoardListener = (snap: BoardSnap) => void
interface SharedBoard {
  snap: BoardSnap
  listeners: Map<BoardListener, number>   // listener -> the intervalMs it asked for (<= 0: reads, never polls)
  timer: ReturnType<typeof setInterval> | undefined
  armedMs: number                          // the interval `timer` was armed with, 0 when none
  alive: boolean                           // false once disposed: a response that lands later is dropped
  load(): Promise<void>
}

const INITIAL_SNAP: BoardSnap = { board: null, error: null, loading: true }
const shared = new WeakMap<CrewApi, Map<string, SharedBoard>>()

// Exactly one timer per entry, at min(positive intervalMs). A change of that minimum clears and re-arms it (never an
// immediate load); an unchanged minimum leaves the timer alone.
function rearm(entry: SharedBoard): void {
  const wanted = [...entry.listeners.values()].filter(ms => ms > 0)
  const next = wanted.length ? Math.min(...wanted) : 0
  if (next === entry.armedMs) return
  if (entry.timer !== undefined) clearInterval(entry.timer)
  entry.timer = next > 0 ? setInterval(entry.load, next) : undefined
  entry.armedMs = next
}

function openEntry(api: CrewApi, query: string): SharedBoard {
  const entry: SharedBoard = {
    snap: INITIAL_SNAP, listeners: new Map(), timer: undefined, armedMs: 0, alive: true,
    load: () =>
      api
        .get<Board>('/board.json' + (query ? '?' + query : ''))
        .then(b => { if (entry.alive) publish(entry, { board: b, error: null, loading: false }) })
        .catch(e => { if (entry.alive) publish(entry, { board: entry.snap.board, error: String((e && e.message) || e), loading: false }) })
  }
  return entry
}

function publish(entry: SharedBoard, snap: BoardSnap): void {
  entry.snap = snap
  entry.listeners.forEach((_, fn) => fn(snap))
}

function peekSnap(api: CrewApi, query: string): BoardSnap {
  return shared.get(api)?.get(query)?.snap ?? INITIAL_SNAP
}

// Joins (api, query), starting its first load when it is new. Returns the entry and the way out; the last way out
// disposes the entry (timer cleared, map slot freed) so a later mount starts clean.
function joinBoard(api: CrewApi, query: string, intervalMs: number, listener: BoardListener): { entry: SharedBoard; leave(): void } {
  let byQuery = shared.get(api)
  if (!byQuery) shared.set(api, (byQuery = new Map()))
  let entry = byQuery.get(query)
  const fresh = !entry
  if (!entry) byQuery.set(query, (entry = openEntry(api, query)))
  const joined = entry
  joined.listeners.set(listener, intervalMs)
  if (!joined.snap.loading) listener(joined.snap)   // a late joiner gets the current board; a still-loading entry keeps what the caller shows (no blank flash on a query change)
  if (fresh) void joined.load()
  rearm(joined)
  return {
    entry: joined,
    leave() {
      joined.listeners.delete(listener)
      if (joined.listeners.size > 0) { rearm(joined); return }
      if (joined.timer !== undefined) clearInterval(joined.timer)
      joined.timer = undefined
      joined.armedMs = 0
      joined.alive = false
      const map = shared.get(api)
      if (map?.get(query) === joined) map.delete(query)
      if (map && map.size === 0) shared.delete(api)
    }
  }
}

// Polls /board.json. A failed poll keeps the last board and sets `error`, so a blip does not blank the page.
// `query` is the flag string appended to the route, e.g. 'all=1&older=1' (no leading '?'). Consumers of the same
// (api, query) share one request per tick (see above).
export function useBoard(api: CrewApi, intervalMs = 2000, query = '') {
  const [snap, setSnap] = useState<BoardSnap>(() => peekSnap(api, query))
  const entryRef = useRef<SharedBoard | null>(null)
  useEffect(() => {
    const { entry, leave } = joinBoard(api, query, intervalMs, setSnap)
    entryRef.current = entry
    return () => { entryRef.current = null; leave() }
  }, [api, intervalMs, query])
  // refresh() polls again now (after an ack) for every consumer of this board; the timer keeps its cadence.
  const refresh = useCallback(() => { void entryRef.current?.load() }, [])
  return { board: snap.board, error: snap.error, loading: snap.loading, refresh }
}

// Polls /card/<id>.json (the card page's data). A failed poll keeps the last card and sets `error`. `paused` stops
// the timer (the page's space key) and `reload()` fetches once now (its r key). A new id starts empty again.
export function useCard(api: CrewApi, id: string, intervalMs = 2000, paused = false) {
  const [card, setCard] = useState<CardJson | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const loadRef = useRef<() => void>(() => {})
  useEffect(() => {
    let live = true
    setCard(null)
    setLoading(true)
    const load = () =>
      api
        .get<CardJson>('/card/' + encodeURIComponent(id) + '.json')
        .then(c => { if (live) { setCard(c); setError(null) } })
        .catch(e => { if (live) setError(String((e && e.message) || e)) })
        .finally(() => { if (live) setLoading(false) })
    loadRef.current = load
    load()
    if (paused) return () => { live = false }
    const timer = setInterval(load, intervalMs)
    return () => { live = false; clearInterval(timer) }
  }, [api, id, intervalMs, paused])
  const reload = useCallback(() => loadRef.current(), [])
  return { card, error, loading, reload }
}
