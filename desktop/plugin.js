// Rariflat Desktop pane — receives the official Hermes plugin event bridge.
import { host, haptic } from '@hermes/plugin-sdk'
import { useState, useEffect } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

// Hermes Desktop evaluates runtime plugins from a blob URL and permits only
// SDK/React imports. Keep these pure normalizers inline; event-contract.mjs
// mirrors them for the Node contract tests.
const ROUTE_FACTORS = ['task_fit', 'reliability', 'rarity', 'restraint']
const DEFAULT_WEIGHTS = { task_fit: 40, reliability: 25, rarity: 20, restraint: 15 }
const DEFAULT_MINIMUM_OBSERVATIONS = 5
const MAX_RECOMMENDATIONS = 3
const MAX_ROUTE_COUNT = 1_000_000

function boundedNumber(value, min = 0, max = 100) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : 0
}

function boundedCount(value) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.min(MAX_ROUTE_COUNT, Math.max(0, Math.trunc(number))) : 0
}

function safeLabel(value) {
  return typeof value === 'string'
    ? value.replace(/[\u0000-\u001f\u007f]/g, '').trim().slice(0, 80)
    : ''
}

function normalizeToolEvent(event) {
  const payload = event?.payload || event || {}
  const phase = ['started', 'done', 'blocked'].includes(payload.phase) ? payload.phase : 'done'
  const tool = typeof payload.tool === 'string' && payload.tool ? payload.tool : 'unknown tool'
  const success = phase === 'started' ? null : phase === 'blocked' ? false : payload.success !== false
  return {
    phase,
    tool,
    success,
    reason: typeof payload.reason === 'string' ? payload.reason : '',
    hapticType: phase === 'blocked' ? 'warning' : phase === 'done' && success === false ? 'warning' : 'tap',
  }
}

function normalizeRouteEvent(event) {
  const payload = event?.payload || event || {}
  const rawRecommendations = Array.isArray(payload.recommended) ? payload.recommended : []
  const recommended = rawRecommendations.slice(0, MAX_RECOMMENDATIONS).flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return []
    const skill = safeLabel(item.skill)
    if (!skill) return []
    const uses = boundedCount(item.uses)
    const successes = Math.min(uses, boundedCount(item.successes))
    const failures = uses - successes
    const factors = item.factors && typeof item.factors === 'object' ? item.factors : {}
    return [{
      skill,
      score: boundedNumber(item.score),
      uses,
      successes,
      failures,
      countsCapped: item.counts_capped === true,
      factors: Object.fromEntries(ROUTE_FACTORS.map((factor) => [factor, boundedNumber(factors[factor])])),
    }]
  })
  const rawWeights = payload.weights && typeof payload.weights === 'object' ? payload.weights : {}
  const weights = Object.fromEntries(ROUTE_FACTORS.map((factor) => [
    factor,
    rawWeights[factor] === undefined ? DEFAULT_WEIGHTS[factor] : boundedNumber(rawWeights[factor]),
  ]))
  const requestedMinimum = boundedCount(payload.minimum_observations)
  return {
    recommended,
    weights,
    minimumObservations: requestedMinimum || DEFAULT_MINIMUM_OBSERVATIONS,
  }
}

function getEvidenceStatus(item, minimumObservations = DEFAULT_MINIMUM_OBSERVATIONS) {
  const uses = boundedCount(item?.uses)
  const minimum = boundedCount(minimumObservations) || DEFAULT_MINIMUM_OBSERVATIONS
  const calls = `${uses.toLocaleString()} observed call${uses === 1 ? '' : 's'}`
  if (item?.countsCapped === true) {
    return {
      limited: false,
      countsCapped: true,
      label: `At least ${calls}; count capped for display`,
      compactLabel: `At least ${uses.toLocaleString()} calls`,
    }
  }
  const limited = uses < minimum
  return {
    limited,
    countsCapped: false,
    label: limited ? `Limited history · ${calls}; fewer than ${minimum} calls` : `Evidence · ${calls}`,
    compactLabel: limited ? `Limited history · ${calls}` : calls,
  }
}

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

const FACTORS = [
  ['task_fit', 'Task fit'],
  ['reliability', 'Reliability'],
  ['rarity', 'Rarity'],
  ['restraint', 'Restraint'],
]

function getChar(tool) {
  for (const token of (tool || '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)) {
    if (CHARACTERS[token]) return CHARACTERS[token]
  }
  return CHARACTERS.default
}

function percent(value) {
  return `${Math.round(value)}%`
}

function EvidenceBadge({ item, minimum, compact = false }) {
  const status = getEvidenceStatus(item, minimum)
  const caution = status.limited || status.countsCapped
  return jsx('span', {
    className: `inline-flex max-w-full rounded-full border px-2 py-0.5 text-[10px] ${caution ? 'border-amber-300/50 text-amber-100' : 'border-emerald-300/40 text-emerald-100'}`,
    children: compact ? status.compactLabel : status.label,
  })
}

function factorRows(item, weights) {
  return FACTORS.map(([key, label]) => {
    const value = item.factors[key]
    return jsxs('div', {
      className: 'space-y-1',
      children: [
        jsxs('div', {
          className: 'flex justify-between gap-2 text-[10px]',
          children: [
            jsx('span', { children: label }),
            jsx('span', { children: `${percent(value)} · ${weights[key]}% weight` }),
          ],
        }),
        jsx('div', {
          className: 'h-1 overflow-hidden rounded bg-white/10',
          'aria-hidden': 'true',
          children: jsx('div', {
            className: 'h-full rounded bg-emerald-400',
            style: { width: `${value}%` },
          }),
        }),
      ],
    }, key)
  })
}

function RouteCard({ decision }) {
  const best = decision.recommended[0]
  return jsxs('section', {
    className: 'rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-3',
    'aria-label': 'Rariflat route decision',
    children: [
      jsxs('div', {
        className: 'flex items-center justify-between gap-2',
        children: [
          jsx('h2', { className: 'font-semibold', children: 'Route decision' }),
          jsx('span', { className: 'rounded-full border px-2 py-0.5 text-[10px]', children: 'Advisory' }),
        ],
      }),
      jsx('p', {
        className: 'mt-1 text-[10px] opacity-70',
        children: 'Recommendations only — no agent dispatch or automatic tool call.',
      }),
      decision.recommended.length
        ? jsx('div', {
          className: 'mt-3 space-y-3',
          children: jsxs('div', {
            className: 'space-y-3',
            children: [
              jsxs('div', {
                className: 'rounded-lg border border-white/10 bg-black/10 p-2',
                children: [
                  jsx('div', { className: 'text-[10px] font-medium uppercase tracking-wide opacity-60', children: 'Top recommendation' }),
                  jsxs('div', {
                    className: 'mt-1 flex items-baseline justify-between gap-2',
                    children: [
                      jsx('strong', { className: 'truncate text-sm', children: best.skill }),
                      jsx('span', { className: 'shrink-0 text-xs font-semibold', children: `${percent(best.score)} score` }),
                    ],
                  }),
                  jsx(EvidenceBadge, { item: best, minimum: decision.minimumObservations }),
                  jsx('p', { className: 'text-[10px] text-slate-300', children: best.countsCapped
                    ? 'Counts capped for display; exact success/failure totals are omitted.'
                    : `${best.successes} successes · ${best.failures} failures observed` }),
                  jsx('div', { className: 'mt-2 space-y-2', children: factorRows(best, decision.weights) }),
                ],
              }),
              decision.recommended.length > 1
                ? jsxs('div', {
                  children: [
                    jsx('h3', { className: 'mb-1 text-[10px] font-medium uppercase tracking-wide opacity-60', children: 'Alternatives' }),
                    jsx('ol', {
                      className: 'space-y-2',
                      children: decision.recommended.slice(1).map((item, index) => jsxs('li', {
                        className: 'flex flex-col gap-1 text-[10px]',
                        children: [
                          jsxs('div', {
                            className: 'flex items-start justify-between gap-2',
                            children: [
                              jsx('span', { className: 'min-w-0 truncate', children: `${index + 2}. ${item.skill}` }),
                              jsx('span', { className: 'shrink-0 text-right', children: `${percent(item.score)} score` }),
                            ],
                          }),
                          jsx(EvidenceBadge, { item, minimum: decision.minimumObservations, compact: true }),
                        ],
                      }, `${item.skill}-${index}`)),
                    }),
                  ],
                })
                : null,
            ],
          }),
        })
        : jsx('p', {
          className: 'mt-3 text-xs text-slate-300',
          children: 'No observed tools yet. Make ordinary tool calls before requesting recommendations.',
        }),
    ],
  })
}

function AgentRankingCard({ ranking }) {
  return jsxs('section', {
    className: 'rounded-xl border border-violet-400/30 bg-violet-400/5 p-3',
    'aria-label': 'Hermes and A2A agent ranking',
    children: [
      jsxs('div', { className: 'flex items-center justify-between gap-2', children: [
        jsx('h2', { className: 'font-semibold', children: 'Agent ranking' }),
        jsx('span', { className: 'rounded-full border px-2 py-0.5 text-[10px]', children: 'Live on-data' }),
      ] }),
      jsx('p', { className: 'mt-1 text-[10px] opacity-70', children: 'Hermes catalog + A2A · recommendations only; no automatic install or dispatch.' }),
      ranking.recommended.length ? jsx('ol', {
        className: 'mt-3 space-y-3',
        children: ranking.recommended.map((agent) => jsxs('li', {
          className: 'rounded-lg border border-white/10 bg-black/10 p-2',
          children: [
            jsxs('div', { className: 'flex items-start justify-between gap-2', children: [
              jsxs('div', { className: 'min-w-0', children: [
                jsx('strong', { className: 'block truncate text-xs', children: `#${agent.rank} · ${agent.name}` }),
                jsx('span', { className: 'text-[10px] opacity-60', children: `${agent.kind.toUpperCase()} · ${agent.status}` }),
              ] }),
              jsx('span', { className: 'shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold', children: agent.tier }),
            ] }),
            jsxs('div', { className: 'mt-2 flex justify-between text-[10px]', children: [
              jsx('span', { children: `Ranking score ${Math.round(agent.score)}%` }),
              jsx('span', { children: `${agent.observations} completed tasks` }),
            ] }),
            jsx('div', { className: 'mt-1 h-1 overflow-hidden rounded bg-white/10', children:
              jsx('div', { className: 'h-full rounded bg-violet-400', style: { width: `${agent.score}%` } }) }),
            jsx('div', { className: 'mt-2 grid grid-cols-2 gap-1 text-[10px] opacity-80', children: [
              jsx('span', { children: `Success ${Math.round(agent.success_rate)}%` }),
              jsx('span', { children: `Task fit ${Math.round(agent.average_task_fit)}%` }),
              jsx('span', { children: agent.average_quality == null ? 'Quality: not supplied' : `Quality ${Math.round(agent.average_quality)}%` }),
              jsx('span', { children: agent.average_duration_seconds == null ? 'Time: n/a' : `Avg ${agent.average_duration_seconds}s` }),
            ] }),
            jsx('p', { className: 'mt-2 text-[10px] opacity-60', children: agent.evidence === 'insufficient_observations'
              ? 'Not ranked by tier yet · needs at least 5 real completions.'
              : 'Rates calculated from recorded completed tasks.' }),
            jsx('p', { className: 'mt-1 break-all text-[10px] opacity-70', children: `Source: ${agent.source || 'not provided'}` }),
            jsx('p', { className: 'break-all text-[10px] opacity-70', children: agent.kind === 'a2a'
              ? `Endpoint: ${agent.endpoint || 'not connected'}`
              : `Install reference: ${agent.install_ref || 'not installed'}` }),
            jsx('p', { className: 'text-[10px] opacity-60', children: 'Source not independently verified · review before installing or connecting.' }),
          ],
        }, agent.id)),
      }) : jsx('p', { className: 'mt-3 text-xs opacity-70', children: 'No agents registered yet. Register a Hermes catalog entry or A2A Agent Card first.' }),
    ],
  })
}

function Pane() {
  const [last, setLast] = useState(null)
  const [agentRanking, setAgentRanking] = useState(null)
  const [history, setHistory] = useState([])
  const [decision, setDecision] = useState(null)
  const [liveMessage, setLiveMessage] = useState('')
  useEffect(() => {
    const unsubscribeTool = host.onEvent?.('plugin.rariflat.tool', (event) => {
      const { phase, tool, success, reason, hapticType } = normalizeToolEvent(event)
      const item = phase === 'blocked'
        ? { ...CHARACTERS.error, tool, success: false, phase, reason }
        : { ...getChar(tool), tool, success, phase, reason }
      setLast(item)
      setHistory((items) => [item, ...items].slice(0, 10))
      if (phase === 'blocked') setLiveMessage(`${tool} blocked by the Rariflat guard.`)
      else if (phase === 'done' && (tool !== 'rariflat_route' || !success)) setLiveMessage(`${tool} call ${success ? 'succeeded' : 'failed'}.`)
      haptic(hapticType)
    })
    const unsubscribeRoute = host.onEvent?.('plugin.rariflat.route', (event) => {
      const nextDecision = normalizeRouteEvent(event)
      setDecision(nextDecision)
      const best = nextDecision.recommended[0]
      setLiveMessage(best
        ? `Rariflat recommends ${best.skill}, score ${Math.round(best.score)} out of 100. ${getEvidenceStatus(best, nextDecision.minimumObservations).label}. Advisory only.`
        : 'Rariflat has no observed tools to recommend yet.')
    })
    const unsubscribeAgentRank = host.onEvent?.('plugin.rariflat.agent_rank', (event) => {
      const payload = event?.payload || event || {}
      const recommended = Array.isArray(payload.recommended) ? payload.recommended.slice(0, 10) : []
      setAgentRanking({ recommended })
      const best = recommended[0]
      setLiveMessage(best
        ? `Agent ranking updated. ${best.name} is ${best.tier}, based on ${best.observations} completed tasks.`
        : 'No registered Hermes or A2A agents to rank yet.')
    })
    return () => {
      unsubscribeTool?.()
      unsubscribeRoute?.()
      unsubscribeAgentRank?.()
    }
  }, [])
  const label = (item) => item.phase === 'blocked' ? 'blocked by guard'
    : item.phase === 'started' ? 'working…'
    : item.success ? 'succeeded' : 'encountered an error'
  return jsxs('div', {
    className: 'flex h-full flex-col gap-3 overflow-auto p-3 text-sm',
    children: [
      jsx('div', { className: 'text-lg font-semibold tracking-tight', children: 'Rariflat' }),
      jsx('div', { className: 'sr-only', role: 'status', 'aria-live': 'polite', 'aria-atomic': 'true', children: liveMessage }),
      decision ? jsx(RouteCard, { decision }) : null,
      agentRanking ? jsx(AgentRankingCard, { ranking: agentRanking }) : null,
      last ? jsxs('div', {
        className: 'rounded-xl p-4 text-center transition-all motion-reduce:transition-none',
        style: { background: last.color + '18', border: `1px solid ${last.color}55` },
        children: [
          jsx('div', { className: 'text-5xl', 'aria-hidden': 'true', children: last.emoji }),
          jsx('div', { className: 'mt-1 font-medium', children: last.name }),
          jsx('div', { className: 'mt-0.5 text-xs opacity-70', children: label(last) }),
          jsx('div', { className: 'mt-1 text-[11px] opacity-70', children: last.tool }),
          last.reason ? jsx('div', { className: 'mt-1 text-[11px] opacity-70', children: last.reason }) : null,
        ],
      }) : jsx('div', { className: 'rounded-xl border border-dashed border-white/10 p-6 text-center text-xs opacity-70', children: 'Waiting for tool calls…' }),
      jsx('div', { className: 'mt-1 text-xs font-medium opacity-70', children: 'Recent tool calls' }),
      history.length ? history.map((item, index) => jsxs('div', {
        className: 'flex items-center gap-2 text-xs',
        children: [
          jsx('span', { 'aria-hidden': 'true', children: item.emoji }),
          jsx('span', { className: 'flex-1 truncate opacity-80', children: item.tool }),
          jsx('span', { className: item.success ? 'text-emerald-400' : 'text-rose-400', children: item.phase === 'started' ? 'In progress' : item.phase === 'blocked' ? 'Blocked' : item.success ? 'Succeeded' : 'Failed' }),
        ],
      }, index)) : jsx('div', { className: 'text-xs opacity-60', children: 'None yet' }),
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
