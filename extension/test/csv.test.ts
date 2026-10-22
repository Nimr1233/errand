import { describe, it, expect } from 'vitest'
import { toCSV } from '../src/panel/csv'

describe('csv', () => {
  it('quotes commas, quotes and newlines (RFC 4180)', () => {
    expect(toCSV(['a', 'b'], [['1,2', 'say "hi"'], ['x\ny', 'z']]))
      .toBe('a,b\r\n"1,2","say ""hi"""\r\n"x\ny",z')
  })
})
