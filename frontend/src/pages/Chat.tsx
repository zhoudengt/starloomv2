import { motion } from 'framer-motion'
import { useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { postSseStream } from '../api/stream'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { useUserStore } from '../stores/userStore'

type Msg = { role: 'user' | 'assistant'; text: string }

const QUICK = [
  { text: '今日运势要注意什么？', icon: 'sparkle' as const },
  { text: '和处女座相处有什么建议？', icon: 'heart' as const },
  { text: '最近事业压力大怎么办？', icon: 'briefcase' as const },
]

function TypingBubble() {
  return (
    <div className="inline-flex max-w-[85%] rounded-2xl rounded-bl-md border border-white/10 bg-white/5 px-4 py-3">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-2 w-2 rounded-full bg-[var(--color-brand-gold)]/70"
            animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
            transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    </div>
  )
}

function friendlyChatError(e: unknown): string {
  if (!(e instanceof Error)) return '暂时无法连接顾问，请稍后重试。'
  const raw = e.message
  try {
    const j = JSON.parse(raw) as { detail?: string }
    if (j.detail?.includes('order_id')) {
      return '请先购买对话套餐，或从「支付完成」页进入本页（需携带订单）。'
    }
    if (j.detail) return j.detail
  } catch {
    /* not JSON */
  }
  if (raw.includes('order_id')) return '请先购买对话，或从支付完成页进入。'
  return raw || '暂时无法连接顾问，请稍后重试。'
}

export default function Chat() {
  const [search] = useSearchParams()
  const orderId = (search.get('order_id') ?? '').trim()
  const token = useUserStore((s) => s.token)
  const [input, setInput] = useState('')
  const [focused, setFocused] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const send = async (text: string) => {
    const t = text.trim()
    if (!token || !t) return
    setMessages((m) => [...m, { role: 'user', text: t }])
    setInput('')
    setLoading(true)
    let acc = ''
    setMessages((m) => [...m, { role: 'assistant', text: '' }])
    try {
      await postSseStream(
        '/chat',
        { message: t, ...(orderId ? { order_id: orderId } : {}) },
        token,
        {
        onContent: (chunk) => {
          acc += chunk
          setMessages((m) => {
            const next = [...m]
            const last = next[next.length - 1]
            if (last?.role === 'assistant') {
              next[next.length - 1] = { role: 'assistant', text: acc }
            }
            return next
          })
        },
      },
      )
    } catch (err) {
      const msg = friendlyChatError(err)
      setMessages((m) => {
        const next = [...m]
        const last = next[next.length - 1]
        if (last?.role === 'assistant' && !last.text) {
          next[next.length - 1] = { role: 'assistant', text: msg }
        }
        return next
      })
    } finally {
      setLoading(false)
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    }
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
      <div className="relative overflow-hidden rounded-2xl border border-[var(--color-brand-gold)]/25 bg-gradient-to-br from-[#1a103c]/80 to-[#0a0b14] p-4">
        <img
          src="/illustrations/chat-advisor.png"
          alt=""
          className="pointer-events-none absolute -right-4 -top-4 h-32 w-32 object-contain opacity-90"
        />
        <div className="relative pr-24">
          <span className="inline-flex rounded-full bg-[var(--color-brand-gold)]/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[var(--color-brand-gold)]">
            AI
          </span>
          <h1 className="mt-2 font-serif text-2xl text-[var(--color-brand-gold)]">AI 星座顾问</h1>
          <p className="mt-2 text-xs leading-relaxed text-[var(--color-text-tertiary)]">
            {orderId
              ? '已关联本笔订单，可直接对话（正式环境需先完成支付）。'
              : '未携带订单时，正式环境需先购买对话；演示模式可在后端开启后免单。'}
          </p>
        </div>
      </div>

      <div className="mt-4 flex max-h-[48vh] flex-col gap-3 overflow-y-auto rounded-2xl border border-white/10 bg-black/25 p-3 backdrop-blur-sm">
        {messages.length === 0 && (
          <p className="py-10 text-center text-sm text-[var(--color-text-muted)]">选一个快捷问题，或直接输入</p>
        )}
        {messages.map((m, i) => {
          if (m.role === 'assistant' && !m.text && loading && i === messages.length - 1) {
            return (
              <div key={i} className="flex justify-start gap-2">
                <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-[var(--color-brand-gold)]/35 bg-[var(--color-surface-3)]/60">
                  <img src="/illustrations/chat-advisor.png" alt="" className="h-full w-full object-cover" />
                </div>
                <TypingBubble />
              </div>
            )
          }
          return (
            <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {m.role === 'assistant' && (
                <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-[var(--color-brand-gold)]/35 bg-[var(--color-surface-3)]/60">
                  <img src="/illustrations/chat-advisor.png" alt="" className="h-full w-full object-cover" />
                </div>
              )}
              <div
                className={`relative max-w-[82%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                  m.role === 'user'
                    ? 'rounded-br-md bg-gradient-to-br from-[var(--color-brand-gold)]/35 to-[var(--color-brand-gold)]/15 text-[var(--color-text-primary)] shadow-[var(--shadow-glow-gold)]'
                    : 'rounded-bl-md border border-white/10 bg-white/5 text-[var(--color-text-primary)]/95'
                }`}
              >
                {m.role === 'assistant' && (
                  <span className="mb-1 block text-[10px] font-medium tracking-wide text-[var(--color-text-muted)]">
                    星织
                  </span>
                )}
                {m.text}
              </div>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>

      <div className="mt-3 flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {QUICK.map((q) => (
          <motion.button
            key={q.text}
            type="button"
            whileTap={{ scale: 0.96 }}
            disabled={loading || !token}
            onClick={() => void send(q.text)}
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-white/15 bg-black/20 px-3 py-2 text-xs text-[var(--color-text-secondary)] disabled:opacity-50"
          >
            <Icon name={q.icon} size={14} className="text-[var(--color-brand-gold)]/80" />
            {q.text}
          </motion.button>
        ))}
      </div>

      <div
        className={`mt-4 flex gap-2 rounded-2xl border bg-black/30 p-1 transition-shadow duration-200 ${
          focused ? 'border-[var(--color-brand-gold)]/45 shadow-[0_0_0_3px_rgba(240,199,94,0.12)]' : 'border-white/10'
        }`}
      >
        <input
          className="min-w-0 flex-1 bg-transparent px-3 py-2.5 text-sm text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)]"
          placeholder="说说你的困惑…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={(e) => e.key === 'Enter' && void send(input)}
        />
        <motion.button
          type="button"
          whileTap={{ rotate: 12 }}
          disabled={loading || !input.trim() || !token}
          onClick={() => void send(input)}
          className="flex shrink-0 items-center justify-center rounded-xl bg-[var(--color-brand-gold)] px-4 py-2 font-semibold text-[#0a0b14] disabled:opacity-50"
        >
          <Icon name="send" size={18} />
        </motion.button>
      </div>
      {!orderId ? (
        <Link
          to="/payment?product=chat"
          className="mt-3 block text-center text-xs text-[var(--color-text-muted)] underline"
        >
          购买 AI 顾问对话 ¥0.10
        </Link>
      ) : null}
    </>
  )
}
