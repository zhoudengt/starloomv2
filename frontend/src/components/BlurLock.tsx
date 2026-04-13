import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Icon } from './icons/Icon'

const CHAPTERS = [
  '太阳星座深度解读',
  '性格优势与挑战',
  '感情与亲密关系',
  '事业与财富节奏',
  '人际关系与社交',
  '年度成长建议',
  '专属行动清单',
]

const DOT_COLORS = ['#ff6b4a', '#00e5ff', '#a78bfa', '#ffd700', '#f472b6', '#34d399', '#38bdf8']

export default function BlurLock({
  ctaTo,
  price = '0.10',
  gender = '',
}: {
  ctaTo: string
  price?: string
  gender?: 'female' | 'male' | ''
}) {
  const heroSrc =
    gender === 'female'
      ? '/illustrations/personality-hero-female.webp'
      : gender === 'male'
        ? '/illustrations/personality-hero.webp'
        : '/illustrations/personality-hero-neutral.webp'

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-40px' }}
      transition={{ duration: 0.45, ease: 'easeOut' }}
      className="relative mt-8"
    >
      <motion.div
        className="pointer-events-none absolute -inset-[1px] rounded-2xl"
        animate={{
          boxShadow: [
            '0 0 0 0 rgba(255,215,0,0.35)',
            '0 0 0 10px rgba(255,215,0,0)',
            '0 0 0 0 rgba(255,215,0,0.35)',
          ],
        }}
        transition={{ duration: 2.8, repeat: Infinity, ease: 'easeInOut' }}
      />
      <div className="relative overflow-hidden rounded-2xl border border-[#ffd700]/35 shadow-[0_0_48px_rgba(139,92,246,0.2)]">
        {/* Full-bleed illustration — clearer than before */}
        <img
          src={heroSrc}
          alt=""
          className="pointer-events-none absolute inset-0 h-full min-h-[100%] w-full object-cover object-right-top opacity-[0.58] sm:object-center"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-r from-[#0a0b18]/95 via-[#0a0b18]/60 to-[#0a0b18]/30 sm:from-[#0a0b18]/92 sm:via-[#0a0b18]/55 sm:to-transparent"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#0a0b18] via-transparent to-[#0a0b18]/40"
          aria-hidden
        />
        <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl" aria-hidden>
          <div className="absolute -left-6 top-4 h-28 w-28 rounded-full bg-[#ff2d78]/15 blur-3xl" />
          <div className="absolute right-0 top-1/4 h-32 w-32 rounded-full bg-[#8b5cf6]/14 blur-3xl" />
        </div>

        <div className="relative z-[1] p-4 sm:p-5">
          <p className="mb-3 flex flex-wrap items-center gap-2 text-[15px] font-bold tracking-tight text-[#ffd700] drop-shadow-[0_2px_8px_rgba(0,0,0,0.75)]">
            <Icon name="lock" size={18} className="shrink-0" />
            完整分析报告 · 共 7 章 · 约 3000+ 字
          </p>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-2 text-[13px] font-medium leading-snug text-white drop-shadow-[0_1px_4px_rgba(0,0,0,0.85)]">
            {CHAPTERS.map((t, i) => (
              <li key={t} className="flex items-start gap-2.5">
                <span
                  className="mt-0.5 h-2 w-2 shrink-0 rounded-full shadow-[0_0_10px_currentColor]"
                  style={{ color: DOT_COLORS[i % DOT_COLORS.length] }}
                />
                {t}
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] leading-relaxed text-white/75">
            解锁后查看完整章节、深度解读与可执行行动清单。
          </p>
          <motion.div
            className="mt-5 w-full"
            animate={{ scale: [1, 1.02, 1] }}
            transition={{ duration: 2.2, repeat: Infinity }}
          >
            <Link
              to={ctaTo}
              className="btn-glow btn-glow-pulse relative flex w-full items-center justify-center rounded-2xl px-6 py-4 text-center text-base font-bold shadow-[0_12px_40px_rgba(255,45,120,0.45)]"
            >
              <span className="relative z-[1] text-[#0a0b14]">解锁完整报告 ¥{price}</span>
            </Link>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}
