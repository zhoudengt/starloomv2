import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useGuidePreview, type GuidePreviewItem } from '../api/guide'
import { useBirthProfileStore } from '../stores/birthProfileStore'
import { sunSignFromDate, ZODIAC_CN, ZODIAC_ORDER, type ZodiacSlug } from '../utils/zodiacCalc'
import { Icon, type IconName } from './icons/Icon'

type CategoryStyle = {
  key: string
  icon: IconName
  image: string
  gradient: string
  borderColor: string
  glowColor: string
}

const CATEGORY_STYLES: Record<string, CategoryStyle> = {
  career: {
    key: 'career',
    icon: 'briefcase',
    image: '/illustrations/guide-career.webp',
    gradient: 'from-[#3b82f6]/20 to-[#1e3a5f]/30',
    borderColor: 'border-[#3b82f6]/25',
    glowColor: 'shadow-[0_0_20px_rgba(59,130,246,0.1)]',
  },
  wealth: {
    key: 'wealth',
    icon: 'coin',
    image: '/illustrations/guide-wealth.webp',
    gradient: 'from-[#f59e0b]/20 to-[#78350f]/30',
    borderColor: 'border-[#f59e0b]/25',
    glowColor: 'shadow-[0_0_20px_rgba(245,158,11,0.1)]',
  },
  relationship: {
    key: 'relationship',
    icon: 'users',
    image: '/illustrations/guide-relationship.webp',
    gradient: 'from-[#ec4899]/20 to-[#831843]/30',
    borderColor: 'border-[#ec4899]/25',
    glowColor: 'shadow-[0_0_20px_rgba(236,72,153,0.1)]',
  },
  energy: {
    key: 'energy',
    icon: 'moon',
    image: '/illustrations/guide-energy.webp',
    gradient: 'from-[#a78bfa]/20 to-[#4c1d95]/30',
    borderColor: 'border-[#a78bfa]/25',
    glowColor: 'shadow-[0_0_20px_rgba(167,139,250,0.1)]',
  },
}

const CATEGORY_ORDER = ['career', 'wealth', 'relationship', 'energy']

function SignPicker({ onSelect }: { onSelect: (slug: ZodiacSlug) => void }) {
  return (
    <div className="rounded-xl border border-[var(--color-brand-gold)]/20 bg-gradient-to-b from-[var(--color-brand-gold)]/[0.06] to-transparent p-5">
      <p className="mb-1 font-serif text-base text-[var(--color-text-primary)]">
        选择你的星座
      </p>
      <p className="mb-4 text-[11px] text-[var(--color-text-muted)]">
        解锁今日专属深度分析
      </p>
      <div className="grid grid-cols-4 gap-2">
        {ZODIAC_ORDER.map((slug) => (
          <button
            key={slug}
            type="button"
            onClick={() => onSelect(slug)}
            className="flex flex-col items-center gap-1 rounded-lg border border-white/[0.06] bg-white/[0.03] py-2.5 text-center transition-all active:scale-95 active:bg-white/[0.08]"
          >
            <img
              src={`/zodiac/${slug}.webp`}
              alt=""
              className="h-7 w-7 object-contain"
              loading="lazy"
            />
            <span className="text-[10px] text-[var(--color-text-secondary)]">
              {ZODIAC_CN[slug]}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

function GuideCard({ item, style, hasAccess }: {
  item: GuidePreviewItem
  style: CategoryStyle
  hasAccess: boolean
}) {
  return (
    <Link
      to={`/guide/${item.category}`}
      className={`group relative block overflow-hidden rounded-xl border ${style.borderColor} bg-gradient-to-br ${style.gradient} ${style.glowColor} p-4 backdrop-blur-sm transition-transform active:scale-[0.97]`}
    >
      {style.image && (
        <div
          className="pointer-events-none absolute inset-y-0 right-0 w-[48%] overflow-hidden rounded-r-[inherit]"
          aria-hidden
        >
          <div className="absolute inset-0 bg-gradient-to-l from-transparent via-[#0a0b14]/20 to-[#0a0b14]/70" />
          <img
            src={style.image}
            alt=""
            className="h-full w-full object-cover object-right opacity-80 transition-opacity group-hover:opacity-95"
            loading="lazy"
          />
        </div>
      )}

      <div className="relative z-[1]">
        <div className="mb-2.5 flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.08]">
            <Icon name={style.icon} size={16} className="text-white/80" />
          </span>
          <h3 className="text-sm font-bold text-white/90">{item.label}</h3>
          {hasAccess ? (
            <span className="ml-auto rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-medium text-emerald-400">
              已解锁
            </span>
          ) : (
            <span className="ml-auto rounded-full bg-[var(--color-brand-gold)]/15 px-1.5 py-0.5 text-[9px] font-medium text-[var(--color-brand-gold)]">
              ¥0.4
            </span>
          )}
        </div>

        <p className="mb-3 line-clamp-2 text-xs leading-relaxed text-white/65">
          {item.preview}
        </p>

        {item.transit_basis && (
          <p className="mb-2.5 text-[10px] text-white/40">
            基于：{item.transit_basis}
          </p>
        )}

        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--color-brand-cyan)]">
          {hasAccess ? '查看详情' : '查看深析'}
          <Icon name="chevronRight" size={11} className="inline" />
        </span>
      </div>
    </Link>
  )
}

export function PracticalGuideSection() {
  const birthDate = useBirthProfileStore((s) => s.birthDate)
  const setBirthDate = useBirthProfileStore((s) => s.setBirthDate)

  const sign = useMemo(() => {
    if (!birthDate) return undefined
    try {
      return sunSignFromDate(birthDate)
    } catch {
      return undefined
    }
  }, [birthDate])

  const signCn = sign ? ZODIAC_CN[sign] : ''
  const { data } = useGuidePreview(sign)

  const [showPicker, setShowPicker] = useState(false)

  const handlePickSign = (slug: ZodiacSlug) => {
    const ranges: Record<string, string> = {
      aries: '1995-04-01', taurus: '1995-05-01', gemini: '1995-06-01',
      cancer: '1995-07-01', leo: '1995-08-01', virgo: '1995-09-01',
      libra: '1995-10-01', scorpio: '1995-11-01', sagittarius: '1995-12-01',
      capricorn: '1995-01-01', aquarius: '1995-02-01', pisces: '1995-03-01',
    }
    setBirthDate(ranges[slug] ?? '1995-06-15')
    setShowPicker(false)
  }

  const itemMap = useMemo(() => {
    const m = new Map<string, GuidePreviewItem>()
    if (data?.items) {
      for (const it of data.items) {
        m.set(it.category, it)
      }
    }
    return m
  }, [data])

  const hasAccess = data?.has_access ?? false

  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <h2 className="bg-gradient-to-r from-[#00e5ff] via-[#a78bfa] to-[#f472b6] bg-clip-text font-serif text-lg font-semibold tracking-tight text-transparent">
          每日星运深析
        </h2>
        <span className="rounded-full bg-[#00e5ff]/10 px-2 py-0.5 text-[10px] font-medium text-[#00e5ff]/80">
          ¥0.4/天
        </span>
      </div>
      <p className="mb-4 text-[11px] leading-relaxed text-[var(--color-text-tertiary)]">
        {sign
          ? `${signCn} · 基于当日天象的 4 维深度分析`
          : '选择你的星座，获取专属深度分析'}
      </p>

      {!sign || showPicker ? (
        <SignPicker onSelect={handlePickSign} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            {CATEGORY_ORDER.map((catKey) => {
              const style = CATEGORY_STYLES[catKey]
              const item = itemMap.get(catKey)
              if (!style) return null
              const fallbackItem: GuidePreviewItem = {
                category: catKey,
                label: style.key === 'career' ? '职场星运'
                  : style.key === 'wealth' ? '财富密码'
                  : style.key === 'relationship' ? '人际沟通'
                  : '情绪能量',
                icon: style.icon,
                title: '',
                preview: '内容生成中，请稍后刷新…',
                transit_basis: null,
              }
              return (
                <GuideCard
                  key={catKey}
                  item={item ?? fallbackItem}
                  style={style}
                  hasAccess={hasAccess}
                />
              )
            })}
          </div>
          <button
            type="button"
            onClick={() => setShowPicker(true)}
            className="mt-4 w-full rounded-xl border border-[var(--color-brand-cyan)]/35 bg-[var(--color-brand-cyan)]/[0.06] py-2.5 text-center text-sm font-semibold text-[var(--color-brand-cyan)] shadow-[0_0_20px_rgba(0,229,255,0.12)] transition-colors active:bg-[var(--color-brand-cyan)]/15 active:text-[#baf3ff]"
          >
            切换星座
          </button>
        </>
      )}
    </div>
  )
}
