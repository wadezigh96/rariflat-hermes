// Rariflat Desktop pane — visual characters that react to tool calls
// Place at: $HERMES_HOME/desktop-plugins/rariflat/plugin.js

import { host, haptic } from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'

const CHARACTERS = {
  web: { emoji: '🦉', name: 'Owl', color: '#4fc3f7' },
  search: { emoji: '🦉', name: 'Owl', color: '#4fc3f7' },
  browser: { emoji: '🔍', name: 'Scout', color: '#26c6da' },
  terminal: { emoji: '⚒️', name: 'Hephaestus', color: '#ff9800' },
  code: { emoji: '⚒️', name: 'Hephaestus', color: '#ff9800' },
  file: { emoji: '📜', name: 'Archivist', color: '#ffd54f' },
  memory: { emoji: '🧠', name: 'Mnemosyne', color: '#ba68c8' },
  skills: { emoji: '🎓', name: 'Mentor', color: '#66bb6a' },
  image: { emoji: '🎨', name: 'Muse', color: '#f06292' },
  vision: { emoji: '👁️', name: 'Seer', color: '#7986cb' },
  tts: { emoji: '🎵', name: 'Bard', color: '#ffee58' },
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
      data: { placement: 'right', width: '300px' },
      render: () => {
        const [last, setLast] = React.useState(null)
        const [history, setHistory] = React.useState([])

        React.useEffect(() => {
          const unsub = host.onEvent?.('plugin.rariflat.tool', (evt) => {
            const char = getChar(evt.tool)
            setLast({ ...char, tool: evt.tool, success: evt.success !== false })
            setHistory((h) => [{ ...char, tool: evt.tool, success: evt.success !== false }, ...h].slice(0, 10))
            haptic('tap')
          })
          return () => unsub?.()
        }, [])

        return jsxs('div', {
          className: 'flex h-full flex-col gap-3 p-3 text-sm',
          children: [
            jsx('div', { className: 'text-lg font-semibold tracking-tight', children: 'Rariflat' }),
            last
              ? jsxs('div', {
                  className: 'rounded-xl p-4 text-center transition-all',
                  style: {
                    background: last.color + '18',
                    border: `1px solid ${last.color}55`,
                  },
                  children: [
                    jsx('div', { className: 'text-5xl', children: last.emoji }),
                    jsx('div', { className: 'mt-1 font-medium', children: last.name }),
                    jsx('div', {
                      className: 'mt-0.5 text-xs opacity-70',
                      children: last.success ? 'succeeded' : 'encountered resistance',
                    }),
                    jsx('div', { className: 'mt-1 text-[11px] opacity-50', children: last.tool }),
                  ],
                })
              : jsx('div', {
                  className: 'rounded-xl border border-dashed border-white/10 p-6 text-center text-xs opacity-50',
                  children: 'Waiting for tool calls…',
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
                          className: h.success ? 'text-emerald-400' : 'text-rose-400',
                          children: h.success ? '✓' : '✗',
                        }),
                      ],
                    },
                    i
                  )
                ),
          ],
        })
      },
    })

    ctx.register({
      id: 'chip',
      area: 'statusBar.right',
      order: 100,
      render: () =>
        jsx('span', {
          className: 'px-1.5 text-xs',
          children: '🚀 Rariflat',
        }),
    })
  },
}
