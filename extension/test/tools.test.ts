import { describe, it, expect } from 'vitest'
import { needsConfirm, validate } from '../src/panel/tools'

describe('confirm gate', () => {
  it('triggers on a dangerous verb in the target name', () => expect(needsConfirm('click', { id: 'f0:1' }, 'Buy now')).toBe(true))
  it('triggers on the irreversible flag', () => expect(needsConfirm('click', { id: 'f0:1', irreversible: true }, 'Next')).toBe(true))
  it('leaves a safe click alone', () => expect(needsConfirm('click', { id: 'f0:1' }, 'Show more')).toBe(false))
  it('ignores tools that do not act', () => expect(needsConfirm('scroll', { direction: 'down' }, 'delete')).toBe(false))
  it('gates type only when it submits', () => {
    expect(needsConfirm('type', { id: 'f0:1', text: 'x' }, 'Search')).toBe(false)
    expect(needsConfirm('type', { id: 'f0:1', text: 'x', submit: true }, 'Send')).toBe(true)
  })
})

describe('validate', () => {
  it('rejects unknown properties', () => expect(validate('type', { id: 'f0:1', text: 'x', bogus: 1 }).ok).toBe(false))
  it('accepts a good save_rows call', () => expect(validate('save_rows', { columns: ['a'], rows: [['1']] }).ok).toBe(true))
  it('caps the wait_for timeout at 10s', () => expect(validate('wait_for', { timeout_ms: 99999 }).ok).toBe(false))
  it('requires http(s) for goto_url', () => expect(validate('goto_url', { url: 'file:///etc' }).ok).toBe(false))
})
