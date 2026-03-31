import { useMutation } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { createPayment } from '../api/payment'
import { StarryBackground } from '../components/StarryBackground'

const PRODUCTS: Record<string, { amount: number; label: string }> = {
  personality: { amount: 9.9, label: '个人性格报告' },
  compatibility: { amount: 19.9, label: '配对分析' },
  annual: { amount: 29.9, label: '年度运势' },
  chat: { amount: 9.9, label: 'AI 顾问对话' },
}

export default function Payment() {
  const [search] = useSearchParams()
  const product = search.get('product') ?? 'personality'
  const cfg = PRODUCTS[product] ?? PRODUCTS.personality
  const [method, setMethod] = useState<'wechat' | 'alipay'>('wechat')

  const mutation = useMutation({
    mutationFn: () =>
      createPayment({
        product_type: product in PRODUCTS ? product : 'personality',
        amount: cfg.amount,
        pay_method: method,
      }),
  })

  const hint = useMemo(() => mutation.error?.message, [mutation.error])

  const onPay = () => {
    mutation.mutate(undefined, {
      onSuccess: (data) => {
        if (data.pay_url) {
          window.location.href = data.pay_url
        }
      },
    })
  }

  return (
    <>
      <StarryBackground />
      <Link to="/" className="mb-4 inline-block text-sm text-[var(--color-starloom-gold)]">
        ← 返回
      </Link>
      <h1 className="font-serif text-xl text-[var(--color-starloom-gold)]">确认支付</h1>
      <p className="mt-2 text-violet-200/80">
        {cfg.label} · ¥{cfg.amount.toFixed(2)}
      </p>

      <div className="mt-6 space-y-3 rounded-2xl border border-white/10 bg-[#2d1b69]/40 p-4">
        <p className="text-sm text-violet-200">支付方式</p>
        <div className="flex gap-2">
          <button
            type="button"
            className={`flex-1 rounded-lg py-2 text-sm ${method === 'wechat' ? 'bg-[#f0c75e] text-[#2d1b69]' : 'bg-black/20'}`}
            onClick={() => setMethod('wechat')}
          >
            微信
          </button>
          <button
            type="button"
            className={`flex-1 rounded-lg py-2 text-sm ${method === 'alipay' ? 'bg-[#f0c75e] text-[#2d1b69]' : 'bg-black/20'}`}
            onClick={() => setMethod('alipay')}
          >
            支付宝
          </button>
        </div>
        <button
          type="button"
          onClick={onPay}
          disabled={mutation.isPending}
          className="mt-4 w-full rounded-xl bg-[var(--color-starloom-gold)] py-3 font-medium text-[#2d1b69] disabled:opacity-50"
        >
          {mutation.isPending ? '创建订单中…' : '去支付'}
        </button>
        {hint && <p className="text-sm text-red-300">{hint}</p>}
        {mutation.data?.qr_code && (
          <p className="break-all text-xs text-violet-300">二维码：{mutation.data.qr_code}</p>
        )}
      </div>
    </>
  )
}
