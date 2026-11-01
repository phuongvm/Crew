// crewSessionChipState / crewChipState at their public seam: only running tickets are counted and shown. Run by
// `node ui/test.mjs` (bundles this file with esbuild, stubs the Desktop SDK); a failed check throws.
import { crewChipState, crewSessionChipState } from '../StatusChip'
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

// done tickets alone never show the chip: a finished session is hidden
{
  const s = crewSessionChipState(board([tile('t_1', 'done', 'sess-a'), tile('t_2', 'done', 'sess-a')]), 'sess-a')
  eq([s.visible, s.count, s.running, s.radar], [false, 0, 0, false], 'done-only session: hidden')
}
// a running ticket shows the chip and lights the radar; the count is running only, done beside it is not counted
{
  const s = crewSessionChipState(board([tile('t_1', 'done', 'sess-a'), tile('t_2', 'running', 'sess-a')]), 'sess-a')
  eq([s.visible, s.count, s.running, s.radar, s.title], [true, 1, 1, true, 'Crew: 1 running ticket'], 'running + done: running only')
}
// open but idle tickets (ready/review/blocked/todo) are not counted either
{
  const s = crewSessionChipState(board([tile('t_1', 'ready', 'sess-a'), tile('t_2', 'review', 'sess-a'), tile('t_3', 'blocked', 'sess-a'), tile('t_4', 'todo', 'sess-a')]), 'sess-a')
  eq([s.visible, s.count, s.radar], [false, 0, false], 'open-only session: hidden')
}
// 100 non-running tickets next to one running: count 1
{
  const many = Array.from({ length: 100 }, (_, i) => tile('t_n' + i, ['done', 'todo', 'review', 'blocked'][i % 4], 'sess-a'))
  eq(crewSessionChipState(board(many), 'sess-a').visible, false, '100 non-running tickets: hidden')
  const s = crewSessionChipState(board([...many, tile('t_run', 'running', 'sess-a')]), 'sess-a')
  eq([s.visible, s.count, s.running], [true, 1, 1], '100 non-running + 1 running: count 1')
}
// archived, probe/test cards, other sessions and an unknown session are not counted, even when running
{
  const b = board([tile('t_1', 'archived', 'sess-a'), tile('t_2', 'running', 'sess-a', { test: true }), tile('t_3', 'running', 'sess-b')])
  eq(crewSessionChipState(b, 'sess-a').visible, false, 'archived, test and foreign cards leave the chip hidden')
  eq(crewSessionChipState(b, '').visible, false, 'no session id: hidden')
  eq(crewSessionChipState(null, 'sess-a').visible, false, 'no board: hidden')
}
// a live run (tile.active) counts as running even when the status text has not caught up
eq(crewSessionChipState(board([tile('t_1', 'ready', 'sess-a', { active: { profile: 'w', run: 1, for_s: 5 } })]), 'sess-a').count, 1, 'active run counts as running')

// navigation: one running ticket opens its card (done / idle ones beside it do not count), several running open the board
{
  const one = crewSessionChipState(board([tile('t_ready', 'ready', 'sess-a'), tile('t_run', 'running', 'sess-a'), tile('t_done', 'done', 'sess-a')]), 'sess-a')
  eq([one.count, one.target], [1, '/crew?card=t_run'], 'one running ticket: target is its card')
  const many = crewSessionChipState(board([tile('t_1', 'running', 'sess-a'), tile('t_2', 'running', 'sess-a'), tile('t_3', 'done', 'sess-a')]), 'sess-a')
  eq([many.count, many.target], [2, '/crew'], 'two running tickets: target is the Crew board')
}
// the global chip counts running tickets the same way
{
  const g = (counts: Record<string, number>, live = 0) => crewChipState({ generated_at: 1, counts, lanes: [], live, cards: 0, attention: [] } as unknown as Board)
  eq([g({ ready: 2, review: 1, done: 4 }).visible, g({ ready: 2 }).count], [false, 0], 'global chip: hidden with nothing running')
  const r = g({ running: 2, ready: 3, done: 4 })
  eq([r.visible, r.count, r.running, r.radar, r.title], [true, 2, 2, true, 'Crew: 2 running tickets'], 'global chip: counts running only')
}

console.log('OK ' + checks + ' checks')
