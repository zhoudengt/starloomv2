/** 与 `public/zodiac/*` 当前导出尺寸一致（约 2× @105px 宽） */
export const ZODIAC_CARD_IMG = { width: 420, height: 234 } as const

export function zodiacPictureSources(sign: string) {
  const slug = sign.toLowerCase()
  return {
    webp: `/zodiac/${slug}.webp`,
    png: `/zodiac/${slug}.png`,
  }
}
