import { useEffect, useState } from 'react'

/** Animated social proof — game-style pill badge */
export function AnimatedUserCount({ target = 12483 }: { target?: number }) {
  const [n, setN] = useState(11820)

  useEffect(() => {
    const from = 11820
    const duration = 2000
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - (1 - t) ** 3
      setN(Math.round(from + (target - from) * eased))
      if (t < 1) requestAnimationFrame(tick)
    }
    const id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [target])

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[#ffd700]/35 bg-gradient-to-r from-[#8b5cf6]/20 via-[#ff2d78]/15 to-[#ffd700]/20 px-3 py-1 font-mono text-sm font-bold tabular-nums text-[#ffd700] shadow-[0_0_20px_rgba(255,215,0,0.2)]">
      <span
        className="h-2 w-2 animate-pulse rounded-full bg-[#00e5ff] shadow-[0_0_8px_#00e5ff]"
        aria-hidden
      />
      {n.toLocaleString('zh-CN')}
    </span>
  )
}
