import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { postSseStream } from '../api/stream'
import { StarryBackground } from '../components/StarryBackground'
import { StreamText } from '../components/StreamText'
import { useUserStore } from '../stores/userStore'

export default function ReportPersonality() {
  const token = useUserStore((s) => s.token)
  const [search] = useSearchParams()
  const orderFromUrl = search.get('order_id') ?? ''

  const [birthDate, setBirthDate] = useState('1995-06-15')
  const [birthTime, setBirthTime] = useState('')
  const [gender, setGender] = useState('')
  const [orderId, setOrderId] = useState(orderFromUrl)
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [doneId, setDoneId] = useState<string | null>(null)
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
    setDoneId(null)
    try {
      await postSseStream(
        '/report/personality',
        {
          birth_date: birthDate,
          birth_time: birthTime || undefined,
          gender: gender || undefined,
          order_id: orderId.trim(),
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
  }

  return (
    <>
      <StarryBackground />
      <Link to="/" className="mb-4 inline-block text-sm text-[var(--color-starloom-gold)]">
        ← 返回
      </Link>
      <h1 className="font-serif text-xl text-[var(--color-starloom-gold)]">个人性格分析报告</h1>
      <p className="mt-2 text-xs text-violet-200/70">付费后生成，内容为 AI 实时输出（流式）。</p>

      <div className="mt-6 space-y-3 rounded-2xl border border-white/10 bg-[#2d1b69]/40 p-4 text-sm">
        <label className="block">
          <span className="text-violet-200">出生日期</span>
          <input
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-violet-50"
            value={birthDate}
            onChange={(e) => setBirthDate(e.target.value)}
            type="date"
          />
        </label>
        <label className="block">
          <span className="text-violet-200">出生时间（可选）</span>
          <input
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-violet-50"
            value={birthTime}
            onChange={(e) => setBirthTime(e.target.value)}
            type="time"
          />
        </label>
        <label className="block">
          <span className="text-violet-200">性别（可选）</span>
          <select
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-violet-50"
            value={gender}
            onChange={(e) => setGender(e.target.value)}
          >
            <option value="">未选择</option>
            <option value="female">女</option>
            <option value="male">男</option>
          </select>
        </label>
        <label className="block">
          <span className="text-violet-200">订单号（支付成功后）</span>
          <input
            className="mt-1 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-violet-50"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            placeholder="ord_..."
          />
        </label>
        <button
          type="button"
          onClick={() => void run()}
          disabled={loading}
          className="w-full rounded-xl bg-[var(--color-starloom-gold)] py-3 font-medium text-[#2d1b69] disabled:opacity-50"
        >
          {loading ? '生成中…' : '开始生成报告'}
        </button>
        <Link
          to="/payment?product=personality"
          className="block text-center text-xs text-violet-300 underline"
        >
          去支付 ¥9.9
        </Link>
      </div>

      {err && <p className="mt-4 text-sm text-red-300">{err}</p>}
      {doneId && <p className="mt-2 text-xs text-emerald-300/90">报告已保存 · {doneId}</p>}

      <div className="mt-8">
        <StreamText text={text} />
      </div>
    </>
  )
}
