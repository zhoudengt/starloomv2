import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getPaymentStatus } from '../api/payment'
import { postSseStream } from '../api/stream'
import { fetchProfile } from '../api/user'
import MarkdownReport from '../components/MarkdownReport'
import ReportCertificateHeader from '../components/ReportCertificateHeader'
import ReportCrossSell from '../components/ReportCrossSell'
import ReportExportActions from '../components/ReportExportActions'
import ReportStreamingLoader from '../components/ReportStreamingLoader'
import { ScoreRing } from '../components/ScoreRing'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { useBirthProfileStore, type BirthProfileGender } from '../stores/birthProfileStore'
import { useUserStore } from '../stores/userStore'
import { SECTION_IMAGES_PERSONALITY, type ReportGender } from '../utils/reportSectionImages'
import { ZODIAC_CN, sunSignFromDate } from '../utils/zodiacCalc'

function formatReportStreamError(e: unknown): string {
  if (!(e instanceof Error)) return '生成失败'
  const raw = e.message
  try {
    const j = JSON.parse(raw) as { detail?: string }
    if (typeof j.detail === 'string') {
      if (j.detail.includes('order_id')) {
        return '请先完成支付，或从「支付完成」页进入后再生成。'
      }
      return j.detail
    }
  } catch {
    /* not JSON */
  }
  if (raw.includes('order_id')) return '请先完成支付，或从支付完成页进入后再生成。'
  return raw
}

export default function ReportPersonality() {
  const [search] = useSearchParams()
  const token = useUserStore((s) => s.token)
  const auto = search.get('auto') === '1'
  const orderId = search.get('order_id') ?? ''
  const pack = (search.get('pack') || '').toLowerCase()
  const isDlc = pack === 'career' || pack === 'love' || pack === 'growth'
  const dlcTitle =
    pack === 'career' ? '职场深潜包' : pack === 'love' ? '恋爱深潜包' : pack === 'growth' ? '成长深潜包' : ''

  const birthDate = useBirthProfileStore((s) => s.birthDate)
  const birthTime = useBirthProfileStore((s) => s.birthTime)
  const gender = useBirthProfileStore((s) => s.gender)
  const setBirthDate = useBirthProfileStore((s) => s.setBirthDate)
  const setBirthTime = useBirthProfileStore((s) => s.setBirthTime)
  const setGender = useBirthProfileStore((s) => s.setGender)
  const applyFromProfile = useBirthProfileStore((s) => s.applyFromProfile)
  const applyFromExtras = useBirthProfileStore((s) => s.applyFromExtras)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [doneId, setDoneId] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const autoKickoff = useRef(false)

  useEffect(() => {
    void fetchProfile()
      .then((p) => applyFromProfile(p))
      .catch(() => {})
  }, [applyFromProfile])

  const runStream = useCallback(
    async (bd: string, bt: string, g: string) => {
      if (!token) {
        setErr('请先打开首页完成登录')
        return
      }
      setErr(null)
      setLoading(true)
      setText('')
      setDoneId(null)
      try {
        const bp = useBirthProfileStore.getState()
        await postSseStream(
          '/report/personality',
          {
            birth_date: bd,
            birth_time: bt || undefined,
            gender: g || undefined,
            birth_place_name: bp.birthPlaceName || undefined,
            birth_place_lat: bp.birthPlaceLat ?? undefined,
            birth_place_lon: bp.birthPlaceLon ?? undefined,
            birth_tz: bp.birthTz || undefined,
            order_id: orderId || undefined,
          },
          token,
          {
            onContent: (t) => setText((prev) => prev + t),
            onDone: (id) => setDoneId(id),
          },
        )
      } catch (e: unknown) {
        setErr(formatReportStreamError(e))
      } finally {
        setLoading(false)
      }
    },
    [token, orderId],
  )

  const runDlcStream = useCallback(
    async (bd: string, bt: string, g: string, oid: string) => {
      if (!token) {
        setErr('请先打开首页完成登录')
        return
      }
      setErr(null)
      setLoading(true)
      setText('')
      setDoneId(null)
      try {
        const bp = useBirthProfileStore.getState()
        await postSseStream(
          '/report/personality-dlc',
          {
            pack,
            birth_date: bd,
            birth_time: bt || undefined,
            gender: g || undefined,
            birth_place_name: bp.birthPlaceName || undefined,
            birth_place_lat: bp.birthPlaceLat ?? undefined,
            birth_place_lon: bp.birthPlaceLon ?? undefined,
            birth_tz: bp.birthTz || undefined,
            order_id: oid,
          },
          token,
          {
            onContent: (t) => setText((prev) => prev + t),
            onDone: (id) => setDoneId(id),
          },
        )
      } catch (e: unknown) {
        setErr(formatReportStreamError(e))
      } finally {
        setLoading(false)
      }
    },
    [token, pack],
  )

  useEffect(() => {
    if (!auto || !orderId || !token || autoKickoff.current) return
    autoKickoff.current = true
    ;(async () => {
      try {
        const s = await getPaymentStatus(orderId)
        if (s.status !== 'paid') {
          autoKickoff.current = false
          return
        }
        const ex = s.extra_data ?? {}
        const bd = typeof ex.birth_date === 'string' ? ex.birth_date : '1995-06-15'
        const bt = typeof ex.birth_time === 'string' ? ex.birth_time : ''
        const g = typeof ex.gender === 'string' ? ex.gender : ''
        applyFromExtras({ ...ex, birth_date: bd, birth_time: bt || undefined, gender: g || undefined })
        if (isDlc) {
          await runDlcStream(bd, bt, g, orderId)
        } else {
          await runStream(bd, bt, g)
        }
      } catch {
        autoKickoff.current = false
        setErr('自动拉取订单信息失败')
      }
    })()
  }, [auto, orderId, token, runStream, runDlcStream, isDlc, applyFromExtras])

  const onManualRun = () => {
    if (isDlc) {
      if (!orderId) {
        setErr('请从支付完成页进入，或先购买对应拓展包')
        return
      }
      void runDlcStream(birthDate, birthTime, gender, orderId)
      return
    }
    void runStream(birthDate, birthTime, gender)
  }

  const shareSnippet = () => {
    if (!text.trim()) return
    const slice = text.slice(0, 280)
    if (navigator.share) {
      void navigator.share({ title: 'StarLoom 性格报告', text: slice })
    } else {
      void navigator.clipboard.writeText(slice)
      alert('已复制摘要到剪贴板')
    }
  }

  const genLabel = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  const signCn = ZODIAC_CN[sunSignFromDate(birthDate)]
  const exportTitle = isDlc ? `性格报告 · ${dlcTitle}` : '个人性格分析报告'

  return (
    <>
      <StarryBackground />
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--color-brand-gold)]"
      >
        ← 返回
      </Link>
      <h1 className="font-serif text-2xl text-[var(--color-brand-gold)]">
        {isDlc ? `性格报告 · ${dlcTitle}` : '个人性格分析报告'}
      </h1>
      <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-tertiary)]">
        AI 实时流式生成；完成后可折叠阅读。支付订单信息可自动带入。
      </p>

      <div className="relative mt-5 overflow-hidden rounded-2xl border border-[var(--color-brand-violet)]/25">
        <img
          src={
            gender === 'female'
              ? '/illustrations/personality-hero-female.png'
              : gender === ''
                ? '/illustrations/personality-hero-neutral.png'
                : '/illustrations/personality-hero.png'
          }
          alt=""
          className="h-40 w-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14]/90 via-transparent to-transparent" />
        <p className="absolute bottom-3 left-4 text-xs font-medium text-white/90 drop-shadow">
          深度性格 · 七章结构
        </p>
      </div>

      <div className="card-elevated mt-6 space-y-3 p-4 text-sm">
        <label className="block">
          <span className="text-[var(--color-text-secondary)]">出生日期</span>
          <input
            className="input-cosmic mt-1"
            value={birthDate}
            onChange={(e) => setBirthDate(e.target.value)}
            type="date"
          />
        </label>
        <label className="block">
          <span className="text-[var(--color-text-secondary)]">出生时间（可选）</span>
          <input
            className="input-cosmic mt-1"
            value={birthTime}
            onChange={(e) => setBirthTime(e.target.value)}
            type="time"
          />
        </label>
        <label className="block">
          <span className="text-[var(--color-text-secondary)]">性别（可选）</span>
          <select
            className="input-cosmic mt-1"
            value={gender}
            onChange={(e) => setGender(e.target.value as BirthProfileGender)}
          >
            <option value="">未选择</option>
            <option value="female">女</option>
            <option value="male">男</option>
          </select>
        </label>
        <button
          type="button"
          onClick={onManualRun}
          disabled={loading}
          className="btn-glow relative w-full rounded-xl py-3.5 text-sm font-medium disabled:opacity-50"
        >
          <span className="relative z-[1] font-semibold text-[#0a0b14]">
            {loading ? '生成中…' : '开始生成报告'}
          </span>
        </button>
        <Link
          to={`/payment?product=personality&birth_date=${encodeURIComponent(birthDate)}${gender ? `&gender=${encodeURIComponent(gender)}` : ''}${birthTime ? `&birth_time=${encodeURIComponent(birthTime)}` : ''}`}
          className="flex items-center justify-center gap-1 text-center text-xs text-[var(--color-text-muted)] underline"
        >
          <Icon name="lock" size={12} />
          未支付？去支付 ¥0.10
        </Link>
      </div>

      {err && <p className="mt-4 text-sm text-red-300">{err}</p>}
      {loading && (
        <ReportStreamingLoader
          loading={loading}
          text={text}
          reportType="personality"
          birthDate={birthDate}
          birthTime={birthTime}
          signCn={signCn}
        />
      )}
      {doneId && (
        <p className="mt-2 text-xs text-emerald-300/90">
          报告已保存 ·{' '}
          <Link to="/my-reports" className="underline">
            我的报告
          </Link>
        </p>
      )}

      <div className="mt-8">
        {doneId && text && !loading ? (
          <>
            <div className="mb-4 flex justify-center">
              <ScoreRing score={Math.min(99, 85 + Math.min(14, Math.floor(text.length / 800)))} label="内容充实度" />
            </div>
            <MarkdownReport
              content={text}
              sectionImages={SECTION_IMAGES_PERSONALITY}
              gender={gender as ReportGender}
              usePersonalityCanonicalImages
              header={
                <ReportCertificateHeader
                  badge="StarLoom · Personality"
                  title={exportTitle}
                  lines={[
                    `出生 ${birthDate}${birthTime ? ` · ${birthTime}` : ''}`,
                    `生成时间 ${genLabel}`,
                  ]}
                />
              }
            />
            <ReportExportActions
              reportType="personality"
              signCn={signCn}
              reportTitle={exportTitle}
              contentText={text}
            />
            <div className="mt-6 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => shareSnippet()}
                className="card-base flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2.5 text-sm text-[var(--color-text-primary)]"
              >
                <Icon name="share" size={16} />
                分享摘要
              </button>
            </div>
            <ReportCrossSell exclude="personality" />
            {!isDlc && (
              <div className="mt-6 rounded-2xl border border-[var(--color-brand-violet)]/30 bg-[var(--color-surface-3)]/40 p-4">
                <p className="text-sm font-medium text-[var(--color-text-primary)]">深度拓展包 · 提升 LTV</p>
                <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
                  已读完基础报告？可继续解锁职场 / 恋爱 / 成长专题（各 ¥0.07）
                </p>
                <div className="mt-3 flex flex-col gap-2">
                  {(
                    [
                      ['personality_career', 'career', '职场深潜'],
                      ['personality_love', 'love', '恋爱深潜'],
                      ['personality_growth', 'growth', '成长深潜'],
                    ] as const
                  ).map(([prod, , label]) => (
                    <Link
                      key={prod}
                      to={`/payment?product=${prod}&birth_date=${encodeURIComponent(birthDate)}${gender ? `&gender=${encodeURIComponent(gender)}` : ''}${birthTime ? `&birth_time=${encodeURIComponent(birthTime)}` : ''}`}
                      className="rounded-xl border border-white/10 bg-black/20 px-3 py-2.5 text-center text-sm text-[var(--color-brand-cyan)]"
                    >
                      购买 {label} →
                    </Link>
                  ))}
                </div>
              </div>
            )}
            <Link
              to="/quicktest"
              className="mt-6 block text-center text-xs text-[var(--color-text-muted)] underline-offset-2 hover:underline"
            >
              想帮朋友生成？去免费解读页邀请 TA
            </Link>
          </>
        ) : null}
      </div>
    </>
  )
}
