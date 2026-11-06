// Rariflat Desktop pane — visual characters that react to tool calls
// Drop into $HERMES_HOME/desktop-plugins/rariflat/plugin.js

import { host, haptic } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'

const CHARACTERS = {
  web: { emoji: '🦉', name: 'Owl', color: '#4fc3f7' },
  terminal: { emoji: '⚒️', name: 'Hephaestus', color: '#ff9800' },
  memory: { emoji: '🧠', name: 'Mnemosyne', color: '#ba68c8' },
  error: { emoji: '🐾', name: 'Cerberus', color: '#ef5350' },
  default: { emoji: '🚀', name: 'Hermes', color: '#00e676' },
}

function getChar(tool) {
  const t = (tool || '').toLowerCase()
  for (const [k, v] of Object.entries(CHARACTERS)) {
    if (t.includes(k)) return v
  }
  return CHARACTERS.default
}

export default {
  id: 'rariflat',
  name: 'Rariflat',
  register(ctx) {
    ctx.register({
      id: 'status-pane',
      area: 'panes',
      title: 'Rariflat',
      data: { placement: 'right', width: '280px' },
      render: () => {
        const [last, setLast] = React.useState(null)
        const [history, setHistory] = React.useState([])

        // In a full version this listens to plugin events from the agent side
        React.useEffect(() => {
          const unsub = host.onEvent?.('plugin.rariflat.tool', (evt) => {
            const char = getChar(evt.tool)
            setLast({ ...char, tool: evt.tool, success: evt.success })
            setHistory(h => [{ ...char, tool: evt.tool }, ...h].slice(0, 8))
            haptic('tap')
          })
          return () => unsub?.()
        }, [])

        return jsxs('div', {
          className: 'flex h-full flex-col gap-3 p-3 text-sm',
          children: [
            jsx('div', { className: 'text-lg font-semibold', children: 'Rariflat' }),
            last
              ? jsxs('div', {
                  className: 'rounded-lg p-3 text-center',
                  style: { background: last.color + '22', border: `1px solid ${last.color}` },
                  children: [
                    jsx('div', { className: 'text-4xl', children: last.emoji }),
                    jsx('div', { className: 'mt-1 font-medium', children: last.name }),
                    jsx('div', { className: 'text-xs opacity-70', children: last.tool }),
                  ]
                })
              : jsx('div', { className: 'text-center opacity-60', children: 'Waiting for tool calls...' }),
            jsx('div', { className: 'mt-2 text-xs opacity-70', children: 'Recent' }),
            ...history.map((h, i) =>
              jsxs('div', {
                key: i,
                className: 'flex items-center gap-2 text-xs',
                children: [
                  jsx('span', { children: h.emoji }),
                  jsx('span', { children: h.tool })
                ]
              })
            )
          ]
        })
      }
    })

    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 100,
      render: () =>
        jsx('span', {
          className: 'px-1 text-xs',
          children: '🚀 Rariflat'
        })
    })
  }
}
