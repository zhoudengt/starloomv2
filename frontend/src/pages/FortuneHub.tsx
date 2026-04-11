import { motion } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchDailyAll, fetchSigns, prefetchDailyFortune } from '../api/constellation'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { usePrice } from '../hooks/usePrices'
import { ZODIAC_CARD_IMG, zodiacPictureSources } from '../utils/zodiacAssets'

export default function FortuneHub() {
  const pricePersonality = usePrice('personality')
  const queryClient = useQueryClient()
  const { data: signsData } = useQuery({ queryKey: ['signs'], queryFn: fetchSigns })
  const { data: dailyAll } = useQuery({ queryKey: ['dailyAll'], queryFn: fetchDailyAll })
  const scoreMap = new Map(dailyAll?.items.map((i) => [i.sign, i.overall_score]) ?? [])

  return (
    <>
      <StarryBackground />
      <div className="flex items-center gap-4">
        <img
          src="/illustrations/season-moon.png"
          alt=""
          className="h-16 w-16 shrink-0 rounded-2xl object-cover opacity-95"
        />
        <div>
          <h1 className="font-serif text-2xl font-medium tracking-tight text-[var(--color-text-primary)]">
            今日十二星座
          </h1>
          <p className="mt-1 text-xs text-[var(--color-text-secondary)]">左右滑动查看，点进详情</p>
        </div>
      </div>
      <div className="mt-6 flex gap-3 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {(signsData?.signs ?? []).map((s, i) => {
          const { webp, png } = zodiacPictureSources(s.sign)
          return (
          <motion.div
            key={s.sign}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.03 }}
            className="min-w-[104px] shrink-0"
          >
            <Link
              to={`/daily/${s.sign}`}
              onMouseEnter={() => void prefetchDailyFortune(queryClient, s.sign)}
              onFocus={() => void prefetchDailyFortune(queryClient, s.sign)}
              className="card-elevated flex flex-col items-center rounded-2xl px-3 py-4 text-center transition-transform active:scale-95"
            >
              <div className="relative flex flex-col items-center">
                <picture className="block h-14 w-14 shrink-0 overflow-hidden rounded-2xl shadow-[0_8px_24px_rgba(0,0,0,0.35)]">
                  <source srcSet={webp} type="image/webp" />
                  <img
                    src={png}
                    alt=""
                    width={ZODIAC_CARD_IMG.width}
                    height={ZODIAC_CARD_IMG.height}
                    sizes="56px"
                    loading={i < 4 ? 'eager' : 'lazy'}
                    {...(i < 4 ? { fetchPriority: 'high' as const } : {})}
                    decoding="async"
                    className="h-full w-full object-cover"
                  />
                </picture>
                <span className="mt-1 block font-serif text-sm text-[var(--color-brand-gold)]">{s.symbol}</span>
              </div>
              <span className="mt-1 text-sm text-[var(--color-text-primary)]">{s.sign_cn}</span>
              {scoreMap.has(s.sign) && (
                <span className="mt-2 rounded-full bg-[var(--color-brand-gold)]/18 px-2 py-0.5 font-mono text-xs text-[var(--color-brand-gold)]">
                  {scoreMap.get(s.sign)}
                </span>
              )}
            </Link>
          </motion.div>
          )
        })}
      </div>
      <div className="mt-10 space-y-3">
        <Link
          to="/quicktest"
          className="btn-glow relative flex w-full items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-semibold"
        >
          <Icon name="sparkle" size={18} className="relative z-[1] text-[#0a0b14]" />
          <span className="relative z-[1] text-[#0a0b14]">免费星座解读 · 生成你的星盘名片</span>
        </Link>
        <Link
          to="/payment?product=personality"
          className="flex w-full items-center justify-center gap-1 rounded-2xl border border-white/[0.1] py-3 text-xs text-[var(--color-text-secondary)] transition-colors active:bg-white/[0.04]"
        >
          直接解锁完整性格报告 ¥{pricePersonality}
          <Icon name="chevronRight" size={14} />
        </Link>
      </div>
    </>
  )
}
