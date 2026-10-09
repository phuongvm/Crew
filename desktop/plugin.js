/**
 * Hermes.Crew Desktop runtime plugin — autonomous proof-gated coordination board.
 *
 * Registers /crew route + sidebar nav entry below OpenSpec under the TOOLS group.
 * Provides live flow graph, multi-agent kanban view, and attention task monitoring.
 *
 * Packaging: single uncompiled ESM file. Runtime loader scans
 * ~/.hermes/plugins/crew/desktop/plugin.js or desktop-plugins/crew/plugin.js.
 */

import {
  Button, Codicon, ROUTES_AREA, SIDEBAR_NAV_AREA
} from '@hermes/plugin-sdk'
import React from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

function CrewPage() {
  var iframeRef = React.useRef(null)
  var [loading, setLoading] = React.useState(true)
  var [boardUrl, setBoardUrl] = React.useState('http://127.0.0.1:8799/')

  React.useEffect(function () {
    var isMounted = true
    async function resolveBoardUrl() {
      try {
        if (window.hermesDesktop && window.hermesDesktop.getConnection) {
          var conn = await window.hermesDesktop.getConnection()
          if (conn && conn.mode === 'remote') {
            var base = (conn.baseUrl || '').replace(/\/+$/, '')
            if (base) {
              if (conn.token) {
                if (isMounted) {
                  setBoardUrl(base + '/api/plugins/crew/board?token=' + encodeURIComponent(conn.token))
                }
                return
              }
              if (window.hermesDesktop && window.hermesDesktop.api) {
                try {
                  var ticketResp = await window.hermesDesktop.api({ path: '/api/auth/ws-ticket', method: 'POST' })
                  if (ticketResp && ticketResp.ticket) {
                    if (isMounted) {
                      setBoardUrl(base + '/api/plugins/crew/board?ticket=' + encodeURIComponent(ticketResp.ticket))
                    }
                    return
                  }
                } catch (ticketErr) {
                  // Fall through to plain url
                }
              }
              if (isMounted) {
                setBoardUrl(base + '/api/plugins/crew/board')
              }
              return
            }
          }
        }
      } catch (err) {
        // Fall back to default local URL
      }
      if (isMounted) {
        setBoardUrl('http://127.0.0.1:8799/')
      }
    }
    resolveBoardUrl()
    return function () {
      isMounted = false
    }
  }, [])

  React.useEffect(function () {
    function syncTheme() {
      setLoading(false)
      var el = iframeRef.current
      if (!el) return
      try {
        var doc = el.contentDocument || (el.contentWindow && el.contentWindow.document)
        if (!doc) return
        var style = window.getComputedStyle(document.documentElement)
        var bg = style.getPropertyValue('--background-base').trim() || style.getPropertyValue('--background').trim() || '#041c1c'
        var fg = style.getPropertyValue('--foreground-base').trim() || style.getPropertyValue('--foreground').trim() || '#ffffff'
        var existing = doc.getElementById('hermes-theme-sync')
        if (!existing) {
          var s = doc.createElement('style')
          s.id = 'hermes-theme-sync'
          doc.head.appendChild(s)
          existing = s
        }
        existing.textContent =
          ':root { --crew-bg: ' + bg + ' !important; --color-background: ' + bg + ' !important; --crew-fg: ' + fg + ' !important; } ' +
          'html, body, main#board { background-color: ' + bg + ' !important; }'
      } catch (err) {
        // Cross-origin fallback
      }
    }

    var el = iframeRef.current
    if (el) {
      el.addEventListener('load', syncTheme)
    }
    return function () {
      if (el) {
        el.removeEventListener('load', syncTheme)
      }
    }
  }, [boardUrl])

  var reloadBoard = function () {
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
                children: 'Crew Coordination Board'
              }),
              jsx('span', {
                style: {
                  fontSize: '10px',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(52, 211, 153, 0.15)',
                  color: '#34d399',
                  fontWeight: 500
                },
                children: 'v0.7.9'
              })
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
        children: jsx('iframe', {
          ref: iframeRef,
          src: boardUrl,
          style: {
            width: '100%',
            height: '100%',
            border: 'none',
            display: 'block',
            backgroundColor: 'var(--background, #041c1c)'
          },
          title: 'Crew Board'
        })
      })
    ]
  })
}

var plugin = {
  id: 'crew',
  name: 'Crew',
  description: 'Autonomous proof-gated coordination board and live flow graph',
  register: function(ctx) {
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
        data: { codicon: 'organization', label: 'Crew', path: '/crew' }
      }
    ])
  }
}

export default plugin
