/**
 * Template section images for Markdown reports — same assets for all users per report type.
 * Keys are matched with `sectionTitle.includes(key)`; longest keys are checked first.
 *
 * Gender variants: for 7 themes, paths `section-{theme}-female.png` / `section-{theme}-neutral.png`
 * are applied via `genderizeSectionImagePath` (male uses base `section-{theme}.png`).
 */

const S = (name: string) => `/illustrations/sections/${name}`

/** Themes that have `-female` / `-neutral` asset variants (not love/social/astro). */
const GENDERED_THEMES = new Set([
  'overview',
  'personality',
  'career',
  'finance',
  'health',
  'growth',
  'tone',
])

export type ReportGender = 'female' | 'male' | ''

/**
 * Strip leading chapter indices from LLM headings (e.g. "1. 太阳星座解读" → "太阳星座解读")
 * so keyword maps match and UI does not duplicate the badge number.
 */
export function stripLeadingSectionIndex(title: string): string {
  let t = title.trim()
  let prev = ''
  while (t !== prev) {
    prev = t
    t = t
      .replace(/^[\d０-９]+[.．、，,]\s*/, '')
      .replace(/^[一二三四五六七八九十]+[、．]\s*/, '')
      .trim()
  }
  return t
}

/** Resolve image path from keyword map (longest keyword wins). */
export function resolveSectionImage(title: string, keywordToSrc: Record<string, string>): string | undefined {
  const normalized = stripLeadingSectionIndex(title)
  const keys = Object.keys(keywordToSrc).sort((a, b) => b.length - a.length)
  for (const k of keys) {
    if (normalized.includes(k)) return keywordToSrc[k]
  }
  return undefined
}

/**
 * Swap section-* base PNG to gendered filename when the theme supports it.
 * `gender` omitted or `'male'` keeps default male art; `''` uses neutral assets.
 */
export function genderizeSectionImagePath(
  src: string | undefined,
  gender: ReportGender | undefined,
): string | undefined {
  if (!src) return undefined
  const g = gender ?? 'male'
  const m = src.match(/\/section-(overview|personality|career|finance|health|growth|tone)\.png(?:\?.*)?$/i)
  if (!m) return src
  const theme = m[1].toLowerCase()
  if (!GENDERED_THEMES.has(theme)) return src
  const base = `/illustrations/sections/section-${theme}`
  if (g === 'female') return `${base}-female.png`
  if (g === '') return `${base}-neutral.png`
  return `${base}.png`
}

/** Normalize loose strings from API / profile into ReportGender. */
export function normalizeReportGender(raw: string | undefined | null): ReportGender | undefined {
  if (raw === undefined || raw === null) return undefined
  if (raw === '') return ''
  const x = String(raw).toLowerCase().trim()
  if (x === 'unknown') return undefined
  if (x === 'female' || x === 'f' || x === '女') return 'female'
  if (x === 'male' || x === 'm' || x === '男') return 'male'
  return undefined
}

/** Read gender from saved report `input_data` (personality / DLC / compatibility). */
export function resolveReportGenderFromInput(input: Record<string, unknown> | undefined): ReportGender | undefined {
  if (!input) return undefined
  const top = input.gender
  if (typeof top === 'string') {
    return normalizeReportGender(top)
  }
  const p1 = input.person1 as { gender?: string } | undefined
  if (p1 && typeof p1.gender === 'string') {
    const n = normalizeReportGender(p1.gender)
    if (n === 'female' || n === 'male') return n
  }
  return undefined
}

export function sectionImagesForReportType(
  reportType: string,
): Record<string, string> | undefined {
  switch (reportType) {
    case 'personality':
    case 'personality_career':
    case 'personality_love':
    case 'personality_growth':
      return SECTION_IMAGES_PERSONALITY
    case 'annual':
      return SECTION_IMAGES_ANNUAL
    case 'compatibility':
      return SECTION_IMAGES_COMPATIBILITY
    case 'astro_event':
      return SECTION_IMAGES_ASTRO_EVENT
    default:
      return undefined
  }
}

/** 年度运势参考 — 概述 / 基调 / 事业学业 / 感情 / 财务 / 健康 / 成长等 */
export const SECTION_IMAGES_ANNUAL: Record<string, string> = {
  整体基调: S('section-tone.png'),
  年度主题: S('section-tone.png'),
  分季度节奏: S('section-growth.png'),
  分季度: S('section-growth.png'),
  机遇与提醒: S('section-growth.png'),
  行动建议: S('section-growth.png'),
  概述: S('section-overview.png'),
  总述: S('section-overview.png'),
  总论: S('section-overview.png'),
  事业与学业: S('section-career.png'),
  事业与财富节奏: S('section-career.png'),
  学业方面: S('section-career.png'),
  事业上: S('section-career.png'),
  职场中: S('section-career.png'),
  事业: S('section-career.png'),
  学业: S('section-career.png'),
  职场: S('section-career.png'),
  财富节奏: S('section-career.png'),
  感情与亲密关系: S('section-love.png'),
  感情: S('section-love.png'),
  亲密关系: S('section-love.png'),
  情感: S('section-love.png'),
  恋爱: S('section-love.png'),
  关系: S('section-love.png'),
  财务: S('section-finance.png'),
  财运: S('section-finance.png'),
  金钱: S('section-finance.png'),
  健康: S('section-health.png'),
  身心: S('section-health.png'),
  成长: S('section-growth.png'),
  建议: S('section-growth.png'),
  复盘: S('section-growth.png'),
}

/**
 * 个人性格报告 — 栏目与底图一一对应，禁止用「性格」等短词兜底到同一张图。
 * 匹配仍按最长 key 优先（resolveSectionImage）。
 */
export const SECTION_IMAGES_PERSONALITY: Record<string, string> = {
  成长建议与行动清单: S('section-health.png'),
  太阳星座与核心动机: S('section-personality.png'),
  性格优势与挑战: S('section-growth.png'),
  感情与亲密关系: S('section-love.png'),
  事业与财富节奏: S('section-career.png'),
  太阳星座解读: S('section-personality.png'),
  性格优势: S('section-growth.png'),
  性格挑战: S('section-tone.png'),
  核心动机: S('section-personality.png'),
  行动清单: S('section-health.png'),
  成长建议: S('section-health.png'),
  概述: S('section-overview.png'),
  总述: S('section-overview.png'),
  太阳星座: S('section-personality.png'),
  感情: S('section-love.png'),
  亲密: S('section-love.png'),
  事业: S('section-career.png'),
  职场: S('section-career.png'),
  财富: S('section-finance.png'),
}

/** 配对分析 — 双人插图，无性别变体；key 与 LLM 栏目标题对齐 */
export const SECTION_IMAGES_COMPATIBILITY: Record<string, string> = {
  你们的化学反应: S('section-compat-chemistry.png'),
  化学反应: S('section-compat-chemistry.png'),
  缘分指数: S('section-compat-fate.png'),
  甜蜜优势: S('section-compat-sweet.png'),
  潜在摩擦: S('section-compat-friction.png'),
  相处秘诀: S('section-compat-secrets.png'),
  相处之道: S('section-compat-secrets.png'),
  秘诀: S('section-compat-secrets.png'),
  概述: S('section-compat-overview.png'),
  总述: S('section-compat-overview.png'),
  缘分: S('section-compat-fate.png'),
  甜蜜: S('section-compat-sweet.png'),
  摩擦: S('section-compat-friction.png'),
  冲突: S('section-compat-friction.png'),
  双人能量与节奏: S('section-compat-overview.png'),
  沟通与相处模式: S('section-compat-chemistry.png'),
  长期关系参考: S('section-compat-sweet.png'),
  冲突与修复建议: S('section-compat-friction.png'),
}

/** 天象事件参考 */
export const SECTION_IMAGES_ASTRO_EVENT: Record<string, string> = {
  背景说明: S('section-astro.png'),
  天象背景: S('section-astro.png'),
  背景: S('section-astro.png'),
  星象: S('section-astro.png'),
  天象: S('section-astro.png'),
  可能感受: S('section-overview.png'),
  感受: S('section-overview.png'),
  行动与复盘: S('section-growth.png'),
  行动建议: S('section-growth.png'),
  行动: S('section-growth.png'),
  复盘: S('section-growth.png'),
  概述: S('section-overview.png'),
}
