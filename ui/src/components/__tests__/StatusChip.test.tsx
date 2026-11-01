// crewSessionChipState at its public seam: which of a session's tickets the sidebar-row chip counts. Run by
// `node ui/test.mjs` (bundles this file with esbuild, stubs the Desktop SDK); a failed check throws.
import { crewSessionChipState } from '../StatusChip'
import type { Board, Tile } from '../../types'

const tile = (id: string, status: string, session_id: string, extra: Record<string, unknown> = {}): Tile =>
  ({ id, title: id, status, role: 'worker', assignee: 'w', active: null, session_id, ...extra }) as unknown as Tile

const board = (tiles: Tile[]): Board =>
  ({ generated_at: 1, counts: {}, live: 0, cards: tiles.length, attention: [],
    lanes: [{ key: 'all', label: 'All', hidden: 0, tiles: tiles.filter(t => t.status !== 'archived') },
            { key: 'archived', label: 'Archived', hidden: 0, tiles: tiles.filter(t => t.status === 'archived') }] }) as unknown as Board

let checks = 0
function eq(actual: unknown, expected: unknown, what: string) {
  checks++
  if (JSON.stringify(actual) !== JSON.stringify(expected))
    throw new Error('FAILED ' + what + ': expected ' + JSON.stringify(expected) + ', got ' + JSON.stringify(actual))
}

// done tickets keep the chip as a static badge while nothing of the session runs
{
  const s = crewSessionChipState(board([tile('t_1', 'done', 'sess-a'), tile('t_2', 'done', 'sess-a')]), 'sess-a')
  eq([s.visible, s.count, s.running, s.radar, s.done], [true, 2, 0, false, 2], 'done-only session: visible, static')
  eq(s.title, 'Crew: 2 tickets · 2 done', 'done-only session: title')
}
// a running ticket lights the radar even beside done ones
{
  const s = crewSessionChipState(board([tile('t_1', 'done', 'sess-a'), tile('t_2', 'running', 'sess-a')]), 'sess-a')
  eq([s.visible, s.count, s.running, s.radar, s.done], [true, 2, 1, true, 1], 'running + done: radar live')
}
// open tickets only keep the open-ticket wording
{
  const s = crewSessionChipState(board([tile('t_1', 'ready', 'sess-a')]), 'sess-a')
  eq([s.count, s.radar, s.title], [1, false, 'Crew: 1 open ticket'], 'open-only session: unchanged wording')
}
// archived, probe/test cards, other sessions and an unknown session are not counted
{
  const b = board([tile('t_1', 'archived', 'sess-a'), tile('t_2', 'done', 'sess-a', { test: true }), tile('t_3', 'done', 'sess-b')])
  eq(crewSessionChipState(b, 'sess-a').visible, false, 'archived, test and foreign cards leave the chip hidden')
  eq(crewSessionChipState(b, '').visible, false, 'no session id: hidden')
  eq(crewSessionChipState(null, 'sess-a').visible, false, 'no board: hidden')
}
// a single done ticket opens its card
eq(crewSessionChipState(board([tile('t_one', 'done', 'sess-a')]), 'sess-a').target, '/crew?card=t_one', 'one ticket: target is its card')

console.log('OK ' + checks + ' checks')
