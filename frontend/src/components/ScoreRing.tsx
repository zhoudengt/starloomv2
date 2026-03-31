import { motion } from 'framer-motion'

type Props = { score: number; label?: string }

export function ScoreRing({ score, label = '综合运势' }: Props) {
  const pct = Math.min(100, Math.max(0, score))
  const circumference = 2 * Math.PI * 42
  const offset = circumference - (pct / 100) * circumference
  return (
    <div className="flex flex-col items-center">
      <div className="relative h-40 w-40">
        <svg className="-rotate-90 transform" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="42" stroke="rgba(240,199,94,0.15)" strokeWidth="8" fill="none" />
          <motion.circle
            cx="50"
            cy="50"
            r="42"
            stroke="var(--color-starloom-gold)"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-serif text-3xl font-bold text-[var(--color-starloom-gold)]">{score}</span>
          <span className="text-xs text-violet-200/80">/100</span>
        </div>
      </div>
      <p className="mt-4 font-serif text-lg text-violet-100">{label}</p>
    </div>
  )
}
