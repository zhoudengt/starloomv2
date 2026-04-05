/** Western sun sign from YYYY-MM-DD (approximate, standard date ranges). */

export const ZODIAC_ORDER = [
  'aries',
  'taurus',
  'gemini',
  'cancer',
  'leo',
  'virgo',
  'libra',
  'scorpio',
  'sagittarius',
  'capricorn',
  'aquarius',
  'pisces',
] as const

export type ZodiacSlug = (typeof ZODIAC_ORDER)[number]

/** Western zodiac classical element — for UI theming */
export type ZodiacElement = 'fire' | 'earth' | 'air' | 'water'

/** Safe for missing/invalid API `sign` strings — avoids runtime throw */
export function elementFromSignSafe(sign: string | undefined | null): ZodiacElement {
  if (sign == null) return 'fire'
  const t = String(sign).trim()
  if (t === '') return 'fire'
  return elementFromSign(t)
}

export function elementFromSign(sign: string): ZodiacElement {
  const s = sign.toLowerCase() as ZodiacSlug
  const fire: ZodiacSlug[] = ['aries', 'leo', 'sagittarius']
  const earth: ZodiacSlug[] = ['taurus', 'virgo', 'capricorn']
  const air: ZodiacSlug[] = ['gemini', 'libra', 'aquarius']
  if (fire.includes(s)) return 'fire'
  if (earth.includes(s)) return 'earth'
  if (air.includes(s)) return 'air'
  return 'water'
}

export const ZODIAC_CN: Record<ZodiacSlug, string> = {
  aries: '白羊座',
  taurus: '金牛座',
  gemini: '双子座',
  cancer: '巨蟹座',
  leo: '狮子座',
  virgo: '处女座',
  libra: '天秤座',
  scorpio: '天蝎座',
  sagittarius: '射手座',
  capricorn: '摩羯座',
  aquarius: '水瓶座',
  pisces: '双鱼座',
}

/** Returns sun sign slug from ISO date string YYYY-MM-DD */
export function sunSignFromDate(isoDate: string): ZodiacSlug {
  const [, m, d] = isoDate.split('-').map(Number)
  const month = m
  const day = d
  if (!month || !day) return 'aries'

  if ((month === 3 && day >= 21) || (month === 4 && day <= 19)) return 'aries'
  if ((month === 4 && day >= 20) || (month === 5 && day <= 20)) return 'taurus'
  if ((month === 5 && day >= 21) || (month === 6 && day <= 20)) return 'gemini'
  if ((month === 6 && day >= 21) || (month === 7 && day <= 22)) return 'cancer'
  if ((month === 7 && day >= 23) || (month === 8 && day <= 22)) return 'leo'
  if ((month === 8 && day >= 23) || (month === 9 && day <= 22)) return 'virgo'
  if ((month === 9 && day >= 23) || (month === 10 && day <= 22)) return 'libra'
  if ((month === 10 && day >= 23) || (month === 11 && day <= 21)) return 'scorpio'
  if ((month === 11 && day >= 22) || (month === 12 && day <= 21)) return 'sagittarius'
  if ((month === 12 && day >= 22) || (month === 1 && day <= 19)) return 'capricorn'
  if ((month === 1 && day >= 20) || (month === 2 && day <= 18)) return 'aquarius'
  return 'pisces'
}

function sunIndex(isoDate: string): number {
  const s = sunSignFromDate(isoDate)
  return ZODIAC_ORDER.indexOf(s)
}

/**
 * Decorative moon / rising from date + optional HH:mm.
 * Not astronomical — deterministic “chart feel” for UX.
 */
export function deriveMoonAndRising(
  isoDate: string,
  birthTime?: string | null,
): { moon: ZodiacSlug; rising: ZodiacSlug } {
  const sun = sunIndex(isoDate)
  const [ys, ms, ds] = isoDate.split('-').map(Number)
  const dayOfYear = simpleDayOfYear(ys, ms, ds)
  const moonOffset = (dayOfYear + (ms ?? 1) * 3 + (ds ?? 1)) % 12
  const moon = ZODIAC_ORDER[(sun + moonOffset + 4) % 12]!

  let hour = 12
  if (birthTime && /^\d{1,2}:\d{2}/.test(birthTime)) {
    const [h] = birthTime.split(':').map(Number)
    if (Number.isFinite(h)) hour = Math.min(23, Math.max(0, h))
  }
  const rising = ZODIAC_ORDER[(sun + Math.floor(hour / 2) + Math.floor(dayOfYear / 30)) % 12]!

  return { moon, rising }
}

function simpleDayOfYear(y: number, m: number, d: number): number {
  const start = new Date(y, 0, 0).getTime()
  const cur = new Date(y, m - 1, d).getTime()
  return Math.floor((cur - start) / 86400000)
}

export function placementsFromBirth(isoDate: string, birthTime?: string | null) {
  const sun = sunSignFromDate(isoDate)
  const { moon, rising } = deriveMoonAndRising(isoDate, birthTime)
  return {
    sun,
    moon,
    rising,
    sunCn: ZODIAC_CN[sun],
    moonCn: ZODIAC_CN[moon],
    risingCn: ZODIAC_CN[rising],
  }
}

/** Chinese zodiac (生肖) year animal — Gregorian year, cycle anchored at 1900 = 鼠 */
export const CHINESE_ZODIAC_ORDER = [
  'rat',
  'ox',
  'tiger',
  'rabbit',
  'dragon',
  'snake',
  'horse',
  'goat',
  'monkey',
  'rooster',
  'dog',
  'pig',
] as const

export type ChineseZodiacAnimal = (typeof CHINESE_ZODIAC_ORDER)[number]

export const CHINESE_ZODIAC_CN: Record<ChineseZodiacAnimal, string> = {
  rat: '鼠',
  ox: '牛',
  tiger: '虎',
  rabbit: '兔',
  dragon: '龙',
  snake: '蛇',
  horse: '马',
  goat: '羊',
  monkey: '猴',
  rooster: '鸡',
  dog: '狗',
  pig: '猪',
}

/** Solar year → zodiac animal (e.g. 2026 → horse). */
export function chineseZodiacFromYear(year: number): ChineseZodiacAnimal {
  const y = Math.trunc(year)
  const idx = ((y - 4) % 12 + 12) % 12
  return CHINESE_ZODIAC_ORDER[idx]!
}

/** Annual report UI: only current Gregorian year and the next year. */
export function clampAnnualYear(year: number): number {
  const cy = new Date().getFullYear()
  const y = Math.trunc(year)
  if (!Number.isFinite(y)) return cy
  return Math.min(Math.max(y, cy), cy + 1)
}

export function allowedAnnualYears(): [number, number] {
  const cy = new Date().getFullYear()
  return [cy, cy + 1]
}

export { triadInsightBlurb } from './triadInsightCopy'
