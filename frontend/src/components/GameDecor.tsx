import { motion } from 'framer-motion'

/** Lively cosmic background — warm indigo base with vibrant color pops */
export function GameDecor() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* Base: warm indigo-to-deep-blue, less black, more color */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'linear-gradient(160deg, #1a1040 0%, #0e1a3a 40%, #0c1228 100%)',
        }}
      />

      {/* Warm aurora wash — top area */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 120% 55% at 50% 0%, rgba(168, 85, 247, 0.22) 0%, transparent 60%), radial-gradient(ellipse 80% 50% at 85% 15%, rgba(244, 114, 182, 0.15) 0%, transparent 50%), radial-gradient(ellipse 70% 45% at 15% 20%, rgba(56, 189, 248, 0.12) 0%, transparent 50%)',
        }}
      />

      {/* Bottom warm glow */}
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse 90% 40% at 50% 100%, rgba(251, 191, 36, 0.08) 0%, transparent 50%)',
        }}
      />

      {/* Floating pastel blobs — lively and warm */}
      <motion.div
        className="absolute -left-6 top-[8%] h-44 w-44 rounded-full bg-[#a78bfa]/20 blur-[70px]"
        animate={{ x: [0, 18, 0], y: [0, -10, 0] }}
        transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute right-[-5%] top-[28%] h-52 w-52 rounded-full bg-[#f472b6]/15 blur-[80px]"
        animate={{ x: [0, -14, 0], y: [0, 18, 0] }}
        transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute bottom-[12%] left-[15%] h-40 w-40 rounded-full bg-[#38bdf8]/12 blur-[60px]"
        animate={{ scale: [1, 1.12, 1], opacity: [0.6, 1, 0.6] }}
        transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute bottom-[30%] right-[10%] h-32 w-32 rounded-full bg-[#fbbf24]/10 blur-[50px]"
        animate={{ x: [0, 10, 0], y: [0, -12, 0] }}
        transition={{ duration: 14, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Playful shapes — circles + soft rings */}
      <motion.div
        className="absolute left-[7%] top-[6%] h-20 w-20 rounded-full border border-[#c084fc]/25"
        animate={{ scale: [1, 1.06, 1] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        aria-hidden
      />
      <div
        className="absolute right-[10%] top-[14%] h-14 w-14 rounded-full border border-[#f9a8d4]/20"
        aria-hidden
      />
      <motion.div
        className="absolute bottom-[20%] left-[12%] h-10 w-10 rounded-full bg-[#fbbf24]/20 blur-[2px]"
        animate={{ opacity: [0.3, 0.7, 0.3] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
        aria-hidden
      />
      <div
        className="absolute bottom-[35%] right-[20%] h-6 w-6 rotate-45 rounded-sm border border-[#67e8f9]/20"
        aria-hidden
      />

      {/* Sparkle particles — colorful and warm */}
      {[...Array(24)].map((_, i) => {
        const colors = [
          'rgba(251,191,36,0.8)',
          'rgba(168,85,247,0.65)',
          'rgba(244,114,182,0.7)',
          'rgba(56,189,248,0.6)',
          'rgba(255,255,255,0.55)',
          'rgba(52,211,153,0.6)',
        ]
        const c = colors[i % colors.length]!
        const size = i % 7 === 0 ? 3.5 : i % 5 === 0 ? 2.5 : 1.8
        return (
          <motion.span
            key={i}
            className="absolute rounded-full"
            style={{
              width: size,
              height: size,
              left: `${(i * 41 + 8) % 98}%`,
              top: `${(i * 59 + 5) % 96}%`,
              background: c,
              boxShadow: `0 0 ${3 + (i % 4)}px ${c}`,
            }}
            animate={{ opacity: [0.1, 0.8, 0.1], scale: [0.8, 1.15, 0.8] }}
            transition={{ duration: 3 + (i % 6) * 0.4, repeat: Infinity, delay: i * 0.08 }}
          />
        )
      })}
    </div>
  )
}
