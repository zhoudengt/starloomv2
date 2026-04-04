import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { createCompatShare } from '../api/growth'
import { getPaymentStatus } from '../api/payment'
import { postSseStream } from '../api/stream'
import { fetchProfile } from '../api/user'
import MarkdownReport from '../components/MarkdownReport'
import ReportCertificateHeader from '../components/ReportCertificateHeader'
import ReportCrossSell from '../components/ReportCrossSell'
import ReportExportActions from '../components/ReportExportActions'
import ReportStreamingLoader from '../components/ReportStreamingLoader'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { useBirthProfileStore } from '../stores/birthProfileStore'
import { useUserStore } from '../stores/userStore'
import { CN_CITY_NAMES } from '../utils/cnCities'
import { SECTION_IMAGES_COMPATIBILITY } from '../utils/reportSectionImages'
import { ZODIAC_CN, sunSignFromDate } from '../utils/zodiacCalc'

type PersonOut = {
  name: string
  birth_date: string
  gender?: string
  birth_time?: string
  birth_place_name?: string
  birth_place_lat?: number
  birth_place_lon?: number
  birth_tz?: string
}

export default function Compatibility() {
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const token = useUserStore((s) => s.token)
  const auto = search.get('auto') === '1'
  const orderId = search.get('order_id') ?? ''

  const p1Date = useBirthProfileStore((s) => s.birthDate)
  const p1Time = useBirthProfileStore((s) => s.birthTime)
  const p1Gender = useBirthProfileStore((s) => s.gender)
  const p1Place = useBirthProfileStore((s) => s.birthPlaceName)
  const p1Lat = useBirthProfileStore((s) => s.birthPlaceLat)
  const p1Lon = useBirthProfileStore((s) => s.birthPlaceLon)
  const p1Tz = useBirthProfileStore((s) => s.birthTz)
  const setBirthDate = useBirthProfileStore((s) => s.setBirthDate)
  const setBirthTime = useBirthProfileStore((s) => s.setBirthTime)
  const setGender = useBirthProfileStore((s) => s.setGender)
  const setBirthPlaceName = useBirthProfileStore((s) => s.setBirthPlaceName)
  const applyFromProfile = useBirthProfileStore((s) => s.applyFromProfile)
  const applyFromExtras = useBirthProfileStore((s) => s.applyFromExtras)

  const [p1Name, setP1Name] = useState('小明')
  const [p2Name, setP2Name] = useState('小红')
  const [p2Date, setP2Date] = useState('1993-11-22')
  const [p2Gender, setP2Gender] = useState('male')
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
    async (p1: PersonOut, p2: PersonOut) => {
      if (!token) {
        setErr('请先打开首页完成登录')
        return
      }
      setErr(null)
      setLoading(true)
      setText('')
      setDoneId(null)
      try {
        await postSseStream(
          '/report/compatibility',
          {
            person1: {
              name: p1.name,
              birth_date: p1.birth_date,
              gender: p1.gender,
              birth_time: p1.birth_time,
              birth_place_name: p1.birth_place_name,
              birth_place_lat: p1.birth_place_lat,
              birth_place_lon: p1.birth_place_lon,
              birth_tz: p1.birth_tz,
            },
            person2: {
              name: p2.name,
              birth_date: p2.birth_date,
              gender: p2.gender,
              birth_time: p2.birth_time,
              birth_place_name: p2.birth_place_name,
              birth_place_lat: p2.birth_place_lat,
              birth_place_lon: p2.birth_place_lon,
              birth_tz: p2.birth_tz,
            },
          },
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
    [token],
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
        type Pin = {
          name?: string
          birth_date?: string
          gender?: string
          birth_time?: string
          birth_place_name?: string
          birth_place_lat?: number
          birth_place_lon?: number
          birth_tz?: string
        }
        const a = ex.person1 as Pin | undefined
        const b = ex.person2 as Pin | undefined
        applyFromExtras({
          birth_date: a?.birth_date,
          birth_time: a?.birth_time,
          gender: a?.gender,
          birth_place_name: a?.birth_place_name,
          birth_place_lat: a?.birth_place_lat,
          birth_place_lon: a?.birth_place_lon,
          birth_tz: a?.birth_tz,
        })
        const st = useBirthProfileStore.getState()
        const p1: PersonOut = {
          name: a?.name ?? '小明',
          birth_date: st.birthDate,
          gender: st.gender || undefined,
          birth_time: st.birthTime || undefined,
          birth_place_name: st.birthPlaceName || undefined,
          birth_place_lat: st.birthPlaceLat ?? undefined,
          birth_place_lon: st.birthPlaceLon ?? undefined,
          birth_tz: st.birthTz || undefined,
        }
        const p2: PersonOut = {
          name: b?.name ?? '小红',
          birth_date: b?.birth_date ?? '1993-11-22',
          gender: b?.gender ?? 'male',
          birth_time: b?.birth_time,
          birth_place_name: b?.birth_place_name,
          birth_place_lat: b?.birth_place_lat,
          birth_place_lon: b?.birth_place_lon,
          birth_tz: b?.birth_tz,
        }
        setP1Name(p1.name)
        setP2Name(p2.name)
        setP2Date(p2.birth_date)
        setP2Gender(p2.gender ?? 'male')
        await runStream(p1, p2)
      } catch {
        autoKickoff.current = false
        setErr('自动拉取订单失败')
      }
    })()
  }, [auto, orderId, token, runStream, applyFromExtras])

  const p1Payload = (): PersonOut => ({
    name: p1Name,
    birth_date: p1Date,
    gender: p1Gender || undefined,
    birth_time: p1Time || undefined,
    birth_place_name: p1Place || undefined,
    birth_place_lat: p1Lat ?? undefined,
    birth_place_lon: p1Lon ?? undefined,
    birth_tz: p1Tz || undefined,
  })

  const onPay = () => {
    const p1 = p1Payload()
    sessionStorage.setItem(
      'starloom_pay_compat',
      JSON.stringify({
        person1: {
          name: p1.name,
          birth_date: p1.birth_date,
          ...(p1.gender ? { gender: p1.gender } : {}),
          ...(p1.birth_time ? { birth_time: p1.birth_time } : {}),
          ...(p1.birth_place_name ? { birth_place_name: p1.birth_place_name } : {}),
          ...(p1.birth_place_lat != null ? { birth_place_lat: p1.birth_place_lat } : {}),
          ...(p1.birth_place_lon != null ? { birth_place_lon: p1.birth_place_lon } : {}),
          ...(p1.birth_tz ? { birth_tz: p1.birth_tz } : {}),
        },
        person2: { name: p2Name, birth_date: p2Date, gender: p2Gender },
      }),
    )
    navigate('/payment?product=compatibility')
  }

  const onRun = () => void runStream(p1Payload(), { name: p2Name, birth_date: p2Date, gender: p2Gender })

  const genLabel = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  const compatSignCn = `${ZODIAC_CN[sunSignFromDate(p1Date)]} × ${ZODIAC_CN[sunSignFromDate(p2Date)]}`

  const splitHeader = (
    <div className="mb-4 flex items-stretch gap-2 rounded-2xl border border-[var(--color-brand-pink)]/30 bg-gradient-to-br from-[var(--color-surface-3)]/85 to-black/50 p-4 backdrop-blur-md">
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="text-[10px] text-[var(--color-text-muted)]">用户 A</p>
        <p className="mt-1 font-serif text-base text-[var(--color-brand-gold)]">{p1Name}</p>
        <p className="mt-1 text-[10px] text-[var(--color-text-secondary)]">{p1Date}</p>
      </div>
      <div className="flex w-10 shrink-0 flex-col items-center justify-center">
        <div className="h-px w-full bg-gradient-to-r from-transparent via-[var(--color-brand-pink)]/60 to-transparent" />
        <Icon name="heart" size={22} className="my-2 text-[var(--color-brand-pink)]" />
        <div className="h-px w-full bg-gradient-to-r from-transparent via-[var(--color-brand-pink)]/60 to-transparent" />
      </div>
      <div className="flex flex-1 flex-col items-center justify-center text-center">
        <p className="text-[10px] text-[var(--color-text-muted)]">用户 B</p>
        <p className="mt-1 font-serif text-base text-[var(--color-brand-gold)]">{p2Name}</p>
        <p className="mt-1 text-[10px] text-[var(--color-text-secondary)]">{p2Date}</p>
      </div>
    </div>
  )

  return (
    <>
      <StarryBackground />
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--color-brand-gold)]"
      >
        ← 返回
      </Link>
      <h1 className="font-serif text-2xl font-medium tracking-tight text-[var(--color-text-primary)]">
        配对分析报告
      </h1>
      <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-secondary)]">
        填写双方信息后生成；支付时可保存信息至订单。
      </p>

      <div className="relative mt-5 overflow-hidden rounded-2xl border border-[var(--color-brand-pink)]/25 shadow-[0_0_32px_rgba(236,72,153,0.12)]">
        <img
          src="/illustrations/compatibility-hero.png"
          alt=""
          className="h-40 w-full object-cover"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14]/90 via-transparent to-transparent" />
        <p className="absolute bottom-3 left-4 text-xs font-medium text-white/90 drop-shadow">
          双人能量 · 合盘解读
        </p>
      </div>

      <div className="card-featured mt-5 rounded-2xl border border-[var(--color-brand-pink)]/25 p-4">
        <p className="flex items-center gap-2 text-sm font-medium text-[var(--color-brand-pink)]">
          <Icon name="share" size={18} />
          拉新钩子 · 双人合盘
        </p>
        <p className="mt-2 text-[11px] leading-relaxed text-[var(--color-text-secondary)]">
          生成前把本页发给 TA，让对方确认生日与称呼；支付成功后双方信息写入订单，可随时在「我的报告」回看。
        </p>
        <button
          type="button"
          className="btn-ghost mt-3 w-full rounded-xl py-2.5 text-xs"
          onClick={() => {
            const url = window.location.href
            void navigator.clipboard.writeText(url).then(
              () => alert('页面链接已复制，发给 TA 一起填写'),
              () => alert(url),
            )
          }}
        >
          复制本页链接邀请 TA
        </button>
        <button
          type="button"
          className="btn-ghost mt-2 w-full rounded-xl py-2.5 text-xs text-[var(--color-brand-cyan)]"
          onClick={() => {
            void createCompatShare({
              person1_name: p1Name,
              person2_name: p2Name,
              preview_score: 87,
            }).then(
              (res) => {
                const shareUrl = `${window.location.origin}/share/compat/${res.token}`
                void navigator.clipboard.writeText(shareUrl).then(
                  () => alert('预览链接已复制，好友打开可看摘要'),
                  () => alert(shareUrl),
                )
              },
              () => alert('生成预览链接失败，请登录后重试'),
            )
          }}
        >
          生成双人预览链接（裂变）
        </button>
      </div>

      <div className="card-elevated mt-6 space-y-4 p-4 text-sm">
        <div className="flex items-stretch gap-2">
          <div className="flex min-w-0 flex-1 flex-col space-y-2">
            <p className="text-center text-[10px] text-[var(--color-text-muted)]">用户 A</p>
            <input
              className="input-cosmic w-full text-sm"
              value={p1Name}
              onChange={(e) => setP1Name(e.target.value)}
              placeholder="称呼"
            />
            <input
              type="date"
              className="input-cosmic w-full text-sm"
              value={p1Date}
              onChange={(e) => setBirthDate(e.target.value)}
            />
            <p className="text-[9px] text-[var(--color-text-muted)]">出生时间（可选）</p>
            <input
              type="time"
              className="input-cosmic w-full text-sm"
              value={p1Time}
              onChange={(e) => setBirthTime(e.target.value)}
            />
            <p className="text-[9px] text-[var(--color-text-muted)]">出生城市（可选）</p>
            <select
              className="input-cosmic w-full text-sm"
              value={p1Place}
              onChange={(e) => setBirthPlaceName(e.target.value)}
            >
              <option value="">默认北京</option>
              {CN_CITY_NAMES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <select className="input-cosmic w-full text-sm" value={p1Gender} onChange={(e) => setGender(e.target.value as 'female' | 'male' | '')}>
              <option value="">未选择</option>
              <option value="female">女</option>
              <option value="male">男</option>
            </select>
          </div>
          <div className="flex w-10 shrink-0 flex-col items-center justify-center py-1">
            <div className="h-px w-full bg-gradient-to-r from-transparent via-[var(--color-brand-pink)]/50 to-transparent" />
            <Icon name="heart" size={22} className="my-2 shrink-0 text-[var(--color-brand-pink)]" />
            <div className="h-px w-full bg-gradient-to-r from-transparent via-[var(--color-brand-pink)]/50 to-transparent" />
          </div>
          <div className="flex min-w-0 flex-1 flex-col space-y-2">
            <p className="text-center text-[10px] text-[var(--color-text-muted)]">用户 B</p>
            <input className="input-cosmic w-full text-sm" value={p2Name} onChange={(e) => setP2Name(e.target.value)} placeholder="称呼" />
            <input
              type="date"
              className="input-cosmic w-full text-sm"
              value={p2Date}
              onChange={(e) => setP2Date(e.target.value)}
            />
            <select className="input-cosmic w-full text-sm" value={p2Gender} onChange={(e) => setP2Gender(e.target.value)}>
              <option value="female">女</option>
              <option value="male">男</option>
            </select>
          </div>
        </div>

        <button
          type="button"
          onClick={onRun}
          disabled={loading}
          className="btn-glow relative w-full rounded-xl py-3 font-medium disabled:opacity-50"
        >
          <span className="relative z-[1] font-semibold text-[#0a0b14]">
            {loading ? '生成中…' : '生成配对报告'}
          </span>
        </button>
        <button
          type="button"
          onClick={onPay}
          className="w-full rounded-xl border border-white/20 py-2.5 text-sm text-[var(--color-text-secondary)]"
        >
          先支付 ¥0.20（保存双方信息）
        </button>
      </div>
      {err && <p className="mt-4 text-sm text-red-300">{err}</p>}
      {loading && (
        <ReportStreamingLoader
          loading={loading}
          text={text}
          reportType="compatibility"
          birthDate={p1Date}
          signCn={compatSignCn}
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
              sectionImages={SECTION_IMAGES_COMPATIBILITY}
              header={
                <>
                  {splitHeader}
                  <ReportCertificateHeader
                    badge="StarLoom · Compatibility"
                    title="配对分析报告"
                    lines={[`${p1Name} × ${p2Name}`, `生成时间 ${genLabel}`]}
                  />
                </>
              }
            />
            <ReportExportActions
              reportType="compatibility"
              signCn={compatSignCn}
              reportTitle="配对分析报告"
              contentText={text}
            />
            <ReportCrossSell exclude="compatibility" />
          </>
        ) : null}
      </div>
    </>
  )
}
