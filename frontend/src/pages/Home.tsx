import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchDailyAll, fetchSigns } from '../api/constellation'
import { AnimatedUserCount } from '../components/AnimatedUserCount'
import { PayButton } from '../components/PayButton'
import { PracticalGuideSection } from '../components/PracticalGuideSection'
import { StarryBackground } from '../components/StarryBackground'
import { FortuneArticleCarousel } from '../components/FortuneArticleCarousel'
import { ZodiacCard } from '../components/ZodiacCard'
import { Icon } from '../components/icons/Icon'
import { usePrice } from '../hooks/usePrices'
import { sunSignFromDate } from '../utils/zodiacCalc'

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
  const navigate = useNavigate()
  const [quickDate, setQuickDate] = useState('')
  const { data: signsData } = useQuery({ queryKey: ['signs'], queryFn: fetchSigns })
  const { data: dailyAll } = useQuery({ queryKey: ['dailyAll'], queryFn: fetchDailyAll })

  const onQuickDateGo = () => {
    if (!quickDate) return
    const sign = sunSignFromDate(quickDate)
    navigate(`/daily/${sign}`)
  }

  const pricePersonality = usePrice('personality')
  const priceCompat = usePrice('compatibility')
  const priceAnnual = usePrice('annual')
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

          <div className="mx-auto mt-6 flex max-w-[280px] items-center gap-2">
            <input
              type="date"
              value={quickDate}
              onChange={(e) => setQuickDate(e.target.value)}
              className="input-cosmic flex-1 text-sm"
              placeholder="输入生日"
            />
            <button
              type="button"
              onClick={onQuickDateGo}
              disabled={!quickDate}
              className="shrink-0 rounded-xl bg-[var(--color-brand-gold)]/90 px-4 py-2.5 text-sm font-semibold text-[#0a0b14] disabled:opacity-40"
            >
              看运势
            </button>
          </div>
          <p className="mt-2 text-[10px] text-[var(--color-text-muted)]">输入生日，一键查看今日星座运势</p>

          <p className="mt-5 flex flex-wrap items-center justify-center gap-2 text-[11px] leading-relaxed text-[var(--color-text-tertiary)]">
            <span>已为</span>
            <AnimatedUserCount />
            <span>位星友完成星盘解读参考</span>
          </p>
        </motion.header>

        <motion.section variants={item} className="relative z-[1] mb-2 flex items-center gap-2 px-0.5">
          <h2 className="shrink-0 bg-gradient-to-r from-white to-[#c4b5fd] bg-clip-text font-serif text-lg font-semibold tracking-tight text-transparent">
            今日运势
          </h2>
          <p className="min-w-0 flex-1 text-center text-[10px] leading-snug text-emerald-300/95 sm:text-[11px]">
            免费星座解读.生成你的星盘名片
          </p>
          <Link
            to="/fortunes"
            className="flex shrink-0 items-center gap-0.5 text-xs font-medium text-[var(--color-brand-cyan)] transition-colors active:text-[#ffd700]"
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

        <motion.section variants={item} className="relative z-[1]">
          <FortuneArticleCarousel />
        </motion.section>

        <motion.section variants={item} className="relative z-[1] section-gap">
          <PracticalGuideSection />
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
            price={pricePersonality}
            to="/payment?product=personality"
            accent="personality"
            chapterCount={7}
          />
          <PayButton
            title="星座配对分析"
            subtitle="双人视角 · 契合与沟通建议"
            price={priceCompat}
            to="/payment?product=compatibility"
            accent="compatibility"
            chapterCount={6}
          />
          <PayButton
            title="年度运势参考"
            subtitle="七章结构 · 全年节奏与月度提示"
            price={priceAnnual}
            to="/payment?product=annual"
            accent="annual"
            chapterCount={7}
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
