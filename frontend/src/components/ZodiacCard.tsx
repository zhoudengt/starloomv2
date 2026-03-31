import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'

type Props = {
  sign: string
  signCn: string
  symbol: string
  score?: number
}

export function ZodiacCard({ sign, signCn, symbol, score }: Props) {
  return (
    <motion.div whileTap={{ scale: 0.97 }} className="h-full">
      <Link
        to={`/daily/${sign}`}
        className="block h-full rounded-2xl border border-[#f0c75e]/25 bg-[#2d1b69]/40 p-3 text-center shadow-lg backdrop-blur-sm"
      >
        <div className="font-serif text-2xl text-[var(--color-starloom-gold)]">{symbol}</div>
        <div className="mt-1 text-sm font-medium text-violet-100">{signCn}</div>
        {score != null && (
          <div className="mt-2 text-xs text-[var(--color-starloom-gold)]">{score} 分</div>
        )}
      </Link>
    </motion.div>
  )
}
