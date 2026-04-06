import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useRef } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { createPayment, getPaymentStatus, getPendingPayment } from '../api/payment'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { useStarloomHydrated } from '../hooks/useStarloomHydrated'
import { useUserStore } from '../stores/userStore'
import { chineseZodiacFromYear } from '../utils/zodiacCalc'

const PRODUCTS: Record<string, { amount: number; label: string; sub: string }> = {
  personality: { amount: 0.1, label: '个人性格报告', sub: '7 章深度结构 · 流式生成 · 可回看' },
  compatibility: { amount: 0.2, label: '配对分析', sub: '双人视角 · 相处与沟通建议' },
  annual: { amount: 0.3, label: '年度运势', sub: '七章结构 · 全年节奏与月度提示' },
  chat: { amount: 0.1, label: 'AI 顾问对话', sub: '星座情绪陪伴' },
  personality_career: { amount: 0.07, label: '性格报告 · 职场深潜包', sub: '职业适配 · 协作与领导力' },
  personality_love: { amount: 0.07, label: '性格报告 · 恋爱深潜包', sub: '亲密关系模式与沟通建议' },
  personality_growth: { amount: 0.07, label: '性格报告 · 成长深潜包', sub: '人生课题与突破方向' },
  astro_event: { amount: 0.1, label: '天象事件参考', sub: '水逆/食相等天文节奏分析' },
  season_pass: { amount: 0.13, label: '星运月卡', sub: '30 天深度运势与专属内容' },
}

/** Optional hero art per product for checkout card */
const PRODUCT_HERO: Partial<Record<string, string>> = {
  personality: '/illustrations/personality-hero.png',
  compatibility: '/illustrations/compatibility-hero.png',
  chat: '/illustrations/chat-advisor.png',
  personality_career: '/illustrations/personality-hero.png',
  personality_love: '/illustrations/personality-hero.png',
  personality_growth: '/illustrations/personality-hero.png',
  astro_event: '/illustrations/astro-event.png',
  season_pass: '/illustrations/season-moon.png',
}

const PREVIEW_CHAPTERS: Record<string, string[]> = {
  personality: ['核心性格与优势', '情感与亲密关系', '事业财富节奏', '… 共 7 章'],
  compatibility: ['缘分指数', '你们的化学反应', '双人能量与节奏', '… 共 6 章'],
  annual: ['整体基调', '事业与学业', '感情与人际', '… 共 7 章'],
  chat: ['多轮对话', '即时回应', '情绪与星座视角陪伴'],
  personality_career: ['职场定位与优势', '团队协作与同事关系', '领导力与向上沟通'],
  personality_love: ['恋爱模式与需求', '理想伴侣画像', '感情雷区与修复'],
  personality_growth: ['人生课题梳理', '突破方向与习惯', '隐藏天赋与行动清单'],
  astro_event: ['天象背景说明', '可能感受与节奏', '行动与复盘建议'],
  season_pass: ['每日深度运势', '每周关键提醒', '月末复盘与角色卡收集'],
}

function buildExtraData(product: string, search: URLSearchParams): Record<string, unknown> | undefined {
  if (product === 'personality') {
    const o: Record<string, unknown> = {}
    const bd = search.get('birth_date')
    if (bd) o.birth_date = bd
    const g = search.get('gender')
    if (g) o.gender = g
    const bt = search.get('birth_time')
    if (bt) o.birth_time = bt
    return Object.keys(o).length ? o : undefined
  }
  if (product === 'annual') {
    const o: Record<string, unknown> = {}
    const bd = search.get('birth_date')
    if (bd) o.birth_date = bd
    const y = search.get('year')
    if (y) o.year = Number(y)
    const bt = search.get('birth_time')
    if (bt) o.birth_time = bt
    const g = search.get('gender')
    if (g) o.gender = g
    const bp = search.get('birth_place_name')
    if (bp) o.birth_place_name = bp
    return Object.keys(o).length ? o : undefined
  }
  if (product === 'astro_event') {
    const o: Record<string, unknown> = {}
    const bd = search.get('birth_date')
    if (bd) o.birth_date = bd
    const ek = search.get('event_key')
    if (ek) o.event_key = ek
    return Object.keys(o).length ? o : undefined
  }
  if (product === 'compatibility') {
    try {
      const raw = sessionStorage.getItem('starloom_pay_compat')
      if (raw) return JSON.parse(raw) as Record<string, unknown>
    } catch {
      /* ignore */
    }
  }
  return undefined
}

const PAY_POLL_MS = 2000
const PAY_POLL_MAX = 150

function isMobileUa(): boolean {
  if (typeof navigator === 'undefined') return false
  return /Mobile|Android|iPhone/i.test(navigator.userAgent)
}

function isWeChatUa(): boolean {
  if (typeof navigator === 'undefined') return false
  return /MicroMessenger/i.test(navigator.userAgent)
}

export default function Payment() {
  const hydrated = useStarloomHydrated()
  const token = useUserStore((s) => s.token)
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const pollAttempts = useRef(0)
  const product = search.get('product') ?? 'personality'
  const cfg = PRODUCTS[product] ?? PRODUCTS.personality
  /** 当前仅签约微信支付，支付宝入口隐藏 */
  const method: 'wechat' = 'wechat'
  const canPay = hydrated && !!token

  const extraData = useMemo(() => {
    const base = buildExtraData(product, search) ?? {}
    const g = search.get('group')
    if (g) return { ...base, group_public_id: g }
    return Object.keys(base).length ? base : undefined
  }, [product, search])

  const payAmount = useMemo(() => {
    const g = search.get('group')
    if (g && (product === 'compatibility' || product === 'personality')) {
      return Math.round(cfg.amount * 0.7 * 100) / 100
    }
    return cfg.amount
  }, [cfg.amount, product, search])

  const mutation = useMutation({
    mutationFn: () =>
      createPayment({
        product_type: product in PRODUCTS ? product : 'personality',
        amount: payAmount,
        pay_method: method,
        extra_data: extraData,
      }),
  })

  const mobile = useMemo(() => isMobileUa(), [])
  const weChat = useMemo(() => isWeChatUa(), [])

  const { data: pendingData } = useQuery({
    queryKey: ['paymentPending', product, token],
    queryFn: () => getPendingPayment(product in PRODUCTS ? product : 'personality'),
    enabled: hydrated && !!token && !mutation.data,
    staleTime: 20_000,
  })

  const hint = useMemo(() => mutation.error?.message, [mutation.error])

  /** 电脑扫码：手机付完后本页不会自动跳转，轮询订单状态并在已支付时进入结果页 */
  const pendingOrderId = mutation.data?.order_id
  useEffect(() => {
    if (!pendingOrderId || !token) return
    pollAttempts.current = 0
    const t = window.setInterval(() => {
      pollAttempts.current += 1
      if (pollAttempts.current > PAY_POLL_MAX) {
        window.clearInterval(t)
        return
      }
      void getPaymentStatus(pendingOrderId)
        .then((s) => {
          if (s.status === 'paid') {
            window.clearInterval(t)
            navigate(`/payment/result?order_id=${encodeURIComponent(pendingOrderId)}`, { replace: true })
          }
        })
        .catch(() => {})
    }, PAY_POLL_MS)
    return () => window.clearInterval(t)
  }, [pendingOrderId, token, navigate])

  /** 年度运势：横幅用当前公历年的生肖图（新年自动切换），与其它入口一致 */
  const productHeroSrc = useMemo(() => {
    const base = PRODUCT_HERO[product]
    if (product === 'annual') {
      return `/zodiac-animals/${chineseZodiacFromYear(new Date().getFullYear())}.png`
    }
    return base
  }, [product])

  const onPay = () => {
    mutation.mutate(undefined, {
      onSuccess: (data) => {
        if (data.order_id) {
          try {
            sessionStorage.setItem('starloom_pay_order_id', data.order_id)
            localStorage.setItem('starloom_pay_order_id', data.order_id)
          } catch {
            /* ignore */
          }
        }
        const jump = data.url
        const qr = data.url_qrcode
        // PC 有扫码图时留在本页；其余场景用 replace 跳转收银台。微信内异步跳转易被拦截，下方保留 <a> 兜底。
        if (!mobile && qr) {
          /* 二维码在下方展示 */
        } else if (jump) {
          window.location.replace(jump)
        }
      },
    })
  }

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
        确认支付
      </h1>
      <p className="mt-1 text-xs text-[var(--color-text-muted)]">单次付费 · 无自动续费 · 支付成功后即时生成</p>

      {pendingData?.order_id && !mutation.data && (
        <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100/95">
          <p className="leading-snug">
            检测到本商品有一笔待支付订单。若已在微信付款，请直接查看支付状态，避免重复付款。
          </p>
          <Link
            to={`/payment/result?order_id=${encodeURIComponent(pendingData.order_id)}&auto=1`}
            className="mt-2 inline-block font-medium text-[var(--color-brand-gold)] underline underline-offset-2"
          >
            查看支付状态
          </Link>
        </div>
      )}

      <div className="card-featured relative mt-6 overflow-hidden p-5">
        {productHeroSrc ? (
          <div className="relative -mx-1 mb-4 overflow-hidden rounded-xl border border-white/10">
            <img
              src={productHeroSrc}
              alt=""
              className="h-28 w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#0a0b14]/85 to-transparent" />
          </div>
        ) : null}
        <p className="text-[10px] tracking-widest text-[var(--color-text-muted)]">本次购买</p>
        <p className="mt-2 font-serif text-lg text-[var(--color-text-primary)]">{cfg.label}</p>
        <p className="mt-1 text-xs text-[var(--color-text-secondary)]/90">{cfg.sub}</p>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
          <div className="flex items-baseline gap-1">
            <span className="text-sm text-[var(--color-text-muted)]">¥</span>
            <span className="font-mono text-3xl font-semibold text-[var(--color-brand-gold)]">
              {payAmount.toFixed(2)}
            </span>
          </div>
          {product === 'annual' && (
            <p className="max-w-[200px] text-right text-[10px] leading-snug text-[var(--color-text-tertiary)]">
              年度报告覆盖更长周期，相比多次单篇购买更省心
            </p>
          )}
        </div>

        <div className="mt-5 rounded-xl border border-white/[0.08] bg-[#08091a]/90 p-3">
          <p className="text-[10px] text-[var(--color-text-muted)]">内容结构预览</p>
          <ul className="mt-2 space-y-1.5">
            {(PREVIEW_CHAPTERS[product] ?? PREVIEW_CHAPTERS.personality).map((line) => (
              <li key={line} className="flex items-center gap-2 text-[11px] text-[var(--color-text-secondary)]">
                <span className="h-1 w-1 shrink-0 rounded-full bg-[var(--color-brand-gold)]/70" />
                {line}
              </li>
            ))}
          </ul>
        </div>

        {extraData && Object.keys(extraData).length > 0 && (
          <p className="mt-4 flex items-start gap-2 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200/90">
            <Icon name="sparkle" size={14} className="mt-0.5 shrink-0" />
            已携带填写的信息，支付成功后将自动用于生成报告。
          </p>
        )}
      </div>

      <div className="mt-6 flex flex-wrap justify-center gap-x-5 gap-y-2 text-[10px] text-[var(--color-text-secondary)]">
        <span className="flex items-center gap-1">
          <Icon name="lock" size={12} className="text-[var(--color-brand-gold)]/80" /> 聚合支付通道
        </span>
        <span className="flex items-center gap-1">
          <Icon name="sparkle" size={12} className="text-[var(--color-brand-gold)]/80" /> 支付成功即时生成
        </span>
        <span className="flex items-center gap-1 text-[var(--color-text-muted)]">满意再继续探索其他报告</span>
      </div>

      <div className="card-elevated mt-6 space-y-4 p-4">
        <p className="text-sm text-[var(--color-text-secondary)]">支付方式</p>
        <div className="rounded-xl border border-white/10 bg-black/30 p-1">
          <div className="relative flex w-full rounded-lg py-2.5 text-center text-sm font-medium text-[#0a0b14]">
            <span className="absolute inset-0 rounded-lg bg-[var(--color-brand-gold)]" />
            <span className="relative z-[1] w-full">微信支付</span>
          </div>
        </div>
        {!canPay && (
          <p className="text-center text-xs text-[var(--color-text-muted)]">
            {!hydrated ? '正在同步本地账号…' : '正在连接账号…'}
          </p>
        )}
        <button
          type="button"
          onClick={onPay}
          disabled={mutation.isPending || !canPay}
          className="btn-glow relative w-full rounded-xl py-3.5 font-medium disabled:opacity-50"
        >
          <span className="relative z-[1] font-semibold text-[#0a0b14]">
            {mutation.isPending ? '创建订单中…' : '去支付'}
          </span>
        </button>
        {hint && <p className="text-sm text-red-300">{hint}</p>}
        {mutation.data?.url && (mobile || weChat || !mutation.data.url_qrcode) && (
          <a
            href={mutation.data.url}
            rel="noopener noreferrer"
            className="block rounded-xl border border-[var(--color-brand-gold)]/40 bg-[var(--color-brand-gold)]/10 py-3 text-center text-sm font-medium text-[var(--color-brand-gold)]"
          >
            若未自动跳转，点此前往微信支付
          </a>
        )}
        {mutation.data?.url_qrcode && (
          <div className="mt-2 space-y-2">
            <p className="text-center text-[10px] text-[var(--color-text-muted)]">电脑端可扫码支付</p>
            <p className="text-center text-[10px] leading-snug text-[var(--color-text-tertiary)]">
              手机微信扫码完成付款后，本页会定时检测支付状态并跳转结果；也可点下方手动进入。
            </p>
            <img
              src={mutation.data.url_qrcode}
              alt="支付二维码"
              className="mx-auto max-h-48 rounded-lg border border-white/10 bg-white p-2"
            />
            {mutation.data.order_id ? (
              <Link
                to={`/payment/result?order_id=${encodeURIComponent(mutation.data.order_id)}&auto=1`}
                className="block text-center text-xs text-[var(--color-brand-gold)] underline"
              >
                我已在手机完成支付，进入结果页
              </Link>
            ) : null}
          </div>
        )}
      </div>
    </>
  )
}
