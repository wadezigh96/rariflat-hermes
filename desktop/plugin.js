// Rariflat Desktop pane — receives the official Hermes plugin event bridge.
import { host, haptic } from '@hermes/plugin-sdk'
import { useState, useEffect } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const CHARACTERS = {
  web: { emoji: '🦉', name: 'Owl', color: '#4fc3f7' },
  search: { emoji: '🦉', name: 'Owl', color: '#4fc3f7' },
  browser: { emoji: '🔍', name: 'Scout', color: '#26c6da' },
  terminal: { emoji: '⚒️', name: 'Hephaestus', color: '#ff9800' },
  code: { emoji: '⚒️', name: 'Hephaestus', color: '#ff9800' },
  file: { emoji: '📜', name: 'Archivist', color: '#ffd54f' },
  memory: { emoji: '🧠', name: 'Mnemosyne', color: '#ba68c8' },
  skill: { emoji: '🎓', name: 'Mentor', color: '#66bb6a' },
  skills: { emoji: '🎓', name: 'Mentor', color: '#66bb6a' },
  image: { emoji: '🎨', name: 'Muse', color: '#f06292' },
  vision: { emoji: '👁️', name: 'Seer', color: '#7986cb' },
  tts: { emoji: '🎵', name: 'Bard', color: '#ffee58' },
  error: { emoji: '🐾', name: 'Cerberus', color: '#ef5350' },
  default: { emoji: '🚀', name: 'Hermes', color: '#00e676' },
}
function getChar(tool) {
  for (const token of (tool || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)) {
    if (CHARACTERS[token]) return CHARACTERS[token]
  }
  return CHARACTERS.default
}
function Pane() {
  const [last, setLast] = useState(null)
  const [history, setHistory] = useState([])
  useEffect(() => {
    const unsubscribe = host.onEvent?.('plugin.rariflat.tool', (event) => {
      const payload = event?.payload || event || {}
      const phase = payload.phase || 'done'
      const tool = payload.tool || 'unknown tool'
      const success = payload.success !== false
      const item = phase === 'blocked'
        ? { ...CHARACTERS.error, tool, success: false, phase, reason: payload.reason || '' }
        : { ...getChar(tool), tool, success, phase, reason: payload.reason || '' }
      setLast(item)
      setHistory((items) => [item, ...items].slice(0, 10))
      haptic(phase === 'blocked' ? 'warning' : 'tap')
    })
    return () => unsubscribe?.()
  }, [])
  const label = (item) => item.phase === 'blocked' ? 'blocked by guard'
    : item.phase === 'started' ? 'working…'
    : item.success ? 'succeeded' : 'encountered an error'
  return jsxs('div', {
    className: 'flex h-full flex-col gap-3 p-3 text-sm',
    children: [
      jsx('div', { className: 'text-lg font-semibold tracking-tight', children: 'Rariflat' }),
      last ? jsxs('div', {
        className: 'rounded-xl p-4 text-center transition-all',
        style: { background: last.color + '18', border: `1px solid ${last.color}55` },
        children: [
          jsx('div', { className: 'text-5xl', children: last.emoji }),
          jsx('div', { className: 'mt-1 font-medium', children: last.name }),
          jsx('div', { className: 'mt-0.5 text-xs opacity-70', children: label(last) }),
          jsx('div', { className: 'mt-1 text-[11px] opacity-50', children: last.tool }),
          last.reason ? jsx('div', { className: 'mt-1 text-[11px] opacity-60', children: last.reason }) : null,
        ],
      }) : jsx('div', { className: 'rounded-xl border border-dashed border-white/10 p-6 text-center text-xs opacity-50', children: 'Waiting for tool calls…' }),
      jsx('div', { className: 'mt-1 text-xs font-medium opacity-60', children: 'Recent' }),
      history.length ? history.map((item, index) => jsxs('div', {
        className: 'flex items-center gap-2 text-xs',
        children: [
          jsx('span', { children: item.emoji }),
          jsx('span', { className: 'flex-1 truncate opacity-80', children: item.tool }),
          jsx('span', { className: item.success ? 'text-emerald-400' : 'text-rose-400', children: item.phase === 'started' ? '…' : item.success ? '✓' : '✗' }),
        ],
      }, index)) : jsx('div', { className: 'text-xs opacity-40', children: 'None yet' }),
    ],
  })
}
export default {
  id: 'rariflat',
  name: 'Rariflat',
  register(ctx) {
    ctx.register({ id: 'status-pane', area: 'panes', title: 'Rariflat',
      data: { placement: 'right', width: '300px' }, render: () => jsx(Pane, {}) })
  },
}
