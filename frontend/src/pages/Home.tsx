import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { fetchDailyAll, fetchSigns } from '../api/constellation'
import { AnimatedUserCount } from '../components/AnimatedUserCount'
import { PayButton } from '../components/PayButton'
import { StarryBackground } from '../components/StarryBackground'
import { ZodiacCard } from '../components/ZodiacCard'
import { Icon } from '../components/icons/Icon'

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.07, delayChildren: 0.08 },
  },
}

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.42, ease: [0.22, 1, 0.36, 1] as const } },
}

export default function Home() {
  const { data: signsData } = useQuery({ queryKey: ['signs'], queryFn: fetchSigns })
  const { data: dailyAll } = useQuery({ queryKey: ['dailyAll'], queryFn: fetchDailyAll })

  const scoreMap = new Map(dailyAll?.items.map((i) => [i.sign, i.overall_score]) ?? [])

  const today = new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <>
      <StarryBackground />
      <motion.div
        className="relative pb-4"
        variants={container}
        initial="hidden"
        animate="show"
      >
        <div className="constellation-bg absolute inset-0 -z-0 rounded-3xl" aria-hidden />

        <motion.header variants={item} className="relative z-[1] mb-10 text-center">
          {/* Floating game-style shapes */}
          <div className="pointer-events-none absolute left-[6%] top-[2%] h-16 w-16 rounded-full border-2 border-[#ff2d78]/20" />
          <motion.div
            className="pointer-events-none absolute right-[8%] top-[8%] h-12 w-12 rounded-lg border-2 border-[#00e5ff]/25"
            animate={{ rotate: [0, 8, 0], y: [0, -4, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          />
          <div className="pointer-events-none absolute bottom-[12%] left-[12%] h-3 w-3 rounded-full bg-[#ffd700]/40 blur-[1px]" />

          <p className="text-[10px] font-bold uppercase tracking-[0.4em] text-[var(--color-brand-cyan)]/90">
            StarLoom
          </p>
          <h1 className="mt-4 px-2 font-serif text-[1.95rem] font-bold leading-tight tracking-tight text-gradient-hero">
            探索你的星座密码
          </h1>
          <p className="mx-auto mt-4 max-w-[300px] text-[15px] leading-[1.65] text-[var(--color-text-secondary)]">
            基于 NASA 公开天文数据与 AI 深度分析，生成可回看的专属报告
          </p>
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">{today}</p>

          <motion.div whileTap={{ scale: 0.96 }} className="mt-10 inline-block">
            <Link
              to="/quicktest"
              className="btn-glow btn-glow-pulse relative inline-flex min-h-[54px] min-w-[272px] items-center justify-center rounded-full px-8 py-3.5 text-[15px] shadow-[0_8px_32px_rgba(255,45,120,0.25)]"
            >
              <span className="relative z-[1] flex items-center gap-2 font-bold">
                <Icon name="sparkle" size={18} className="text-[#0a0b14]" />
                开始星座解读
              </span>
            </Link>
          </motion.div>

          <p className="mt-5 flex flex-wrap items-center justify-center gap-2 text-[11px] leading-relaxed text-[var(--color-text-tertiary)]">
            <span>已为</span>
            <AnimatedUserCount />
            <span>位星友完成星盘解读参考</span>
          </p>

          <div className="mx-auto mt-8 flex max-w-sm flex-wrap items-center justify-center gap-x-5 gap-y-2 border-y border-white/[0.08] py-4 text-[11px] text-[var(--color-text-secondary)]">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-brand-cyan)] shadow-[0_0_8px_#00e5ff]" />
              NASA 天文数据
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-brand-violet)] shadow-[0_0_8px_#8b5cf6]" />
              AI 深度分析
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[#ffd700] shadow-[0_0_8px_#ffd700]" />
              流式生成可回看
            </span>
          </div>
        </motion.header>

        <motion.section variants={item} className="relative z-[1] mb-2 flex items-center justify-between px-0.5">
          <h2 className="bg-gradient-to-r from-white to-[#c4b5fd] bg-clip-text font-serif text-lg font-semibold tracking-tight text-transparent">
            今日运势
          </h2>
          <Link
            to="/fortunes"
            className="flex items-center gap-0.5 text-xs font-medium text-[var(--color-brand-cyan)] transition-colors active:text-[#ffd700]"
          >
            全部星座
            <Icon name="chevronRight" size={14} />
          </Link>
        </motion.section>
        <div className="relative z-[1]">
          <div className="scroll-fade-x flex gap-3 overflow-x-auto pb-3 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {(signsData?.signs ?? []).map((s, i) => (
              <div key={s.sign} className="min-w-[105px] shrink-0">
                <ZodiacCard
                  sign={s.sign}
                  signCn={s.sign_cn}
                  symbol={s.symbol}
                  score={scoreMap.get(s.sign)}
                  index={i}
                />
              </div>
            ))}
          </div>
        </div>

        <motion.section variants={item} className="relative z-[1] section-gap">
          <Link
            to="/report/compatibility"
            className="card-game-glow group relative block min-h-[210px] overflow-hidden rounded-2xl border-2 border-[#ff2d78]/25 shadow-[0_0_40px_rgba(255,45,120,0.15)] transition-all active:scale-[0.99]"
          >
            <img
              src="/illustrations/compatibility-home.png"
              alt="双人合盘"
              className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14] via-[#0a0b14]/60 to-transparent" />

            <div className="relative z-[1] flex min-h-[210px] flex-col justify-end p-5">
              <span className="absolute right-3 top-3 rounded-full bg-gradient-to-r from-[#ff2d78] to-[#db2777] px-3 py-1.5 text-xs font-black text-white shadow-lg">
                ¥0.20
              </span>
              <p className="text-lg font-bold leading-snug text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.6)]">
                测测你和 TA 的匹配度
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-white/80 drop-shadow-[0_1px_4px_rgba(0,0,0,0.4)]">
                双人合盘 · 输入生日即可生成，支付后解锁完整相处与沟通建议
              </p>
              <p className="mt-3 flex items-center gap-1 text-[11px] font-bold text-[#f472b6] drop-shadow-[0_1px_4px_rgba(0,0,0,0.4)]">
                解锁完整报告
                <Icon name="chevronRight" size={12} className="inline" />
              </p>
            </div>
          </Link>
        </motion.section>

        <motion.section variants={item} className="relative z-[1] section-gap space-y-4">
          <div>
            <h2 className="bg-gradient-to-r from-[#fde68a] via-[#f472b6] to-[#a78bfa] bg-clip-text font-serif text-xl font-semibold tracking-tight text-transparent">
              深度报告
            </h2>
            <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-tertiary)]">
              以下为报告样式预览，支付后 AI 流式生成全文，可在「我的报告」随时回看
            </p>
          </div>
          <PayButton
            title="个人星座性格报告"
            subtitle="7 章深度结构 · 约 3000+ 字参考"
            price="0.10"
            to="/payment?product=personality"
            accent="personality"
            chapterCount={7}
          />
          <PayButton
            title="星座配对分析"
            subtitle="双人视角 · 契合与沟通建议"
            price="0.20"
            to="/payment?product=compatibility"
            accent="compatibility"
            chapterCount={6}
          />
          <PayButton
            title="年度运势参考"
            subtitle="全年节奏 · 分季度提示"
            price="0.30"
            to="/payment?product=annual"
            accent="annual"
            chapterCount={5}
          />
        </motion.section>

        <motion.div
          variants={item}
          className="relative z-[1] section-gap flex flex-col items-center gap-4 border-t border-white/[0.08] pt-10 text-sm"
        >
          <div className="flex flex-wrap justify-center gap-8">
            <Link
              to="/chat"
              className="flex items-center gap-1.5 font-medium text-[var(--color-text-secondary)] transition-colors active:text-[var(--color-brand-cyan)]"
            >
              <Icon name="sparkle" size={16} />
              AI 顾问
            </Link>
            <Link
              to="/my-reports"
              className="flex items-center gap-1.5 font-bold text-[#ffd700]"
            >
              <Icon name="reports" size={16} />
              我的报告
            </Link>
          </div>
          <p className="max-w-xs text-center text-[10px] leading-relaxed text-[var(--color-text-muted)]">
            内容仅供娱乐与自我探索参考，请勿作为医疗、法律或重大决策依据。
          </p>
        </motion.div>
      </motion.div>
    </>
  )
}
