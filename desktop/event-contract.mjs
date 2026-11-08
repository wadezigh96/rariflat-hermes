// Pure event contracts shared by the Desktop pane and Node tests.
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

export function normalizeToolEvent(event) {
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

export function normalizeRouteEvent(event) {
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

export function getEvidenceStatus(item, minimumObservations = DEFAULT_MINIMUM_OBSERVATIONS) {
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
