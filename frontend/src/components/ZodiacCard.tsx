import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { prefetchDailyFortune } from '../api/constellation'
import { elementFromSign, type ZodiacElement } from '../utils/zodiacCalc'

type Props = {
  sign: string
  signCn: string
  symbol: string
  score?: number
  index?: number
}

const ELEMENT_BAR: Record<
  ZodiacElement,
  { bg: string; glow: string; ring: string }
> = {
  fire: {
    bg: 'bg-gradient-to-b from-[#fff0e6] to-[#ffe0cc]',
    glow: 'shadow-[0_4px_18px_rgba(255,107,74,0.22)]',
    ring: 'stroke-[#ff6b4a]',
  },
  earth: {
    bg: 'bg-gradient-to-b from-[#e6fff2] to-[#ccffe6]',
    glow: 'shadow-[0_4px_18px_rgba(52,211,153,0.2)]',
    ring: 'stroke-[#34d399]',
  },
  air: {
    bg: 'bg-gradient-to-b from-[#e6f4ff] to-[#d9ecff]',
    glow: 'shadow-[0_4px_18px_rgba(56,189,248,0.2)]',
    ring: 'stroke-[#38bdf8]',
  },
  water: {
    bg: 'bg-gradient-to-b from-[#f0e6ff] to-[#e6d9ff]',
    glow: 'shadow-[0_4px_18px_rgba(139,92,246,0.22)]',
    ring: 'stroke-[#a78bfa]',
  },
}

function zodiacImageSrc(sign: string) {
  return `/zodiac/${sign.toLowerCase()}.png`
}

export function ZodiacCard({ sign, signCn, symbol: _symbol, score, index = 0 }: Props) {
  const queryClient = useQueryClient()
  const warmDailyDetail = () => {
    void prefetchDailyFortune(queryClient, sign)
  }
  const el = elementFromSign(sign)
  const e = ELEMENT_BAR[el]
  const pct = score != null ? Math.min(100, Math.max(0, score)) : null
  const r = 16
  const c = 2 * Math.PI * r
  const offset = pct != null ? c - (pct / 100) * c : c

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-20px' }}
      transition={{ delay: index * 0.04, duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      whileTap={{ scale: 0.97 }}
      className="h-full"
    >
      <Link
        to={`/daily/${sign}`}
        onMouseEnter={warmDailyDetail}
        onFocus={warmDailyDetail}
        className={`group relative flex min-h-[152px] flex-col overflow-hidden rounded-2xl border border-white/60 text-center transition-all active:scale-[0.99] active:border-white/80 ${e.bg} ${e.glow}`}
      >
        {/* Character art — edge-to-edge, no dead space */}
        <div className="relative h-[104px] w-full shrink-0 overflow-hidden rounded-t-2xl">
          <img
            src={zodiacImageSrc(sign)}
            alt={`${signCn}角色`}
            className="h-full w-full object-cover object-center transition-transform duration-300 group-hover:scale-[1.03]"
            loading="lazy"
            decoding="async"
          />
        </div>

        <div className="relative z-[2] flex min-h-0 flex-1 flex-col justify-center px-1.5 pb-1.5 pt-1">
          <p className="text-[13px] font-bold leading-tight text-[#1a1a2e]">{signCn}</p>
          {pct != null && (
            <div className="mt-1 flex items-center justify-center gap-1">
              <svg width="32" height="32" viewBox="0 0 44 44" className="-rotate-90 shrink-0 scale-[0.75]">
                <circle
                  cx="22"
                  cy="22"
                  r={r}
                  fill="none"
                  stroke="rgba(0,0,0,0.1)"
                  strokeWidth="4"
                />
                <circle
                  cx="22"
                  cy="22"
                  r={r}
                  fill="none"
                  className={e.ring}
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={c}
                  strokeDashoffset={offset}
                />
              </svg>
              <div className="text-left">
                <p className="font-mono text-[13px] font-bold leading-none text-[#1a1a2e]">{pct}</p>
                <p className="text-[7px] leading-tight text-[#5c5c6e]">今日指数</p>
              </div>
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  )
}
