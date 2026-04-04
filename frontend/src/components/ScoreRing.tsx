import { motion } from 'framer-motion'

type Props = { score: number; label?: string; size?: 'md' | 'lg' }

export function ScoreRing({ score, label = '综合运势', size = 'md' }: Props) {
  const pct = Math.min(100, Math.max(0, score))
  const isLg = size === 'lg'
  const r = isLg ? 44 : 42
  const circumference = 2 * Math.PI * r
  const offset = circumference - (pct / 100) * circumference
  const dim = isLg ? 'h-52 w-52' : 'h-40 w-40'
  const sw = isLg ? 9 : 8
  const scoreCls = isLg ? 'font-serif text-4xl font-bold' : 'font-serif text-3xl font-bold'

  return (
    <div className="flex flex-col items-center">
      <div className={`relative ${dim}`}>
        <svg className="-rotate-90 transform" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={r} stroke="rgba(240,199,94,0.15)" strokeWidth={sw} fill="none" />
          <motion.circle
            cx="50"
            cy="50"
            r={r}
            stroke="var(--color-starloom-gold)"
            strokeWidth={sw}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`${scoreCls} text-[var(--color-starloom-gold)]`}>{score}</span>
          <span className="text-xs text-[var(--color-text-secondary)]/80">/100</span>
        </div>
      </div>
      <p className="mt-4 font-serif text-lg text-[var(--color-text-primary)]">{label}</p>
    </div>
  )
}
