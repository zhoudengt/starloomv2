import { motion } from 'framer-motion'

export default function LoadingAnalysis({ message = '正在解读你的星盘…' }: { message?: string }) {
  return (
    <div className="flex min-h-[55vh] flex-col items-center justify-center gap-8 px-4">
      <div className="relative h-36 w-36">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <motion.span
            key={i}
            className="absolute left-1/2 top-1/2 h-2.5 w-2.5 rounded-full bg-[var(--color-brand-gold)] shadow-[var(--shadow-glow-gold)]"
            style={{ marginLeft: -5, marginTop: -5 }}
            animate={{
              x: Math.cos((i / 6) * Math.PI * 2) * 48,
              y: Math.sin((i / 6) * Math.PI * 2) * 48,
              opacity: [0.25, 1, 0.25],
              scale: [0.75, 1.15, 0.75],
            }}
            transition={{
              duration: 2.4,
              repeat: Infinity,
              delay: i * 0.12,
              ease: 'easeInOut',
            }}
          />
        ))}
        <motion.div
          className="absolute inset-2 rounded-full border-2 border-[var(--color-brand-gold)]/35"
          animate={{ scale: [1, 1.12, 1], opacity: [0.55, 0.15, 0.55] }}
          transition={{ duration: 2.8, repeat: Infinity }}
        />
        <motion.div
          className="absolute inset-6 rounded-full border border-[var(--color-brand-violet)]/25"
          animate={{ scale: [1.05, 1, 1.05], opacity: [0.2, 0.45, 0.2] }}
          transition={{ duration: 3.2, repeat: Infinity }}
        />
      </div>
      <div className="text-center">
        <p className="font-serif text-base text-[var(--color-brand-gold)]">{message}</p>
        <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">AI 正在连接星象数据…</p>
      </div>
    </div>
  )
}
