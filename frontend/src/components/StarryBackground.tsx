import { motion } from 'framer-motion'

export function StarryBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_#4c3d8a_0%,_#1a0f3d_50%,_#0a0518_100%)]" />
      {[...Array(24)].map((_, i) => (
        <motion.span
          key={i}
          className="absolute h-0.5 w-0.5 rounded-full bg-white/70"
          style={{
            left: `${(i * 37) % 100}%`,
            top: `${(i * 53) % 100}%`,
          }}
          animate={{ opacity: [0.2, 1, 0.2] }}
          transition={{ duration: 2 + (i % 5), repeat: Infinity, delay: i * 0.1 }}
        />
      ))}
    </div>
  )
}
