/**
 * Template section images for Markdown reports — same assets for all users per report type.
 * Keys are matched with `sectionTitle.includes(key)`; longest keys are checked first.
 *
 * Gender variants: for 7 themes, paths `section-{theme}-female.webp` / `section-{theme}-neutral.webp`
 * are applied via `genderizeSectionImagePath` (male uses base `section-{theme}.webp`).
 */

const S = (name: string) => `/illustrations/sections/${name.replace(/\.png$/, '.webp')}`

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

/** 个人性格报告七章正式标题（与 BlurLock / ReportGeneratingShell 一致）— 每章对应唯一底图。 */
export const PERSONALITY_CANONICAL_TITLES = [
  '太阳星座深度解读',
  '性格优势与挑战',
  '感情与亲密关系',
  '事业与财富节奏',
  '人际关系与社交',
  '年度成长建议',
  '专属行动清单',
] as const

/** 七章标题 → 唯一 section 插图（避免两章共用同一张）。 */
export const PERSONALITY_CANONICAL_IMAGES: Record<(typeof PERSONALITY_CANONICAL_TITLES)[number], string> = {
  太阳星座深度解读: S('section-personality.png'),
  性格优势与挑战: S('section-growth.png'),
  感情与亲密关系: S('section-love.png'),
  事业与财富节奏: S('section-career.png'),
  人际关系与社交: S('section-tone.png'),
  年度成长建议: S('section-overview.png'),
  专属行动清单: S('section-health.png'),
}

/**
 * 规范化性格报告章节标题，用于精确/前缀匹配。
 */
export function normalizePersonalitySectionTitle(title: string): string {
  let t = stripLeadingSectionIndex(title)
  t = t.replace(/\s+/g, ' ').trim()
  t = t.replace(/[（(][^）)]*[）)]\s*$/u, '').trim()
  return t
}

/**
 * 性格报告专用：优先完全匹配七章标题，再前缀匹配，最后才用宽松子串匹配（仅长 key），
 * 避免「事业」「感情」等短词误命中。
 */
export function resolvePersonalitySectionImage(title: string): string | undefined {
  const n = normalizePersonalitySectionTitle(title)
  const canonical = PERSONALITY_CANONICAL_IMAGES as Record<string, string>
  if (canonical[n]) return canonical[n]

  const ordered = [...PERSONALITY_CANONICAL_TITLES].sort((a, b) => b.length - a.length)
  for (const k of ordered) {
    if (n.startsWith(k)) return canonical[k]
  }

  const legacy = SECTION_IMAGES_PERSONALITY
  const longKeys = Object.keys(legacy)
    .filter((k) => k.length >= 5)
    .sort((a, b) => b.length - a.length)
  for (const k of longKeys) {
    if (n.includes(k)) return legacy[k]
  }
  for (const k of Object.keys(legacy).sort((a, b) => b.length - a.length)) {
    if (n.includes(k)) return legacy[k]
  }
  return undefined
}

/** 是否为「性格优势与挑战」章节（用于专项样式）。 */
export function isPersonalityStrengthsSectionTitle(title: string): boolean {
  return normalizePersonalitySectionTitle(title) === '性格优势与挑战'
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
  const m = src.match(
    /\/section-(overview|personality|career|finance|health|growth|tone)\.(?:png|webp)(?:\?.*)?$/i,
  )
  if (!m) return src
  const theme = m[1].toLowerCase()
  if (!GENDERED_THEMES.has(theme)) return src
  const base = `/illustrations/sections/section-${theme}`
  if (g === 'female') return `${base}-female.webp`
  if (g === '') return `${base}-neutral.webp`
  return `${base}.webp`
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
  感情与人际: S('section-love.png'),
  财务与资源: S('section-finance.png'),
  健康与节奏: S('section-health.png'),
  月度提示: S('section-overview.png'),
  成长建议: S('section-growth.png'),
}

/** 年度运势七章正式标题（与 ReportGeneratingShell / 提示词一致）— 每章对应唯一底图。 */
export const ANNUAL_CANONICAL_TITLES = [
  '整体基调',
  '事业与学业',
  '感情与人际',
  '财务与资源',
  '健康与节奏',
  '月度提示',
  '成长建议',
] as const

export const ANNUAL_CANONICAL_IMAGES: Record<(typeof ANNUAL_CANONICAL_TITLES)[number], string> = {
  整体基调: S('section-tone.png'),
  事业与学业: S('section-career.png'),
  感情与人际: S('section-love.png'),
  财务与资源: S('section-finance.png'),
  健康与节奏: S('section-health.png'),
  月度提示: S('section-overview.png'),
  成长建议: S('section-growth.png'),
}

export function normalizeAnnualSectionTitle(title: string): string {
  let t = stripLeadingSectionIndex(title)
  t = t.replace(/\s+/g, ' ').trim()
  t = t.replace(/[（(][^）)]*[）)]\s*$/u, '').trim()
  return t
}

/** 年度运势：优先完全匹配七章标题，再前缀匹配，最后 legacy SECTION_IMAGES_ANNUAL。 */
export function resolveAnnualSectionImage(title: string): string | undefined {
  const n = normalizeAnnualSectionTitle(title)
  const canonical = ANNUAL_CANONICAL_IMAGES as Record<string, string>
  if (canonical[n]) return canonical[n]

  const ordered = [...ANNUAL_CANONICAL_TITLES].sort((a, b) => b.length - a.length)
  for (const k of ordered) {
    if (n.startsWith(k)) return canonical[k]
  }

  const legacy = SECTION_IMAGES_ANNUAL
  const longKeys = Object.keys(legacy)
    .filter((k) => k.length >= 5)
    .sort((a, b) => b.length - a.length)
  for (const k of longKeys) {
    if (n.includes(k)) return legacy[k]
  }
  for (const k of Object.keys(legacy).sort((a, b) => b.length - a.length)) {
    if (n.includes(k)) return legacy[k]
  }
  return undefined
}

/**
 * 个人性格报告 — 栏目与底图一一对应，禁止用「性格」等短词兜底到同一张图。
 * 匹配仍按最长 key 优先（resolveSectionImage）。
 */
export const SECTION_IMAGES_PERSONALITY: Record<string, string> = {
  成长建议与行动清单: S('section-health.png'),
  太阳星座与核心动机: S('section-personality.png'),
  太阳星座深度解读: S('section-personality.png'),
  性格优势与挑战: S('section-growth.png'),
  感情与亲密关系: S('section-love.png'),
  事业与财富节奏: S('section-career.png'),
  人际关系与社交: S('section-tone.png'),
  年度成长建议: S('section-overview.png'),
  专属行动清单: S('section-health.png'),
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
  沟通与相处模式: S('section-compat-secrets.png'),
  长期关系参考: S('section-compat-sweet.png'),
  冲突与修复建议: S('section-compat-friction.png'),
}

/** 配对分析报告六章正式标题 — 每章唯一底图（与 ReportGeneratingShell / 提示词一致）。 */
export const COMPATIBILITY_CANONICAL_TITLES = [
  '缘分指数',
  '你们的化学反应',
  '双人能量与节奏',
  '沟通与相处模式',
  '冲突与修复建议',
  '长期关系参考',
] as const

export const COMPATIBILITY_CANONICAL_IMAGES: Record<(typeof COMPATIBILITY_CANONICAL_TITLES)[number], string> = {
  缘分指数: S('section-compat-fate.png'),
  你们的化学反应: S('section-compat-chemistry.png'),
  双人能量与节奏: S('section-compat-overview.png'),
  沟通与相处模式: S('section-compat-secrets.png'),
  冲突与修复建议: S('section-compat-friction.png'),
  长期关系参考: S('section-compat-sweet.png'),
}

export function normalizeCompatibilitySectionTitle(title: string): string {
  let t = stripLeadingSectionIndex(title)
  t = t.replace(/\s+/g, ' ').trim()
  t = t.replace(/[（(][^）)]*[）)]\s*$/u, '').trim()
  return t
}

export function resolveCompatibilitySectionImage(title: string): string | undefined {
  const n = normalizeCompatibilitySectionTitle(title)
  const canonical = COMPATIBILITY_CANONICAL_IMAGES as Record<string, string>
  if (canonical[n]) return canonical[n]

  const ordered = [...COMPATIBILITY_CANONICAL_TITLES].sort((a, b) => b.length - a.length)
  for (const k of ordered) {
    if (n.startsWith(k)) return canonical[k]
  }

  const legacy = SECTION_IMAGES_COMPATIBILITY
  const longKeys = Object.keys(legacy)
    .filter((k) => k.length >= 5)
    .sort((a, b) => b.length - a.length)
  for (const k of longKeys) {
    if (n.includes(k)) return legacy[k]
  }
  for (const k of Object.keys(legacy).sort((a, b) => b.length - a.length)) {
    if (n.includes(k)) return legacy[k]
  }
  return undefined
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
