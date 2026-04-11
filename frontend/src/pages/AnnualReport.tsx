import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { getPaymentStatus } from '../api/payment'
import { postSseStream } from '../api/stream'
import { fetchProfile } from '../api/user'
import MarkdownReport from '../components/MarkdownReport'
import ReportCertificateHeader from '../components/ReportCertificateHeader'
import ReportCrossSell from '../components/ReportCrossSell'
import ReportExportActions from '../components/ReportExportActions'
import ReportStreamingLoader from '../components/ReportStreamingLoader'
import { StarryBackground } from '../components/StarryBackground'
import { useBirthProfileStore } from '../stores/birthProfileStore'
import { useUserStore } from '../stores/userStore'
import { usePrice } from '../hooks/usePrices'
import { CN_CITY_NAMES } from '../utils/cnCities'
import { SECTION_IMAGES_ANNUAL, type ReportGender } from '../utils/reportSectionImages'
import {
  allowedAnnualYears,
  CHINESE_ZODIAC_CN,
  chineseZodiacFromYear,
  clampAnnualYear,
  ZODIAC_CN,
  sunSignFromDate,
} from '../utils/zodiacCalc'

export default function AnnualReport() {
  const priceAnnual = usePrice('annual')
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const token = useUserStore((s) => s.token)
  const auto = search.get('auto') === '1'
  const orderId = search.get('order_id') ?? ''

  const birthDate = useBirthProfileStore((s) => s.birthDate)
  const birthTime = useBirthProfileStore((s) => s.birthTime)
  const gender = useBirthProfileStore((s) => s.gender)
  const birthPlaceName = useBirthProfileStore((s) => s.birthPlaceName)
  const setBirthDate = useBirthProfileStore((s) => s.setBirthDate)
  const setBirthTime = useBirthProfileStore((s) => s.setBirthTime)
  const setGender = useBirthProfileStore((s) => s.setGender)
  const setBirthPlaceName = useBirthProfileStore((s) => s.setBirthPlaceName)
  const applyFromProfile = useBirthProfileStore((s) => s.applyFromProfile)
  const applyFromExtras = useBirthProfileStore((s) => s.applyFromExtras)
  const [year, setYear] = useState(() => clampAnnualYear(new Date().getFullYear()))
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamStage, setStreamStage] = useState('')
  const [streamProgress, setStreamProgress] = useState(0)
  const [doneId, setDoneId] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const autoKickoff = useRef(false)

  useEffect(() => {
    void fetchProfile()
      .then((p) => applyFromProfile(p))
      .catch(() => {})
  }, [applyFromProfile])

  const runStream = useCallback(
    async (y: number) => {
      if (!token) {
        setErr('请先打开首页完成登录')
        return
      }
      setErr(null)
      setLoading(true)
      setText('')
      setStreamStage('')
      setStreamProgress(0)
      setDoneId(null)
      try {
        const st = useBirthProfileStore.getState()
        await postSseStream(
          '/report/annual',
          {
            birth_date: st.birthDate,
            year: y,
            birth_time: st.birthTime || undefined,
            birth_place_name: st.birthPlaceName || undefined,
            birth_place_lat: st.birthPlaceLat ?? undefined,
            birth_place_lon: st.birthPlaceLon ?? undefined,
            birth_tz: st.birthTz || undefined,
            order_id: orderId || undefined,
          },
          token,
          {
            onContent: (t) => setText((prev) => prev + t),
            onDone: (id) => setDoneId(id),
            onStage: (s) => setStreamStage(s),
            onProgress: (p) => setStreamProgress(p),
          },
        )
      } catch (e: unknown) {
        setErr(e instanceof Error ? e.message : '生成失败')
      } finally {
        setLoading(false)
      }
    },
    [token, orderId],
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
        const rawY = ex.year
        const y =
          typeof rawY === 'number'
            ? rawY
            : typeof rawY === 'string'
              ? parseInt(rawY, 10)
              : new Date().getFullYear()
        const fy = clampAnnualYear(Number.isFinite(y) ? y : new Date().getFullYear())
        applyFromExtras(ex as Record<string, unknown>)
        setYear(fy)
        await runStream(fy)
      } catch {
        autoKickoff.current = false
        setErr('自动拉取订单失败')
      }
    })()
  }, [auto, orderId, token, runStream, applyFromExtras])

  const onPay = () => {
    const st = useBirthProfileStore.getState()
    const q = new URLSearchParams({
      product: 'annual',
      birth_date: st.birthDate,
      year: String(year),
    })
    if (st.birthTime) q.set('birth_time', st.birthTime)
    if (st.gender) q.set('gender', st.gender)
    if (st.birthPlaceName) q.set('birth_place_name', st.birthPlaceName)
    navigate(`/payment?${q.toString()}`)
  }

  const genLabel = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
  const signCn = ZODIAC_CN[sunSignFromDate(birthDate)]
  const [yAllowed0, yAllowed1] = allowedAnnualYears()
  const zodiacAnimal = chineseZodiacFromYear(year)
  const heroZodiacSrc = `/zodiac-animals/${zodiacAnimal}.png`

  return (
    <>
      <StarryBackground />
      <Link
        to="/"
        className="mb-4 inline-block text-sm text-[var(--color-brand-gold)]"
      >
        ← 返回
      </Link>
      <h1 className="font-serif text-2xl text-[var(--color-brand-gold)]">年度运势参考</h1>
      <p className="mt-2 text-xs text-[var(--color-text-tertiary)]">选择出生日期与年份，生成年度节奏参考。</p>

      <div className="relative mt-5 overflow-hidden rounded-2xl border border-[var(--color-brand-gold)]/20">
        <img src={heroZodiacSrc} alt="" className="h-40 w-full object-cover" loading="lazy" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14]/90 via-transparent to-transparent" />
        <p className="absolute bottom-3 left-4 text-xs font-medium text-white/90 drop-shadow">
          {year} 年 · {CHINESE_ZODIAC_CN[zodiacAnimal]}年 · 四季参考
        </p>
      </div>

      <div className="card-elevated mt-6 space-y-3 p-4 text-sm">
        <div className="grid grid-cols-2 gap-x-3 gap-y-4">
          <label className="block min-w-0">
            <span className="text-[var(--color-text-secondary)]">出生日期</span>
            <p className="mt-0.5 min-h-[2.25rem] text-[10px] leading-snug text-[var(--color-text-muted)]">
              公历日期，用于太阳星座与年运主题
            </p>
            <input
              type="date"
              className="input-cosmic mt-1 w-full min-w-0"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
            />
          </label>
          <label className="block min-w-0">
            <span className="text-[var(--color-text-secondary)]">出生时间（可选）</span>
            <p className="mt-0.5 min-h-[2.25rem] text-[10px] leading-snug text-[var(--color-text-muted)]">
              用于上升点与宫位参考，不填则按当日正午近似
            </p>
            <input
              type="time"
              className="input-cosmic mt-1 w-full min-w-0"
              value={birthTime}
              onChange={(e) => setBirthTime(e.target.value)}
            />
          </label>
          <label className="block min-w-0">
            <span className="text-[var(--color-text-secondary)]">出生城市（可选）</span>
            <p className="mt-0.5 min-h-[2.25rem] text-[10px] leading-snug text-[var(--color-text-muted)]">
              用于经纬度与宫位计算，不选则默认北京
            </p>
            <select
              className="input-cosmic mt-1 w-full min-w-0"
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
          </label>
          <label className="block min-w-0">
            <span className="text-[var(--color-text-secondary)]">性别（可选，影响配图）</span>
            <p className="mt-0.5 min-h-[2.25rem] text-[10px] leading-snug text-[var(--color-text-muted)]">
              影响报告章节插图的性别化配图
            </p>
            <select
              className="input-cosmic mt-1 w-full min-w-0"
              value={gender}
              onChange={(e) => setGender(e.target.value as 'female' | 'male' | '')}
            >
              <option value="">未选择</option>
              <option value="female">女</option>
              <option value="male">男</option>
            </select>
          </label>
        </div>
        <label className="block">
          <span className="text-[var(--color-text-secondary)]">年份（仅今年与明年）</span>
          <select
            className="input-cosmic mt-1"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            <option value={yAllowed0}>
              {yAllowed0} 年（{CHINESE_ZODIAC_CN[chineseZodiacFromYear(yAllowed0)]}年）
            </option>
            <option value={yAllowed1}>
              {yAllowed1} 年（{CHINESE_ZODIAC_CN[chineseZodiacFromYear(yAllowed1)]}年）
            </option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => void runStream(year)}
          disabled={loading}
          className="btn-glow relative w-full rounded-xl py-3 font-medium disabled:opacity-50"
        >
          <span className="relative z-[1] font-semibold text-[#0a0b14]">
            {loading ? '生成中…' : '生成年度报告'}
          </span>
        </button>
        <button
          type="button"
          onClick={onPay}
          className="btn-secondary w-full rounded-xl py-2.5 text-sm"
        >
          先支付 ¥{priceAnnual}（保存出生日期与年份）
        </button>
      </div>
      {err && (
        <div className="mt-4 space-y-2">
          <p className="text-sm text-red-300">{err}</p>
          {text && !doneId && (
            <button
              type="button"
              onClick={() => void runStream(year)}
              className="text-xs text-[var(--color-brand-gold)] underline"
            >
              重试生成
            </button>
          )}
        </div>
      )}
      {loading && (
        <ReportStreamingLoader
          loading={loading}
          text={text}
          reportType="annual"
          birthDate={birthDate}
          signCn={signCn}
          heroSrc={heroZodiacSrc}
          stage={streamStage}
          progress={streamProgress}
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
      {!loading && text && !doneId && err && (
        <div className="mt-4">
          <p className="mb-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200/90">
            以下为中断前已接收的部分内容，完整报告需重新生成。
          </p>
          <MarkdownReport content={text} sectionImages={SECTION_IMAGES_ANNUAL} useAnnualCanonicalImages gender={gender as ReportGender} />
        </div>
      )}
      <div className="mt-8">
        {doneId && text && !loading ? (
          <>
            <MarkdownReport
              content={text}
              sectionImages={SECTION_IMAGES_ANNUAL}
              useAnnualCanonicalImages
              gender={gender as ReportGender}
              header={
                <ReportCertificateHeader
                  badge="StarLoom · Annual"
                  title="年度运势参考报告"
                  lines={[
                    `出生 ${birthDate}${birthTime ? ` · ${birthTime}` : ''}`,
                    `${year} 年 · 生成 ${genLabel}`,
                  ]}
                />
              }
            />
            <ReportExportActions
              reportType="annual"
              signCn={signCn}
              reportTitle="年度运势参考报告"
              contentText={text}
            />
            <ReportCrossSell exclude="annual" />
          </>
        ) : null}
      </div>
    </>
  )
}
