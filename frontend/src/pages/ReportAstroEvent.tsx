import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getPaymentStatus } from '../api/payment'
import { postSseStream } from '../api/stream'
import { fetchProfile } from '../api/user'
import MarkdownReport from '../components/MarkdownReport'
import ReportCertificateHeader from '../components/ReportCertificateHeader'
import ReportExportActions from '../components/ReportExportActions'
import ReportStreamingLoader from '../components/ReportStreamingLoader'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { useUserStore } from '../stores/userStore'
import { SECTION_IMAGES_ASTRO_EVENT, type ReportGender } from '../utils/reportSectionImages'
import { ZODIAC_CN, sunSignFromDate } from '../utils/zodiacCalc'

export default function ReportAstroEvent() {
  const [search] = useSearchParams()
  const token = useUserStore((s) => s.token)
  const auto = search.get('auto') === '1'
  const orderId = search.get('order_id') ?? ''
  const eventKey = search.get('event_key') || 'mercury_retrograde'

  const [birthDate, setBirthDate] = useState('1995-06-15')
  const [gender, setGender] = useState('')
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [doneId, setDoneId] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const autoKickoff = useRef(false)

  useEffect(() => {
    fetchProfile()
      .then((p) => {
        if (p.birth_date) setBirthDate(p.birth_date)
        if (p.gender && p.gender !== 'unknown') setGender(p.gender)
      })
      .catch(() => {})
  }, [])

  const run = useCallback(
    async (bd: string, oid: string) => {
      if (!token) {
        setErr('请先登录')
        return
      }
      setErr(null)
      setLoading(true)
      setText('')
      setDoneId(null)
      try {
        await postSseStream(
          '/report/astro-event',
          { birth_date: bd, event_key: eventKey, order_id: oid },
          token,
          {
            onContent: (t) => setText((prev) => prev + t),
            onDone: (id) => setDoneId(id),
          },
        )
      } catch (e: unknown) {
        setErr(e instanceof Error ? e.message : '生成失败')
      } finally {
        setLoading(false)
      }
    },
    [token, eventKey],
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
        const bd = typeof ex.birth_date === 'string' ? ex.birth_date : birthDate
        const g = typeof ex.gender === 'string' ? ex.gender : ''
        setBirthDate(bd)
        if (g) setGender(g)
        await run(bd, orderId)
      } catch {
        autoKickoff.current = false
        setErr('拉取订单失败')
      }
    })()
  }, [auto, orderId, token, run])

  const genLabel = new Date().toLocaleString('zh-CN')
  const signCn = ZODIAC_CN[sunSignFromDate(birthDate)]

  return (
    <>
      <StarryBackground />
      <Link to="/" className="mb-4 inline-flex gap-1 text-sm text-[var(--color-brand-gold)]">
        ← 返回
      </Link>
      <h1 className="font-serif text-2xl text-[var(--color-brand-gold)]">天象事件参考</h1>
      <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">基于天文历法的性格与节奏参考，非占卜。</p>

      <div className="relative mt-5 overflow-hidden rounded-2xl border border-cyan-500/20">
        <img
          src="/illustrations/astro-event.png"
          alt=""
          className="h-40 w-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14]/90 via-transparent to-transparent" />
        <p className="absolute bottom-3 left-4 text-xs font-medium text-white/90 drop-shadow">天象节奏 · 参考分析</p>
      </div>

      <div className="card-elevated mt-6 space-y-3 p-4 text-sm">
        <label className="block">
          <span className="text-[var(--color-text-secondary)]">出生日期</span>
          <input
            className="input-cosmic mt-1"
            type="date"
            value={birthDate}
            onChange={(e) => setBirthDate(e.target.value)}
          />
        </label>
        <label className="block">
          <span className="text-[var(--color-text-secondary)]">性别（可选，影响配图）</span>
          <select className="input-cosmic mt-1" value={gender} onChange={(e) => setGender(e.target.value)}>
            <option value="">未选择</option>
            <option value="female">女</option>
            <option value="male">男</option>
          </select>
        </label>
        <button
          type="button"
          disabled={loading || !orderId}
          onClick={() => orderId && run(birthDate, orderId)}
          className="btn-glow relative w-full rounded-xl py-3 text-sm font-medium disabled:opacity-50"
        >
          生成
        </button>
        <Link
          to={`/payment?product=astro_event&birth_date=${encodeURIComponent(birthDate)}&event_key=${encodeURIComponent(eventKey)}`}
          className="flex justify-center gap-1 text-xs text-[var(--color-text-muted)] underline"
        >
          <Icon name="lock" size={12} />
          未支付？¥0.10
        </Link>
      </div>

      {err && <p className="mt-4 text-sm text-red-300">{err}</p>}
      {loading && (
        <ReportStreamingLoader
          loading={loading}
          text={text}
          reportType="astro_event"
          birthDate={birthDate}
          signCn={signCn}
        />
      )}
      {doneId && (
        <p className="mt-2 text-xs text-emerald-300/90">
          已保存 ·{' '}
          <Link to="/my-reports" className="underline">
            我的报告
          </Link>
        </p>
      )}

      <div className="mt-8">
        {doneId && text && !loading ? (
          <>
            <MarkdownReport
              content={text}
              sectionImages={SECTION_IMAGES_ASTRO_EVENT}
              gender={gender as ReportGender}
              header={
                <ReportCertificateHeader
                  badge="StarLoom · Astro"
                  title="天象事件参考"
                  lines={[`事件 ${eventKey}`, `生成 ${genLabel}`]}
                />
              }
            />
            <ReportExportActions
              reportType="astro_event"
              signCn={signCn}
              reportTitle="天象事件参考"
              contentText={text}
            />
          </>
        ) : null}
      </div>
    </>
  )
}
