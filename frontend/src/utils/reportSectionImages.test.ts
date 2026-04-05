import { describe, expect, it } from 'vitest'
import {
  ANNUAL_CANONICAL_IMAGES,
  COMPATIBILITY_CANONICAL_IMAGES,
  PERSONALITY_CANONICAL_IMAGES,
  normalizeAnnualSectionTitle,
  normalizeCompatibilitySectionTitle,
  normalizePersonalitySectionTitle,
  resolveAnnualSectionImage,
  resolveCompatibilitySectionImage,
  resolvePersonalitySectionImage,
} from './reportSectionImages'

describe('resolvePersonalitySectionImage', () => {
  const paths = Object.values(PERSONALITY_CANONICAL_IMAGES)
  it('maps each canonical title to a unique asset path', () => {
    const unique = new Set(paths)
    expect(unique.size).toBe(paths.length)
  })

  it('exact match after stripping index', () => {
    expect(resolvePersonalitySectionImage('1. 太阳星座深度解读')).toBe(PERSONALITY_CANONICAL_IMAGES['太阳星座深度解读'])
    expect(resolvePersonalitySectionImage('2. 性格优势与挑战')).toBe(PERSONALITY_CANONICAL_IMAGES['性格优势与挑战'])
  })

  it('does not mis-route long titles containing 事业/感情 substrings', () => {
    const t = '事业与财富节奏（含感情与亲密关系参考）'
    expect(resolvePersonalitySectionImage(t)).toBe(PERSONALITY_CANONICAL_IMAGES['事业与财富节奏'])
  })

  it('prefix match for trailing parenthetical', () => {
    expect(normalizePersonalitySectionTitle('年度成长建议（本命）')).toBe('年度成长建议')
    expect(resolvePersonalitySectionImage('年度成长建议（补充）')).toBe(PERSONALITY_CANONICAL_IMAGES['年度成长建议'])
  })
})

describe('resolveCompatibilitySectionImage', () => {
  const paths = Object.values(COMPATIBILITY_CANONICAL_IMAGES)
  it('maps each canonical title to a unique asset path', () => {
    const unique = new Set(paths)
    expect(unique.size).toBe(paths.length)
  })

  it('exact match with index prefix', () => {
    expect(resolveCompatibilitySectionImage('1. 缘分指数')).toBe(COMPATIBILITY_CANONICAL_IMAGES['缘分指数'])
    expect(resolveCompatibilitySectionImage('3. 双人能量与节奏')).toBe(COMPATIBILITY_CANONICAL_IMAGES['双人能量与节奏'])
  })

  it('沟通与相处模式 maps to secrets art not chemistry', () => {
    expect(resolveCompatibilitySectionImage('沟通与相处模式')).toBe('/illustrations/sections/section-compat-secrets.png')
  })

  it('normalize strips trailing parenthetical', () => {
    expect(normalizeCompatibilitySectionTitle('冲突与修复建议（补充）')).toBe('冲突与修复建议')
  })
})

describe('resolveAnnualSectionImage', () => {
  const paths = Object.values(ANNUAL_CANONICAL_IMAGES)
  it('maps each canonical title to a unique asset path', () => {
    const unique = new Set(paths)
    expect(unique.size).toBe(paths.length)
  })

  it('exact match after stripping index', () => {
    expect(resolveAnnualSectionImage('1. 整体基调')).toBe(ANNUAL_CANONICAL_IMAGES['整体基调'])
    expect(resolveAnnualSectionImage('4. 财务与资源')).toBe(ANNUAL_CANONICAL_IMAGES['财务与资源'])
  })

  it('prefix match for trailing parenthetical', () => {
    expect(normalizeAnnualSectionTitle('月度提示（Q1–Q4）')).toBe('月度提示')
    expect(resolveAnnualSectionImage('月度提示（快照）')).toBe(ANNUAL_CANONICAL_IMAGES['月度提示'])
  })

  it('legacy long key fallback for old report headings', () => {
    expect(resolveAnnualSectionImage('感情与亲密关系')).toBe('/illustrations/sections/section-love.png')
  })
})
