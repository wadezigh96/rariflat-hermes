// Pure event contract shared by the Desktop pane and its Node tests.
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
