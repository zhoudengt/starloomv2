import type { SVGProps } from 'react'

export type IconName =
  | 'home'
  | 'fortune'
  | 'reports'
  | 'profile'
  | 'share'
  | 'lock'
  | 'chevronRight'
  | 'calendar'
  | 'sparkle'
  | 'send'
  | 'female'
  | 'male'
  | 'heart'
  | 'briefcase'
  | 'coin'
  | 'leaf'

const ZODIAC_GLYPH: Record<string, string> = {
  aries: '♈',
  taurus: '♉',
  gemini: '♊',
  cancer: '♋',
  leo: '♌',
  virgo: '♍',
  libra: '♎',
  scorpio: '♏',
  sagittarius: '♐',
  capricorn: '♑',
  aquarius: '♒',
  pisces: '♓',
}

type Props = SVGProps<SVGSVGElement> & {
  name: IconName | `zodiac:${string}`
  size?: number
}

export function Icon({ name, size = 22, className = '', ...rest }: Props) {
  const s = size
  if (name.startsWith('zodiac:')) {
    const key = name.slice('zodiac:'.length).toLowerCase()
    const g = ZODIAC_GLYPH[key] ?? '✦'
    return (
      <svg
        width={s}
        height={s}
        viewBox="0 0 24 24"
        className={className}
        aria-hidden
        {...rest}
      >
        <text
          x="12"
          y="16"
          textAnchor="middle"
          className="fill-[var(--color-brand-gold)]"
          style={{ fontSize: s * 0.72, fontFamily: 'serif' }}
        >
          {g}
        </text>
      </svg>
    )
  }

  const stroke = 'currentColor'
  const sw = 1.65
  const common = { stroke, strokeWidth: sw, fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }

  switch (name) {
    case 'home':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path d="M4 10.5 12 4l8 6.5" {...common} />
          <path d="M6 10v10h12V10" {...common} />
          <path d="M10 20v-6h4v6" {...common} />
        </svg>
      )
    case 'fortune':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path
            d="M12 3a6.5 6.5 0 0 1 0 13c-2.5 0-4.5-1.2-5.8-3"
            {...common}
          />
          <path d="M12 16v5M9 21h6" {...common} />
        </svg>
      )
    case 'reports':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path d="M7 3h10a2 2 0 0 1 2 2v16l-4-2-4 2-4-2-4 2V5a2 2 0 0 1 2-2z" {...common} />
          <path d="M9 8h6M9 12h6M9 16h4" {...common} strokeWidth={1.2} />
        </svg>
      )
    case 'profile':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <circle cx="12" cy="9" r="4" {...common} />
          <path d="M5 20.5c1.5-4 5-5.5 7-5.5s5.5 1.5 7 5.5" {...common} />
        </svg>
      )
    case 'share':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <circle cx="18" cy="5" r="2.5" {...common} />
          <circle cx="6" cy="12" r="2.5" {...common} />
          <circle cx="18" cy="19" r="2.5" {...common} />
          <path d="m7.5 10.5 7-3.5M14.5 17 7.5 13.5" {...common} />
        </svg>
      )
    case 'lock':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <rect x="5" y="11" width="14" height="10" rx="2" {...common} />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" {...common} />
        </svg>
      )
    case 'chevronRight':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path d="m9 6 6 6-6 6" {...common} />
        </svg>
      )
    case 'calendar':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <rect x="4" y="5" width="16" height="16" rx="2" {...common} />
          <path d="M8 3v4M16 3v4M4 11h16" {...common} />
        </svg>
      )
    case 'sparkle':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" {...common} />
          <circle cx="12" cy="12" r="3" {...common} />
        </svg>
      )
    case 'send':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" {...common} />
        </svg>
      )
    case 'female':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <circle cx="12" cy="9" r="4" {...common} />
          <path d="M12 13v8M9 18h6" {...common} />
        </svg>
      )
    case 'male':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <circle cx="10" cy="14" r="4" {...common} />
          <path d="m14 10 6-6M14 4h6v6" {...common} />
        </svg>
      )
    case 'heart':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path
            d="M12 21s-7-4.35-7-10a5 5 0 0 1 9.09-2.91A5 5 0 0 1 19 11c0 5.65-7 10-7 10z"
            {...common}
          />
        </svg>
      )
    case 'briefcase':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <rect x="4" y="8" width="16" height="12" rx="2" {...common} />
          <path d="M8 8V6a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" {...common} />
        </svg>
      )
    case 'coin':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <circle cx="12" cy="12" r="8" {...common} />
          <path d="M12 8v8M9.5 10.5h5M9.5 13.5h5" {...common} strokeWidth={1.2} />
        </svg>
      )
    case 'leaf':
      return (
        <svg width={s} height={s} viewBox="0 0 24 24" className={className} aria-hidden {...rest}>
          <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 6.5 1 8.5a7 7 0 0 1-9 9.5z" {...common} />
        </svg>
      )
    default:
      return null
  }
}
