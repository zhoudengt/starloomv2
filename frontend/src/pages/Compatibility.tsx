import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { postSseStream } from '../api/stream'
import { StarryBackground } from '../components/StarryBackground'
import { useUserStore } from '../stores/userStore'

export default function Compatibility() {
  const token = useUserStore((s) => s.token)
  const [search] = useSearchParams()
  const orderFromUrl = search.get('order_id') ?? ''

  const [p1Name, setP1Name] = useState('小明')
  const [p1Date, setP1Date] = useState('1995-06-15')
  const [p1Gender, setP1Gender] = useState('female')
  const [p2Name, setP2Name] = useState('小红')
  const [p2Date, setP2Date] = useState('1993-11-22')
  const [p2Gender, setP2Gender] = useState('male')
  const [orderId, setOrderId] = useState(orderFromUrl)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const run = async () => {
    if (!token) {
      setErr('请先打开首页完成登录')
      return
    }
    if (!orderId.trim()) {
      setErr('请先完成支付或填写订单号')
      return
    }
    setErr(null)
    setLoading(true)
    setText('')
    try {
      await postSseStream(
        '/report/compatibility',
        {
          person1: { name: p1Name, birth_date: p1Date, gender: p1Gender },
          person2: { name: p2Name, birth_date: p2Date, gender: p2Gender },
          order_id: orderId.trim(),
        },
        token,
        { onContent: (t) => setText((prev) => prev + t) },
      )
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : '生成失败')
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
      <h1 className="font-serif text-xl text-[var(--color-starloom-gold)]">配对分析报告</h1>

      <div className="mt-6 space-y-4 rounded-2xl border border-white/10 bg-[#2d1b69]/40 p-4 text-sm">
        <p className="text-violet-200">用户 A</p>
        <input
          className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
          value={p1Name}
          onChange={(e) => setP1Name(e.target.value)}
          placeholder="称呼"
        />
        <input
          type="date"
          className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
          value={p1Date}
          onChange={(e) => setP1Date(e.target.value)}
        />
        <select
          className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
          value={p1Gender}
          onChange={(e) => setP1Gender(e.target.value)}
        >
          <option value="female">女</option>
          <option value="male">男</option>
        </select>

        <p className="text-violet-200">用户 B</p>
        <input
          className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
          value={p2Name}
          onChange={(e) => setP2Name(e.target.value)}
        />
        <input
          type="date"
          className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
          value={p2Date}
          onChange={(e) => setP2Date(e.target.value)}
        />
        <select
          className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
          value={p2Gender}
          onChange={(e) => setP2Gender(e.target.value)}
        >
          <option value="female">女</option>
          <option value="male">男</option>
        </select>

        <label className="block">
          <span className="text-violet-200">订单号</span>
          <input
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
          />
        </label>
        <button
          type="button"
          onClick={() => void run()}
          disabled={loading}
          className="w-full rounded-xl bg-[var(--color-starloom-gold)] py-3 font-medium text-[#2d1b69]"
        >
          {loading ? '生成中…' : '生成配对报告'}
        </button>
        <Link to="/payment?product=compatibility" className="block text-center text-xs text-violet-300 underline">
          去支付 ¥19.9
        </Link>
      </div>
      {err && <p className="mt-4 text-sm text-red-300">{err}</p>}
      <article className="mt-8 whitespace-pre-wrap text-sm text-violet-100/90">{text}</article>
    </>
  )
}
