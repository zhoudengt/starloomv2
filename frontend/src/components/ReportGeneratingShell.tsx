import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { COMPATIBILITY_STREAM_BG } from '../constants/reportStreamVisual'
import { Icon } from './icons/Icon'
import { sunSignFromDate, ZODIAC_CN } from '../utils/zodiacCalc'

export type ReportStreamingKind = 'personality' | 'compatibility' | 'annual' | 'astro_event'

/** 与 QuickTest loading 一致，条数略减以适配正文区高度 */
const STREAM_MASK_PARTICLES = Array.from({ length: 20 }, (_, i) => ({
  id: i,
  left: `${5 + ((i * 13) % 90)}%`,
  top: `${8 + ((i * 19) % 84)}%`,
  delay: (i % 7) * 0.07,
  duration: 1.6 + (i % 6) * 0.22,
  streak: i % 3 === 0,
  wide: i % 4 === 0,
}))

const CHAPTERS: Record<ReportStreamingKind, string[]> = {
  personality: [
    '太阳星座与核心动机',
    '性格优势与挑战',
    '感情与亲密关系',
    '事业与财富节奏',
    '成长建议与行动清单',
  ],
  compatibility: [
    '双人能量与节奏',
    '沟通与相处模式',
    '冲突与修复建议',
    '长期关系参考',
  ],
  annual: ['年度主题', '分季度节奏', '机遇与提醒', '行动建议'],
  astro_event: ['天象背景', '个人节奏感受', '行动与复盘'],
}

export default function ReportGeneratingShell({
  text,
  loading,
  reportType = 'personality',
  birthDate,
  signCn,
}: {
  text: string
  loading: boolean
  reportType?: ReportStreamingKind
  /** YYYY-MM-DD — 流式正文区遮罩用太阳星座插画（配对报告遮罩用双人图，不依赖此项） */
  birthDate?: string
  /** 预留：与速测一致后续可在遮罩内展示示意盘 */
  birthTime?: string
  /** 配对：双星座文案「A座 × B座」；其它类型可传中文星座名单人展示 */
  signCn?: string
}) {
  const chapters = CHAPTERS[reportType] ?? CHAPTERS.personality
  const charCount = text.length
  const isCompatibility = reportType === 'compatibility'
  const sunSlug = birthDate ? sunSignFromDate(birthDate) : 'gemini'
  const signLabel = birthDate ? ZODIAC_CN[sunSignFromDate(birthDate)] : '星座'
  const maskBgSrc = isCompatibility ? COMPATIBILITY_STREAM_BG : `/zodiac/${sunSlug}.png`
  const maskEyebrow = isCompatibility ? '双人合盘' : '太阳星座'
  const maskTitle = isCompatibility ? signCn || '双人视角' : signLabel

  return (
    <div className="relative mt-2 min-h-[8rem] rounded-2xl border border-white/[0.08] bg-[#08091a]/60">
      {loading && (
        <div className="sticky top-0 z-20 flex items-center justify-between gap-2 border-b border-white/[0.06] bg-[#0a0b18]/95 px-3 py-2 backdrop-blur-md">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--color-brand-gold)]">
            <motion.span
              animate={{ rotate: 360 }}
              transition={{ duration: 2.5, repeat: Infinity, ease: 'linear' }}
            >
              <Icon name="sparkle" size={14} />
            </motion.span>
            生成中
          </div>
          <span className="font-mono text-[10px] text-[var(--color-text-tertiary)]">
            已输出 {charCount} 字
          </span>
        </div>
      )}

      <div className="px-3 pb-4 pt-3">
        <p className="mb-3 text-[10px] text-[var(--color-text-muted)]">
          流式输出中，章节将随内容逐步呈现（约 1–3 分钟）
        </p>
        <ul className="mb-4 flex flex-wrap gap-1.5">
          {chapters.map((t) => (
            <li
              key={t}
              className="rounded-full border border-white/[0.06] bg-black/25 px-2 py-0.5 text-[9px] text-[var(--color-text-tertiary)]"
            >
              {t}
            </li>
          ))}
        </ul>

        <div className="markdown-report relative min-h-[min(55vh,320px)] max-h-[55vh] overflow-hidden rounded-xl border border-white/[0.05] bg-black/20 text-[14px] leading-relaxed text-violet-100/95 [&_a]:text-[var(--color-brand-gold)] [&_h3]:mt-2 [&_strong]:text-[var(--color-text-primary)]">
          {/* 流式阶段仅遮挡正文区：不展示未排版 Markdown，由父级 state 继续累积 */}
          {!loading && text ? (
            <div className="max-h-[55vh] overflow-y-auto px-3 py-3">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
            </div>
          ) : !loading ? (
            <div className="px-3 py-3">
              <p className="text-xs text-[var(--color-text-muted)]">等待首段内容…</p>
            </div>
          ) : null}

          {loading && (
            <div
              className="absolute inset-0 z-10 flex min-h-[min(55vh,320px)] flex-col items-center justify-center overflow-hidden rounded-xl"
              aria-hidden
            >
              <img
                src={maskBgSrc}
                alt=""
                className={`pointer-events-none absolute inset-0 h-full w-full object-cover ${isCompatibility ? 'report-stream-couple-heartbeat' : 'report-zodiac-heartbeat'}`}
              />
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#08091a]/80 via-[#08091a]/70 to-[#08091a]/86" />

              {/* 轨道环 — 与速测「星盘绘制中」同逻辑，尺寸适配正文卡片 */}
              <motion.div
                className="pointer-events-none absolute left-1/2 top-1/2 z-[2] h-[min(72%,220px)] w-[min(72%,220px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#ffd700]/20"
                animate={{ rotate: 360 }}
                transition={{ duration: 14, repeat: Infinity, ease: 'linear' }}
              />
              <motion.div
                className="pointer-events-none absolute left-1/2 top-1/2 z-[2] h-[min(66%,200px)] w-[min(66%,200px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#a78bfa]/35"
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
              />
              <motion.div
                className="pointer-events-none absolute left-1/2 top-1/2 z-[2] h-[min(58%,175px)] w-[min(58%,175px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-dashed border-[#00e5ff]/28"
                animate={{ rotate: -360 }}
                transition={{ duration: 28, repeat: Infinity, ease: 'linear' }}
              />
              <motion.div
                className="pointer-events-none absolute left-1/2 top-1/2 z-[2] h-[min(50%,150px)] w-[min(50%,150px)] -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#ff2d78]/22"
                animate={{ rotate: -360 }}
                transition={{ duration: 32, repeat: Infinity, ease: 'linear' }}
              />

              {/* 流星划过 — 位移用百分比，相对遮罩容器 */}
              {[0, 1, 2, 3].map((i) => (
                <motion.div
                  key={`stream-meteor-${i}`}
                  className="pointer-events-none absolute left-0 z-[3] h-px w-[min(42%,150px)] origin-left -rotate-[38deg] bg-gradient-to-r from-transparent via-white/90 to-transparent"
                  style={{ top: `${10 + i * 20}%` }}
                  initial={{ opacity: 0, x: '110%' }}
                  animate={{ opacity: [0, 1, 0], x: ['110%', '-20%'] }}
                  transition={{
                    duration: 2.4 + i * 0.35,
                    repeat: Infinity,
                    delay: i * 0.55,
                    ease: 'linear',
                  }}
                />
              ))}

              {STREAM_MASK_PARTICLES.map((p) => (
                <motion.span
                  key={`stream-p-${p.id}`}
                  className={
                    p.streak
                      ? 'pointer-events-none absolute z-[3] rounded-full bg-gradient-to-r from-transparent via-white/80 to-transparent shadow-[0_0_6px_rgba(167,139,250,0.8)]'
                      : 'pointer-events-none absolute z-[3] rounded-full bg-white/70 shadow-[0_0_8px_rgba(167,139,250,0.9)]'
                  }
                  style={{
                    left: p.left,
                    top: p.top,
                    width: p.streak ? (p.wide ? 12 : 8) : p.wide ? 4 : 3,
                    height: p.streak ? 2 : p.wide ? 4 : 3,
                  }}
                  animate={{ opacity: [0.15, 1, 0.15], scale: p.streak ? [0.85, 1.1, 0.85] : [0.6, 1.15, 0.6] }}
                  transition={{ duration: p.duration, repeat: Infinity, delay: p.delay, ease: 'easeInOut' }}
                />
              ))}

              <motion.div
                className="pointer-events-none absolute left-1/2 top-[46%] z-[4] h-[min(35%,120px)] w-[min(35%,120px)] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[radial-gradient(circle,rgba(139,92,246,0.35)_0%,rgba(240,199,94,0.1)_45%,transparent_72%)] blur-md"
                animate={{ scale: [1, 1.08, 1], opacity: [0.55, 0.85, 0.55] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              />

              <div className="relative z-[12] flex flex-col items-center px-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-[var(--color-brand-cyan)]">
                  {maskEyebrow}
                </p>
                <p className="mt-2 max-w-[18rem] text-center font-serif text-xl font-bold text-white drop-shadow-md">
                  {maskTitle}
                </p>
                <p className="mt-4 text-sm font-medium text-[var(--color-brand-gold)]">内容生成中…</p>
                <p className="mt-2 max-w-[16rem] text-center text-[10px] leading-relaxed text-[var(--color-text-muted)]">
                  成稿后将展示完整排版；流式字数仍在累计
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
