import test from 'node:test'
import assert from 'node:assert/strict'
import { getEvidenceStatus, normalizeRouteEvent, normalizeToolEvent } from '../desktop/event-contract.mjs'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'

const pluginSource = readFileSync(new URL('../desktop/plugin.js', import.meta.url), 'utf8')

test('Desktop runtime entry imports only Hermes SDK and React modules', () => {
  const imports = [
    ...[...pluginSource.matchAll(/\bfrom\s+['"]([^'"]+)['"]/g)].map((match) => match[1]),
    ...[...pluginSource.matchAll(/^\s*import\s+['"]([^'"]+)['"]/gm)].map((match) => match[1]),
  ]
  assert.deepEqual(imports, ['@hermes/plugin-sdk', 'react', 'react/jsx-runtime'])
  assert.doesNotMatch(pluginSource, /\bimport\s*\(/, 'runtime plugins cannot load dynamic modules')
})

test('inline Desktop normalizers match the tested Node event contract', () => {
  const runtimeSource = pluginSource
    .replace(/^\s*import\b.*$/gm, '')
    .replace(/export default \{[\s\S]*$/, '')
    + '\nglobalThis.__rariflat = { getEvidenceStatus, normalizeRouteEvent, normalizeToolEvent }'
  const sandbox = {}
  runInNewContext(runtimeSource, sandbox)
  const runtime = sandbox.__rariflat

  const toolCases = [
    null,
    { phase: 'started', tool: 'browser', success: null },
    { payload: { phase: 'done', tool: 'browser', success: true } },
    { payload: { phase: 'done', tool: 'browser', success: false, reason: 'timeout' } },
    { payload: { phase: 'blocked', tool: 'browser', success: false, reason: 'guard' } },
    { payload: { phase: 'not-a-phase', tool: '', success: false, extra: 'discarded' } },
  ]
  for (const input of toolCases) {
    assert.deepEqual(JSON.parse(JSON.stringify(runtime.normalizeToolEvent(input))), normalizeToolEvent(input))
  }

  const routeCases = [
    { payload: {
      task: 'must not be exposed',
      recommended: [{
        skill: 'web_search', score: 84.25, uses: 4, successes: 3, failures: 1,
        factors: { task_fit: 90, reliability: 75, rarity: 60, restraint: 100 },
        reason: 'contains private task tokens',
      }],
      weights: { task_fit: 40, reliability: 25, rarity: 20, restraint: 15 },
      minimum_observations: 5,
    } },
    { recommended: [
      { skill: 'first', score: 120, uses: 2, successes: 5, failures: 8, factors: { task_fit: -1 } },
      { skill: 'second', score: 'NaN', uses: -4 },
      { skill: 'third', score: 50 },
      { skill: 'fourth', score: 99 },
      { skill: '   ', score: 99 },
    ], extra: 'discarded' },
    { recommended: [{
      skill: 'large-history', score: 90, uses: 1_000_000, successes: 900_000, failures: 100_000,
      counts_capped: true, factors: {},
    }] },
    { payload: { recommended: 'not-an-array', weights: null, minimum_observations: 'bad' } },
  ]
  for (const input of routeCases) {
    assert.deepEqual(JSON.parse(JSON.stringify(runtime.normalizeRouteEvent(input))), normalizeRouteEvent(input))
  }

  const evidenceCases = [
    [{ uses: 4 }, 5],
    [{ uses: 5 }, 5],
    [{ uses: 1_000_000, countsCapped: true }, 5],
    [{ uses: 0 }, 0],
  ]
  for (const [item, minimum] of evidenceCases) {
    assert.deepEqual(
      JSON.parse(JSON.stringify(runtime.getEvidenceStatus(item, minimum))),
      getEvidenceStatus(item, minimum),
    )
  }
})

test('normalizes every emitted tool phase for Desktop', () => {
  const cases = [
    [{ phase: 'started', tool: 'browser', success: null }, 'started', null, 'tap'],
    [{ phase: 'done', tool: 'browser', success: true }, 'done', true, 'tap'],
    [{ phase: 'done', tool: 'browser', success: false, reason: 'timeout' }, 'done', false, 'warning'],
    [{ phase: 'blocked', tool: 'browser', success: false, reason: 'guard' }, 'blocked', false, 'warning'],
  ]
  for (const [input, phase, success, haptic] of cases) {
    const event = normalizeToolEvent({ payload: input })
    assert.equal(event.phase, phase)
    assert.equal(event.success, success)
    assert.equal(event.hapticType, haptic)
    assert.equal(event.tool, 'browser')
  }
})

test('unknown tool payloads safely normalize to a completed event', () => {
  assert.deepEqual(normalizeToolEvent(null), {
    phase: 'done', tool: 'unknown tool', success: true, reason: '', hapticType: 'tap',
  })
})

test('normalizes a privacy-safe route decision and preserves its evidence threshold', () => {
  const event = normalizeRouteEvent({ payload: {
    task: 'must not be exposed',
    recommended: [{
      skill: 'web_search', score: 84.25, uses: 4, successes: 3, failures: 1,
      factors: { task_fit: 90, reliability: 75, rarity: 60, restraint: 100 },
      reason: 'contains private task tokens',
    }],
    weights: { task_fit: 40, reliability: 25, rarity: 20, restraint: 15 },
    minimum_observations: 5,
  } })

  assert.deepEqual(event, {
    recommended: [{
      skill: 'web_search', score: 84.25, uses: 4, successes: 3, failures: 1, countsCapped: false,
      factors: { task_fit: 90, reliability: 75, rarity: 60, restraint: 100 },
    }],
    weights: { task_fit: 40, reliability: 25, rarity: 20, restraint: 15 },
    minimumObservations: 5,
  })
  assert.doesNotMatch(JSON.stringify(event), /private task tokens|must not be exposed/)
  assert.deepEqual(getEvidenceStatus(event.recommended[0], event.minimumObservations), {
    limited: true,
    countsCapped: false,
    label: 'Limited history · 4 observed calls; fewer than 5 calls',
    compactLabel: 'Limited history · 4 observed calls',
  })
  assert.equal(getEvidenceStatus({ uses: 5 }, 5).limited, false)
})

test('limits route cards and clamps malformed metrics without retaining unknown fields', () => {
  const event = normalizeRouteEvent({
    recommended: [
      { skill: 'first', score: 120, uses: 2, successes: 5, failures: 8, factors: { task_fit: -1 } },
      { skill: 'second', score: 'NaN', uses: -4 },
      { skill: 'third', score: 50 },
      { skill: 'fourth', score: 99 },
      { skill: '   ', score: 99 },
    ],
    extra: 'discarded',
  })

  assert.equal(event.recommended.length, 3)
  assert.deepEqual(event.recommended[0], {
    skill: 'first', score: 100, uses: 2, successes: 2, failures: 0, countsCapped: false,
    factors: { task_fit: 0, reliability: 0, rarity: 0, restraint: 0 },
  })
  assert.deepEqual(event.recommended[1], {
    skill: 'second', score: 0, uses: 0, successes: 0, failures: 0, countsCapped: false,
    factors: { task_fit: 0, reliability: 0, rarity: 0, restraint: 0 },
  })
  assert.equal(event.minimumObservations, 5)
  assert.equal('extra' in event, false)
})

test('keeps display counts consistent when the event marks saturation', () => {
  const event = normalizeRouteEvent({ recommended: [{
    skill: 'large-history', score: 90, uses: 1_000_000, successes: 900_000, failures: 100_000,
    counts_capped: true, factors: {},
  }] })
  const item = event.recommended[0]
  assert.equal(item.successes + item.failures, item.uses)
  assert.equal(getEvidenceStatus(item).countsCapped, true)
  assert.match(getEvidenceStatus(item).label, /At least 1,000,000 observed calls/)
})


test('Desktop pane exposes live Hermes and A2A agent tier rankings', () => {
  assert.match(pluginSource, /function AgentRankingCard\(/)
  assert.match(pluginSource, /plugin\.rariflat\.agent_rank/)
  assert.match(pluginSource, /MYTHIC|LEGEND|EPIC/)
  assert.match(pluginSource, /completed tasks/)
  assert.match(pluginSource, /no automatic install or dispatch/)
})


test('Desktop agent ranking separates requested fit and historical performance', () => {
  assert.match(pluginSource, /agent\.requested_task_fit/)
  assert.match(pluginSource, /agent\.performance_score/)
  assert.match(pluginSource, /Source not independently verified/)
})
