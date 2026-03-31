import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { postSseStream } from '../api/stream'
import { StarryBackground } from '../components/StarryBackground'
import { useUserStore } from '../stores/userStore'

export default function AnnualReport() {
  const token = useUserStore((s) => s.token)
  const [search] = useSearchParams()
  const orderFromUrl = search.get('order_id') ?? ''

  const [birthDate, setBirthDate] = useState('1995-06-15')
  const [year, setYear] = useState(new Date().getFullYear())
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
        '/report/annual',
        { birth_date: birthDate, order_id: orderId.trim(), year },
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
      <h1 className="font-serif text-xl text-[var(--color-starloom-gold)]">年度运势参考</h1>
      <div className="mt-6 space-y-3 rounded-2xl border border-white/10 bg-[#2d1b69]/40 p-4 text-sm">
        <label className="block">
          出生日期
          <input
            type="date"
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
            value={birthDate}
            onChange={(e) => setBirthDate(e.target.value)}
          />
        </label>
        <label className="block">
          年份
          <input
            type="number"
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          />
        </label>
        <label className="block">
          订单号
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
          {loading ? '生成中…' : '生成年度报告'}
        </button>
        <Link to="/payment?product=annual" className="block text-center text-xs text-violet-300 underline">
          去支付 ¥29.9
        </Link>
      </div>
      {err && <p className="mt-4 text-sm text-red-300">{err}</p>}
      <article className="mt-8 whitespace-pre-wrap text-sm text-violet-100/90">{text}</article>
    </>
  )
}
