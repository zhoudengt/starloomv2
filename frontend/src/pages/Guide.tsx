import { motion } from 'framer-motion'
import { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useGuideFull, useGuidePreview } from '../api/guide'
import IRRenderer, { IRMetaBar } from '../components/IRRenderer'
import { Icon } from '../components/icons/Icon'
import { isContentIr } from '../types/contentIr'
import { useBirthProfileStore } from '../stores/birthProfileStore'
import { useUserStore } from '../stores/userStore'
import { sunSignFromDate, ZODIAC_CN } from '../utils/zodiacCalc'

const CATEGORIES = [
  { key: 'career', label: '职场星运', icon: 'briefcase' as const, gradient: 'from-blue-500/20 to-blue-800/10' },
  { key: 'wealth', label: '财富密码', icon: 'coin' as const, gradient: 'from-amber-500/20 to-amber-800/10' },
  { key: 'relationship', label: '人际沟通', icon: 'users' as const, gradient: 'from-pink-500/20 to-pink-800/10' },
  { key: 'energy', label: '情绪能量', icon: 'moon' as const, gradient: 'from-violet-500/20 to-violet-800/10' },
]

export default function Guide() {
  const { category: catParam } = useParams<{ category: string }>()
  const category = catParam ?? 'career'
  const navigate = useNavigate()
  const token = useUserStore((s) => s.token)
  const birthDate = useBirthProfileStore((s) => s.birthDate)

  const sign = useMemo(() => {
    if (!birthDate) return undefined
    return sunSignFromDate(birthDate)
  }, [birthDate])
  const signCn = sign ? ZODIAC_CN[sign] : ''

  const { data: fullData, isLoading, error } = useGuideFull(category, sign)
  const { data: previewData } = useGuidePreview(sign)

  const hasAccess = fullData?.has_access ?? previewData?.has_access ?? false
  const catMeta = CATEGORIES.find((c) => c.key === category) ?? CATEGORIES[0]

  const handlePay = () => {
    navigate(`/payment?product=daily_guide`)
  }

  const onCategorySwitch = (key: string) => {
    navigate(`/guide/${key}`, { replace: true })
  }

  if (!sign) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
        <p className="text-lg text-[var(--color-text-primary)]">请先设置你的生日</p>
        <p className="text-sm text-[var(--color-text-secondary)]">我们需要知道你的星座，才能为你生成专属深析</p>
        <Link
          to="/"
          className="mt-2 rounded-xl bg-[var(--color-brand-gold)] px-6 py-2.5 text-sm font-semibold text-[#0a0b14]"
        >
          返回首页
        </Link>
      </div>
    )
  }

  return (
    <>
      <Link
        to="/"
        className="mb-3 inline-flex items-center gap-1 text-sm text-[var(--color-brand-gold)]"
      >
        ← 返回首页
      </Link>

      {/* Header */}
      <div className="mb-5">
        <div className="flex items-center gap-2">
          <Icon name={catMeta.icon} size={20} className="text-[var(--color-brand-gold)]" />
          <h1 className="font-serif text-xl font-medium text-[var(--color-text-primary)]">
            {catMeta.label}
          </h1>
        </div>
        <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
          {signCn} · {fullData?.date ?? previewData?.date ?? ''}
        </p>
        {fullData?.content_row_date &&
          fullData.date &&
          fullData.content_row_date !== fullData.date && (
            <p className="mt-1.5 text-[10px] leading-snug text-amber-200/90">
              今日内容生成中，暂展示 {fullData.content_row_date} 的数据；完成后将自动切换为今日。
            </p>
          )}
        {fullData?.transit_basis && (
          <p className="mt-1.5 inline-block rounded-md bg-white/[0.06] px-2 py-0.5 text-[10px] text-[var(--color-text-muted)]">
            基于：{fullData.transit_basis}
          </p>
        )}
      </div>

      {/* Content area */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--color-brand-gold)] border-t-transparent" />
        </div>
      ) : error && !fullData ? (
        <div className="rounded-xl border border-red-400/20 bg-red-400/5 p-4 text-sm text-red-200">
          内容加载失败，请稍后刷新重试
        </div>
      ) : (
        <div className="relative">
          {/* Preview always visible */}
          {!hasAccess && fullData?.preview && (
            <div className="mb-0 rounded-t-xl border border-b-0 border-white/[0.08] bg-[#0d0e1a] p-4">
              <p className="text-sm leading-relaxed text-[var(--color-text-primary)]">
                {fullData.preview}
              </p>
            </div>
          )}

          {hasAccess && fullData?.content ? (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="prose-guide rounded-xl border border-white/[0.08] bg-[#0d0e1a] p-4"
            >
              {fullData.content_ir && isContentIr(fullData.content_ir) ? (
                <>
                  <IRMetaBar meta={fullData.content_ir.meta} />
                  <IRRenderer blocks={fullData.content_ir.blocks} />
                </>
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {fullData.content}
                </ReactMarkdown>
              )}
            </motion.div>
          ) : !hasAccess ? (
            <>
              {/* Blurred placeholder */}
              <div className="relative overflow-hidden rounded-b-xl border border-t-0 border-white/[0.08] bg-[#0d0e1a]">
                <div className="pointer-events-none select-none p-4 blur-[6px]">
                  <p className="text-sm leading-relaxed text-[var(--color-text-secondary)]">
                    此处为 800-1500 字的深度分析内容，包含具体问题诊断、行动清单、场景示例和关键词指引。每个星座的内容完全不同，基于当日天象实时生成。
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-[var(--color-text-secondary)]">
                    解锁后可查看完整的 4 个维度分析：职场星运、财富密码、人际沟通、情绪能量。所有内容今日有效，助你把握当天最佳行动方向。
                  </p>
                </div>
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0a0b14]/60 to-[#0a0b14]" />
              </div>

              {/* Paywall CTA */}
              <div className="mt-4 rounded-xl border border-[var(--color-brand-gold)]/30 bg-gradient-to-b from-[var(--color-brand-gold)]/[0.08] to-transparent p-5 text-center">
                <p className="font-serif text-lg text-[var(--color-text-primary)]">
                  解锁今日全部深度分析
                </p>
                <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                  含职场 · 财富 · 沟通 · 情绪 4 大维度 · 今日有效
                </p>
                <div className="mt-3 flex items-baseline justify-center gap-1">
                  <span className="text-sm text-[var(--color-text-muted)]">¥</span>
                  <span className="font-mono text-3xl font-semibold text-[var(--color-brand-gold)]">0.40</span>
                </div>
                {token ? (
                  <button
                    type="button"
                    onClick={handlePay}
                    className="btn-glow mt-4 w-full max-w-xs rounded-xl py-3 font-semibold text-[#0a0b14]"
                  >
                    立即解锁
                  </button>
                ) : (
                  <Link
                    to="/profile"
                    className="mt-4 inline-block rounded-xl bg-[var(--color-brand-gold)] px-8 py-3 font-semibold text-[#0a0b14]"
                  >
                    登录后解锁
                  </Link>
                )}
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Category tabs */}
      <div className="mt-6 grid grid-cols-4 gap-2">
        {CATEGORIES.map((cat) => {
          const active = cat.key === category
          return (
            <button
              key={cat.key}
              type="button"
              onClick={() => onCategorySwitch(cat.key)}
              className={`flex flex-col items-center gap-1 rounded-xl border px-2 py-3 text-center transition-all ${
                active
                  ? 'border-[var(--color-brand-gold)]/40 bg-[var(--color-brand-gold)]/10'
                  : 'border-white/[0.06] bg-white/[0.03]'
              }`}
            >
              <Icon
                name={cat.icon}
                size={16}
                className={active ? 'text-[var(--color-brand-gold)]' : 'text-[var(--color-text-muted)]'}
              />
              <span className={`text-[10px] leading-tight ${active ? 'text-[var(--color-brand-gold)]' : 'text-[var(--color-text-secondary)]'}`}>
                {cat.label}
              </span>
              {hasAccess && (
                <span className="text-[8px] text-emerald-400">已解锁</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Tomorrow hook */}
      {hasAccess && (
        <div className="mt-6 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
          <p className="text-xs font-medium text-[var(--color-text-secondary)]">
            明日预告
          </p>
          <p className="mt-1 text-xs text-[var(--color-text-muted)]">
            {signCn}明天的{catMeta.label}将受到新的星体影响，每日内容不重复。明天见 ✦
          </p>
        </div>
      )}

      {/* Markdown styles */}
      <style>{`
        .prose-guide h2 { font-size: 1.1rem; font-weight: 600; color: var(--color-brand-gold); margin: 1.5rem 0 0.5rem; }
        .prose-guide h3 { font-size: 1rem; font-weight: 600; color: var(--color-text-primary); margin: 1.2rem 0 0.4rem; }
        .prose-guide p { font-size: 0.875rem; line-height: 1.7; color: var(--color-text-secondary); margin-bottom: 0.6rem; }
        .prose-guide ul, .prose-guide ol { padding-left: 1.2rem; margin-bottom: 0.6rem; }
        .prose-guide li { font-size: 0.875rem; line-height: 1.7; color: var(--color-text-secondary); margin-bottom: 0.3rem; }
        .prose-guide strong { color: var(--color-text-primary); }
        .prose-guide hr { border-color: rgba(255,255,255,0.06); margin: 1.2rem 0; }
      `}</style>
    </>
  )
}
