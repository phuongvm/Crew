/**
 * Hermes.Crew Desktop runtime plugin — autonomous proof-gated coordination board.
 *
 * Registers /crew route + sidebar nav entry below OpenSpec under the TOOLS group.
 * Provides live flow graph, multi-agent kanban view, and attention task monitoring.
 * Dual mode: the /crew tile (asTile) and a right-hand 'Crew Flow Graph' pane (PANES_AREA, SandboxedFrame)
 * are registered together and neither replaces the other.
 *
 * Packaging: single uncompiled ESM file. Runtime loader scans
 * ~/.hermes/plugins/crew/desktop/plugin.js or desktop-plugins/crew/plugin.js.
 */

import {
  Button, Codicon, host, PALETTE_AREA, PANES_AREA, ROUTES_AREA, SandboxedFrame, Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue, SIDEBAR_NAV_AREA
} from '@hermes/plugin-sdk'
import React from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

function getThemeTokens() {
  if (typeof document === 'undefined') return { bg: '#041c1c', fg: '#ffffff', mode: 'dark' }
  var root = window.getComputedStyle(document.documentElement)
  var mode = document.documentElement.dataset.hermesMode || (root.getPropertyValue('color-scheme').trim()) || 'dark'
  var bg = root.getPropertyValue('--dt-background').trim() || root.getPropertyValue('--ui-bg-editor').trim() || root.getPropertyValue('--background').trim() || (mode === 'light' ? '#ffffff' : '#041c1c')
  var fg = root.getPropertyValue('--ui-text-primary').trim() || root.getPropertyValue('--dt-foreground').trim() || root.getPropertyValue('--foreground').trim() || (mode === 'light' ? '#17171a' : '#ffffff')
  return { bg: bg, fg: fg, mode: mode }
}

function withThemeQuery(url) {
  var t = getThemeTokens()
  var sep = url.indexOf('?') === -1 ? '?' : '&'
  return url + sep + 'theme=' + encodeURIComponent(t.mode) + '&bg=' + encodeURIComponent(t.bg) + '&fg=' + encodeURIComponent(t.fg)
}

var LOCAL_BOARD_URL = 'http://127.0.0.1:8799/'
var LOCAL_HEALTH_URL = 'http://127.0.0.1:8799/healthz'
var AUTH_REQUIRED_MESSAGE = 'Authentication required: please log in to Hermes Gateway or ensure local Crew daemon is running'

// A card page's "discussion" chip posts { type: 'hermes:open-session', sessionId, profile } (card.js openDiscussion).
// The payload is plain identifiers or nothing: a session id with a slash, a dot or a shell character, or a
// profile that is not a profile name, is dropped before it can reach host.openSession.
var SESSION_IDENT_RE = /^[A-Za-z0-9_-]+$/

function parseOpenSession(data) {
  if (!data || typeof data !== 'object' || data.type !== 'hermes:open-session') return null
  var sid = String(data.sessionId == null ? '' : data.sessionId).trim()
  var prof = String(data.profile == null ? '' : data.profile).trim()
  if (!sid || sid.length > 128 || sid === 'no-session' || !SESSION_IDENT_RE.test(sid)) return null
  if (prof && (prof.length > 64 || !SESSION_IDENT_RE.test(prof))) return null
  return { sessionId: sid, profile: prof }
}

// Opens the card's discussion in Desktop. Resolves false (never throws) when the host cannot.
function openCardSession(target, sdkHost) {
  if (!target || !sdkHost || typeof sdkHost.openSession !== 'function') return Promise.resolve(false)
  var opts = target.profile ? { profile: target.profile } : {}
  try {
    return Promise.resolve(sdkHost.openSession(target.sessionId, opts)).then(
      function () { return true },
      function (err) {
        console.warn('[Crew] host.openSession failed:', err)
        return false
      }
    )
  } catch (err) {
    console.warn('[Crew] host.openSession failed:', err)
    return Promise.resolve(false)
  }
}

// True when the local crew_graph_serve daemon answers. no-cors: the daemon sends no CORS headers, so the
// response is opaque, but a resolved fetch proves the port is serving and a network error rejects.
async function probeLocalDaemon(timeoutMs) {
  if (typeof fetch !== 'function') return false
  var ctrl = typeof AbortController === 'function' ? new AbortController() : null
  var timer = ctrl ? setTimeout(function () { ctrl.abort() }, timeoutMs || 1500) : null
  try {
    await fetch(LOCAL_HEALTH_URL, { mode: 'no-cors', cache: 'no-store', signal: ctrl ? ctrl.signal : undefined })
    return true
  } catch (probeErr) {
    return false
  } finally {
    if (timer) clearTimeout(timer)
  }
}

function CrewPage() {
  var iframeRef = React.useRef(null)
  var [loading, setLoading] = React.useState(true)
  var [boardUrl, setBoardUrl] = React.useState('http://127.0.0.1:8799/')
  // Set instead of a board URL when no authenticated route and no local daemon exist: never iframe a raw 401.
  var [authError, setAuthError] = React.useState('')
  var [resolveNonce, setResolveNonce] = React.useState(0)
  // No board name is baked in: the generic 'Board' shows until the board page posts its live name.
  var [boardTitle, setBoardTitle] = React.useState('Board')

  React.useEffect(function () {
    // The active board's display name, posted by board.js from /board.json (board_name, else board), shown as written.
    // A card page's discussion chip posts hermes:open-session; only our own board iframe is listened to.
    function onMsg(e) {
      if (!e || !e.data) return
      if (e.data.type === 'hermes:board-info') {
        var name = String(e.data.board_name || e.data.board || '').trim()
        if (name) setBoardTitle(name)
      } else if (e.data.type === 'hermes:open-session') {
        var frame = iframeRef.current
        if (!frame || e.source !== frame.contentWindow) return
        var target = parseOpenSession(e.data)
        if (target) openCardSession(target, host)
      }
    }
    window.addEventListener('message', onMsg)
    return function () { window.removeEventListener('message', onMsg) }
  }, [])

  React.useEffect(function () {
    var isMounted = true
    function applyUrl(url) {
      if (!isMounted) return
      setAuthError('')
      setBoardUrl(withThemeQuery(url))
    }
    async function resolveBoardUrl() {
      if (await probeLocalDaemon(1500)) {
        return applyUrl(LOCAL_BOARD_URL)
      }
      var conn = null
      try {
        if (window.hermesDesktop && window.hermesDesktop.getConnection) {
          conn = await window.hermesDesktop.getConnection()
        }
      } catch (connErr) {
        conn = null
      }
      var base = conn && conn.baseUrl ? String(conn.baseUrl).replace(/\/+$/, '') : ''
      if (conn && conn.mode === 'remote' && base) {
        if (conn.token) {
          return applyUrl(base + '/api/plugins/crew/board?token=' + encodeURIComponent(conn.token))
        }
        if (window.hermesDesktop && window.hermesDesktop.api) {
          try {
            var ticketResp = await window.hermesDesktop.api({ path: '/api/auth/ws-ticket', method: 'POST' })
            if (ticketResp && ticketResp.ticket) {
              return applyUrl(base + '/api/plugins/crew/board?ticket=' + encodeURIComponent(ticketResp.ticket))
            }
          } catch (ticketErr) {
            // Not authenticated with the remote gateway: fall through to the local daemon.
          }
        }
        // No token and no ticket: the gateway URL would only render {"error":"unauthenticated",...}.
        if (await probeLocalDaemon(1500)) {
          return applyUrl(LOCAL_BOARD_URL)
        }
        if (isMounted) setAuthError(AUTH_REQUIRED_MESSAGE)
        return
      }
      // Local backend (or no connection info): resolve authenticated Gateway/Dashboard proxy first;
      // otherwise fall back to the local daemon if running.
      if (base) {
        if (conn && conn.token) {
          return applyUrl(base + '/api/plugins/crew/board?token=' + encodeURIComponent(conn.token))
        }
        if (window.hermesDesktop && window.hermesDesktop.api) {
          try {
            var ticketResp = await window.hermesDesktop.api({ path: '/api/auth/ws-ticket', method: 'POST' })
            if (ticketResp && ticketResp.ticket) {
              return applyUrl(base + '/api/plugins/crew/board?ticket=' + encodeURIComponent(ticketResp.ticket))
            }
          } catch (ticketErr) {}
        }
      }
      if (await probeLocalDaemon(1500)) {
        return applyUrl(LOCAL_BOARD_URL)
      }
      if (base) {
        return applyUrl(base + '/api/plugins/crew/board')
      }
      applyUrl(LOCAL_BOARD_URL)
    }
    resolveBoardUrl()
    return function () {
      isMounted = false
    }
  }, [resolveNonce])

  React.useEffect(function () {
    function syncTheme() {
      setLoading(false)
      var el = iframeRef.current
      if (!el) return
      var t = getThemeTokens()
      try {
        if (el.contentWindow) {
          el.contentWindow.postMessage({ type: 'hermes:theme', bg: t.bg, fg: t.fg, theme: t.mode }, '*')
        }
      } catch (postErr) {}
      try {
        var doc = el.contentDocument || (el.contentWindow && el.contentWindow.document)
        if (!doc) return
        var existing = doc.getElementById('hermes-theme-sync')
        if (!existing) {
          var s = doc.createElement('style')
          s.id = 'hermes-theme-sync'
          doc.head.appendChild(s)
          existing = s
        }
        existing.textContent =
          ':root { color-scheme: ' + t.mode + ' !important; --crew-scheme: ' + t.mode + ' !important; --crew-bg: ' + t.bg + ' !important; --color-background: ' + t.bg + ' !important; --crew-fg: ' + t.fg + ' !important; } ' +
          'html, body, main#board, main, #main, .page-card { background-color: ' + t.bg + ' !important; ' + (t.fg ? 'color: ' + t.fg + ' !important;' : '') + '}'
      } catch (err) {
        // Cross-origin fallback
      }
    }

    var el = iframeRef.current
    if (el) {
      el.addEventListener('load', syncTheme)
    }
    var obs = null
    try {
      obs = new MutationObserver(syncTheme)
      obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-hermes-mode', 'class', 'style'] })
    } catch (obsErr) {}

    return function () {
      if (el) {
        el.removeEventListener('load', syncTheme)
      }
      if (obs) {
        obs.disconnect()
      }
    }
  }, [boardUrl])

  var reloadBoard = function () {
    if (authError) {
      // Nothing loaded yet: re-run the resolution (login may have happened, or the daemon started).
      setResolveNonce(function (n) { return n + 1 })
      return
    }
    if (iframeRef.current) {
      setLoading(true)
      iframeRef.current.src = boardUrl
    }
  }

  var openStandalone = function () {
    if (window.hermesDesktop && window.hermesDesktop.openExternal) {
      window.hermesDesktop.openExternal(boardUrl)
    } else {
      window.open(boardUrl, '_blank')
    }
  }

  return jsxs('div', {
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      backgroundColor: 'var(--background, #041c1c)'
    },
    children: [
      jsxs('header', {
        style: {
          height: '36px',
          minHeight: '36px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          borderBottom: '1px solid var(--border, rgba(255, 255, 255, 0.08))',
          backgroundColor: 'var(--card, rgba(0, 0, 0, 0.2))'
        },
        children: [
          jsxs('div', {
            style: { display: 'flex', alignItems: 'center', gap: '8px' },
            children: [
              jsx(Codicon, { name: 'organization', style: { fontSize: '14px', color: 'var(--primary, #34d399)' } }),
              jsx('span', {
                style: { fontSize: '12px', fontWeight: 600, letterSpacing: '0.02em', color: 'var(--foreground, #ffffff)' },
                children: boardTitle
              }),
            ]
          }),
          jsxs('div', {
            style: { display: 'flex', alignItems: 'center', gap: '6px' },
            children: [
              jsx(Button, {
                size: 'sm',
                variant: 'ghost',
                onClick: reloadBoard,
                style: { height: '24px', padding: '0 6px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' },
                children: jsxs(React.Fragment, {
                  children: [
                    jsx(Codicon, { name: 'refresh', style: { fontSize: '12px' } }),
                    jsx('span', { children: 'Refresh' })
                  ]
                })
              }),
              jsx(Button, {
                size: 'sm',
                variant: 'ghost',
                onClick: openStandalone,
                style: { height: '24px', padding: '0 6px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' },
                children: jsxs(React.Fragment, {
                  children: [
                    jsx(Codicon, { name: 'link-external', style: { fontSize: '12px' } }),
                    jsx('span', { children: 'Standalone' })
                  ]
                })
              })
            ]
          })
        ]
      }),
      jsx('div', {
        style: { flex: 1, width: '100%', position: 'relative', overflow: 'hidden' },
        children: authError
          ? jsxs('div', {
              role: 'alert',
              style: {
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '10px',
                padding: '24px',
                textAlign: 'center',
                color: 'var(--foreground, #ffffff)'
              },
              children: [
                jsx(Codicon, { name: 'lock', style: { fontSize: '28px', color: 'var(--primary, #34d399)' } }),
                jsx('div', { style: { fontSize: '13px', fontWeight: 600 }, children: authError }),
                jsx('div', {
                  style: { fontSize: '11px', opacity: 0.7 },
                  children: 'Start the crew dashboard service (crew_graph_serve.py, set up by install.py), or sign in to the gateway, then press Refresh.'
                }),
                jsx(Button, { size: 'sm', variant: 'outline', onClick: reloadBoard, children: 'Retry' })
              ]
            })
          : jsx('iframe', {
              ref: iframeRef,
              src: boardUrl,
              style: {
                width: '100%',
                height: '100%',
                border: 'none',
                display: 'block',
                backgroundColor: 'var(--background, #041c1c)'
              },
              title: boardTitle
            })
      })
    ]
  })
}

// ---------------------------------------------------------------- Flow Graph extension pane (PANES_AREA)
// Issue #10: one card's flow graph in a right-hand Desktop pane, BESIDE the /crew tile, never instead of it.
// The card list comes from ctx.rest('/board.json') (this plugin's own authenticated, profile-aware namespace);
// the graph is the crew card page inside the SDK's SandboxedFrame (opaque origin: the page cannot reach the app,
// its storage or the preload bridge). A frame src never carries the gateway token: the local daemon needs no
// credential and a remote gateway gets a single-use ws-ticket.

var PANE_ID = 'crew-flow-graph-pane'
var PANE_TITLE = 'Crew Flow Graph'
var PANE_POLL_MS = 5000
var CARD_ID_RE = /^[A-Za-z0-9_-]+$/
// The pane's default card: what is working now first, then what needs the owner, then the rest.
var PANE_LANE_ORDER = ['running', 'blocked', 'review', 'queued', 'done']
var BOARD_UNREACHABLE_MESSAGE = 'Crew board unreachable: the crew dashboard service is not answering'

// The board's cards in pane order (archived lane left out), only ids a frame src may carry.
function paneCards(board) {
  var lanes = board && Array.isArray(board.lanes) ? board.lanes : []
  var out = []
  PANE_LANE_ORDER.forEach(function (key) {
    lanes.forEach(function (lane) {
      if (!lane || lane.key !== key || !Array.isArray(lane.tiles)) return
      lane.tiles.forEach(function (tile) {
        if (tile && CARD_ID_RE.test(String(tile.id || ''))) out.push(tile)
      })
    })
  })
  return out
}

// The card to show: the current one while it is still on the board (no focus jumps), else the first in pane order.
function pickFocusCard(cards, currentId) {
  if (!cards || !cards.length) return ''
  for (var i = 0; i < cards.length; i++) {
    if (currentId && cards[i].id === currentId) return currentId
  }
  return cards[0].id
}

// What makes the shown graph stale: a status move, a new run, a new outcome or a different live run.
function cardSignature(tile) {
  if (!tile) return ''
  var run = tile.active && tile.active.run != null ? tile.active.run : ''
  return [tile.status || '', tile.runs || 0, tile.last_outcome || '', run].join('|')
}

// The pane frame's src for a card, or null when nothing reachable is authorised (the pane then shows why).
// Ladder: local backend -> the local daemon; any gateway -> its crew proxy with a single-use ticket;
// remote without a ticket -> the local daemon. conn.token is never put in a URL.
async function resolvePaneFrameSrc(cardId, env) {
  if (!CARD_ID_RE.test(String(cardId || ''))) return null
  var probe = env && env.probe ? env.probe : probeLocalDaemon
  var desktop = env && 'desktop' in env ? env.desktop : (typeof window !== 'undefined' ? window.hermesDesktop : null)
  var path = 'card/' + encodeURIComponent(cardId)
  var conn = null
  try {
    if (desktop && desktop.getConnection) conn = await desktop.getConnection()
  } catch (connErr) {
    conn = null
  }
  var base = conn && conn.baseUrl ? String(conn.baseUrl).replace(/\/+$/, '') : ''
  if (!/^https?:\/\//i.test(base)) base = ''
  var remote = !!(conn && conn.mode === 'remote' && base)
  if (!remote && await probe(1500)) return LOCAL_BOARD_URL + path
  if (base && desktop && desktop.api) {
    try {
      var resp = await desktop.api({ path: '/api/auth/ws-ticket', method: 'POST' })
      if (resp && resp.ticket) {
        return base + '/api/plugins/crew/' + path + '?ticket=' + encodeURIComponent(resp.ticket)
      }
    } catch (ticketErr) {
      // Not signed in to this gateway: the local daemon is the last rung.
    }
  }
  if (remote && await probe(1500)) return LOCAL_BOARD_URL + path
  return null
}

function shortCardTitle(title) {
  var t = String(title || '').trim()
  return t.length > 48 ? t.slice(0, 47) + '…' : t
}

function CrewFlowGraphPane(props) {
  var rest = props ? props.rest : null
  var onHide = props ? props.onHide : null
  var frameRef = React.useRef(null)
  var cardIdRef = React.useRef('')
  var sigRef = React.useRef('')
  var [cards, setCards] = React.useState([])
  var [cardId, setCardId] = React.useState('')
  var [boardError, setBoardError] = React.useState('')
  var [frameSrc, setFrameSrc] = React.useState('')
  var [frameError, setFrameError] = React.useState('')
  var [reloadNonce, setReloadNonce] = React.useState(0)
  var [pollNonce, setPollNonce] = React.useState(0)
  cardIdRef.current = cardId

  function postTheme() {
    var el = frameRef.current
    if (!el || !el.contentWindow) return
    var t = getThemeTokens()
    try {
      // The frame's origin is opaque, so '*' is the only target that reaches it; theme colours are not secret.
      el.contentWindow.postMessage({ type: 'hermes:theme', bg: t.bg, fg: t.fg, theme: t.mode }, '*')
    } catch (postErr) {}
  }

  // The board poll: the card list, the focused card, and a frame reload when that card moved on.
  // A hidden pane does not poll (host.paneVisibility, feature-detected on older desktops).
  React.useEffect(function () {
    var alive = true
    var timer = null
    var visible = null
    try {
      if (host && typeof host.paneVisibility === 'function') visible = host.paneVisibility('crew:' + PANE_ID)
    } catch (visErr) {
      visible = null
    }
    async function poll() {
      if (!alive) return
      if (visible && typeof visible.get === 'function' && !visible.get()) {
        timer = setTimeout(poll, PANE_POLL_MS)
        return
      }
      try {
        if (typeof rest !== 'function') throw new Error('ctx.rest unavailable')
        var board = await rest('/board.json')
        if (!alive) return
        var list = paneCards(board)
        var id = pickFocusCard(list, cardIdRef.current)
        var tile = null
        for (var i = 0; i < list.length; i++) {
          if (list[i].id === id) tile = list[i]
        }
        var sig = id + '#' + cardSignature(tile)
        setCards(list)
        setBoardError('')
        if (id !== cardIdRef.current) {
          setCardId(id)
        } else if (sigRef.current && sig !== sigRef.current) {
          setReloadNonce(function (n) { return n + 1 })
        }
        sigRef.current = sig
      } catch (pollErr) {
        if (alive) setBoardError(BOARD_UNREACHABLE_MESSAGE)
      }
      if (alive) timer = setTimeout(poll, PANE_POLL_MS)
    }
    poll()
    return function () {
      alive = false
      if (timer) clearTimeout(timer)
    }
  }, [rest, pollNonce])

  // The frame src for the focused card, re-resolved on every reload (a ticket is single-use).
  React.useEffect(function () {
    var alive = true
    if (!cardId) {
      setFrameSrc('')
      setFrameError('')
      return function () { alive = false }
    }
    resolvePaneFrameSrc(cardId).then(function (src) {
      if (!alive) return
      if (src) {
        setFrameError('')
        setFrameSrc(withThemeQuery(src))
      } else {
        setFrameSrc('')
        setFrameError(AUTH_REQUIRED_MESSAGE)
      }
    })
    return function () { alive = false }
  }, [cardId, reloadNonce])

  // The card page's discussion chip (hermes:open-session) from our own frame only; theme follows the app.
  React.useEffect(function () {
    function onMsg(e) {
      var frame = frameRef.current
      if (!frame || !e || e.source !== frame.contentWindow || !e.data) return
      if (e.data.type === 'hermes:open-session') {
        var target = parseOpenSession(e.data)
        if (target) openCardSession(target, host)
      }
    }
    window.addEventListener('message', onMsg)
    var obs = null
    try {
      obs = new MutationObserver(postTheme)
      obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-hermes-mode', 'class', 'style'] })
    } catch (obsErr) {}
    return function () {
      window.removeEventListener('message', onMsg)
      if (obs) obs.disconnect()
    }
  }, [])

  var refresh = function () {
    setPollNonce(function (n) { return n + 1 })
    setReloadNonce(function (n) { return n + 1 })
  }

  var openTile = function () {
    if (host && typeof host.navigate === 'function') host.navigate('/crew')
  }

  var message = boardError || frameError || (!cardId ? 'No cards on the board' : '')

  return jsxs('div', {
    style: { width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
    children: [
      jsxs('header', {
        style: {
          minHeight: '32px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '0 8px',
          borderBottom: '1px solid var(--border, rgba(255, 255, 255, 0.08))'
        },
        children: [
          jsx(Codicon, { name: 'organization', style: { fontSize: '13px', color: 'var(--primary, #34d399)' } }),
          // The SDK's themed Select (portalled menu), not a native <select>: Electron's native popup does not
          // inherit the closed control's colours, so a transparent/white-text select listed unreadable options.
          jsx(Select, {
            value: cardId,
            disabled: !cards.length,
            onValueChange: function (value) {
              if (!CARD_ID_RE.test(String(value || ''))) return
              sigRef.current = ''
              setCardId(value)
            },
            children: [
              jsx(SelectTrigger, {
                size: 'xs',
                'aria-label': 'Crew card',
                title: 'Crew card',
                style: { flex: 1, minWidth: 0, height: '22px' },
                children: jsx(SelectValue, { placeholder: cards.length ? 'Select a card' : 'No cards' })
              }, 'trigger'),
              jsx(SelectContent, {
                children: cards.map(function (tile) {
                  return jsx(SelectItem, { value: tile.id, children: tile.id + ' · ' + shortCardTitle(tile.title) }, tile.id)
                })
              }, 'content')
            ]
          }),
          jsx(Button, {
            size: 'sm',
            variant: 'ghost',
            onClick: refresh,
            title: 'Refresh',
            style: { height: '22px', padding: '0 4px' },
            children: jsx(Codicon, { name: 'refresh', style: { fontSize: '12px' } })
          }),
          jsx(Button, {
            size: 'sm',
            variant: 'ghost',
            onClick: openTile,
            title: 'Open the Crew board tile',
            style: { height: '22px', padding: '0 4px' },
            children: jsx(Codicon, { name: 'link-external', style: { fontSize: '12px' } })
          }),
          typeof onHide === 'function'
            ? jsx(Button, {
                size: 'sm',
                variant: 'ghost',
                onClick: onHide,
                title: 'Hide this pane (show it again from Ctrl+K: Toggle Crew Flow Graph pane)',
                'aria-label': 'Hide the Crew Flow Graph pane',
                style: { height: '22px', padding: '0 4px' },
                children: jsx(Codicon, { name: 'eye-closed', style: { fontSize: '12px' } })
              })
            : null
        ]
      }),
      jsx('div', {
        style: { flex: 1, position: 'relative', overflow: 'hidden' },
        children: message
          ? jsxs('div', {
              role: boardError || frameError ? 'alert' : 'status',
              style: {
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '16px',
                textAlign: 'center',
                fontSize: '12px',
                color: 'var(--foreground, #ffffff)'
              },
              children: [
                jsx('div', { children: message }),
                boardError || frameError
                  ? jsx(Button, { size: 'sm', variant: 'outline', onClick: refresh, children: 'Retry' })
                  : null
              ]
            })
          : frameSrc
            ? jsx(SandboxedFrame, {
                ref: frameRef,
                src: frameSrc,
                title: PANE_TITLE,
                onLoad: postTheme,
                style: { width: '100%', height: '100%', display: 'block' }
              }, cardId + ':' + reloadNonce)
            : jsx('div', { role: 'status', style: { padding: '16px', fontSize: '12px', opacity: 0.7 }, children: 'Loading flow graph…' })
      })
    ]
  })
}

// ---------------------------------------------------------------- pane show/hide (Ctrl+K and the pane's Hide button)
// Hiding unregisters the pane contribution only: Desktop drops an unregistered pane out of the grid (its zone
// folds away) while the tree keeps its spot, so showing it again re-adopts it where it was. The /crew tile,
// the nav row and the palette row stay registered, so the plugin is never disabled. The choice persists in
// ctx.storage across launches. Showing is an explicit user action, so it reveals (fronts) the pane; boot never does.
var PANE_HOST_ID = 'crew:' + PANE_ID
var PANE_SHOWN_KEY = 'flowGraphPaneShown'
var PANE_TOGGLE_ID = 'crew.flow-graph-pane.toggle'

function createPaneToggle(ctx, sdkHost) {
  var dispose = null
  var storage = ctx ? ctx.storage : null

  function readShown() {
    try {
      return !(storage && typeof storage.get === 'function' && storage.get(PANE_SHOWN_KEY, true) === false)
    } catch (readErr) {
      return true
    }
  }

  function writeShown(shown) {
    try {
      if (storage && typeof storage.set === 'function') storage.set(PANE_SHOWN_KEY, shown)
    } catch (writeErr) {}
  }

  function paneContribution() {
    return {
      // uncloseable: Desktop offers no Close for it, so closing can never take the single-pane plugin path
      // (setPluginEnabled(false)) that would also remove the /crew tile; Hide below is the close verb.
      // hideOnly is not used: it trips "Last tab stays" when this is the only tab in its zone.
      id: PANE_ID,
      area: PANES_AREA,
      title: PANE_TITLE,
      data: { placement: 'right', width: '380px', uncloseable: true },
      render: function() { return jsx(CrewFlowGraphPane, { rest: ctx.rest, onHide: hide }) }
    }
  }

  function mount() {
    if (dispose) return
    var d = ctx.register(paneContribution())
    dispose = typeof d === 'function' ? d : function () {}
  }

  // On screen, not merely registered: a registered pane in a minimized zone or behind another tab reads off.
  function isShown() {
    if (!dispose) return false
    try {
      if (sdkHost && typeof sdkHost.paneVisibility === 'function') {
        var visible = sdkHost.paneVisibility(PANE_HOST_ID)
        if (visible && typeof visible.get === 'function') return !!visible.get()
      }
    } catch (visErr) {}
    return true
  }

  function show() {
    mount()
    writeShown(true)
    if (sdkHost && typeof sdkHost.revealPane === 'function') {
      // Next tick: adoption of a just-registered pane lands first, then the reveal fronts it.
      setTimeout(function () {
        try { sdkHost.revealPane(PANE_HOST_ID) } catch (revealErr) {}
      }, 0)
    }
  }

  function hide() {
    var d = dispose
    dispose = null
    writeShown(false)
    if (d) d()
  }

  function toggle() {
    if (isShown()) hide()
    else show()
  }

  return {
    boot: function () { if (readShown()) mount() },
    hide: hide,
    show: show,
    toggle: toggle,
    isShown: isShown,
    palette: {
      id: 'pane-toggle',
      area: PALETTE_AREA,
      data: {
        id: PANE_TOGGLE_ID,
        label: 'Toggle Crew Flow Graph pane',
        keywords: ['crew', 'flow', 'graph', 'pane', 'card', 'kanban', 'show', 'hide', 'on', 'off'],
        detail: function () { return isShown() ? 'on' : 'off' },
        detailVariant: 'state',
        keepOpen: true,
        run: toggle
      }
    }
  }
}

var plugin = {
  id: 'crew',
  name: 'Crew',
  description: 'Autonomous proof-gated coordination board and live flow graph',
  register: function(ctx) {
    var paneToggle = createPaneToggle(ctx, host)
    ctx.registerMany([
      {
        id: 'page',
        area: ROUTES_AREA,
        data: { path: '/crew' },
        render: function() { return jsx(CrewPage, {}) }
      },
      {
        id: 'nav',
        area: SIDEBAR_NAV_AREA,
        order: 55,
        data: { codicon: 'organization', label: 'Crew', path: '/crew', asTile: true }
      },
      paneToggle.palette
    ])
    // The Flow Graph pane, beside the tile above (Issue #10), unless the user hid it.
    paneToggle.boot()
  }
}

export default plugin


const ID = '[A-Za-z0-9_-]+'
const BOARD_QUERY = '(\\?(?:all=1|older=1)(?:&(?:all=1|older=1))?)?'

const ROUTES = [
  { method: 'GET', re: new RegExp('^board\\.json' + BOARD_QUERY + '$'), to: m => '/board.json' + (m[1] || ''), out: 'json' },
  { method: 'GET', re: new RegExp('^card/(' + ID + ')\\.json$'), to: m => '/card/' + m[1] + '.json', out: 'json' },
  { method: 'GET', re: /^avatars\/role\/([a-z0-9][a-z0-9_-]{0,39})\.svg$/, to: m => '/embed/avatar/role/' + m[1] + '.svg', out: 'data_url' },
  { method: 'POST', re: new RegExp('^ack/(' + ID + ')(\\?undo=1)?$'), to: m => '/embed/ack/' + m[1] + (m[2] || ''), out: 'ack' }
]

const NAV_RE = new RegExp('^(?:(board)|card/(' + ID + '))(\\?all=1)?$')

export function routeFor(method, path) {
  if (typeof method !== 'string' || typeof path !== 'string') return null
  for (const r of ROUTES) {
    const m = r.method === method.toUpperCase() ? r.re.exec(path) : null
    if (m) return { path: r.to(m), out: r.out }
  }
  return null
}

// A chat session the card page may ask to open: a profile name and a session id.
const PROFILE_RE = /^[A-Za-z0-9_.-]{1,64}$/
const SESSION_RE = /^[A-Za-z0-9_-]{1,128}$/

export function openSessionTarget(v) {
  if (!v || typeof v !== 'object' || typeof v.profile !== 'string' || typeof v.session !== 'string') return null
  if (v.session === 'no-session' || !PROFILE_RE.test(v.profile) || !SESSION_RE.test(v.session)) return null
  return { profile: v.profile, session: v.session }
}

export function navTarget(path) {
  const m = typeof path === 'string' ? NAV_RE.exec(path) : null
  return m ? { page: m[1] ? 'board' : 'card', id: m[2] || null, all: !!m[3] } : null
}

export function toDataUrl(html) {
  const bytes = new TextEncoder().encode(html)
  let bin = ''
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000))
  return 'data:text/html;charset=utf-8;base64,' + btoa(bin)
}

function reply(source, id, body) {
  try { source.postMessage({ crew: 1, id, ...body }, '*') } catch (e) { /* the frame went away */ }
}

export async function handleFrameMessage(ctx, frameWindow, event, setView) {
  const m = event.data
  if (!frameWindow || event.source !== frameWindow || !m || m.crew !== 1) return
  if (m.navigate !== undefined) {
    const view = navTarget(m.navigate)
    if (view) setView(view)
    return
  }
  if (m.openSession !== undefined) {
    // The Desktop plugin ctx has no session-open call. window.hermesDesktop.openSessionWindow is the preload API
    // (apps/desktop/electron/preload.ts:55); it opens the session in its own window.
    const t = openSessionTarget(m.openSession)
    const open = globalThis.window && window.hermesDesktop && window.hermesDesktop.openSessionWindow
    if (t && typeof open === 'function') open(t.session, { profile: t.profile })
    return
  }
  const id = m.id
  if (typeof id !== 'number') return
  const route = routeFor(m.method, m.path)
  if (!route) return reply(event.source, id, { error: 'crew: path not allowed' })
  try {
    const res = await ctx.rest(route.path, { method: m.method.toUpperCase() })
    if (route.out === 'json') reply(event.source, id, { status: 200, text: JSON.stringify(res) })
    else if (route.out === 'data_url') reply(event.source, id, { status: 200, text: res.data_url })
    else reply(event.source, id, { status: res.status, text: res.text })
  } catch (e) {
    reply(event.source, id, { error: String((e && e.message) || e) })
  }
}
