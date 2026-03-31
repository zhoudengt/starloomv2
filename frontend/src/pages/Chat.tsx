import { useState } from 'react'
import { Link } from 'react-router-dom'
import { postSseStream } from '../api/stream'
import { StarryBackground } from '../components/StarryBackground'
import { useUserStore } from '../stores/userStore'

export default function Chat() {
  const token = useUserStore((s) => s.token)
  const [msg, setMsg] = useState('')
  const [orderId, setOrderId] = useState('')
  const [reply, setReply] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    if (!token) return
    if (!orderId.trim()) return
    setLoading(true)
    setReply('')
    try {
      await postSseStream(
        '/chat',
        { message: msg, order_id: orderId || undefined },
        token,
        { onContent: (t) => setReply((p) => p + t) },
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <StarryBackground />
      <Link to="/" className="mb-4 inline-block text-sm text-[var(--color-starloom-gold)]">
        ← 返回
      </Link>
      <h1 className="font-serif text-xl text-[var(--color-starloom-gold)]">AI 星座顾问</h1>
      <p className="mt-2 text-xs text-violet-200/70">需先购买「AI 顾问对话」并填写订单号。</p>
      <div className="mt-4 space-y-2">
        <input
          className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm"
          placeholder="订单号（必填）"
          value={orderId}
          onChange={(e) => setOrderId(e.target.value)}
        />
        <textarea
          className="min-h-[100px] w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm"
          placeholder="说说你的困惑…"
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
        />
        <button
          type="button"
          disabled={loading || !msg.trim() || !orderId.trim()}
          onClick={() => void send()}
          className="w-full rounded-xl bg-[var(--color-starloom-gold)] py-3 text-sm font-medium text-[#2d1b69] disabled:opacity-50"
        >
          {loading ? '回复中…' : '发送'}
        </button>
        <Link to="/payment?product=chat" className="block text-center text-xs text-violet-300 underline">
          购买对话次数 ¥9.9
        </Link>
      </div>
      <article className="mt-6 whitespace-pre-wrap text-sm text-violet-100/90">{reply}</article>
    </>
  )
}
