import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeToolEvent } from '../desktop/event-contract.mjs'

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

test('unknown payloads safely normalize to a completed event', () => {
  assert.deepEqual(normalizeToolEvent(null), {
    phase: 'done', tool: 'unknown tool', success: true, reason: '', hapticType: 'tap',
  })
})
