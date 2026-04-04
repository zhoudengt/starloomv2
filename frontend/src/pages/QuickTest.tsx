import { useMutation } from '@tanstack/react-query'
import html2canvas from 'html2canvas'
import QRCode from 'qrcode'
import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { postQuickTest } from '../api/quicktest'
import { fetchProfile } from '../api/user'
import BirthChartWheel from '../components/BirthChartWheel'
import BlurLock from '../components/BlurLock'
import RadarChart from '../components/RadarChart'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { CN_CITY_NAMES } from '../utils/cnCities'
import { placementsFromBirth, sunSignFromDate, ZODIAC_CN } from '../utils/zodiacCalc'
import { useBirthProfileStore } from '../stores/birthProfileStore'
import { useUserStore } from '../stores/userStore'

const SUMMARY_DOTS = ['#ff6b4a', '#00e5ff', '#a78bfa', '#ffd700', '#f472b6']

const QUICKTEST_SHARE_URL = () =>
  typeof window === 'undefined' ? 'https://starloom.app/quicktest' : `${window.location.origin}/quicktest`

/** 28 particles: some dots, some short streaks for stronger motion */
const PARTICLE_SEED = Array.from({ length: 28 }, (_, i) => ({
  id: i,
  left: `${5 + ((i * 13) % 90)}%`,
  top: `${8 + ((i * 19) % 84)}%`,
  delay: (i % 7) * 0.07,
  duration: 1.6 + (i % 6) * 0.22,
  streak: i % 3 === 0,
  wide: i % 4 === 0,
}))

const RADAR_DIM_ROWS = [
  { key: 'love' as const, label: '感情', hint: '情感表达与亲密连接', color: '#f472b6' },
  { key: 'career' as const, label: '事业', hint: '目标驱动与执行力', color: '#fbbf24' },
  { key: 'social' as const, label: '社交', hint: '人际吸引与沟通', color: '#34d399' },
  { key: 'creativity' as const, label: '创造', hint: '灵感与创新能力', color: '#a78bfa' },
  { key: 'intuition' as const, label: '直觉', hint: '洞察力与第六感', color: '#38bdf8' },
]

/** 星盘卡片：紫金动态底图（喜庆、明显） */
function WheelCardAnimatedBg() {
  const stars = useMemo(
    () =>
      Array.from({ length: 14 }, (_, i) => ({
        id: i,
        left: `${(i * 17) % 92}%`,
        top: `${(i * 23) % 88}%`,
        delay: (i % 5) * 0.12,
        dur: 1.8 + (i % 4) * 0.4,
      })),
    [],
  )
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl" aria-hidden>
      <motion.div
        className="absolute inset-[-8%] bg-[radial-gradient(ellipse_85%_70%_at_50%_38%,rgba(139,92,246,0.55)_0%,rgba(88,28,135,0.35)_35%,rgba(8,8,20,0.97)_70%,#030308_100%)]"
        animate={{ scale: [1, 1.05, 1], opacity: [0.92, 1, 0.92] }}
        transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        className="absolute left-1/2 top-1/2 h-[min(120%,420px)] w-[min(120%,420px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#ffd700]/30"
        animate={{ rotate: 360 }}
        transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="absolute left-1/2 top-1/2 h-[min(95%,340px)] w-[min(95%,340px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-[#a78bfa]/35"
        animate={{ rotate: -360 }}
        transition={{ duration: 26, repeat: Infinity, ease: 'linear' }}
      />
      <motion.div
        className="absolute left-1/2 top-[42%] h-[min(70%,240px)] w-[min(70%,240px)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(240,199,94,0.22)_0%,transparent_65%)] blur-xl"
        animate={{ scale: [1, 1.12, 1], opacity: [0.5, 0.85, 0.5] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />
      {stars.map((s) => (
        <motion.span
          key={s.id}
          className="absolute h-1 w-1 rounded-full bg-white shadow-[0_0_6px_#fff]"
          style={{ left: s.left, top: s.top }}
          animate={{ opacity: [0.2, 1, 0.2], scale: [0.7, 1.15, 0.7] }}
          transition={{ duration: s.dur, repeat: Infinity, delay: s.delay, ease: 'easeInOut' }}
        />
      ))}
      <div className="absolute inset-0 bg-gradient-to-t from-[#030308] via-transparent to-[#08091a]/50" />
    </div>
  )
}

/** 雷达卡片：能量脉冲动态底图 */
function RadarCardAnimatedBg() {
  const blobs = useMemo(
    () => [
      { left: '10%', top: '20%', color: 'rgba(244,114,182,0.35)', delay: 0 },
      { left: '60%', top: '15%', color: 'rgba(250,204,21,0.28)', delay: 0.5 },
      { left: '70%', top: '55%', color: 'rgba(167,139,250,0.32)', delay: 1 },
      { left: '15%', top: '60%', color: 'rgba(56,189,248,0.28)', delay: 1.5 },
    ],
    [],
  )
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl" aria-hidden>
      <motion.div
        className="absolute inset-[-10%] bg-[radial-gradient(ellipse_90%_75%_at_50%_45%,rgba(168,85,247,0.42)_0%,rgba(236,72,153,0.18)_40%,rgba(8,8,22,0.96)_68%,#020208_100%)]"
        animate={{ scale: [1, 1.06, 1], opacity: [0.88, 1, 0.88] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#f0c75e]/20"
          style={{ width: `${45 + i * 18}%`, height: `${45 + i * 18}%`, maxWidth: 380, maxHeight: 380 }}
          initial={{ scale: 0.85, opacity: 0.5 }}
          animate={{ scale: [0.85, 1.15], opacity: [0.45, 0] }}
          transition={{ duration: 3.2, repeat: Infinity, delay: i * 0.9, ease: 'easeOut' }}
        />
      ))}
      {blobs.map((b, i) => (
        <motion.div
          key={i}
          className="absolute h-24 w-24 rounded-full blur-3xl"
          style={{ left: b.left, top: b.top, background: b.color }}
          animate={{ x: [0, 12, -8, 0], y: [0, -10, 8, 0], scale: [1, 1.15, 0.95, 1] }}
          transition={{ duration: 8 + i, repeat: Infinity, delay: b.delay, ease: 'easeInOut' }}
        />
      ))}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#08091a]/25 to-[#030308]/90" />
    </div>
  )
}

export default function QuickTest() {
  const token = useUserStore((s) => s.token)
  const birthDate = useBirthProfileStore((s) => s.birthDate)
  const birthTime = useBirthProfileStore((s) => s.birthTime)
  const birthPlaceName = useBirthProfileStore((s) => s.birthPlaceName)
  const gender = useBirthProfileStore((s) => s.gender)
  const setBirthDate = useBirthProfileStore((s) => s.setBirthDate)
  const setBirthTime = useBirthProfileStore((s) => s.setBirthTime)
  const setBirthPlaceName = useBirthProfileStore((s) => s.setBirthPlaceName)
  const setGender = useBirthProfileStore((s) => s.setGender)
  const applyFromProfile = useBirthProfileStore((s) => s.applyFromProfile)
  const [step, setStep] = useState<'form' | 'result'>('form')
  const [wheelLoop, setWheelLoop] = useState(0)
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null)
  const [captureBusy, setCaptureBusy] = useState(false)

  const resultCardRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({
    mutationFn: () =>
      postQuickTest({
        birth_date: birthDate,
        gender: gender || undefined,
        birth_time: birthTime || undefined,
        birth_place_name: birthPlaceName || undefined,
      }),
    onSuccess: () => setStep('result'),
  })

  useEffect(() => {
    if (!token) return
    void fetchProfile()
      .then((p) => applyFromProfile(p))
      .catch(() => {})
  }, [token, applyFromProfile])

  const placements = useMemo(
    () => placementsFromBirth(birthDate, birthTime || null),
    [birthDate, birthTime],
  )

  const sunSlug = useMemo(() => sunSignFromDate(birthDate), [birthDate])
  const sunCn = ZODIAC_CN[sunSlug]

  useEffect(() => {
    if (!mutation.isPending) {
      setWheelLoop(0)
      return
    }
    let raf: number
    const start = performance.now()
    const cycleMs = 3200
    const tick = () => {
      const t = ((performance.now() - start) % cycleMs) / cycleMs
      setWheelLoop(t)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [mutation.isPending])

  useEffect(() => {
    if (step !== 'result' || !mutation.data) {
      setQrDataUrl(null)
      return
    }
    let cancelled = false
    void QRCode.toDataURL(QUICKTEST_SHARE_URL(), { width: 96, margin: 1, color: { dark: '#0a0b14', light: '#ffffff' } }).then(
      (url) => {
        if (!cancelled) setQrDataUrl(url)
      },
    )
    return () => {
      cancelled = true
    }
  }, [step, mutation.data])

  const payHref = `/payment?product=personality&birth_date=${encodeURIComponent(birthDate)}${gender ? `&gender=${encodeURIComponent(gender)}` : ''}${birthTime ? `&birth_time=${encodeURIComponent(birthTime)}` : ''}`

  const captureResultCard = async (): Promise<Blob | null> => {
    const node = resultCardRef.current
    if (!node) return null
    window.scrollTo(0, 0)
    const canvas = await html2canvas(node, {
      scale: 2,
      backgroundColor: '#08091a',
      logging: false,
      useCORS: true,
      allowTaint: true,
    })
    return new Promise((resolve) => {
      canvas.toBlob((b) => resolve(b), 'image/png')
    })
  }

  const saveResultCard = async () => {
    if (!mutation.data) return
    setCaptureBusy(true)
    try {
      const blob = await captureResultCard()
      if (!blob) return
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `starloom-${mutation.data.sign_cn}-星座解读.png`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setCaptureBusy(false)
    }
  }

  const shareResultCard = async () => {
    if (!mutation.data) return
    setCaptureBusy(true)
    try {
      const blob = await captureResultCard()
      if (!blob) return
      const file = new File([blob], `starloom-${mutation.data.sign_cn}.png`, { type: 'image/png' })
      const text = `${mutation.data.persona_label} · ${mutation.data.sign_cn} — StarLoom 星座解读`
      try {
        if (navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], title: 'StarLoom', text })
          return
        }
      } catch {
        /* fall through */
      }
      try {
        if (navigator.share) {
          await navigator.share({ title: 'StarLoom', text, url: QUICKTEST_SHARE_URL() })
          return
        }
      } catch {
        /* fall through */
      }
      await saveResultCard()
    } finally {
      setCaptureBusy(false)
    }
  }

  if (mutation.isPending) {
    return (
      <>
        <StarryBackground />
        <div className="relative flex min-h-[100dvh] flex-col items-center justify-center overflow-hidden px-4 py-10">
          <img
            src={`/zodiac/${sunSlug}.png`}
            alt=""
            className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-[0.35]"
            aria-hidden
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#08091a]/80 via-[#08091a]/55 to-[#08091a]" aria-hidden />

          {/* Orbit rings — layered "star gate" */}
          <motion.div
            className="pointer-events-none absolute left-1/2 top-1/2 h-[min(98vw,420px)] w-[min(98vw,420px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#ffd700]/20"
            animate={{ rotate: 360 }}
            transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
          />
          <motion.div
            className="pointer-events-none absolute left-1/2 top-1/2 h-[min(92vw,380px)] w-[min(92vw,380px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#a78bfa]/35"
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          />
          <motion.div
            className="pointer-events-none absolute left-1/2 top-1/2 h-[min(78vw,320px)] w-[min(78vw,320px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-[#00e5ff]/28"
            animate={{ rotate: -360 }}
            transition={{ duration: 28, repeat: Infinity, ease: 'linear' }}
          />
          <motion.div
            className="pointer-events-none absolute left-1/2 top-1/2 h-[min(64vw,260px)] w-[min(64vw,260px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#ff2d78]/22"
            animate={{ rotate: -360 }}
            transition={{ duration: 32, repeat: Infinity, ease: 'linear' }}
          />

          {/* Shooting stars — diagonal sweeps */}
          {[0, 1, 2, 3].map((i) => (
            <motion.div
              key={`star-${i}`}
              className="pointer-events-none absolute left-0 h-px w-[min(40vw,180px)] origin-left -rotate-[38deg] bg-gradient-to-r from-transparent via-white/90 to-transparent"
              style={{ top: `${12 + i * 22}%` }}
              initial={{ opacity: 0, x: '110vw' }}
              animate={{ opacity: [0, 1, 0], x: ['110vw', '-30vw'] }}
              transition={{
                duration: 2.4 + i * 0.35,
                repeat: Infinity,
                delay: i * 0.55,
                ease: 'linear',
              }}
            />
          ))}

          {PARTICLE_SEED.map((p) => (
            <motion.span
              key={p.id}
              className={
                p.streak
                  ? 'pointer-events-none absolute rounded-full bg-gradient-to-r from-transparent via-white/80 to-transparent shadow-[0_0_6px_rgba(167,139,250,0.8)]'
                  : 'pointer-events-none absolute rounded-full bg-white/70 shadow-[0_0_8px_rgba(167,139,250,0.9)]'
              }
              style={{
                left: p.left,
                top: p.top,
                width: p.streak ? (p.wide ? 14 : 10) : p.wide ? 5 : 3,
                height: p.streak ? 2 : p.wide ? 5 : 3,
              }}
              animate={{ opacity: [0.15, 1, 0.15], scale: p.streak ? [0.85, 1.1, 0.85] : [0.6, 1.15, 0.6] }}
              transition={{ duration: p.duration, repeat: Infinity, delay: p.delay, ease: 'easeInOut' }}
            />
          ))}

          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="relative z-[1] w-full max-w-sm text-center"
          >
            <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-[var(--color-brand-cyan)]">
              星盘绘制中
            </p>
            <div className="relative mt-6 flex justify-center">
              <motion.div
                className="pointer-events-none absolute left-1/2 top-1/2 h-[min(72vw,300px)] w-[min(72vw,300px)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(139,92,246,0.38)_0%,rgba(240,199,94,0.12)_45%,transparent_72%)] blur-md"
                animate={{ scale: [1, 1.08, 1], opacity: [0.55, 0.85, 0.55] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              />
              <div className="relative z-[1]">
                <BirthChartWheel
                  sun={placements.sun}
                  moon={placements.moon}
                  rising={placements.rising}
                  size={220}
                  drawProgress={wheelLoop}
                />
              </div>
            </div>
            <p className="mt-8 font-serif text-lg font-semibold text-gradient-shimmer">正在解读你的星象…</p>
            <p className="mt-3 text-xs leading-relaxed text-[var(--color-text-secondary)]">
              基于生日与出生时间生成示意星盘，仅供风格化展示
            </p>
          </motion.div>
        </div>
      </>
    )
  }

  if (step === 'result' && mutation.data) {
    const d = mutation.data
    return (
      <>
        <StarryBackground />
        <Link
          to="/"
          className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-[#ffd700]"
        >
          ← 返回首页
        </Link>
        <motion.div
          ref={resultCardRef}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          className="card-featured relative overflow-hidden rounded-2xl"
        >
          {/* Hero */}
          <div className="relative h-[min(50vw,280px)] w-full overflow-hidden">
            <img
              src={`/zodiac/${sunSlug}.png`}
              alt=""
              className="h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#08091a] via-[#08091a]/55 to-[#08091a]/25" />
            <div className="absolute inset-x-0 bottom-0 p-5 pb-6">
              <p className="text-[10px] font-bold tracking-[0.28em] text-[#ffd700]/95">你的星座人格标签</p>
              <h1 className="mt-2 font-serif text-[1.75rem] font-bold leading-tight tracking-tight text-white drop-shadow-[0_2px_12px_rgba(0,0,0,0.65)]">
                {d.persona_label}
              </h1>
              <p className="mt-2 font-serif text-lg text-white/90">
                {d.symbol} {d.sign_cn}
              </p>
            </div>
          </div>

          <div className="relative px-5 pb-6 pt-2">
            <div className="pointer-events-none absolute inset-0 hex-grid-bg opacity-[0.28]" aria-hidden />

            {/* 星盘：动态底图 + 图上标注说明 */}
            <div className="relative z-[1] mt-4 overflow-hidden rounded-2xl border border-white/[0.08] shadow-[0_0_0_1px_rgba(255,215,0,0.1)]">
              <WheelCardAnimatedBg />
              <img
                src="/illustrations/section-astro-bg.png"
                alt=""
                className="pointer-events-none absolute inset-0 z-0 h-full w-full object-cover opacity-[0.32]"
                aria-hidden
              />
              <div className="relative z-[1] px-2 pb-5 pt-4 sm:px-4">
                <p className="text-center text-xs font-bold tracking-[0.22em] text-[#ffd700]/95">星盘分布</p>
                <p className="mt-1.5 text-center text-[10px] leading-relaxed text-[var(--color-text-tertiary)]">
                  外圈为十二宫位简写；虚线连到文字说明太阳、月亮、上升的含义
                </p>
                <div className="mt-1 flex justify-center overflow-x-auto">
                  <BirthChartWheel
                    sun={placements.sun}
                    moon={placements.moon}
                    rising={placements.rising}
                    size={240}
                    showLegend={false}
                    annotations={{
                      sun: { label: `太阳 ${placements.sunCn}`, hint: '核心性格与自我意识' },
                      moon: { label: `月亮 ${placements.moonCn}`, hint: '内在情感与潜意识' },
                      rising: { label: `上升 ${placements.risingCn}`, hint: '外在表现与第一印象' },
                    }}
                  />
                </div>
              </div>
            </div>

            {/* 五维雷达：动态底图 + 维度分数与说明在图上 */}
            <div className="relative z-[1] mt-6 overflow-hidden rounded-2xl border border-white/[0.08] shadow-[0_0_0_1px_rgba(255,215,0,0.12)]">
              <RadarCardAnimatedBg />
              <img
                src="/illustrations/section-radar-bg.png"
                alt=""
                className="pointer-events-none absolute inset-0 z-0 h-full w-full object-cover opacity-[0.32]"
                aria-hidden
              />
              <div className="relative z-[1] px-2 pb-5 pt-4 sm:px-4">
                <p className="text-center text-xs font-bold tracking-[0.22em] text-[#ffd700]/95">五维能量分布</p>
                <p className="mt-1.5 text-center text-[10px] leading-relaxed text-[var(--color-text-tertiary)]">
                  各顶点旁为分数与参考解读；面积越大该维度能量越强
                </p>
                <div className="mt-2 flex justify-center">
                  <RadarChart
                    dimensions={d.dimensions}
                    size={300}
                    hints={Object.fromEntries(RADAR_DIM_ROWS.map((r) => [r.key, r.hint]))}
                    hintColors={Object.fromEntries(RADAR_DIM_ROWS.map((r) => [r.key, r.color]))}
                  />
                </div>
              </div>
            </div>

            <div className="relative z-[1] mt-6 rounded-2xl border border-white/[0.06] border-l-4 border-l-[#ffd700]/85 bg-black/20 py-4 pl-4 pr-4">
              <ul className="space-y-4 text-base leading-relaxed text-[var(--color-text-primary)]/95">
                {d.summary.map((line, i) => (
                  <li key={i} className="flex gap-3">
                    <span
                      className="mt-2.5 h-2 w-2 shrink-0 rounded-full shadow-[0_0_10px_currentColor]"
                      style={{ color: SUMMARY_DOTS[i % SUMMARY_DOTS.length] }}
                    />
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative z-[1] mt-8 flex flex-row items-center gap-4 border-t border-white/[0.08] pt-6">
              <div className="shrink-0">
                <p className="text-[9px] tracking-[0.15em] text-[var(--color-text-tertiary)]">邀请好友</p>
                {qrDataUrl ? (
                  <img
                    src={qrDataUrl}
                    alt=""
                    className="mt-1.5 h-[88px] w-[88px] rounded-lg border border-white/15 bg-white p-1"
                  />
                ) : (
                  <div className="mt-1.5 flex h-[88px] w-[88px] items-center justify-center rounded-lg border border-white/10 bg-black/30 text-[9px] text-[var(--color-text-muted)]">
                    生成中…
                  </div>
                )}
              </div>
              <div className="min-w-0 flex-1 space-y-2">
                <p className="break-all text-[9px] text-[var(--color-text-muted)]">{QUICKTEST_SHARE_URL()}</p>
                <div className="flex gap-2">
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.98 }}
                    disabled={captureBusy}
                    onClick={() => void saveResultCard()}
                    className="card-elevated flex flex-1 items-center justify-center gap-2 rounded-xl border border-white/15 py-2.5 text-sm text-[var(--color-text-primary)] disabled:opacity-50"
                  >
                    <Icon name="share" size={16} />
                    {captureBusy ? '生成中…' : '保存图片'}
                  </motion.button>
                  <motion.button
                    type="button"
                    whileTap={{ scale: 0.98 }}
                    disabled={captureBusy}
                    onClick={() => void shareResultCard()}
                    className="btn-glow relative flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold disabled:opacity-50"
                  >
                    <span className="relative z-[1] text-[#0a0b14]">分享</span>
                  </motion.button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        <BlurLock ctaTo={payHref} price="0.10" gender={gender} />

        <p className="mt-4 text-center text-[10px] text-[var(--color-text-muted)]">
          邀请好友通过扫码进入，一起探索星座密码
        </p>
      </>
    )
  }

  return (
    <>
      <StarryBackground />
      <Link to="/" className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-[#ffd700]">
        ← 返回
      </Link>
      <h1 className="bg-gradient-to-r from-white via-[#c4b5fd] to-[#f472b6] bg-clip-text font-serif text-2xl font-bold tracking-tight text-transparent">
        免费星座解读
      </h1>

      <div className="card-elevated relative mt-6 overflow-hidden rounded-2xl border-2 border-[#8b5cf6]/40 shadow-[0_0_36px_rgba(139,92,246,0.22)]">
        {/* Zodiac hero — 40vh */}
        <div className="relative h-[40vh] min-h-[220px] w-full overflow-hidden">
          <AnimatePresence mode="sync">
            <motion.img
              key={sunSlug}
              src={`/zodiac/${sunSlug}.png`}
              alt=""
              className="absolute inset-0 h-full w-full object-cover"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.45, ease: 'easeOut' }}
            />
          </AnimatePresence>
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#08091a] via-[#08091a]/40 to-[#1e1b4b]/35" />
          <div className="absolute inset-x-0 bottom-0 p-5">
            <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-[#ffd700]/90">太阳星座</p>
            <motion.h2
              key={sunSlug}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
              className="mt-1 font-serif text-4xl font-bold tracking-tight text-white drop-shadow-[0_4px_24px_rgba(0,0,0,0.5)]"
            >
              {sunCn}
            </motion.h2>
          </div>
        </div>

        <div className="space-y-5 p-5">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold text-[#a78bfa]">生日</label>
              <div className="relative mt-1.5 flex items-center rounded-xl border-2 border-[#8b5cf6]/35 bg-[#08091a]/70 px-3 py-2.5">
                <Icon name="calendar" size={20} className="mr-2 shrink-0 text-[#a78bfa]" />
                <input
                  type="date"
                  className="input-cosmic flex-1 border-0 bg-transparent p-0 text-sm focus-ring-violet"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="text-xs font-bold text-[#22d3ee]">出生时间</label>
              <p className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">
                用于上升点与十二宫位计算，不填则按当日正午近似
              </p>
              <div className="relative mt-1.5 flex items-center rounded-xl border-2 border-[#00e5ff]/30 bg-[#08091a]/70 px-3 py-2.5">
                <Icon name="sparkle" size={20} className="mr-2 shrink-0 text-[#00e5ff]" />
                <input
                  type="time"
                  className="input-cosmic flex-1 border-0 bg-transparent p-0 text-sm focus-ring-cyan"
                  value={birthTime}
                  onChange={(e) => setBirthTime(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-[#a78bfa]">出生城市（可选）</label>
            <p className="mt-0.5 text-[10px] text-[var(--color-text-muted)]">用于经纬度与宫位计算，不选则默认北京</p>
            <select
              className="input-cosmic mt-1.5 w-full rounded-xl border-2 border-[#8b5cf6]/30 bg-[#08091a]/70 px-3 py-2.5 text-sm"
              value={birthPlaceName}
              onChange={(e) => setBirthPlaceName(e.target.value)}
            >
              <option value="">默认北京</option>
              {CN_CITY_NAMES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="text-xs font-bold text-[#ffd700]">性别（可选）</span>
            <div className="mt-2 flex gap-2">
              {(
                [
                  { key: 'female' as const, label: '女' },
                  { key: 'male' as const, label: '男' },
                  { key: '' as const, label: '不选' },
                ] as const
              ).map(({ key, label }) => {
                const active = gender === key
                return (
                  <motion.button
                    key={label}
                    type="button"
                    whileTap={{ scale: 0.97 }}
                    onClick={() => setGender(key)}
                    className={`flex-1 rounded-full border-2 py-2.5 text-sm font-semibold transition-all ${
                      active
                        ? 'border-[#ffd700]/70 bg-gradient-to-r from-[#8b5cf6]/35 to-[#ff2d78]/25 text-white shadow-[0_0_20px_rgba(255,215,0,0.25)]'
                        : 'border-white/[0.12] bg-black/25 text-[var(--color-text-secondary)]'
                    }`}
                  >
                    {label}
                  </motion.button>
                )
              })}
            </div>
          </div>

          {mutation.isError && (
            <p className="text-sm text-red-300/90">{(mutation.error as Error)?.message ?? '请求失败'}</p>
          )}
          {!token && <p className="text-center text-xs text-amber-200/80">正在连接账号…</p>}

          <motion.button
            type="button"
            whileTap={{ scale: 0.97 }}
            onClick={() => mutation.mutate()}
            disabled={!token}
            className="btn-glow relative w-full rounded-xl py-4 text-base font-bold disabled:opacity-45"
          >
            <span className="relative z-[1] text-[#0a0b14]">揭晓我的星盘</span>
          </motion.button>
        </div>
      </div>
    </>
  )
}
