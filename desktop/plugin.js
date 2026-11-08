// Rariflat desktop half. Lives at <hermes home>/plugins/rariflat/desktop/plugin.js;
// the desktop app copies it to desktop-plugins/rariflat/ (opt-in: toggle it on in Settings → Plugins).
// The Python half emits `plugin.rariflat.tool` through hermes_cli.plugin_events; this pane only listens.

import { haptic, host } from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'rariflat' // must match the folder name
const EVENT = 'plugin.rariflat.tool'
const MAX_HISTORY = 10

const COLORS = {
  Owl: '#4fc3f7',
  Scout: '#26c6da',
  Hephaestus: '#ff9800',
  Archivist: '#ffd54f',
  Mnemosyne: '#ba68c8',
  Mentor: '#66bb6a',
  Muse: '#f06292',
  Seer: '#7986cb',
  Bard: '#ffee58',
  Cerberus: '#ef5350',
  Hermes: '#00e676'
}

function RariflatPane() {
  const [active, setActive] = useState(null)
  const [last, setLast] = useState(null)
  const [history, setHistory] = useState([])

  useEffect(() => {
    const off = host.onEvent(EVENT, evt => {
      const p = (evt && evt.payload) || {}
      if (!p.tool) return
      if (p.phase === 'start') {
        setActive(p)
        return
      }
      setActive(null)
      setLast(p)
      setHistory(h => [p, ...h].slice(0, MAX_HISTORY))
      if (p.phase === 'blocked') haptic('tap')
    })
    return () => {
      if (typeof off === 'function') off()
    }
  }, [])

  const shown = active || last
  const color = shown ? COLORS[shown.character] || COLORS.Hermes : '#888888'
  const status = !shown
    ? ''
    : active
      ? 'working…'
      : shown.phase === 'blocked'
        ? 'blocked by your Rariflat config'
        : shown.success
          ? 'succeeded'
          : 'encountered resistance'

  return jsxs('div', {
    className: 'flex h-full flex-col gap-3 p-3 text-sm',
    children: [
      jsx('div', { className: 'text-lg font-semibold tracking-tight', children: 'Rariflat' }),
      shown
        ? jsxs('div', {
            className: 'rounded-xl p-4 text-center',
            style: { background: color + '18', border: '1px solid ' + color + '55' },
            children: [
              jsx('div', { className: 'text-5xl', children: shown.emoji }),
              jsx('div', { className: 'mt-1 font-medium', children: shown.character }),
              jsx('div', { className: 'mt-0.5 text-xs opacity-70', children: status }),
              jsx('div', { className: 'mt-1 text-[11px] opacity-50', children: shown.tool })
            ]
          })
        : jsx('div', {
            className: 'rounded-xl border border-dashed border-white/10 p-6 text-center text-xs opacity-50',
            children: 'Waiting for tool calls…'
          }),
      jsx('div', { className: 'mt-1 text-xs font-medium opacity-60', children: 'Recent' }),
      history.length === 0
        ? jsx('div', { className: 'text-xs opacity-40', children: 'None yet' })
        : history.map((h, i) =>
            jsxs(
              'div',
              {
                className: 'flex items-center gap-2 text-xs',
                children: [
                  jsx('span', { children: h.emoji }),
                  jsx('span', { className: 'flex-1 truncate opacity-80', children: h.tool }),
                  jsx('span', {
                    className: h.phase === 'blocked' ? 'text-amber-400' : h.success ? 'text-emerald-400' : 'text-rose-400',
                    children: h.phase === 'blocked' ? '⛔' : h.success ? '✓' : '✗'
                  })
                ]
              },
              i
            )
          )
    ]
  })
}

function RariflatChip() {
  return jsx('span', { className: 'px-1.5 text-xs', children: '🚀 Rariflat' })
}

export default {
  id: ID,
  name: 'Rariflat',
  // The desktop pane is opt-in; users must enable it in Capabilities → Plugins.
  defaultEnabled: false,
  register(ctx) {
    ctx.register({
      id: 'status-pane',
      area: 'panes',
      title: 'Rariflat',
      data: { placement: 'right', width: '300px' },
      render: () => jsx(RariflatPane, {})
    })
    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 100,
      render: () => jsx(RariflatChip, {})
    })
  }
}
