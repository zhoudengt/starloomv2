import { describe, expect, it } from 'vitest'
import { triadInsightBlurb } from './triadInsightCopy'

describe('triadInsightBlurb', () => {
  it('returns identical string for identical placements (deterministic)', () => {
    const a = triadInsightBlurb('virgo', 'pisces', 'scorpio')
    const b = triadInsightBlurb('virgo', 'pisces', 'scorpio')
    expect(a).toBe(b)
    expect(a.length).toBeGreaterThan(30)
  })

  it('changes when any axis changes', () => {
    const base = triadInsightBlurb('virgo', 'pisces', 'scorpio')
    expect(triadInsightBlurb('libra', 'pisces', 'scorpio')).not.toBe(base)
    expect(triadInsightBlurb('virgo', 'aries', 'scorpio')).not.toBe(base)
    expect(triadInsightBlurb('virgo', 'pisces', 'libra')).not.toBe(base)
  })
})
